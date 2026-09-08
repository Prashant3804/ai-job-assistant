import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from app.database.models.user import User, UserProfile, Education, Experience, CandidateSkill, Project, JobPreference
from app.database.models.job import Job, JobSource
from app.modules.applications.preparation_service import ApplicationPreparationService, ApplicationPreparationPackage
from app.modules.applications.capability_service import ApplicationCapabilityService, ApplicationSubmissionCapability
from app.shared.constants import ConnectorCapabilityStatus, PolicyDecision
from app.modules.applications.policy import ApplicationPolicyEngine
from app.database.models.application import ApplicationPolicy


# =====================================================================
# 1. Match Threshold Qualification: 64.99 -> Skip, 65.00 -> Qualify
# =====================================================================
def test_match_threshold_rule_65_percent():
    policy = ApplicationPolicy(
        auto_apply_enabled=True,
        minimum_match_score=65.0,
        daily_application_limit=210,
        per_source_daily_limit=30
    )
    job = Job(company_name="Acme", title="Software Engineer", location="Remote")

    # 64.99% -> SKIP_LOW_MATCH
    match_below = MagicMock()
    match_below.overall_score = 64.99
    match_below.eligibility_status = "ELIGIBLE"
    appr_below, dec_below, _ = ApplicationPolicyEngine.evaluate(
        policy=policy, job=job, match=match_below, daily_applications_count=0, source_daily_applications_count=0
    )
    assert not appr_below
    assert dec_below == PolicyDecision.SKIP_LOW_MATCH

    # 65.00% -> QUALIFIES
    match_at = MagicMock()
    match_at.overall_score = 65.00
    match_at.eligibility_status = "ELIGIBLE"
    appr_at, dec_at, _ = ApplicationPolicyEngine.evaluate(
        policy=policy, job=job, match=match_at, daily_applications_count=0, source_daily_applications_count=0
    )
    assert appr_at
    assert dec_at == PolicyDecision.AUTO_APPLY


# =====================================================================
# 2. Application Preparation: Zero-Hallucination & Factual Integrity
# =====================================================================
@pytest.mark.asyncio
async def test_preparation_service_verified_data_and_zero_hallucination():
    user = User(
        id=uuid.uuid4(),
        email="rahul.sharma@example.com",
        full_name="Rahul Sharma",
    )
    profile = UserProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        phone="+91 98765 43210",
        headline="Full Stack Python & React Engineer",
        years_of_experience=4.5,
        location="Bengaluru, India",
        linkedin_url="https://linkedin.com/in/rahulsharma",
        github_url="https://github.com/rahulsharma",
        portfolio_url="https://rahulsharma.dev"
    )
    edu = Education(
        id=uuid.uuid4(),
        user_profile_id=profile.id,
        degree="B.Tech in Computer Science",
        institution="NIT Trichy",
        field_of_study="Computer Science",
        end_date="2022"
    )
    exp = Experience(
        id=uuid.uuid4(),
        user_profile_id=profile.id,
        company_name="TechVentures India",
        title="Software Engineer",
        start_date="2022-07",
        end_date="Present",
        description="Built resilient backend microservices using FastAPI and PostgreSQL."
    )
    skills = [
        CandidateSkill(id=uuid.uuid4(), user_profile_id=profile.id, name="Python", category="TECHNICAL"),
        CandidateSkill(id=uuid.uuid4(), user_profile_id=profile.id, name="FastAPI", category="TECHNICAL"),
        CandidateSkill(id=uuid.uuid4(), user_profile_id=profile.id, name="PostgreSQL", category="TECHNICAL"),
        CandidateSkill(id=uuid.uuid4(), user_profile_id=profile.id, name="React", category="TECHNICAL"),
    ]
    pref = JobPreference(
        id=uuid.uuid4(),
        user_id=user.id,
        sponsorship_required=False,
        min_base_salary=2500000,
        currency="INR"
    )

    job = Job(
        id=uuid.uuid4(),
        title="Senior Python Backend Developer",
        company_name="Global Fintech Labs",
        description="Seeking an experienced Python developer with strong database and API skills.",
        apply_url="https://fintech.example.com/careers/backend-eng",
        deduplication_hash="unique_hash_fintech_001",
        source_metadata={
            "application_questions": [
                {"key": "q1", "question": "What is your full name?", "required": True},
                {"key": "q2", "question": "What is your email address?", "required": True},
                {"key": "q3", "question": "Are you legally authorized to work?", "required": True},
                {"key": "q4", "question": "Do you have 10 years of experience with Rust?", "required": True},
                {"key": "q5", "question": "What is your Secret Security Clearance Level?", "required": True},
            ]
        }
    )

    prep_service = ApplicationPreparationService()
    pkg = await prep_service.prepare_package(
        user=user,
        job=job,
        profile=profile,
        preferences=pref,
        educations=[edu],
        experiences=[exp],
        skills=skills,
        projects=[]
    )

    assert pkg.candidate_name == "Rahul Sharma"
    assert pkg.email == "rahul.sharma@example.com"
    assert pkg.phone == "+91 98765 43210"
    assert pkg.location == "Bengaluru, India"
    assert pkg.linkedin_url == "https://linkedin.com/in/rahulsharma"
    assert pkg.cover_letter is not None
    assert "Rahul Sharma" in pkg.cover_letter
    assert "Global Fintech Labs" in pkg.cover_letter

    # Check screening answers
    answers_by_key = {a["question_key"]: a for a in pkg.screening_answers}
    assert answers_by_key["q1"]["answer_text"] == "Rahul Sharma"
    assert answers_by_key["q2"]["answer_text"] == "rahul.sharma@example.com"
    assert answers_by_key["q3"]["answer_text"] == "Yes"

    # ZERO HALLUCINATION: Unknown Rust experience & security clearance must NOT be guessed
    assert answers_by_key["q4"]["answer_text"] == "MISSING_REQUIRED_FIELD"
    assert answers_by_key["q5"]["answer_text"] == "MISSING_REQUIRED_FIELD"

    assert "q4" in pkg.missing_required_fields
    assert "q5" in pkg.missing_required_fields


# =====================================================================
# 3. AI Dual-Routing Resilience: Gemini -> OpenRouter
# =====================================================================
@pytest.mark.asyncio
async def test_preparation_ai_routing_gemini_success():
    mock_ai = MagicMock()
    mock_ai.generate_text = AsyncMock(return_value="Dear Hiring Team,\nI am writing to express my verified interest.")
    mock_ai.last_provider_used = "gemini"
    mock_ai.last_fallback_occurred = False

    prep_service = ApplicationPreparationService(ai_service=mock_ai)
    facts = {
        "name": "Alex Candidate",
        "skills": ["Python", "FastAPI"],
        "years_of_experience": 3.0,
        "headline": "Backend Engineer",
        "highest_degree": "B.S.",
        "institution": "Tech Univ"
    }
    letter, provider, fallback = await prep_service.generate_tailored_cover_letter(
        candidate_facts=facts,
        job_title="Software Engineer",
        company_name="CloudCorp"
    )
    assert "Alex Candidate" in letter or "Dear Hiring Team" in letter
    assert provider == "gemini"
    assert fallback is False


@pytest.mark.asyncio
async def test_preparation_ai_routing_gemini_fallback_to_openrouter():
    mock_ai = MagicMock()
    # Simulate Gemini failing with 429 quota, fallback resolving to OpenRouter
    mock_ai.generate_text = AsyncMock(return_value="Dear Hiring Team at CloudCorp,\nTailored cover letter via OpenRouter.")
    mock_ai.last_provider_used = "omniroute"
    mock_ai.last_fallback_occurred = True

    prep_service = ApplicationPreparationService(ai_service=mock_ai)
    facts = {
        "name": "Sam Candidate",
        "skills": ["React", "TypeScript"],
        "years_of_experience": 2.0,
        "headline": "Frontend Developer",
    }
    letter, provider, fallback = await prep_service.generate_tailored_cover_letter(
        candidate_facts=facts,
        job_title="Frontend Engineer",
        company_name="WebScale"
    )
    assert provider == "omniroute"
    assert fallback is True


# =====================================================================
# 4. Application Capability Service: Platform Routing
# =====================================================================
def test_platform_capability_service_routes_all_7_platforms_honestly():
    platforms_external_required = [
        "naukri",
        "indeed",
        "unstop",
        "linkedin",
        "internshala",
        "wellfound",
        "career_pages",
        "aggregated_feeds",
    ]

    for p in platforms_external_required:
        source = JobSource(slug=p, name=p.title(), capability_status=ConnectorCapabilityStatus.EXTERNAL_APPLICATION_REQUIRED.value)
        job = Job(company_name="Acme", title="Dev", description="Role desc", job_source=source)
        cap, reason = ApplicationCapabilityService.evaluate_job(job)
        assert cap == ApplicationSubmissionCapability.EXTERNAL_APPLICATION_REQUIRED
        assert len(reason) > 10

    # Mock ATS is legitimately supported for automated testing
    mock_source = JobSource(slug="mock_ats", name="Mock ATS", capability_status=ConnectorCapabilityStatus.SUPPORTED_AUTO_APPLY.value)
    mock_job = Job(company_name="TestCorp", title="Dev", description="Role desc", job_source=mock_source)
    cap_mock, _ = ApplicationCapabilityService.evaluate_job(mock_job)
    assert cap_mock == ApplicationSubmissionCapability.SUPPORTED_AUTO_APPLY


# =====================================================================
# 5. Duplicate Protection
# =====================================================================
@pytest.mark.asyncio
async def test_duplicate_application_protection(async_session):
    from app.modules.applications.duplicate import DuplicateDetector
    from app.database.models.application import Application

    user_id = uuid.uuid4()
    job = Job(
        id=uuid.uuid4(),
        title="Python Engineer",
        company_name="Stripe",
        description="Engineering role at Stripe.",
        deduplication_hash="unique_hash_stripe_001",
        is_active=True
    )
    async_session.add(job)
    await async_session.flush()

    # Before application: Not a duplicate
    is_dup1, _, _ = await DuplicateDetector.check_duplicate(user_id, job, async_session)
    assert is_dup1 is False

    # Insert existing application
    app = Application(
        id=uuid.uuid4(),
        user_id=user_id,
        job_id=job.id,
        source="career_pages",
        status="APPLIED"
    )
    async_session.add(app)
    await async_session.commit()

    # After application: Detected as duplicate
    is_dup2, existing_id, _ = await DuplicateDetector.check_duplicate(user_id, job, async_session)
    assert is_dup2 is True
    assert existing_id == app.id
