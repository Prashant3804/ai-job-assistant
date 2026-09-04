from typing import Tuple

TRANSIENT_ERROR_CODES = {
    "TIMEOUT",
    "NETWORK_ERROR",
    "SERVER_ERROR",
    "500",
    "502",
    "503",
    "504",
    "RATE_LIMIT",
    "429",
    "SERVICE_UNAVAILABLE"
}

PERMANENT_ERROR_CODES = {
    "UNAUTHORIZED",
    "401",
    "FORBIDDEN",
    "403",
    "NOT_FOUND",
    "404",
    "INVALID_DATA",
    "400",
    "MISSING_INFORMATION",
    "DUPLICATE_APPLICATION",
    "409",
    "AUTO_APPLY_UNSUPPORTED",
    "EXTERNAL_APPLICATION_REQUIRED",
    "CAPTCHA_DETECTED"
}

class RetryManager:
    """Calculates exponential retry backoff and determines retryability of application errors."""

    @staticmethod
    def should_retry(
        error_code: str,
        attempt_count: int,
        max_attempts: int = 3,
        is_explicit_transient: bool = False
    ) -> Tuple[bool, int, str]:
        code_upper = str(error_code or "").upper().strip()

        # Check if permanently non-retryable
        if code_upper in PERMANENT_ERROR_CODES:
            return False, 0, f"Permanent error '{error_code}': Retry is not permitted."

        # Check if attempt limits exceeded
        if attempt_count >= max_attempts:
            return False, 0, f"Max retry limit ({max_attempts}) reached. Marking application as failed."

        # Check if known transient error or marked explicit transient
        if code_upper in TRANSIENT_ERROR_CODES or is_explicit_transient:
            delay_seconds = min(300, (2 ** attempt_count) * 5)
            return True, delay_seconds, f"Transient error '{error_code}': Scheduled retry attempt #{attempt_count + 1} in {delay_seconds}s."

        return False, 0, f"Unrecognized error '{error_code}': Not retrying automatically."
