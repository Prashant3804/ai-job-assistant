from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class JobCapability(str, Enum):
    JOB_DISCOVERY = "JOB_DISCOVERY"
    AUTO_APPLY = "AUTO_APPLY"
    EXTERNAL_APPLICATION = "EXTERNAL_APPLICATION"
    UNSUPPORTED = "UNSUPPORTED"

class NormalizedJob(BaseModel):
    job_id: Optional[str] = None
    source: str
    external_job_id: str
    company: str
    title: str
    description: str
    requirements: List[str] = []
    skills: List[str] = []
    experience_required: str = "MID_LEVEL"  # "ENTRY", "MID_LEVEL", "SENIOR", "LEAD"
    education_required: Optional[str] = "Bachelor's Degree in Computer Science or related field"
    location: str = "Remote"
    remote_type: str = "REMOTE"  # "REMOTE", "HYBRID", "ONSITE"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "USD"
    employment_type: str = "FULL_TIME"  # "FULL_TIME", "CONTRACT", "INTERNSHIP", "PART_TIME"
    application_url: str
    posted_at: Optional[str] = None
    deadline: Optional[str] = None
    source_metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseJobConnector(ABC):
    def __init__(self, name: str, slug: str, base_url: Optional[str] = None):
        self.name = name
        self.slug = slug
        self.base_url = base_url

    @abstractmethod
    async def search_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        remote: Optional[str] = None,
        salary: Optional[int] = None,
        experience: Optional[str] = None,
        employment_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> List[NormalizedJob]:
        """Search and retrieve jobs matching query filters."""
        pass

    @abstractmethod
    async def get_job_details(self, external_job_id: str) -> Optional[NormalizedJob]:
        """Retrieve full details for a specific external job ID."""
        pass

    @abstractmethod
    def normalize_job(self, raw_data: Dict[str, Any]) -> NormalizedJob:
        """Standardize raw platform payload into normalized candidate-ready job model."""
        pass

    @abstractmethod
    def get_source_status(self) -> Dict[str, Any]:
        """Returns health, connectivity status, and rate limit status of the connector."""
        pass

    @abstractmethod
    def get_application_capabilities(self) -> JobCapability:
        """Returns the supported application capability."""
        pass
