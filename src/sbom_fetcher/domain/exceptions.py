"""Custom exception hierarchy for SBOM fetcher."""

from typing import Optional

from .models import ErrorType


class SBOMFetcherError(Exception):
    """Base exception for all SBOM fetcher errors."""

    pass


class ConfigurationError(SBOMFetcherError):
    """Configuration-related errors."""

    pass


class TokenLoadError(ConfigurationError):
    """Failed to load GitHub token."""

    pass


class InvalidConfigError(ConfigurationError):
    """Invalid configuration."""

    pass


class APIError(SBOMFetcherError):
    """API interaction errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        """Initialize API error with optional status code."""
        super().__init__(message)
        self.status_code = status_code


class GitHubAPIError(APIError):
    """GitHub API specific errors."""

    error_type: ErrorType = ErrorType.PERMANENT


class RateLimitError(GitHubAPIError):
    """Rate limit exceeded (transient)."""

    error_type = ErrorType.TRANSIENT

    def __init__(self, message: str = "Rate limit exceeded", status_code: int = 429):
        """Initialize rate limit error."""
        super().__init__(message, status_code)


class AuthenticationError(GitHubAPIError):
    """Authentication failed (permanent)."""

    error_type = ErrorType.PERMANENT

    def __init__(self, message: str = "Authentication failed", status_code: int = 401):
        """Initialize authentication error."""
        super().__init__(message, status_code)


class DependencyGraphDisabledError(GitHubAPIError):
    """Dependency graph not enabled (permanent)."""

    error_type = ErrorType.PERMANENT

    def __init__(self, message: str = "Dependency graph not enabled", status_code: int = 404):
        """Initialize dependency graph disabled error."""
        super().__init__(message, status_code)


class RegistryAPIError(APIError):
    """Package registry API errors."""

    pass


class NPMRegistryError(RegistryAPIError):
    """NPM registry specific errors."""

    pass


class PyPIRegistryError(RegistryAPIError):
    """PyPI registry specific errors."""

    pass


class StorageError(SBOMFetcherError):
    """Storage operation errors."""

    pass


class ValidationError(SBOMFetcherError):
    """Input validation errors."""

    pass


class InvalidPURLError(ValidationError):
    """Invalid Package URL format."""

    pass
