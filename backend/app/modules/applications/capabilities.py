from typing import Tuple
from app.database.models.job import Job
from app.shared.constants import ConnectorCapabilityStatus

class PlatformCapabilityManager:
    """Evaluates whether a target job source permits authorized automated submissions."""

    @staticmethod
    def check_capability(job: Job) -> Tuple[bool, str, str]:
        if not job.job_source:
            # Direct or unspecified jobs require external application
            return False, ConnectorCapabilityStatus.EXTERNAL_APPLICATION_REQUIRED.value, "No authorized connector configured for direct job posting."

        status = job.job_source.capability_status
        if status == ConnectorCapabilityStatus.SUPPORTED_AUTO_APPLY.value:
            return True, ConnectorCapabilityStatus.SUPPORTED_AUTO_APPLY.value, f"Platform '{job.job_source.name}' supports authorized direct application API."

        if status == ConnectorCapabilityStatus.EXTERNAL_APPLICATION_REQUIRED.value:
            return False, ConnectorCapabilityStatus.EXTERNAL_APPLICATION_REQUIRED.value, f"Platform '{job.job_source.name}' requires candidate submission on external employer website."

        if status == ConnectorCapabilityStatus.SUPPORTED_JOB_DISCOVERY_ONLY.value:
            return False, ConnectorCapabilityStatus.SUPPORTED_JOB_DISCOVERY_ONLY.value, f"Platform '{job.job_source.name}' is registered for job discovery only."

        return False, ConnectorCapabilityStatus.NOT_SUPPORTED.value, f"Platform '{job.job_source.name}' does not support authorized automated applications."
