"""Additional reporter tests to increase coverage above 96%."""

import tempfile
from pathlib import Path

from sbom_fetcher.domain.models import FetcherStats
from sbom_fetcher.services.reporters import MarkdownReporter


class TestAdditionalReporterCoverage:
    """Additional tests for edge cases in reporter."""

    def test_component_count_with_mixed_package_info(self):
        """Test component count with some packages having info and some not."""
        reporter = MarkdownReporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            stats = FetcherStats()
            stats.packages_in_sbom = 3
            stats.github_repos_mapped = 3
            stats.unique_repos = 3
            stats.sboms_downloaded = 3

            version_mapping = {
                "owner1/repo1": {
                    "package_name": "pkg1",
                    "ecosystem": "npm",
                    "component_count": 10,
                },
                "owner2/repo2": {
                    # Missing package_name and ecosystem
                    "component_count": 5,
                },
                "owner3/repo3": {
                    "package_name": "",  # Empty package name
                    "ecosystem": "pypi",
                    "component_count": 3,
                },
            }
            dependency_component_counts = {
                "owner1/repo1": 10,
                "owner2/repo2": 5,
                "owner3/repo3": 3,
            }

            filename = reporter.generate(
                output_dir=temp_dir,
                owner="test",
                repo="test",
                stats=stats,
                packages=[],
                version_mapping=version_mapping,
                failed_sboms=[],
                unmapped_packages=[],
                root_component_count=20,
                dependency_component_counts=dependency_component_counts,
            )

            content = (temp_dir / filename).read_text()

            # Should handle all three cases
            assert "owner1/repo1" in content
            assert "owner2/repo2" in content
            assert "owner3/repo3" in content
            assert "38 components" in content  # Grand total: 20 + 10 + 5 + 3

    def test_component_count_with_zero_root_but_dependencies(self):
        """Test component count with zero root components but some dependencies."""
        reporter = MarkdownReporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            stats = FetcherStats()
            stats.packages_in_sbom = 2
            stats.sboms_downloaded = 2

            version_mapping = {
                "owner/repo1": {"package_name": "pkg1", "ecosystem": "npm"},
                "owner/repo2": {"package_name": "pkg2", "ecosystem": "npm"},
            }
            dependency_component_counts = {"owner/repo1": 10, "owner/repo2": 5}

            filename = reporter.generate(
                output_dir=temp_dir,
                owner="test",
                repo="test",
                stats=stats,
                packages=[],
                version_mapping=version_mapping,
                failed_sboms=[],
                unmapped_packages=[],
                root_component_count=0,  # Zero root
                dependency_component_counts=dependency_component_counts,
            )

            content = (temp_dir / filename).read_text()

            # Should still show component count section because dependencies exist
            assert "## Component Count Analysis" in content
            assert "**Components:** 0" in content
            assert "15 components" in content  # Total dependencies

    def test_component_count_empty_version_mapping(self):
        """Test component count when version_mapping is empty."""
        reporter = MarkdownReporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            stats = FetcherStats()
            stats.packages_in_sbom = 0

            filename = reporter.generate(
                output_dir=temp_dir,
                owner="test",
                repo="test",
                stats=stats,
                packages=[],
                version_mapping={},  # Empty
                failed_sboms=[],
                unmapped_packages=[],
                root_component_count=100,
                dependency_component_counts={},  # Empty
            )

            content = (temp_dir / filename).read_text()

            # Should show root component count
            assert "Root SBOM: `test/test`" in content
            assert "**Components:** 100" in content
            # Should not show grand total when no dependencies
            assert "Grand Total" not in content

    def test_reporter_with_large_component_counts(self):
        """Test reporter handles large component counts correctly."""
        reporter = MarkdownReporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            stats = FetcherStats()
            stats.packages_in_sbom = 5
            stats.sboms_downloaded = 5

            # Create large component counts
            version_mapping = {}
            dependency_component_counts = {}
            for i in range(5):
                repo_key = f"owner{i}/repo{i}"
                version_mapping[repo_key] = {
                    "package_name": f"pkg{i}",
                    "ecosystem": "npm",
                }
                dependency_component_counts[repo_key] = 1000 + i * 100

            filename = reporter.generate(
                output_dir=temp_dir,
                owner="test",
                repo="test",
                stats=stats,
                packages=[],
                version_mapping=version_mapping,
                failed_sboms=[],
                unmapped_packages=[],
                root_component_count=5000,
                dependency_component_counts=dependency_component_counts,
            )

            content = (temp_dir / filename).read_text()

            # Verify grand total calculation: 5000 + (1000 + 1100 + 1200 + 1300 + 1400) = 11000
            assert "**11000 components**" in content
            assert "**Components:** 5000" in content  # Root
            assert "**All dependency SBOM components:** 6000" in content  # All dependencies

    def test_component_count_single_dependency(self):
        """Test component count with only one dependency."""
        reporter = MarkdownReporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            stats = FetcherStats()
            stats.packages_in_sbom = 1
            stats.sboms_downloaded = 1

            version_mapping = {
                "single/repo": {"package_name": "single-pkg", "ecosystem": "pypi"}
            }
            dependency_component_counts = {"single/repo": 42}

            filename = reporter.generate(
                output_dir=temp_dir,
                owner="test",
                repo="test",
                stats=stats,
                packages=[],
                version_mapping=version_mapping,
                failed_sboms=[],
                unmapped_packages=[],
                root_component_count=10,
                dependency_component_counts=dependency_component_counts,
            )

            content = (temp_dir / filename).read_text()

            # Should show single dependency
            assert "single/repo" in content
            assert "42 components" in content
            assert "52 components" in content  # Grand total: 10 + 42
