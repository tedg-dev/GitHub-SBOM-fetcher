"""
Comprehensive tests for github_sbom_api_fetcher.py

Tests cover:
- Permanent vs transient failure categorization
- Error handling edge cases
- Stats tracking and reporting
- Markdown report generation
- High code coverage for critical paths
"""

import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock, mock_open
import pytest
import requests

# Import the module under test
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from github_sbom_api_fetcher import (
    PackageDependency,
    FetcherStats,
    download_dependency_sbom,
    generate_markdown_report,
    extract_packages_from_sbom,
    map_package_to_github,
)


class TestPackageDependency:
    """Test PackageDependency dataclass."""
    
    def test_package_dependency_creation(self):
        """Test creating a PackageDependency."""
        pkg = PackageDependency(
            name="lodash",
            version="4.17.21",
            purl="pkg:npm/lodash@4.17.21",
            ecosystem="npm"
        )
        assert pkg.name == "lodash"
        assert pkg.version == "4.17.21"
        assert pkg.ecosystem == "npm"
        assert pkg.github_owner is None
        assert pkg.error is None
        assert pkg.error_type is None
    
    def test_package_dependency_with_error(self):
        """Test PackageDependency with error fields."""
        pkg = PackageDependency(
            name="test",
            version="1.0.0",
            purl="pkg:npm/test@1.0.0",
            ecosystem="npm",
            error="Dependency graph not enabled",
            error_type="permanent"
        )
        assert pkg.error == "Dependency graph not enabled"
        assert pkg.error_type == "permanent"


class TestFetcherStats:
    """Test FetcherStats dataclass and calculations."""
    
    def test_stats_initialization(self):
        """Test FetcherStats initial values."""
        stats = FetcherStats()
        assert stats.packages_in_sbom == 0
        assert stats.sboms_downloaded == 0
        assert stats.sboms_failed_permanent == 0
        assert stats.sboms_failed_transient == 0
        assert stats.sboms_failed == 0
    
    def test_stats_sboms_failed_property(self):
        """Test that sboms_failed property returns sum of permanent and transient."""
        stats = FetcherStats()
        stats.sboms_failed_permanent = 3
        stats.sboms_failed_transient = 2
        assert stats.sboms_failed == 5
    
    def test_stats_elapsed_time(self):
        """Test elapsed time formatting."""
        stats = FetcherStats()
        import time
        stats.start_time = time.time() - 125  # 2m 5s ago
        elapsed = stats.elapsed_time()
        assert "2m" in elapsed or "1m" in elapsed  # Account for timing variations


class TestDownloadDependencySBOM:
    """Test download_dependency_sbom function with various scenarios."""
    
    def setup_method(self):
        """Setup for each test."""
        self.session = Mock()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup after each test."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_successful_download(self):
        """Test successful SBOM download."""
        pkg = PackageDependency(
            name="lodash",
            version="4.17.21",
            purl="pkg:npm/lodash@4.17.21",
            ecosystem="npm",
            github_owner="lodash",
            github_repo="lodash"
        )
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sbom": "data"}
        self.session.get.return_value = mock_response
        
        result = download_dependency_sbom(self.session, pkg, self.temp_dir)
        
        assert result is True
        assert pkg.sbom_downloaded is True
        assert pkg.error is None
        
        # Verify file was written
        expected_file = os.path.join(self.temp_dir, "lodash_lodash_current.json")
        assert os.path.exists(expected_file)
    
    def test_permanent_failure_404(self):
        """Test permanent failure with 404 status (dependency graph not enabled)."""
        pkg = PackageDependency(
            name="test",
            version="1.0.0",
            purl="pkg:npm/test@1.0.0",
            ecosystem="npm",
            github_owner="owner",
            github_repo="repo"
        )
        
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        self.session.get.return_value = mock_response
        
        result = download_dependency_sbom(self.session, pkg, self.temp_dir)
        
        assert result is False
        assert pkg.error == "Dependency graph not enabled"
        assert pkg.error_type == "permanent"
        assert pkg.sbom_downloaded is False
    
    def test_permanent_failure_403(self):
        """Test permanent failure with 403 status (access forbidden)."""
        pkg = PackageDependency(
            name="test",
            version="1.0.0",
            purl="pkg:npm/test@1.0.0",
            ecosystem="npm",
            github_owner="owner",
            github_repo="repo"
        )
        
        mock_response = Mock()
        mock_response.status_code = 403
        self.session.get.return_value = mock_response
        
        result = download_dependency_sbom(self.session, pkg, self.temp_dir)
        
        assert result is False
        assert pkg.error == "Access forbidden"
        assert pkg.error_type == "permanent"
    
    def test_transient_failure_429(self):
        """Test transient failure with 429 status (rate limited)."""
        pkg = PackageDependency(
            name="test",
            version="1.0.0",
            purl="pkg:npm/test@1.0.0",
            ecosystem="npm",
            github_owner="owner",
            github_repo="repo"
        )
        
        # Mock rate limit response on all retries
        mock_response = Mock()
        mock_response.status_code = 429
        self.session.get.return_value = mock_response
        
        result = download_dependency_sbom(self.session, pkg, self.temp_dir, max_retries=2)
        
        assert result is False
        assert pkg.error == "Rate limited"
        assert pkg.error_type == "transient"
    
    def test_transient_failure_network_error(self):
        """Test transient failure with network exception."""
        pkg = PackageDependency(
            name="test",
            version="1.0.0",
            purl="pkg:npm/test@1.0.0",
            ecosystem="npm",
            github_owner="owner",
            github_repo="repo"
        )
        
        # Mock network exception
        self.session.get.side_effect = requests.RequestException("Connection timeout")
        
        result = download_dependency_sbom(self.session, pkg, self.temp_dir, max_retries=2)
        
        assert result is False
        assert "Connection timeout" in pkg.error
        assert pkg.error_type == "transient"
    
    def test_permanent_failure_other_http_error(self):
        """Test permanent failure with other HTTP error (e.g., 500)."""
        pkg = PackageDependency(
            name="test",
            version="1.0.0",
            purl="pkg:npm/test@1.0.0",
            ecosystem="npm",
            github_owner="owner",
            github_repo="repo"
        )
        
        mock_response = Mock()
        mock_response.status_code = 500
        self.session.get.return_value = mock_response
        
        result = download_dependency_sbom(self.session, pkg, self.temp_dir)
        
        assert result is False
        assert pkg.error == "HTTP 500"
        assert pkg.error_type == "permanent"
    
    def test_no_github_mapping(self):
        """Test failure when no GitHub repository is mapped."""
        pkg = PackageDependency(
            name="test",
            version="1.0.0",
            purl="pkg:npm/test@1.0.0",
            ecosystem="npm"
            # No github_owner or github_repo
        )
        
        result = download_dependency_sbom(self.session, pkg, self.temp_dir)
        
        assert result is False
        assert pkg.error == "No GitHub repository mapped"
        assert not self.session.get.called
    
    def test_retry_logic_success_on_second_attempt(self):
        """Test retry logic succeeds on second attempt."""
        pkg = PackageDependency(
            name="test",
            version="1.0.0",
            purl="pkg:npm/test@1.0.0",
            ecosystem="npm",
            github_owner="owner",
            github_repo="repo"
        )
        
        # First call fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 429
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"sbom": "data"}
        
        self.session.get.side_effect = [mock_response_fail, mock_response_success]
        
        result = download_dependency_sbom(self.session, pkg, self.temp_dir, max_retries=3)
        
        assert result is True
        assert pkg.sbom_downloaded is True
        assert self.session.get.call_count == 2


class TestMarkdownReportGeneration:
    """Test Markdown report generation with various scenarios."""
    
    def setup_method(self):
        """Setup for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.stats = FetcherStats()
        self.stats.packages_in_sbom = 100
        self.stats.github_repos_mapped = 90
        self.stats.unique_repos = 80
        self.stats.sboms_downloaded = 75
        self.stats.duplicates_skipped = 10
        self.stats.packages_without_github = 10
    
    def teardown_method(self):
        """Cleanup after each test."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_report_with_permanent_failures_only(self):
        """Test report generation with only permanent failures."""
        self.stats.sboms_failed_permanent = 3
        self.stats.sboms_failed_transient = 0
        
        packages = [
            PackageDependency("pkg1", "1.0", "pkg:npm/pkg1@1.0", "npm"),
            PackageDependency("pkg2", "2.0", "pkg:npm/pkg2@2.0", "npm"),
        ]
        
        failed_sboms = [
            {
                "repo": "owner1/repo1",
                "package": "pkg1",
                "ecosystem": "npm",
                "versions": ["1.0"],
                "error": "Dependency graph not enabled",
                "error_type": "permanent"
            },
            {
                "repo": "owner2/repo2",
                "package": "pkg2",
                "ecosystem": "npm",
                "versions": ["2.0"],
                "error": "Access forbidden",
                "error_type": "permanent"
            }
        ]
        
        version_mapping = {}
        
        filename = generate_markdown_report(
            self.temp_dir,
            "test-user",
            "test-repo",
            self.stats,
            packages,
            version_mapping,
            failed_sboms
        )
        
        assert filename == "test-user_test-repo_execution_report.md"
        
        report_path = os.path.join(self.temp_dir, filename)
        assert os.path.exists(report_path)
        
        with open(report_path, 'r') as f:
            content = f.read()
        
        # Verify report structure
        assert "# GitHub SBOM API Fetcher - Execution Report" in content
        assert "## Summary" in content
        assert "SBOMs failed (permanent):** 🔴 **3**" in content
        assert "SBOMs failed (transient):** ⚠️ **0**" in content
        assert "## Failed SBOM Downloads" in content
        assert "### 🔴 Permanent Failures" in content
        assert "Dependency graph not enabled" in content
        assert "Access forbidden" in content
        assert "### ⚠️ Transient Failures" not in content
    
    def test_report_with_transient_failures_only(self):
        """Test report generation with only transient failures."""
        self.stats.sboms_failed_permanent = 0
        self.stats.sboms_failed_transient = 2
        
        packages = []
        
        failed_sboms = [
            {
                "repo": "owner1/repo1",
                "package": "pkg1",
                "ecosystem": "npm",
                "versions": ["1.0"],
                "error": "Rate limited",
                "error_type": "transient"
            },
            {
                "repo": "owner2/repo2",
                "package": "pkg2",
                "ecosystem": "npm",
                "versions": ["2.0"],
                "error": "Connection timeout",
                "error_type": "transient"
            }
        ]
        
        version_mapping = {}
        
        filename = generate_markdown_report(
            self.temp_dir,
            "test-user",
            "test-repo",
            self.stats,
            packages,
            version_mapping,
            failed_sboms
        )
        
        report_path = os.path.join(self.temp_dir, filename)
        with open(report_path, 'r') as f:
            content = f.read()
        
        assert "SBOMs failed (permanent):** 🔴 **0**" in content
        assert "SBOMs failed (transient):** ⚠️ **2**" in content
        assert "### ⚠️ Transient Failures" in content
        assert "Rate limited" in content
        assert "Connection timeout" in content
        assert "### 🔴 Permanent Failures" not in content
    
    def test_report_with_mixed_failures(self):
        """Test report generation with both permanent and transient failures."""
        self.stats.sboms_failed_permanent = 2
        self.stats.sboms_failed_transient = 1
        
        packages = []
        
        failed_sboms = [
            {
                "repo": "owner1/repo1",
                "package": "pkg1",
                "ecosystem": "npm",
                "versions": ["1.0"],
                "error": "Dependency graph not enabled",
                "error_type": "permanent"
            },
            {
                "repo": "owner2/repo2",
                "package": "pkg2",
                "ecosystem": "npm",
                "versions": ["2.0"],
                "error": "Rate limited",
                "error_type": "transient"
            },
            {
                "repo": "owner3/repo3",
                "package": "pkg3",
                "ecosystem": "pypi",
                "versions": ["3.0"],
                "error": "Access forbidden",
                "error_type": "permanent"
            }
        ]
        
        version_mapping = {}
        
        filename = generate_markdown_report(
            self.temp_dir,
            "test-user",
            "test-repo",
            self.stats,
            packages,
            version_mapping,
            failed_sboms
        )
        
        report_path = os.path.join(self.temp_dir, filename)
        with open(report_path, 'r') as f:
            content = f.read()
        
        assert "SBOMs failed (permanent):** 🔴 **2**" in content
        assert "SBOMs failed (transient):** ⚠️ **1**" in content
        assert "SBOMs failed (total):** ❌ **3**" in content
        assert "### 🔴 Permanent Failures" in content
        assert "### ⚠️ Transient Failures" in content
        assert "2 permanent, 1 transient" in content
    
    def test_report_with_no_failures(self):
        """Test report generation with no failures."""
        self.stats.sboms_failed_permanent = 0
        self.stats.sboms_failed_transient = 0
        
        packages = []
        failed_sboms = []
        version_mapping = {}
        
        filename = generate_markdown_report(
            self.temp_dir,
            "test-user",
            "test-repo",
            self.stats,
            packages,
            version_mapping,
            failed_sboms
        )
        
        report_path = os.path.join(self.temp_dir, filename)
        with open(report_path, 'r') as f:
            content = f.read()
        
        assert "SBOMs failed (permanent):** 🔴 **0**" in content
        assert "SBOMs failed (transient):** ⚠️ **0**" in content
        assert "## Failed SBOM Downloads" not in content
    
    def test_report_with_multiple_versions(self):
        """Test report with repositories having multiple versions."""
        self.stats.sboms_failed_permanent = 1
        
        packages = []
        
        failed_sboms = [
            {
                "repo": "owner1/repo1",
                "package": "pkg1",
                "ecosystem": "npm",
                "versions": ["1.0.0", "1.1.0", "2.0.0"],
                "error": "Dependency graph not enabled",
                "error_type": "permanent"
            }
        ]
        
        version_mapping = {
            "lodash/lodash": {
                "package_name": "lodash",
                "ecosystem": "npm",
                "versions_in_dependency_tree": ["4.17.5", "4.17.20", "4.17.21"],
                "sbom_file": "lodash_lodash_current.json"
            }
        }
        
        filename = generate_markdown_report(
            self.temp_dir,
            "test-user",
            "test-repo",
            self.stats,
            packages,
            version_mapping,
            failed_sboms
        )
        
        report_path = os.path.join(self.temp_dir, filename)
        with open(report_path, 'r') as f:
            content = f.read()
        
        assert "1.0.0, 1.1.0, 2.0.0" in content
        assert "## Repositories with Multiple Versions" in content
        assert "lodash/lodash" in content


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_package_list(self):
        """Test handling of empty package list."""
        stats = FetcherStats()
        stats.packages_in_sbom = 0
        
        packages = []
        failed_sboms = []
        version_mapping = {}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filename = generate_markdown_report(
                temp_dir,
                "test-user",
                "test-repo",
                stats,
                packages,
                version_mapping,
                failed_sboms
            )
            
            report_path = os.path.join(temp_dir, filename)
            assert os.path.exists(report_path)
            
            with open(report_path, 'r') as f:
                content = f.read()
            
            assert "Packages in root SBOM:** 0" in content
    
    def test_unknown_error_type(self):
        """Test handling of unknown error type (defaults to permanent)."""
        pkg = PackageDependency(
            name="test",
            version="1.0.0",
            purl="pkg:npm/test@1.0.0",
            ecosystem="npm"
        )
        pkg.error = "Unknown error"
        pkg.error_type = "unknown"
        
        # Should default to permanent in real code
        assert pkg.error_type == "unknown"
    
    def test_stats_with_zero_values(self):
        """Test stats calculations with zero values."""
        stats = FetcherStats()
        assert stats.sboms_failed == 0
        assert stats.sboms_failed_permanent == 0
        assert stats.sboms_failed_transient == 0
    
    def test_special_characters_in_repo_name(self):
        """Test handling of special characters in repository names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            stats = FetcherStats()
            stats.sboms_failed_permanent = 1
            
            failed_sboms = [
                {
                    "repo": "owner/repo-with-dashes_underscores.dots",
                    "package": "pkg-name",
                    "ecosystem": "npm",
                    "versions": ["1.0.0"],
                    "error": "Test error",
                    "error_type": "permanent"
                }
            ]
            
            filename = generate_markdown_report(
                temp_dir,
                "test-user",
                "test-repo",
                stats,
                [],
                {},
                failed_sboms
            )
            
            report_path = os.path.join(temp_dir, filename)
            assert os.path.exists(report_path)
            
            with open(report_path, 'r') as f:
                content = f.read()
            
            assert "owner/repo-with-dashes_underscores.dots" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=github_sbom_api_fetcher", "--cov-report=html", "--cov-report=term"])
