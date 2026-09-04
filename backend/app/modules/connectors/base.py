from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.shared.constants import PlatformCapability, ConnectorStatus, AuthorizationType
from app.modules.jobs.connectors.base import NormalizedJob
from app.modules.applications.connectors.base import ApplicationSubmissionResult

class PlatformCapabilityDeclaration(BaseModel):
    slug: str
    name: str
    supported_capabilities: List[PlatformCapability]
    status: ConnectorStatus
    authorization_type: AuthorizationType
    api_version: str = "v1"
    terms_reference: str = "Official Developer Terms of Service"
    rate_limit_policy: str = "60 req/min"
    is_auto_apply_supported: bool = False
    is_external_application_required: bool = True
    docs_url: Optional[str] = None
    notes: str = ""

class JobPlatformConnector(ABC):
    """Unified production interface for job discovery and authorized application connectors."""

    def __init__(self, name: str, slug: str, base_url: Optional[str] = None):
        self.name = name
        self.slug = slug
        self.base_url = base_url

    @abstractmethod
    def get_capabilities(self) -> PlatformCapabilityDeclaration:
        """Returns the formal capability declaration for this platform connector."""
        pass

    async def authenticate(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Performs authentication or token exchange if supported."""
        cap = self.get_capabilities()
        if cap.authorization_type == AuthorizationType.NO_AUTH:
            return {"status": "NO_AUTH_REQUIRED", "message": "Public connector, no credentials needed."}
        if cap.authorization_type == AuthorizationType.UNSUPPORTED:
            raise NotImplementedError(f"Authentication not supported for {self.name}.")
        return {"status": "AUTHENTICATED", "provider": self.slug}

    async def disconnect(self, user_id: Optional[str] = None) -> bool:
        """Disconnects / revokes user authorization if applicable."""
        return True

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
    async def get_job(self, external_job_id: str) -> Optional[NormalizedJob]:
        """Retrieve full details for a specific external job ID."""
        pass

    async def get_application_status(self, external_application_id: str) -> Dict[str, Any]:
        """Fetches status of an external application if supported."""
        cap = self.get_capabilities()
        if PlatformCapability.APPLICATION_STATUS_TRACKING not in cap.supported_capabilities:
            return {
                "status": "UNSUPPORTED",
                "message": f"Status tracking not supported by {self.name} API."
            }
        return {"status": "SUBMITTED", "external_application_id": external_application_id}

    async def submit_application(
        self,
        prepared_payload: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> ApplicationSubmissionResult:
        """Submits an application via authorized API. Unsupported platforms return structured error."""
        cap = self.get_capabilities()
        if not cap.is_auto_apply_supported or PlatformCapability.AUTO_APPLY not in cap.supported_capabilities:
            return ApplicationSubmissionResult(
                success=False,
                status="EXTERNAL_APPLICATION_REQUIRED",
                response_code=400,
                error_code="EXTERNAL_APPLICATION_REQUIRED",
                error_message=f"Platform '{self.name}' requires candidate to apply via official employer portal."
            )
        raise NotImplementedError("submit_application must be implemented by authorized provider adapter.")

    def get_rate_limits(self) -> Dict[str, Any]:
        """Returns rate limit status and remaining quota."""
        cap = self.get_capabilities()
        return {
            "policy": cap.rate_limit_policy,
            "requests_per_minute": 60,
            "is_rate_limited": False
        }
