import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.models.application import Application, ApplicationPolicy, ApplicationQueueItem
from app.database.models.job import Job, JobSource
from app.database.models.match import JobMatch
from app.database.models.user import User
from app.shared.constants import (
    ApplicationStatus,
    SubmissionMethod,
    QueueStatus,
    PolicyDecision
)
from app.modules.applications.policy import ApplicationPolicyEngine
from app.modules.applications.service import ApplicationService
from app.modules.applications.schemas import ApplicationPolicyUpdate
from app.modules.chat.tools.application_tools import (
    GetAutoApplyStatusTool,
    GetAutoApplyPolicyTool
)

@pytest.mark.asyncio
async def test_unlimited_mode_policy_evaluation():
    """Test that when daily limits are None, unlimited applications are permitted."""
    policy = ApplicationPolicy(
        auto_apply_enabled=True,
        minimum_match_score=80.0,
        daily_application_limit=None,
        per_source_daily_limit=None,
        blocked_companies=["ScamCorp"],
        blocked_keywords=["unpaid"],
        allow_remote=True,
        allow_hybrid=True,
        allow_onsite=True
    )

    job = Job(
        id=uuid.uuid4(),
        title="Senior Python Engineer",
        company_name="TechCorp",
        description="Great engineering role",
        remote_type="REMOTE",
        deduplication_hash="test_hash_1",
        is_active=True
    )

    match = JobMatch(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        job_id=job.id,
        overall_score=90.0,
        eligibility_status="ELIGIBLE"
    )

    # 1. 0 applications today -> Approved
    approved, dec, reason = ApplicationPolicyEngine.evaluate(
        policy, job, match, daily_applications_count=0, source_daily_applications_count=0
    )
    assert approved is True
    assert dec == PolicyDecision.AUTO_APPLY

    # 2. 30 applications today -> STILL Approved (no artificial 30 limit!)
    approved, dec, reason = ApplicationPolicyEngine.evaluate(
        policy, job, match, daily_applications_count=30, source_daily_applications_count=15
    )
    assert approved is True
    assert dec == PolicyDecision.AUTO_APPLY

    # 3. 500 applications today -> STILL Approved
    approved, dec, reason = ApplicationPolicyEngine.evaluate(
        policy, job, match, daily_applications_count=500, source_daily_applications_count=200
    )
    assert approved is True
    assert dec == PolicyDecision.AUTO_APPLY

@pytest.mark.asyncio
async def test_explicit_limit_mode_still_enforced_if_configured():
    """Test that if candidate explicitly sets a daily limit, it is honored."""
    policy = ApplicationPolicy(
        auto_apply_enabled=True,
        minimum_match_score=80.0,
        daily_application_limit=15,
        per_source_daily_limit=5,
        allow_remote=True,
        allow_hybrid=True,
        allow_onsite=True
    )

    job = Job(
        id=uuid.uuid4(),
        title="Software Engineer",
        company_name="GoodTech",
        description="Software development",
        remote_type="REMOTE",
        deduplication_hash="test_hash_2",
        is_active=True
    )
    match = JobMatch(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        job_id=job.id,
        overall_score=85.0,
        eligibility_status="ELIGIBLE"
    )

    # Under limit
    approved, dec, _ = ApplicationPolicyEngine.evaluate(policy, job, match, daily_applications_count=14)
    assert approved is True

    # At or above limit
    approved, dec, reason = ApplicationPolicyEngine.evaluate(policy, job, match, daily_applications_count=15)
    assert approved is False
    assert dec == PolicyDecision.SKIP_DAILY_LIMIT
    assert "Daily application limit (15) reached" in reason

    # Source limit
    approved, dec, reason = ApplicationPolicyEngine.evaluate(policy, job, match, daily_applications_count=5, source_daily_applications_count=5)
    assert approved is False
    assert dec == PolicyDecision.SKIP_DAILY_LIMIT

@pytest.mark.asyncio
async def test_guardrails_remain_active_in_unlimited_mode():
    """Verify blocked companies, blocked keywords, and score thresholds still block even in unlimited mode."""
    policy = ApplicationPolicy(
        auto_apply_enabled=True,
        minimum_match_score=85.0,
        daily_application_limit=None,
        blocked_companies=["BadEmployer"],
        blocked_keywords=["unpaid internship"],
        allow_remote=True,
        allow_hybrid=True,
        allow_onsite=True
    )

    # Blocked company
    job_bad_company = Job(
        id=uuid.uuid4(),
        title="Dev",
        company_name="BadEmployer LLC",
        description="Coding",
        remote_type="REMOTE",
        deduplication_hash="hash_bc",
        is_active=True
    )
    match_ok = JobMatch(id=uuid.uuid4(), user_id=uuid.uuid4(), job_id=job_bad_company.id, overall_score=95.0, eligibility_status="ELIGIBLE")
    approved, dec, _ = ApplicationPolicyEngine.evaluate(policy, job_bad_company, match_ok)
    assert approved is False
    assert dec == PolicyDecision.SKIP_BLOCKED_COMPANY

    # Blocked keyword
    job_bad_kw = Job(
        id=uuid.uuid4(),
        title="Junior Dev",
        company_name="GoodCorp",
        description="This is an unpaid internship position.",
        remote_type="REMOTE",
        deduplication_hash="hash_kw",
        is_active=True
    )
    approved, dec, _ = ApplicationPolicyEngine.evaluate(policy, job_bad_kw, match_ok)
    assert approved is False
    assert dec == PolicyDecision.SKIP_BLOCKED_KEYWORD

    # Low score
    job_low_score = Job(
        id=uuid.uuid4(),
        title="Senior Architect",
        company_name="GoodCorp",
        description="Complex architecture",
        remote_type="REMOTE",
        deduplication_hash="hash_low",
        is_active=True
    )
    match_low = JobMatch(id=uuid.uuid4(), user_id=uuid.uuid4(), job_id=job_low_score.id, overall_score=65.0, eligibility_status="ELIGIBLE")
    approved, dec, _ = ApplicationPolicyEngine.evaluate(policy, job_low_score, match_low)
    assert approved is False
    assert dec == PolicyDecision.SKIP_LOW_MATCH

@pytest.mark.asyncio
async def test_service_get_or_create_defaults_to_210_capacity(async_session: AsyncSession):
    """Test ApplicationService creates a policy with 210 daily limit (30/source across 7 sources)."""
    user = User(
        id=uuid.uuid4(),
        email="capacity_test@example.com",
        hashed_password="hashedpassword",
        full_name="Capacity User",
        is_active=True,
        role="CANDIDATE"
    )
    async_session.add(user)
    await async_session.commit()

    service = ApplicationService(async_session)
    policy = await service.get_or_create_policy(user.id)

    assert policy.daily_application_limit == 210
    assert policy.per_source_daily_limit == 30

    # Check status endpoint output
    status = await service.get_auto_apply_status(user.id)
    assert status.daily_application_limit == 210
    assert status.daily_limit_enabled is True
    assert status.daily_limit_label == "210/day"
    assert status.remaining_daily_quota == 210

@pytest.mark.asyncio
async def test_service_policy_update_toggle_unlimited(async_session: AsyncSession):
    """Test updating policy to set a limit and clearing it back to None (unlimited)."""
    user = User(
        id=uuid.uuid4(),
        email="toggle_test@example.com",
        hashed_password="hashedpassword",
        full_name="Toggle User",
        is_active=True,
        role="CANDIDATE"
    )
    async_session.add(user)
    await async_session.commit()

    service = ApplicationService(async_session)

    # 1. Update to limit = 25
    updated = await service.update_policy(user.id, ApplicationPolicyUpdate(daily_application_limit=25))
    assert updated.daily_application_limit == 25
    status = await service.get_auto_apply_status(user.id)
    assert status.daily_application_limit == 25
    assert status.daily_limit_enabled is True
    assert status.daily_limit_label == "25/day"
    assert status.remaining_daily_quota == 25

    # 2. Update to limit = None (unlimited)
    updated_unlimited = await service.update_policy(user.id, ApplicationPolicyUpdate(daily_application_limit=None))
    assert updated_unlimited.daily_application_limit is None
    status2 = await service.get_auto_apply_status(user.id)
    assert status2.daily_application_limit is None
    assert status2.daily_limit_enabled is False
    assert status2.daily_limit_label == "Unlimited"
    assert status2.remaining_daily_quota is None

@pytest.mark.asyncio
async def test_chatbot_tools_render_unlimited(async_session: AsyncSession):
    """Verify chatbot tools output 'Unlimited' when daily limit is set to None."""
    user = User(
        id=uuid.uuid4(),
        email="chat_unlimited@example.com",
        hashed_password="hashedpassword",
        full_name="Chat Unlimited User",
        is_active=True,
        role="CANDIDATE"
    )
    async_session.add(user)
    await async_session.commit()

    service = ApplicationService(async_session)
    await service.get_or_create_policy(user.id)
    await service.update_policy(user.id, ApplicationPolicyUpdate(daily_application_limit=None))

    # Test status tool
    status_tool = GetAutoApplyStatusTool()
    res = await status_tool.run(user.id, async_session, {})
    assert res.success is True
    assert "Daily Limit: Unlimited" in res.summary
    assert "Remaining Quota: Unlimited" in res.summary

    # Test policy tool
    policy_tool = GetAutoApplyPolicyTool()
    res_pol = await policy_tool.run(user.id, async_session, {})
    assert res_pol.success is True
    assert "Daily Limit=Unlimited" in res_pol.summary
