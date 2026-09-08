from enum import Enum
from typing import Tuple, Optional, Dict, Any
from app.database.models.job import Job
from app.shared.constants import ConnectorCapabilityStatus


class ApplicationSubmissionCapability(str, Enum):
    SUPPORTED_AUTO_APPLY = "SUPPORTED_AUTO_APPLY"
    EXTERNAL_APPLICATION_REQUIRED = "EXTERNAL_APPLICATION_REQUIRED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    UNSUPPORTED = "UNSUPPORTED"


class ApplicationCapabilityService:
    """
    Centralized Application Capability Service.
    Determines whether a job platform legitimately permits authorized automated submission.
    Enforces strict anti-bot and Terms of Service non-circumvention rules.
    """

    # Primary 7 platforms and their honest submission capability
    PLATFORM_CAPABILITIES: Dict[str, Dict[str, Any]] = {
        "naukri": {
            "capability": ApplicationSubmissionCapability.EXTERNAL_APPLICATION_REQUIRED,
            "reason": "Naukri requires candidate submission on external employer website; proprietary login/OTP needed.",
            "auto_apply_supported": False,
        },
        "indeed": {
            "capability": ApplicationSubmissionCapability.EXTERNAL_APPLICATION_REQUIRED,
            "reason": "Indeed Apply requires employer-side OAuth 2.0 client credentials and partner whitelisting. External portal application required.",
            "auto_apply_supported": False,
        },
        "unstop": {
            "capability": ApplicationSubmissionCapability.EXTERNAL_APPLICATION_REQUIRED,
            "reason": "Unstop requires candidate portal authentication. Automated submissions are not legitimately permitted without candidate session.",
            "auto_apply_supported": False,
        },
        "linkedin": {
            "capability": ApplicationSubmissionCapability.EXTERNAL_APPLICATION_REQUIRED,
            "reason": "LinkedIn EasyApply requires official LinkedIn Talent Solutions partner API credentials. Candidate external application required.",
            "auto_apply_supported": False,
        },
        "internshala": {
            "capability": ApplicationSubmissionCapability.EXTERNAL_APPLICATION_REQUIRED,
            "reason": "Internshala requires authenticated candidate session and CSRF challenge on portal. Automated submissions prohibited.",
            "auto_apply_supported": False,
        },
        "wellfound": {
            "capability": ApplicationSubmissionCapability.EXTERNAL_APPLICATION_REQUIRED,
            "reason": "Wellfound (AngelList) requires proprietary talent portal authentication and candidate verification.",
            "auto_apply_supported": False,
        },
        "career_pages": {
            "capability": ApplicationSubmissionCapability.EXTERNAL_APPLICATION_REQUIRED,
            "reason": "Public Greenhouse/Lever job boards provide read-only discovery feeds. Applicant submission write endpoints require employer-specific secret tokens.",
            "auto_apply_supported": False,
        },
        "aggregated_feeds": {
            "capability": ApplicationSubmissionCapability.EXTERNAL_APPLICATION_REQUIRED,
            "reason": "Aggregated job feeds (Remotive, Arbeitnow, Jobicy) syndicate listings directing candidates to employer portals.",
            "auto_apply_supported": False,
        },
        "mock_ats": {
            "capability": ApplicationSubmissionCapability.SUPPORTED_AUTO_APPLY,
            "reason": "Authorized test ATS connector for deterministic integration verification.",
            "auto_apply_supported": True,
        },
        "direct_api": {
            "capability": ApplicationSubmissionCapability.SUPPORTED_AUTO_APPLY,
            "reason": "Authorized Direct Partner API connector with confirmed API credentials.",
            "auto_apply_supported": True,
        }
    }

    @classmethod
    def evaluate_job(cls, job: Any) -> Tuple[ApplicationSubmissionCapability, str]:
        """
        Evaluates a Job or NormalizedJob object and returns:
        (ApplicationSubmissionCapability, human_readable_reason)
        """
        source_slug = None
        if hasattr(job, "job_source") and job.job_source:
            source_slug = getattr(job.job_source, "slug", None)
        if not source_slug:
            source_slug = getattr(job, "source", None)

        if not source_slug:
            return (
                ApplicationSubmissionCapability.EXTERNAL_APPLICATION_REQUIRED,
                "No registered source connector found; candidate must apply directly via job URL."
            )

        norm_slug = str(source_slug).lower().strip()
        info = cls.PLATFORM_CAPABILITIES.get(norm_slug)

        if not info:
            # Fallback check on job_source model capability status if present
            if hasattr(job, "job_source") and job.job_source:
                status = getattr(job.job_source, "capability_status", None)
                if status == ConnectorCapabilityStatus.SUPPORTED_AUTO_APPLY.value:
                    return (
                        ApplicationSubmissionCapability.SUPPORTED_AUTO_APPLY,
                        f"Platform '{job.job_source.name}' has verified authorized auto-apply capability."
                    )

            return (
                ApplicationSubmissionCapability.EXTERNAL_APPLICATION_REQUIRED,
                f"Platform '{norm_slug}' does not support authorized automated API applications."
            )

        return info["capability"], info["reason"]
