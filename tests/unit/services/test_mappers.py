"""Comprehensive unit tests for package mappers - Complete Coverage."""

from unittest.mock import Mock, patch

import pytest
import requests

from sbom_fetcher.domain.models import GitHubRepository
from sbom_fetcher.infrastructure.config import Config
from sbom_fetcher.services.mappers import (
    NPMPackageMapper,
    NullMapper,
    PackageMapper,
    PyPIPackageMapper,
    search_org_for_package,
)


class TestPackageMapperBase:
    """Tests for base PackageMapper interface."""

    def test_base_mapper_not_implemented(self):
        """Test base mapper raises NotImplementedError."""
        mapper = PackageMapper()
        with pytest.raises(NotImplementedError):
            mapper.map_to_github("test-package")


class TestNPMPackageMapper:
    """Comprehensive tests for NPM package mapper."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config()

    @pytest.fixture
    def mapper(self, config):
        """Create NPM mapper."""
        return NPMPackageMapper(config)

    def test_initialization(self, config):
        """Test mapper initializes correctly."""
        mapper = NPMPackageMapper(config)
        assert mapper._config == config

    @patch("requests.get")
    def test_map_package_with_dict_repository(self, mock_get, mapper):
        """Test mapping package with dictionary repository field."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repository": {"type": "git", "url": "git+https://github.com/lodash/lodash.git"}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("lodash")

        assert result is not None
        assert result.owner == "lodash"
        assert result.repo == "lodash"

    @patch("requests.get")
    def test_map_package_with_string_repository(self, mock_get, mapper):
        """Test mapping package with string repository field."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"repository": "https://github.com/express/express"}
        mock_get.return_value = mock_response

        result = mapper.map_to_github("express")

        assert result is not None
        assert result.owner == "express"
        assert result.repo == "express"

    @patch("requests.get")
    def test_map_package_shorthand_format(self, mock_get, mapper):
        """Test mapping package with shorthand format (owner/repo)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"repository": "owner/repo"}
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-package")

        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"

    @patch("requests.get")
    def test_map_scoped_package(self, mock_get, mapper):
        """Test mapping scoped npm package."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repository": {"url": "https://github.com/babel/babel.git"}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("@babel/core")

        assert result is not None
        assert result.owner == "babel"
        assert result.repo == "babel"
        # Verify URL encoding was used in npm registry call
        # (Also makes a verification call to check SBOM availability)
        assert mock_get.call_count >= 1
        npm_call = mock_get.call_args_list[0]
        assert "%40babel" in npm_call[0][0]

    @patch("requests.get")
    def test_map_package_with_git_protocol(self, mock_get, mapper):
        """Test mapping package with git:// protocol."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"repository": "git://github.com/owner/repo.git"}
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"

    @patch("requests.get")
    def test_map_package_with_ssh_protocol(self, mock_get, mapper):
        """Test mapping package with SSH protocol."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"repository": "ssh://git@github.com/owner/repo.git"}
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"

    @patch("requests.get")
    def test_map_package_with_branch_reference(self, mock_get, mapper):
        """Test mapping package with branch reference in URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"repository": "https://github.com/owner/repo#master"}
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"

    @patch("requests.get")
    def test_map_package_null_repository(self, mock_get, mapper):
        """Test mapping package with null repository field."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"repository": None}
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is None

    @patch("requests.get")
    def test_map_package_empty_repository(self, mock_get, mapper):
        """Test mapping package with empty repository URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"repository": {"url": ""}}
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is None

    @patch("requests.get")
    def test_map_package_non_github_repository(self, mock_get, mapper):
        """Test mapping package with non-GitHub repository."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"repository": "https://gitlab.com/owner/repo"}
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is None

    @patch("requests.get")
    def test_map_package_404(self, mock_get, mapper):
        """Test mapping package that doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = mapper.map_to_github("nonexistent-package")

        assert result is None

    @patch("requests.get")
    def test_map_package_network_error(self, mock_get, mapper):
        """Test mapping package with network error."""
        mock_get.side_effect = requests.RequestException("Network error")

        result = mapper.map_to_github("test-pkg")

        assert result is None

    @patch("requests.get")
    def test_map_package_invalid_json(self, mock_get, mapper):
        """Test mapping package with invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is None

    @patch("requests.get")
    def test_map_package_malformed_url(self, mock_get, mapper):
        """Test mapping package with malformed repository URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"repository": "not-a-valid-url"}
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is None


class TestPyPIPackageMapper:
    """Comprehensive tests for PyPI package mapper."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config()

    @pytest.fixture
    def mapper(self, config):
        """Create PyPI mapper."""
        return PyPIPackageMapper(config)

    def test_initialization(self, config):
        """Test mapper initializes correctly."""
        mapper = PyPIPackageMapper(config)
        assert mapper._config == config

    @patch("requests.get")
    def test_map_package_with_source_url(self, mock_get, mapper):
        """Test mapping package with Source URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"project_urls": {"Source": "https://github.com/psf/requests"}}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("requests")

        assert result is not None
        assert result.owner == "psf"
        assert result.repo == "requests"

    @patch("requests.get")
    def test_map_package_with_repository_url(self, mock_get, mapper):
        """Test mapping package with Repository URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"project_urls": {"Repository": "https://github.com/numpy/numpy"}}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("numpy")

        assert result is not None
        assert result.owner == "numpy"
        assert result.repo == "numpy"

    @patch("requests.get")
    def test_map_package_with_homepage(self, mock_get, mapper):
        """Test mapping package with Homepage as fallback."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"project_urls": {"Homepage": "https://github.com/django/django"}}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("django")

        assert result is not None
        assert result.owner == "django"
        assert result.repo == "django"

    @patch("requests.get")
    def test_map_package_with_home_page(self, mock_get, mapper):
        """Test mapping package with home_page field."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"home_page": "https://github.com/flask/flask"}}
        mock_get.return_value = mock_response

        result = mapper.map_to_github("flask")

        assert result is not None
        assert result.owner == "flask"
        assert result.repo == "flask"

    @patch("requests.get")
    def test_map_package_with_git_extension(self, mock_get, mapper):
        """Test mapping package with .git extension."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"project_urls": {"Source": "https://github.com/owner/repo.git"}}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"

    @patch("requests.get")
    def test_map_package_with_branch_ref(self, mock_get, mapper):
        """Test mapping package with branch reference."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"project_urls": {"Source": "https://github.com/owner/repo#main"}}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"

    @patch("requests.get")
    def test_map_package_no_github_url(self, mock_get, mapper):
        """Test mapping package without GitHub URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"project_urls": {"Homepage": "https://example.com"}}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is None

    @patch("requests.get")
    def test_map_package_empty_project_urls(self, mock_get, mapper):
        """Test mapping package with empty project URLs."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"project_urls": {}}}
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is None

    @patch("requests.get")
    def test_map_package_null_project_urls(self, mock_get, mapper):
        """Test mapping package with null project URLs."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"project_urls": None}}
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is None

    @patch("requests.get")
    def test_map_package_404(self, mock_get, mapper):
        """Test mapping package that doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = mapper.map_to_github("nonexistent")

        assert result is None

    @patch("requests.get")
    def test_map_package_network_error(self, mock_get, mapper):
        """Test mapping package with network error."""
        mock_get.side_effect = requests.RequestException("Network error")

        result = mapper.map_to_github("test-pkg")

        assert result is None

    @patch("requests.get")
    def test_map_package_invalid_json(self, mock_get, mapper):
        """Test mapping package with invalid JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is None

    @patch("requests.get")
    def test_map_package_malformed_github_url(self, mock_get, mapper):
        """Test mapping package with malformed GitHub URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"project_urls": {"Source": "https://github.com/invalid"}}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-pkg")

        assert result is None


class TestNullMapper:
    """Tests for NullMapper (unsupported ecosystems)."""

    def test_null_mapper_always_returns_none(self):
        """Test null mapper always returns None."""
        mapper = NullMapper()

        result = mapper.map_to_github("any-package")

        assert result is None

    def test_null_mapper_multiple_calls(self):
        """Test null mapper consistently returns None."""
        mapper = NullMapper()

        assert mapper.map_to_github("package1") is None
        assert mapper.map_to_github("package2") is None
        assert mapper.map_to_github("package3") is None


class TestSearchOrgForPackage:
    """Tests for search_org_for_package function."""

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_exact_match_found(self, mock_get):
        """Test finding package by exact repo name match."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "owner": {"login": "CiscoSecurityServices"},
            "name": "corona-sdk",
        }
        mock_get.return_value = mock_response

        result = search_org_for_package("corona-sdk", "CiscoSecurityServices", "test-token")

        assert result is not None
        assert result.owner == "CiscoSecurityServices"
        assert result.repo == "corona-sdk"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_exact_match_with_underscore_variation(self, mock_get):
        """Test finding package with underscore to hyphen conversion."""
        # First call (exact name) fails, second call (hyphenated) succeeds
        mock_response_404 = Mock()
        mock_response_404.status_code = 404

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "owner": {"login": "TestOrg"},
            "name": "test-package",
        }

        mock_get.side_effect = [mock_response_404, mock_response_200]

        result = search_org_for_package("test_package", "TestOrg", "test-token")

        assert result is not None
        assert result.repo == "test-package"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_exact_match_with_hyphen_variation(self, mock_get):
        """Test finding package with hyphen to underscore conversion."""
        # First call (exact name) fails, second call (underscored) succeeds
        mock_response_404 = Mock()
        mock_response_404.status_code = 404

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "owner": {"login": "TestOrg"},
            "name": "test_package",
        }

        mock_get.side_effect = [mock_response_404, mock_response_200]

        result = search_org_for_package("test-package", "TestOrg", "test-token")

        assert result is not None
        assert result.repo == "test_package"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_org_search_fallback(self, mock_get):
        """Test falling back to org search when exact match fails."""
        # All exact matches fail (original name + underscore variation)
        mock_response_404 = Mock()
        mock_response_404.status_code = 404

        # Search returns results
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "items": [
                {"owner": {"login": "CiscoSecurityServices"}, "name": "corona-sdk-internal"}
            ]
        }

        # corona-sdk has hyphen, so it tries: corona-sdk, corona_sdk, then search
        mock_get.side_effect = [mock_response_404, mock_response_404, mock_search_response]

        result = search_org_for_package("corona-sdk", "CiscoSecurityServices", "test-token")

        assert result is not None
        assert result.owner == "CiscoSecurityServices"
        assert result.repo == "corona-sdk-internal"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_org_search_no_results(self, mock_get):
        """Test when org search returns no results."""
        mock_response_404 = Mock()
        mock_response_404.status_code = 404

        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {"items": []}

        # "nonexistent" has no hyphens/underscores, so only 1 exact match + search
        mock_get.side_effect = [mock_response_404, mock_search_response]

        result = search_org_for_package("nonexistent", "TestOrg", "test-token")

        assert result is None

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_org_search_api_failure(self, mock_get):
        """Test when org search API returns error."""
        mock_response_404 = Mock()
        mock_response_404.status_code = 404

        mock_search_response = Mock()
        mock_search_response.status_code = 403  # Rate limited

        # "package" has no hyphens/underscores, so only 1 exact match + search
        mock_get.side_effect = [mock_response_404, mock_search_response]

        result = search_org_for_package("package", "TestOrg", "test-token")

        assert result is None

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_without_token(self, mock_get):
        """Test search without authentication token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "owner": {"login": "TestOrg"},
            "name": "public-repo",
        }
        mock_get.return_value = mock_response

        result = search_org_for_package("public-repo", "TestOrg")

        assert result is not None
        # Verify no Authorization header
        call_args = mock_get.call_args
        headers = call_args[1].get("headers", {})
        assert "Authorization" not in headers

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = search_org_for_package("package", "TestOrg", "test-token")

        assert result is None

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_json_decode_error(self, mock_get):
        """Test handling of JSON decode errors."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        result = search_org_for_package("package", "TestOrg", "test-token")

        assert result is None
