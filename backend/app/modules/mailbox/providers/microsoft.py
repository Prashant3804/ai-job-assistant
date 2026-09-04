from datetime import datetime
from typing import List, Optional, Tuple
import httpx
from app.modules.mailbox.providers.base import BaseMailboxProvider
from app.modules.mailbox.normalizer import NormalizedEmail, normalize_microsoft_message
from app.modules.mailbox.exceptions import MailboxAuthError, TokenExpiredError, ProviderRateLimitError

MICROSOFT_GRAPH_BASE = "https://graph.microsoft.com/v1.0/me"

class MicrosoftMailboxProvider(BaseMailboxProvider):
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def fetch_messages(
        self,
        cursor: Optional[str] = None,
        max_results: int = 50,
        since: Optional[datetime] = None
    ) -> Tuple[List[NormalizedEmail], Optional[str]]:
        params = {"$top": min(max_results, 50)}
        if cursor:
            params["$skipToken"] = cursor
        if since:
            since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["$filter"] = f"receivedDateTime ge {since_iso}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{MICROSOFT_GRAPH_BASE}/messages",
                headers=self.headers,
                params=params,
                timeout=15.0
            )
            if resp.status_code == 401:
                raise TokenExpiredError("Microsoft access token has expired")
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "60"))
                raise ProviderRateLimitError(retry_after_seconds=retry_after)
            elif resp.status_code != 200:
                raise MailboxAuthError(f"Microsoft Graph API error: {resp.text}")

            data = resp.json()
            messages = data.get("value", [])
            next_link = data.get("@odata.nextLink")
            next_cursor = None
            if next_link and "$skipToken=" in next_link:
                next_cursor = next_link.split("$skipToken=")[1].split("&")[0]

            normalized_list = [normalize_microsoft_message(m) for m in messages]
            return normalized_list, next_cursor

    async def fetch_message_by_id(self, external_message_id: str) -> Optional[NormalizedEmail]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{MICROSOFT_GRAPH_BASE}/messages/{external_message_id}",
                headers=self.headers,
                timeout=15.0
            )
            if resp.status_code == 401:
                raise TokenExpiredError("Microsoft access token has expired")
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "60"))
                raise ProviderRateLimitError(retry_after_seconds=retry_after)
            elif resp.status_code != 200:
                return None

            return normalize_microsoft_message(resp.json())

    async def fetch_thread_messages(self, external_thread_id: str) -> List[NormalizedEmail]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{MICROSOFT_GRAPH_BASE}/messages",
                headers=self.headers,
                params={"$filter": f"conversationId eq '{external_thread_id}'", "$orderby": "receivedDateTime asc"},
                timeout=15.0
            )
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            return [normalize_microsoft_message(m) for m in data.get("value", [])]
