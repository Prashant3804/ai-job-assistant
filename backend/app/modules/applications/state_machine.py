from typing import Set, Dict
from app.shared.constants import ApplicationStatus
from app.modules.applications.exceptions import InvalidStateTransitionError

# Valid State Transition Matrix
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    ApplicationStatus.DISCOVERED.value: {
        ApplicationStatus.MATCHED.value,
        ApplicationStatus.POLICY_PENDING.value,
        ApplicationStatus.POLICY_APPROVED.value,
        ApplicationStatus.DUPLICATE.value,
        ApplicationStatus.AUTO_APPLY_UNSUPPORTED.value,
        ApplicationStatus.BLOCKED.value,
        ApplicationStatus.QUEUED.value,
        ApplicationStatus.DRAFT.value,
    },
    ApplicationStatus.MATCHED.value: {
        ApplicationStatus.POLICY_PENDING.value,
        ApplicationStatus.POLICY_APPROVED.value,
        ApplicationStatus.QUEUED.value,
        ApplicationStatus.DUPLICATE.value,
        ApplicationStatus.BLOCKED.value,
        ApplicationStatus.AUTO_APPLY_UNSUPPORTED.value,
        ApplicationStatus.MISSING_INFORMATION.value,
    },
    ApplicationStatus.POLICY_PENDING.value: {
        ApplicationStatus.POLICY_APPROVED.value,
        ApplicationStatus.QUEUED.value,
        ApplicationStatus.BLOCKED.value,
        ApplicationStatus.DUPLICATE.value,
        ApplicationStatus.AUTO_APPLY_UNSUPPORTED.value,
        ApplicationStatus.MISSING_INFORMATION.value,
    },
    ApplicationStatus.POLICY_APPROVED.value: {
        ApplicationStatus.QUEUED.value,
        ApplicationStatus.PREPARING.value,
        ApplicationStatus.DUPLICATE.value,
        ApplicationStatus.BLOCKED.value,
    },
    ApplicationStatus.QUEUED.value: {
        ApplicationStatus.PREPARING.value,
        ApplicationStatus.FAILED.value,
        ApplicationStatus.AUTO_APPLY_UNSUPPORTED.value,
        ApplicationStatus.BLOCKED.value,
    },
    ApplicationStatus.PREPARING.value: {
        ApplicationStatus.VALIDATING.value,
        ApplicationStatus.MISSING_INFORMATION.value,
        ApplicationStatus.FAILED.value,
        ApplicationStatus.BLOCKED.value,
    },
    ApplicationStatus.VALIDATING.value: {
        ApplicationStatus.SUBMITTING.value,
        ApplicationStatus.MISSING_INFORMATION.value,
        ApplicationStatus.FAILED.value,
        ApplicationStatus.BLOCKED.value,
    },
    ApplicationStatus.SUBMITTING.value: {
        ApplicationStatus.APPLIED.value,
        ApplicationStatus.SUBMITTED.value,
        ApplicationStatus.FAILED.value,
        ApplicationStatus.RETRYING.value,
        ApplicationStatus.RATE_LIMITED.value,
        ApplicationStatus.AUTO_APPLY_UNSUPPORTED.value,
    },
    ApplicationStatus.FAILED.value: {
        ApplicationStatus.RETRYING.value,
        ApplicationStatus.QUEUED.value,
        ApplicationStatus.ARCHIVED.value,
    },
    ApplicationStatus.RETRYING.value: {
        ApplicationStatus.SUBMITTING.value,
        ApplicationStatus.PREPARING.value,
        ApplicationStatus.FAILED.value,
        ApplicationStatus.RATE_LIMITED.value,
    },
    ApplicationStatus.RATE_LIMITED.value: {
        ApplicationStatus.RETRYING.value,
        ApplicationStatus.QUEUED.value,
        ApplicationStatus.FAILED.value,
    },
    ApplicationStatus.APPLIED.value: {
        ApplicationStatus.UNDER_REVIEW.value,
        ApplicationStatus.INTERVIEW_SCHEDULED.value,
        ApplicationStatus.OFFER_RECEIVED.value,
        ApplicationStatus.REJECTED.value,
        ApplicationStatus.ARCHIVED.value,
    },
    ApplicationStatus.SUBMITTED.value: {
        ApplicationStatus.UNDER_REVIEW.value,
        ApplicationStatus.INTERVIEW_SCHEDULED.value,
        ApplicationStatus.OFFER_RECEIVED.value,
        ApplicationStatus.REJECTED.value,
        ApplicationStatus.ARCHIVED.value,
    },
    ApplicationStatus.UNDER_REVIEW.value: {
        ApplicationStatus.INTERVIEW_SCHEDULED.value,
        ApplicationStatus.OFFER_RECEIVED.value,
        ApplicationStatus.REJECTED.value,
        ApplicationStatus.ARCHIVED.value,
    },
    ApplicationStatus.INTERVIEW_SCHEDULED.value: {
        ApplicationStatus.INTERVIEW_SCHEDULED.value,
        ApplicationStatus.OFFER_RECEIVED.value,
        ApplicationStatus.REJECTED.value,
        ApplicationStatus.ARCHIVED.value,
    },
    ApplicationStatus.OFFER_RECEIVED.value: {
        ApplicationStatus.ARCHIVED.value,
    },
    ApplicationStatus.REJECTED.value: {
        ApplicationStatus.ARCHIVED.value,
    },
    ApplicationStatus.DRAFT.value: {
        ApplicationStatus.QUEUED.value,
        ApplicationStatus.PREPARING.value,
        ApplicationStatus.SUBMITTED.value,
        ApplicationStatus.APPLIED.value,
        ApplicationStatus.ARCHIVED.value,
    },
    ApplicationStatus.DUPLICATE.value: {
        ApplicationStatus.ARCHIVED.value,
    },
    ApplicationStatus.BLOCKED.value: {
        ApplicationStatus.ARCHIVED.value,
    },
    ApplicationStatus.AUTO_APPLY_UNSUPPORTED.value: {
        ApplicationStatus.ARCHIVED.value,
        ApplicationStatus.DRAFT.value,
    },
    ApplicationStatus.MISSING_INFORMATION.value: {
        ApplicationStatus.PREPARING.value,
        ApplicationStatus.VALIDATING.value,
        ApplicationStatus.ARCHIVED.value,
    },
    ApplicationStatus.EXPIRED.value: {
        ApplicationStatus.ARCHIVED.value,
    },
    ApplicationStatus.ARCHIVED.value: set(),
}

class ApplicationStateMachine:
    """Enforces valid application lifecycle transitions."""

    @staticmethod
    def can_transition(current_status: str, target_status: str) -> bool:
        if current_status == target_status:
            return True
        allowed = VALID_TRANSITIONS.get(current_status, set())
        return target_status in allowed

    @staticmethod
    def validate_transition(current_status: str, target_status: str) -> None:
        if not ApplicationStateMachine.can_transition(current_status, target_status):
            raise InvalidStateTransitionError(current_status, target_status)
