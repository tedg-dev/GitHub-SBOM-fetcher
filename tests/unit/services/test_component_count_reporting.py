"""Tests for component count reporting feature."""

import tempfile
from pathlib import Path

import pytest

from sbom_fetcher.domain.models import FetcherStats, GitHubRepository, PackageDependency
from sbom_fetcher.services.reporters import MarkdownReporter


class TestComponentCountReporting:
    """Tests for component count analysis in reports."""

    @pytest.fixture
    def reporter(self):
        """Create reporter instance."""
        return MarkdownReporter()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def basic_stats(self):
        """Basic statistics fixture."""
        stats = FetcherStats()
        stats.packages_in_sbom = 5
        stats.github_repos_mapped = 3
        stats.unique_repos = 3
        stats.sboms_downloaded = 3
        return stats

    @pytest.fixture
    def sample_packages(self):
        """Sample packages with GitHub repositories."""
        pkg1 = PackageDependency(
            name="pytest",
            version="7.0.0",
            purl="pkg:pypi/pytest@7.0.0",
            ecosystem="pypi",
            github_repository=GitHubRepository(owner="pytest-dev", repo="pytest"),
        )
        pkg2 = PackageDependency(
            name="requests",
            version="2.28.0",
            purl="pkg:pypi/requests@2.28.0",
            ecosystem="pypi",
            github_repository=GitHubRepository(owner="psf", repo="requests"),
        )
        pkg3 = PackageDependency(
            name="click",
            version="8.0.0",
            purl="pkg:pypi/click@8.0.0",
            ecosystem="pypi",
            github_repository=GitHubRepository(owner="pallets", repo="click"),
        )
        return [pkg1, pkg2, pkg3]

    def test_component_count_with_root_and_dependencies(
        self, reporter, temp_dir, basic_stats, sample_packages
    ):
        """Test report includes component count analysis with root and dependencies."""
        version_mapping = {
            "pytest-dev/pytest": {
                "package_name": "pytest",
                "ecosystem": "pypi",
                "component_count": 44,
            },
            "psf/requests": {
                "package_name": "requests",
                "ecosystem": "pypi",
                "component_count": 28,
            },
            "pallets/click": {
                "package_name": "click",
                "ecosystem": "pypi",
                "component_count": 13,
            },
        }
        dependency_component_counts = {
            "pytest-dev/pytest": 44,
            "psf/requests": 28,
            "pallets/click": 13,
        }

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="test-owner",
            repo="test-repo",
            stats=basic_stats,
            packages=sample_packages,
            version_mapping=version_mapping,
            failed_sboms=[],
            unmapped_packages=[],
            root_component_count=22,
            dependency_component_counts=dependency_component_counts,
        )

        content = (temp_dir / filename).read_text()

        # Check component count analysis section exists
        assert "## Component Count Analysis" in content
        assert "Root SBOM: `test-owner/test-repo`" in content
        assert "**Components:** 22" in content

        # Check dependency SBOMs section
        assert "### Dependency SBOMs" in content
        assert "pytest-dev/pytest" in content
        assert "44 components" in content
        assert "psf/requests" in content
        assert "28 components" in content
        assert "pallets/click" in content
        assert "13 components" in content

        # Check grand total
        assert "### Grand Total" in content
        assert "**Root SBOM components:** 22" in content
        assert "**All dependency SBOM components:** 85" in content
        assert "**🎯 Grand Total (Root + All Dependencies):** **107 components**" in content

    def test_component_count_sorted_by_count(
        self, reporter, temp_dir, basic_stats, sample_packages
    ):
        """Test dependencies are sorted by component count descending."""
        version_mapping = {
            "pytest-dev/pytest": {"package_name": "pytest", "ecosystem": "pypi"},
            "psf/requests": {"package_name": "requests", "ecosystem": "pypi"},
            "pallets/click": {"package_name": "click", "ecosystem": "pypi"},
        }
        dependency_component_counts = {
            "pallets/click": 13,  # Smallest
            "pytest-dev/pytest": 44,  # Largest
            "psf/requests": 28,  # Middle
        }

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=basic_stats,
            packages=sample_packages,
            version_mapping=version_mapping,
            failed_sboms=[],
            unmapped_packages=[],
            root_component_count=10,
            dependency_component_counts=dependency_component_counts,
        )

        content = (temp_dir / filename).read_text()

        # Find positions in the content
        pytest_pos = content.find("pytest-dev/pytest")
        requests_pos = content.find("psf/requests")
        click_pos = content.find("pallets/click")

        # Verify order: pytest (44) should come before requests (28) before click (13)
        assert pytest_pos < requests_pos < click_pos

    def test_component_count_without_package_info(self, reporter, temp_dir, basic_stats):
        """Test component count when version_mapping lacks package info."""
        version_mapping = {"owner/repo": {}}  # Missing package_name and ecosystem
        dependency_component_counts = {"owner/repo": 15}

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="test",
            repo="test",
            stats=basic_stats,
            packages=[],
            version_mapping=version_mapping,
            failed_sboms=[],
            unmapped_packages=[],
            root_component_count=5,
            dependency_component_counts=dependency_component_counts,
        )

        content = (temp_dir / filename).read_text()

        # Should still show the repo, just without ecosystem/package info
        assert "owner/repo" in content
        assert "15 components" in content

    def test_component_count_with_only_root(self, reporter, temp_dir, basic_stats):
        """Test component count with only root SBOM, no dependencies."""
        filename = reporter.generate(
            output_dir=temp_dir,
            owner="test",
            repo="test",
            stats=basic_stats,
            packages=[],
            version_mapping={},
            failed_sboms=[],
            unmapped_packages=[],
            root_component_count=50,
            dependency_component_counts={},
        )

        content = (temp_dir / filename).read_text()

        # Should show component count analysis
        assert "## Component Count Analysis" in content
        assert "Root SBOM: `test/test`" in content
        assert "**Components:** 50" in content

        # Should not show dependency section or grand total (no dependencies)
        assert "### Dependency SBOMs" not in content
        assert "### Grand Total" not in content

    def test_component_count_none_defaults(self, reporter, temp_dir, basic_stats):
        """Test component count with None defaults (backward compatibility)."""
        filename = reporter.generate(
            output_dir=temp_dir,
            owner="test",
            repo="test",
            stats=basic_stats,
            packages=[],
            version_mapping={},
            failed_sboms=[],
            unmapped_packages=[],
            # Not passing root_component_count or dependency_component_counts
        )

        content = (temp_dir / filename).read_text()

        # Should not show component count analysis section
        assert "## Component Count Analysis" not in content

    def test_component_count_with_zero_counts(self, reporter, temp_dir, basic_stats):
        """Test component count with all zeros."""
        filename = reporter.generate(
            output_dir=temp_dir,
            owner="test",
            repo="test",
            stats=basic_stats,
            packages=[],
            version_mapping={},
            failed_sboms=[],
            unmapped_packages=[],
            root_component_count=0,
            dependency_component_counts={},
        )

        content = (temp_dir / filename).read_text()

        # Should not show component count analysis when all zeros
        assert "## Component Count Analysis" not in content

    def test_component_count_grand_total_calculation(self, reporter, temp_dir, basic_stats):
        """Test grand total calculation is correct."""
        version_mapping = {
            "repo1": {"package_name": "pkg1", "ecosystem": "npm"},
            "repo2": {"package_name": "pkg2", "ecosystem": "npm"},
            "repo3": {"package_name": "pkg3", "ecosystem": "npm"},
        }
        dependency_component_counts = {
            "repo1": 100,
            "repo2": 200,
            "repo3": 300,
        }

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="test",
            repo="test",
            stats=basic_stats,
            packages=[],
            version_mapping=version_mapping,
            failed_sboms=[],
            unmapped_packages=[],
            root_component_count=50,
            dependency_component_counts=dependency_component_counts,
        )

        content = (temp_dir / filename).read_text()

        # Root: 50, Dependencies: 100+200+300=600, Grand Total: 650
        assert "**Root SBOM components:** 50" in content
        assert "**All dependency SBOM components:** 600" in content
        assert "**650 components**" in content
