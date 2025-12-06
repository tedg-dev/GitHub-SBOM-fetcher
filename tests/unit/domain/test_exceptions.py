"""Unit tests for domain exceptions."""

from sbom_fetcher.domain.exceptions import (
    APIError,
    AuthenticationError,
    DependencyGraphDisabledError,
    GitHubAPIError,
    InvalidConfigError,
    RateLimitError,
    SBOMFetcherError,
    StorageError,
    ValidationError,
)


class TestExceptions:
    """Tests for custom exceptions."""

    def test_sbom_fetcher_error(self):
        """Test base SBOMFetcherError exception."""
        error = SBOMFetcherError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_api_error(self):
        """Test APIError exception."""
        error = APIError("API failed")
        assert str(error) == "API failed"
        assert isinstance(error, SBOMFetcherError)

    def test_github_api_error(self):
        """Test GitHubAPIError exception."""
        error = GitHubAPIError("GitHub API failed")
        assert str(error) == "GitHub API failed"
        assert isinstance(error, APIError)
        assert isinstance(error, SBOMFetcherError)

    def test_validation_error(self):
        """Test ValidationError exception."""
        error = ValidationError("Invalid data")
        assert str(error) == "Invalid data"
        assert isinstance(error, SBOMFetcherError)

    def test_storage_error(self):
        """Test StorageError exception."""
        error = StorageError("Storage failed")
        assert str(error) == "Storage failed"
        assert isinstance(error, SBOMFetcherError)

    def test_exception_with_cause(self):
        """Test exception with underlying cause."""
        cause = ValueError("Original error")
        try:
            raise APIError("Wrapped error") from cause
        except APIError as error:
            assert str(error) == "Wrapped error"
            assert error.__cause__ == cause

    def test_rate_limit_error(self):
        """Test RateLimitError with default message."""
        error = RateLimitError()
        assert "Rate limit exceeded" in str(error)
        assert error.status_code == 429

    def test_rate_limit_error_custom(self):
        """Test RateLimitError with custom message."""
        error = RateLimitError("Custom rate limit message", 429)
        assert str(error) == "Custom rate limit message"

    def test_authentication_error(self):
        """Test AuthenticationError with default message."""
        error = AuthenticationError()
        assert "Authentication failed" in str(error)
        assert error.status_code == 401

    def test_authentication_error_custom(self):
        """Test AuthenticationError with custom message."""
        error = AuthenticationError("Invalid token", 401)
        assert str(error) == "Invalid token"

    def test_dependency_graph_disabled_error(self):
        """Test DependencyGraphDisabledError with default message."""
        error = DependencyGraphDisabledError()
        assert "Dependency graph not enabled" in str(error)
        assert error.status_code == 404

    def test_dependency_graph_disabled_error_custom(self):
        """Test DependencyGraphDisabledError with custom message."""
        error = DependencyGraphDisabledError("Please enable dependency graph", 404)
        assert str(error) == "Please enable dependency graph"
