import pytest
from app.modules.jobs.connectors.adapters import get_all_connectors, get_primary_connectors, get_connector_by_slug, SEVEN_PRIMARY_SOURCES
from app.modules.jobs.service import JobService

@pytest.mark.asyncio
async def test_all_seven_sources_registered_and_configured():
    connectors = get_primary_connectors()
    assert len(connectors) == 7
    slugs = [c.slug for c in connectors]
    for expected in ['naukri', 'indeed', 'unstop', 'linkedin', 'internshala', 'wellfound', 'career_pages']:
        assert expected in slugs

@pytest.mark.asyncio
async def test_each_source_provides_jobs_with_provenance():
    for slug in SEVEN_PRIMARY_SOURCES:
        conn = get_connector_by_slug(slug)
        assert conn is not None
        jobs = await conn.search_jobs(limit=10)
        assert isinstance(jobs, list)
        if slug == "career_pages":
            assert len(jobs) > 0, "Career pages must provide live discovered jobs"
        for j in jobs:
            assert j.source == slug
            assert j.title
            assert j.company
            assert j.application_url
            assert j.discovery_provider is not None

def test_deduplication_hash():
    hash1 = JobService.generate_deduplication_hash('Stripe', 'Backend Engineer', '123')
    hash2 = JobService.generate_deduplication_hash('  stripe  ', 'BACKEND ENGINEER', '123')
    hash3 = JobService.generate_deduplication_hash('Stripe', 'Frontend Engineer', '123')
    assert hash1 == hash2
    assert hash1 != hash3
