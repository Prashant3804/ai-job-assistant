import uuid
import asyncio
from typing import Dict, Any, List, Tuple, Optional
from app.modules.applications.connectors.base import ApplicationConnector, ApplicationSubmissionResult

class MockApplicationConnector(ApplicationConnector):
    """
    Configurable Mock Application Connector for testing end-to-end auto-apply flows,
    rate limiting, failure handling, retry policies, and edge cases.
    """

    def __init__(self, mode: str = "SUCCESS"):
        super().__init__(name="Mock ATS Partner API", slug="mock_ats")
        self.mode = mode
        self.submitted_applications: List[Dict[str, Any]] = []
        self.submission_attempts = 0

    def set_mode(self, mode: str):
        self.mode = mode

    def get_capabilities(self) -> Dict[str, Any]:
        if self.mode == "UNSUPPORTED":
            return {
                "auto_apply_supported": False,
                "external_application_supported": False,
                "job_discovery_supported": True,
                "authentication_required": False,
                "captcha_present": False,
                "api_supported": False
            }
        if self.mode == "EXTERNAL_APPLICATION_REQUIRED":
            return {
                "auto_apply_supported": False,
                "external_application_supported": True,
                "job_discovery_supported": True,
                "authentication_required": True,
                "captcha_present": False,
                "api_supported": False
            }
        return {
            "auto_apply_supported": True,
            "external_application_supported": True,
            "job_discovery_supported": True,
            "authentication_required": True,
            "captcha_present": False,
            "api_supported": True
        }

    async def prepare_application(
        self,
        external_job_id: str,
        candidate_data: Dict[str, Any],
        mapped_answers: List[Dict[str, Any]],
        resume_url: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "job_id": external_job_id,
            "candidate": candidate_data,
            "answers": mapped_answers,
            "resume_url": resume_url or "/uploads/default_resume.pdf",
            "source_slug": self.slug
        }

    async def validate_application(self, prepared_payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
        candidate = prepared_payload.get("candidate", {})
        errors = []
        if not candidate.get("name"):
            errors.append("Candidate name is required by Mock ATS.")
        if not candidate.get("email"):
            errors.append("Candidate email is required by Mock ATS.")
        return len(errors) == 0, errors

    async def submit_application(
        self,
        prepared_payload: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> ApplicationSubmissionResult:
        self.submission_attempts += 1

        if self.mode == "SUCCESS":
            app_id = f"mock-app-{uuid.uuid4().hex[:10]}"
            self.submitted_applications.append({
                "external_application_id": app_id,
                "payload": prepared_payload,
                "idempotency_key": idempotency_key
            })
            return ApplicationSubmissionResult(
                success=True,
                status="SUBMITTED",
                external_application_id=app_id,
                response_code=201,
                details={"confirmation_number": f"CONF-{uuid.uuid4().hex[:8].upper()}"}
            )

        elif self.mode == "TIMEOUT":
            return ApplicationSubmissionResult(
                success=False,
                status="RETRYING",
                response_code=408,
                error_code="TIMEOUT",
                error_message="ATS connection timed out after 5000ms.",
                is_transient_error=True
            )

        elif self.mode == "RATE_LIMIT_429":
            return ApplicationSubmissionResult(
                success=False,
                status="RATE_LIMITED",
                response_code=429,
                error_code="RATE_LIMIT",
                error_message="429 Too Many Requests: Rate limit exceeded on platform.",
                is_transient_error=True
            )

        elif self.mode == "AUTH_ERROR_401":
            return ApplicationSubmissionResult(
                success=False,
                status="FAILED",
                response_code=401,
                error_code="UNAUTHORIZED",
                error_message="401 Unauthorized: Invalid integration partner credentials.",
                is_transient_error=False
            )

        elif self.mode == "SERVER_ERROR_500":
            return ApplicationSubmissionResult(
                success=False,
                status="RETRYING",
                response_code=500,
                error_code="SERVER_ERROR",
                error_message="500 Internal Server Error on partner platform.",
                is_transient_error=True
            )

        elif self.mode == "MALFORMED_RESPONSE":
            return ApplicationSubmissionResult(
                success=False,
                status="FAILED",
                response_code=502,
                error_code="MALFORMED_RESPONSE",
                error_message="Invalid or non-JSON response returned by platform gateway.",
                is_transient_error=False
            )

        elif self.mode == "DUPLICATE_EXTERNAL":
            return ApplicationSubmissionResult(
                success=False,
                status="DUPLICATE",
                response_code=409,
                error_code="DUPLICATE_APPLICATION",
                error_message="Platform rejected submission: Candidate has an existing active application for this job.",
                is_transient_error=False
            )

        elif self.mode == "UNSUPPORTED":
            return ApplicationSubmissionResult(
                success=False,
                status="AUTO_APPLY_UNSUPPORTED",
                response_code=400,
                error_code="AUTO_APPLY_UNSUPPORTED",
                error_message="Platform does not support automated API submissions.",
                is_transient_error=False
            )

        elif self.mode == "EXTERNAL_APPLICATION_REQUIRED":
            return ApplicationSubmissionResult(
                success=False,
                status="AUTO_APPLY_UNSUPPORTED",
                response_code=400,
                error_code="EXTERNAL_APPLICATION_REQUIRED",
                error_message="Candidate must submit application on external portal.",
                is_transient_error=False
            )

        return ApplicationSubmissionResult(
            success=False,
            status="FAILED",
            response_code=400,
            error_code="UNKNOWN_ERROR",
            error_message="Unknown mock connector error condition."
        )

    async def get_submission_status(self, external_application_id: str) -> Dict[str, Any]:
        return {
            "external_application_id": external_application_id,
            "status": "SUBMITTED",
            "last_checked": "NOW"
        }
