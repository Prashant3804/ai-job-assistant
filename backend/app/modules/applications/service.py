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
    ProcessQueueResponse,
    PlatformStatItem,
    PlatformsDashboardResponse,
    TodayAuditResponse
)
from app.modules.applications.policy import ApplicationPolicyEngine
from app.modules.applications.duplicate import DuplicateDetector
from app.modules.applications.capabilities import PlatformCapabilityManager
from app.modules.applications.queue import ApplicationQueueService
from app.modules.applications.agent import ApplicationAgent
from app.modules.applications.events import ApplicationEventManager
import logging
from app.modules.applications.audit import ApplicationAuditLogger
from app.modules.applications.state_machine import ApplicationStateMachine
from app.modules.applications.window_service import (
    is_application_window_open,
    get_application_window_status,
    get_next_application_window
)
from app.modules.applications.date_utils import (
    get_current_business_day_range,
    ensure_utc,
    to_ist,
    format_ist,
    KOLKATA_TZ
)

logger = logging.getLogger("app.applications.service")

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
                minimum_match_score=65.0,
                daily_application_limit=None,
                per_source_daily_limit=None,
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

        is_limited = policy.daily_application_limit is not None
        remaining = max(0, policy.daily_application_limit - today_count) if is_limited else None
        limit_label = f"{policy.daily_application_limit}/day" if is_limited else "Unlimited"

        return AutoApplyStatusRead(
            auto_apply_enabled=policy.auto_apply_enabled,
            minimum_match_score=policy.minimum_match_score,
            daily_application_limit=policy.daily_application_limit,
            daily_limit_enabled=is_limited,
            daily_limit_label=limit_label,
            applications_submitted_today=today_count,
            remaining_daily_quota=remaining,
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
        immediate_process: bool = False,
        enforce_window: bool = False
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

        start_of_today_utc, end_of_today_utc = get_current_business_day_range()
        ts_col = func.coalesce(Application.applied_date, Application.created_at)
        stmt_daily = select(func.count(Application.id)).where(
            and_(
                Application.user_id == user_id,
                Application.status.in_([ApplicationStatus.APPLIED.value, ApplicationStatus.SUBMITTED.value]),
                ts_col >= start_of_today_utc,
                ts_col <= end_of_today_utc
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

        # Check Application Execution Window (10:00 AM - 11:59 AM IST)
        window_open = True if (immediate_process or not enforce_window) else is_application_window_open()

        # 5. Create Application in initial state
        if is_approved:
            initial_status = ApplicationStatus.QUEUED.value if window_open else ApplicationStatus.QUEUED_FOR_NEXT_WINDOW.value
        else:
            initial_status = (
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

        event_title = "Application Created via Auto-Apply Evaluation" if window_open else "Application Prepared & Queued For Next Window"
        event_desc = policy_reason if window_open else "Prepared outside 10:00 AM - 11:59 AM IST window. Staged for dispatch during next window."
        await ApplicationEventManager.log_event(
            self.db, app.id, ApplicationEventType.APPLICATION_CREATED,
            title=event_title,
            new_status=app.status,
            description=event_desc
        )
        await self.db.commit()

        # 6. Enqueue if approved
        if is_approved:
            queue_service = ApplicationQueueService(self.db)
            if not window_open:
                queue_item = ApplicationQueueItem(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    application_id=app.id,
                    job_id=job.id,
                    priority=10,
                    status=QueueStatus.QUEUED_FOR_NEXT_WINDOW.value
                )
                self.db.add(queue_item)
                await self.db.commit()
            else:
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

    async def list_applications(
        self,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        source: Optional[str] = None,
        time_range: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Application]:
        from datetime import timedelta
        now_utc = datetime.now(timezone.utc)
        start_of_today_utc, end_of_today_utc = get_current_business_day_range(now_utc)

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

        if source:
            source_lower = source.lower()
            if source_lower in ["career_pages", "company_careers", "ats"]:
                stmt = stmt.where(Application.source.in_(["career_pages", "greenhouse", "lever", "authorized_api", "direct"]))
            else:
                stmt = stmt.where(Application.source == source_lower)

        if time_range:
            tr = time_range.lower()
            ts_col = func.coalesce(Application.applied_date, Application.created_at)
            if tr == "today":
                stmt = stmt.where(and_(ts_col >= start_of_today_utc, ts_col <= end_of_today_utc))
            elif tr == "yesterday":
                start_yesterday_utc, end_yesterday_utc = get_current_business_day_range(now_utc - timedelta(days=1))
                stmt = stmt.where(and_(ts_col >= start_yesterday_utc, ts_col <= end_yesterday_utc))
            elif tr in ["7d", "last_7_days"]:
                seven_d_utc = now_utc - timedelta(days=7)
                stmt = stmt.where(ts_col >= seven_d_utc)
            elif tr in ["30d", "last_30_days"]:
                thirty_d_utc = now_utc - timedelta(days=30)
                stmt = stmt.where(ts_col >= thirty_d_utc)

        stmt = stmt.order_by(Application.created_at.desc()).limit(limit).offset(offset)
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
        if not is_application_window_open():
            logger.info("Application execution window closed (outside 10:00 AM - 11:59 AM IST). Skipping automated queue submission.")
            return ProcessQueueResponse(
                processed_count=0,
                successful_count=0,
                failed_count=0,
                retried_count=0,
                skipped_count=0,
                details=[]
            )

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

    async def get_platform_statistics(self, user_id: uuid.UUID) -> PlatformsDashboardResponse:
        from app.database.models.application import AutoApplyDailyRun
        from app.modules.jobs.connectors.adapters import get_connector_by_slug

        start_of_today_utc, end_of_today_utc = get_current_business_day_range()
        now_utc = datetime.now(timezone.utc)
        now_kolkata = now_utc.astimezone(KOLKATA_TZ)
        date_str = now_kolkata.strftime("%Y-%m-%d")

        policy = await self.get_or_create_policy(user_id)
        is_routine_active = bool(policy and policy.auto_apply_enabled)

        PLATFORM_CONFIG = [
            {"slug": "naukri", "name": "Naukri", "auto_type": "EXTERNAL_PORTAL"},
            {"slug": "indeed", "name": "Indeed", "auto_type": "EXTERNAL_PORTAL"},
            {"slug": "unstop", "name": "Unstop", "auto_type": "DISCOVERY_FEED"},
            {"slug": "linkedin", "name": "LinkedIn Jobs", "auto_type": "EXTERNAL_PORTAL"},
            {"slug": "internshala", "name": "Internshala", "auto_type": "DISCOVERY_FEED"},
            {"slug": "wellfound", "name": "Wellfound", "auto_type": "DISCOVERY_FEED"},
            {"slug": "career_pages", "name": "Company Careers", "auto_type": "DIRECT_ATS_API"},
        ]

        # 1. Query all user applications
        apps_stmt = (
            select(Application)
            .options(selectinload(Application.job))
            .where(Application.user_id == user_id)
        )
        apps_res = await self.db.execute(apps_stmt)
        all_user_apps = list(apps_res.scalars().all())

        # 2. Query active jobs count grouped by source slug
        jobs_stmt = (
            select(JobSource.slug, func.count(Job.id))
            .join(Job, Job.job_source_id == JobSource.id)
            .where(Job.is_active == True)
            .group_by(JobSource.slug)
        )
        job_counts_res = (await self.db.execute(jobs_stmt)).all()
        job_counts_by_source = {row[0]: row[1] for row in job_counts_res}

        # 3. Query matches count grouped by source slug for this user
        matches_stmt = (
            select(JobSource.slug, func.count(JobMatch.id))
            .join(Job, JobMatch.job_id == Job.id)
            .join(JobSource, Job.job_source_id == JobSource.id)
            .where(and_(JobMatch.user_id == user_id, JobMatch.overall_score >= policy.minimum_match_score))
            .group_by(JobSource.slug)
        )
        match_counts_res = (await self.db.execute(matches_stmt)).all()
        match_counts_by_source = {row[0]: row[1] for row in match_counts_res}

        # 4. Last completed daily run for fallback timestamps
        last_run_stmt = (
            select(AutoApplyDailyRun)
            .where(AutoApplyDailyRun.user_id == user_id)
            .order_by(AutoApplyDailyRun.started_at.desc())
            .limit(1)
        )
        last_run = (await self.db.execute(last_run_stmt)).scalar_one_or_none()

        platforms_map: Dict[str, PlatformStatItem] = {}
        total_applied_today = 0
        total_manual_today = 0
        total_failed_today = 0
        total_matching_jobs = 0

        for cfg in PLATFORM_CONFIG:
            slug = cfg["slug"]
            name = cfg["name"]
            auto_type = cfg["auto_type"]

            if slug == "career_pages":
                target_slugs = ["career_pages", "greenhouse", "lever", "authorized_api"]
            else:
                target_slugs = [slug]

            # Jobs discovered
            jobs_discovered = sum(job_counts_by_source.get(s, 0) for s in target_slugs)

            # Matching jobs
            plat_matching_jobs = sum(match_counts_by_source.get(s, 0) for s in target_slugs)
            total_matching_jobs += plat_matching_jobs

            # User applications for this platform
            plat_apps = [
                a for a in all_user_apps
                if (a.source in target_slugs or (slug == "career_pages" and a.source in ["career_pages", "greenhouse", "lever", "authorized_api", "direct"]))
            ]

            # Applied all time & today (Honest: ONLY APPLIED or SUBMITTED)
            applied_all = [
                a for a in plat_apps
                if a.status in [ApplicationStatus.APPLIED.value, ApplicationStatus.SUBMITTED.value]
            ]
            applied_today = [
                a for a in applied_all
                if ensure_utc(a.applied_date or a.submitted_at or a.created_at)
                and start_of_today_utc <= ensure_utc(a.applied_date or a.submitted_at or a.created_at) <= end_of_today_utc
            ]

            # Manual required all time & today
            manual_all = [
                a for a in plat_apps
                if a.status == ApplicationStatus.EXTERNAL_APPLICATION_REQUIRED.value
            ]
            manual_today = [
                a for a in manual_all
                if ensure_utc(a.created_at or a.applied_date)
                and start_of_today_utc <= ensure_utc(a.created_at or a.applied_date) <= end_of_today_utc
            ]

            # Failed all time & today
            failed_all = [
                a for a in plat_apps
                if a.status == ApplicationStatus.FAILED.value
            ]
            failed_today = [
                a for a in failed_all
                if ensure_utc(a.created_at or a.applied_date)
                and start_of_today_utc <= ensure_utc(a.created_at or a.applied_date) <= end_of_today_utc
            ]

            # Queued for next window
            queued_all = [
                a for a in plat_apps
                if a.status == ApplicationStatus.QUEUED_FOR_NEXT_WINDOW.value
            ]

            daily_limit = 30
            applied_count_today = len(applied_today)
            current_daily_count = applied_count_today
            progress_pct = min(100.0, round((current_daily_count / daily_limit) * 100.0, 1))

            total_applied_today += applied_count_today
            total_manual_today += len(manual_today)
            total_failed_today += len(failed_today)

            # Determine last activity time
            all_plat_timestamps = []
            for a in plat_apps:
                ts = ensure_utc(a.applied_date or a.submitted_at or a.created_at)
                if ts:
                    all_plat_timestamps.append(ts)

            last_activity_utc = max(all_plat_timestamps) if all_plat_timestamps else None
            if not last_activity_utc and last_run and last_run.completed_at:
                if last_run.run_summary_json and "source_counts" in last_run.run_summary_json:
                    if last_run.run_summary_json["source_counts"].get(slug, 0) > 0:
                        last_activity_utc = ensure_utc(last_run.completed_at)

            last_activity_ist = format_ist(last_activity_utc)

            # Determine live status
            connector = get_connector_by_slug(slug)
            if not connector and slug == "career_pages":
                connector = get_connector_by_slug("greenhouse") or get_connector_by_slug("career_pages")

            if not connector:
                status_str = "NO CONNECTOR"
            elif not is_routine_active:
                status_str = "PAUSED"
            else:
                try:
                    conn_status = connector.get_source_status()
                    if conn_status.get("status") != "HEALTHY":
                        status_str = "ERROR"
                    elif conn_status.get("rate_limit_remaining", 100) <= 0:
                        status_str = "RATE LIMITED"
                    elif slug == "career_pages":
                        status_str = "AUTOMATION AVAILABLE"
                    else:
                        status_str = "ACTIVE"
                except Exception:
                    status_str = "ERROR"

            platforms_map[slug] = PlatformStatItem(
                name=name,
                slug=slug,
                jobs_discovered=jobs_discovered,
                matching_jobs=plat_matching_jobs,
                applied=len(applied_all),
                manual_required=len(manual_all),
                failed=len(failed_all),
                daily_limit=daily_limit,
                applied_today=applied_count_today,
                manual_today=len(manual_today),
                failed_today=len(failed_today),
                queued_today=len(queued_all),
                current_daily_count=current_daily_count,
                progress_pct=progress_pct,
                last_activity_utc=last_activity_utc,
                last_activity_ist=last_activity_ist,
                status=status_str,
                automation_type=auto_type
            )

        # Count total queued for next window across all platforms for this user
        total_queued_for_next_window = sum(
            1 for a in all_user_apps
            if a.status == ApplicationStatus.QUEUED_FOR_NEXT_WINDOW.value
        )

        window_status_dict = get_application_window_status()

        return PlatformsDashboardResponse(
            date=date_str,
            schedule_time="10:00 AM IST",
            total_applied_today=total_applied_today,
            total_daily_limit=210,
            total_manual_required_today=total_manual_today,
            total_failed_today=total_failed_today,
            total_queued_for_next_window=total_queued_for_next_window,
            total_matching_jobs=total_matching_jobs,
            application_window=window_status_dict,
            platforms=platforms_map
        )

    async def get_today_audit(self, user_id: uuid.UUID) -> TodayAuditResponse:
        """Returns deep candidate-isolated forensic verification metrics for the current calendar day in IST."""
        start_utc, end_utc = get_current_business_day_range()
        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc.astimezone(KOLKATA_TZ)

        stats = await self.get_platform_statistics(user_id)
        window_status = get_application_window_status()

        # Fetch applications processed today
        apps_today = await self.list_applications(user_id=user_id, time_range="today", limit=50)
        recent_activity_today = [
            {
                "id": str(a.id),
                "job_title": a.job.title if a.job else "Job Application",
                "company_name": a.job.company_name if a.job else "Company",
                "source": a.source,
                "status": a.status,
                "match_score": a.match_score,
                "applied_at": a.applied_date.isoformat() if a.applied_date else (a.created_at.isoformat() if a.created_at else None),
                "applied_at_ist": format_ist(a.applied_date or a.created_at),
                "submission_method": a.submission_method
            }
            for a in apps_today
        ]

        metrics_today = {
            "applications_submitted": stats.total_applied_today,
            "queued_for_next_window": stats.total_queued_for_next_window,
            "jobs_matched_qualifying": stats.total_matching_jobs,
            "manual_required": stats.total_manual_required_today,
            "failed": stats.total_failed_today
        }

        platforms_summary = {
            slug: {
                "name": p.name,
                "discovered": p.jobs_discovered,
                "matching": p.matching_jobs,
                "submitted_today": p.applied_today,
                "manual_today": p.manual_today,
                "failed_today": p.failed_today,
                "queued_today": p.queued_today,
                "status": p.status
            }
            for slug, p in stats.platforms.items()
        }

        return TodayAuditResponse(
            user_id=str(user_id),
            date_ist=now_ist.strftime("%Y-%m-%d"),
            start_of_today_utc=start_utc,
            end_of_today_utc=end_utc,
            current_time_ist=now_ist.strftime("%b %d, %Y • %I:%M:%S %p IST"),
            application_window=window_status,
            metrics_today=metrics_today,
            platforms=platforms_summary,
            recent_activity_today=recent_activity_today
        )
