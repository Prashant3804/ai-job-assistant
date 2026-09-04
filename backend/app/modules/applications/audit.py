import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.application import ApplicationAuditLog

class ApplicationAuditLogger:
    """Records immutable audit logs for every automated application decision and submission."""

    @staticmethod
    async def log_action(
        db: AsyncSession,
        user_id: uuid.UUID,
        result: str,
        application_id: Optional[uuid.UUID] = None,
        job_id: Optional[uuid.UUID] = None,
        source: Optional[str] = None,
        match_score: Optional[float] = None,
        policy_decision: Optional[str] = None,
        resume_version_id: Optional[uuid.UUID] = None,
        connector: Optional[str] = None,
        submission_method: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> ApplicationAuditLog:
        audit = ApplicationAuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            application_id=application_id,
            job_id=job_id,
            source=source,
            match_score=match_score,
            policy_decision=policy_decision,
            resume_version_id=resume_version_id,
            connector=connector,
            submission_method=submission_method,
            result=result,
            failure_reason=failure_reason
        )
        db.add(audit)
        return audit
