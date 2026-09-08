import re
from typing import List, Optional, Dict, Any
from app.modules.matching.schemas import DimensionScore

ROLE_CLUSTERS = {
    "software_engineering": {
        "software engineer", "software developer", "sde", "sde i", "sde ii", "sde iii",
        "backend engineer", "backend developer", "frontend engineer", "frontend developer",
        "full stack engineer", "full stack developer", "fullstack developer", "fullstack engineer",
        "full-stack engineer", "full-stack developer",
        "web developer", "web engineer", "applications engineer", "systems engineer",
        "react developer", "react engineer", "python developer", "python engineer",
        "java developer", "java engineer", "node developer", "node engineer",
        "mobile developer", "ios developer", "android developer"
    },
    "data_ai": {
        "data engineer", "data scientist", "machine learning engineer",
        "ai engineer", "ml engineer", "data analyst", "business intelligence analyst",
        "analytics engineer", "nlp engineer", "deep learning engineer"
    },
    "devops_cloud": {
        "devops engineer", "site reliability engineer", "sre", "cloud engineer",
        "infrastructure engineer", "platform engineer", "systems administrator"
    },
    "product_design": {
        "product manager", "product owner", "ui/ux designer", "graphic designer",
        "product designer", "interaction designer"
    }
}

class RoleMatcher:
    """Job role & title compatibility matcher."""

    @classmethod
    def _normalize_title(cls, title: str) -> str:
        clean = title.lower().strip()
        clean = re.sub(r"\(.*?\)", "", clean)
        clean = re.sub(r"\b(senior|junior|lead|principal|staff|associate|entry level|intern)\b", "", clean)
        return re.sub(r"\s+", " ", clean).strip()

    @classmethod
    def _get_cluster(cls, title: str) -> Optional[str]:
        norm = cls._normalize_title(title)
        for cluster_name, titles in ROLE_CLUSTERS.items():
            if any(t in norm or norm in t for t in titles):
                return cluster_name
        if any(w in norm for w in ["developer", "engineer", "programmer", "architect", "coder"]):
            if any(w in norm for w in ["data", "ml", "ai", "machine learning"]):
                return "data_ai"
            if any(w in norm for w in ["devops", "sre", "cloud", "infra", "platform"]):
                return "devops_cloud"
            return "software_engineering"
        return None

    @classmethod
    def match(
        cls,
        candidate_target_roles: List[str],
        candidate_headline: Optional[str],
        job_title: str,
        weight: float = 10.0
    ) -> DimensionScore:
        norm_job = cls._normalize_title(job_title)
        job_cluster = cls._get_cluster(job_title)

        cand_titles = list(candidate_target_roles or [])
        if candidate_headline:
            cand_titles.append(candidate_headline)

        if not cand_titles:
            # Neutral default if candidate hasn't configured target roles
            score = 80.0
            status = "MATCH"
            rationale = f"Role title evaluated as {job_title}."
        else:
            is_direct_match = False
            is_cluster_match = False

            for ct in cand_titles:
                norm_cand = cls._normalize_title(ct)
                cand_cluster = cls._get_cluster(ct)
                
                if norm_cand in norm_job or norm_job in norm_cand:
                    is_direct_match = True
                    break
                if job_cluster and cand_cluster and job_cluster == cand_cluster:
                    is_cluster_match = True

            if is_direct_match:
                score = 100.0
                status = "MATCH"
                rationale = f"Job title '{job_title}' directly matches candidate target role profile."
            elif is_cluster_match:
                score = 85.0
                status = "MATCH"
                rationale = f"Job title '{job_title}' is closely related to candidate domain focus."
            else:
                score = 35.0
                status = "MISMATCH"
                rationale = f"Role mismatch: Job is for '{job_title}' which diverges from candidate targets ({', '.join(cand_titles[:2])})."

        score = round(max(0.0, min(100.0, score)), 1)
        contribution = round((score * weight) / 100.0, 2)

        return DimensionScore(
            score=score,
            weight=weight,
            contribution=contribution,
            status=status,
            details={
                "candidate_roles": cand_titles,
                "job_title": job_title,
                "job_cluster": job_cluster or "OTHER"
            },
            rationale=rationale
        )
