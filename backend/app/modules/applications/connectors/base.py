from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
from pydantic import BaseModel, Field

class ApplicationSubmissionResult(BaseModel):
    success: bool
    status: str  # "SUBMITTED", "FAILED", "RETRYING", "AUTO_APPLY_UNSUPPORTED", "RATE_LIMITED"
    external_application_id: Optional[str] = None
    response_code: Optional[int] = 200
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    is_transient_error: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)

class ApplicationConnector(ABC):
    """Platform-independent interface for ATS and job portal application submission."""

    def __init__(self, name: str, slug: str):
        self.name = name
        self.slug = slug

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Returns connector capabilities such as:
        {
            "auto_apply_supported": bool,
            "external_application_supported": bool,
            "job_discovery_supported": bool,
            "authentication_required": bool,
            "captcha_present": bool,
            "api_supported": bool
        }
        """
        pass

    @abstractmethod
    async def prepare_application(
        self,
        external_job_id: str,
        candidate_data: Dict[str, Any],
        mapped_answers: List[Dict[str, Any]],
        resume_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Maps candidate profile and answers into platform-specific submission payload."""
        pass

    @abstractmethod
    async def validate_application(self, prepared_payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validates that all required fields for the platform are present and valid."""
        pass

    @abstractmethod
    async def submit_application(
        self,
        prepared_payload: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> ApplicationSubmissionResult:
        """Executes the application submission to the authorized platform integration."""
        pass

    @abstractmethod
    async def get_submission_status(self, external_application_id: str) -> Dict[str, Any]:
        """Queries status of an already submitted application."""
        pass
