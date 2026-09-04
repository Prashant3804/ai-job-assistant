from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.application import ApplicationQueueItem, DeadLetterApplicationQueue
from app.shared.constants import QueueStatus

class WorkerStatus:
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.status = "ACTIVE"
        self.started_at = datetime.now(timezone.utc)
        self.last_heartbeat_at = datetime.now(timezone.utc)
        self.jobs_processed = 0
        self.jobs_failed = 0
        self.current_job_id: Optional[str] = None

    def heartbeat(self, current_job_id: Optional[str] = None):
        self.last_heartbeat_at = datetime.now(timezone.utc)
        self.current_job_id = current_job_id
        self.status = "ACTIVE"

    def record_completed(self):
        self.jobs_processed += 1
        self.current_job_id = None
        self.last_heartbeat_at = datetime.now(timezone.utc)

    def record_failed(self):
        self.jobs_failed += 1
        self.current_job_id = None
        self.last_heartbeat_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "last_heartbeat_at": self.last_heartbeat_at.isoformat(),
            "jobs_processed": self.jobs_processed,
            "jobs_failed": self.jobs_failed,
            "current_job_id": self.current_job_id
        }

class WorkerMonitorService:
    """Monitors worker heartbeats, queue depths, throughput, and dead-letter statistics."""

    def __init__(self):
        self._workers: Dict[str, WorkerStatus] = {}
        self.recovery_events_count: int = 0

    def register_worker(self, worker_id: str) -> WorkerStatus:
        if worker_id not in self._workers:
            self._workers[worker_id] = WorkerStatus(worker_id)
        return self._workers[worker_id]

    def heartbeat(self, worker_id: str, current_job_id: Optional[str] = None):
        w = self.register_worker(worker_id)
        w.heartbeat(current_job_id)

    def record_completed(self, worker_id: str = "worker-default"):
        w = self.register_worker(worker_id)
        w.record_completed()

    def record_failed(self, worker_id: str = "worker-default"):
        w = self.register_worker(worker_id)
        w.record_failed()


    async def get_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        # Count by status in queue
        stmt_queue = select(ApplicationQueueItem.status, func.count(ApplicationQueueItem.id)).group_by(ApplicationQueueItem.status)
        res_queue = await db.execute(stmt_queue)
        queue_counts = dict(res_queue.all())

        # Count in DLQ
        stmt_dlq = select(func.count(DeadLetterApplicationQueue.id))
        dlq_count = (await db.execute(stmt_dlq)).scalar_one()

        # Prune dead workers if heartbeat older than 5 mins
        now = datetime.now(timezone.utc)
        for wid, w in self._workers.items():
            if now - w.last_heartbeat_at > timedelta(seconds=300):
                w.status = "INACTIVE"

        return {
            "active_workers_count": sum(1 for w in self._workers.values() if w.status == "ACTIVE"),
            "total_workers": [w.to_dict() for w in self._workers.values()],
            "queue_depth": {
                "queued": queue_counts.get(QueueStatus.QUEUED.value, 0),
                "processing": queue_counts.get(QueueStatus.PROCESSING.value, 0),
                "retrying": queue_counts.get(QueueStatus.RETRYING.value, 0),
                "completed": queue_counts.get(QueueStatus.COMPLETED.value, 0),
                "failed": queue_counts.get(QueueStatus.FAILED.value, 0),
            },
            "dead_letter_count": dlq_count,
            "recovery_events_count": self.recovery_events_count
        }

# Global Singleton
worker_monitor_service = WorkerMonitorService()
