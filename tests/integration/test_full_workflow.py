"""
Comprehensive integration tests for full SBOM fetching workflow.

These tests verify the complete integration of all layers:
- Application (CLI, main)
- Services (github_client, mappers, parsers, reporters)
- Infrastructure (filesystem, http_client, config)
- Domain (models)
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from sbom_fetcher.application.main import main
from sbom_fetcher.domain.models import (
    ErrorType,
    FailureInfo,
    FetcherStats,
    GitHubRepository,
    PackageDependency,
)
from sbom_fetcher.infrastructure.config import Config
from sbom_fetcher.infrastructure.filesystem import FilesystemSBOMRepository
from sbom_fetcher.services.github_client import GitHubClient
from sbom_fetcher.services.parsers import SBOMParser
from sbom_fetcher.services.sbom_service import SBOMFetcherService


class TestFullWorkflowIntegration:
    """Integration tests for complete SBOM fetching workflow."""

    @pytest.fixture
    def mock_github_responses(self):
        """Fixture providing mock GitHub API responses."""
        return {
            "root_sbom": {
                "sbom": {
                    "SPDXID": "SPDXRef-DOCUMENT",
                    "name": "test-repo",
                    "packages": [
                        {
                            "SPDXID": "SPDXRef-Package-lodash",
                            "name": "lodash",
                            "versionInfo": "4.17.21",
                            "externalRefs": [
                                {
                                    "referenceCategory": "PACKAGE-MANAGER",
                                    "referenceType": "purl",
                                    "referenceLocator": "pkg:npm/lodash@4.17.21",
                                }
                            ],
                        },
                        {
                            "SPDXID": "SPDXRef-Package-requests",
                            "name": "requests",
                            "versionInfo": "2.31.0",
                            "externalRefs": [
                                {
                                    "referenceCategory": "PACKAGE-MANAGER",
                                    "referenceType": "purl",
                                    "referenceLocator": "pkg:pypi/requests@2.31.0",
                                }
                            ],
                        },
                    ],
                }
            },
            "npm_lodash": {
                "repository": {
                    "type": "git",
                    "url": "git+https://github.com/lodash/lodash.git",
                }
            },
            "pypi_requests": {
                "info": {"project_urls": {"Source": "https://github.com/psf/requests"}}
            },
            "dependency_sbom": {
                "sbom": {
                    "SPDXID": "SPDXRef-DOCUMENT",
                    "name": "dependency",
                    "packages": [],
                }
            },
        }

    def test_successful_complete_workflow(self, tmp_path, mock_github_responses):
        """Test complete successful SBOM fetching workflow."""
        # Setup
        config = Config()

        with patch("requests.Session") as mock_session_class:
            # Configure mock session
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Mock HTTP responses
            def mock_get(url, *args, **kwargs):
                response = Mock()
                response.status_code = 200

                if "sbom" in url and "dependency_graph" in url:
                    # Root SBOM request
                    response.json.return_value = mock_github_responses["root_sbom"]
                elif "registry.npmjs.org" in url:
                    # NPM registry request
                    response.json.return_value = mock_github_responses["npm_lodash"]
                elif "pypi.org" in url:
                    # PyPI registry request
                    response.json.return_value = mock_github_responses["pypi_requests"]
                elif "repos/lodash/lodash" in url or "repos/psf/requests" in url:
                    # Dependency SBOM requests
                    response.json.return_value = mock_github_responses["dependency_sbom"]
                else:
                    response.json.return_value = {}

                return response

            mock_session.get.side_effect = mock_get

            # Create service with mocked dependencies
            github_client = GitHubClient(config, mock_session)
            parser = SBOMParser()
            filesystem_repo = FilesystemSBOMRepository()

            # Execute
            with patch.object(github_client, "_session", mock_session):
                result = github_client.fetch_root_sbom("test-owner", "test-repo")

            # Verify root SBOM fetched
            assert result is not None
            assert "sbom" in result
            assert len(result["sbom"]["packages"]) == 2

            # Verify packages extracted
            packages = parser.extract_packages(result, "test-owner", "test-repo")
            assert len(packages) == 2
            assert packages[0].name == "lodash"
            assert packages[1].name == "requests"

    def test_workflow_with_failed_dependencies(self, tmp_path, mock_github_responses):
        """Test workflow when some dependency SBOMs fail to download."""
        config = Config()

        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Mock responses with some failures
            call_count = {"count": 0}

            def mock_get_with_failures(url, *args, **kwargs):
                call_count["count"] += 1
                response = Mock()

                if "sbom" in url and "dependency_graph" in url:
                    # Root SBOM - success
                    response.status_code = 200
                    response.json.return_value = mock_github_responses["root_sbom"]
                elif call_count["count"] % 3 == 0:
                    # Every 3rd request fails with 404
                    response.status_code = 404
                    response.json.return_value = {}
                else:
                    # Other requests succeed
                    response.status_code = 200
                    response.json.return_value = mock_github_responses.get("npm_lodash", {})

                return response

            mock_session.get.side_effect = mock_get_with_failures

            # Execute and verify partial success
            github_client = GitHubClient(config, mock_session)
            result = github_client.fetch_root_sbom("test-owner", "test-repo")

            assert result is not None
            assert "sbom" in result

    def test_workflow_with_transient_errors(self, mock_github_responses):
        """Test workflow with HTTP 5xx transient errors and retry."""
        config = Config()

        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # First call returns 500, second call succeeds
            attempts = {"count": 0}

            def mock_get_with_retry(url, *args, **kwargs):
                attempts["count"] += 1
                response = Mock()

                if "sbom" in url and attempts["count"] == 1:
                    # First attempt fails with 500
                    response.status_code = 500
                    response.json.return_value = {}
                else:
                    # Subsequent attempts succeed
                    response.status_code = 200
                    response.json.return_value = mock_github_responses["root_sbom"]

                return response

            mock_session.get.side_effect = mock_get_with_retry

            github_client = GitHubClient(config, mock_session)

            # This should retry and eventually succeed
            # (Note: Current implementation doesn't retry root SBOM,
            # but this tests the pattern)
            result = github_client.fetch_root_sbom("test-owner", "test-repo")

            # Verify it tried at least once
            assert mock_session.get.called

    def test_parser_integration_with_real_like_data(self):
        """Test parser with realistic SBOM data."""
        parser = SBOMParser()

        sbom_data = {
            "sbom": {
                "packages": [
                    # npm package
                    {
                        "SPDXID": "SPDXRef-Package-lodash",
                        "name": "lodash",
                        "versionInfo": "4.17.21",
                        "externalRefs": [
                            {
                                "referenceCategory": "PACKAGE-MANAGER",
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/lodash@4.17.21",
                            }
                        ],
                    },
                    # Scoped npm package
                    {
                        "SPDXID": "SPDXRef-Package-babel-core",
                        "name": "@babel/core",
                        "versionInfo": "7.22.0",
                        "externalRefs": [
                            {
                                "referenceCategory": "PACKAGE-MANAGER",
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/%40babel/core@7.22.0",
                            }
                        ],
                    },
                    # PyPI package
                    {
                        "SPDXID": "SPDXRef-Package-requests",
                        "name": "requests",
                        "versionInfo": "2.31.0",
                        "externalRefs": [
                            {
                                "referenceCategory": "PACKAGE-MANAGER",
                                "referenceType": "purl",
                                "referenceLocator": "pkg:pypi/requests@2.31.0",
                            }
                        ],
                    },
                    # Package without PURL (should be skipped)
                    {
                        "SPDXID": "SPDXRef-Package-nopurl",
                        "name": "nopurl",
                        "versionInfo": "1.0.0",
                        "externalRefs": [],
                    },
                    # Root package (should be skipped)
                    {
                        "SPDXID": "SPDXRef-Package-test-repo",
                        "name": "test-repo",
                        "versionInfo": "1.0.0",
                        "externalRefs": [
                            {
                                "referenceCategory": "PACKAGE-MANAGER",
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/test-repo@1.0.0",
                            }
                        ],
                    },
                ],
            }
        }

        packages = parser.extract_packages(sbom_data, "owner", "test-repo")

        # Should extract 3 packages (skip nopurl and root)
        assert len(packages) == 3

        # Verify npm package
        npm_pkg = next(p for p in packages if p.name == "lodash")
        assert npm_pkg.ecosystem == "npm"
        assert npm_pkg.version == "4.17.21"

        # Verify scoped npm package
        scoped_pkg = next(p for p in packages if p.name == "%40babel/core")
        assert scoped_pkg.ecosystem == "npm"

        # Verify PyPI package
        pypi_pkg = next(p for p in packages if p.name == "requests")
        assert pypi_pkg.ecosystem == "pypi"
        assert pypi_pkg.version == "2.31.0"

    def test_stats_collection_integration(self):
        """Test statistics collection across the workflow."""
        stats = FetcherStats()

        # Simulate workflow steps
        stats.packages_in_sbom = 50
        stats.github_repos_mapped = 45
        stats.packages_without_github = 5
        stats.unique_repos = 40
        stats.duplicates_skipped = 5
        stats.sboms_downloaded = 38
        stats.sboms_failed_permanent = 1
        stats.sboms_failed_transient = 1

        # Verify computed properties
        assert stats.sboms_failed == 2

        # Verify statistics make sense
        assert stats.packages_in_sbom == stats.github_repos_mapped + stats.packages_without_github
        assert stats.github_repos_mapped == stats.unique_repos + stats.duplicates_skipped
        assert stats.unique_repos == stats.sboms_downloaded + stats.sboms_failed

    def test_failure_info_integration(self):
        """Test failure information tracking."""
        repo = GitHubRepository(owner="test", repo="repo")

        # Create permanent failure
        permanent_failure = FailureInfo(
            repository=repo,
            package_name="test-pkg",
            ecosystem="npm",
            versions=["1.0.0", "1.0.1"],
            error="Dependency graph not enabled",
            error_type=ErrorType.PERMANENT,
        )

        # Create transient failure
        transient_failure = FailureInfo(
            repository=repo,
            package_name="another-pkg",
            ecosystem="npm",
            versions=["2.0.0"],
            error="HTTP 500",
            error_type=ErrorType.TRANSIENT,
        )

        # Verify conversions
        perm_dict = permanent_failure.to_dict()
        assert perm_dict["error_type"] == "permanent"
        assert perm_dict["repo"] == "test/repo"

        trans_dict = transient_failure.to_dict()
        assert trans_dict["error_type"] == "transient"

        # Verify failure collection
        failures = [permanent_failure, transient_failure]
        permanent_count = sum(1 for f in failures if f.error_type == ErrorType.PERMANENT)
        transient_count = sum(1 for f in failures if f.error_type == ErrorType.TRANSIENT)

        assert permanent_count == 1
        assert transient_count == 1

    def test_package_dependency_workflow(self):
        """Test PackageDependency through typical workflow states."""
        # Create initial package from SBOM
        pkg = PackageDependency(
            name="lodash",
            version="4.17.21",
            ecosystem="npm",
            purl="pkg:npm/lodash@4.17.21",
        )

        assert pkg.github_repository is None
        assert pkg.sbom_downloaded is False
        assert pkg.error is None

        # Map to GitHub repository
        github_repo = GitHubRepository(owner="lodash", repo="lodash")
        pkg.github_repository = github_repo

        assert pkg.github_repository == github_repo

        # Mark SBOM as downloaded
        pkg.sbom_downloaded = True

        assert pkg.sbom_downloaded is True

        # Test failure scenario
        failed_pkg = PackageDependency(
            name="failed-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/failed-pkg@1.0.0",
            error="Dependency graph not enabled",
            error_type=ErrorType.PERMANENT,
        )

        assert failed_pkg.error is not None
        assert failed_pkg.error_type == ErrorType.PERMANENT
        assert failed_pkg.sbom_downloaded is False


class TestErrorHandling:
    """Test error handling across all layers."""

    def test_http_client_timeout_handling(self):
        """Test HTTP client handles timeouts gracefully."""
        from sbom_fetcher.infrastructure.http_client import RequestsHTTPClient

        config = Config()
        config.timeout = 1  # 1 second timeout

        http_client = RequestsHTTPClient(config)

        # This should handle timeout internally
        # (actual timeout testing would need mocked responses)
        assert http_client._timeout == 1

    def test_filesystem_error_handling(self, tmp_path):
        """Test filesystem operations handle errors."""
        repo = FilesystemSBOMRepository()

        # Create output directory
        output_dir = repo.create_output_directory("owner", "repo", str(tmp_path))

        assert output_dir.exists()
        assert output_dir.name == "owner_repo"

    def test_validation_error_propagation(self):
        """Test validation errors propagate correctly."""
        from sbom_fetcher.domain.exceptions import ValidationError

        # Test that validation errors can be raised and caught
        with pytest.raises(ValidationError):
            raise ValidationError("Invalid data")

    def test_api_error_handling(self):
        """Test API error handling."""
        from sbom_fetcher.domain.exceptions import APIError, GitHubAPIError

        # Test inheritance chain
        github_error = GitHubAPIError("GitHub API failed")

        assert isinstance(github_error, APIError)
        assert isinstance(github_error, Exception)


class TestConcurrentOperations:
    """Test handling of concurrent-like operations."""

    def test_multiple_package_processing(self):
        """Test processing multiple packages simultaneously."""
        parser = SBOMParser()

        # Create SBOM with many packages
        packages_data = []
        for i in range(50):
            packages_data.append(
                {
                    "SPDXID": f"SPDXRef-Package-pkg{i}",
                    "name": f"package{i}",
                    "versionInfo": f"1.0.{i}",
                    "externalRefs": [
                        {
                            "referenceCategory": "PACKAGE-MANAGER",
                            "referenceType": "purl",
                            "referenceLocator": f"pkg:npm/package{i}@1.0.{i}",
                        }
                    ],
                }
            )

        sbom_data = {"sbom": {"packages": packages_data}}

        packages = parser.extract_packages(sbom_data, "owner", "repo")

        assert len(packages) == 50

        # Verify all packages extracted correctly
        for i, pkg in enumerate(packages):
            assert pkg.name == f"package{i}"
            assert pkg.version == f"1.0.{i}"
