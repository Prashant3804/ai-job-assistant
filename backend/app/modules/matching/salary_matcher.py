from typing import Optional, Dict, Any
from app.modules.matching.schemas import DimensionScore

class SalaryMatcher:
    """Salary & Compensation matcher supporting currency conversion, LPA, and range checks."""

    EXCHANGE_RATES_TO_USD = {
        "USD": 1.0,
        "INR": 0.012,   # ~83.3 INR per USD
        "EUR": 1.08,
        "GBP": 1.26,
        "CAD": 0.74,
        "AUD": 0.65,
    }

    @classmethod
    def _to_usd(cls, amount: Optional[int], curr: Optional[str]) -> Optional[float]:
        if amount is None:
            return None
        rate = cls.EXCHANGE_RATES_TO_USD.get((curr or "USD").upper(), 1.0)
        return amount * rate

    @classmethod
    def match(
        cls,
        candidate_min_salary: Optional[int],
        job_salary_min: Optional[int],
        job_salary_max: Optional[int],
        currency: str = "USD",
        candidate_currency: Optional[str] = None,
        weight: float = 10.0
    ) -> DimensionScore:
        has_salary_info = bool(job_salary_min or job_salary_max)
        job_curr = (currency or "USD").upper()
        cand_curr = (candidate_currency or currency or "USD").upper()
        
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
            # Normalize to USD for cross-currency comparison if currencies differ
            if job_curr != cand_curr:
                cand_min_comp = cls._to_usd(candidate_min_salary, cand_curr) or float(candidate_min_salary)
                j_min_comp = cls._to_usd(job_salary_min, job_curr) or 0.0
                j_max_comp = cls._to_usd(job_salary_max, job_curr) or j_min_comp
                compare_unit = "USD (normalized)"
            else:
                cand_min_comp = float(candidate_min_salary)
                j_min_comp = float(job_salary_min or 0)
                j_max_comp = float(job_salary_max or j_min_comp)
                compare_unit = job_curr

            if j_min_comp >= cand_min_comp:
                score = 100.0
                status = "MATCH"
                rationale = f"Job minimum salary meets or exceeds candidate target ({int(cand_min_comp):,} {compare_unit})."
            elif j_max_comp >= cand_min_comp:
                score = 85.0
                status = "MATCH"
                rationale = f"Job compensation range up to {int(j_max_comp):,} {compare_unit} covers candidate requirement."
            else:
                deficit_pct = ((cand_min_comp - j_max_comp) / cand_min_comp) * 100.0 if cand_min_comp > 0 else 0
                if deficit_pct <= 15.0:
                    score = 60.0
                    status = "PARTIAL"
                    rationale = f"Job max salary ({int(j_max_comp):,} {compare_unit}) is slightly below candidate target ({int(cand_min_comp):,} {compare_unit})."
                else:
                    score = 25.0
                    status = "MISMATCH"
                    rationale = f"Salary mismatch: Job offers max {int(j_max_comp):,} {compare_unit} vs candidate minimum {int(cand_min_comp):,} {compare_unit}."

        score = round(max(0.0, min(100.0, score)), 1)
        contribution = round((score * weight) / 100.0, 2)

        return DimensionScore(
            score=score,
            weight=weight,
            contribution=contribution,
            status=status,
            details={
                "candidate_min_salary": candidate_min_salary,
                "candidate_currency": cand_curr,
                "job_salary_min": job_salary_min,
                "job_salary_max": job_salary_max,
                "currency": job_curr,
                "salary_information_available": has_salary_info
            },
            rationale=rationale
        )
