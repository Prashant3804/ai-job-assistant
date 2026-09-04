import re
from typing import List, Set, Dict, Tuple, Any
from app.modules.matching.constants import SKILL_ALIASES
from app.modules.matching.schemas import DimensionScore

class SkillMatcher:
    """Intelligent Skill Matcher supporting canonical aliases and required vs preferred separation."""

    @classmethod
    def normalize_skill(cls, skill_name: str) -> str:
        if not skill_name:
            return ""
        clean = skill_name.strip().lower()
        # Remove version indicators like "python 3.10" -> "python"
        clean = re.sub(r"\s+v?\d+(\.\d+)*$", "", clean)
        clean = re.sub(r"[^\w\.\-\+#]", "", clean)
        return SKILL_ALIASES.get(clean, clean)

    @classmethod
    def match(
        cls,
        candidate_skills: List[str],
        job_required_skills: List[str],
        job_preferred_skills: List[str],
        weight: float = 35.0
    ) -> Tuple[DimensionScore, List[str], List[str], List[str]]:
        """
        Evaluate candidate skills against job requirements.
        Returns: (DimensionScore, matched_skills, missing_required_skills, missing_preferred_skills)
        """
        cand_norm_map: Dict[str, str] = {}
        for s in candidate_skills:
            norm = cls.normalize_skill(s)
            if norm:
                cand_norm_map[norm] = s

        matched_skills: List[str] = []
        missing_required: List[str] = []
        missing_preferred: List[str] = []

        req_norm = [cls.normalize_skill(s) for s in job_required_skills if cls.normalize_skill(s)]
        pref_norm = [cls.normalize_skill(s) for s in job_preferred_skills if cls.normalize_skill(s)]

        # 1. Match Required Skills
        matched_req_count = 0
        if req_norm:
            for orig, norm in zip(job_required_skills, req_norm):
                # Check direct or substring match
                is_matched = False
                for c_norm, c_orig in cand_norm_map.items():
                    if norm == c_norm or (len(norm) >= 3 and norm in c_norm) or (len(c_norm) >= 3 and c_norm in norm):
                        is_matched = True
                        if c_orig not in matched_skills:
                            matched_skills.append(c_orig)
                        break
                if is_matched:
                    matched_req_count += 1
                else:
                    missing_required.append(orig)
            req_ratio = matched_req_count / len(req_norm)
        else:
            # If no explicit required skills listed on job, candidate gets neutral baseline
            req_ratio = 0.85
            matched_skills = candidate_skills[:5]

        # 2. Match Preferred Skills
        matched_pref_count = 0
        if pref_norm:
            for orig, norm in zip(job_preferred_skills, pref_norm):
                is_matched = False
                for c_norm, c_orig in cand_norm_map.items():
                    if norm == c_norm or (len(norm) >= 3 and norm in c_norm) or (len(c_norm) >= 3 and c_norm in norm):
                        is_matched = True
                        if c_orig not in matched_skills:
                            matched_skills.append(c_orig)
                        break
                if is_matched:
                    matched_pref_count += 1
                else:
                    missing_preferred.append(orig)
            pref_ratio = matched_pref_count / len(pref_norm)
        else:
            pref_ratio = 1.0

        # Weighted calculation: Required skills account for 75%, preferred account for 25%
        if req_norm and pref_norm:
            raw_score = (req_ratio * 75.0) + (pref_ratio * 25.0)
        elif req_norm:
            raw_score = req_ratio * 100.0
        elif pref_norm:
            raw_score = 50.0 + (pref_ratio * 50.0)
        else:
            raw_score = 80.0

        score = round(max(0.0, min(100.0, raw_score)), 1)
        contribution = round((score * weight) / 100.0, 2)

        if score >= 80.0:
            status = "MATCH"
            rationale = f"Strong technical skill match ({len(matched_skills)} matched)."
        elif score >= 50.0:
            status = "PARTIAL"
            rationale = f"Partial skill match ({len(missing_required)} required skills missing)."
        else:
            status = "MISMATCH"
            rationale = f"Low skill alignment; missing key required skills: {', '.join(missing_required[:3])}."

        dimension = DimensionScore(
            score=score,
            weight=weight,
            contribution=contribution,
            status=status,
            details={
                "matched_count": len(matched_skills),
                "missing_required_count": len(missing_required),
                "missing_preferred_count": len(missing_preferred),
                "req_ratio": round(req_ratio, 2) if req_norm else 1.0,
                "pref_ratio": round(pref_ratio, 2) if pref_norm else 1.0,
            },
            rationale=rationale
        )

        return dimension, matched_skills, missing_required, missing_preferred
