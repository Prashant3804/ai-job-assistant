import re
from typing import List, Optional, Dict, Any
from app.modules.matching.schemas import DimensionScore

DEGREE_LEVEL_HIERARCHY = {
    "phd": 5,
    "doctorate": 5,
    "master": 4,
    "m.tech": 4,
    "mtech": 4,
    "m.s.": 4,
    "ms": 4,
    "mca": 4,
    "mba": 4,
    "bachelor": 3,
    "b.tech": 3,
    "btech": 3,
    "b.e.": 3,
    "be": 3,
    "b.s.": 3,
    "bs": 3,
    "bca": 3,
    "b.sc": 3,
    "associate": 2,
    "diploma": 2,
    "high school": 1,
}

TECH_FIELDS = {
    "computer science", "cs", "information technology", "it",
    "software engineering", "computer engineering", "computer applications",
    "data science", "artificial intelligence", "electrical engineering",
    "electronics", "mathematics", "statistics"
}

class EducationMatcher:
    """Education matcher evaluating degree level, field relevance, and equivalents."""

    @classmethod
    def _extract_degree_level(cls, degree_str: str) -> int:
        if not degree_str:
            return 0
        clean = degree_str.lower()
        clean_no_punct = re.sub(r"[^\w\s]", "", clean)
        for deg_key, rank in DEGREE_LEVEL_HIERARCHY.items():
            deg_key_clean = re.sub(r"[^\w\s]", "", deg_key)
            if deg_key in clean or deg_key_clean in clean_no_punct:
                return rank
        return 1 if "high school" in clean else 2  # Default tertiary/diploma level

    @classmethod
    def _is_tech_field(cls, field_str: str) -> bool:
        if not field_str:
            return True
        clean = field_str.lower()
        return any(tf in clean for tf in TECH_FIELDS)

    @classmethod
    def match(
        cls,
        candidate_educations: List[Dict[str, Any]],
        job_education_required: Optional[str] = None,
        weight: float = 15.0
    ) -> DimensionScore:
        if not candidate_educations:
            # Candidate has no educational records in profile
            if not job_education_required or "not required" in job_education_required.lower():
                score = 80.0
                status = "MATCH"
                rationale = "No explicit formal degree required by job."
            else:
                score = 40.0
                status = "PARTIAL"
                rationale = "Candidate education details are missing from profile."
        else:
            cand_max_rank = max((cls._extract_degree_level(e.get("degree", "")) for e in candidate_educations), default=3)
            cand_fields = [e.get("field_of_study", "") for e in candidate_educations]
            cand_has_tech = any(cls._is_tech_field(f) for f in cand_fields)

            if job_education_required:
                req_rank = cls._extract_degree_level(job_education_required)
                req_is_tech = cls._is_tech_field(job_education_required)
                
                if cand_max_rank >= req_rank:
                    if not req_is_tech or cand_has_tech:
                        score = 100.0
                        status = "MATCH"
                        rationale = f"Candidate degree meets or exceeds the required level ({job_education_required})."
                    else:
                        score = 80.0
                        status = "PARTIAL"
                        rationale = f"Candidate holds equivalent degree level but from related non-primary discipline."
                elif cand_max_rank == req_rank - 1:
                    score = 70.0
                    status = "PARTIAL"
                    rationale = f"Candidate education is one tier below preferred requirement ({job_education_required})."
                else:
                    score = 45.0
                    status = "MISMATCH"
                    rationale = f"Education requirement ({job_education_required}) not fully satisfied."
            else:
                # No specific educational constraint on job
                score = 100.0 if cand_has_tech else 90.0
                status = "MATCH"
                rationale = "Candidate possesses relevant educational background for engineering requirements."

        score = round(max(0.0, min(100.0, score)), 1)
        contribution = round((score * weight) / 100.0, 2)

        return DimensionScore(
            score=score,
            weight=weight,
            contribution=contribution,
            status=status,
            details={
                "candidate_education_count": len(candidate_educations),
                "required_education": job_education_required or "UNSPECIFIED"
            },
            rationale=rationale
        )
