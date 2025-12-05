"""Unit tests for GitHub API client."""

from unittest.mock import Mock, patch

import pytest

from sbom_fetcher.domain.models import ErrorType, GitHubRepository, PackageDependency
from sbom_fetcher.infrastructure.config import Config
from sbom_fetcher.services.github_client import GitHubClient


class TestGitHubClient:
    """Tests for GitHubClient."""

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return Config()

    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP client."""
        return Mock()

    @pytest.fixture
    def client(self, mock_http_client, config):
        """GitHub client with mocked HTTP client."""
        token = "test_token_123"
        client = GitHubClient(mock_http_client, token, config)
        # Mock the internal session for backward compatibility
        client._session = Mock()
        return client

    @pytest.fixture
    def mock_session(self, client):
        """Get mock session from client."""
        return client._session

    def test_fetch_root_sbom_success(self, client, mock_session):
        """Test successful root SBOM fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sbom": {"packages": []}}
        mock_session.get.return_value = mock_response

        result = client.fetch_root_sbom("owner", "repo")

        assert result is not None
        assert "sbom" in result
        mock_session.get.assert_called_once()

    def test_fetch_root_sbom_404(self, client, mock_session):
        """Test root SBOM fetch when dependency graph not enabled."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response

        result = client.fetch_root_sbom("owner", "repo")

        assert result is None

    def test_fetch_root_sbom_403(self, client, mock_session):
        """Test root SBOM fetch when access forbidden."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_session.get.return_value = mock_response

        result = client.fetch_root_sbom("owner", "repo")

        assert result is None

    def test_fetch_root_sbom_500(self, client, mock_session):
        """Test root SBOM fetch with server error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_session.get.return_value = mock_response

        result = client.fetch_root_sbom("owner", "repo")

        # Should fail (root SBOM doesn't retry)
        assert result is None

    def test_detect_default_branch_main(self, client, mock_session):
        """Test default branch detection for 'main'."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"default_branch": "main"}
        mock_session.get.return_value = mock_response

        branch = client.detect_default_branch("owner", "repo")

        assert branch == "main"

    def test_detect_default_branch_master(self, client, mock_session):
        """Test default branch detection for 'master'."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"default_branch": "master"}
        mock_session.get.return_value = mock_response

        branch = client.detect_default_branch("owner", "repo")

        assert branch == "master"

    def test_detect_default_branch_failure(self, client, mock_session):
        """Test default branch detection when API fails."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response

        branch = client.detect_default_branch("owner", "repo")

        # Should return None on failure
        assert branch is None

    def test_download_dependency_sbom_success(self, client, mock_session, tmp_path):
        """Test successful dependency SBOM download."""
        repo = GitHubRepository(owner="lodash", repo="lodash")
        pkg = PackageDependency(
            name="lodash",
            version="4.17.21",
            ecosystem="npm",
            purl="pkg:npm/lodash@4.17.21",
            github_repository=repo
        )

        # Mock default branch detection
        mock_branch_response = Mock()
        mock_branch_response.status_code = 200
        mock_branch_response.json.return_value = {"default_branch": "main"}

        # Mock SBOM fetch
        mock_sbom_response = Mock()
        mock_sbom_response.status_code = 200
        mock_sbom_response.json.return_value = {"sbom": {"packages": []}}

        mock_session.get.side_effect = [
            mock_branch_response,  # Default branch detection
            mock_sbom_response,  # SBOM fetch
        ]

        success = client._download_single_sbom(pkg, str(tmp_path))

        assert success is True
        assert pkg.sbom_downloaded is True
        assert pkg.error is None

    def test_download_dependency_sbom_404(self, client, mock_session, tmp_path):
        """Test dependency SBOM download when not found."""
        repo = GitHubRepository(owner="test", repo="repo")
        pkg = PackageDependency(
            name="test-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/test-pkg@1.0.0",
            github_repository=repo
        )

        # Mock default branch detection
        mock_branch_response = Mock()
        mock_branch_response.status_code = 200
        mock_branch_response.json.return_value = {"default_branch": "main"}

        # Mock SBOM fetch - 404
        mock_sbom_response = Mock()
        mock_sbom_response.status_code = 404

        mock_session.get.side_effect = [
            mock_branch_response,
            mock_sbom_response,
        ]

        success = client._download_single_sbom(pkg, str(tmp_path))

        assert success is False
        assert pkg.sbom_downloaded is False
        assert pkg.error == "Dependency graph not enabled"
        assert pkg.error_type == ErrorType.PERMANENT

    def test_download_dependency_sbom_500_retry(self, client, mock_session, tmp_path):
        """Test dependency SBOM download with 5xx error and retry."""
        repo = GitHubRepository(owner="test", repo="repo")
        pkg = PackageDependency(
            name="test-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/test-pkg@1.0.0",
            github_repository=repo
        )

        # Mock default branch detection
        mock_branch_response = Mock()
        mock_branch_response.status_code = 200
        mock_branch_response.json.return_value = {"default_branch": "main"}

        # Mock SBOM fetch - 500 then success
        mock_error_response = Mock()
        mock_error_response.status_code = 500

        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"sbom": {"packages": []}}

        mock_session.get.side_effect = [
            mock_branch_response,  # Default branch
            mock_error_response,  # First attempt - 500
            mock_success_response,  # Retry - success
        ]

        success = client._download_single_sbom(pkg, str(tmp_path))

        # Should succeed after retry
        assert success is True
        assert pkg.sbom_downloaded is True
        assert pkg.error is None

    def test_download_dependency_sbom_500_max_retries(
        self, client, mock_session, tmp_path
    ):
        """Test dependency SBOM download exhausts retries on 5xx errors."""
        repo = GitHubRepository(owner="test", repo="repo")
        pkg = PackageDependency(
            name="test-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/test-pkg@1.0.0",
            github_repository=repo
        )

        # Mock default branch detection
        mock_branch_response = Mock()
        mock_branch_response.status_code = 200
        mock_branch_response.json.return_value = {"default_branch": "main"}

        # Mock SBOM fetch - always 500
        mock_error_response = Mock()
        mock_error_response.status_code = 500

        mock_session.get.side_effect = [
            mock_branch_response,  # Default branch
            mock_error_response,  # Attempt 1
            mock_error_response,  # Attempt 2
            mock_error_response,  # Attempt 3
        ]

        success = client._download_single_sbom(pkg, str(tmp_path))

        assert success is False
        assert pkg.sbom_downloaded is False
        assert pkg.error == "HTTP 500"
        assert pkg.error_type == ErrorType.TRANSIENT

    def test_download_dependency_sbom_429_rate_limit(
        self, client, mock_session, tmp_path
    ):
        """Test dependency SBOM download handles rate limiting."""
        repo = GitHubRepository(owner="test", repo="repo")
        pkg = PackageDependency(
            name="test-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/test-pkg@1.0.0",
            github_repository=repo
        )

        # Mock default branch detection
        mock_branch_response = Mock()
        mock_branch_response.status_code = 200
        mock_branch_response.json.return_value = {"default_branch": "main"}

        # Mock SBOM fetch - 429 then success
        mock_rate_limit_response = Mock()
        mock_rate_limit_response.status_code = 429

        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"sbom": {"packages": []}}

        mock_session.get.side_effect = [
            mock_branch_response,
            mock_rate_limit_response,  # Rate limited
            mock_success_response,  # Retry success
        ]

        with patch("time.sleep"):  # Mock sleep to speed up test
            success = client._download_single_sbom(pkg, str(tmp_path))

        assert success is True
        assert pkg.sbom_downloaded is True
