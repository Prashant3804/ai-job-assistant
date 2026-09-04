import re
from typing import Optional, Dict, Any, Tuple
from app.modules.matching.schemas import DimensionScore

class ExperienceMatcher:
    """Experience matcher handling entry-level freshers, seniority levels, and year ranges."""

    @classmethod
    def parse_job_years(cls, job_exp_str: Optional[str], experience_level: Optional[str]) -> Tuple[float, float]:
        """Extract min and max years required from job description or level."""
        min_years = 0.0
        max_years = 100.0

        if job_exp_str:
            clean = job_exp_str.lower().strip()
            # Check for patterns like "0-2 years", "3-5 yrs", "2+ years", "fresher"
            if "fresher" in clean or "entry" in clean or "0 year" in clean:
                return 0.0, 2.0
            
            range_match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)", clean)
            if range_match:
                return float(range_match.group(1)), float(range_match.group(2))
            
            plus_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", clean)
            if plus_match:
                min_val = float(plus_match.group(1))
                return min_val, max(min_val + 3.0, 10.0)

        # Fallback to experience_level enum string
        level = (experience_level or "").upper()
        if level in ("ENTRY", "INTERNSHIP", "JUNIOR", "FRESHER"):
            return 0.0, 2.0
        elif level in ("MID", "MID_LEVEL", "ASSOCIATE"):
            return 2.0, 5.0
        elif level in ("SENIOR", "STAFF"):
            return 5.0, 8.0
        elif level in ("LEAD", "PRINCIPAL", "DIRECTOR", "EXECUTIVE"):
            return 8.0, 20.0

        return 0.0, 100.0  # Open/unspecified

    @classmethod
    def match(
        cls,
        candidate_years: float,
        job_exp_str: Optional[str] = None,
        job_level: Optional[str] = None,
        weight: float = 20.0
    ) -> DimensionScore:
        min_req, max_req = cls.parse_job_years(job_exp_str, job_level)

        cand_years = max(0.0, candidate_years)

        # 1. Fresher vs Entry/0-2 years
        if cand_years == 0.0 and min_req == 0.0:
            score = 100.0
            status = "MATCH"
            rationale = "Ideal fit: Fresher / entry-level qualification matches 0-2 years requirement."
        # 2. Within required range
        elif min_req <= cand_years <= max_req:
            score = 100.0
            status = "MATCH"
            rationale = f"Experience of {cand_years:g} yrs falls directly within the required {min_req:g}-{max_req:g} yrs range."
        # 3. Candidate has more experience than required
        elif cand_years > max_req:
            # Minor overqualification check
            diff = cand_years - max_req
            if diff <= 2.0:
                score = 95.0
                status = "MATCH"
                rationale = f"Candidate experience of {cand_years:g} yrs exceeds requirement ({max_req:g} yrs) with strong domain depth."
            else:
                score = 85.0
                status = "MATCH"
                rationale = f"Candidate is highly experienced ({cand_years:g} yrs) for target range ({min_req:g}-{max_req:g} yrs)."
        # 4. Candidate has less experience than required
        else:
            deficit = min_req - cand_years
            if deficit <= 1.0:
                score = 75.0
                status = "PARTIAL"
                rationale = f"Slight experience deficit ({cand_years:g} yrs vs {min_req:g} yrs required), candidate is close to requirements."
            elif deficit <= 2.0:
                score = 50.0
                status = "PARTIAL"
                rationale = f"Moderate experience gap ({cand_years:g} yrs vs {min_req:g} yrs required)."
            else:
                score = 25.0
                status = "MISMATCH"
                rationale = f"Significant experience gap ({cand_years:g} yrs vs {min_req:g}+ yrs required for seniority)."

        score = round(max(0.0, min(100.0, score)), 1)
        contribution = round((score * weight) / 100.0, 2)

        return DimensionScore(
            score=score,
            weight=weight,
            contribution=contribution,
            status=status,
            details={
                "candidate_years": cand_years,
                "job_min_years": min_req,
                "job_max_years": max_req,
                "job_level": job_level or "UNSPECIFIED"
            },
            rationale=rationale
        )
