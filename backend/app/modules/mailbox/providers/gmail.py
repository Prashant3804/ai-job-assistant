from datetime import datetime
from typing import List, Optional, Tuple
import httpx
from app.modules.mailbox.providers.base import BaseMailboxProvider
from app.modules.mailbox.normalizer import NormalizedEmail, normalize_gmail_message
from app.modules.mailbox.exceptions import MailboxAuthError, TokenExpiredError, ProviderRateLimitError

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

class GmailMailboxProvider(BaseMailboxProvider):
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def fetch_messages(
        self,
        cursor: Optional[str] = None,
        max_results: int = 50,
        since: Optional[datetime] = None
    ) -> Tuple[List[NormalizedEmail], Optional[str]]:
        params = {"maxResults": min(max_results, 100)}
        if cursor:
            params["pageToken"] = cursor
        if since:
            timestamp = int(since.timestamp())
            params["q"] = f"after:{timestamp}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GMAIL_API_BASE}/messages",
                headers=self.headers,
                params=params,
                timeout=15.0
            )
            if resp.status_code == 401:
                raise TokenExpiredError("Gmail access token has expired")
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "60"))
                raise ProviderRateLimitError(retry_after_seconds=retry_after)
            elif resp.status_code != 200:
                raise MailboxAuthError(f"Gmail API error: {resp.text}")

            data = resp.json()
            message_stubs = data.get("messages", [])
            next_page_token = data.get("nextPageToken")

            normalized_list: List[NormalizedEmail] = []
            for stub in message_stubs:
                msg_id = stub.get("id")
                if msg_id:
                    msg = await self.fetch_message_by_id(msg_id)
                    if msg:
                        normalized_list.append(msg)

            return normalized_list, next_page_token

    async def fetch_message_by_id(self, external_message_id: str) -> Optional[NormalizedEmail]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GMAIL_API_BASE}/messages/{external_message_id}",
                headers=self.headers,
                params={"format": "full"},
                timeout=15.0
            )
            if resp.status_code == 401:
                raise TokenExpiredError("Gmail access token has expired")
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "60"))
                raise ProviderRateLimitError(retry_after_seconds=retry_after)
            elif resp.status_code != 200:
                return None

            return normalize_gmail_message(resp.json())

    async def fetch_thread_messages(self, external_thread_id: str) -> List[NormalizedEmail]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GMAIL_API_BASE}/threads/{external_thread_id}",
                headers=self.headers,
                params={"format": "full"},
                timeout=15.0
            )
            if resp.status_code != 200:
                return []
            
            thread_data = resp.json()
            messages = thread_data.get("messages", [])
            return [normalize_gmail_message(m) for m in messages]
