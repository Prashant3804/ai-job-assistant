"""
Mailbox OAuth Providers
"""
from app.modules.mailbox.oauth.base import BaseOAuthClient
from app.modules.mailbox.oauth.gmail import GoogleOAuthClient
from app.modules.mailbox.oauth.microsoft import MicrosoftOAuthClient

__all__ = ["BaseOAuthClient", "GoogleOAuthClient", "MicrosoftOAuthClient"]
