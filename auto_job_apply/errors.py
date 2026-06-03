class AutoJobApplyError(Exception):
    """Base error for app exceptions."""


class ValidationError(AutoJobApplyError):
    """Raised when data validation fails."""


class StorageError(AutoJobApplyError):
    """Raised when storage operations fail."""


class ResumeParseError(AutoJobApplyError):
    """Raised when resume parsing fails."""
