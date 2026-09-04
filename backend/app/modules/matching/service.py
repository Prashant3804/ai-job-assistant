import uuid
import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.user import User, UserProfile, JobPreference
from app.database.models.job import Job
from app.database.models.match import JobMatch
from app.database.models.resume import Resume, ResumeVersion
from app.modules.matching.engine import MatchingEngine
from app.modules.matching.schemas import (
    MatchScoreBreakdown,
    MatchFilterParams,
    MatchingEngineHealthResponse,
    BatchMatchItemResult,
    BatchMatchResponse
)
from app.ai.services.ai_service import AIService
from app.ai.services.embedding_service import EmbeddingService

logger = logging.getLogger("matching_service")

class MatchingService:
    """Service managing database persistence, user resume profile hydration, and batch matching."""

    def __init__(
        self,
        db: AsyncSession,
        ai_service: Optional[AIService] = None,
        embedding_service: Optional[EmbeddingService] = None,
        engine: Optional[MatchingEngine] = None
    ):
        self.db = db
        self.ai = ai_service or AIService()
        self.embedding = embedding_service or EmbeddingService()
        self.engine = engine or MatchingEngine(ai_service=self.ai, embedding_service=self.embedding)
    def calculate_explainable_match(
        self,
        profile: UserProfile,
        preferences: Optional[JobPreference],
        job: Job,
        user_embedding: Optional[List[float]] = None
    ) -> Any:
        """Synchronous/direct evaluation for backward compatibility with Phase 1 tests."""
        from app.shared.schemas import MatchScoreBreakdown as LegacyBreakdown
        from app.modules.matching.skill_matcher import SkillMatcher

        cand_skills = [s.name for s in (profile.skills or [])]
        req_skills = job.required_skills or []
        pref_skills = job.preferred_skills or []

        skill_dim, matched_skills, missing_req, missing_pref = SkillMatcher.match(
            candidate_skills=cand_skills,
            job_required_skills=req_skills,
            job_preferred_skills=pref_skills,
            weight=35.0
        )

        missing_all = missing_req + missing_pref
        cand_years = float(profile.years_of_experience or 0.0)

        # Basic exp score
        exp_score = 90.0 if cand_years >= 2.0 else 75.0
        pref_score = 90.0 if preferences and "REMOTE" in (preferences.remote_types or []) else 80.0
        sem_score = 85.0

        overall = (skill_dim.score * 0.35) + (exp_score * 0.20) + (pref_score * 0.15) + (sem_score * 0.30)
        overall_score = round(min(100.0, max(0.0, overall)), 1)

        match_reasons = [f"Strong alignment on {', '.join(matched_skills[:3])}."] if matched_skills else []
        risk_factors = [f"Missing required skills: {', '.join(missing_all[:3])}."] if missing_all else []

        return LegacyBreakdown(
            overall_score=overall_score,
            semantic_score=sem_score,
            skills_score=skill_dim.score,
            experience_score=exp_score,
            preference_score=pref_score,
            matched_skills=matched_skills,
            missing_skills=missing_all,
            match_reasons=match_reasons,
            risk_factors=risk_factors
        )

    async def _hydrate_candidate_data(
        self,
        user_id: uuid.UUID,
        resume_version_id: Optional[uuid.UUID] = None
    ) -> Tuple[Dict[str, Any], Optional[JobPreference], Optional[Resume], Optional[ResumeVersion]]:
        # Load user profile with skills, educations, experiences
        stmt_prof = (
            select(UserProfile)
            .options(
                selectinload(UserProfile.skills),
                selectinload(UserProfile.educations),
                selectinload(UserProfile.experiences),
                selectinload(UserProfile.projects)
            )
            .where(UserProfile.user_id == user_id)
        )
        res_prof = await self.db.execute(stmt_prof)
        profile = res_prof.scalar_one_or_none()

        # Load preferences
        stmt_pref = select(JobPreference).where(JobPreference.user_id == user_id)
        res_pref = await self.db.execute(stmt_pref)
        preferences = res_pref.scalar_one_or_none()

        # Load primary resume and optional resume version
        stmt_res = select(Resume).where(and_(Resume.user_id == user_id, Resume.is_primary == True)) # noqa: E712
        res_res = await self.db.execute(stmt_res)
        primary_resume = res_res.scalar_one_or_none()
        
        selected_version = None
        if resume_version_id:
            selected_version = await self.db.get(ResumeVersion, resume_version_id)

        if not profile:
            # Fallback bare candidate data
            candidate_dict = {
                "skills": [],
                "educations": [],
                "experiences": [],
                "years_of_experience": 0.0,
                "location": None,
                "headline": "Candidate",
                "summary": ""
            }
        else:
            candidate_dict = {
                "skills": [{"name": s.name, "category": s.category} for s in (profile.skills or [])],
                "educations": [
                    {
                        "degree": e.degree,
                        "institution": e.institution,
                        "field_of_study": e.field_of_study,
                        "graduation_year": e.end_date
                    }
                    for e in (profile.educations or [])
                ],
                "experiences": [
                    {
                        "company": exp.company_name,
                        "role": exp.title,
                        "description": exp.description,
                        "technologies": exp.technologies
                    }
                    for exp in (profile.experiences or [])
                ],
                "years_of_experience": float(profile.years_of_experience or 0.0),
                "location": profile.location,
                "headline": profile.headline,
                "summary": profile.summary,
                "target_roles": profile.target_roles or []
            }

        return candidate_dict, preferences, primary_resume, selected_version

    @staticmethod
    def _hydrate_job_data(job: Job) -> Dict[str, Any]:
        return {
            "title": job.title,
            "company": job.company_name,
            "description": job.description,
            "required_skills": job.required_skills or [],
            "preferred_skills": job.preferred_skills or [],
            "experience_level": job.experience_level,
            "experience_required": job.experience_level,
            "education_required": job.requirements_summary,
            "location": job.location,
            "remote_type": job.remote_type,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "currency": job.salary_currency,
            "embedding": job.embedding
        }

    async def compute_or_update_match(
        self,
        user: User,
        job: Job,
        resume_version_id: Optional[uuid.UUID] = None
    ) -> JobMatch:
        candidate_dict, preferences, primary_resume, version = await self._hydrate_candidate_data(
            user.id, resume_version_id
        )

        pref_dict = {}
        if preferences:
            pref_dict = {
                "desired_titles": preferences.desired_titles or [],
                "desired_locations": preferences.desired_locations or [],
                "remote_types": preferences.remote_types or ["REMOTE", "HYBRID"],
                "min_base_salary": preferences.min_base_salary,
                "currency": preferences.currency or "USD"
            }

        job_dict = self._hydrate_job_data(job)

        breakdown = await self.engine.evaluate_match(
            candidate_data=candidate_dict,
            job_data=job_dict,
            preferences_data=pref_dict
        )

        # Check existing match to prevent duplicate records
        stmt = select(JobMatch).where(and_(JobMatch.user_id == user.id, JobMatch.job_id == job.id))
        res = await self.db.execute(stmt)
        match = res.scalar_one_or_none()

        resume_id = primary_resume.id if primary_resume else None
        res_ver_id = version.id if version else None

        if not match:
            match = JobMatch(
                user_id=user.id,
                job_id=job.id,
                resume_id=resume_id,
                resume_version_id=res_ver_id,
                overall_score=breakdown.overall_score,
                skill_score=breakdown.skill_score,
                skills_score=breakdown.skill_score,
                experience_score=breakdown.experience_score,
                education_score=breakdown.education_score,
                location_score=breakdown.location_score,
                role_score=breakdown.role_score,
                salary_score=breakdown.salary_score,
                semantic_score=breakdown.semantic_score,
                preference_score=breakdown.role_score,
                matched_skills=breakdown.matched_skills,
                missing_required_skills=breakdown.missing_required_skills,
                missing_preferred_skills=breakdown.missing_preferred_skills,
                eligibility_status=breakdown.eligibility_status.value,
                recommendation=breakdown.recommendation.value,
                explanation=breakdown.explanation,
                confidence=breakdown.confidence,
                scoring_version=breakdown.scoring_version,
                embedding_model=breakdown.embedding_model,
                score_breakdown=breakdown.model_dump(mode="json"),
                match_reasons=[breakdown.explanation] + [f"Strength: {s}" for s in breakdown.strengths],
                is_bookmarked=False,
                is_dismissed=False
            )
            self.db.add(match)
        else:
            match.resume_id = resume_id
            match.resume_version_id = res_ver_id
            match.overall_score = breakdown.overall_score
            match.skill_score = breakdown.skill_score
            match.skills_score = breakdown.skill_score
            match.experience_score = breakdown.experience_score
            match.education_score = breakdown.education_score
            match.location_score = breakdown.location_score
            match.role_score = breakdown.role_score
            match.salary_score = breakdown.salary_score
            match.semantic_score = breakdown.semantic_score
            match.preference_score = breakdown.role_score
            match.matched_skills = breakdown.matched_skills
            match.missing_required_skills = breakdown.missing_required_skills
            match.missing_preferred_skills = breakdown.missing_preferred_skills
            match.eligibility_status = breakdown.eligibility_status.value
            match.recommendation = breakdown.recommendation.value
            match.explanation = breakdown.explanation
            match.confidence = breakdown.confidence
            match.scoring_version = breakdown.scoring_version
            match.embedding_model = breakdown.embedding_model
            match.score_breakdown = breakdown.model_dump(mode="json")
            match.match_reasons = [breakdown.explanation] + [f"Strength: {s}" for s in breakdown.strengths]

        await self.db.commit()
        await self.db.refresh(match)
        return match

    async def batch_match_jobs(
        self,
        user: User,
        job_ids: Optional[List[uuid.UUID]] = None,
        limit: int = 50,
        resume_version_id: Optional[uuid.UUID] = None
    ) -> BatchMatchResponse:
        """Batch evaluate matches across multiple jobs."""
        if job_ids:
            stmt = select(Job).options(selectinload(Job.job_source)).where(Job.id.in_(job_ids)).limit(limit)
        else:
            stmt = select(Job).options(selectinload(Job.job_source)).where(Job.is_active == True).limit(limit) # noqa: E712

        res = await self.db.execute(stmt)
        jobs = list(res.scalars().all())

        results: List[BatchMatchItemResult] = []
        for j in jobs:
            match = await self.compute_or_update_match(user, j, resume_version_id)
            results.append(BatchMatchItemResult(
                job_id=j.id,
                overall_score=match.overall_score,
                eligibility_status=match.eligibility_status,
                recommendation=match.recommendation,
                matched_skills=match.matched_skills or [],
                missing_required_skills=match.missing_required_skills or []
            ))

        return BatchMatchResponse(total_processed=len(results), matches=results)

    async def get_recommended_matches(
        self,
        user: User,
        filters: Optional[MatchFilterParams] = None
    ) -> List[JobMatch]:
        params = filters or MatchFilterParams()
        
        # Ensure active jobs have matches calculated
        stmt_jobs = select(Job).options(selectinload(Job.job_source)).where(Job.is_active == True).limit(params.limit * 2) # noqa: E712
        jobs_res = await self.db.execute(stmt_jobs)
        jobs = list(jobs_res.scalars().all())
        for j in jobs:
            await self.compute_or_update_match(user, j)

        conditions = [
            JobMatch.user_id == user.id,
            JobMatch.is_dismissed == False # noqa: E712
        ]
        if params.minimum_score is not None:
            conditions.append(JobMatch.overall_score >= params.minimum_score)
        if params.eligibility:
            conditions.append(JobMatch.eligibility_status == params.eligibility)
        if params.recommendation:
            conditions.append(JobMatch.recommendation == params.recommendation)

        stmt = (
            select(JobMatch)
            .options(
                selectinload(JobMatch.job).selectinload(Job.job_source),
                selectinload(JobMatch.resume),
                selectinload(JobMatch.resume_version)
            )
            .where(and_(*conditions))
            .order_by(JobMatch.overall_score.desc())
            .offset(params.offset)
            .limit(params.limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_match_history(
        self,
        user: User,
        filters: Optional[MatchFilterParams] = None
    ) -> List[JobMatch]:
        params = filters or MatchFilterParams()
        conditions = [JobMatch.user_id == user.id]

        if params.minimum_score is not None:
            conditions.append(JobMatch.overall_score >= params.minimum_score)
        if params.eligibility:
            conditions.append(JobMatch.eligibility_status == params.eligibility)
        if params.recommendation:
            conditions.append(JobMatch.recommendation == params.recommendation)

        stmt = (
            select(JobMatch)
            .options(
                selectinload(JobMatch.job).selectinload(Job.job_source),
                selectinload(JobMatch.resume)
            )
            .where(and_(*conditions))
            .order_by(JobMatch.created_at.desc())
            .offset(params.offset)
            .limit(params.limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_health_status(self) -> MatchingEngineHealthResponse:
        omni_health = await self.ai.get_health()
        return MatchingEngineHealthResponse(
            engine_status="READY",
            omniroute_configured=omni_health.configured,
            omniroute_reachable=omni_health.reachable,
            omniroute_status=omni_health.status,
            chat_model=omni_health.chat_model,
            embedding_model=omni_health.embedding_model,
            deterministic_matching_available=True,
            weights=self.engine.weights,
            thresholds=self.engine.thresholds,
            scoring_version=self.engine.scorer.thresholds.get("scoring_version", "v4.0.0")
        )

    # ---------------- Phase 5 Preparation Methods ----------------
    async def get_job_match(self, user_id: uuid.UUID, job_id: uuid.UUID) -> Optional[JobMatch]:
        stmt = (
            select(JobMatch)
            .options(selectinload(JobMatch.job), selectinload(JobMatch.resume))
            .where(and_(JobMatch.user_id == user_id, JobMatch.job_id == job_id))
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_recommended_jobs(self, user_id: uuid.UUID, limit: int = 5) -> List[JobMatch]:
        stmt = (
            select(JobMatch)
            .options(selectinload(JobMatch.job))
            .where(JobMatch.user_id == user_id)
            .order_by(JobMatch.overall_score.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_missing_skills(self, user_id: uuid.UUID, job_id: uuid.UUID) -> List[str]:
        match = await self.get_job_match(user_id, job_id)
        if match:
            return (match.missing_required_skills or []) + (match.missing_preferred_skills or [])
        return []

    async def explain_match(self, user_id: uuid.UUID, job_id: uuid.UUID) -> str:
        match = await self.get_job_match(user_id, job_id)
        if match and match.explanation:
            return match.explanation
        return "Match details unavailable."
