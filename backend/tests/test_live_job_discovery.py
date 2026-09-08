import pytest
import uuid
import httpx
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.modules.jobs.connectors.base import NormalizedJob
from app.modules.jobs.discovery.base import BaseDiscoveryProvider
from app.modules.jobs.discovery.greenhouse import GreenhouseDiscoveryProvider
from app.modules.jobs.discovery.lever import LeverDiscoveryProvider
from app.modules.jobs.discovery.public_feeds import RemotiveDiscoveryProvider, ArbeitnowDiscoveryProvider
from app.modules.jobs.discovery.aggregators import JSearchAggregatorProvider
from app.modules.jobs.discovery.orchestrator import JobDiscoveryOrchestrator
from app.modules.jobs.service import JobService
from app.database.models.job import Job, JobSource

# -------------------------------------------------------------
# 1. Provider Tests: Success, Empty, Malformed, Timeout, 429, 5xx
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_provider_success_response():
    provider = GreenhouseDiscoveryProvider(boards=["cloudflare"])
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "jobs": [
            {
                "id": 12345,
                "title": "Staff Backend Engineer",
                "location": {"name": "Bengaluru, India"},
                "absolute_url": "https://boards.greenhouse.io/cloudflare/jobs/12345",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "departments": [{"name": "Infrastructure"}]
            }
        ]
    }
    with patch.object(provider, "_safe_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        jobs = await provider.discover_jobs(limit=10)
        assert len(jobs) == 1
        assert jobs[0].company == "Cloudflare"
        assert jobs[0].title == "Staff Backend Engineer"
        assert jobs[0].source == "career_pages"
        assert jobs[0].discovery_provider == "greenhouse_public_board"

@pytest.mark.asyncio
async def test_provider_empty_response():
    provider = LeverDiscoveryProvider(companies=["spotify"])
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []
    with patch.object(provider, "_safe_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        jobs = await provider.discover_jobs(limit=10)
        assert jobs == []

@pytest.mark.asyncio
async def test_provider_malformed_response():
    provider = GreenhouseDiscoveryProvider(boards=["figma"])
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"not_jobs": "unexpected_payload"}
    with patch.object(provider, "_safe_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        jobs = await provider.discover_jobs(limit=10)
        assert jobs == []

@pytest.mark.asyncio
async def test_provider_timeout_and_5xx_handling():
    provider = GreenhouseDiscoveryProvider(boards=["stripe"])
    with patch.object(provider, "_safe_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None  # Simulates network timeout or 5xx exhaustion
        jobs = await provider.discover_jobs(limit=10)
        assert jobs == []

# -------------------------------------------------------------
# 2. Normalization: Remote, Employment Type, Experience Level
# -------------------------------------------------------------
def test_normalization_rules():
    assert BaseDiscoveryProvider.normalize_remote_type("Remote") == "REMOTE"
    assert BaseDiscoveryProvider.normalize_remote_type(None, "Work from Home") == "REMOTE"
    assert BaseDiscoveryProvider.normalize_remote_type("Hybrid", "New York, NY") == "HYBRID"
    assert BaseDiscoveryProvider.normalize_remote_type("On-site", "Bengaluru") == "ONSITE"

    assert BaseDiscoveryProvider.normalize_employment_type("Software Engineer Intern") == "INTERNSHIP"
    assert BaseDiscoveryProvider.normalize_employment_type("Senior Contractor", "Contract") == "CONTRACT"
    assert BaseDiscoveryProvider.normalize_employment_type("Part-time Developer") == "PART_TIME"
    assert BaseDiscoveryProvider.normalize_employment_type("Full Stack Engineer") == "FULL_TIME"

    assert BaseDiscoveryProvider.normalize_experience_level("Staff Platform Engineer") == "LEAD"
    assert BaseDiscoveryProvider.normalize_experience_level("Senior Python Developer") == "SENIOR"
    assert BaseDiscoveryProvider.normalize_experience_level("Junior Associate Engineer") == "ENTRY"
    assert BaseDiscoveryProvider.normalize_experience_level("Backend Engineer") == "MID_LEVEL"

# -------------------------------------------------------------
# 3. Deduplication Hierarchy: Hash, URL, Company+Title+Location
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_multi_layer_deduplication(async_session):
    service = JobService(async_session)

    job1 = NormalizedJob(
        source="career_pages",
        discovery_provider="greenhouse_public_board",
        external_job_id="gh-dup-1",
        canonical_url="https://boards.greenhouse.io/corp/1",
        application_url="https://boards.greenhouse.io/corp/1",
        company="Acme Corp",
        title="Python Backend Engineer",
        description="Core systems",
        location="Remote",
        remote_type="REMOTE",
        skills=["Python"]
    )
    j1 = await service.ingest_normalized_job(job1)
    assert j1.id is not None

    # Exact duplicate (same external ID and company)
    j2 = await service.ingest_normalized_job(job1)
    assert j2.id == j1.id

    # Same job from another provider with same canonical URL
    job_diff_provider = NormalizedJob(
        source="linkedin",
        discovery_provider="jsearch",
        external_job_id="jsearch-dup-xyz",
        canonical_url="https://boards.greenhouse.io/corp/1",
        application_url="https://boards.greenhouse.io/corp/1",
        company="Acme Corp",
        title="Python Backend Engineer",
        description="Core systems updated",
        location="Remote",
        remote_type="REMOTE",
        skills=["Python", "FastAPI"]
    )
    j3 = await service.ingest_normalized_job(job_diff_provider)
    assert j3.id == j1.id

    # Same job with identical Company + Title + Location
    job_match_text = NormalizedJob(
        source="indeed",
        discovery_provider="jsearch",
        external_job_id="ind-9999",
        canonical_url="https://indeed.com/viewjob?id=9999",
        application_url="https://indeed.com/viewjob?id=9999",
        company="  acme corp  ",
        title="python backend engineer",
        description="Core systems match",
        location="remote",
        remote_type="REMOTE",
        skills=["Python"]
    )
    j4 = await service.ingest_normalized_job(job_match_text)
    assert j4.id == j1.id

# -------------------------------------------------------------
# 4. Source Provenance: Platform + Discovery Provider
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_source_provenance_tracking(async_session):
    service = JobService(async_session)

    job = NormalizedJob(
        source="linkedin",
        discovery_provider="jsearch",
        external_job_id="js-li-001",
        canonical_url="https://linkedin.com/jobs/view/123",
        application_url="https://linkedin.com/jobs/view/123",
        company="Google",
        title="Site Reliability Engineer",
        description="Infrastructure reliability",
        location="Mountain View, CA",
        remote_type="HYBRID",
        skills=["Go", "Kubernetes"],
        source_metadata={"publisher": "LinkedIn", "provider": "jsearch"}
    )
    saved = await service.ingest_normalized_job(job)
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    stmt = select(Job).options(selectinload(Job.job_source)).where(Job.id == saved.id)
    res = await async_session.execute(stmt)
    loaded_job = res.scalar_one()

    assert loaded_job.job_source.slug == "linkedin"
    assert loaded_job.discovery_provider == "jsearch"
    assert loaded_job.canonical_url == "https://linkedin.com/jobs/view/123"
    assert loaded_job.source_metadata.get("publisher") == "LinkedIn"

# -------------------------------------------------------------
# 5. Failure Isolation: Provider A failure -> Provider B still runs
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_failure_isolation_in_orchestrator():
    orch = JobDiscoveryOrchestrator()

    # Mock Greenhouse to throw an unhandled exception
    orch.greenhouse.discover_jobs = AsyncMock(side_effect=RuntimeError("Greenhouse API Down"))

    # Mock Lever to succeed normally
    lever_job = NormalizedJob(
        source="career_pages",
        discovery_provider="lever_public_postings",
        external_job_id="lev-1",
        application_url="https://jobs.lever.co/spotify/1",
        company="Spotify",
        title="Backend Engineer",
        description="Audio backend services",
        location="Remote",
        skills=["Java", "GCP"]
    )
    orch.lever.discover_jobs = AsyncMock(return_value=[lever_job])
    orch.remotive.discover_jobs = AsyncMock(return_value=[])
    orch.arbeitnow.discover_jobs = AsyncMock(return_value=[])

    jobs = await orch.discover_for_platform("career_pages", limit=20)
    assert len(jobs) == 1
    assert jobs[0].company == "Spotify"
    assert jobs[0].discovery_provider == "lever_public_postings"

# -------------------------------------------------------------
# 6. Zero Production Catalog Dependency
# -------------------------------------------------------------
def test_production_code_does_not_use_catalog():
    import os
    app_dir = os.path.join(os.path.dirname(__file__), "..", "app")
    found_usages = []
    for root, _, files in os.walk(app_dir):
        for f in files:
            if f.endswith(".py") and f != "catalog.py":
                filepath = os.path.join(root, f)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                    if "get_catalog_for_source" in content or "JOB_CATALOG" in content:
                        found_usages.append(filepath)

    assert found_usages == [], f"Found production usages of catalog.py: {found_usages}"

# -------------------------------------------------------------
# 7. Phase 2C: Non-Technical Role Rejection in Feeds
# -------------------------------------------------------------
def test_relevance_filter_rejects_non_tech_and_accepts_software():
    from app.modules.jobs.discovery.relevance_filter import is_technical_role

    # Technical roles -> Accept
    assert is_technical_role("Software Engineer") is True
    assert is_technical_role("Python Backend Developer") is True
    assert is_technical_role("React Frontend Engineer") is True
    assert is_technical_role("Full Stack Developer") is True
    assert is_technical_role("Software Engineer, Intern") is True
    assert is_technical_role("Machine Learning Engineer") is True

    # Non-technical roles -> Reject
    assert is_technical_role("Sales Jedi") is False
    assert is_technical_role("Freelance Writer") is False
    assert is_technical_role("Freelance Copywriter") is False
    assert is_technical_role("Associate General Counsel, Privacy Compliance") is False
    assert is_technical_role("Customer Service Specialist") is False
    assert is_technical_role("HR Recruiter") is False
    assert is_technical_role("Financial Consultant") is False

# -------------------------------------------------------------
# 8. Phase 2C: India & Remote Location Eligibility
# -------------------------------------------------------------
def test_location_eligibility_for_india_candidate():
    from app.modules.jobs.discovery.location_helper import is_location_eligible

    # Indian locations -> Accept
    assert is_location_eligible("Bengaluru, India", candidate_location="India") is True
    assert is_location_eligible("Bangalore", candidate_location="India") is True
    assert is_location_eligible("Pune, India", candidate_location="India") is True
    assert is_location_eligible("Remote - India", candidate_location="India") is True

    # Worldwide / Global -> Accept
    assert is_location_eligible("Worldwide Remote", candidate_location="India") is True
    assert is_location_eligible("Anywhere", candidate_location="India") is True
    assert is_location_eligible("APAC", candidate_location="India") is True

    # Explicit non-India restrictions -> Reject
    assert is_location_eligible("USA Only", candidate_location="India") is False
    assert is_location_eligible("US - Remote", candidate_location="India") is False
    assert is_location_eligible("Remote - The Netherlands", candidate_location="India") is False
    assert is_location_eligible("Europe Only", candidate_location="India") is False
    assert is_location_eligible("London, UK", candidate_location="India") is False

# -------------------------------------------------------------
# 9. Phase 2C: Zero False Platform Attribution
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_no_false_platform_attribution_when_aggregator_unconfigured():
    orch = JobDiscoveryOrchestrator()
    # Mock jsearch as unconfigured
    orch.jsearch.is_configured = lambda: False

    for portal in ["linkedin", "indeed", "naukri", "unstop", "internshala", "wellfound"]:
        jobs = await orch.discover_for_platform(portal, limit=10)
        assert len(jobs) == 0, f"Portal {portal} must return 0 jobs when genuine provider is unconfigured"

# -------------------------------------------------------------
# 11. Phase 2C: Strict Provenance Mapping (LinkedIn, Indeed, Naukri, DICE, Monster, Remotive, Greenhouse, Lever)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_provenance_rules_for_publishers_and_sources():
    orch = JobDiscoveryOrchestrator()
    orch.jsearch.is_configured = lambda: True

    def make_mock_jsearch_item(title: str, publisher: str):
        return {
            "job_id": f"test-{publisher.lower()}",
            "job_title": title,
            "employer_name": "Acme Inc",
            "job_publisher": publisher,
            "job_apply_link": f"https://{publisher.lower()}.com/job",
            "job_city": "Bengaluru",
            "job_country": "India"
        }

    # 1. JSearch publisher=LinkedIn -> source_platform=linkedin
    orch.jsearch._safe_get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {"data": [make_mock_jsearch_item("Python Developer", "LinkedIn")]}))
    jobs_li = await orch.jsearch.discover_jobs(target_platform="linkedin")
    assert len(jobs_li) == 1
    assert jobs_li[0].source == "linkedin"
    assert jobs_li[0].discovery_provider == "jsearch"

    # 2. JSearch publisher=Indeed -> source_platform=indeed
    orch.jsearch._safe_get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {"data": [make_mock_jsearch_item("Backend Developer", "Indeed")]}))
    jobs_ind = await orch.jsearch.discover_jobs(target_platform="indeed")
    assert len(jobs_ind) == 1
    assert jobs_ind[0].source == "indeed"
    assert jobs_ind[0].discovery_provider == "jsearch"

    # 3. JSearch publisher=Naukri -> source_platform=naukri
    orch.jsearch._safe_get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {"data": [make_mock_jsearch_item("Full Stack Developer", "Naukri")]}))
    jobs_nk = await orch.jsearch.discover_jobs(target_platform="naukri")
    assert len(jobs_nk) == 1
    assert jobs_nk[0].source == "naukri"
    assert jobs_nk[0].discovery_provider == "jsearch"

    # 4. JSearch publisher=DICE -> source_platform=aggregated_feeds (NEVER career_pages)
    orch.jsearch._safe_get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {"data": [make_mock_jsearch_item("Software Engineer", "DICE")]}))
    jobs_dice = await orch.jsearch.discover_jobs()
    assert len(jobs_dice) == 1
    assert jobs_dice[0].source == "aggregated_feeds"
    assert jobs_dice[0].discovery_provider == "jsearch"

    # 5. JSearch publisher=Monster -> source_platform=aggregated_feeds (NEVER career_pages)
    orch.jsearch._safe_get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {"data": [make_mock_jsearch_item("Software Engineer", "Monster")]}))
    jobs_mon = await orch.jsearch.discover_jobs()
    assert len(jobs_mon) == 1
    assert jobs_mon[0].source == "aggregated_feeds"
    assert jobs_mon[0].discovery_provider == "jsearch"

@pytest.mark.asyncio
async def test_remotive_greenhouse_lever_provenance():
    # 6. Remotive job -> source_platform=aggregated_feeds
    rem_provider = RemotiveDiscoveryProvider()
    rem_data = {
        "jobs": [
            {
                "id": 9991,
                "title": "Python Developer",
                "company_name": "RemoteCo",
                "category": "Software Development",
                "tags": ["python"],
                "candidate_required_location": "Worldwide",
                "url": "https://remotive.com/9991"
            }
        ]
    }
    rem_provider._safe_get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: rem_data))
    rem_jobs = await rem_provider.discover_jobs()
    assert len(rem_jobs) == 1
    assert rem_jobs[0].source == "aggregated_feeds"
    assert rem_jobs[0].discovery_provider == "remotive_public_api"

    # 7. Greenhouse job -> source_platform=career_pages
    gh_provider = GreenhouseDiscoveryProvider(boards=["cloudflare"])
    gh_data = {
        "jobs": [
            {
                "id": 8881,
                "title": "Systems Engineer",
                "location": {"name": "Bengaluru, India"},
                "absolute_url": "https://boards.greenhouse.io/cloudflare/jobs/8881",
                "departments": [{"name": "Engineering"}]
            }
        ]
    }
    gh_provider._safe_get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: gh_data))
    gh_jobs = await gh_provider.discover_jobs()
    assert len(gh_jobs) == 1
    assert gh_jobs[0].source == "career_pages"
    assert gh_jobs[0].discovery_provider == "greenhouse_public_board"

    # 8. Lever job -> source_platform=career_pages
    lever_provider = LeverDiscoveryProvider(companies=["spotify"])
    lever_data = [
        {
            "id": "lev-7771",
            "text": "Android Engineer",
            "categories": {"team": "Engineering", "location": "Bengaluru, India"},
            "hostedUrl": "https://jobs.lever.co/spotify/lev-7771"
        }
    ]
    lever_provider._safe_get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: lever_data))
    lever_jobs = await lever_provider.discover_jobs()
    assert len(lever_jobs) == 1
    assert lever_jobs[0].source == "career_pages"
    assert lever_jobs[0].discovery_provider == "lever_public_postings"


