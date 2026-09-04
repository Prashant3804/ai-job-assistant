import uuid
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.application import ApplicationEvent
from app.shared.constants import ApplicationEventType

class ApplicationEventManager:
    """Creates and persists timeline events for tracking application lifecycle progression."""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        application_id: uuid.UUID,
        event_type: ApplicationEventType,
        title: str,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApplicationEvent:
        event = ApplicationEvent(
            id=uuid.uuid4(),
            application_id=application_id,
            event_type=event_type.value if hasattr(event_type, 'value') else str(event_type),
            old_status=old_status,
            new_status=new_status,
            title=title,
            description=description,
            event_metadata=metadata or {}
        )
        db.add(event)
        return event
