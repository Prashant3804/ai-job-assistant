import logging
from datetime import datetime, timezone
from typing import List, Optional
from app.modules.jobs.connectors.base import NormalizedJob
from app.modules.jobs.discovery.base import BaseDiscoveryProvider

from app.modules.jobs.discovery.location_helper import is_location_eligible
from app.modules.jobs.discovery.relevance_filter import is_technical_role

logger = logging.getLogger("app.jobs.discovery.public_feeds")

class RemotiveDiscoveryProvider(BaseDiscoveryProvider):
    """Legitimate public Remotive Remote Software Jobs API with technical filtering and location validation."""

    def __init__(self):
        super().__init__(name="Remotive Public API", provider_id="remotive_public_api")

    async def discover_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 30
    ) -> List[NormalizedJob]:
        url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=50"
        discovered: List[NormalizedJob] = []
        try:
            resp = await self._safe_get(url)
            if not resp or resp.status_code != 200:
                return []

            data = resp.json()
            jobs = data.get("jobs", [])
            for item in jobs:
                title = item.get("title", "").strip()
                category = item.get("category", "")
                tags = item.get("tags", [])

                # 1. Strict technical role relevance filter
                if not is_technical_role(title, category=category, tags=tags):
                    continue

                # 2. Candidate location eligibility filter
                req_loc = item.get("candidate_required_location") or "Worldwide"
                if not is_location_eligible(req_loc, candidate_location=location):
                    continue

                company = item.get("company_name", "Tech Employer")
                skills = tags if tags else ["Software Engineering", "Python"]
                app_url = item.get("url", "https://remotive.com")
                job_id = str(item.get("id"))

                norm = NormalizedJob(
                    source="aggregated_feeds",
                    discovery_provider="remotive_public_api",
                    external_job_id=f"remotive-{job_id}",
                    canonical_url=app_url,
                    application_url=app_url,
                    company=company,
                    title=title,
                    description=f"Direct opening at {company} for {title}. Remote engineering opportunity discovered via Remotive Public Feed. Skills: {', '.join(skills[:4])}.",
                    requirements=["Demonstrated experience in software development", "Independent remote work discipline"],
                    skills=skills[:6],
                    experience_required=self.normalize_experience_level(title),
                    education_required="Bachelor's Degree in Computer Science, STEM, or equivalent",
                    location=req_loc,
                    remote_type="REMOTE",
                    salary_min=None,
                    salary_max=None,
                    currency="USD",
                    employment_type=self.normalize_employment_type(title, item.get("job_type")),
                    posted_at=item.get("publication_date") or datetime.now(timezone.utc).isoformat(),
                    discovered_at=datetime.now(timezone.utc).isoformat(),
                    source_metadata={"provider": "remotive", "category": category, "live_verified": True}
                )
                discovered.append(norm)
                if len(discovered) >= limit:
                    break

        except Exception as e:
            logger.warning(f"[remotive] Error querying Remotive: {e}")

        return discovered

class ArbeitnowDiscoveryProvider(BaseDiscoveryProvider):
    """Legitimate public Arbeitnow Job Board API."""

    def __init__(self):
        super().__init__(name="Arbeitnow Public API", provider_id="arbeitnow_public_api")

    async def discover_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 30
    ) -> List[NormalizedJob]:
        url = "https://www.arbeitnow.com/api/job-board-api"
        discovered: List[NormalizedJob] = []
        try:
            resp = await self._safe_get(url)
            if not resp or resp.status_code != 200:
                return []

            data = resp.json()
            jobs = data.get("data", [])
            for item in jobs:
                title = item.get("title", "").strip()
                tags = item.get("tags", [])
                if not is_technical_role(title, tags=tags):
                    continue

                raw_loc = item.get("location") or ("Remote" if item.get("remote") else "Germany")
                if not is_location_eligible(raw_loc, candidate_location=location):
                    continue

                company = item.get("company_name", "Tech Employer")
                skills = tags if tags else ["Software Development"]
                app_url = item.get("url", "https://www.arbeitnow.com")
                job_id = str(item.get("slug", item.get("id", len(discovered))))

                norm = NormalizedJob(
                    source="aggregated_feeds",
                    discovery_provider="arbeitnow_public_api",
                    external_job_id=f"arbeitnow-{job_id}",
                    canonical_url=app_url,
                    application_url=app_url,
                    company=company,
                    title=title,
                    description=f"Direct opening at {company} for {title}. Discovered via Arbeitnow Public Feed.",
                    requirements=["Relevant technical experience in software systems"],
                    skills=skills[:6],
                    experience_required=self.normalize_experience_level(title),
                    education_required="Bachelor's Degree in Computer Science or related STEM discipline",
                    location=raw_loc,
                    remote_type="REMOTE" if item.get("remote") else "HYBRID",
                    salary_min=None,
                    salary_max=None,
                    currency="EUR",
                    employment_type=self.normalize_employment_type(title),
                    posted_at=datetime.now(timezone.utc).isoformat(),
                    discovered_at=datetime.now(timezone.utc).isoformat(),
                    source_metadata={"provider": "arbeitnow", "live_verified": True}
                )
                discovered.append(norm)
                if len(discovered) >= limit:
                    break

        except Exception as e:
            logger.warning(f"[arbeitnow] Error querying Arbeitnow: {e}")

        return discovered

class JobicyDiscoveryProvider(BaseDiscoveryProvider):
    """Legitimate public Jobicy Remote Jobs API."""

    def __init__(self):
        super().__init__(name="Jobicy Public API", provider_id="jobicy_public_api")

    async def discover_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 25
    ) -> List[NormalizedJob]:
        url = "https://jobicy.com/api/v2/remote-jobs?count=25&tag=dev"
        discovered: List[NormalizedJob] = []
        try:
            resp = await self._safe_get(url)
            if not resp or resp.status_code != 200:
                return []

            data = resp.json()
            jobs = data.get("jobs", [])
            for item in jobs:
                title = item.get("jobTitle", "").strip()
                if not is_technical_role(title):
                    continue

                geo = item.get("jobGeo") or "Worldwide"
                if not is_location_eligible(geo, candidate_location=location):
                    continue

                company = item.get("companyName", "Employer")
                app_url = item.get("url", "https://jobicy.com")
                job_id = str(item.get("id"))

                norm = NormalizedJob(
                    source="aggregated_feeds",
                    discovery_provider="jobicy_public_api",
                    external_job_id=f"jobicy-{job_id}",
                    canonical_url=app_url,
                    application_url=app_url,
                    company=company,
                    title=title,
                    description=f"Remote opportunity at {company} for {title}. Discovered via Jobicy Public Feed.",
                    requirements=["Relevant practical software engineering skills"],
                    skills=["Software Development", "Remote Engineering"],
                    experience_required=self.normalize_experience_level(title),
                    education_required="Bachelor's Degree in Computer Science or related field",
                    location=geo,
                    remote_type="REMOTE",
                    salary_min=item.get("annualSalaryMin"),
                    salary_max=item.get("annualSalaryMax"),
                    currency=item.get("salaryCurrency", "USD"),
                    employment_type=self.normalize_employment_type(title, item.get("jobType")),
                    posted_at=item.get("pubDate") or datetime.now(timezone.utc).isoformat(),
                    discovered_at=datetime.now(timezone.utc).isoformat(),
                    source_metadata={"provider": "jobicy", "live_verified": True}
                )
                discovered.append(norm)
                if len(discovered) >= limit:
                    break

        except Exception as e:
            logger.warning(f"[jobicy] Error querying Jobicy: {e}")

        return discovered
