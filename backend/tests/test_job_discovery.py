import pytest
import uuid
from app.modules.jobs.connectors.base import JobCapability, NormalizedJob
from app.modules.jobs.connectors.adapters import (
    get_all_connectors,
    get_connector_by_slug,
    GreenhouseConnector,
    LeverConnector,
    AuthorizedJobAPIConnector,
    LinkedInConnector,
    IndeedConnector,
    NaukriConnector,
    UnstopConnector,
    InternshalaConnector,
    WellfoundConnector,
    CompanyCareerPagesConnector,
)
from app.modules.jobs.service import JobService
from app.database.models.job import Job

# 1. Test All 10 Connectors Capability Reporting
def test_all_connector_capabilities():
    connectors = get_all_connectors()
    assert len(connectors) == 10

    expected_capabilities = {
        "greenhouse": JobCapability.AUTO_APPLY,
        "lever": JobCapability.AUTO_APPLY,
        "authorized_api": JobCapability.AUTO_APPLY,
        "linkedin": JobCapability.JOB_DISCOVERY,
        "indeed": JobCapability.EXTERNAL_APPLICATION,
        "naukri": JobCapability.EXTERNAL_APPLICATION,
        "unstop": JobCapability.JOB_DISCOVERY,
        "internshala": JobCapability.JOB_DISCOVERY,
        "wellfound": JobCapability.JOB_DISCOVERY,
        "career_pages": JobCapability.EXTERNAL_APPLICATION,
    }

    for conn in connectors:
        assert conn.slug in expected_capabilities
        assert conn.get_application_capabilities() == expected_capabilities[conn.slug]
        status = conn.get_source_status()
        assert status["status"] == "HEALTHY"

# 2. Test Job Normalization
def test_job_normalization():
    conn = GreenhouseConnector()
    raw_payload = {
        "id": 99281,
        "company_name": "Stripe",
        "title": "Senior Backend Infrastructure Engineer",
        "content": "Work on Stripe's payment transaction processing engine.",
        "requirements": ["5+ years experience in Python and PostgreSQL", "Async concurrency"],
        "skills": ["Python", "FastAPI", "PostgreSQL", "Kafka"],
        "experience_level": "SENIOR",
        "location": {"name": "Remote (US)"},
        "remote_type": "REMOTE",
        "salary_min": 190000,
        "salary_max": 240000,
        "currency": "USD",
        "absolute_url": "https://boards.greenhouse.io/stripe/jobs/99281"
    }

    norm = conn.normalize_job(raw_payload)
    assert isinstance(norm, NormalizedJob)
    assert norm.source == "greenhouse"
    assert norm.external_job_id == "99281"
    assert norm.company == "Stripe"
    assert norm.title == "Senior Backend Infrastructure Engineer"
    assert "Python" in norm.skills
    assert norm.remote_type == "REMOTE"
    assert norm.salary_min == 190000
    assert norm.application_url == "https://boards.greenhouse.io/stripe/jobs/99281"

# 3. Test Deduplication Guard
@pytest.mark.asyncio
async def test_job_deduplication_guard(async_session):
    service = JobService(async_session)

    norm_job = NormalizedJob(
        source="greenhouse",
        external_job_id="ext-dedup-101",
        company="Datadog",
        title="Senior Platform Engineer",
        description="Build scalable telemetry intake systems with Python.",
        requirements=["Distributed systems", "Python"],
        skills=["Python", "FastAPI", "PostgreSQL"],
        experience_required="SENIOR",
        location="Remote",
        remote_type="REMOTE",
        salary_min=180000,
        salary_max=220000,
        currency="USD",
        employment_type="FULL_TIME",
        application_url="https://jobs.example.com/ext-dedup-101"
    )

    # Ingest 1st time
    job1 = await service.ingest_normalized_job(norm_job)
    assert job1.id is not None

    # Ingest 2nd time with exact same company + title + external_id
    job2 = await service.ingest_normalized_job(norm_job)
    assert job2.id == job1.id  # Same record, not duplicated!

    # Verify count in database
    from sqlalchemy import select, func
    res = await async_session.execute(select(func.count(Job.id)))
    count = res.scalar()
    assert count == 1

# 4. Test Multi-Criteria Search Filtering
@pytest.mark.asyncio
async def test_multi_criteria_search(async_session):
    service = JobService(async_session)

    # Ingest 3 distinct jobs
    jobs = [
        NormalizedJob(
            source="lever",
            external_job_id="j1",
            company="Anthropic",
            title="Senior AI Systems Engineer",
            description="LLM inference scaling and agentic systems.",
            skills=["Python", "AI/LLM Architecture", "PostgreSQL"],
            experience_required="SENIOR",
            location="San Francisco, CA",
            remote_type="HYBRID",
            salary_min=200000,
            salary_max=260000,
            employment_type="FULL_TIME",
            application_url="https://jobs.lever.co/anthropic/j1"
        ),
        NormalizedJob(
            source="naukri",
            external_job_id="j2",
            company="Flipkart",
            title="Junior Backend Developer",
            description="E-commerce catalog pipelines.",
            skills=["Java", "MySQL"],
            experience_required="ENTRY",
            location="Bengaluru, India",
            remote_type="ONSITE",
            salary_min=80000,
            salary_max=110000,
            employment_type="FULL_TIME",
            application_url="https://naukri.com/j2"
        ),
        NormalizedJob(
            source="wellfound",
            external_job_id="j3",
            company="Modal Labs",
            title="Staff Cloud Engineer",
            description="Serverless container runtimes with Python and Docker.",
            skills=["Python", "Docker", "Kubernetes"],
            experience_required="LEAD",
            location="Remote",
            remote_type="REMOTE",
            salary_min=190000,
            salary_max=250000,
            employment_type="FULL_TIME",
            application_url="https://wellfound.com/j3"
        )
    ]

    for j in jobs:
        await service.ingest_normalized_job(j)

    # Filter by Keyword "Anthropic"
    results, total = await service.list_jobs_advanced(query="Anthropic")
    assert total == 1
    assert results[0].company_name == "Anthropic"

    # Filter by Remote Type "REMOTE"
    results, total = await service.list_jobs_advanced(remote_type="REMOTE")
    assert total == 1
    assert results[0].company_name == "Modal Labs"

    # Filter by Min Salary $180,000
    results, total = await service.list_jobs_advanced(min_salary=180000)
    assert total == 2

    # Filter by Experience "ENTRY"
    results, total = await service.list_jobs_advanced(experience_level="ENTRY")
    assert total == 1
    assert results[0].company_name == "Flipkart"

# 5. Test Discovery Sync Across All Connectors
@pytest.mark.asyncio
async def test_source_discovery_sync(async_session):
    service = JobService(async_session)
    sync_result = await service.sync_all_discovery_sources()

    assert sync_result["total_connectors_synced"] == 10
    assert sync_result["total_discovered"] >= 10
    assert sync_result["new_jobs_ingested"] >= 10
