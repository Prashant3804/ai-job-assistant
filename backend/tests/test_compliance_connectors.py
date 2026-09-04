import pytest
import uuid
from app.database.models.job import Job, JobSource
from app.modules.applications.service import ApplicationService
from app.modules.integrations.service import ConnectorComplianceService
from app.shared.schemas import ApplicationCreate
from app.shared.constants import ConnectorCapabilityStatus, SubmissionMethod
from app.core.exceptions import UnauthorizedIntegrationError, DuplicateEntityError

@pytest.mark.asyncio
async def test_safe_connector_compliance_blocks_unauthorized_auto_apply(async_session):
    # Setup job source with EXTERNAL_APPLICATION_REQUIRED
    source = JobSource(
        id=uuid.uuid4(),
        name="External Career Site",
        slug="external_site",
        capability_status=ConnectorCapabilityStatus.EXTERNAL_APPLICATION_REQUIRED.value,
        is_active=True
    )
    async_session.add(source)
    await async_session.flush()

    job = Job(
        id=uuid.uuid4(),
        job_source_id=source.id,
        title="Backend Engineer",
        company_name="Acme Corp",
        description="Engineering role",
        deduplication_hash="dedup-1234",
        is_active=True
    )
    async_session.add(job)
    await async_session.commit()

    compliance = ConnectorComplianceService(async_session)
    with pytest.raises(UnauthorizedIntegrationError):
        await compliance.validate_application_submission_safety(source.id)

    # Attempting to submit application via DIRECT_API must be blocked by ApplicationService
    app_service = ApplicationService(async_session)
    user_id = uuid.uuid4()
    with pytest.raises(UnauthorizedIntegrationError):
        await app_service.create_application(
            user_id=user_id,
            payload=ApplicationCreate(
                job_id=job.id,
                submission_method=SubmissionMethod.DIRECT_API.value
            )
        )

@pytest.mark.asyncio
async def test_application_duplicate_guard(async_session):
    source = JobSource(
        id=uuid.uuid4(),
        name="Direct API Source",
        slug="direct_api",
        capability_status=ConnectorCapabilityStatus.SUPPORTED_AUTO_APPLY.value,
        is_active=True
    )
    job = Job(
        id=uuid.uuid4(),
        job_source_id=source.id,
        title="Senior Python Engineer",
        company_name="Tech Co",
        description="Great role",
        deduplication_hash="dedup-5678",
        is_active=True
    )
    async_session.add_all([source, job])
    await async_session.commit()

    app_service = ApplicationService(async_session)
    user_id = uuid.uuid4()

    # 1. First application succeeds
    app1 = await app_service.create_application(
        user_id=user_id,
        payload=ApplicationCreate(
            job_id=job.id,
            submission_method=SubmissionMethod.MANUAL.value,
            notes="First attempt"
        )
    )
    assert app1 is not None
    assert len(app1.events) >= 1

    # 2. Second application for same (user_id, job_id) is blocked by duplicate guard
    with pytest.raises(DuplicateEntityError):
        await app_service.create_application(
            user_id=user_id,
            payload=ApplicationCreate(
                job_id=job.id,
                submission_method=SubmissionMethod.MANUAL.value
            )
        )
