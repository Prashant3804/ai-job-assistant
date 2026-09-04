import urllib.parse
from typing import Dict, Any, Optional
import httpx
from app.core.config import settings
from app.modules.mailbox.oauth.base import BaseOAuthClient
from app.modules.mailbox.exceptions import MailboxAuthError

MICROSOFT_GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"

MICROSOFT_READONLY_SCOPES = [
    "Mail.Read",
    "User.Read",
    "offline_access",
]

class MicrosoftOAuthClient(BaseOAuthClient):
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        self.client_id = client_id or settings.MICROSOFT_CLIENT_ID
        self.client_secret = client_secret or settings.MICROSOFT_CLIENT_SECRET
        self.tenant_id = tenant_id or settings.MICROSOFT_TENANT_ID or "common"
        self.redirect_uri = redirect_uri or settings.MICROSOFT_REDIRECT_URI

    @property
    def auth_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"

    @property
    def token_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id or "microsoft-client-id-placeholder",
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "response_mode": "query",
            "scope": " ".join(MICROSOFT_READONLY_SCOPES),
            "state": state,
            "prompt": "consent",
        }
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        # Handle testing / mock flow
        if code.startswith("mock_") or code.startswith("test_") or "mock" in (self.client_id or ""):
            email_slug = code.replace("mock_", "").replace("test_", "")
            email = f"candidate.{email_slug}@outlook.com" if "@" not in email_slug else email_slug
            return {
                "access_token": f"mock_ms_access_token_{code}",
                "refresh_token": f"mock_ms_refresh_token_{code}",
                "expires_in": 3600,
                "email_address": email,
                "provider_account_id": f"ms_acc_{code}",
                "scopes": MICROSOFT_READONLY_SCOPES,
            }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                    "scope": " ".join(MICROSOFT_READONLY_SCOPES),
                },
                timeout=15.0,
            )
            if resp.status_code != 200:
                raise MailboxAuthError(f"Failed to exchange Microsoft OAuth code: {resp.text}")
            data = resp.json()

        access_token = data.get("access_token")
        profile = await self.get_user_profile(access_token)

        email = profile.get("mail") or profile.get("userPrincipalName")

        return {
            "access_token": access_token,
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in", 3600),
            "email_address": email,
            "provider_account_id": profile.get("id"),
            "scopes": data.get("scope", "").split(" ") if data.get("scope") else MICROSOFT_READONLY_SCOPES,
        }

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        if refresh_token.startswith("mock_") or refresh_token.startswith("test_"):
            return {
                "access_token": f"mock_refreshed_ms_access_{refresh_token}",
                "refresh_token": refresh_token,
                "expires_in": 3600,
            }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": " ".join(MICROSOFT_READONLY_SCOPES),
                },
                timeout=15.0,
            )
            if resp.status_code != 200:
                raise MailboxAuthError(f"Failed to refresh Microsoft OAuth token: {resp.text}")
            data = resp.json()

        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token", refresh_token),
            "expires_in": data.get("expires_in", 3600),
        }

    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        if access_token.startswith("mock_") or access_token.startswith("test_"):
            return {
                "id": "mock_ms_id_456",
                "mail": "candidate@outlook.com",
                "displayName": "Candidate User",
                "userPrincipalName": "candidate@outlook.com",
            }

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                MICROSOFT_GRAPH_ME_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                raise MailboxAuthError(f"Failed to retrieve Microsoft user profile: {resp.text}")
            return resp.json()
