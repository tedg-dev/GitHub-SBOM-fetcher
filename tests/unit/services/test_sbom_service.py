"""Comprehensive unit tests for SBOM fetcher service - Complete Coverage."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, call, mock_open, patch

import pytest

from sbom_fetcher.domain.models import (
    ErrorType,
    FetcherResult,
    FetcherStats,
    GitHubRepository,
    PackageDependency,
)
from sbom_fetcher.infrastructure.config import Config
from sbom_fetcher.services.sbom_service import SBOMFetcherService, save_root_sbom


class TestSBOMFetcherServiceInitialization:
    """Tests for service initialization."""

    def test_service_initialization(self):
        """Test service initializes with all dependencies."""
        github_client = Mock()
        mapper_factory = Mock()
        repository = Mock()
        reporter = Mock()
        config = Config()

        service = SBOMFetcherService(
            github_client=github_client,
            mapper_factory=mapper_factory,
            repository=repository,
            reporter=reporter,
            config=config,
        )

        assert service._github_client == github_client
        assert service._mapper_factory == mapper_factory
        assert service._repository == repository
        assert service._reporter == reporter
        assert service._config == config
        assert service._parser is not None


class TestFetchAllSBOMs:
    """Comprehensive tests for main workflow."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create all mocked dependencies."""
        github_client = Mock()
        mapper_factory = Mock()
        repository = Mock()
        reporter = Mock()
        config = Config()
        return {
            "github_client": github_client,
            "mapper_factory": mapper_factory,
            "repository": repository,
            "reporter": reporter,
            "config": config,
        }

    @pytest.fixture
    def service(self, mock_dependencies):
        """Create service with mocked dependencies."""
        return SBOMFetcherService(**mock_dependencies)

    @pytest.fixture
    def mock_session(self):
        """Create mock requests session."""
        return Mock()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_fetch_all_sboms_root_fetch_failure(self, service, mock_session, mock_dependencies):
        """Test handling of root SBOM fetch failure."""
        mock_dependencies["github_client"].fetch_root_sbom.return_value = None

        result = service.fetch_all_sboms("owner", "repo", mock_session)

        assert isinstance(result, FetcherResult)
        assert len(result.packages) == 0
        assert len(result.failed_downloads) == 0
        assert result.stats.packages_in_sbom == 0

    @patch("sbom_fetcher.services.sbom_service.save_root_sbom")
    @patch("sbom_fetcher.services.sbom_service.Path")
    def test_fetch_all_sboms_no_packages_found(
        self, mock_path, mock_save, service, mock_session, mock_dependencies
    ):
        """Test handling when no packages found in SBOM."""
        # Setup mocks
        mock_dependencies["github_client"].fetch_root_sbom.return_value = {"sbom": {"packages": []}}

        # Mock Path operations
        mock_output_dir = Mock()
        mock_output_dir.mkdir = Mock()
        mock_path.return_value = mock_output_dir
        mock_output_dir.__truediv__ = Mock(return_value=mock_output_dir)

        with patch.object(service._parser, "extract_packages", return_value=[]):
            result = service.fetch_all_sboms("owner", "repo", mock_session)

        assert len(result.packages) == 0
        assert result.stats.packages_in_sbom == 0

    @patch("sbom_fetcher.services.sbom_service.save_root_sbom")
    @patch("sbom_fetcher.services.sbom_service.Path")
    @patch("sbom_fetcher.services.sbom_service.time.sleep")
    def test_fetch_all_sboms_successful_workflow(
        self, mock_sleep, mock_path, mock_save, service, mock_session, mock_dependencies
    ):
        """Test complete successful workflow."""
        # Setup root SBOM
        root_sbom = {"sbom": {"packages": [{"name": "test"}]}}
        mock_dependencies["github_client"].fetch_root_sbom.return_value = root_sbom

        # Setup packages
        pkg1 = PackageDependency(
            name="lodash",
            version="4.17.21",
            ecosystem="npm",
            purl="pkg:npm/lodash@4.17.21",
            github_repository=GitHubRepository(owner="lodash", repo="lodash"),
        )
        pkg2 = PackageDependency(
            name="requests",
            version="2.31.0",
            ecosystem="pypi",
            purl="pkg:pypi/requests@2.31.0",
            github_repository=GitHubRepository(owner="psf", repo="requests"),
        )

        # Mock Path operations
        mock_output_dir = Mock()
        mock_output_dir.mkdir = Mock()
        mock_path.return_value = mock_output_dir
        mock_output_dir.__truediv__ = Mock(return_value=mock_output_dir)
        mock_output_dir.__str__ = Mock(return_value="/tmp/test")

        # Mock parser
        with patch.object(service._parser, "extract_packages", return_value=[pkg1, pkg2]):
            # Mock mapper
            mock_dependencies["mapper_factory"].map_package_to_github.return_value = True

            # Mock downloader
            mock_dependencies["github_client"].download_dependency_sbom.return_value = True

            # Mock reporter
            mock_dependencies["reporter"].generate.return_value = "report.md"

            # Mock json.dump for version_mapping
            with patch("builtins.open", mock_open()):
                with patch("sbom_fetcher.services.sbom_service.json.dump"):
                    result = service.fetch_all_sboms("owner", "repo", mock_session)

        assert result.stats.packages_in_sbom == 2
        assert result.stats.github_repos_mapped == 2
        assert result.stats.unique_repos == 2
        assert result.stats.sboms_downloaded == 2

    @patch("sbom_fetcher.services.sbom_service.save_root_sbom")
    @patch("sbom_fetcher.services.sbom_service.Path")
    def test_fetch_all_sboms_with_unmapped_packages(
        self, mock_path, mock_save, service, mock_session, mock_dependencies
    ):
        """Test workflow with packages that can't be mapped."""
        root_sbom = {"sbom": {"packages": [{"name": "test"}]}}
        mock_dependencies["github_client"].fetch_root_sbom.return_value = root_sbom

        pkg = PackageDependency(
            name="unmapped",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/unmapped@1.0.0",
        )

        # Mock Path
        mock_output_dir = Mock()
        mock_output_dir.mkdir = Mock()
        mock_path.return_value = mock_output_dir
        mock_output_dir.__truediv__ = Mock(return_value=mock_output_dir)
        mock_output_dir.__str__ = Mock(return_value="/tmp/test")

        with patch.object(service._parser, "extract_packages", return_value=[pkg]):
            mock_dependencies["mapper_factory"].map_package_to_github.return_value = False
            mock_dependencies["reporter"].generate.return_value = "report.md"

            with patch("builtins.open", mock_open()):
                with patch("sbom_fetcher.services.sbom_service.json.dump"):
                    result = service.fetch_all_sboms("owner", "repo", mock_session)

        assert result.stats.packages_without_github == 1
        assert len(result.unmapped_packages) == 1

    @patch("sbom_fetcher.services.sbom_service.save_root_sbom")
    @patch("sbom_fetcher.services.sbom_service.Path")
    @patch("sbom_fetcher.services.sbom_service.time.sleep")
    def test_fetch_all_sboms_with_failed_downloads(
        self, mock_sleep, mock_path, mock_save, service, mock_session, mock_dependencies
    ):
        """Test workflow with failed SBOM downloads."""
        root_sbom = {"sbom": {"packages": [{"name": "test"}]}}
        mock_dependencies["github_client"].fetch_root_sbom.return_value = root_sbom

        pkg = PackageDependency(
            name="failing",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/failing@1.0.0",
            github_repository=GitHubRepository(owner="test", repo="failing"),
        )

        # Mock Path
        mock_output_dir = Mock()
        mock_output_dir.mkdir = Mock()
        mock_path.return_value = mock_output_dir
        mock_output_dir.__truediv__ = Mock(return_value=mock_output_dir)
        mock_output_dir.__str__ = Mock(return_value="/tmp/test")

        with patch.object(service._parser, "extract_packages", return_value=[pkg]):
            mock_dependencies["mapper_factory"].map_package_to_github.return_value = True
            mock_dependencies["github_client"].download_dependency_sbom.return_value = False

            # Set error on package
            pkg.error = "Dependency graph not enabled"
            pkg.error_type = ErrorType.PERMANENT

            mock_dependencies["reporter"].generate.return_value = "report.md"

            with patch("builtins.open", mock_open()):
                with patch("sbom_fetcher.services.sbom_service.json.dump"):
                    result = service.fetch_all_sboms("owner", "repo", mock_session)

        assert result.stats.sboms_failed_permanent == 1
        assert len(result.failed_downloads) == 1
        assert result.failed_downloads[0].error == "Dependency graph not enabled"

    @patch("sbom_fetcher.services.sbom_service.save_root_sbom")
    @patch("sbom_fetcher.services.sbom_service.Path")
    @patch("sbom_fetcher.services.sbom_service.time.sleep")
    def test_fetch_all_sboms_with_deduplication(
        self, mock_sleep, mock_path, mock_save, service, mock_session, mock_dependencies
    ):
        """Test workflow handles duplicate repositories."""
        root_sbom = {"sbom": {"packages": [{"name": "test"}]}}
        mock_dependencies["github_client"].fetch_root_sbom.return_value = root_sbom

        # Same repo, different versions
        pkg1 = PackageDependency(
            name="lodash",
            version="4.17.20",
            ecosystem="npm",
            purl="pkg:npm/lodash@4.17.20",
            github_repository=GitHubRepository(owner="lodash", repo="lodash"),
        )
        pkg2 = PackageDependency(
            name="lodash",
            version="4.17.21",
            ecosystem="npm",
            purl="pkg:npm/lodash@4.17.21",
            github_repository=GitHubRepository(owner="lodash", repo="lodash"),
        )

        # Mock Path
        mock_output_dir = Mock()
        mock_output_dir.mkdir = Mock()
        mock_path.return_value = mock_output_dir
        mock_output_dir.__truediv__ = Mock(return_value=mock_output_dir)
        mock_output_dir.__str__ = Mock(return_value="/tmp/test")

        with patch.object(service._parser, "extract_packages", return_value=[pkg1, pkg2]):
            mock_dependencies["mapper_factory"].map_package_to_github.return_value = True
            mock_dependencies["github_client"].download_dependency_sbom.return_value = True
            mock_dependencies["reporter"].generate.return_value = "report.md"

            with patch("builtins.open", mock_open()):
                with patch("sbom_fetcher.services.sbom_service.json.dump"):
                    result = service.fetch_all_sboms("owner", "repo", mock_session)

        # Should have 1 unique repo, 1 duplicate skipped
        assert result.stats.unique_repos == 1
        assert result.stats.duplicates_skipped == 1
        # Should only download once
        assert result.stats.sboms_downloaded == 1

    @patch("sbom_fetcher.services.sbom_service.save_root_sbom")
    @patch("sbom_fetcher.services.sbom_service.Path")
    def test_fetch_all_sboms_transient_error(
        self, mock_path, mock_save, service, mock_session, mock_dependencies
    ):
        """Test workflow with transient error handling."""
        root_sbom = {"sbom": {"packages": [{"name": "test"}]}}
        mock_dependencies["github_client"].fetch_root_sbom.return_value = root_sbom

        pkg = PackageDependency(
            name="timeout",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/timeout@1.0.0",
            github_repository=GitHubRepository(owner="test", repo="timeout"),
        )

        # Mock Path
        mock_output_dir = Mock()
        mock_output_dir.mkdir = Mock()
        mock_path.return_value = mock_output_dir
        mock_output_dir.__truediv__ = Mock(return_value=mock_output_dir)
        mock_output_dir.__str__ = Mock(return_value="/tmp/test")

        with patch.object(service._parser, "extract_packages", return_value=[pkg]):
            mock_dependencies["mapper_factory"].map_package_to_github.return_value = True
            mock_dependencies["github_client"].download_dependency_sbom.return_value = False

            pkg.error = "Timeout"
            pkg.error_type = ErrorType.TRANSIENT

            mock_dependencies["reporter"].generate.return_value = "report.md"

            with patch("builtins.open", mock_open()):
                with patch("sbom_fetcher.services.sbom_service.json.dump"):
                    result = service.fetch_all_sboms("owner", "repo", mock_session)

        assert result.stats.sboms_failed_transient == 1
        assert result.failed_downloads[0].error_type == ErrorType.TRANSIENT


class TestSaveRootSBOM:
    """Tests for save_root_sbom helper function."""

    def test_save_root_sbom(self, tmp_path):
        """Test saving root SBOM to file."""
        sbom_data = {"sbom": {"packages": []}}
        output_dir = str(tmp_path)

        save_root_sbom(sbom_data, output_dir, "owner", "repo")

        expected_file = tmp_path / "owner_repo_root.json"
        assert expected_file.exists()

        with open(expected_file) as f:
            import json

            loaded_data = json.load(f)
            assert loaded_data == sbom_data

    def test_save_root_sbom_filename_format(self, tmp_path):
        """Test correct filename format."""
        sbom_data = {"test": "data"}

        save_root_sbom(sbom_data, str(tmp_path), "myowner", "myrepo")

        expected_file = tmp_path / "myowner_myrepo_root.json"
        assert expected_file.exists()
