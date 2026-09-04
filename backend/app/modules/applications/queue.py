import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.application import ApplicationQueueItem, Application, DeadLetterApplicationQueue
from app.database.models.job import Job
from app.shared.constants import QueueStatus

class ApplicationQueueService:
    """Manages the background application queue with priority scheduling, worker leasing, and dead-letter handling."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def enqueue(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        job_id: uuid.UUID,
        priority: int = 10,
        idempotency_key: Optional[str] = None
    ) -> ApplicationQueueItem:
        # Check existing active queue item for this application
        stmt_check = select(ApplicationQueueItem).where(
            and_(
                ApplicationQueueItem.application_id == application_id,
                ApplicationQueueItem.status.in_([QueueStatus.QUEUED.value, QueueStatus.PROCESSING.value, QueueStatus.RETRYING.value])
            )
        )
        res_check = await self.db.execute(stmt_check)
        existing = res_check.scalar_one_or_none()
        if existing:
            return existing

        key = idempotency_key or f"q_{user_id}_{job_id}_{uuid.uuid4().hex[:6]}"
        item = ApplicationQueueItem(
            id=uuid.uuid4(),
            user_id=user_id,
            application_id=application_id,
            job_id=job_id,
            priority=priority,
            status=QueueStatus.QUEUED.value,
            attempt_count=0,
            max_attempts=3,
            scheduled_at=datetime.now(timezone.utc),
            idempotency_key=key
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_due_items(self, limit: int = 10) -> List[ApplicationQueueItem]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(ApplicationQueueItem)
            .options(
                selectinload(ApplicationQueueItem.application),
                selectinload(ApplicationQueueItem.job).selectinload(Job.job_source),
                selectinload(ApplicationQueueItem.user),
            )
            .where(
                and_(
                    ApplicationQueueItem.status.in_([QueueStatus.QUEUED.value, QueueStatus.RETRYING.value]),
                    ApplicationQueueItem.scheduled_at <= now
                )
            )
            .order_by(ApplicationQueueItem.priority.desc(), ApplicationQueueItem.scheduled_at.asc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_user_queue(self, user_id: uuid.UUID) -> List[ApplicationQueueItem]:
        stmt = (
            select(ApplicationQueueItem)
            .options(
                selectinload(ApplicationQueueItem.job),
                selectinload(ApplicationQueueItem.application)
            )
            .where(ApplicationQueueItem.user_id == user_id)
            .order_by(ApplicationQueueItem.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def mark_processing(
        self,
        item: ApplicationQueueItem,
        worker_id: Optional[str] = None,
        lease_seconds: int = 300
    ) -> None:
        now = datetime.now(timezone.utc)
        item.status = QueueStatus.PROCESSING.value
        item.started_at = now
        item.attempt_count += 1
        item.locked_by = worker_id or "worker-default"
        item.locked_at = now
        item.lease_expires_at = now + timedelta(seconds=lease_seconds)
        await self.db.flush()

    async def mark_completed(self, item: ApplicationQueueItem) -> None:
        item.status = QueueStatus.COMPLETED.value
        item.completed_at = datetime.now(timezone.utc)
        item.error_message = None
        item.locked_by = None
        item.lease_expires_at = None
        await self.db.flush()

    async def mark_failed(self, item: ApplicationQueueItem, error_message: str) -> None:
        item.status = QueueStatus.FAILED.value
        item.completed_at = datetime.now(timezone.utc)
        item.error_message = error_message
        item.locked_by = None
        item.lease_expires_at = None
        await self.db.flush()

    async def mark_retrying(self, item: ApplicationQueueItem, delay_seconds: int, error_message: str) -> None:
        item.status = QueueStatus.RETRYING.value
        item.scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        item.error_message = error_message
        item.locked_by = None
        item.lease_expires_at = None
        await self.db.flush()

    async def recover_expired_leases(self, lease_timeout_seconds: int = 300) -> int:
        """Finds PROCESSING items whose lease expired (worker crash recovery) and resets them for re-processing."""
        now = datetime.now(timezone.utc)
        stmt = select(ApplicationQueueItem).where(
            and_(
                ApplicationQueueItem.status == QueueStatus.PROCESSING.value,
                or_(
                    ApplicationQueueItem.lease_expires_at <= now,
                    ApplicationQueueItem.started_at <= (now - timedelta(seconds=lease_timeout_seconds))
                )
            )
        )
        res = await self.db.execute(stmt)
        stuck_items = list(res.scalars().all())
        for item in stuck_items:
            item.status = QueueStatus.RETRYING.value
            item.locked_by = None
            item.lease_expires_at = None
            item.scheduled_at = now
            item.error_message = "Worker lease expired; re-queued for recovery."
        if stuck_items:
            await self.db.flush()
        return len(stuck_items)

    async def move_to_dead_letter(
        self,
        item: ApplicationQueueItem,
        failure_reason: str,
        last_error: Optional[str] = None
    ) -> DeadLetterApplicationQueue:
        """Moves a permanently failed queue item into the dead letter queue."""
        item.status = QueueStatus.FAILED.value
        item.completed_at = datetime.now(timezone.utc)
        item.error_message = failure_reason
        item.locked_by = None
        item.lease_expires_at = None

        dlq_entry = DeadLetterApplicationQueue(
            id=uuid.uuid4(),
            user_id=item.user_id,
            application_id=item.application_id,
            job_id=item.job_id,
            failure_reason=failure_reason,
            attempt_count=item.attempt_count,
            last_error=last_error or item.error_message,
            resolved=False
        )
        self.db.add(dlq_entry)
        await self.db.flush()
        return dlq_entry

    async def get_dead_letter_items(self, user_id: Optional[uuid.UUID] = None) -> List[DeadLetterApplicationQueue]:
        stmt = select(DeadLetterApplicationQueue).options(
            selectinload(DeadLetterApplicationQueue.application),
            selectinload(DeadLetterApplicationQueue.job)
        )
        if user_id:
            stmt = stmt.where(DeadLetterApplicationQueue.user_id == user_id)
        stmt = stmt.order_by(DeadLetterApplicationQueue.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

