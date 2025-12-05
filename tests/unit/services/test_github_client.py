"""Comprehensive unit tests for GitHub API client - Complete Coverage."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest
import requests

from sbom_fetcher.domain.models import (
    ErrorType,
    GitHubRepository,
    PackageDependency,
)
from sbom_fetcher.infrastructure.config import Config
from sbom_fetcher.infrastructure.http_client import RequestsHTTPClient
from sbom_fetcher.services.github_client import GitHubClient


class TestGitHubClientInitialization:
    """Tests for GitHub client initialization."""

    def test_client_initialization(self):
        """Test GitHub client initializes with correct parameters."""
        config = Config()
        http_client = RequestsHTTPClient(config)
        token = "test_token_123"

        client = GitHubClient(http_client, token, config)

        assert client._http_client == http_client
        assert client._token == token
        assert client._config == config
        assert client._api_url == config.github_api_url
        assert isinstance(client._branch_cache, dict)


class TestFetchRootSBOM:
    """Tests for fetching root repository SBOM."""

    @pytest.fixture
    def client(self):
        """Create GitHub client for testing."""
        config = Config()
        http_client = RequestsHTTPClient(config)
        return GitHubClient(http_client, "test_token", config)

    def test_fetch_root_sbom_success(self, client):
        """Test successful root SBOM fetch."""
        expected_sbom = {"sbom": {"packages": []}}

        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = expected_sbom
            mock_session.get.return_value = mock_response

            result = client.fetch_root_sbom("owner", "repo")

            assert result == expected_sbom
            mock_session.get.assert_called_once()

    def test_fetch_root_sbom_404(self, client):
        """Test root SBOM fetch when dependency graph not enabled."""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            mock_response = Mock()
            mock_response.status_code = 404
            mock_session.get.return_value = mock_response

            result = client.fetch_root_sbom("owner", "repo")

            assert result is None

    def test_fetch_root_sbom_403(self, client):
        """Test root SBOM fetch when access forbidden."""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            mock_response = Mock()
            mock_response.status_code = 403
            mock_session.get.return_value = mock_response

            result = client.fetch_root_sbom("owner", "repo")

            assert result is None

    def test_fetch_root_sbom_500(self, client):
        """Test root SBOM fetch with server error."""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            mock_response = Mock()
            mock_response.status_code = 500
            mock_session.get.return_value = mock_response

            result = client.fetch_root_sbom("owner", "repo")

            assert result is None

    def test_fetch_root_sbom_request_exception(self, client):
        """Test root SBOM fetch handles request exceptions."""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.side_effect = requests.RequestException("Network error")

            result = client.fetch_root_sbom("owner", "repo")

            assert result is None


class TestGetDefaultBranch:
    """Tests for getting default branch name."""

    @pytest.fixture
    def client(self):
        """Create GitHub client for testing."""
        config = Config()
        http_client = RequestsHTTPClient(config)
        return GitHubClient(http_client, "test_token", config)

    @pytest.fixture
    def mock_session(self):
        """Create mock requests session."""
        return Mock(spec=requests.Session)

    def test_get_default_branch_main(self, client, mock_session):
        """Test default branch detection for 'main'."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"default_branch": "main"}
        mock_session.get.return_value = mock_response

        branch = client.get_default_branch(mock_session, "owner", "repo")

        assert branch == "main"
        assert "owner/repo" in client._branch_cache
        assert client._branch_cache["owner/repo"] == "main"

    def test_get_default_branch_master(self, client, mock_session):
        """Test default branch detection for 'master'."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"default_branch": "master"}
        mock_session.get.return_value = mock_response

        branch = client.get_default_branch(mock_session, "owner", "repo")

        assert branch == "master"

    def test_get_default_branch_develop(self, client, mock_session):
        """Test default branch detection for custom branch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"default_branch": "develop"}
        mock_session.get.return_value = mock_response

        branch = client.get_default_branch(mock_session, "owner", "repo")

        assert branch == "develop"

    def test_get_default_branch_cached(self, client, mock_session):
        """Test default branch uses cache."""
        # First call
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"default_branch": "main"}
        mock_session.get.return_value = mock_response

        branch1 = client.get_default_branch(mock_session, "owner", "repo")
        
        # Second call (should use cache)
        branch2 = client.get_default_branch(mock_session, "owner", "repo")

        assert branch1 == branch2 == "main"
        # Should only call API once due to caching
        assert mock_session.get.call_count == 1

    def test_get_default_branch_failure_fallback(self, client, mock_session):
        """Test default branch falls back to 'main' on failure."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response

        branch = client.get_default_branch(mock_session, "owner", "repo")

        assert branch == "main"
        assert client._branch_cache["owner/repo"] == "main"

    def test_get_default_branch_exception_fallback(self, client, mock_session):
        """Test default branch handles exceptions."""
        mock_session.get.side_effect = Exception("Network error")

        branch = client.get_default_branch(mock_session, "owner", "repo")

        assert branch == "main"


class TestDownloadDependencySBOM:
    """Tests for downloading dependency SBOMs."""

    @pytest.fixture
    def client(self):
        """Create GitHub client for testing."""
        config = Config()
        http_client = RequestsHTTPClient(config)
        return GitHubClient(http_client, "test_token", config)

    @pytest.fixture
    def mock_session(self):
        """Create mock requests session."""
        return Mock(spec=requests.Session)

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_download_without_github_repo(self, client, mock_session, temp_dir):
        """Test download fails when package has no GitHub repository."""
        pkg = PackageDependency(
            name="test-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/test-pkg@1.0.0"
        )

        result = client.download_dependency_sbom(mock_session, pkg, temp_dir)

        assert result is False
        assert pkg.error == "No GitHub repository mapped"
        assert pkg.sbom_downloaded is False

    def test_download_success(self, client, mock_session, temp_dir):
        """Test successful SBOM download."""
        repo = GitHubRepository(owner="lodash", repo="lodash")
        pkg = PackageDependency(
            name="lodash",
            version="4.17.21",
            ecosystem="npm",
            purl="pkg:npm/lodash@4.17.21",
            github_repository=repo
        )

        # Mock SBOM download
        sbom_response = Mock()
        sbom_response.status_code = 200
        sbom_response.json.return_value = {"sbom": {"packages": []}}

        # Mock default branch call
        branch_response = Mock()
        branch_response.status_code = 200
        branch_response.json.return_value = {"default_branch": "main"}

        mock_session.get.side_effect = [sbom_response, branch_response]

        result = client.download_dependency_sbom(mock_session, pkg, temp_dir)

        assert result is True
        assert pkg.sbom_downloaded is True
        assert pkg.error is None

        # Verify file was created
        expected_file = Path(temp_dir) / "lodash_lodash_main.json"
        assert expected_file.exists()

    def test_download_404_error(self, client, mock_session, temp_dir):
        """Test download handles 404 (dependency graph not enabled)."""
        repo = GitHubRepository(owner="test", repo="repo")
        pkg = PackageDependency(
            name="test-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/test-pkg@1.0.0",
            github_repository=repo
        )

        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response

        result = client.download_dependency_sbom(mock_session, pkg, temp_dir)

        assert result is False
        assert pkg.error == "Dependency graph not enabled"
        assert pkg.error_type == ErrorType.PERMANENT
        assert pkg.sbom_downloaded is False

    def test_download_403_error(self, client, mock_session, temp_dir):
        """Test download handles 403 (forbidden)."""
        repo = GitHubRepository(owner="test", repo="repo")
        pkg = PackageDependency(
            name="test-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/test-pkg@1.0.0",
            github_repository=repo
        )

        mock_response = Mock()
        mock_response.status_code = 403
        mock_session.get.return_value = mock_response

        result = client.download_dependency_sbom(mock_session, pkg, temp_dir)

        assert result is False
        assert pkg.error == "Access forbidden"
        assert pkg.error_type == ErrorType.PERMANENT

    def test_download_500_retry_success(self, client, mock_session, temp_dir):
        """Test download retries on 500 error and succeeds."""
        repo = GitHubRepository(owner="test", repo="repo")
        pkg = PackageDependency(
            name="test-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/test-pkg@1.0.0",
            github_repository=repo
        )

        # First call: 500 error
        error_response = Mock()
        error_response.status_code = 500

        # Second call: success
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"sbom": {"packages": []}}

        # Branch call
        branch_response = Mock()
        branch_response.status_code = 200
        branch_response.json.return_value = {"default_branch": "main"}

        mock_session.get.side_effect = [
            error_response, success_response, branch_response
        ]

        with patch("time.sleep"):  # Speed up test
            result = client.download_dependency_sbom(mock_session, pkg, temp_dir)

        assert result is True
        assert pkg.sbom_downloaded is True
        assert mock_session.get.call_count >= 2

    def test_download_500_max_retries(self, client, mock_session, temp_dir):
        """Test download exhausts retries on persistent 500 errors."""
        repo = GitHubRepository(owner="test", repo="repo")
        pkg = PackageDependency(
            name="test-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/test-pkg@1.0.0",
            github_repository=repo
        )

        mock_response = Mock()
        mock_response.status_code = 500
        mock_session.get.return_value = mock_response

        with patch("time.sleep"):  # Speed up test
            result = client.download_dependency_sbom(mock_session, pkg, temp_dir)

        assert result is False
        assert pkg.error == "HTTP 500"
        assert pkg.error_type == ErrorType.TRANSIENT
        assert pkg.sbom_downloaded is False

    def test_download_429_rate_limit_retry(self, client, mock_session, temp_dir):
        """Test download handles rate limiting with retry."""
        repo = GitHubRepository(owner="test", repo="repo")
        pkg = PackageDependency(
            name="test-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/test-pkg@1.0.0",
            github_repository=repo
        )

        # First: rate limited
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429

        # Second: success
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"sbom": {"packages": []}}

        # Branch call
        branch_response = Mock()
        branch_response.status_code = 200
        branch_response.json.return_value = {"default_branch": "main"}

        mock_session.get.side_effect = [
            rate_limit_response, success_response, branch_response
        ]

        with patch("time.sleep"):
            result = client.download_dependency_sbom(mock_session, pkg, temp_dir)

        assert result is True
        assert pkg.sbom_downloaded is True
