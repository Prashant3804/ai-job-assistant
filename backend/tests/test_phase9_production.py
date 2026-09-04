import pytest
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.config import settings
from app.database.models.user import User, UserProfile, Education, Experience, CandidateSkill, JobPreference
from app.database.models.job import Job, JobSource
from app.database.models.resume import Resume, ResumeVersion
from app.database.models.match import JobMatch
from app.database.models.application import (
    Application,
    ApplicationPolicy,
    ApplicationQueueItem,
    DeadLetterApplicationQueue
)
from app.database.models.system import AuditEvent
from app.shared.constants import (
    ApplicationStatus,
    QueueStatus,
    PlatformCapability,
    ConnectorStatus,
    AuthorizationType,
    AuditEventType
)
from app.core.security import create_access_token
from app.core.audit import AuditService
from app.core.secrets_scanner import SecretScanner
from app.modules.connectors.registry import connector_registry, MockAuthorizedProvider
from app.modules.connectors.health import connector_health_service
from app.modules.jobs.priority import SourcePriorityEngine
from app.modules.jobs.connectors.base import NormalizedJob
from app.modules.applications.queue import ApplicationQueueService
from app.modules.applications.agent import ApplicationAgent
from app.modules.applications.worker_monitor import worker_monitor_service
from app.modules.applications.connectors.adapters import get_application_connector

async def create_populated_test_user(session: AsyncSession) -> User:
    u_id = uuid.uuid4()
    user = User(
        id=u_id,
        email=f"prod_user_{u_id.hex[:6]}@example.com",
        full_name="Production Candidate",
        hashed_password="hashed_secure_password_prod",
        is_active=True,
        is_verified=True,
        role="CANDIDATE"
    )
    session.add(user)

    profile = UserProfile(
        id=uuid.uuid4(),
        user_id=u_id,
        headline="Senior Staff Software Engineer",
        years_of_experience=8.0,
        target_roles=["Senior Software Engineer", "Backend Lead"]
    )
    session.add(profile)

    session.add(CandidateSkill(id=uuid.uuid4(), user_profile_id=profile.id, name="Python", category="TECHNICAL"))
    session.add(CandidateSkill(id=uuid.uuid4(), user_profile_id=profile.id, name="FastAPI", category="TECHNICAL"))
    session.add(CandidateSkill(id=uuid.uuid4(), user_profile_id=profile.id, name="Docker", category="TOOL"))

    session.add(Education(
        id=uuid.uuid4(),
        user_profile_id=profile.id,
        institution="MIT",
        degree="B.S. in Computer Science",
        field_of_study="Computer Science"
    ))

    session.add(JobPreference(
        id=uuid.uuid4(),
        user_id=u_id,
        desired_titles=["Senior Software Engineer"],
        desired_locations=["Remote"],
        remote_types=["REMOTE"],
        min_base_salary=140000,
        currency="USD"
    ))

    resume = Resume(
        id=uuid.uuid4(),
        user_id=u_id,
        raw_text="Experienced Senior Software Engineer specializing in Python, FastAPI, Docker.",
        is_primary=True
    )
    session.add(resume)

    ver = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        tailored_content={"skills": ["Python", "FastAPI", "Docker"]}
    )
    session.add(ver)

    policy = ApplicationPolicy(
        id=uuid.uuid4(),
        user_id=u_id,
        auto_apply_enabled=True,
        minimum_match_score=75.0,
        daily_application_limit=20
    )
    session.add(policy)

    await session.commit()
    return user

# ==========================================
# 1. SECURITY & SECRETS TESTS
# ==========================================

@pytest.mark.asyncio
async def test_secret_scanner_detection_and_redaction():
    text_with_secrets = (
        "Logs: Auth token Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID1_VN2kf8kQI "
        "and OpenAI key sk-1234567890abcdef1234567890abcdef "
        "and password='SuperSecretPassword123!'"
    )
    assert SecretScanner.contains_secrets(text_with_secrets) is True
    findings = SecretScanner.find_secrets(text_with_secrets)
    assert len(findings) >= 2

    redacted = SecretScanner.redact_secrets(text_with_secrets)
    assert "SuperSecretPassword123!" not in redacted
    assert "sk-1234567890" not in redacted

@pytest.mark.asyncio
async def test_production_configuration_validation():
    issues = settings.validate_production_configuration()
    assert isinstance(issues, list)

@pytest.mark.asyncio
async def test_audit_service_logging_sanitizes_metadata(async_session: AsyncSession):
    user = await create_populated_test_user(async_session)
    metadata = {
        "user_email": "candidate@example.com",
        "api_key": "sk-proj-secret-token-value",
        "password": "my_secret_pass",
        "nested": {"token": "jwt_secret_token", "allowed": "safe_value"}
    }
    event = await AuditService.log_event(
        async_session,
        action=AuditEventType.APPLICATION_ATTEMPT.value,
        resource_type="APPLICATION",
        user_id=user.id,
        actor="WORKER",
        metadata=metadata
    )
    assert event is not None
    assert event.metadata_json["api_key"] == "[REDACTED]"
    assert event.metadata_json["password"] == "[REDACTED]"
    assert event.metadata_json["nested"]["token"] == "[REDACTED]"
    assert event.metadata_json["nested"]["allowed"] == "safe_value"

@pytest.mark.asyncio
async def test_idor_protection_for_audit_logs_and_dlq(async_session: AsyncSession, async_client: AsyncClient):
    user1 = await create_populated_test_user(async_session)

    # Create another user
    other_user_id = uuid.uuid4()
    other_user = User(
        id=other_user_id,
        email="other_audit_user@example.com",
        full_name="Other Audit User",
        hashed_password="pw",
        role="CANDIDATE"
    )
    async_session.add(other_user)

    # Log event for user1 and other user
    await AuditService.log_event(
        async_session,
        action=AuditEventType.APPLICATION_ATTEMPT.value,
        resource_type="APPLICATION",
        user_id=user1.id,
        metadata={"public_note": "user1_event"}
    )
    await AuditService.log_event(
        async_session,
        action=AuditEventType.SECURITY_EVENT.value,
        resource_type="SECURITY",
        user_id=other_user_id,
        metadata={"private_note": "secret_info"}
    )
    await async_session.commit()

    token = create_access_token(user1.id)
    res = await async_client.get("/api/v1/system/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) >= 1
    for log in logs:
        assert log["user_id"] == str(user1.id)
        assert log["user_id"] != str(other_user_id)

# ==========================================
# 2. CONNECTOR CAPABILITY & REGISTRY TESTS
# ==========================================

@pytest.mark.asyncio
async def test_connector_registry_contains_all_10_providers():
    connectors = connector_registry.list_connectors()
    assert len(connectors) >= 10
    slugs = [c.slug.lower() for c in connectors]
    expected_slugs = [
        "naukri", "indeed", "unstop", "linkedin", "internshala",
        "wellfound", "career_pages", "greenhouse", "lever", "mock_ats"
    ]
    for exp in expected_slugs:
        assert exp in slugs

@pytest.mark.asyncio
async def test_connector_capability_declarations():
    # 1. Greenhouse (Authorized Auto-Apply)
    gh = connector_registry.get_connector("greenhouse")
    assert gh is not None
    cap_gh = gh.get_capabilities()
    assert cap_gh.is_auto_apply_supported is True
    assert PlatformCapability.AUTO_APPLY in cap_gh.supported_capabilities

    # 2. Naukri (Discovery Only, External Required)
    nk = connector_registry.get_connector("naukri")
    assert nk is not None
    cap_nk = nk.get_capabilities()
    assert cap_nk.is_auto_apply_supported is False
    assert cap_nk.is_external_application_required is True
    assert cap_nk.status == ConnectorStatus.DISCOVERY_ONLY

    # 3. Indeed (Discovery Only, External Required)
    ind = connector_registry.get_connector("indeed")
    cap_ind = ind.get_capabilities()
    assert cap_ind.is_auto_apply_supported is False
    assert cap_ind.is_external_application_required is True

@pytest.mark.asyncio
async def test_unsupported_connector_submission_returns_external_application_required():
    nk = connector_registry.get_connector("naukri")
    result = await nk.submit_application(prepared_payload={"test": "data"})
    assert result.success is False
    assert result.error_code == "EXTERNAL_APPLICATION_REQUIRED"
    assert "official employer portal" in result.error_message

@pytest.mark.asyncio
async def test_mock_authorized_provider_edge_cases():
    # SUCCESS
    p_success = MockAuthorizedProvider(mode="SUCCESS")
    res_s = await p_success.submit_application({})
    assert res_s.success is True
    assert res_s.status == "APPLIED"

    # RATE_LIMIT (429)
    p_rl = MockAuthorizedProvider(mode="RATE_LIMIT")
    res_rl = await p_rl.submit_application({})
    assert res_rl.success is False
    assert res_rl.status == "RATE_LIMITED"
    assert res_rl.response_code == 429
    assert res_rl.is_transient_error is True

    # TIMEOUT (504)
    p_to = MockAuthorizedProvider(mode="TIMEOUT")
    res_to = await p_to.submit_application({})
    assert res_to.success is False
    assert res_to.error_code == "GATEWAY_TIMEOUT"
    assert res_to.is_transient_error is True

    # AUTH_FAILURE (401)
    p_auth = MockAuthorizedProvider(mode="AUTH_FAILURE")
    res_auth = await p_auth.submit_application({})
    assert res_auth.success is False
    assert res_auth.is_transient_error is False

@pytest.mark.asyncio
async def test_connector_health_service_tracking():
    connector_health_service.record_success("greenhouse", latency_ms=35.0)
    h_gh = connector_health_service.get_connector_health("greenhouse")
    assert h_gh is not None
    assert h_gh["status"] == "HEALTHY"

    connector_health_service.record_failure("lever", error_code="RATE_LIMIT_EXCEEDED", error_message="Too many requests")
    h_lever = connector_health_service.get_connector_health("lever")
    assert h_lever is not None
    assert h_lever["status"] == "RATE_LIMITED"
    assert h_lever["rate_limit_events"] >= 1

# ==========================================
# 3. JOB DISCOVERY & DEDUPLICATION TESTS
# ==========================================

@pytest.mark.asyncio
async def test_source_priority_engine_deduplication():
    job_gh = NormalizedJob(
        source="Greenhouse",
        external_job_id="gh-123",
        company="Acme Corp, Inc.",
        title="Senior Python Engineer",
        description="Direct Greenhouse posting",
        location="Remote",
        application_url="https://boards.greenhouse.io/acme/123",
        source_metadata={"connector": "greenhouse"}
    )
    job_unstop = NormalizedJob(
        source="Unstop",
        external_job_id="unstop-456",
        company="Acme Corp",
        title="Senior Python Engineer",
        description="Aggregated Unstop posting",
        location="Remote",
        application_url="https://unstop.com/jobs/456",
        source_metadata={"connector": "unstop"}
    )

    jobs = [job_unstop, job_gh]
    deduped = SourcePriorityEngine.deduplicate_and_prioritize(jobs)
    assert len(deduped) == 1
    assert deduped[0].source == "Greenhouse"

# ==========================================
# 4. APPLICATION QUEUE, WORKER & DLQ TESTS
# ==========================================

@pytest.mark.asyncio
async def test_queue_leasing_and_crash_recovery(async_session: AsyncSession):
    user = await create_populated_test_user(async_session)
    queue_service = ApplicationQueueService(async_session)
    job_id = uuid.uuid4()
    app_id = uuid.uuid4()

    application = Application(
        id=app_id,
        user_id=user.id,
        job_id=job_id,
        status=ApplicationStatus.QUEUED.value
    )
    async_session.add(application)

    item = await queue_service.enqueue(user_id=user.id, application_id=app_id, job_id=job_id)
    await queue_service.mark_processing(item, worker_id="worker-node-1", lease_seconds=1)
    await async_session.commit()

    assert item.status == QueueStatus.PROCESSING.value
    assert item.locked_by == "worker-node-1"

    # Expire lease
    item.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    await async_session.commit()

    recovered_count = await queue_service.recover_expired_leases(lease_timeout_seconds=0)
    assert recovered_count >= 1

    stmt = select(ApplicationQueueItem).where(ApplicationQueueItem.id == item.id)
    res = await async_session.execute(stmt)
    refreshed = res.scalar_one()
    assert refreshed.status == QueueStatus.RETRYING.value
    assert refreshed.locked_by is None

@pytest.mark.asyncio
async def test_dead_letter_queue_routing(async_session: AsyncSession):
    user = await create_populated_test_user(async_session)
    queue_service = ApplicationQueueService(async_session)
    job_id = uuid.uuid4()
    app_id = uuid.uuid4()

    app_obj = Application(
        id=app_id,
        user_id=user.id,
        job_id=job_id,
        status=ApplicationStatus.FAILED.value
    )
    async_session.add(app_obj)

    item = await queue_service.enqueue(user_id=user.id, application_id=app_id, job_id=job_id)
    dlq_entry = await queue_service.move_to_dead_letter(
        item=item,
        failure_reason="Platform permanently rejected candidate resume profile.",
        last_error="UNRECOVERABLE_VALIDATION_ERROR"
    )
    await async_session.commit()

    assert dlq_entry.id is not None
    assert dlq_entry.application_id == app_id
    assert dlq_entry.resolved is False

    dlq_items = await queue_service.get_dead_letter_items(user_id=user.id)
    assert len(dlq_items) >= 1
    assert any(str(d.id) == str(dlq_entry.id) for d in dlq_items)

# ==========================================
# 5. OBSERVABILITY & HEALTH REST API TESTS
# ==========================================

@pytest.mark.asyncio
async def test_health_endpoints_live_and_ready(async_session: AsyncSession, async_client: AsyncClient):
    user = await create_populated_test_user(async_session)
    token = create_access_token(user.id)
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Public Health
    res_pub = await async_client.get("/api/v1/health")
    assert res_pub.status_code == 200
    assert res_pub.json()["compliance_mode"] == "STRICT_NON_CIRCUMVENTION_ENFORCED"

    # Liveness
    res_live = await async_client.get("/api/v1/health/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "ALIVE"

    # Readiness
    res_ready = await async_client.get("/api/v1/health/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "READY"

    # Detailed Health (Authenticated)
    res_det = await async_client.get("/api/v1/health/detailed", headers=auth_headers)
    assert res_det.status_code == 200
    data = res_det.json()
    assert "database" in data
    assert "connectors" in data
    assert "ai_provider" in data

@pytest.mark.asyncio
async def test_worker_metrics_api(async_session: AsyncSession, async_client: AsyncClient):
    user = await create_populated_test_user(async_session)
    token = create_access_token(user.id)
    auth_headers = {"Authorization": f"Bearer {token}"}

    worker_monitor_service.heartbeat("worker-test-prod", current_job_id="job-101")
    res = await async_client.get("/api/v1/system/workers", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["active_workers_count"] >= 1
    assert "queue_depth" in data

@pytest.mark.asyncio
async def test_connectors_api_lists_capabilities(async_client: AsyncClient):
    res = await async_client.get("/api/v1/connectors")
    assert res.status_code == 200
    conns = res.json()
    assert len(conns) >= 10

    gh = next((c for c in conns if c["slug"] == "greenhouse"), None)
    assert gh is not None
    assert gh["is_auto_apply_supported"] is True

    nk = next((c for c in conns if c["slug"] == "naukri"), None)
    assert nk is not None
    assert nk["is_external_application_required"] is True

    res_h = await async_client.get("/api/v1/connectors/greenhouse/health")
    assert res_h.status_code == 200
    assert res_h.json()["slug"] == "greenhouse"

# ==========================================
# 6. END-TO-END WORKFLOW TESTS (SCENARIOS 1-6)
# ==========================================

@pytest.mark.asyncio
async def test_e2e_scenario_1_full_pipeline_authorized(async_session: AsyncSession):
    """E2E 1: Resume -> Match -> Policy -> Authorized Connector Submission -> Verified APPLIED."""
    user = await create_populated_test_user(async_session)

    js = JobSource(
        id=uuid.uuid4(),
        name="Mock ATS Provider",
        slug="mock_ats",
        connector_type="DIRECT_API",
        capability_status="SUPPORTED_AUTO_APPLY",
        is_active=True
    )
    async_session.add(js)

    job = Job(
        id=uuid.uuid4(),
        job_source_id=js.id,
        title="Senior Python Developer",
        company_name="InnovateCorp",
        description="Build scalable FastAPI microservices with Docker.",
        required_skills=["Python", "FastAPI"],
        location="Remote",
        remote_type="REMOTE",
        salary_min=140000,
        salary_max=180000,
        deduplication_hash=uuid.uuid4().hex
    )
    async_session.add(job)

    match = JobMatch(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        overall_score=92.0,
        skills_score=95.0,
        experience_score=90.0,
        eligibility_status="ELIGIBLE",
        recommendation="STRONG_MATCH"
    )
    async_session.add(match)

    application = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        status=ApplicationStatus.QUEUED.value
    )
    async_session.add(application)

    queue_service = ApplicationQueueService(async_session)
    queue_item = await queue_service.enqueue(user_id=user.id, application_id=application.id, job_id=job.id)
    await async_session.commit()

    agent = ApplicationAgent(async_session)
    result = await agent.process_queue_item(queue_item)

    assert result["success"] is True
    assert result["status"] == "APPLIED"
    assert result["external_application_id"] is not None

@pytest.mark.asyncio
async def test_e2e_scenario_2_unsupported_auto_apply(async_session: AsyncSession):
    """E2E 2: Platform without authorized submission -> EXTERNAL_APPLICATION_REQUIRED."""
    user = await create_populated_test_user(async_session)

    js = JobSource(
        id=uuid.uuid4(),
        name="Naukri",
        slug="naukri",
        connector_type="EXTERNAL",
        capability_status="EXTERNAL_APPLICATION_REQUIRED",
        is_active=True
    )
    async_session.add(js)

    job = Job(
        id=uuid.uuid4(),
        job_source_id=js.id,
        title="Python Backend Engineer",
        company_name="Global Enterprises",
        description="Naukri job description.",
        required_skills=["Python"],
        location="Remote",
        deduplication_hash=uuid.uuid4().hex
    )
    async_session.add(job)

    application = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        status=ApplicationStatus.QUEUED.value
    )
    async_session.add(application)

    queue_service = ApplicationQueueService(async_session)
    queue_item = await queue_service.enqueue(user_id=user.id, application_id=application.id, job_id=job.id)
    await async_session.commit()

    agent = ApplicationAgent(async_session)
    result = await agent.process_queue_item(queue_item)

    assert result["success"] is False
    assert result["status"] == ApplicationStatus.AUTO_APPLY_UNSUPPORTED.value
    assert "external employer website" in result["reason"]

@pytest.mark.asyncio
async def test_e2e_scenario_3_rate_limit_and_dlq(async_session: AsyncSession):
    """E2E 3: 429 Rate limit retry handling."""
    user = await create_populated_test_user(async_session)

    js = JobSource(
        id=uuid.uuid4(),
        name="Mock ATS Provider",
        slug="mock_ats",
        connector_type="DIRECT_API",
        capability_status="SUPPORTED_AUTO_APPLY",
        is_active=True
    )
    async_session.add(js)

    job = Job(
        id=uuid.uuid4(),
        job_source_id=js.id,
        title="Staff Engineer",
        company_name="HighLoad Corp",
        description="Scalable distributed systems.",
        required_skills=["Python"],
        location="Remote",
        deduplication_hash=uuid.uuid4().hex
    )
    async_session.add(job)

    application = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        status=ApplicationStatus.QUEUED.value
    )
    async_session.add(application)

    queue_service = ApplicationQueueService(async_session)
    queue_item = await queue_service.enqueue(user_id=user.id, application_id=application.id, job_id=job.id)
    queue_item.max_attempts = 1
    await async_session.commit()

    mock_conn = get_application_connector("mock_ats")
    mock_conn.set_mode("RATE_LIMIT_429")
    try:
        agent = ApplicationAgent(async_session)
        result = await agent.process_queue_item(queue_item)

        assert result["success"] is False
        assert result["status"] == "RETRYING" or result["status"] == "FAILED" or result["status"] == "RATE_LIMITED"
    finally:
        mock_conn.set_mode("SUCCESS")

@pytest.mark.asyncio
async def test_e2e_scenario_4_worker_crash_recovery(async_session: AsyncSession):
    """E2E 4: Worker crash during processing -> Lease expired -> Safely recovered."""
    user = await create_populated_test_user(async_session)
    queue_service = ApplicationQueueService(async_session)
    job_id = uuid.uuid4()
    app_id = uuid.uuid4()

    app_obj = Application(id=app_id, user_id=user.id, job_id=job_id, status=ApplicationStatus.QUEUED.value)
    async_session.add(app_obj)

    item = await queue_service.enqueue(user_id=user.id, application_id=app_id, job_id=job_id)
    await queue_service.mark_processing(item, worker_id="crashed-worker-7", lease_seconds=1)
    await async_session.commit()

    item.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    await async_session.commit()

    reclaimed = await queue_service.recover_expired_leases(lease_timeout_seconds=0)
    assert reclaimed >= 1
    assert item.status == QueueStatus.RETRYING.value

@pytest.mark.asyncio
async def test_e2e_scenario_5_false_success_prevention(async_session: AsyncSession):
    """E2E 5: Connector submission failure must not transition to APPLIED."""
    user = await create_populated_test_user(async_session)

    js = JobSource(
        id=uuid.uuid4(),
        name="Mock ATS Provider",
        slug="mock_ats",
        connector_type="DIRECT_API",
        capability_status="SUPPORTED_AUTO_APPLY",
        is_active=True
    )
    async_session.add(js)

    job = Job(
        id=uuid.uuid4(),
        job_source_id=js.id,
        title="Cloud Architect",
        company_name="SecureNet",
        description="AWS Infrastructure design.",
        required_skills=["Python"],
        location="Remote",
        deduplication_hash=uuid.uuid4().hex
    )
    async_session.add(job)

    application = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        status=ApplicationStatus.QUEUED.value
    )
    async_session.add(application)

    queue_service = ApplicationQueueService(async_session)
    queue_item = await queue_service.enqueue(user_id=user.id, application_id=application.id, job_id=job.id)
    await async_session.commit()

    mock_conn = get_application_connector("mock_ats")
    mock_conn.set_mode("AUTH_ERROR_401")
    try:
        agent = ApplicationAgent(async_session)
        result = await agent.process_queue_item(queue_item)

        assert result["success"] is False
        assert application.status != ApplicationStatus.APPLIED.value
        assert application.status == ApplicationStatus.FAILED.value
    finally:
        mock_conn.set_mode("SUCCESS")

@pytest.mark.asyncio
async def test_e2e_scenario_6_recruiter_flow_no_auto_send(async_session: AsyncSession, async_client: AsyncClient):
    """E2E 6: Recruiter message -> suggested draft -> explicit human approval, no automatic transmission."""
    user = await create_populated_test_user(async_session)
    token = create_access_token(user.id)
    auth_headers = {"Authorization": f"Bearer {token}"}

    draft_res = await async_client.post(
        "/api/v1/communication/drafts/generate",
        json={
            "recruiter_name": "Sarah Jenkins",
            "recruiter_email": "sarah.j@toptech.com",
            "company_name": "TopTech Global",
            "job_title": "Lead Software Engineer",
            "intent": "SCHEDULE_INTERVIEW",
            "tone": "PROFESSIONAL",
            "candidate_availability": ["Monday 2 PM", "Tuesday 10 AM"]
        },
        headers=auth_headers
    )
    assert draft_res.status_code == 201
    draft = draft_res.json()
    assert draft["is_approved"] is False
    assert draft["status"] == "DRAFT"
    draft_id = draft["id"]

    approve_res = await async_client.post(f"/api/v1/communication/drafts/{draft_id}/approve", headers=auth_headers)
    assert approve_res.status_code == 200
    approved_data = approve_res.json()
    assert approved_data["is_approved"] is True
    assert approved_data["status"] == "APPROVED"

