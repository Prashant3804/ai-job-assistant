import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.application import (
    Application,
    ApplicationPolicy,
    ApplicationQueueItem,
    ApplicationEvent,
    ApplicationAttempt,
    ApplicationAuditLog
)
from app.database.models.job import Job, JobSource
from app.database.models.match import JobMatch
from app.database.models.user import User
from app.core.exceptions import DuplicateEntityError, EntityNotFoundError, UnauthorizedIntegrationError
from app.shared.constants import (
    ApplicationStatus,
    ApplicationEventType,
    SubmissionMethod,
    ConnectorCapabilityStatus,
    QueueStatus,
    PolicyDecision
)
from app.shared.schemas import ApplicationCreate, ApplicationUpdateStatus
from app.modules.applications.schemas import (
    ApplicationPolicyUpdate,
    ApplicationPolicyRead,
    AutoApplyStatusRead,
    ApplicationStatisticsRead,
    ProcessQueueResponse
)
from app.modules.applications.policy import ApplicationPolicyEngine
from app.modules.applications.duplicate import DuplicateDetector
from app.modules.applications.capabilities import PlatformCapabilityManager
from app.modules.applications.queue import ApplicationQueueService
from app.modules.applications.agent import ApplicationAgent
from app.modules.applications.events import ApplicationEventManager
from app.modules.applications.audit import ApplicationAuditLogger
from app.modules.applications.state_machine import ApplicationStateMachine

class ApplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== POLICY MANAGEMENT ====================

    async def get_or_create_policy(self, user_id: uuid.UUID) -> ApplicationPolicy:
        stmt = select(ApplicationPolicy).where(ApplicationPolicy.user_id == user_id)
        res = await self.db.execute(stmt)
        policy = res.scalar_one_or_none()
        if not policy:
            policy = ApplicationPolicy(
                id=uuid.uuid4(),
                user_id=user_id,
                auto_apply_enabled=False,
                minimum_match_score=85.0,
                daily_application_limit=30,
                per_source_daily_limit=10,
                duplicate_protection=True,
                allow_entry_level=True,
                allow_internships=True,
                allow_remote=True,
                allow_hybrid=True,
                allow_onsite=True
            )
            self.db.add(policy)
            await self.db.commit()
            await self.db.refresh(policy)
        return policy

    async def update_policy(self, user_id: uuid.UUID, payload: ApplicationPolicyUpdate) -> ApplicationPolicy:
        policy = await self.get_or_create_policy(user_id)
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(policy, key, value)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def get_auto_apply_status(self, user_id: uuid.UUID) -> AutoApplyStatusRead:
        policy = await self.get_or_create_policy(user_id)

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt_today = select(func.count(Application.id)).where(
            and_(
                Application.user_id == user_id,
                Application.status.in_([ApplicationStatus.APPLIED.value, ApplicationStatus.SUBMITTED.value]),
                Application.applied_date >= today_start
            )
        )
        today_count = (await self.db.execute(stmt_today)).scalar_one()

        stmt_queue = select(func.count(ApplicationQueueItem.id)).where(
            and_(
                ApplicationQueueItem.user_id == user_id,
                ApplicationQueueItem.status.in_([QueueStatus.QUEUED.value, QueueStatus.PROCESSING.value, QueueStatus.RETRYING.value])
            )
        )
        queue_count = (await self.db.execute(stmt_queue)).scalar_one()

        stmt_stats = select(Application.status, func.count(Application.id)).where(Application.user_id == user_id).group_by(Application.status)
        stat_rows = (await self.db.execute(stmt_stats)).all()
        counts_by_status = {row[0]: row[1] for row in stat_rows}

        successful = counts_by_status.get(ApplicationStatus.APPLIED.value, 0) + counts_by_status.get(ApplicationStatus.SUBMITTED.value, 0)
        failed = counts_by_status.get(ApplicationStatus.FAILED.value, 0)
        skipped = sum(v for k, v in counts_by_status.items() if k in [ApplicationStatus.BLOCKED.value, ApplicationStatus.POLICY_PENDING.value, ApplicationStatus.DUPLICATE.value])
        unsupported = counts_by_status.get(ApplicationStatus.AUTO_APPLY_UNSUPPORTED.value, 0)

        return AutoApplyStatusRead(
            auto_apply_enabled=policy.auto_apply_enabled,
            minimum_match_score=policy.minimum_match_score,
            daily_application_limit=policy.daily_application_limit,
            applications_submitted_today=today_count,
            remaining_daily_quota=max(0, policy.daily_application_limit - today_count),
            queued_applications_count=queue_count,
            successful_applications_count=successful,
            failed_applications_count=failed,
            skipped_applications_count=skipped,
            unsupported_sources_count=unsupported
        )

    # ==================== APPLICATION LIFECYCLE & AUTO-APPLY ====================

    async def auto_evaluate_and_apply_job(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        immediate_process: bool = False
    ) -> Application:
        """Evaluates a job for auto-apply, creates application record, enqueues if eligible, and executes if requested."""
        # 1. Load Job
        stmt_job = select(Job).options(selectinload(Job.job_source)).where(Job.id == job_id)
        res_job = await self.db.execute(stmt_job)
        job = res_job.scalar_one_or_none()
        if not job:
            raise EntityNotFoundError("Job", job_id)

        # 2. Check Duplicates
        is_dup, existing_id, dup_reason = await DuplicateDetector.check_duplicate(user_id, job, self.db)
        if is_dup:
            # Check existing record
            existing_app = await self.get_application_by_id(existing_id)
            if existing_app:
                return existing_app
            raise DuplicateEntityError(dup_reason or "Duplicate application detected.")

        # 3. Load Match & Policy
        stmt_match = select(JobMatch).where(and_(JobMatch.user_id == user_id, JobMatch.job_id == job_id))
        match = (await self.db.execute(stmt_match)).scalar_one_or_none()
        policy = await self.get_or_create_policy(user_id)

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt_daily = select(func.count(Application.id)).where(
            and_(
                Application.user_id == user_id,
                Application.status.in_([ApplicationStatus.APPLIED.value, ApplicationStatus.SUBMITTED.value]),
                Application.applied_date >= today_start
            )
        )
        daily_count = (await self.db.execute(stmt_daily)).scalar_one()

        # 4. Policy Decision
        is_approved, decision, policy_reason = ApplicationPolicyEngine.evaluate(
            policy=policy,
            job=job,
            match=match,
            daily_applications_count=daily_count,
            source_daily_applications_count=0
        )

        source_slug = job.job_source.slug if job.job_source else (job.source if hasattr(job, 'source') else "direct")

        # 5. Create Application in initial state
        initial_status = ApplicationStatus.QUEUED.value if is_approved else (
            ApplicationStatus.BLOCKED.value if decision.value == "SKIP_INELIGIBLE" else ApplicationStatus.POLICY_PENDING.value
        )

        app = Application(
            id=uuid.uuid4(),
            user_id=user_id,
            job_id=job.id,
            source=source_slug,
            external_job_id=job.external_id,
            status=initial_status,
            match_score=match.overall_score if match else None,
            eligibility_status=match.eligibility_status if match else None,
            policy_decision=decision.value if hasattr(decision, 'value') else str(decision),
            submission_method=SubmissionMethod.DIRECT_API.value,
            failure_reason=None if is_approved else policy_reason
        )
        self.db.add(app)
        await self.db.flush()

        await ApplicationEventManager.log_event(
            self.db, app.id, ApplicationEventType.APPLICATION_CREATED,
            title="Application Created via Auto-Apply Evaluation",
            new_status=app.status,
            description=policy_reason
        )
        await self.db.commit()

        # 6. Enqueue if approved
        if is_approved:
            queue_service = ApplicationQueueService(self.db)
            queue_item = await queue_service.enqueue(user_id, app.id, job.id, priority=10)
            await self.db.commit()

            if immediate_process:
                agent = ApplicationAgent(self.db)
                await agent.process_queue_item(queue_item)

        return await self.get_application_by_id(app.id)

    async def create_application(self, user_id: uuid.UUID, payload: ApplicationCreate) -> Application:
        """Manual tracked application creation."""
        stmt_dup = select(Application).where(and_(Application.user_id == user_id, Application.job_id == payload.job_id))
        if (await self.db.execute(stmt_dup)).scalar_one_or_none():
            raise DuplicateEntityError("You have already applied or created a tracked application for this job.")

        stmt_job = select(Job).options(selectinload(Job.job_source)).where(Job.id == payload.job_id)
        job = (await self.db.execute(stmt_job)).scalar_one_or_none()
        if not job:
            raise EntityNotFoundError("Job", payload.job_id)

        if payload.submission_method == SubmissionMethod.DIRECT_API.value:
            if not job.job_source or job.job_source.capability_status != ConnectorCapabilityStatus.SUPPORTED_AUTO_APPLY.value:
                raise UnauthorizedIntegrationError(
                    f"Automated API application is not authorized for source '{job.job_source.name if job.job_source else 'Unknown'}'. "
                    "Status is EXTERNAL_APPLICATION_REQUIRED. Direct web scraping/anti-bot circumvention is strictly prohibited."
                )

        source_slug = job.job_source.slug if job.job_source else (job.source if hasattr(job, 'source') else "direct")

        app = Application(
            id=uuid.uuid4(),
            user_id=user_id,
            job_id=payload.job_id,
            resume_id=payload.resume_id,
            source=source_slug,
            external_job_id=job.external_id,
            status=ApplicationStatus.SUBMITTED.value if payload.submission_method != SubmissionMethod.MANUAL.value else ApplicationStatus.DRAFT.value,
            applied_date=datetime.now(timezone.utc) if payload.submission_method != SubmissionMethod.MANUAL.value else None,
            submission_method=payload.submission_method,
            notes=payload.notes
        )
        self.db.add(app)
        await self.db.flush()

        await ApplicationEventManager.log_event(
            self.db, app.id, ApplicationEventType.CREATED,
            title="Manual Application Tracked",
            new_status=app.status,
            description=f"Tracked via {payload.submission_method}."
        )
        await self.db.commit()
        return await self.get_application_by_id(app.id)

    async def update_status(self, application_id: uuid.UUID, user_id: uuid.UUID, payload: ApplicationUpdateStatus) -> Application:
        stmt = (
            select(Application)
            .options(selectinload(Application.events))
            .where(and_(Application.id == application_id, Application.user_id == user_id))
        )
        res = await self.db.execute(stmt)
        app = res.scalar_one_or_none()
        if not app:
            raise EntityNotFoundError("Application", application_id)

        # Validate state transition
        ApplicationStateMachine.validate_transition(app.status, payload.status)

        old_status = app.status
        app.status = payload.status
        if payload.status in [ApplicationStatus.SUBMITTED.value, ApplicationStatus.APPLIED.value] and not app.applied_date:
            app.applied_date = datetime.now(timezone.utc)
        if payload.notes:
            app.notes = f"{app.notes or ''}\n{payload.notes}".strip()

        await ApplicationEventManager.log_event(
            self.db, app.id, ApplicationEventType.STATUS_CHANGED,
            title=f"Status changed to {payload.status.replace('_', ' ').title()}",
            old_status=old_status,
            new_status=payload.status,
            description=payload.notes or f"Application status updated to {payload.status}."
        )
        await self.db.commit()
        return await self.get_application_by_id(app.id)

    async def list_applications(self, user_id: uuid.UUID, status: Optional[str] = None) -> List[Application]:
        stmt = (
            select(Application)
            .options(
                selectinload(Application.job).selectinload(Job.job_source),
                selectinload(Application.events),
                selectinload(Application.attempts),
            )
            .where(Application.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        if status:
            stmt = stmt.where(Application.status == status)

        stmt = stmt.order_by(Application.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_application_by_id(self, application_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> Optional[Application]:
        stmt = (
            select(Application)
            .options(
                selectinload(Application.job).selectinload(Job.job_source),
                selectinload(Application.events),
                selectinload(Application.attempts),
            )
            .where(Application.id == application_id)
            .execution_options(populate_existing=True)
        )
        if user_id:
            stmt = stmt.where(Application.user_id == user_id)

        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_statistics(self, user_id: uuid.UUID) -> ApplicationStatisticsRead:
        stmt = select(Application.status, func.count(Application.id)).where(Application.user_id == user_id).group_by(Application.status)
        rows = (await self.db.execute(stmt)).all()
        by_status = {row[0]: row[1] for row in rows}

        stmt_queue = select(func.count(ApplicationQueueItem.id)).where(
            and_(
                ApplicationQueueItem.user_id == user_id,
                ApplicationQueueItem.status == QueueStatus.QUEUED.value
            )
        )
        queued_count = (await self.db.execute(stmt_queue)).scalar_one()

        total = sum(by_status.values())
        applied = by_status.get(ApplicationStatus.APPLIED.value, 0) + by_status.get(ApplicationStatus.SUBMITTED.value, 0)
        failed = by_status.get(ApplicationStatus.FAILED.value, 0)
        in_progress = by_status.get(ApplicationStatus.PREPARING.value, 0) + by_status.get(ApplicationStatus.VALIDATING.value, 0) + by_status.get(ApplicationStatus.SUBMITTING.value, 0)
        interviews = by_status.get(ApplicationStatus.INTERVIEW_SCHEDULED.value, 0)
        offers = by_status.get(ApplicationStatus.OFFER_RECEIVED.value, 0)
        rejected = by_status.get(ApplicationStatus.REJECTED.value, 0)
        skipped = by_status.get(ApplicationStatus.POLICY_PENDING.value, 0) + by_status.get(ApplicationStatus.BLOCKED.value, 0) + by_status.get(ApplicationStatus.DUPLICATE.value, 0)
        unsupported = by_status.get(ApplicationStatus.AUTO_APPLY_UNSUPPORTED.value, 0)
        missing_info = by_status.get(ApplicationStatus.MISSING_INFORMATION.value, 0)

        return ApplicationStatisticsRead(
            total_applications=total,
            applied=applied,
            queued=queued_count,
            in_progress=in_progress,
            failed=failed,
            interviews=interviews,
            offers=offers,
            rejected=rejected,
            skipped_policy=skipped,
            unsupported_platform=unsupported,
            missing_information=missing_info
        )

    # ==================== QUEUE PROCESSING ====================

    async def get_user_queue_items(self, user_id: uuid.UUID) -> List[ApplicationQueueItem]:
        queue_service = ApplicationQueueService(self.db)
        return await queue_service.get_user_queue(user_id)

    async def process_queue(self, limit: int = 10) -> ProcessQueueResponse:
        queue_service = ApplicationQueueService(self.db)
        due_items = await queue_service.get_due_items(limit=limit)

        processed = 0
        successful = 0
        failed = 0
        retried = 0
        skipped = 0
        details = []

        agent = ApplicationAgent(self.db)
        for item in due_items:
            processed += 1
            await queue_service.mark_processing(item)
            res = await agent.process_queue_item(item)

            status = res.get("status")
            if res.get("success"):
                successful += 1
            elif res.get("should_retry"):
                retried += 1
            elif status in [ApplicationStatus.POLICY_PENDING.value, ApplicationStatus.BLOCKED.value]:
                skipped += 1
            else:
                failed += 1

            details.append({
                "queue_item_id": str(item.id),
                "application_id": str(item.application_id),
                "result": res
            })

        return ProcessQueueResponse(
            processed_count=processed,
            successful_count=successful,
            failed_count=failed,
            retried_count=retried,
            skipped_count=skipped,
            details=details
        )
