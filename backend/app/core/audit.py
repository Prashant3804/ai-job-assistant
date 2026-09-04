import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.system import AuditEvent
from app.shared.constants import AuditEventType
from app.core.config import settings

logger = logging.getLogger(__name__)

# Sensitive keys to scrub from metadata
SENSITIVE_KEYS = {
    "password", "secret", "token", "access_token", "refresh_token",
    "authorization", "api_key", "secret_key", "encryption_key",
    "client_secret", "cookie"
}

def sanitize_metadata(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not data or not isinstance(data, dict):
        return {}
    sanitized = {}
    for k, v in data.items():
        if any(sens in k.lower() for sens in SENSITIVE_KEYS):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_metadata(v)
        elif isinstance(v, str) and len(v) > 500:
            sanitized[k] = v[:500] + "... [TRUNCATED]"
        else:
            sanitized[k] = v
    return sanitized

class AuditService:
    """Centralized audit logger for security, compliance, and lifecycle events."""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        action: str,
        resource_type: str,
        user_id: Optional[uuid.UUID] = None,
        actor: str = "USER",
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[AuditEvent]:
        if not settings.AUDIT_LOGGING_ENABLED:
            return None

        clean_meta = sanitize_metadata(metadata)
        event = AuditEvent(
            id=uuid.uuid4(),
            user_id=user_id,
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            metadata_json=clean_meta
        )
        db.add(event)
        try:
            await db.flush()
        except Exception as e:
            logger.warning(f"Failed to record audit event: {e}")
        return event
