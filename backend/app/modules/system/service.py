import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy import select, text, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.database.models.system import AuditEvent
from app.database.models.application import ApplicationQueueItem, DeadLetterApplicationQueue
from app.modules.connectors.registry import connector_registry
from app.modules.connectors.health import connector_health_service
from app.modules.applications.worker_monitor import worker_monitor_service

class SystemMonitoringService:
    """Aggregates system health, worker telemetry, connector status, and audit logs."""

    @staticmethod
    async def check_readiness(db: AsyncSession) -> Dict[str, Any]:
        db_status = "HEALTHY"
        try:
            await db.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"DOWN: {str(e)}"

        return {
            "status": "READY" if db_status == "HEALTHY" else "NOT_READY",
            "database": db_status,
            "queue": "HEALTHY",
            "connectors": "HEALTHY",
            "timestamp": datetime.now(timezone.utc)
        }

    @staticmethod
    async def get_detailed_health(db: AsyncSession) -> Dict[str, Any]:
        # 1. Database Check
        db_details = {"status": "HEALTHY", "engine": "async-sql"}
        try:
            await db.execute(text("SELECT 1"))
        except Exception as e:
            db_details = {"status": "UNHEALTHY", "error": str(e)}

        # 2. Worker & Queue metrics
        worker_metrics = await worker_monitor_service.get_metrics(db)

        # 3. Connector health summary
        conn_health = connector_health_service.get_all_health()

        # 4. AI Provider status
        ai_status = {
            "provider": settings.DEFAULT_AI_PROVIDER,
            "status": "CONFIGURED",
            "chat_model": settings.OMNIROUTE_CHAT_MODEL if settings.DEFAULT_AI_PROVIDER == "omniroute" else settings.OPENAI_MODEL,
            "timeout_seconds": settings.OMNIROUTE_TIMEOUT_SECONDS
        }

        overall = "HEALTHY" if db_details["status"] == "HEALTHY" else "DEGRADED"

        return {
            "status": overall,
            "environment": settings.ENVIRONMENT,
            "database": db_details,
            "queue": worker_metrics["queue_depth"],
            "workers": {
                "active_count": worker_metrics["active_workers_count"],
                "dead_letter_count": worker_metrics["dead_letter_count"]
            },
            "connectors": conn_health,
            "ai_provider": ai_status,
            "timestamp": datetime.now(timezone.utc)
        }

    @staticmethod
    async def get_audit_logs(
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AuditEvent]:
        stmt = select(AuditEvent)
        conditions = []
        if user_id:
            conditions.append(AuditEvent.user_id == user_id)
        if action:
            conditions.append(AuditEvent.action == action)
        if resource_type:
            conditions.append(AuditEvent.resource_type == resource_type)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)
        res = await db.execute(stmt)
        return list(res.scalars().all())
