import pytest
import uuid
from app.database.models.user import UserProfile, CandidateSkill, JobPreference
from app.database.models.job import Job
from app.modules.matching.service import MatchingService
from app.modules.ai.service import MockAIProvider

@pytest.mark.asyncio
async def test_explainable_match_calculation():
    ai = MockAIProvider()
    service = MatchingService(None, ai_service=ai)

    # Setup mock candidate profile
    profile = UserProfile(
        id=uuid.uuid4(),
        headline="Senior Backend Engineer",
        summary="Specialized in Python and FastAPI distributed systems",
        location="San Francisco, CA",
        remote_preference="REMOTE",
        years_of_experience=5.0,
    )
    profile.skills = [
        CandidateSkill(name="Python", category="TECHNICAL", years_experience=5.0),
        CandidateSkill(name="FastAPI", category="TECHNICAL", years_experience=4.0),
        CandidateSkill(name="PostgreSQL", category="TECHNICAL", years_experience=5.0),
        CandidateSkill(name="Docker", category="TOOL", years_experience=3.0),
    ]

    preferences = JobPreference(
        remote_types=["REMOTE"],
        min_base_salary=150000,
        max_base_salary=200000
    )

    # Matching Job
    matching_job = Job(
        id=uuid.uuid4(),
        title="Senior Python Backend Engineer",
        company_name="Acme Inc",
        location="Remote",
        remote_type="REMOTE",
        experience_level="SENIOR",
        salary_min=160000,
        salary_max=190000,
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        preferred_skills=["Docker"],
        description="High throughput backend role",
        deduplication_hash="hash1",
        embedding=[0.1] * 128
    )

    user_emb = [0.1] * 128
    breakdown = service.calculate_explainable_match(profile, preferences, matching_job, user_emb)

    assert breakdown.overall_score >= 85.0
    assert breakdown.skills_score == 100.0  # All required skills matched
    assert "Python" in breakdown.matched_skills
    assert "Fastapi" in breakdown.matched_skills or "FastAPI" in breakdown.matched_skills
    assert len(breakdown.match_reasons) > 0

@pytest.mark.asyncio
async def test_missing_skills_detection():
    ai = MockAIProvider()
    service = MatchingService(None, ai_service=ai)

    profile = UserProfile(
        id=uuid.uuid4(),
        headline="Junior Frontend Developer",
        years_of_experience=1.0,
    )
    profile.skills = [
        CandidateSkill(name="HTML", category="TECHNICAL", years_experience=1.0),
        CandidateSkill(name="CSS", category="TECHNICAL", years_experience=1.0),
    ]

    job = Job(
        id=uuid.uuid4(),
        title="Staff Rust Systems Architect",
        company_name="RustLabs",
        remote_type="ONSITE",
        experience_level="LEAD",
        required_skills=["Rust", "Kubernetes", "Distributed Systems"],
        description="Low level systems engineering",
        deduplication_hash="hash2",
        embedding=await ai.generate_embedding("Staff Rust Systems Architect")
    )

    user_emb = await ai.generate_embedding("Junior Frontend Developer")
    breakdown = service.calculate_explainable_match(profile, None, job, user_emb)

    assert breakdown.skills_score == 0.0
    assert len(breakdown.missing_skills) == 3
    assert len(breakdown.risk_factors) > 0
