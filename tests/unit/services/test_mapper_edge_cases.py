"""Tests for edge cases in package mappers."""

from unittest.mock import Mock, patch

import pytest

from sbom_fetcher.infrastructure.config import Config
from sbom_fetcher.services.mappers import NPMPackageMapper, PyPIPackageMapper


class TestNPMMapperEdgeCases:
    """Test NPM mapper edge cases."""

    @pytest.fixture
    def mapper(self):
        """Create NPM mapper."""
        return NPMPackageMapper(Config())

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_npm_url_with_branch_reference(self, mock_get, mapper):
        """Test npm package with # branch reference in URL."""
        # This covers line 110 in mappers.py
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repository": {"type": "git", "url": "git+https://github.com/owner/repo.git#develop"}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-package")

        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_npm_invalid_path_structure(self, mock_get, mapper):
        """Test npm package with invalid GitHub URL path structure."""
        # This covers lines 119-122 in mappers.py (logging when parts < 2)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repository": {"type": "git", "url": "git+https://github.com/invalid"}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-package")

        assert result is None

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_npm_shorthand_with_missing_repo(self, mock_get, mapper):
        """Test npm shorthand format with missing repository part."""
        # This covers line 78 in mappers.py (unreachable else after return)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repository": "github:owner"  # Invalid shorthand, missing repo
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-package")

        assert result is None


class TestPyPIMapperEdgeCases:
    """Test PyPI mapper edge cases."""

    @pytest.fixture
    def mapper(self):
        """Create PyPI mapper."""
        return PyPIPackageMapper(Config())

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_pypi_url_with_branch_reference(self, mock_get, mapper):
        """Test PyPI package with # branch reference in URL."""
        # This covers line 199 in mappers.py
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"project_urls": {"Source": "https://github.com/owner/repo#main"}}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-package")

        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_pypi_url_with_dot_git_and_branch(self, mock_get, mapper):
        """Test PyPI package with .git extension and branch reference."""
        # This covers lines 196-199 in mappers.py
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"project_urls": {"Repository": "https://github.com/owner/repo.git#develop"}}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-package")

        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_pypi_url_ending_with_dot_git(self, mock_get, mapper):
        """Test PyPI package URL ending with .git."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"project_urls": {"Source Code": "https://github.com/owner/repo.git"}}
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test-package")

        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"
