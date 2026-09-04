"""
Custom exceptions for the Mailbox & OAuth Integration module.
"""

class MailboxError(Exception):
    """Base exception for all mailbox operations."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class MailboxAuthError(MailboxError):
    """Raised when authentication with the mailbox provider fails."""
    pass

class TokenExpiredError(MailboxAuthError):
    """Raised when access token has expired and refresh token is missing or invalid."""
    pass

class OAuthStateMismatchError(MailboxAuthError):
    """Raised when OAuth state token verification fails."""
    pass

class ProviderRateLimitError(MailboxError):
    """Raised when the upstream provider rate-limits API requests."""
    def __init__(self, message: str = "Rate limit exceeded by mailbox provider", retry_after_seconds: int = 60, details: dict = None):
        super().__init__(message, details)
        self.retry_after_seconds = retry_after_seconds

class MailboxSyncError(MailboxError):
    """Raised when an error occurs during email synchronization."""
    pass

class MailboxQuotaExceededError(MailboxError):
    """Raised when synchronization limits are reached."""
    pass

class MailboxConnectionNotFoundError(MailboxError):
    """Raised when a mailbox connection ID cannot be found for the user."""
    pass
