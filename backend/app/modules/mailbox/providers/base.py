from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.modules.mailbox.normalizer import NormalizedEmail

class BaseMailboxProvider(ABC):
    """Abstract interface for mailbox data provider."""

    @abstractmethod
    async def fetch_messages(
        self,
        cursor: Optional[str] = None,
        max_results: int = 50,
        since: Optional[datetime] = None
    ) -> Tuple[List[NormalizedEmail], Optional[str]]:
        """
        Fetches normalized messages from the mailbox provider.
        Returns (list_of_normalized_messages, next_cursor).
        """
        pass

    @abstractmethod
    async def fetch_message_by_id(self, external_message_id: str) -> Optional[NormalizedEmail]:
        """Fetches full normalized details for a specific message."""
        pass

    @abstractmethod
    async def fetch_thread_messages(self, external_thread_id: str) -> List[NormalizedEmail]:
        """Fetches all messages belonging to a thread."""
        pass
