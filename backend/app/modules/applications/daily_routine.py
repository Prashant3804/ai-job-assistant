"""Auto-Apply Daily Routine Service.

Runs the automated application routine at 10:00 AM IST (Asia/Kolkata).
Steps:
1. Load user's primary resume & candidate profile.
2. Search/sync available job sources.
3. Match jobs against skills, languages, experience, education, roles, and location.
4. Filter matching jobs exceeding candidate threshold (minimum_match_score).
5. Exclude duplicates, already applied, closed, and ineligible jobs.
6. Submit applications for all eligible matching jobs via authorized APIs.
7. Mark jobs that require external/manual portal submission as 'EXTERNAL_APPLICATION_REQUIRED' (never fabricate applied).
8. Record real timestamps (UTC internally, displayed in Asia/Kolkata) in AutoApplyDailyRun.
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from zoneinfo import ZoneInfo
from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.user import User, UserProfile, JobPreference
from app.database.models.job import Job, JobSource
from app.database.models.resume import Resume
from app.database.models.match import JobMatch
from app.database.models.application import (
    Application,
    ApplicationPolicy,
    ApplicationQueueItem,
    AutoApplyDailyRun
)
from app.shared.constants import (
    ApplicationStatus,
    ApplicationEventType,
    SubmissionMethod,
    QueueStatus,
    PolicyDecision,
    ConnectorCapabilityStatus
)
from app.modules.applications.policy import ApplicationPolicyEngine
from app.modules.applications.duplicate import DuplicateDetector
from app.modules.applications.agent import ApplicationAgent
from app.modules.applications.events import ApplicationEventManager
from app.modules.applications.schemas import AutoApplyDailyRunRead, AutoApplyDailyRoutineInfo
from app.modules.jobs.service import JobService
from app.modules.matching.service import MatchingService

logger = logging.getLogger("app.auto_apply.daily_routine")

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")


class AutoApplyDailyRoutineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def calculate_next_scheduled_run(
        now_utc: Optional[datetime] = None,
        target_hour: int = 10,
        target_minute: int = 0
    ) -> Tuple[datetime, str]:
        """Calculates the next occurrence of target_hour:target_minute in Asia/Kolkata (IST)."""
        if not now_utc:
            now_utc = datetime.now(timezone.utc)

        now_kolkata = now_utc.astimezone(KOLKATA_TZ)
        target_today = now_kolkata.replace(
            hour=target_hour, minute=target_minute, second=0, microsecond=0
        )

        if now_kolkata < target_today:
            next_kolkata = target_today
        else:
            next_kolkata = target_today + timedelta(days=1)

        next_utc = next_kolkata.astimezone(timezone.utc)
        # Format display in IST e.g. "Sep 7, 2026 • 10:00 AM IST"
        display_str = next_kolkata.strftime("%b %d, %Y • %I:%M %p IST")
        return next_utc, display_str

    async def get_routine_info(self, user_id: uuid.UUID) -> AutoApplyDailyRoutineInfo:
        """Returns the complete routine status, schedule, next run, and last run summary for a user."""
        # 1. Load user policy
        stmt_pol = select(ApplicationPolicy).where(ApplicationPolicy.user_id == user_id)
        pol_res = await self.db.execute(stmt_pol)
        policy = pol_res.scalar_one_or_none()
        is_enabled = bool(policy and policy.auto_apply_enabled)

        # 2. Next scheduled run
        next_run_utc, next_run_display = self.calculate_next_scheduled_run()

        # 3. Last completed/attempted run
        stmt_last = (
            select(AutoApplyDailyRun)
            .where(AutoApplyDailyRun.user_id == user_id)
            .order_by(AutoApplyDailyRun.started_at.desc())
            .limit(1)
        )
        last_res = await self.db.execute(stmt_last)
        last_run = last_res.scalar_one_or_none()

        # 4. Total count of runs
        count_stmt = select(func.count(AutoApplyDailyRun.id)).where(AutoApplyDailyRun.user_id == user_id)
        total_runs = (await self.db.execute(count_stmt)).scalar_one()

        last_run_read = AutoApplyDailyRunRead.model_validate(last_run, from_attributes=True) if last_run else None

        return AutoApplyDailyRoutineInfo(
            schedule_time_display="10:00 AM IST",
            schedule_timezone="Asia/Kolkata",
            auto_apply_enabled=is_enabled,
            status="Active" if is_enabled else "Disabled",
            next_run_at=next_run_utc,
            next_run_display=next_run_display,
            last_run=last_run_read,
            total_runs_count=total_runs
        )

    async def get_history(self, user_id: uuid.UUID, limit: int = 20) -> List[AutoApplyDailyRunRead]:
        """Retrieves past daily run records for the user."""
        stmt = (
            select(AutoApplyDailyRun)
            .where(AutoApplyDailyRun.user_id == user_id)
            .order_by(AutoApplyDailyRun.started_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        runs = res.scalars().all()
        return [AutoApplyDailyRunRead.model_validate(r, from_attributes=True) for r in runs]

    async def execute_daily_routine_for_user(
        self,
        user_id: uuid.UUID,
        scheduled_time: Optional[datetime] = None
    ) -> AutoApplyDailyRun:
        """Executes the complete 8-step Auto-Apply routine for a single user."""
        start_time = datetime.now(timezone.utc)
        if not scheduled_time:
            scheduled_time = start_time

        # Create Run record in RUNNING state
        run_record = AutoApplyDailyRun(
            id=uuid.uuid4(),
            user_id=user_id,
            scheduled_for=scheduled_time,
            started_at=start_time,
            status="RUNNING"
        )
        self.db.add(run_record)
        await self.db.commit()

        try:
            # STEP 1: Load User, Profile, Resume, and Policy
            user_stmt = select(User).options(
                selectinload(User.profile),
                selectinload(User.job_preferences),
                selectinload(User.resumes)
            ).where(User.id == user_id)
            user_res = await self.db.execute(user_stmt)
            user = user_res.scalar_one_or_none()

            if not user or not user.profile:
                run_record.status = "FAILED"
                run_record.error_message = "Candidate profile is missing or incomplete."
                run_record.completed_at = datetime.now(timezone.utc)
                await self.db.commit()
                return run_record

            pol_stmt = select(ApplicationPolicy).where(ApplicationPolicy.user_id == user_id)
            pol_res = await self.db.execute(pol_stmt)
            policy = pol_res.scalar_one_or_none()

            if not policy:
                policy = ApplicationPolicy(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    auto_apply_enabled=False,
                    minimum_match_score=85.0
                )
                self.db.add(policy)
                await self.db.flush()

            if not policy.auto_apply_enabled:
                run_record.status = "SKIPPED"
                run_record.error_message = "Auto-apply is disabled in candidate settings."
                run_record.completed_at = datetime.now(timezone.utc)
                await self.db.commit()
                return run_record

            # STEP 2: Search available authorized job sources and ingest latest
            job_service = JobService(self.db)
            try:
                sync_res = await job_service.sync_all_discovery_sources()
                logger.info(f"Daily routine job discovery sync: {sync_res}")
            except Exception as e:
                logger.warning(f"Job discovery sync non-fatal warning during daily routine: {e}")

            # Query active non-expired jobs
            stmt_jobs = select(Job).options(selectinload(Job.job_source)).where(Job.is_active == True) # noqa: E712
            jobs_res = await self.db.execute(stmt_jobs)
            active_jobs = list(jobs_res.scalars().all())
            run_record.jobs_found = len(active_jobs)

            # STEP 3 & 4: Evaluate match for each job against resume/profile
            matching_service = MatchingService(self.db)
            agent = ApplicationAgent(self.db)

            matching_jobs = 0
            applied_count = 0
            already_applied_count = 0
            manual_required_count = 0
            failed_count = 0
            skipped_count = 0
            application_summaries = []

            for job in active_jobs:
                # Compute or retrieve match score
                stmt_match = select(JobMatch).where(and_(JobMatch.user_id == user_id, JobMatch.job_id == job.id))
                match = (await self.db.execute(stmt_match)).scalar_one_or_none()

                if not match:
                    try:
                        match = await matching_service.compute_or_update_match(user, job)
                    except Exception as me:
                        logger.warning(f"Could not compute match for job {job.id}: {me}")
                        match = None

                score = match.overall_score if match else 0.0

                # STEP 5: Matching threshold check
                if score < policy.minimum_match_score:
                    skipped_count += 1
                    continue

                matching_jobs += 1

                # STEP 6: Pre-filter duplicate or already processed applications
                is_dup, existing_app_id, _ = await DuplicateDetector.check_duplicate(user_id, job, self.db)
                if is_dup:
                    already_applied_count += 1
                    continue

                # Evaluate complete policy (blocked keywords, blocked companies, remote rules)
                is_approved, decision, reason = ApplicationPolicyEngine.evaluate(
                    policy=policy,
                    job=job,
                    match=match,
                    daily_applications_count=applied_count,
                    source_daily_applications_count=0
                )

                if not is_approved:
                    skipped_count += 1
                    continue

                # STEP 7: Check integration submission capability
                # Non-circumvention rule: If platform requires manual portal / CAPTCHA, mark EXTERNAL_APPLICATION_REQUIRED
                is_direct_auto = (
                    job.job_source
                    and job.job_source.capability_status == ConnectorCapabilityStatus.SUPPORTED_AUTO_APPLY.value
                )

                source_slug = job.job_source.slug if job.job_source else (getattr(job, 'source', None) or "direct")

                if not is_direct_auto:
                    # Platform requires manual candidate submission
                    manual_required_count += 1
                    manual_app = Application(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        job_id=job.id,
                        source=source_slug,
                        external_job_id=job.external_id,
                        status=ApplicationStatus.EXTERNAL_APPLICATION_REQUIRED.value,
                        match_score=score,
                        eligibility_status=match.eligibility_status if match else "ELIGIBLE",
                        policy_decision=decision.value,
                        submission_method=SubmissionMethod.EXTERNAL_PORTAL.value,
                        failure_reason="Platform requires manual submission via employer careers portal."
                    )
                    self.db.add(manual_app)
                    await self.db.flush()

                    await ApplicationEventManager.log_event(
                        self.db, manual_app.id, ApplicationEventType.APPLICATION_CREATED,
                        title="Manual Application Required",
                        new_status=manual_app.status,
                        description="Direct automated API submission is unavailable for this employer portal. Manual candidate action required."
                    )
                    application_summaries.append({
                        "company": job.company_name,
                        "title": job.title,
                        "status": "MANUAL_REQUIRED",
                        "match_score": score
                    })
                    continue

                # Authorized submission candidate
                app = Application(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    job_id=job.id,
                    source=source_slug,
                    external_job_id=job.external_id,
                    status=ApplicationStatus.QUEUED.value,
                    match_score=score,
                    eligibility_status=match.eligibility_status if match else "ELIGIBLE",
                    policy_decision=decision.value,
                    submission_method=SubmissionMethod.DIRECT_API.value,
                    failure_reason=None
                )
                self.db.add(app)
                await self.db.flush()

                # Enqueue and execute submission
                queue_item = ApplicationQueueItem(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    application_id=app.id,
                    job_id=job.id,
                    priority=10,
                    status=QueueStatus.QUEUED.value
                )
                self.db.add(queue_item)
                await self.db.commit()

                # Process submission through agent
                result = await agent.process_queue_item(queue_item)
                if result.get("success"):
                    applied_count += 1
                    application_summaries.append({
                        "company": job.company_name,
                        "title": job.title,
                        "status": "APPLIED",
                        "match_score": score
                    })
                elif result.get("status") == "AUTO_APPLY_UNSUPPORTED":
                    manual_required_count += 1
                    application_summaries.append({
                        "company": job.company_name,
                        "title": job.title,
                        "status": "MANUAL_REQUIRED",
                        "match_score": score
                    })
                else:
                    failed_count += 1
                    application_summaries.append({
                        "company": job.company_name,
                        "title": job.title,
                        "status": "FAILED",
                        "match_score": score,
                        "reason": result.get("reason")
                    })

            # STEP 8: Finalize Daily Run Record
            run_record.status = "COMPLETED"
            run_record.matching_jobs = matching_jobs
            run_record.applied_count = applied_count
            run_record.already_applied_count = already_applied_count
            run_record.manual_required_count = manual_required_count
            run_record.failed_count = failed_count
            run_record.skipped_count = skipped_count
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.run_summary_json = {
                "applications": application_summaries[:50],
                "duration_seconds": (run_record.completed_at - run_record.started_at).total_seconds()
            }
            await self.db.commit()
            return run_record

        except Exception as exc:
            logger.error(f"Error executing auto-apply daily routine for user {user_id}: {exc}", exc_info=True)
            run_record.status = "FAILED"
            run_record.error_message = str(exc)
            run_record.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return run_record

    async def execute_daily_routine_for_all_active_users(
        self,
        scheduled_time: Optional[datetime] = None
    ) -> List[AutoApplyDailyRun]:
        """Runs the 10:00 AM routine for all users who have auto-apply enabled."""
        stmt = (
            select(ApplicationPolicy.user_id)
            .where(ApplicationPolicy.auto_apply_enabled == True) # noqa: E712
        )
        res = await self.db.execute(stmt)
        user_ids = res.scalars().all()
        logger.info(f"Auto-Apply Daily Routine starting for {len(user_ids)} active candidate accounts.")

        results = []
        for uid in user_ids:
            run = await self.execute_daily_routine_for_user(uid, scheduled_time=scheduled_time)
            results.append(run)

        return results
