from typing import Dict, Any, List, Tuple, Optional
from app.modules.applications.connectors.base import ApplicationConnector, ApplicationSubmissionResult
from app.modules.applications.connectors.mock_connector import MockApplicationConnector

class ReadOnlyDiscoveryAdapter(ApplicationConnector):
    """Adapter for discovery-only platforms that do not provide automated submission APIs."""

    def __init__(self, name: str, slug: str, capability: str = "EXTERNAL_APPLICATION_REQUIRED"):
        super().__init__(name=name, slug=slug)
        self.capability = capability

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "auto_apply_supported": False,
            "external_application_supported": (self.capability == "EXTERNAL_APPLICATION_REQUIRED"),
            "job_discovery_supported": True,
            "authentication_required": True,
            "captcha_present": False,
            "api_supported": False
        }

    async def prepare_application(
        self,
        external_job_id: str,
        candidate_data: Dict[str, Any],
        mapped_answers: List[Dict[str, Any]],
        resume_url: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "external_job_id": external_job_id,
            "source_slug": self.slug,
            "external_url_required": True
        }

    async def validate_application(self, prepared_payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
        return False, [f"Platform '{self.name}' requires manual external application submission."]

    async def submit_application(
        self,
        prepared_payload: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> ApplicationSubmissionResult:
        return ApplicationSubmissionResult(
            success=False,
            status="AUTO_APPLY_UNSUPPORTED",
            response_code=400,
            error_code="EXTERNAL_APPLICATION_REQUIRED",
            error_message=f"Platform '{self.name}' requires candidate to apply via official employer portal."
        )

    async def get_submission_status(self, external_application_id: str) -> Dict[str, Any]:
        return {"status": "UNSUPPORTED"}

# Global Registry
_CONNECTORS: Dict[str, ApplicationConnector] = {
    "mock_ats": MockApplicationConnector(mode="SUCCESS"),
    "greenhouse": ReadOnlyDiscoveryAdapter("Greenhouse", "greenhouse", "EXTERNAL_APPLICATION_REQUIRED"),
    "lever": ReadOnlyDiscoveryAdapter("Lever", "lever", "EXTERNAL_APPLICATION_REQUIRED"),
    "linkedin": ReadOnlyDiscoveryAdapter("LinkedIn Jobs", "linkedin", "EXTERNAL_APPLICATION_REQUIRED"),
    "indeed": ReadOnlyDiscoveryAdapter("Indeed", "indeed", "EXTERNAL_APPLICATION_REQUIRED"),
    "naukri": ReadOnlyDiscoveryAdapter("Naukri", "naukri", "EXTERNAL_APPLICATION_REQUIRED"),
    "unstop": ReadOnlyDiscoveryAdapter("Unstop", "unstop", "EXTERNAL_APPLICATION_REQUIRED"),
    "internshala": ReadOnlyDiscoveryAdapter("Internshala", "internshala", "EXTERNAL_APPLICATION_REQUIRED"),
    "wellfound": ReadOnlyDiscoveryAdapter("Wellfound", "wellfound", "EXTERNAL_APPLICATION_REQUIRED"),
}

def get_application_connector(source_slug: Optional[str] = None) -> ApplicationConnector:
    """Returns the application connector for a given source slug, defaulting to MockApplicationConnector if unspecified."""
    if not source_slug:
        return _CONNECTORS["mock_ats"]
    return _CONNECTORS.get(source_slug.lower(), _CONNECTORS["mock_ats"])
