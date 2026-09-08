import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from app.core.config import settings
from app.modules.jobs.connectors.base import NormalizedJob
from app.modules.jobs.discovery.greenhouse import GreenhouseDiscoveryProvider
from app.modules.jobs.discovery.lever import LeverDiscoveryProvider
from app.modules.jobs.discovery.public_feeds import (
    RemotiveDiscoveryProvider,
    ArbeitnowDiscoveryProvider,
    JobicyDiscoveryProvider
)
from app.modules.jobs.discovery.aggregators import JSearchAggregatorProvider, SerpApiAggregatorProvider

logger = logging.getLogger("app.jobs.discovery.orchestrator")

class JobDiscoveryOrchestrator:
    """Central orchestrator for live job discovery across all 7 platform categories with failure isolation."""

    def __init__(self):
        self.greenhouse = GreenhouseDiscoveryProvider()
        self.lever = LeverDiscoveryProvider()
        self.remotive = RemotiveDiscoveryProvider()
        self.arbeitnow = ArbeitnowDiscoveryProvider()
        self.jobicy = JobicyDiscoveryProvider()
        self.jsearch = JSearchAggregatorProvider()
        self.serpapi = SerpApiAggregatorProvider()

    async def discover_for_platform(
        self,
        platform_slug: str,
        query: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 30
    ) -> List[NormalizedJob]:
        """Discovers real jobs for a specific platform category with failure isolation."""
        platform = platform_slug.lower()
        results: List[NormalizedJob] = []

        if platform in ["career_pages", "greenhouse", "lever", "authorized_api"]:
            # Direct employer ATS discovery: Greenhouse + Lever ONLY
            tasks = [
                self.greenhouse.discover_jobs(query=query, location=location, limit=limit),
                self.lever.discover_jobs(query=query, location=location, limit=limit),
            ]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in raw_results:
                if isinstance(res, list):
                    results.extend(res)
                elif isinstance(res, Exception):
                    logger.warning(f"[orchestrator] Error during career_pages discovery: {res}")

        elif platform in ["aggregated_feeds", "public_feeds"]:
            # Third-Party Aggregated Job Feeds: Remotive + Arbeitnow + Jobicy
            if getattr(settings, "PUBLIC_FEEDS_ENABLED", True):
                tasks = [
                    self.remotive.discover_jobs(query=query, location=location, limit=limit // 2),
                    self.arbeitnow.discover_jobs(query=query, location=location, limit=limit // 2),
                    self.jobicy.discover_jobs(query=query, location=location, limit=limit // 2),
                ]
                raw_results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in raw_results:
                    if isinstance(res, list):
                        results.extend(res)
                    elif isinstance(res, Exception):
                        logger.warning(f"[orchestrator] Error during aggregated_feeds discovery: {res}")

        elif platform in ["linkedin", "indeed", "naukri", "internshala", "unstop", "wellfound"]:
            # Closed Portals: Query JSearch aggregator ONLY if configured
            if self.jsearch.is_configured():
                try:
                    j_jobs = await self.jsearch.discover_jobs(query=query, location=location, limit=limit, target_platform=platform)
                    results.extend(j_jobs)
                except Exception as e:
                    logger.warning(f"[orchestrator] JSearch error for {platform}: {e}")
            else:
                # Option B: Do NOT falsely relabel feeds as LinkedIn, Naukri, etc.
                logger.info(f"[orchestrator] Platform '{platform}' has no configured direct aggregator. Returning 0 jobs to preserve honest provenance.")

        # Deduplicate in-memory before returning
        deduped: List[NormalizedJob] = []
        seen_keys = set()
        for job in results:
            key = (job.company.strip().lower(), job.title.strip().lower(), job.external_job_id)
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(job)

        logger.info(f"[orchestrator] Discovered {len(deduped)} real jobs for platform '{platform_slug}'")
        return deduped[:limit]

    async def run_discovery_all(
        self,
        candidate_keywords: Optional[List[str]] = None,
        candidate_location: Optional[str] = None
    ) -> Dict[str, List[NormalizedJob]]:
        """Runs live discovery across all 7 primary sources simultaneously with failure isolation."""
        query_str = " ".join(candidate_keywords[:3]) if candidate_keywords else "software developer"
        SEVEN_PRIMARY = ["career_pages", "naukri", "indeed", "unstop", "linkedin", "internshala", "wellfound"]

        tasks = [
            self.discover_for_platform(slug, query=query_str, location=candidate_location, limit=30)
            for slug in SEVEN_PRIMARY
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        platform_jobs_map: Dict[str, List[NormalizedJob]] = {}
        for slug, res in zip(SEVEN_PRIMARY, results_list):
            if isinstance(res, list):
                platform_jobs_map[slug] = res
            else:
                logger.error(f"[orchestrator] Platform '{slug}' discovery raised unhandled exception: {res}")
                platform_jobs_map[slug] = []

        return platform_jobs_map

_global_orchestrator: Optional[JobDiscoveryOrchestrator] = None

def get_discovery_orchestrator() -> JobDiscoveryOrchestrator:
    global _global_orchestrator
    if _global_orchestrator is None:
        _global_orchestrator = JobDiscoveryOrchestrator()
    return _global_orchestrator
