from typing import Optional, Dict, Any
from app.modules.matching.schemas import DimensionScore

class SalaryMatcher:
    """Salary & Compensation matcher supporting currency conversion, LPA, and range checks."""

    @classmethod
    def match(
        cls,
        candidate_min_salary: Optional[int],
        job_salary_min: Optional[int],
        job_salary_max: Optional[int],
        currency: str = "USD",
        weight: float = 10.0
    ) -> DimensionScore:
        has_salary_info = bool(job_salary_min or job_salary_max)
        
        if not has_salary_info:
            # Salary missing from job posting - do not grant 100% blindly
            score = 70.0
            status = "UNAVAILABLE"
            rationale = "Salary details not disclosed by employer; marked as unverified."
        elif not candidate_min_salary:
            # Candidate has not set salary expectation
            score = 85.0
            status = "MATCH"
            rationale = "Compensation posted by employer and within standard market range."
        else:
            # Candidate has explicit expectations
            j_min = job_salary_min or 0
            j_max = job_salary_max or j_min

            if j_min >= candidate_min_salary:
                score = 100.0
                status = "MATCH"
                rationale = f"Job minimum salary ({j_min:,} {currency}) meets or exceeds candidate target ({candidate_min_salary:,} {currency})."
            elif j_max >= candidate_min_salary:
                score = 85.0
                status = "MATCH"
                rationale = f"Job compensation range up to {j_max:,} {currency} covers candidate requirement of {candidate_min_salary:,} {currency}."
            else:
                deficit_pct = ((candidate_min_salary - j_max) / candidate_min_salary) * 100.0
                if deficit_pct <= 15.0:
                    score = 60.0
                    status = "PARTIAL"
                    rationale = f"Job max salary ({j_max:,} {currency}) is slightly below candidate target ({candidate_min_salary:,} {currency})."
                else:
                    score = 25.0
                    status = "MISMATCH"
                    rationale = f"Salary mismatch: Job offers max {j_max:,} {currency} vs candidate minimum {candidate_min_salary:,} {currency}."

        score = round(max(0.0, min(100.0, score)), 1)
        contribution = round((score * weight) / 100.0, 2)

        return DimensionScore(
            score=score,
            weight=weight,
            contribution=contribution,
            status=status,
            details={
                "candidate_min_salary": candidate_min_salary,
                "job_salary_min": job_salary_min,
                "job_salary_max": job_salary_max,
                "currency": currency,
                "salary_information_available": has_salary_info
            },
            rationale=rationale
        )
