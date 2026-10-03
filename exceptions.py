"""Custom domain exceptions for Patient Management System."""

class PatientManagementException(Exception):
    """Base exception for all domain-specific errors."""
    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

class PatientNotFoundError(PatientManagementException):
    """Raised when a requested patient record cannot be located."""
    def __init__(self, message: str = "Patient not found"):
        super().__init__(message=message, error_code="PATIENT_NOT_FOUND")

class PatientAlreadyExistsError(PatientManagementException):
    """Raised when attempting to create a record with an existing ID."""
    def __init__(self, message: str = "Patient already exists"):
        super().__init__(message=message, error_code="PATIENT_ALREADY_EXISTS")

class InvalidQueryParameterError(PatientManagementException):
    """Raised when query or filter parameters fail business validation."""
    def __init__(self, message: str):
        super().__init__(message=message, error_code="INVALID_QUERY_PARAMETER")
