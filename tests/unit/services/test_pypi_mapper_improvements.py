"""Tests for improved PyPI mapper flexibility."""

from unittest.mock import Mock, patch

import pytest

from sbom_fetcher.infrastructure.config import Config
from sbom_fetcher.services.mappers import PyPIPackageMapper


class TestPyPIMapperImprovements:
    """Test improved PyPI mapper with flexible key matching."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return Config()

    @pytest.fixture
    def mapper(self, config):
        """Create PyPI mapper."""
        return PyPIPackageMapper(config)

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_maps_source_code_key(self, mock_get, mapper):
        """Test mapping package with 'Source Code' key (e.g., bandit)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "project_urls": {
                    "Documentation": "https://bandit.readthedocs.io/",
                    "Source Code": "https://github.com/PyCQA/bandit",
                    "Issue Tracker": "https://github.com/PyCQA/bandit/issues",
                }
            }
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("bandit")

        assert result is not None
        assert result.owner == "PyCQA"
        assert result.repo == "bandit"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_maps_sources_key(self, mock_get, mapper):
        """Test mapping package with 'Sources' key (e.g., pytest-cov)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "project_urls": {
                    "Documentation": "https://pytest-cov.readthedocs.io/",
                    "Sources": "https://github.com/pytest-dev/pytest-cov",
                    "Issue Tracker": "https://github.com/pytest-dev/pytest-cov/issues",
                }
            }
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("pytest-cov")

        assert result is not None
        assert result.owner == "pytest-dev"
        assert result.repo == "pytest-cov"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_maps_code_key(self, mock_get, mapper):
        """Test mapping package with 'Code' key."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "project_urls": {
                    "Code": "https://github.com/test/example",
                    "Homepage": "https://example.com",
                }
            }
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("example")

        assert result is not None
        assert result.owner == "test"
        assert result.repo == "example"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_prefers_exact_match_over_partial(self, mock_get, mapper):
        """Test that exact key matches are preferred."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "project_urls": {
                    "Source": "https://github.com/exact/match",
                    "Source Code Documentation": "https://github.com/partial/match",
                }
            }
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test")

        assert result is not None
        assert result.owner == "exact"
        assert result.repo == "match"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_case_insensitive_partial_matching(self, mock_get, mapper):
        """Test case-insensitive partial matching for source/repository keys."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "project_urls": {
                    "GitHub Repository": "https://github.com/test/repo",
                    "Homepage": "https://example.com",
                }
            }
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test")

        assert result is not None
        assert result.owner == "test"
        assert result.repo == "repo"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_skips_non_github_urls(self, mock_get, mapper):
        """Test that non-GitHub URLs are skipped."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "project_urls": {
                    "Source Code": "https://gitlab.com/test/repo",
                    "Repository": "https://bitbucket.org/test/repo",
                    "Homepage": "https://example.com",
                }
            }
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test")

        assert result is None

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_github_homepage_fallback(self, mock_get, mapper):
        """Test fallback to Homepage if it points to GitHub."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "project_urls": {
                    "Documentation": "https://docs.example.com",
                    "Homepage": "https://github.com/test/homepage",
                }
            }
        }
        mock_get.return_value = mock_response

        result = mapper.map_to_github("test")

        assert result is not None
        assert result.owner == "test"
        assert result.repo == "homepage"

    @patch("sbom_fetcher.services.mappers.requests.get")
    def test_handles_github_url_variations(self, mock_get, mapper):
        """Test handling of various GitHub URL formats."""
        test_cases = [
            "https://github.com/owner/repo",
            "https://github.com/owner/repo.git",
            "https://github.com/owner/repo/",
            "http://github.com/owner/repo",
        ]

        for url in test_cases:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "info": {"project_urls": {"Source": url}}
            }
            mock_get.return_value = mock_response

            result = mapper.map_to_github("test")

            assert result is not None, f"Failed to parse: {url}"
            assert result.owner == "owner"
            assert result.repo == "repo"
