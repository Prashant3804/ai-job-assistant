import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import httpx

from app.core.config import settings
from app.modules.jobs.connectors.base import NormalizedJob

logger = logging.getLogger("app.jobs.discovery")

class BaseDiscoveryProvider(ABC):
    """Abstract base class for all job discovery providers with failure isolation."""

    def __init__(self, name: str, provider_id: str, timeout: Optional[int] = None):
        self.name = name
        self.provider_id = provider_id
        self.timeout = timeout or getattr(settings, "DISCOVERY_TIMEOUT_SECONDS", 15)
        self.max_retries = getattr(settings, "DISCOVERY_MAX_RETRIES", 2)

    @abstractmethod
    async def discover_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 50
    ) -> List[NormalizedJob]:
        """Discovers jobs from external feed/API with failure isolation."""
        pass

    async def _safe_get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[httpx.Response]:
        """Performs GET request with timeout, retries, exponential backoff, and failure isolation."""
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        if headers:
            default_headers.update(headers)

        for attempt in range(1, self.max_retries + 2):
            try:
                async with httpx.AsyncClient(timeout=float(self.timeout), follow_redirects=True) as client:
                    resp = await client.get(url, headers=default_headers, params=params)
                    if resp.status_code == 200:
                        return resp
                    elif resp.status_code == 429:
                        logger.warning(f"[{self.provider_id}] Rate limited (429) at {url}. Backing off.")
                        await asyncio.sleep(1.0 * attempt)
                    elif resp.status_code >= 500:
                        logger.warning(f"[{self.provider_id}] Server error ({resp.status_code}) at {url}. Attempt {attempt}/{self.max_retries + 1}")
                        await asyncio.sleep(1.0 * attempt)
                    else:
                        logger.info(f"[{self.provider_id}] Non-success HTTP status {resp.status_code} for {url}")
                        return resp
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                logger.warning(f"[{self.provider_id}] Network timeout/connect error for {url}: {exc}. Attempt {attempt}")
                if attempt <= self.max_retries:
                    await asyncio.sleep(1.0 * attempt)
            except Exception as exc:
                logger.error(f"[{self.provider_id}] Unexpected error querying {url}: {exc}")
                break

        return None

    @staticmethod
    def normalize_remote_type(val: Optional[str], loc_str: Optional[str] = "") -> str:
        s = f"{val or ''} {loc_str or ''}".lower()
        if any(w in s for w in ["remote", "work from home", "telecommute", "wfh", "anywhere"]):
            return "REMOTE"
        if any(w in s for w in ["hybrid", "flexible"]):
            return "HYBRID"
        if any(w in s for w in ["onsite", "in office", "on-site"]):
            return "ONSITE"
        return "HYBRID" if loc_str and loc_str.strip() else "REMOTE"

    @staticmethod
    def normalize_employment_type(title: str, raw_emp: Optional[str] = "") -> str:
        s = f"{title} {raw_emp or ''}".lower()
        if any(w in s for w in ["intern", "trainee", "apprenticeship"]):
            return "INTERNSHIP"
        if any(w in s for w in ["contract", "contractor", "freelance", "temp"]):
            return "CONTRACT"
        if any(w in s for w in ["part-time", "part time"]):
            return "PART_TIME"
        return "FULL_TIME"

    @staticmethod
    def normalize_experience_level(title: str, raw_exp: Optional[str] = "") -> str:
        s = f"{title} {raw_exp or ''}".lower()
        if any(w in s for w in ["principal", "staff", "architect", "lead", "director"]):
            return "LEAD"
        if any(w in s for w in ["senior", "sr.", "sr ", "experienced"]):
            return "SENIOR"
        if any(w in s for w in ["junior", "jr.", "jr ", "entry", "intern", "associate", "graduate", "fresher"]):
            return "ENTRY"
        return "MID_LEVEL"
