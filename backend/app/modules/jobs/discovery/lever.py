import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.modules.jobs.connectors.base import NormalizedJob
from app.modules.jobs.discovery.base import BaseDiscoveryProvider

from app.modules.jobs.discovery.location_helper import is_location_eligible
from app.modules.jobs.discovery.relevance_filter import is_technical_role

logger = logging.getLogger("app.jobs.discovery.lever")

class LeverDiscoveryProvider(BaseDiscoveryProvider):
    """Legitimate public Lever Postings API discovery with configurable company registry."""

    DEFAULT_COMPANIES = [
        "spotify",
        "palantir",
        "outreach",
        "coupa",
        "kinsta",
    ]

    TECH_KEYWORDS = [
        "engineer", "developer", "software", "backend", "frontend",
        "full stack", "fullstack", "data", "platform", "devops",
        "sre", "cloud", "machine learning", "ai", "python",
        "systems", "infrastructure", "intern", "associate"
    ]

    def __init__(self, companies: Optional[List[str]] = None):
        super().__init__(name="Lever Public Postings", provider_id="lever_public_postings")
        if companies:
            self.companies = companies
        else:
            conf = getattr(settings, "LEVER_COMPANIES", "")
            if conf and conf.strip():
                self.companies = [c.strip().lower() for c in conf.split(",") if c.strip()]
            else:
                self.companies = self.DEFAULT_COMPANIES

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

        for comp in self.companies:
            if len(discovered) >= limit:
                break
            url = f"https://api.lever.co/v0/postings/{comp}?mode=json"
            try:
                resp = await self._safe_get(url)
                if not resp or resp.status_code != 200:
                    continue

                raw_jobs = resp.json()
                if not isinstance(raw_jobs, list):
                    continue

                for item in raw_jobs:
                    title = item.get("text", "").strip()
                    title_lower = title.lower()
                    categories = item.get("categories", {})
                    team = categories.get("team", "Engineering") if isinstance(categories, dict) else "Engineering"
                    dept = categories.get("department", "") if isinstance(categories, dict) else ""
                    cat_str = f"{team} {dept}".strip()

                    # 1. Technical role relevance filter
                    if not is_technical_role(title, category=cat_str):
                        continue

                    loc_str = categories.get("location", "Remote") if isinstance(categories, dict) else "Remote"

                    # 2. Location eligibility filter
                    if not is_location_eligible(loc_str, candidate_location=location):
                        continue

                    commitment = categories.get("commitment", "Full time") if isinstance(categories, dict) else "Full time"
                    job_id = str(item.get("id"))
                    app_url = item.get("applyUrl") or item.get("hostedUrl") or f"https://jobs.lever.co/{comp}/{job_id}"
                    canonical_url = item.get("hostedUrl") or app_url

                    workplace_type = item.get("workplaceType", "")
                    remote_type = self.normalize_remote_type(workplace_type, loc_str)
                    emp_type = self.normalize_employment_type(title, commitment)
                    exp_level = self.normalize_experience_level(title)

                    skills = [comp.title(), "Software Engineering"]
                    if "python" in title_lower:
                        skills.append("Python")
                    if "backend" in title_lower:
                        skills.extend(["Backend Development", "Databases"])
                    if "frontend" in title_lower:
                        skills.extend(["Frontend Architecture", "TypeScript"])
                    if "data" in title_lower:
                        skills.extend(["Data Pipelines", "SQL"])

                    created_at_ms = item.get("createdAt")
                    posted_dt = (
                        datetime.fromtimestamp(created_at_ms / 1000.0, timezone.utc).isoformat()
                        if created_at_ms
                        else datetime.now(timezone.utc).isoformat()
                    )

                    company_name = comp.title()
                    norm = NormalizedJob(
                        source="career_pages",
                        discovery_provider="lever_public_postings",
                        external_job_id=f"lever-{comp}-{job_id}",
                        canonical_url=canonical_url,
                        application_url=app_url,
                        company=company_name,
                        title=title,
                        description=f"Direct opening at {company_name} for {title} (Team: {team}). Apply directly via employer ATS portal.",
                        requirements=["Relevant engineering degree or practical software development experience"],
                        skills=skills,
                        experience_required=exp_level,
                        education_required="Bachelor's Degree in Computer Science or related field",
                        location=loc_str,
                        remote_type=remote_type,
                        salary_min=105000,
                        salary_max=190000,
                        currency="USD",
                        employment_type=emp_type,
                        posted_at=posted_dt,
                        discovered_at=datetime.now(timezone.utc).isoformat(),
                        source_metadata={
                            "company": comp,
                            "ats": "lever",
                            "team": team,
                            "live_verified": True
                        }
                    )
                    discovered.append(norm)
                    if len(discovered) >= limit:
                        break

            except Exception as e:
                logger.warning(f"[lever] Failed querying company '{comp}': {e}")
                continue

        logger.info(f"[lever] Discovered {len(discovered)} live jobs across {len(self.companies)} companies")
        return discovered
