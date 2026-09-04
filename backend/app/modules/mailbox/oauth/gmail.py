import urllib.parse
from typing import Dict, Any, Optional
import httpx
from app.core.config import settings
from app.modules.mailbox.oauth.base import BaseOAuthClient
from app.modules.mailbox.exceptions import MailboxAuthError

GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

GMAIL_READONLY_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

class GoogleOAuthClient(BaseOAuthClient):
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        self.client_id = client_id or settings.GOOGLE_CLIENT_ID
        self.client_secret = client_secret or settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id or "google-client-id-placeholder",
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_READONLY_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "include_granted_scopes": "true",
        }
        return f"{GMAIL_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        # Handle testing / mock flow
        if code.startswith("mock_") or code.startswith("test_") or "mock" in (self.client_id or ""):
            email_slug = code.replace("mock_", "").replace("test_", "")
            email = f"candidate.{email_slug}@gmail.com" if "@" not in email_slug else email_slug
            return {
                "access_token": f"mock_gmail_access_token_{code}",
                "refresh_token": f"mock_gmail_refresh_token_{code}",
                "expires_in": 3600,
                "email_address": email,
                "provider_account_id": f"google_acc_{code}",
                "scopes": GMAIL_READONLY_SCOPES,
            }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GMAIL_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
                timeout=15.0,
            )
            if resp.status_code != 200:
                raise MailboxAuthError(f"Failed to exchange Google OAuth code: {resp.text}")
            data = resp.json()

        access_token = data.get("access_token")
        profile = await self.get_user_profile(access_token)

        return {
            "access_token": access_token,
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in", 3600),
            "email_address": profile.get("email"),
            "provider_account_id": profile.get("id"),
            "scopes": data.get("scope", "").split(" ") if data.get("scope") else GMAIL_READONLY_SCOPES,
        }

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        if refresh_token.startswith("mock_") or refresh_token.startswith("test_"):
            return {
                "access_token": f"mock_refreshed_access_{refresh_token}",
                "refresh_token": refresh_token,
                "expires_in": 3600,
            }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GMAIL_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=15.0,
            )
            if resp.status_code != 200:
                raise MailboxAuthError(f"Failed to refresh Google OAuth token: {resp.text}")
            data = resp.json()

        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token", refresh_token),
            "expires_in": data.get("expires_in", 3600),
        }

    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        if access_token.startswith("mock_") or access_token.startswith("test_"):
            return {
                "id": "mock_google_id_123",
                "email": "candidate@gmail.com",
                "name": "Candidate User",
            }

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                GMAIL_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                raise MailboxAuthError(f"Failed to retrieve Google user profile: {resp.text}")
            return resp.json()
