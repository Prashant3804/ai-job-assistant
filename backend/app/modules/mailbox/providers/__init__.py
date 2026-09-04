"""
Mailbox Providers (Gmail, Microsoft Graph, and Mock Provider)
"""
from app.modules.mailbox.providers.base import BaseMailboxProvider
from app.modules.mailbox.providers.gmail import GmailMailboxProvider
from app.modules.mailbox.providers.microsoft import MicrosoftMailboxProvider
from app.modules.mailbox.providers.mock import MockMailboxProvider

__all__ = [
    "BaseMailboxProvider",
    "GmailMailboxProvider",
    "MicrosoftMailboxProvider",
    "MockMailboxProvider",
]
