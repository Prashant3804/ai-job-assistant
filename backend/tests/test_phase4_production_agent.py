"""Phase 4 Production Autonomous Agent End-to-End Verification Suite.

Tests:
1. Deterministic 5-Job Application Flow:
   - Job 1: Match 82%, supported auto-apply -> SUBMITTED (increments applied_count)
   - Job 2: Match 73%, unsupported portal -> EXTERNAL_APPLICATION_REQUIRED (increments manual_required_count, NOT applied_count)
   - Job 3: Match 64%, any portal -> SKIPPED (< 65% threshold, does not qualify)
   - Job 4: Match 65%, supported auto-apply -> QUALIFIES (>= 65% threshold) -> SUBMITTED (increments applied_count)
   - Job 5: Match 90%, supported auto-apply with API/connector failure -> FAILED (increments failed_count, NOT applied_count)

2. Counting Integrity:
   - Verified total jobs found: 5
   - Verified matching jobs (>= 65%): 4
   - Verified applications submitted: 2
   - Verified manual required: 1
   - Verified failed: 1
   - Verified skipped: 1

3. Scheduler Idempotency:
   - Standalone daily run at 10:00 AM IST cannot be executed multiple times for the same user on the same calendar day.
"""

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserProfile, Education, Experience, CandidateSkill, JobPreference
from app.database.models.job import Job, JobSource
from app.database.models.match import JobMatch
from app.database.models.application import (
    Application,
    ApplicationPolicy,
    AutoApplyDailyRun
)
from app.shared.constants import (
    ApplicationStatus,
    ConnectorCapabilityStatus,
    SubmissionMethod
)
from app.modules.applications.daily_routine import AutoApplyDailyRoutineService


@pytest.mark.asyncio
async def test_phase4_deterministic_5_job_flow_and_counting_integrity(async_session: AsyncSession):
    """Executes the exact 5-job deterministic scenario and asserts counting integrity."""
    # 1. Setup Candidate User & Profile
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="phase4_candidate@example.com",
        hashed_password="secure_hashed_password_123",
        full_name="Arjun Verma",
        is_active=True,
    )
    async_session.add(user)
    await async_session.flush()

    profile = UserProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        headline="Senior Distributed Systems & Cloud Engineer",
        summary="Computer Science graduate with 5 years building scalable backend services.",
        target_roles=["Senior Backend Engineer", "Distributed Systems Engineer"],
        years_of_experience=5.0,
        location="Bengaluru, India",
    )
    async_session.add(profile)

    pref = JobPreference(
        id=uuid.uuid4(),
        user_id=user.id,
        sponsorship_required=False,
        min_base_salary=2800000,
        currency="INR",
    )
    async_session.add(pref)

    edu = Education(
        id=uuid.uuid4(),
        user_profile_id=profile.id,
        degree="B.Tech in Computer Science",
        institution="IIT Delhi",
        field_of_study="Computer Science & Engineering",
        end_date="2021",
    )
    async_session.add(edu)

    exp = Experience(
        id=uuid.uuid4(),
        user_profile_id=profile.id,
        company_name="HyperScale India",
        title="Software Development Engineer II",
        start_date="2021-07",
        end_date="Present",
        description="Architected high-throughput message processing pipelines using Python, Kafka, and Redis.",
    )
    async_session.add(exp)

    skills = [
        CandidateSkill(id=uuid.uuid4(), user_profile_id=profile.id, name="Python", category="TECHNICAL"),
        CandidateSkill(id=uuid.uuid4(), user_profile_id=profile.id, name="FastAPI", category="TECHNICAL"),
        CandidateSkill(id=uuid.uuid4(), user_profile_id=profile.id, name="PostgreSQL", category="TECHNICAL"),
        CandidateSkill(id=uuid.uuid4(), user_profile_id=profile.id, name="Kafka", category="TECHNICAL"),
    ]
    async_session.add_all(skills)

    # Policy: Auto-apply enabled, 65% minimum match score threshold
    policy = ApplicationPolicy(
        id=uuid.uuid4(),
        user_id=user.id,
        auto_apply_enabled=True,
        minimum_match_score=65.0,
        daily_application_limit=210,
        per_source_daily_limit=30,
        duplicate_protection=True,
    )
    async_session.add(policy)

    # 2. Setup Sources
    # Source A: Supported direct ATS / API
    src_supported = JobSource(
        id=uuid.uuid4(),
        name="Supported Partner ATS",
        slug="mock_ats",
        connector_type="DIRECT_API",
        capability_status=ConnectorCapabilityStatus.SUPPORTED_AUTO_APPLY.value,
        is_active=True,
    )
    # Source B: Unsupported portal (LinkedIn / Naukri / Company Careers)
    src_unsupported = JobSource(
        id=uuid.uuid4(),
        name="Company Careers Portal",
        slug="career_pages",
        connector_type="PORTAL",
        capability_status=ConnectorCapabilityStatus.EXTERNAL_APPLICATION_REQUIRED.value,
        is_active=True,
    )
    async_session.add_all([src_supported, src_unsupported])
    await async_session.flush()

    # 3. Setup the 5 Deterministic Jobs with valid deduplication_hash
    # Job 1: Match = 82% (Supported -> SUBMITTED)
    job1 = Job(
        id=uuid.uuid4(),
        job_source_id=src_supported.id,
        title="Distributed Systems Engineer",
        company_name="CloudScale Corp",
        description="Design and build event-driven microservices in Python and Kafka.",
        location="Bengaluru / Remote",
        apply_url="https://cloudscale.example.com/jobs/101",
        deduplication_hash=f"phase4_hash_1_{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    # Job 2: Match = 73% (Unsupported portal -> EXTERNAL_APPLICATION_REQUIRED)
    job2 = Job(
        id=uuid.uuid4(),
        job_source_id=src_unsupported.id,
        title="Backend Infrastructure Engineer",
        company_name="FintechCore India",
        description="Scaling payment gateways using Python and PostgreSQL.",
        location="Remote, India",
        apply_url="https://fintechcore.example.com/apply/202",
        deduplication_hash=f"phase4_hash_2_{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    # Job 3: Match = 64% (Below 65% threshold -> SKIPPED)
    job3 = Job(
        id=uuid.uuid4(),
        job_source_id=src_supported.id,
        title="Frontend UI Developer",
        company_name="DesignFirst Labs",
        description="CSS, Tailwind, and React design system engineering.",
        location="Hyderabad, India",
        apply_url="https://designfirst.example.com/jobs/303",
        deduplication_hash=f"phase4_hash_3_{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    # Job 4: Match = 65% (Exactly threshold, Supported -> SUBMITTED)
    job4 = Job(
        id=uuid.uuid4(),
        job_source_id=src_supported.id,
        title="Platform Reliability Engineer",
        company_name="InfraSecure",
        description="Observability, logging, and backend infrastructure reliability.",
        location="Remote",
        apply_url="https://infrasecure.example.com/apply/404",
        deduplication_hash=f"phase4_hash_4_{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    # Job 5: Match = 90% (Supported, but connector fails -> FAILED)
    job5 = Job(
        id=uuid.uuid4(),
        job_source_id=src_supported.id,
        title="Principal Backend Architect",
        company_name="TitanCloud",
        description="Distributed architecture leadership and high-scale Python engines.",
        location="Bengaluru, India",
        apply_url="https://titancloud.example.com/careers/505",
        deduplication_hash=f"phase4_hash_5_{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    async_session.add_all([job1, job2, job3, job4, job5])
    await async_session.flush()

    # 4. Setup Pre-calculated Matches
    m1 = JobMatch(id=uuid.uuid4(), user_id=user.id, job_id=job1.id, overall_score=82.0, eligibility_status="ELIGIBLE")
    m2 = JobMatch(id=uuid.uuid4(), user_id=user.id, job_id=job2.id, overall_score=73.0, eligibility_status="ELIGIBLE")
    m3 = JobMatch(id=uuid.uuid4(), user_id=user.id, job_id=job3.id, overall_score=64.0, eligibility_status="REVIEW")
    m4 = JobMatch(id=uuid.uuid4(), user_id=user.id, job_id=job4.id, overall_score=65.0, eligibility_status="ELIGIBLE")
    m5 = JobMatch(id=uuid.uuid4(), user_id=user.id, job_id=job5.id, overall_score=90.0, eligibility_status="ELIGIBLE")
    async_session.add_all([m1, m2, m3, m4, m5])
    await async_session.commit()

    # 5. Dynamic Queue Processing mock: Job 5 fails, Jobs 1 & 4 succeed
    async def dynamic_process(queue_item):
        app_stmt = select(Application).where(Application.id == queue_item.application_id)
        app_res = await async_session.execute(app_stmt)
        app_obj = app_res.scalar_one()

        if app_obj.job_id == job5.id:
            app_obj.status = ApplicationStatus.FAILED.value
            app_obj.failure_reason = "401 Unauthorized: Partner API credentials expired or revoked."
            await async_session.commit()
            return {
                "success": False,
                "status": "FAILED",
                "reason": "401 Unauthorized: Partner API credentials expired."
            }
        else:
            app_obj.status = ApplicationStatus.APPLIED.value
            app_obj.external_job_id = f"ext-sub-{uuid.uuid4().hex[:8]}"
            await async_session.commit()
            return {
                "success": True,
                "status": "SUBMITTED",
                "external_application_id": app_obj.external_job_id
            }

    # 6. Execute Daily Routine
    routine_service = AutoApplyDailyRoutineService(async_session)

    with patch("app.modules.jobs.service.JobService.sync_all_discovery_sources", new_callable=AsyncMock) as mock_sync,          patch("app.modules.applications.agent.ApplicationAgent.process_queue_item", side_effect=dynamic_process):
        mock_sync.return_value = {"synced": 5}

        scheduled_time = datetime(2026, 9, 8, 4, 30, tzinfo=timezone.utc)
        run = await routine_service.execute_daily_routine_for_user(user.id, scheduled_time=scheduled_time)

    # 7. Strictly Assert Counting Integrity
    assert run is not None
    assert run.status == "COMPLETED"
    assert run.jobs_found == 5, f"Expected 5 jobs found, got {run.jobs_found}"
    assert run.matching_jobs == 4, f"Expected 4 matching jobs (>=65%), got {run.matching_jobs}"
    assert run.applied_count == 2, f"Expected exactly 2 applied (Jobs 1 & 4), got {run.applied_count}"
    assert run.manual_required_count == 1, f"Expected 1 manual required (Job 2), got {run.manual_required_count}"
    assert run.failed_count == 1, f"Expected 1 failed (Job 5), got {run.failed_count}"
    assert run.skipped_count == 1, f"Expected 1 skipped (Job 3 with 64%), got {run.skipped_count}"
    assert run.already_applied_count == 0

    # 8. Assert Individual Application Records in Database
    apps_stmt = select(Application).where(Application.user_id == user.id)
    apps = list((await async_session.execute(apps_stmt)).scalars().all())

    assert len(apps) == 4

    job_app_map = {app.job_id: app for app in apps}

    # Job 1: Applied
    assert job1.id in job_app_map
    assert job_app_map[job1.id].status in ["APPLIED", "SUBMITTED"]
    assert job_app_map[job1.id].match_score == 82.0

    # Job 2: Manual Action Required
    assert job2.id in job_app_map
    assert job_app_map[job2.id].status == ApplicationStatus.EXTERNAL_APPLICATION_REQUIRED.value
    assert job_app_map[job2.id].submission_method == SubmissionMethod.EXTERNAL_PORTAL.value
    assert job_app_map[job2.id].match_score == 73.0

    # Job 3: NOT in applications (skipped due to 64% < 65%)
    assert job3.id not in job_app_map

    # Job 4: Applied
    assert job4.id in job_app_map
    assert job_app_map[job4.id].status in ["APPLIED", "SUBMITTED"]
    assert job_app_map[job4.id].match_score == 65.0

    # Job 5: Failed
    assert job5.id in job_app_map
    assert job_app_map[job5.id].status == ApplicationStatus.FAILED.value
    assert job_app_map[job5.id].match_score == 90.0


@pytest.mark.asyncio
async def test_scheduler_idempotency_prevents_duplicate_daily_runs(async_session: AsyncSession):
    """Verifies that 10:00 AM IST daily routine cannot be executed multiple times on the same calendar day."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="idempotent_candidate@example.com",
        hashed_password="secure_password",
        full_name="Priya Patel",
        is_active=True,
    )
    async_session.add(user)
    await async_session.flush()

    profile = UserProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        headline="Full Stack Software Engineer",
        target_roles=["Full Stack Engineer"],
    )
    async_session.add(profile)

    policy = ApplicationPolicy(
        id=uuid.uuid4(),
        user_id=user.id,
        auto_apply_enabled=True,
        minimum_match_score=65.0,
    )
    async_session.add(policy)
    await async_session.commit()

    routine_service = AutoApplyDailyRoutineService(async_session)

    # 1st execution of 10:00 AM routine
    scheduled_10am = datetime(2026, 9, 8, 4, 30, tzinfo=timezone.utc)  # 10:00 AM IST
    with patch("app.modules.jobs.service.JobService.sync_all_discovery_sources", new_callable=AsyncMock) as mock_sync:
        mock_sync.return_value = {}
        first_runs = await routine_service.execute_daily_routine_for_all_active_users(scheduled_time=scheduled_10am)

    assert len(first_runs) == 1
    assert first_runs[0].status == "COMPLETED"
    run_id_first = first_runs[0].id

    # 2nd execution attempt on the SAME day (e.g. worker container restarts)
    with patch("app.modules.jobs.service.JobService.sync_all_discovery_sources", new_callable=AsyncMock) as mock_sync:
        mock_sync.return_value = {}
        second_runs = await routine_service.execute_daily_routine_for_all_active_users(scheduled_time=scheduled_10am)

    # Must return the existing run and NOT trigger a duplicate execution
    assert len(second_runs) == 1
    assert second_runs[0].id == run_id_first

    # Total runs in DB for this user must remain exactly 1
    total_runs_stmt = select(AutoApplyDailyRun).where(AutoApplyDailyRun.user_id == user.id)
    all_runs = list((await async_session.execute(total_runs_stmt)).scalars().all())
    assert len(all_runs) == 1
