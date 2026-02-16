"""Custom exceptions for CrackATS application."""


class CrackATSException(Exception):
    """Base exception for the CrackATS application."""

    def __init__(self, message: str = "", details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class APIKeyError(CrackATSException):
    """Raised when API key is missing, invalid, or expired."""

    pass


class APIRateLimitError(CrackATSException):
    """Raised when API rate limit is exceeded."""

    pass


class APIAccessDeniedError(CrackATSException):
    """Raised when API access is denied."""

    pass


class ScrapingError(CrackATSException):
    """Raised when job scraping fails."""

    pass


class AuthenticationWallError(ScrapingError):
    """Raised when an authentication wall is encountered."""

    pass


class CaptchaError(ScrapingError):
    """Raised when a CAPTCHA is encountered."""

    pass


class FileOperationError(CrackATSException):
    """Raised when file operation fails."""

    pass


class TemplateNotFoundError(FileOperationError):
    """Raised when a template file is not found."""

    pass


class ValidationError(CrackATSException):
    """Raised when input validation fails."""

    pass


class DatabaseError(CrackATSException):
    """Raised when database operation fails."""

    pass


class ConfigurationError(CrackATSException):
    """Raised when configuration is invalid or missing."""

    pass
