from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseOAuthClient(ABC):
    """Abstract base class for Mailbox OAuth2 providers."""

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Returns the provider authorization URL with required read-only scopes."""
        pass

    @abstractmethod
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """
        Exchanges the authorization code for tokens and user profile information.
        Must return:
        {
            "access_token": str,
            "refresh_token": Optional[str],
            "expires_in": int, # seconds
            "email_address": str,
            "provider_account_id": Optional[str],
            "scopes": List[str]
        }
        """
        pass

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refreshes an expired access token using the refresh token.
        Must return:
        {
            "access_token": str,
            "refresh_token": Optional[str],
            "expires_in": int
        }
        """
        pass

    @abstractmethod
    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Fetches the user's primary email address and account ID."""
        pass
