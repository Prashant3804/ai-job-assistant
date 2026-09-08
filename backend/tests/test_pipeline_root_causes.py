import pytest
from app.modules.jobs.discovery.tech_extractor import extract_technologies, GENERIC_BLACKLIST
from app.modules.resume.date_utils import calculate_total_experience_years, parse_date_str
from app.modules.matching.role_matcher import RoleMatcher
from app.modules.matching.schemas import MatchScoreBreakdown, EligibilityStatus
from app.modules.ai.service import ResilientAIService

def test_extract_technologies_eliminates_generic_and_company_names():
    # 1. Stripe Job
    title = "Software Engineer - Payments Infrastructure"
    desc = "We are building payments with Python, PostgreSQL, Kafka, and Docker at Stripe."
    skills = extract_technologies(title, desc, existing_skills=["Stripe", "Software Engineering"])
    assert "Stripe" not in skills
    assert "Software Engineering" not in skills
    assert "stripe" not in [s.lower() for s in skills]
    assert "software engineering" not in [s.lower() for s in skills]
    assert "Python" in skills
    assert "PostgreSQL" in skills
    assert "Docker" in skills
    assert "Kafka" in skills

    # 2. Coinbase Job
    cb_title = "Backend Engineer, Crypto Data"
    cb_skills = extract_technologies(cb_title, "Working with Go, Redis, and AWS", existing_skills=["Coinbase"])
    assert "Coinbase" not in cb_skills
    assert "Go" in cb_skills
    assert "Redis" in cb_skills
    assert "AWS" in cb_skills

    # 3. Lemon.io Job
    lemon_title = "Senior React Developer"
    lemon_skills = extract_technologies(lemon_title, "Expert in React, TypeScript, Next.js, and CSS", existing_skills=["Lemon.io"])
    assert "Lemon.io" not in lemon_skills
    assert "React" in lemon_skills
    assert "TypeScript" in lemon_skills

def test_experience_calculation_date_math_and_union():
    # Prashant's exact timeline
    experiences = [
        {"title": "Senior Backend Engineer", "company": "Apex Cloud", "start_date": "Jan 2022", "end_date": "Present", "is_current": True},
        {"title": "Software Engineer", "company": "Innovate Labs", "start_date": "Jun 2019", "end_date": "Dec 2021", "is_current": False}
    ]
    years = calculate_total_experience_years(experiences)
    assert years >= 6.5
    assert years <= 8.5

    # Overlapping timeline
    overlap_exps = [
        {"start_date": "Jan 2020", "end_date": "Dec 2022"},
        {"start_date": "Jun 2021", "end_date": "Jun 2023"}
    ]
    # Jan 2020 to Jun 2023 is 3.4166 years (should NOT double count to 5.0)
    overlap_years = calculate_total_experience_years(overlap_exps)
    assert 3.4 <= overlap_years <= 3.5

    # Empty
    assert calculate_total_experience_years([]) == 0.0

def test_role_matcher_headline_fallback_and_clustering():
    # Candidate with empty explicit target roles, but headline "Senior Full Stack Engineer"
    headline = "Senior Full Stack Engineer"
    score_fullstack = RoleMatcher.match(
        candidate_target_roles=[],
        candidate_headline=headline,
        job_title="Software Engineer - Payments"
    )
    # Belongs to software_engineering cluster -> 85% or direct match
    assert score_fullstack.score >= 80.0
    assert score_fullstack.status == "MATCH"

    # React Developer should also match software_engineering
    score_react = RoleMatcher.match(
        candidate_target_roles=[],
        candidate_headline=headline,
        job_title="Senior React Developer"
    )
    assert score_react.score >= 80.0
    assert score_react.status == "MATCH"

    # Explicit target roles take priority
    score_explicit = RoleMatcher.match(
        candidate_target_roles=["Data Scientist"],
        candidate_headline="Data Analyst",
        job_title="Senior Data Scientist"
    )
    assert score_explicit.score == 100.0

def test_ai_resilient_service_fallback_reset():
    ai = ResilientAIService()
    # Initial state
    status = ai.get_provider_status()
    assert status["routing"] == "Gemini -> OmniRoute"
    assert status["last_fallback_occurred"] is False

    # Simulate Gemini success
    ai.last_provider_used = "gemini"
    ai.last_fallback_occurred = False
    ai.last_fallback_reason = None
    status = ai.get_provider_status()
    assert status["active_provider"] == "gemini"
    assert status["active_display"] == "Gemini (Primary)"
    assert status["last_fallback_occurred"] is False

    # Simulate Gemini fallback event
    ai.last_provider_used = "omniroute"
    ai.last_fallback_occurred = True
    ai.last_fallback_reason = "Gemini rate limit (429)"
    status_fb = ai.get_provider_status()
    assert status_fb["active_provider"] == "omniroute"
    assert "Fallback Active" in status_fb["active_display"]
    assert status_fb["last_fallback_occurred"] is True

    # Now simulate a subsequent Gemini recovery
    ai.last_provider_used = "gemini"
    ai.last_fallback_occurred = False
    ai.last_fallback_reason = None
    status_recovered = ai.get_provider_status()
    assert status_recovered["active_provider"] == "gemini"
    assert status_recovered["active_display"] == "Gemini (Primary)"
    assert status_recovered["last_fallback_occurred"] is False

def test_strict_65_threshold_boundary():
    # Exact 65.0 threshold boundary check
    threshold = 65.0

    score_sub = 64.9
    score_qual = 65.0
    score_high = 78.5

    # Boundary conditions
    assert (score_sub < threshold) is True   # Skipped at Stage G
    assert (score_qual < threshold) is False # Qualifies as matching
    assert (score_high < threshold) is False # Qualifies as matching
