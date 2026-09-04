class ApplicationError(Exception):
    """Base exception for application domain errors."""
    def __init__(self, message: str, code: str = "APPLICATION_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

class InvalidStateTransitionError(ApplicationError):
    def __init__(self, from_state: str, to_state: str):
        super().__init__(
            f"Invalid application state transition from '{from_state}' to '{to_state}'.",
            code="INVALID_STATE_TRANSITION"
        )
        self.from_state = from_state
        self.to_state = to_state

class DuplicateApplicationError(ApplicationError):
    def __init__(self, message: str = "Duplicate application detected."):
        super().__init__(message, code="DUPLICATE_APPLICATION")

class MissingRequiredInformationError(ApplicationError):
    def __init__(self, missing_fields: list):
        super().__init__(
            f"Required application information missing: {', '.join(missing_fields)}",
            code="MISSING_INFORMATION"
        )
        self.missing_fields = missing_fields

class UnsupportedPlatformError(ApplicationError):
    def __init__(self, source_name: str, reason: str = "Automated application not supported."):
        super().__init__(
            f"Platform '{source_name}' does not support authorized automated submission: {reason}",
            code="AUTO_APPLY_UNSUPPORTED"
        )
        self.source_name = source_name

class DailyLimitReachedError(ApplicationError):
    def __init__(self, limit: int, current_count: int):
        super().__init__(
            f"Daily application limit reached ({current_count}/{limit}).",
            code="DAILY_LIMIT_REACHED"
        )
        self.limit = limit
        self.current_count = current_count

class PolicyViolationError(ApplicationError):
    def __init__(self, reason: str):
        super().__init__(f"Application policy violation: {reason}", code="POLICY_VIOLATION")
        self.reason = reason

class ConnectorExecutionError(ApplicationError):
    def __init__(self, message: str, status_code: int = 500, is_transient: bool = False):
        super().__init__(message, code="CONNECTOR_ERROR")
        self.status_code = status_code
        self.is_transient = is_transient
