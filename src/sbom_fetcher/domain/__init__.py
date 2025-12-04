"""Domain layer - core business models and exceptions."""

from .exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    DependencyGraphDisabledError,
    ErrorType,
    GitHubAPIError,
    InvalidConfigError,
    InvalidPURLError,
    NPMRegistryError,
    PyPIRegistryError,
    RateLimitError,
    RegistryAPIError,
    SBOMFetcherError,
    StorageError,
    TokenLoadError,
    ValidationError,
)
from .models import (
    FailureInfo,
    FetcherResult,
    FetcherStats,
    GitHubRepository,
    PackageDependency,
)

__all__ = [
    # Exceptions
    "SBOMFetcherError",
    "ConfigurationError",
    "TokenLoadError",
    "InvalidConfigError",
    "APIError",
    "GitHubAPIError",
    "RateLimitError",
    "AuthenticationError",
    "DependencyGraphDisabledError",
    "RegistryAPIError",
    "NPMRegistryError",
    "PyPIRegistryError",
    "StorageError",
    "ValidationError",
    "InvalidPURLError",
    "ErrorType",
    # Models
    "GitHubRepository",
    "PackageDependency",
    "FetcherStats",
    "FetcherResult",
    "FailureInfo",
]
