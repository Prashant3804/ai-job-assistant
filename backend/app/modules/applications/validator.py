import re
from typing import Dict, Any, List, Tuple, Optional
from app.shared.constants import ApplicationStatus

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_REGEX = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.I)

class ApplicationValidator:
    """Validates candidate data integrity and completeness before submitting an application."""

    @staticmethod
    def validate_application(
        candidate_data: Dict[str, Any],
        has_resume: bool,
        missing_question_fields: Optional[List[str]] = None,
        mapped_answers: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[bool, ApplicationStatus, List[str], List[str]]:
        """
        Returns:
            - is_valid: bool
            - resulting_status: ApplicationStatus
            - missing_fields: List[str]
            - validation_errors: List[str]
        """
        missing_fields: List[str] = list(missing_question_fields or [])
        validation_errors: List[str] = []

        # 1. Essential Candidate Info
        name = candidate_data.get("name", "").strip()
        email = candidate_data.get("email", "").strip()

        if not name:
            missing_fields.append("candidate_name")
            validation_errors.append("Full Name is required.")

        if not email:
            missing_fields.append("candidate_email")
            validation_errors.append("Email address is required.")
        elif not EMAIL_REGEX.match(email):
            validation_errors.append(f"Email '{email}' is not a valid email format.")

        # 2. Resume Document Check
        if not has_resume:
            missing_fields.append("resume_document")
            validation_errors.append("A primary or tailored resume is required.")

        # 3. URL Format Checks
        for url_field in ["linkedin_url", "github_url", "portfolio_url"]:
            val = candidate_data.get(url_field, "").strip()
            if val and not URL_REGEX.match(val):
                validation_errors.append(f"Field '{url_field}' has invalid URL structure: {val}")

        # 4. Result Evaluation
        if missing_fields:
            return False, ApplicationStatus.MISSING_INFORMATION, missing_fields, validation_errors

        if validation_errors:
            return False, ApplicationStatus.FAILED, missing_fields, validation_errors

        return True, ApplicationStatus.VALIDATING, [], []
