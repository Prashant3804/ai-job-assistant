import logging
from typing import List, Optional, Dict, Any
from app.ai.services.ai_service import AIService
from app.ai.schemas.ai_schemas import AIExplanationRequest, AIExplanationResponse
from app.modules.matching.constants import EligibilityStatus, RecommendationStatus
from app.modules.matching.schemas import DimensionScore

logger = logging.getLogger("explanation_generator")

class ExplanationGenerator:
    """Generates human-readable match explanations using OmniRoute AI with deterministic fallback."""

    def __init__(self, ai_service: Optional[AIService] = None):
        self.ai = ai_service or AIService()

    async def generate_explanation(
        self,
        job_title: str,
        company_name: str,
        overall_score: float,
        dimensions: Dict[str, DimensionScore],
        matched_skills: List[str],
        missing_required_skills: List[str],
        missing_preferred_skills: List[str],
        eligibility: EligibilityStatus,
        recommendation: RecommendationStatus
    ) -> AIExplanationResponse:
        exp_dim = dimensions.get("experience")
        loc_dim = dimensions.get("location")

        req = AIExplanationRequest(
            job_title=job_title,
            company_name=company_name,
            overall_score=overall_score,
            matched_skills=matched_skills[:8],
            missing_required_skills=missing_required_skills[:5],
            missing_preferred_skills=missing_preferred_skills[:5],
            eligibility_status=eligibility.value,
            recommendation=recommendation.value,
            experience_summary=exp_dim.rationale if exp_dim else None,
            location_summary=loc_dim.rationale if loc_dim else None,
        )

        try:
            return await self.ai.explain(req)
        except Exception as e:
            logger.warning(f"AI explanation generation failed ({e}). Using deterministic template.")
            # Deterministic fallback
            matched_text = ", ".join(matched_skills[:4]) if matched_skills else "general profile"
            missing_text = f" Missing required: {', '.join(missing_required_skills[:3])}." if missing_required_skills else ""
            return AIExplanationResponse(
                summary=(
                    f"Overall score of {overall_score:.1f}% for {job_title} at {company_name}. "
                    f"Key strengths align on {matched_text}.{missing_text}"
                ),
                strengths=[f"Strong alignment on {s}" for s in matched_skills[:3]],
                gaps=[f"Missing {s}" for s in missing_required_skills[:3]],
                recommendation_note=f"Recommendation: {recommendation.value.replace('_', ' ')} with {eligibility.value.lower().replace('_', ' ')} status."
            )
