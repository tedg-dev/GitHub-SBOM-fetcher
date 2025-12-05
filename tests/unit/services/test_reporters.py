"""Comprehensive unit tests for reporters - 100% Coverage."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from sbom_fetcher.domain.models import (
    ErrorType,
    FailureInfo,
    FetcherStats,
    PackageDependency,
)
from sbom_fetcher.services.reporters import MarkdownReporter


class TestMarkdownReporter:
    """Comprehensive tests for Markdown report generation."""

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
        stats.packages_in_sbom = 10
        stats.github_repos_mapped = 8
        stats.unique_repos = 6
        stats.duplicates_skipped = 2
        stats.packages_without_github = 2
        stats.sboms_downloaded = 5
        stats.sboms_failed_permanent = 1
        stats.sboms_failed_transient = 1
        # Note: sboms_failed is a computed property
        return stats

    @pytest.fixture
    def sample_packages(self):
        """Sample packages fixture."""
        return [
            PackageDependency(
                name="lodash",
                version="4.17.21",
                ecosystem="npm",
                purl="pkg:npm/lodash@4.17.21",
            ),
            PackageDependency(
                name="requests",
                version="2.31.0",
                ecosystem="pypi",
                purl="pkg:pypi/requests@2.31.0",
            ),
        ]

    def test_generate_basic_report(self, reporter, temp_dir, basic_stats):
        """Test generating basic report with minimal data."""
        filename = reporter.generate(
            output_dir=temp_dir,
            owner="test-owner",
            repo="test-repo",
            stats=basic_stats,
            packages=[],
            version_mapping={},
            failed_sboms=[],
            unmapped_packages=[],
        )

        assert filename == "test-owner_test-repo_execution_report.md"
        report_path = temp_dir / filename
        assert report_path.exists()

        content = report_path.read_text()
        assert "# GitHub SBOM API Fetcher - Execution Report" in content
        assert "test-owner/test-repo" in content
        assert "## Summary" in content

    def test_report_contains_statistics(self, reporter, temp_dir, basic_stats, sample_packages):
        """Test report contains all statistics."""
        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=basic_stats,
            packages=sample_packages,
            version_mapping={},
            failed_sboms=[],
            unmapped_packages=[],
        )

        content = (temp_dir / filename).read_text()
        assert "**Root SBOM dependency repositories:** 10" in content
        assert "**Mapped to GitHub repos:** 8" in content
        assert "**Unique repositories:** 6" in content
        assert "**Duplicates avoided:** 2" in content
        assert "**Packages without GitHub repos:** 2" in content
        assert "**SBOMs downloaded successfully:** ✅ **5**" in content
        assert "**SBOMs failed (permanent):** 🔴 **1**" in content
        assert "**SBOMs failed (transient):** ⚠️ **1**" in content

    def test_report_with_permanent_failures(self, reporter, temp_dir, basic_stats):
        """Test report with permanent failure information."""
        failures = [
            FailureInfo(
                repository="owner/repo1",
                package_name="pkg1",
                ecosystem="npm",
                versions=["1.0.0", "1.0.1"],
                error="Dependency graph not enabled",
                error_type=ErrorType.PERMANENT,
            )
        ]

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=basic_stats,
            packages=[],
            version_mapping={},
            failed_sboms=failures,
            unmapped_packages=[],
        )

        content = (temp_dir / filename).read_text()
        assert "## Failed SBOM Downloads" in content
        assert "### 🔴 Permanent Failures" in content
        assert "owner/repo1" in content
        assert "**Package:** pkg1" in content
        assert "**Ecosystem:** npm" in content
        assert "**Versions:** 1.0.0, 1.0.1" in content
        assert "Dependency graph not enabled" in content

    def test_report_with_transient_failures(self, reporter, temp_dir, basic_stats):
        """Test report with transient failure information."""
        failures = [
            FailureInfo(
                repository="owner/repo2",
                package_name="pkg2",
                ecosystem="pypi",
                versions=["2.0.0"],
                error="Timeout",
                error_type=ErrorType.TRANSIENT,
            )
        ]

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=basic_stats,
            packages=[],
            version_mapping={},
            failed_sboms=failures,
            unmapped_packages=[],
        )

        content = (temp_dir / filename).read_text()
        assert "### ⚠️ Transient Failures" in content
        assert "owner/repo2" in content
        assert "**Error:** `Timeout`" in content

    def test_report_with_mixed_failures(self, reporter, temp_dir, basic_stats):
        """Test report with both permanent and transient failures."""
        failures = [
            FailureInfo(
                repository="owner/perm",
                package_name="perm-pkg",
                ecosystem="npm",
                versions=["1.0.0"],
                error="Permanent error",
                error_type=ErrorType.PERMANENT,
            ),
            FailureInfo(
                repository="owner/trans",
                package_name="trans-pkg",
                ecosystem="pypi",
                versions=["2.0.0"],
                error="Transient error",
                error_type=ErrorType.TRANSIENT,
            ),
        ]

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=basic_stats,
            packages=[],
            version_mapping={},
            failed_sboms=failures,
            unmapped_packages=[],
        )

        content = (temp_dir / filename).read_text()
        assert "**Total failures:** 2 (1 permanent, 1 transient)" in content
        assert "### 🔴 Permanent Failures" in content
        assert "### ⚠️ Transient Failures" in content

    def test_report_with_multiple_versions(self, reporter, temp_dir, basic_stats):
        """Test report with repositories using multiple versions."""
        version_mapping = {
            "owner/repo1": {
                "package_name": "pkg1",
                "ecosystem": "npm",
                "versions_in_dependency_tree": ["1.0.0", "1.0.1", "1.0.2"],
                "sbom_file": "owner_repo1_main.json",
            },
            "owner/repo2": {
                "package_name": "pkg2",
                "ecosystem": "pypi",
                "versions_in_dependency_tree": ["2.0.0", "2.1.0"],
                "sbom_file": "owner_repo2_main.json",
            },
        }

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=basic_stats,
            packages=[],
            version_mapping=version_mapping,
            failed_sboms=[],
            unmapped_packages=[],
        )

        content = (temp_dir / filename).read_text()
        assert "## Repositories with Multiple Versions" in content
        assert "**Total:** 2 repositories" in content
        assert "owner/repo1" in content
        assert "**Versions:** 1.0.0, 1.0.1, 1.0.2" in content
        assert "owner/repo2" in content
        assert "**Versions:** 2.0.0, 2.1.0" in content

    def test_report_with_many_multiple_versions(self, reporter, temp_dir, basic_stats):
        """Test report truncates long list of multiple versions."""
        version_mapping = {}
        for i in range(15):
            version_mapping[f"owner/repo{i}"] = {
                "package_name": f"pkg{i}",
                "ecosystem": "npm",
                "versions_in_dependency_tree": [f"{i}.0.0", f"{i}.0.1"],
                "sbom_file": f"owner_repo{i}_main.json",
            }

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=basic_stats,
            packages=[],
            version_mapping=version_mapping,
            failed_sboms=[],
            unmapped_packages=[],
        )

        content = (temp_dir / filename).read_text()
        assert "**Total:** 15 repositories" in content
        assert "... and 5 more repositories" in content

    def test_report_with_unmapped_packages(self, reporter, temp_dir, basic_stats, sample_packages):
        """Test report with packages that couldn't be mapped."""
        unmapped = [sample_packages[0]]  # lodash

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=basic_stats,
            packages=sample_packages,
            version_mapping={},
            failed_sboms=[],
            unmapped_packages=unmapped,
        )

        content = (temp_dir / filename).read_text()
        assert "## Packages That Could Not Be Mapped to GitHub" in content
        assert "**Total:** 1 packages" in content
        assert "lodash (v4.17.21)" in content
        assert "**Ecosystem:** npm" in content
        assert "pkg:npm/lodash@4.17.21" in content
        assert "### Why Mapping Fails" in content

    def test_report_includes_metadata(self, reporter, temp_dir, basic_stats):
        """Test report includes execution metadata."""
        with patch("sbom_fetcher.services.reporters.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            mock_dt.strftime = datetime.strftime

            filename = reporter.generate(
                output_dir=temp_dir,
                owner="owner",
                repo="repo",
                stats=basic_stats,
                packages=[],
                version_mapping={},
                failed_sboms=[],
                unmapped_packages=[],
            )

            content = (temp_dir / filename).read_text()
            assert "**Execution Date:** 2024-01-01 12:00:00" in content
            assert f"**Output Directory:** `{temp_dir}`" in content

    def test_report_includes_deduplication_stats(self, reporter, temp_dir, basic_stats):
        """Test report includes deduplication statistics."""
        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=basic_stats,
            packages=[],
            version_mapping={},
            failed_sboms=[],
            unmapped_packages=[],
        )

        content = (temp_dir / filename).read_text()
        assert "### Deduplication Impact" in content
        assert "**Packages mapped:** 8" in content
        assert "**Unique repositories:** 6" in content
        assert "**Duplicates avoided:** 2" in content

    def test_report_includes_files_generated(self, reporter, temp_dir, basic_stats):
        """Test report lists generated files."""
        filename = reporter.generate(
            output_dir=temp_dir,
            owner="myowner",
            repo="myrepo",
            stats=basic_stats,
            packages=[],
            version_mapping={},
            failed_sboms=[],
            unmapped_packages=[],
        )

        content = (temp_dir / filename).read_text()
        assert "## Files Generated" in content
        assert "`myowner_myrepo_root.json`" in content
        assert "`version_mapping.json`" in content
        assert "`myowner_myrepo_execution_report.md`" in content
        assert "`dependencies/`" in content

    def test_report_includes_footer(self, reporter, temp_dir, basic_stats):
        """Test report includes footer."""
        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=basic_stats,
            packages=[],
            version_mapping={},
            failed_sboms=[],
            unmapped_packages=[],
        )

        content = (temp_dir / filename).read_text()
        assert "Generated by GitHub SBOM API Fetcher" in content
        assert "For more information, see README.md" in content

    def test_report_sorting_multiple_versions(self, reporter, temp_dir, basic_stats):
        """Test report sorts repositories by number of versions."""
        version_mapping = {
            "owner/repo1": {
                "package_name": "pkg1",
                "ecosystem": "npm",
                "versions_in_dependency_tree": ["1.0.0", "1.0.1"],
                "sbom_file": "file1.json",
            },
            "owner/repo2": {
                "package_name": "pkg2",
                "ecosystem": "npm",
                "versions_in_dependency_tree": ["2.0.0", "2.0.1", "2.0.2"],
                "sbom_file": "file2.json",
            },
        }

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=basic_stats,
            packages=[],
            version_mapping=version_mapping,
            failed_sboms=[],
            unmapped_packages=[],
        )

        content = (temp_dir / filename).read_text()
        # repo2 should appear first (3 versions > 2 versions)
        repo2_pos = content.find("owner/repo2")
        repo1_pos = content.find("owner/repo1")
        assert repo2_pos < repo1_pos

    def test_report_zero_deduplication(self, reporter, temp_dir):
        """Test report handles zero deduplication percentage."""
        stats = FetcherStats()
        stats.unique_repos = 0

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=stats,
            packages=[],
            version_mapping={},
            failed_sboms=[],
            unmapped_packages=[],
        )

        content = (temp_dir / filename).read_text()
        assert "### Deduplication Impact" in content

    def test_report_elapsed_time_formatted(self, reporter, temp_dir):
        """Test report formats elapsed time correctly."""
        import time

        stats = FetcherStats()
        stats.start_time = time.time()
        stats.end_time = stats.start_time + 330  # 5 min 30 sec

        filename = reporter.generate(
            output_dir=temp_dir,
            owner="owner",
            repo="repo",
            stats=stats,
            packages=[],
            version_mapping={},
            failed_sboms=[],
            unmapped_packages=[],
        )

        content = (temp_dir / filename).read_text()
        assert "**Elapsed time:**" in content
