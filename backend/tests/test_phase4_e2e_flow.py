import pytest
import uuid
import httpx
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.database.models.user import User, UserProfile, CandidateSkill, JobPreference
from app.database.models.job import Job
from app.database.models.resume import Resume, ResumeVersion
from app.database.models.match import JobMatch

@pytest.mark.asyncio
async def test_full_phase4_e2e_api_workflow(async_client: httpx.AsyncClient, async_session: AsyncSession):
    # 1. Setup Candidate User
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"e2e_candidate_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashed_password",
        full_name="Alice Developer",
        is_active=True,
        is_verified=True,
        role="CANDIDATE"
    )
    async_session.add(user)
    await async_session.commit()

    # 2. Setup Candidate Profile, Skills & Preferences
    profile_id = uuid.uuid4()
    profile = UserProfile(
        id=profile_id,
        user_id=user_id,
        headline="Senior Full Stack Engineer",
        years_of_experience=5.0,
        location="San Francisco, CA",
        remote_preference="REMOTE",
        target_roles=["Senior Full Stack Engineer", "Backend Engineer"]
    )
    async_session.add(profile)
    await async_session.commit()

    skill1 = CandidateSkill(id=uuid.uuid4(), user_profile_id=profile_id, name="Python", proficiency_level="EXPERT", years_experience=5.0)
    skill2 = CandidateSkill(id=uuid.uuid4(), user_profile_id=profile_id, name="FastAPI", proficiency_level="EXPERT", years_experience=4.0)
    skill3 = CandidateSkill(id=uuid.uuid4(), user_profile_id=profile_id, name="React", proficiency_level="ADVANCED", years_experience=3.0)
    async_session.add_all([skill1, skill2, skill3])

    pref = JobPreference(
        id=uuid.uuid4(),
        user_id=user_id,
        desired_titles=["Senior Full Stack Engineer", "Backend Engineer"],
        desired_locations=["San Francisco", "Remote"],
        remote_types=["REMOTE", "HYBRID"],
        min_base_salary=140000,
        currency="USD"
    )
    async_session.add(pref)

    # 3. Setup Resume & Active Version
    resume = Resume(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Master Resume",
        file_url="/resumes/alice_resume.pdf",
        file_format="PDF",
        is_primary=True,
        raw_text="Alice Developer. Senior Full Stack Engineer. Expert in Python, FastAPI, and React.",
        parsed_data={"skills": ["Python", "FastAPI", "React"], "personal": {"name": "Alice Developer"}}
    )
    async_session.add(resume)
    await async_session.commit()

    version = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        tailored_content={"skills": ["Python", "FastAPI", "React", "Docker"], "experience_years": 5},
        file_url="/resumes/v1.pdf"
    )
    async_session.add(version)

    # 4. Ingest Jobs
    job1_id = uuid.uuid4()
    job1 = Job(
        id=job1_id,
        external_id=f"gh-{uuid.uuid4().hex[:6]}",
        company_name="TechNova",
        title="Senior Full Stack Engineer",
        description="We are seeking an experienced Senior Full Stack Engineer with Python, FastAPI, and React expertise.",
        required_skills=["Python", "FastAPI"],
        preferred_skills=["React", "Docker"],
        experience_level="SENIOR",
        location="Remote",
        remote_type="REMOTE",
        salary_min=150000,
        salary_max=180000,
        salary_currency="USD",
        employment_type="FULL_TIME",
        deduplication_hash=uuid.uuid4().hex,
        is_active=True
    )

    job2_id = uuid.uuid4()
    job2 = Job(
        id=job2_id,
        external_id=f"lev-{uuid.uuid4().hex[:6]}",
        company_name="BioTech Global",
        title="Clinical Research Associate",
        description="Looking for Clinical Research Associate with biology lab experience and GCP certification.",
        required_skills=["Clinical Research", "GCP", "Biology"],
        preferred_skills=["Lab Management"],
        experience_level="MID",
        location="New York, NY",
        remote_type="ONSITE",
        salary_min=80000,
        salary_max=95000,
        salary_currency="USD",
        employment_type="FULL_TIME",
        deduplication_hash=uuid.uuid4().hex,
        is_active=True
    )
    async_session.add_all([job1, job2])
    await async_session.commit()

    # 5. Generate Auth Token
    token = create_access_token(str(user_id))
    headers = {"Authorization": f"Bearer {token}"}

    # 6. Test Matching Health Endpoint
    health_resp = await async_client.get("/api/v1/matching/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["engine_status"] in ["READY", "DEGRADED"]
    assert "omniroute_configured" in health_data
    assert "weights" in health_data

    # 7. Test Single Job Match Calculation (Job 1 - High Match)
    match1_resp = await async_client.post(f"/api/v1/matching/jobs/{job1_id}", headers=headers)
    assert match1_resp.status_code == 200
    match1_data = match1_resp.json()
    assert match1_data["overall_score"] >= 70.0
    assert match1_data["eligibility_status"] in ["ELIGIBLE", "LIKELY_ELIGIBLE"]
    assert match1_data["recommendation"] in ["STRONG_MATCH", "GOOD_MATCH", "POSSIBLE_MATCH"]
    assert "Python" in match1_data["matched_skills"]
    assert match1_data["score_breakdown"] is not None
    assert len(match1_data["score_breakdown"]["dimensions"]) == 6

    # 8. Test Single Job Match Retrieval (Cached from DB)
    get_match1_resp = await async_client.get(f"/api/v1/matching/jobs/{job1_id}", headers=headers)
    assert get_match1_resp.status_code == 200
    assert get_match1_resp.json()["overall_score"] == match1_data["overall_score"]

    # 9. Test Batch Match Execution
    batch_resp = await async_client.post("/api/v1/matching/batch", json={"limit": 10}, headers=headers)
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert batch_data["total_processed"] >= 2
    assert len(batch_data["matches"]) >= 2

    # 10. Test Recommended Jobs Endpoint with Filter
    rec_resp = await async_client.get("/api/v1/matching/recommended?minimum_score=70", headers=headers)
    assert rec_resp.status_code == 200
    rec_list = rec_resp.json()
    assert len(rec_list) >= 1
    assert rec_list[0]["job_id"] == str(job1_id)

    # 11. Test Bookmarking a Match
    bm_resp = await async_client.post(f"/api/v1/matching/jobs/{job1_id}/bookmark", headers=headers)
    assert bm_resp.status_code == 200
    assert bm_resp.json()["data"]["is_bookmarked"] is True

    # 12. Test Match History List
    history_resp = await async_client.get("/api/v1/matching/matches", headers=headers)
    assert history_resp.status_code == 200
    history_list = history_resp.json()
    assert len(history_list) >= 2

    # 13. Test Unauthorized Access with Invalid Token (Security & Auth)
    unauth_resp = await async_client.post(f"/api/v1/matching/jobs/{job1_id}", headers={"Authorization": "Bearer invalid_token_xyz"})
    assert unauth_resp.status_code == 401

    # 14. Test User Data Isolation (User B gets their own isolated match record)
    user2_id = uuid.uuid4()
    user2 = User(
        id=user2_id,
        email=f"bob_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashed_password",
        full_name="Bob User",
        is_active=True,
        is_verified=True,
        role="CANDIDATE"
    )
    async_session.add(user2)
    await async_session.commit()

    token2 = create_access_token(str(user2_id))
    headers2 = {"Authorization": f"Bearer {token2}"}

    bob_get_match = await async_client.get(f"/api/v1/matching/jobs/{job1_id}", headers=headers2)
    assert bob_get_match.status_code == 200
    bob_data = bob_get_match.json()
    assert bob_data["user_id"] == str(user2_id)
    assert bob_data["id"] != match1_data["id"]

    # 15. Verify DB Persistence & Composite Index Structure
    db_matches = (await async_session.execute(select(JobMatch).where(JobMatch.user_id == user_id))).scalars().all()
    assert len(db_matches) >= 2
    for m in db_matches:
        assert m.overall_score is not None
        assert m.skill_score is not None
        assert m.experience_score is not None
        assert m.education_score is not None
        assert m.location_score is not None
        assert m.role_score is not None
        assert m.salary_score is not None
        assert m.eligibility_status is not None
        assert m.recommendation is not None
        assert m.confidence is not None
