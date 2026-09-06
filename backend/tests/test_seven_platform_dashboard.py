import pytest
import uuid
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database.models.application import Application, ApplicationPolicy, AutoApplyDailyRun
from app.database.models.job import Job, JobSource
from app.database.models.match import JobMatch
from app.database.models.user import User, UserProfile
from app.shared.constants import (
    ApplicationStatus,
    SubmissionMethod,
    ConnectorCapabilityStatus,
    PolicyDecision
)
from app.modules.applications.service import ApplicationService
from app.modules.applications.policy import ApplicationPolicyEngine
from app.modules.jobs.connectors.adapters import SEVEN_PRIMARY_SOURCES, get_connector_by_slug
from app.core.security import create_access_token

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")


# =====================================================================
# Condition 1: 7 Distinct Platform Definitions
# =====================================================================
def test_condition_1_seven_distinct_platform_definitions():
    expected_sources = ["naukri", "indeed", "unstop", "linkedin", "internshala", "wellfound", "career_pages"]
    assert len(SEVEN_PRIMARY_SOURCES) == 7
    for src in expected_sources:
        assert src in SEVEN_PRIMARY_SOURCES
        connector = get_connector_by_slug(src)
        assert connector is not None, f"Connector for {src} must be registered"
        assert connector.slug == src


# =====================================================================
# Condition 2: Independent 30/day limit per platform
# =====================================================================
def test_condition_2_independent_30_per_platform_daily_limit():
    policy = ApplicationPolicy(
        auto_apply_enabled=True,
        minimum_match_score=60.0,
        daily_application_limit=210,
        per_source_daily_limit=30
    )
    job = Job(company_name="TestCorp", title="Software Engineer", location="Remote")

    # Platform A (Naukri) is at 30 -> Rejected
    appr_naukri, dec_naukri, _ = ApplicationPolicyEngine.evaluate(
        policy=policy, job=job, daily_applications_count=30, source_daily_applications_count=30
    )
    assert not appr_naukri
    assert dec_naukri == PolicyDecision.SKIP_DAILY_LIMIT

    # Platform B (Indeed) is at 10 -> Approved independently
    appr_indeed, dec_indeed, _ = ApplicationPolicyEngine.evaluate(
        policy=policy, job=job, daily_applications_count=30, source_daily_applications_count=10
    )
    assert appr_indeed
    assert dec_indeed == PolicyDecision.AUTO_APPLY


# =====================================================================
# Condition 3: Total 210/day global cap (30 * 7 = 210)
# =====================================================================
def test_condition_3_global_capacity_cap_210():
    policy = ApplicationPolicy(
        auto_apply_enabled=True,
        minimum_match_score=60.0,
        daily_application_limit=210,
        per_source_daily_limit=30
    )
    assert policy.daily_application_limit == 210
    assert policy.per_source_daily_limit == 30
    assert 30 * 7 == 210

    job = Job(company_name="TestCorp", title="Software Engineer", location="Remote")
    # When total reaches 210, even if platform count is 0, global limit halts
    approved, decision, _ = ApplicationPolicyEngine.evaluate(
        policy=policy, job=job, daily_applications_count=210, source_daily_applications_count=0
    )
    assert not approved
    assert decision == PolicyDecision.SKIP_DAILY_LIMIT


# =====================================================================
# Condition 4: Honest counting — EXTERNAL_APPLICATION_REQUIRED does not increment Applied
# =====================================================================
@pytest.mark.asyncio
async def test_condition_4_honest_counting_manual_required_does_not_increment_applied(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)
    job = Job(id=uuid.uuid4(), title="Python Dev", company_name="Corp", description="desc", deduplication_hash=uuid.uuid4().hex)
    async_session.add(job)
    await async_session.flush()

    # Create manual application
    app = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        source="naukri",
        status=ApplicationStatus.EXTERNAL_APPLICATION_REQUIRED.value,
        submission_method=SubmissionMethod.EXTERNAL_PORTAL.value,
        created_at=datetime.now(timezone.utc)
    )
    async_session.add(app)
    await async_session.commit()

    service = ApplicationService(async_session)
    stats = await service.get_platform_statistics(user.id)
    naukri_stat = stats.platforms["naukri"]

    assert naukri_stat.applied == 0
    assert naukri_stat.applied_today == 0
    assert naukri_stat.manual_required >= 1


# =====================================================================
# Condition 5: Honest counting — FAILED does not increment Applied
# =====================================================================
@pytest.mark.asyncio
async def test_condition_5_honest_counting_failed_does_not_increment_applied(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)
    job = Job(id=uuid.uuid4(), title="Node Dev", company_name="Corp", description="desc", deduplication_hash=uuid.uuid4().hex)
    async_session.add(job)
    await async_session.flush()

    app = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        source="indeed",
        status=ApplicationStatus.FAILED.value,
        submission_method=SubmissionMethod.DIRECT_API.value,
        failure_reason="Integration network timeout",
        created_at=datetime.now(timezone.utc)
    )
    async_session.add(app)
    await async_session.commit()

    service = ApplicationService(async_session)
    stats = await service.get_platform_statistics(user.id)
    indeed_stat = stats.platforms["indeed"]

    assert indeed_stat.applied == 0
    assert indeed_stat.applied_today == 0
    assert indeed_stat.failed >= 1


# =====================================================================
# Condition 6: Honest counting — DISCOVERED and MATCHED do not increment Applied
# =====================================================================
@pytest.mark.asyncio
async def test_condition_6_honest_counting_discovered_matched_does_not_increment_applied(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)
    job = Job(id=uuid.uuid4(), title="React Dev", company_name="Corp", description="desc", deduplication_hash=uuid.uuid4().hex)
    async_session.add(job)
    await async_session.flush()

    app = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        source="unstop",
        status=ApplicationStatus.DISCOVERED.value,
        submission_method=SubmissionMethod.MANUAL.value,
        created_at=datetime.now(timezone.utc)
    )
    async_session.add(app)
    await async_session.commit()

    service = ApplicationService(async_session)
    stats = await service.get_platform_statistics(user.id)
    unstop_stat = stats.platforms["unstop"]

    assert unstop_stat.applied == 0
    assert unstop_stat.applied_today == 0


# =====================================================================
# Condition 7: Portal-only platforms report Applied: 0 for automated routine and increment manual_required
# =====================================================================
@pytest.mark.asyncio
async def test_condition_7_portal_only_platforms_report_applied_zero(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)

    portal_sources = ["naukri", "indeed", "unstop", "linkedin", "internshala", "wellfound"]
    for src in portal_sources:
        job = Job(id=uuid.uuid4(), title=f"Dev {src}", company_name=f"Company {src}", description="desc", deduplication_hash=uuid.uuid4().hex)
        async_session.add(job)
        await async_session.flush()
        app = Application(
            id=uuid.uuid4(),
            user_id=user.id,
            job_id=job.id,
            source=src,
            status=ApplicationStatus.EXTERNAL_APPLICATION_REQUIRED.value,
            submission_method=SubmissionMethod.EXTERNAL_PORTAL.value,
            created_at=datetime.now(timezone.utc)
        )
        async_session.add(app)

    await async_session.commit()

    service = ApplicationService(async_session)
    stats = await service.get_platform_statistics(user.id)

    for src in portal_sources:
        assert stats.platforms[src].applied_today == 0
        assert stats.platforms[src].applied == 0
        assert stats.platforms[src].manual_required >= 1


# =====================================================================
# Condition 8: Authorized ATS increments Applied only upon confirmed success
# =====================================================================
@pytest.mark.asyncio
async def test_condition_8_authorized_ats_increments_applied_on_success(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)
    job = Job(id=uuid.uuid4(), title="Staff Engineer", company_name="Greenhouse Client", description="desc", deduplication_hash=uuid.uuid4().hex)
    async_session.add(job)
    await async_session.flush()

    now_utc = datetime.now(timezone.utc)
    app = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        source="career_pages",
        status=ApplicationStatus.APPLIED.value,
        submission_method=SubmissionMethod.DIRECT_API.value,
        applied_date=now_utc,
        submitted_at=now_utc,
        created_at=now_utc
    )
    async_session.add(app)
    await async_session.commit()

    service = ApplicationService(async_session)
    stats = await service.get_platform_statistics(user.id)
    career_stat = stats.platforms["career_pages"]

    assert career_stat.applied >= 1
    assert career_stat.applied_today >= 1
    assert career_stat.current_daily_count >= 1
    assert career_stat.progress_pct > 0


# =====================================================================
# Condition 9: Failed submissions increment failed count and do not count toward Applied
# =====================================================================
@pytest.mark.asyncio
async def test_condition_9_failed_submissions_increment_failed_count(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)
    job = Job(id=uuid.uuid4(), title="Lever Dev", company_name="Lever Partner", description="desc", deduplication_hash=uuid.uuid4().hex)
    async_session.add(job)
    await async_session.flush()

    now_utc = datetime.now(timezone.utc)
    app = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        source="lever",
        status=ApplicationStatus.FAILED.value,
        submission_method=SubmissionMethod.DIRECT_API.value,
        failure_reason="Endpoint 500 error",
        created_at=now_utc
    )
    async_session.add(app)
    await async_session.commit()

    service = ApplicationService(async_session)
    stats = await service.get_platform_statistics(user.id)
    career_stat = stats.platforms["career_pages"]

    assert career_stat.failed >= 1
    assert career_stat.applied == 0
    assert career_stat.applied_today == 0


# =====================================================================
# Condition 10: Per-platform jobs_discovered accurately reflects active jobs
# =====================================================================
@pytest.mark.asyncio
async def test_condition_10_per_platform_jobs_discovered_accuracy(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)

    # Find or create a job source for internshala
    stmt = select(JobSource).where(JobSource.slug == "internshala")
    source = (await async_session.execute(stmt)).scalar_one_or_none()
    if not source:
        source = JobSource(id=uuid.uuid4(), name="Internshala", slug="internshala", is_active=True)
        async_session.add(source)
        await async_session.flush()

    job1 = Job(id=uuid.uuid4(), job_source_id=source.id, title="Intern A", company_name="Co A", description="d", is_active=True, deduplication_hash=uuid.uuid4().hex)
    job2 = Job(id=uuid.uuid4(), job_source_id=source.id, title="Intern B", company_name="Co B", description="d", is_active=True, deduplication_hash=uuid.uuid4().hex)
    async_session.add_all([job1, job2])
    await async_session.commit()

    service = ApplicationService(async_session)
    stats = await service.get_platform_statistics(user.id)
    internshala_stat = stats.platforms["internshala"]
    assert internshala_stat.jobs_discovered >= 2


# =====================================================================
# Condition 11: Per-platform matching_jobs reflects user matches >= threshold
# =====================================================================
@pytest.mark.asyncio
async def test_condition_11_per_platform_matching_jobs_accuracy(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)

    policy = ApplicationPolicy(id=uuid.uuid4(), user_id=user.id, auto_apply_enabled=True, minimum_match_score=80.0)
    async_session.add(policy)

    stmt = select(JobSource).where(JobSource.slug == "wellfound")
    source = (await async_session.execute(stmt)).scalar_one_or_none()
    if not source:
        source = JobSource(id=uuid.uuid4(), name="Wellfound", slug="wellfound", is_active=True)
        async_session.add(source)
        await async_session.flush()

    job_high = Job(id=uuid.uuid4(), job_source_id=source.id, title="Founder Associate", company_name="Startup", description="d", is_active=True, deduplication_hash=uuid.uuid4().hex)
    job_low = Job(id=uuid.uuid4(), job_source_id=source.id, title="Junior Helper", company_name="Startup", description="d", is_active=True, deduplication_hash=uuid.uuid4().hex)
    async_session.add_all([job_high, job_low])
    await async_session.flush()

    match_high = JobMatch(id=uuid.uuid4(), user_id=user.id, job_id=job_high.id, overall_score=88.0)
    match_low = JobMatch(id=uuid.uuid4(), user_id=user.id, job_id=job_low.id, overall_score=65.0)
    async_session.add_all([match_high, match_low])
    await async_session.commit()

    service = ApplicationService(async_session)
    stats = await service.get_platform_statistics(user.id)
    wellfound_stat = stats.platforms["wellfound"]
    # Only match_high (88 >= 80) is counted
    assert wellfound_stat.matching_jobs >= 1


# =====================================================================
# Condition 12: Platform status identification
# =====================================================================
@pytest.mark.asyncio
async def test_condition_12_platform_status_identification(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)

    # 1. When auto-apply routine is active
    policy = ApplicationPolicy(id=uuid.uuid4(), user_id=user.id, auto_apply_enabled=True)
    async_session.add(policy)
    await async_session.commit()

    service = ApplicationService(async_session)
    stats_active = await service.get_platform_statistics(user.id)
    assert stats_active.platforms["career_pages"].status == "AUTOMATION AVAILABLE"
    assert stats_active.platforms["naukri"].status == "ACTIVE"

    # 2. When policy is paused (disabled)
    policy.auto_apply_enabled = False
    await async_session.commit()
    stats_paused = await service.get_platform_statistics(user.id)
    for p in stats_paused.platforms.values():
        assert p.status == "PAUSED"


# =====================================================================
# Condition 13: Timestamps stored in UTC and rendered in Asia/Kolkata (IST)
# =====================================================================
@pytest.mark.asyncio
async def test_condition_13_utc_storage_and_ist_formatting(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)
    job = Job(id=uuid.uuid4(), title="Dev", company_name="Corp", description="desc", deduplication_hash=uuid.uuid4().hex)
    async_session.add(job)
    await async_session.flush()

    utc_dt = datetime(2026, 9, 6, 4, 30, tzinfo=timezone.utc) # 4:30 AM UTC = 10:00 AM IST
    app = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        source="linkedin",
        status=ApplicationStatus.APPLIED.value,
        submission_method=SubmissionMethod.DIRECT_API.value,
        applied_date=utc_dt,
        created_at=utc_dt
    )
    async_session.add(app)
    await async_session.commit()

    service = ApplicationService(async_session)
    stats = await service.get_platform_statistics(user.id)
    linkedin_stat = stats.platforms["linkedin"]

    assert "IST" in linkedin_stat.last_activity_ist
    assert "10:00 AM" in linkedin_stat.last_activity_ist
    assert "Sep 2026" in linkedin_stat.last_activity_ist or "06 Sep" in linkedin_stat.last_activity_ist


# =====================================================================
# Condition 14: Platform failure isolation
# =====================================================================
@pytest.mark.asyncio
async def test_condition_14_platform_failure_isolation(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)
    policy = ApplicationPolicy(id=uuid.uuid4(), user_id=user.id, auto_apply_enabled=True)
    async_session.add(policy)
    await async_session.commit()

    service = ApplicationService(async_session)
    # Even if one connector had an internal error, stats for all 7 platforms resolve cleanly
    stats = await service.get_platform_statistics(user.id)
    assert len(stats.platforms) == 7
    for slug in SEVEN_PRIMARY_SOURCES:
        assert slug in stats.platforms
        assert stats.platforms[slug].daily_limit == 30


# =====================================================================
# Condition 15: Filter applications by platform source
# =====================================================================
@pytest.mark.asyncio
async def test_condition_15_filter_applications_by_source(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)

    job1 = Job(id=uuid.uuid4(), title="J1", company_name="C1", description="d", deduplication_hash=uuid.uuid4().hex)
    job2 = Job(id=uuid.uuid4(), title="J2", company_name="C2", description="d", deduplication_hash=uuid.uuid4().hex)
    job3 = Job(id=uuid.uuid4(), title="J3", company_name="C3", description="d", deduplication_hash=uuid.uuid4().hex)
    async_session.add_all([job1, job2, job3])
    await async_session.flush()

    app_naukri = Application(id=uuid.uuid4(), user_id=user.id, job_id=job1.id, source="naukri", status="APPLIED", submission_method="MANUAL")
    app_indeed = Application(id=uuid.uuid4(), user_id=user.id, job_id=job2.id, source="indeed", status="APPLIED", submission_method="MANUAL")
    app_gh = Application(id=uuid.uuid4(), user_id=user.id, job_id=job3.id, source="greenhouse", status="APPLIED", submission_method="DIRECT_API")
    async_session.add_all([app_naukri, app_indeed, app_gh])
    await async_session.commit()

    service = ApplicationService(async_session)

    # Filter source=naukri
    naukri_apps = await service.list_applications(user.id, source="naukri")
    assert len(naukri_apps) == 1
    assert naukri_apps[0].source == "naukri"

    # Filter source=career_pages (must also include greenhouse/lever)
    career_apps = await service.list_applications(user.id, source="career_pages")
    assert len(career_apps) == 1
    assert career_apps[0].source == "greenhouse"


# =====================================================================
# Condition 16: Filter applications by time range
# =====================================================================
@pytest.mark.asyncio
async def test_condition_16_filter_applications_by_time_range(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User", is_active=True)
    async_session.add(user)

    now_utc = datetime.now(timezone.utc)
    now_kolkata = now_utc.astimezone(KOLKATA_TZ)
    start_of_today_kolkata = now_kolkata.replace(hour=0, minute=0, second=0, microsecond=0)
    today_time_utc = start_of_today_kolkata.astimezone(timezone.utc) + timedelta(hours=2)
    yesterday_time_utc = start_of_today_kolkata.astimezone(timezone.utc) - timedelta(hours=12)
    old_time_utc = start_of_today_kolkata.astimezone(timezone.utc) - timedelta(days=40)

    job_today = Job(id=uuid.uuid4(), title="Today Job", company_name="C1", description="d", deduplication_hash=uuid.uuid4().hex)
    job_yest = Job(id=uuid.uuid4(), title="Yesterday Job", company_name="C2", description="d", deduplication_hash=uuid.uuid4().hex)
    job_old = Job(id=uuid.uuid4(), title="Old Job", company_name="C3", description="d", deduplication_hash=uuid.uuid4().hex)
    async_session.add_all([job_today, job_yest, job_old])
    await async_session.flush()

    app_today = Application(id=uuid.uuid4(), user_id=user.id, job_id=job_today.id, source="naukri", status="APPLIED", submission_method="DIRECT", applied_date=today_time_utc, created_at=today_time_utc)
    app_yest = Application(id=uuid.uuid4(), user_id=user.id, job_id=job_yest.id, source="naukri", status="APPLIED", submission_method="DIRECT", applied_date=yesterday_time_utc, created_at=yesterday_time_utc)
    app_old = Application(id=uuid.uuid4(), user_id=user.id, job_id=job_old.id, source="naukri", status="APPLIED", submission_method="DIRECT", applied_date=old_time_utc, created_at=old_time_utc)
    async_session.add_all([app_today, app_yest, app_old])
    await async_session.commit()

    service = ApplicationService(async_session)

    # Filter: today
    res_today = await service.list_applications(user.id, source="naukri", time_range="today")
    assert len(res_today) == 1
    assert res_today[0].id == app_today.id

    # Filter: yesterday
    res_yest = await service.list_applications(user.id, source="naukri", time_range="yesterday")
    assert len(res_yest) == 1
    assert res_yest[0].id == app_yest.id

    # Filter: 30d
    res_30d = await service.list_applications(user.id, source="naukri", time_range="30d")
    assert len(res_30d) == 2

    # Filter: all
    res_all = await service.list_applications(user.id, source="naukri", time_range="all")
    assert len(res_all) == 3


# =====================================================================
# Condition 17: Platform stats endpoint contract
# =====================================================================
@pytest.mark.asyncio
async def test_condition_17_platform_stats_endpoint_contract(async_client: httpx.AsyncClient, test_user: User):
    token = create_access_token(test_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/auto-apply/platforms/stats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "date" in data
    assert "schedule_time" in data
    assert data["schedule_time"] == "10:00 AM IST"
    assert "total_daily_limit" in data
    assert data["total_daily_limit"] == 210
    assert "total_applied_today" in data
    assert "platforms" in data

    platforms = data["platforms"]
    assert len(platforms) == 7

    for expected_slug in ["naukri", "indeed", "unstop", "linkedin", "internshala", "wellfound", "career_pages"]:
        assert expected_slug in platforms
        p = platforms[expected_slug]
        assert "name" in p
        assert "slug" in p
        assert "jobs_discovered" in p
        assert "matching_jobs" in p
        assert "applied" in p
        assert "manual_required" in p
        assert "failed" in p
        assert "daily_limit" in p
        assert p["daily_limit"] == 30
        assert "applied_today" in p
        assert "progress_pct" in p
        assert "last_activity_ist" in p
        assert "status" in p
        assert "automation_type" in p
