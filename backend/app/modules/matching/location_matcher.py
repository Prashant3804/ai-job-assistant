import re
from typing import Optional, List, Dict, Any
from app.modules.matching.schemas import DimensionScore

class LocationMatcher:
    """Location & Workplace model matcher (Remote, Hybrid, Onsite, Geo-matching)."""

    @classmethod
    def match(
        cls,
        candidate_location: Optional[str],
        preferred_remote_types: Optional[List[str]],
        desired_locations: Optional[List[str]],
        job_location: Optional[str],
        job_remote_type: Optional[str],
        weight: float = 10.0
    ) -> DimensionScore:
        pref_remote = [r.upper() for r in (preferred_remote_types or ["REMOTE", "HYBRID"])]
        job_remote = (job_remote_type or "ONSITE").upper()
        
        has_job_loc = bool(job_location and job_location.strip())
        has_cand_loc = bool(candidate_location and candidate_location.strip())

        # 1. Check Remote Match
        if job_remote == "REMOTE" and ("REMOTE" in pref_remote or "ANY" in pref_remote):
            score = 100.0
            status = "MATCH"
            rationale = "100% remote job perfectly aligns with candidate remote preference."
        elif job_remote == "HYBRID" and "HYBRID" in pref_remote:
            score = 90.0
            status = "MATCH"
            rationale = "Hybrid workplace model aligns with candidate work preferences."
        elif not has_job_loc and job_remote != "REMOTE":
            score = 65.0
            status = "UNAVAILABLE"
            rationale = "Specific job location not disclosed by employer; remote suitability pending review."
        elif has_job_loc and has_cand_loc:
            c_loc = candidate_location.lower()
            j_loc = job_location.lower()
            
            # Check country boundary mismatch
            if ("us only" in j_loc or "usa only" in j_loc or "united states" in j_loc) and ("india" in c_loc or "uk" in c_loc or "canada" in c_loc):
                score = 20.0
                status = "MISMATCH"
                rationale = f"Geographic eligibility mismatch: Job requires US residency ({job_location}) while candidate is located in {candidate_location}."
            elif any(d.lower() in j_loc for d in (desired_locations or [])):
                score = 100.0
                status = "MATCH"
                rationale = f"Job location ({job_location}) matches candidate desired location target."
            elif c_loc in j_loc or j_loc in c_loc:
                score = 100.0
                status = "MATCH"
                rationale = f"Candidate location ({candidate_location}) directly matches job location ({job_location})."
            elif job_remote in pref_remote:
                score = 80.0
                status = "PARTIAL"
                rationale = f"Workplace type ({job_remote}) matches, though located in {job_location}."
            else:
                score = 40.0
                status = "MISMATCH"
                rationale = f"Location mismatch: Job is onsite in {job_location}."
        else:
            score = 70.0
            status = "PARTIAL"
            rationale = "Location parameters are partially specified."

        score = round(max(0.0, min(100.0, score)), 1)
        contribution = round((score * weight) / 100.0, 2)

        return DimensionScore(
            score=score,
            weight=weight,
            contribution=contribution,
            status=status,
            details={
                "candidate_location": candidate_location or "UNSPECIFIED",
                "job_location": job_location or "UNSPECIFIED",
                "job_remote_type": job_remote,
                "location_information_available": has_job_loc or job_remote == "REMOTE"
            },
            rationale=rationale
        )
