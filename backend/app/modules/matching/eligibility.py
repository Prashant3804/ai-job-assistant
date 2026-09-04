from typing import List, Dict, Optional, Any
from app.modules.matching.constants import EligibilityStatus
from app.modules.matching.schemas import DimensionScore

class EligibilityEvaluator:
    """Evaluates candidate hard eligibility independently from match score."""

    @classmethod
    def evaluate(
        cls,
        dimensions: Dict[str, DimensionScore],
        missing_required_skills: List[str],
        has_profile_data: bool,
        has_job_data: bool
    ) -> EligibilityStatus:
        if not has_profile_data or not has_job_data:
            return EligibilityStatus.INSUFFICIENT_DATA

        skill_dim = dimensions.get("skills")
        exp_dim = dimensions.get("experience")
        edu_dim = dimensions.get("education")
        loc_dim = dimensions.get("location")

        # 1. Hard Disqualifications
        # a. Critical location mismatch (e.g. US residency constraint violated)
        if loc_dim and loc_dim.status == "MISMATCH" and loc_dim.score <= 25.0:
            return EligibilityStatus.NOT_ELIGIBLE

        # b. Severe experience gap for Lead/Senior roles (deficit > 3 years)
        if exp_dim and exp_dim.status == "MISMATCH" and exp_dim.score <= 25.0:
            return EligibilityStatus.NOT_ELIGIBLE

        # c. Severe skill gap: all mandatory required skills missing
        if skill_dim and len(missing_required_skills) >= 3 and skill_dim.score <= 20.0:
            return EligibilityStatus.NOT_ELIGIBLE

        # 2. Review Triggers
        if (loc_dim and loc_dim.status == "UNAVAILABLE") or (edu_dim and edu_dim.status == "PARTIAL"):
            return EligibilityStatus.REVIEW

        if missing_required_skills:
            # 1-2 missing required skills -> Likely eligible or Review
            if len(missing_required_skills) == 1:
                return EligibilityStatus.LIKELY_ELIGIBLE
            return EligibilityStatus.REVIEW

        # 3. Full eligibility
        if exp_dim and exp_dim.score >= 70.0 and (not edu_dim or edu_dim.score >= 70.0):
            return EligibilityStatus.ELIGIBLE

        return EligibilityStatus.LIKELY_ELIGIBLE
