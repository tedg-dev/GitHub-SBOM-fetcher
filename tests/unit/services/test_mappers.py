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
        # Verify URL encoding was used
        mock_get.assert_called_once()
        assert "%40babel" in mock_get.call_args[0][0]

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
