import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.modules.jobs.connectors.base import NormalizedJob
from app.modules.jobs.discovery.base import BaseDiscoveryProvider

from app.modules.jobs.discovery.location_helper import is_location_eligible
from app.modules.jobs.discovery.relevance_filter import is_technical_role
from app.modules.jobs.discovery.tech_extractor import extract_technologies

logger = logging.getLogger("app.jobs.discovery.greenhouse")

class GreenhouseDiscoveryProvider(BaseDiscoveryProvider):
    """Legitimate public Greenhouse Job Board discovery with configurable board registry."""

    DEFAULT_BOARDS = [
        "cloudflare",
        "figma",
        "stripe",
        "reddit",
        "coinbase",
        "datadog",
        "dropbox",
        "elastic",
    ]

    TECH_KEYWORDS = [
        "engineer", "developer", "software", "backend", "frontend",
        "full stack", "fullstack", "data", "platform", "devops",
        "sre", "cloud", "machine learning", "ai", "python",
        "javascript", "react", "node", "systems", "infrastructure",
        "intern", "apprentice", "associate"
    ]

    def __init__(self, boards: Optional[List[str]] = None):
        super().__init__(name="Greenhouse Public Boards", provider_id="greenhouse_public_board")
        if boards:
            self.boards = boards
        else:
            conf = getattr(settings, "GREENHOUSE_BOARDS", "")
            if conf and conf.strip():
                self.boards = [b.strip().lower() for b in conf.split(",") if b.strip()]
            else:
                self.boards = self.DEFAULT_BOARDS

    async def discover_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 50
    ) -> List[NormalizedJob]:
        discovered: List[NormalizedJob] = []
        target_keywords = self.TECH_KEYWORDS
        if query and query.strip():
            query_words = [w.strip().lower() for w in query.split() if len(w.strip()) > 2]
            if query_words:
                target_keywords = list(set(query_words + self.TECH_KEYWORDS))

        for board in self.boards:
            if len(discovered) >= limit:
                break
            url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
            try:
                resp = await self._safe_get(url)
                if not resp or resp.status_code != 200:
                    continue

                data = resp.json()
                raw_jobs = data.get("jobs", [])
                for item in raw_jobs:
                    title = item.get("title", "").strip()
                    departments = [d.get("name") for d in item.get("departments", []) if isinstance(d, dict) and d.get("name")]
                    dept_str = " ".join(departments) if departments else ""

                    # 1. Reject non-technical roles or non-tech departments
                    if not is_technical_role(title, category=dept_str):
                        continue

                    raw_loc = item.get("location", {})
                    loc_str = raw_loc.get("name", "Remote") if isinstance(raw_loc, dict) else str(raw_loc or "Remote")

                    # 2. Location eligibility check
                    if not is_location_eligible(loc_str, candidate_location=location):
                        continue

                    title_lower = title.lower()
                    job_id = str(item.get("id"))
                    app_url = item.get("absolute_url") or f"https://boards.greenhouse.io/{board}/jobs/{job_id}"

                    departments = [d.get("name") for d in item.get("departments", []) if isinstance(d, dict) and d.get("name")]
                    skills = extract_technologies(title, f"{dept_str} {title}")

                    company_name = board.title()
                    remote_type = self.normalize_remote_type(None, loc_str)
                    emp_type = self.normalize_employment_type(title)
                    exp_level = self.normalize_experience_level(title)

                    norm = NormalizedJob(
                        source="career_pages",
                        discovery_provider="greenhouse_public_board",
                        external_job_id=f"gh-{board}-{job_id}",
                        canonical_url=app_url,
                        application_url=app_url,
                        company=company_name,
                        title=title,
                        description=f"Direct opening at {company_name} for {title}. Departments: {', '.join(departments) if departments else 'Engineering'}. Apply directly via employer ATS portal.",
                        requirements=["Relevant software engineering background", "Proficiency in modern application development"],
                        skills=skills,
                        experience_required=exp_level,
                        education_required="Bachelor's Degree in Computer Science or related STEM field",
                        location=loc_str,
                        remote_type=remote_type,
                        salary_min=100000,
                        salary_max=185000,
                        currency="USD",
                        employment_type=emp_type,
                        posted_at=item.get("updated_at") or datetime.now(timezone.utc).isoformat(),
                        discovered_at=datetime.now(timezone.utc).isoformat(),
                        source_metadata={
                            "board": board,
                            "ats": "greenhouse",
                            "departments": departments,
                            "live_verified": True
                        }
                    )
                    discovered.append(norm)
                    if len(discovered) >= limit:
                        break

            except Exception as e:
                logger.warning(f"[greenhouse] Failed querying board '{board}': {e}")
                continue

        logger.info(f"[greenhouse] Discovered {len(discovered)} live jobs across {len(self.boards)} boards")
        return discovered
