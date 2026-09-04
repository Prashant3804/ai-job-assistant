import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.application import (
    Application,
    ApplicationPolicy,
    ApplicationQueueItem,
    ApplicationAttempt,
    ApplicationAnswer,
    ApplicationEvent,
    ApplicationAuditLog,
    DeadLetterApplicationQueue
)
from app.database.models.job import Job
from app.database.models.user import User, UserProfile, Education, Experience, CandidateSkill, Project, JobPreference
from app.database.models.match import JobMatch
from app.shared.constants import ApplicationStatus, ApplicationEventType, SubmissionMethod, QueueStatus
from app.modules.applications.policy import ApplicationPolicyEngine
from app.modules.applications.capabilities import PlatformCapabilityManager
from app.modules.applications.resume_selector import ResumeSelectionService
from app.modules.applications.mapper import ApplicationDataMapper
from app.modules.applications.validator import ApplicationValidator
from app.modules.applications.connectors.adapters import get_application_connector
from app.modules.applications.retry import RetryManager
from app.modules.applications.events import ApplicationEventManager
from app.modules.applications.audit import ApplicationAuditLogger
from app.modules.applications.state_machine import ApplicationStateMachine
from app.modules.applications.worker_monitor import worker_monitor_service

logger = logging.getLogger(__name__)

class ApplicationAgent:
    """Autonomous agent that executes authorized auto-apply pipeline for queued candidate jobs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_queue_item(self, queue_item: ApplicationQueueItem) -> Dict[str, Any]:
        user_id = queue_item.user_id
        application_id = queue_item.application_id
        job_id = queue_item.job_id

        # 1. Load Application & Job with relations
        stmt_app = (
            select(Application)
            .options(
                selectinload(Application.job).selectinload(Job.job_source),
                selectinload(Application.user),
                selectinload(Application.events),
                selectinload(Application.attempts)
            )
            .where(Application.id == application_id)
        )
        res_app = await self.db.execute(stmt_app)
        app = res_app.scalar_one_or_none()
        if not app:
            queue_item.status = QueueStatus.FAILED.value
            queue_item.error_message = "Associated Application record not found."
            await self.db.commit()
            return {"success": False, "status": "FAILED", "reason": "APPLICATION_NOT_FOUND"}

        job = app.job

        # 2. Check User Policy
        stmt_policy = select(ApplicationPolicy).where(ApplicationPolicy.user_id == user_id)
        res_policy = await self.db.execute(stmt_policy)
        policy = res_policy.scalar_one_or_none()

        # Count daily applications
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt_daily = select(func.count(Application.id)).where(
            and_(
                Application.user_id == user_id,
                Application.status.in_([ApplicationStatus.APPLIED.value, ApplicationStatus.SUBMITTED.value]),
                Application.applied_date >= today_start
            )
        )
        daily_count = (await self.db.execute(stmt_daily)).scalar_one()

        # Load match score if exists
        stmt_match = select(JobMatch).where(and_(JobMatch.user_id == user_id, JobMatch.job_id == job_id))
        res_match = await self.db.execute(stmt_match)
        match = res_match.scalar_one_or_none()

        is_approved, decision, policy_reason = ApplicationPolicyEngine.evaluate(
            policy=policy,
            job=job,
            match=match,
            daily_applications_count=daily_count,
            source_daily_applications_count=0
        )

        app.policy_decision = decision.value if hasattr(decision, 'value') else str(decision)
        if match:
            app.match_score = match.overall_score
            app.eligibility_status = match.eligibility_status

        if not is_approved:
            # Policy skipped
            app.status = ApplicationStatus.BLOCKED.value if decision.value == "SKIP_INELIGIBLE" else ApplicationStatus.POLICY_PENDING.value
            app.failure_reason = policy_reason
            queue_item.status = QueueStatus.CANCELLED.value
            queue_item.error_message = policy_reason

            await ApplicationEventManager.log_event(
                self.db, app.id, ApplicationEventType.STATUS_CHANGED,
                title=f"Application Skipped ({app.policy_decision})",
                new_status=app.status,
                description=policy_reason
            )
            await ApplicationAuditLogger.log_action(
                self.db, user_id=user_id, result="SKIPPED",
                application_id=app.id, job_id=job.id,
                source=job.source if hasattr(job, 'source') else None,
                match_score=app.match_score, policy_decision=app.policy_decision,
                failure_reason=policy_reason
            )
            await self.db.commit()
            return {"success": False, "status": app.status, "reason": policy_reason}

        # 3. Check Platform Capability
        cap_supported, cap_status, cap_reason = PlatformCapabilityManager.check_capability(job)
        if not cap_supported:
            app.status = ApplicationStatus.AUTO_APPLY_UNSUPPORTED.value
            app.failure_reason = cap_reason
            queue_item.status = QueueStatus.FAILED.value
            queue_item.error_message = cap_reason

            await ApplicationEventManager.log_event(
                self.db, app.id, ApplicationEventType.AUTO_APPLY_UNSUPPORTED,
                title="Automated Application Unsupported",
                new_status=app.status,
                description=cap_reason
            )
            await ApplicationAuditLogger.log_action(
                self.db, user_id=user_id, result="UNSUPPORTED",
                application_id=app.id, job_id=job.id,
                source=job.source if hasattr(job, 'source') else None,
                policy_decision=app.policy_decision, failure_reason=cap_reason
            )
            await self.db.commit()
            return {"success": False, "status": app.status, "reason": cap_reason}

        # 4. Resume Selection
        resume_id, resume_ver_id, resume_title = await ResumeSelectionService.select_best_resume(user_id, job, self.db)
        app.resume_id = resume_id
        app.resume_version_id = resume_ver_id

        # 5. Load Verified Candidate Data
        stmt_prof = select(UserProfile).where(UserProfile.user_id == user_id)
        profile = (await self.db.execute(stmt_prof)).scalar_one_or_none()

        stmt_pref = select(JobPreference).where(JobPreference.user_id == user_id)
        pref = (await self.db.execute(stmt_pref)).scalar_one_or_none()

        stmt_edu = select(Education).where(Education.user_profile_id == (profile.id if profile else None)).order_by(Education.created_at.desc())
        edus = list((await self.db.execute(stmt_edu)).scalars().all()) if profile else []

        stmt_exp = select(Experience).where(Experience.user_profile_id == (profile.id if profile else None)).order_by(Experience.created_at.desc())
        exps = list((await self.db.execute(stmt_exp)).scalars().all()) if profile else []

        stmt_skills = select(CandidateSkill).where(CandidateSkill.user_profile_id == (profile.id if profile else None))
        skills = list((await self.db.execute(stmt_skills)).scalars().all()) if profile else []

        stmt_projs = select(Project).where(Project.user_profile_id == (profile.id if profile else None))
        projs = list((await self.db.execute(stmt_projs)).scalars().all()) if profile else []

        # 6. Map Application Form Questions
        meta = getattr(job, "metadata_json", None) or {}
        if isinstance(meta, dict):
            app_questions = meta.get("application_questions", [])
        elif isinstance(meta, list):
            app_questions = meta
        else:
            app_questions = []

        cand_payload, mapped_answers, missing_q_fields = ApplicationDataMapper.map_application_data(
            user=app.user, profile=profile, preferences=pref,
            educations=edus, experiences=exps, skills=skills, projects=projs,
            application_questions=app_questions
        )

        # 7. Validate Application Data
        is_valid, val_status, missing_fields, val_errors = ApplicationValidator.validate_application(
            candidate_data=cand_payload,
            has_resume=(resume_id is not None),
            missing_question_fields=missing_q_fields,
            mapped_answers=mapped_answers
        )

        job_source_name = job.job_source.name if (hasattr(job, 'job_source') and job.job_source) else getattr(job, 'source', None)

        if not is_valid:
            app.status = val_status.value
            err_msg = "; ".join(val_errors) or f"Missing required fields: {', '.join(missing_fields)}"
            app.failure_reason = err_msg
            queue_item.status = QueueStatus.FAILED.value
            queue_item.error_message = err_msg

            await ApplicationEventManager.log_event(
                self.db, app.id, ApplicationEventType.VALIDATION_FAILED,
                title="Application Validation Failed",
                new_status=app.status,
                description=err_msg
            )
            await ApplicationAuditLogger.log_action(
                self.db, user_id=user_id, result="VALIDATION_FAILED",
                application_id=app.id, job_id=job.id,
                source=job_source_name,
                policy_decision=app.policy_decision, failure_reason=err_msg
            )
            await self.db.commit()
            return {"success": False, "status": app.status, "reason": err_msg}

        # 8. Store verified mapped answers in DB
        for ans in mapped_answers:
            ans_record = ApplicationAnswer(
                id=uuid.uuid4(),
                application_id=app.id,
                question_key=ans["question_key"],
                question_text=ans["question_text"],
                answer_text=ans["answer_text"],
                is_sensitive=ans["is_sensitive"],
                confidence_source=ans["confidence_source"]
            )
            self.db.add(ans_record)

        # 9. Execute Submission via Application Connector
        app.status = ApplicationStatus.SUBMITTING.value
        source_slug = job.job_source.slug if job.job_source else (job.source if hasattr(job, 'source') else None)
        connector = get_application_connector(source_slug)

        prepared_payload = await connector.prepare_application(
            external_job_id=job.external_id or str(job.id),
            candidate_data=cand_payload,
            mapped_answers=mapped_answers,
            resume_url="/uploads/candidate_resume.pdf"
        )

        attempt_num = (len(app.attempts) + 1)
        submission_start = datetime.now(timezone.utc)

        await ApplicationEventManager.log_event(
            self.db, app.id, ApplicationEventType.SUBMISSION_STARTED,
            title=f"Submission Attempt #{attempt_num}",
            new_status=ApplicationStatus.SUBMITTING.value,
            description=f"Sending application to {connector.name}."
        )

        sub_result = await connector.submit_application(
            prepared_payload=prepared_payload,
            idempotency_key=queue_item.idempotency_key
        )

        submission_end = datetime.now(timezone.utc)

        # Record Attempt
        attempt = ApplicationAttempt(
            id=uuid.uuid4(),
            application_id=app.id,
            attempt_number=attempt_num,
            status=sub_result.status,
            submission_method=SubmissionMethod.DIRECT_API.value,
            response_code=sub_result.response_code,
            external_application_id=sub_result.external_application_id,
            error_code=sub_result.error_code,
            error_message=sub_result.error_message,
            started_at=submission_start,
            completed_at=submission_end
        )
        self.db.add(attempt)
        app.last_attempt_at = submission_end

        # 10. Handle Submission Result
        if sub_result.success:
            app.status = ApplicationStatus.APPLIED.value
            app.applied_date = submission_end
            app.submitted_at = submission_end
            app.submission_method = SubmissionMethod.DIRECT_API.value
            app.external_application_id = sub_result.external_application_id
            app.failure_reason = None

            queue_item.status = QueueStatus.COMPLETED.value
            queue_item.completed_at = submission_end
            queue_item.error_message = None
            queue_item.locked_by = None
            queue_item.lease_expires_at = None

            worker_monitor_service.record_completed()

            await ApplicationEventManager.log_event(
                self.db, app.id, ApplicationEventType.SUBMISSION_SUCCESS,
                title="Application Submitted Successfully",
                old_status=ApplicationStatus.SUBMITTING.value,
                new_status=ApplicationStatus.APPLIED.value,
                description=f"Confirmation ID: {sub_result.external_application_id}",
                metadata=sub_result.details
            )
            await ApplicationAuditLogger.log_action(
                self.db, user_id=user_id, result="APPLIED",
                application_id=app.id, job_id=job.id,
                source=job_source_name,
                match_score=app.match_score, policy_decision=app.policy_decision,
                resume_version_id=app.resume_version_id, connector=connector.name,
                submission_method=SubmissionMethod.DIRECT_API.value
            )
            await self.db.commit()
            return {
                "success": True,
                "status": "APPLIED",
                "application_id": str(app.id),
                "external_application_id": sub_result.external_application_id
            }

        else:
            # Handle Failure & Check Retryability
            should_retry, delay_sec, retry_reason = RetryManager.should_retry(
                error_code=sub_result.error_code or "ERROR",
                attempt_count=attempt_num,
                max_attempts=queue_item.max_attempts,
                is_explicit_transient=sub_result.is_transient_error
            )

            if should_retry:
                app.status = ApplicationStatus.RETRYING.value
                app.failure_reason = sub_result.error_message
                queue_item.status = QueueStatus.RETRYING.value
                queue_item.scheduled_at = datetime.now(timezone.utc).replace(microsecond=0)
                queue_item.error_message = retry_reason
                queue_item.locked_by = None
                queue_item.lease_expires_at = None

                await ApplicationEventManager.log_event(
                    self.db, app.id, ApplicationEventType.RETRY_SCHEDULED,
                    title=f"Retry Scheduled (Attempt #{attempt_num + 1})",
                    new_status=ApplicationStatus.RETRYING.value,
                    description=retry_reason
                )
            else:
                app.status = sub_result.status if sub_result.status in ApplicationStatus.__members__ else ApplicationStatus.FAILED.value
                app.failure_reason = sub_result.error_message or "Submission rejected by platform."
                queue_item.status = QueueStatus.FAILED.value
                queue_item.completed_at = submission_end
                queue_item.error_message = app.failure_reason
                queue_item.locked_by = None
                queue_item.lease_expires_at = None

                worker_monitor_service.record_failed()

                # Add to Dead Letter Queue for permanent failures
                dlq_entry = DeadLetterApplicationQueue(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    application_id=app.id,
                    job_id=job.id,
                    failure_reason=app.failure_reason,
                    attempt_count=attempt_num,
                    last_error=sub_result.error_message,
                    resolved=False
                )
                self.db.add(dlq_entry)

                await ApplicationEventManager.log_event(
                    self.db, app.id, ApplicationEventType.SUBMISSION_FAILED,
                    title="Application Submission Failed",
                    new_status=app.status,
                    description=app.failure_reason
                )
                await ApplicationAuditLogger.log_action(
                    self.db, user_id=user_id, result="FAILED",
                    application_id=app.id, job_id=job.id,
                    source=job_source_name,
                    match_score=app.match_score, policy_decision=app.policy_decision,
                    connector=connector.name, failure_reason=app.failure_reason
                )

            await self.db.commit()
            return {
                "success": False,
                "status": app.status,
                "should_retry": should_retry,
                "reason": sub_result.error_message
            }
