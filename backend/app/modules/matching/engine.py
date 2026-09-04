import logging
from typing import Dict, Any, Optional, List
from app.ai.services.ai_service import AIService
from app.ai.services.embedding_service import EmbeddingService
from app.modules.matching.constants import (
    DEFAULT_WEIGHTS,
    DEFAULT_THRESHOLDS,
    SCORING_VERSION,
    EligibilityStatus,
    RecommendationStatus,
)
from app.modules.matching.schemas import (
    MatchScoreBreakdown,
    DimensionScore
)
from app.modules.matching.skill_matcher import SkillMatcher
from app.modules.matching.experience_matcher import ExperienceMatcher
from app.modules.matching.education_matcher import EducationMatcher
from app.modules.matching.location_matcher import LocationMatcher
from app.modules.matching.salary_matcher import SalaryMatcher
from app.modules.matching.role_matcher import RoleMatcher
from app.modules.matching.semantic_matcher import SemanticMatcher
from app.modules.matching.scoring import WeightedScoringCalculator
from app.modules.matching.eligibility import EligibilityEvaluator
from app.modules.matching.explanation import ExplanationGenerator

logger = logging.getLogger("matching_engine")

class MatchingEngine:
    """Production-grade AI Job Matching Engine with explainable scoring and OmniRoute integration."""

    def __init__(
        self,
        ai_service: Optional[AIService] = None,
        embedding_service: Optional[EmbeddingService] = None,
        weights: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, float]] = None
    ):
        self.ai_service = ai_service or AIService()
        self.embedding_service = embedding_service or EmbeddingService()
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.thresholds = thresholds or dict(DEFAULT_THRESHOLDS)
        
        self.scorer = WeightedScoringCalculator(self.weights, self.thresholds)
        self.semantic_matcher = SemanticMatcher(self.embedding_service)
        self.explanation_gen = ExplanationGenerator(self.ai_service)

    async def evaluate_match(
        self,
        candidate_data: Dict[str, Any],
        job_data: Dict[str, Any],
        preferences_data: Optional[Dict[str, Any]] = None,
        user_embedding: Optional[List[float]] = None
    ) -> MatchScoreBreakdown:
        # 1. Sanitize untrusted job content against prompt injection
        sanitized_description = self.ai_service.sanitize_untrusted_input(job_data.get("description", ""))
        job_title = job_data.get("title", "Software Engineer")
        company_name = job_data.get("company", "Company")

        # 2. Extract Candidate Information
        cand_skills = [s.get("name", "") if isinstance(s, dict) else str(s) for s in candidate_data.get("skills", [])]
        cand_years = float(candidate_data.get("years_of_experience", 0.0))
        cand_educations = candidate_data.get("educations", [])
        cand_location = candidate_data.get("location")
        cand_headline = candidate_data.get("headline")
        cand_target_roles = candidate_data.get("target_roles", [])
        
        # Candidate Preferences
        pref_data = preferences_data or {}
        pref_remote = pref_data.get("remote_types", ["REMOTE", "HYBRID"])
        pref_locations = pref_data.get("desired_locations", [])
        pref_min_salary = pref_data.get("min_base_salary")
        pref_currency = pref_data.get("currency", "USD")

        # 3. Extract Job Information
        job_req_skills = job_data.get("required_skills", []) or []
        job_pref_skills = job_data.get("preferred_skills", []) or []
        job_exp_str = job_data.get("experience_required")
        job_level = job_data.get("experience_level")
        job_edu_req = job_data.get("education_required")
        job_location = job_data.get("location")
        job_remote = job_data.get("remote_type", "ONSITE")
        job_sal_min = job_data.get("salary_min")
        job_sal_max = job_data.get("salary_max")
        job_currency = job_data.get("currency", pref_currency)
        job_embedding = job_data.get("embedding")

        # 4. Run Deterministic Matchers
        skill_dim, matched_skills, missing_req, missing_pref = SkillMatcher.match(
            candidate_skills=cand_skills,
            job_required_skills=job_req_skills,
            job_preferred_skills=job_pref_skills,
            weight=self.weights["skills"]
        )

        exp_dim = ExperienceMatcher.match(
            candidate_years=cand_years,
            job_exp_str=job_exp_str,
            job_level=job_level,
            weight=self.weights["experience"]
        )

        edu_dim = EducationMatcher.match(
            candidate_educations=cand_educations,
            job_education_required=job_edu_req,
            weight=self.weights["education"]
        )

        loc_dim = LocationMatcher.match(
            candidate_location=cand_location,
            preferred_remote_types=pref_remote,
            desired_locations=pref_locations,
            job_location=job_location,
            job_remote_type=job_remote,
            weight=self.weights["location"]
        )

        sal_dim = SalaryMatcher.match(
            candidate_min_salary=pref_min_salary,
            job_salary_min=job_sal_min,
            job_salary_max=job_sal_max,
            currency=job_currency,
            weight=self.weights["salary"]
        )

        role_dim = RoleMatcher.match(
            candidate_target_roles=pref_data.get("desired_titles", cand_target_roles),
            candidate_headline=cand_headline,
            job_title=job_title,
            weight=self.weights["role"]
        )

        dimensions: Dict[str, DimensionScore] = {
            "skills": skill_dim,
            "experience": exp_dim,
            "education": edu_dim,
            "location": loc_dim,
            "role": role_dim,
            "salary": sal_dim,
        }

        # 5. Semantic Vector Similarity (OmniRoute Embeddings)
        cand_summary_text = (
            f"Candidate: {cand_headline or ''}. "
            f"Skills: {', '.join(cand_skills)}. "
            f"Experience: {cand_years} years. {candidate_data.get('summary', '')}"
        )
        semantic_score, embedding_model, conf = await self.semantic_matcher.match(
            candidate_summary_text=cand_summary_text,
            job_description_text=sanitized_description,
            job_embedding=job_embedding
        )

        # 6. Aggregate Deterministic Score & Recommendation
        overall_score = self.scorer.calculate_overall_score(dimensions)
        recommendation = self.scorer.determine_recommendation(overall_score)

        # 7. Evaluate Eligibility Independently
        has_profile_data = bool(cand_skills or cand_educations or cand_years > 0 or cand_headline)
        has_job_data = bool(job_title and (sanitized_description or job_req_skills))
        
        eligibility = EligibilityEvaluator.evaluate(
            dimensions=dimensions,
            missing_required_skills=missing_req,
            has_profile_data=has_profile_data,
            has_job_data=has_job_data
        )

        # 8. Generate Natural Language Explanation (OmniRoute with fallback)
        ai_resp = await self.explanation_gen.generate_explanation(
            job_title=job_title,
            company_name=company_name,
            overall_score=overall_score,
            dimensions=dimensions,
            matched_skills=matched_skills,
            missing_required_skills=missing_req,
            missing_preferred_skills=missing_pref,
            eligibility=eligibility,
            recommendation=recommendation
        )

        return MatchScoreBreakdown(
            overall_score=overall_score,
            skill_score=skill_dim.score,
            experience_score=exp_dim.score,
            education_score=edu_dim.score,
            location_score=loc_dim.score,
            role_score=role_dim.score,
            salary_score=sal_dim.score,
            semantic_score=semantic_score,
            dimensions=dimensions,
            matched_skills=matched_skills,
            missing_required_skills=missing_req,
            missing_preferred_skills=missing_pref,
            eligibility_status=eligibility,
            recommendation=recommendation,
            explanation=ai_resp.summary,
            strengths=ai_resp.strengths,
            gaps=ai_resp.gaps,
            confidence=conf,
            scoring_version=SCORING_VERSION,
            embedding_model=embedding_model
        )
