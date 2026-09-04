import re
import hashlib
from typing import List, Dict, Any, Optional
from app.modules.jobs.connectors.base import NormalizedJob

# Priority ranking: Higher number = Higher preference
SOURCE_PRIORITY_SCORES: Dict[str, int] = {
    "greenhouse": 100,
    "lever": 100,
    "career_pages": 90,
    "indeed": 80,
    "naukri": 75,
    "wellfound": 70,
    "linkedin": 70,
    "internshala": 60,
    "unstop": 60,
    "mock_ats": 50,
}

class SourcePriorityEngine:
    """Prioritizes authorized direct ATS sources and deduplicates jobs across multi-provider sources."""

    @staticmethod
    def get_source_score(source_slug: str) -> int:
        return SOURCE_PRIORITY_SCORES.get(source_slug.lower(), 50)

    @staticmethod
    def compute_canonical_hash(company: str, title: str, location: str) -> str:
        """Generates a normalized SHA-256 fingerprint for cross-platform deduplication."""
        def clean(s: str) -> str:
            if not s:
                return ""
            s = s.lower().strip()
            # Remove common suffixes like Inc, LLC, Corp, Ltd
            s = re.sub(r"\b(inc|llc|corp|corporation|ltd|limited|pvt|co)\b", "", s)
            # Remove punctuation and extra whitespace
            s = re.sub(r"[^\w\s]", "", s)
            return " ".join(s.split())

        norm_comp = clean(company)
        norm_title = clean(title)
        norm_loc = clean(location)
        raw = f"{norm_comp}::{norm_title}::{norm_loc}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def deduplicate_and_prioritize(cls, jobs: List[NormalizedJob]) -> List[NormalizedJob]:
        """Deduplicates a mixed list of jobs from multiple providers, keeping the highest-priority source for each job."""
        grouped: Dict[str, List[NormalizedJob]] = {}
        for job in jobs:
            c_hash = cls.compute_canonical_hash(job.company, job.title, job.location)
            if c_hash not in grouped:
                grouped[c_hash] = []
            grouped[c_hash].append(job)

        deduped: List[NormalizedJob] = []
        for c_hash, variants in grouped.items():
            # Sort by source priority descending
            variants.sort(
                key=lambda j: cls.get_source_score(j.source_metadata.get("connector", j.source)),
                reverse=True
            )
            # Pick highest priority variant
            deduped.append(variants[0])

        return deduped
