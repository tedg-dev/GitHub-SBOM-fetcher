"""Unit tests for domain exceptions."""

from sbom_fetcher.domain.exceptions import (
    APIError,
    GitHubAPIError,
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
