"""Unit tests for domain models."""

from sbom_fetcher.domain.models import (
    ErrorType,
    FailureInfo,
    FetcherResult,
    FetcherStats,
    GitHubRepository,
    PackageDependency,
)


class TestPackageDependency:
    """Tests for PackageDependency model."""

    def test_create_package_dependency(self):
        """Test creating a package dependency."""
        pkg = PackageDependency(
            name="lodash", version="4.17.21", ecosystem="npm", purl="pkg:npm/lodash@4.17.21"
        )

        assert pkg.name == "lodash"
        assert pkg.version == "4.17.21"
        assert pkg.ecosystem == "npm"
        assert pkg.purl == "pkg:npm/lodash@4.17.21"
        assert pkg.github_repository is None
        assert pkg.error is None
        assert pkg.error_type is None
        assert pkg.sbom_downloaded is False

    def test_package_dependency_with_github_repo(self):
        """Test package dependency with GitHub repository."""
        repo = GitHubRepository(owner="lodash", repo="lodash")
        pkg = PackageDependency(
            name="lodash",
            version="4.17.21",
            ecosystem="npm",
            purl="pkg:npm/lodash@4.17.21",
            github_repository=repo,
        )

        assert pkg.github_repository == repo

    def test_package_dependency_with_error(self):
        """Test package dependency with error."""
        pkg = PackageDependency(
            name="test-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/test-pkg@1.0.0",
            error="Dependency graph not enabled",
            error_type=ErrorType.PERMANENT,
        )

        assert pkg.error == "Dependency graph not enabled"
        assert pkg.error_type == ErrorType.PERMANENT


class TestGitHubRepository:
    """Tests for GitHubRepository model."""

    def test_create_github_repository(self):
        """Test creating a GitHub repository."""
        repo = GitHubRepository(owner="lodash", repo="lodash")

        assert repo.owner == "lodash"
        assert repo.repo == "lodash"
        assert str(repo) == "lodash/lodash"

    def test_github_repository_equality(self):
        """Test GitHub repository equality."""
        repo1 = GitHubRepository(owner="lodash", repo="lodash")
        repo2 = GitHubRepository(owner="lodash", repo="lodash")
        repo3 = GitHubRepository(owner="different", repo="lodash")

        assert repo1 == repo2
        assert repo1 != repo3

    def test_github_repository_hash(self):
        """Test GitHub repository hashing (for use in sets/dicts)."""
        repo1 = GitHubRepository(owner="lodash", repo="lodash")
        repo2 = GitHubRepository(owner="lodash", repo="lodash")

        # Should be able to use in sets
        repo_set = {repo1, repo2}
        assert len(repo_set) == 1


class TestFetcherStats:
    """Tests for FetcherStats model."""

    def test_create_fetcher_stats(self):
        """Test creating fetcher stats."""
        stats = FetcherStats()

        assert stats.packages_in_sbom == 0
        assert stats.github_repos_mapped == 0
        assert stats.unique_repos == 0
        assert stats.sboms_downloaded == 0
        assert stats.sboms_failed == 0
        assert stats.sboms_failed_permanent == 0
        assert stats.sboms_failed_transient == 0

    def test_fetcher_stats_all_fields(self):
        """Test fetcher stats with all fields."""
        stats = FetcherStats(
            packages_in_sbom=50,
            github_repos_mapped=45,
            packages_without_github=5,
            unique_repos=40,
            duplicates_skipped=5,
            sboms_downloaded=38,
            sboms_failed_permanent=1,
            sboms_failed_transient=1,
        )

        assert stats.packages_in_sbom == 50
        assert stats.github_repos_mapped == 45
        assert stats.packages_without_github == 5
        assert stats.unique_repos == 40
        assert stats.duplicates_skipped == 5
        assert stats.sboms_downloaded == 38
        assert stats.sboms_failed == 2  # computed property
        assert stats.sboms_failed_permanent == 1
        assert stats.sboms_failed_transient == 1


class TestErrorType:
    """Tests for ErrorType enum."""

    def test_error_types(self):
        """Test error type enum values."""
        assert ErrorType.PERMANENT.value == "permanent"
        assert ErrorType.TRANSIENT.value == "transient"
        assert ErrorType.UNKNOWN.value == "unknown"

    def test_error_type_comparison(self):
        """Test error type comparisons."""
        assert ErrorType.PERMANENT == ErrorType.PERMANENT
        assert ErrorType.TRANSIENT == ErrorType.TRANSIENT
        assert ErrorType.PERMANENT != ErrorType.TRANSIENT


class TestFailureInfo:
    """Tests for FailureInfo model."""

    def test_create_failure_info(self):
        """Test creating failure info."""
        repo = GitHubRepository(owner="test", repo="repo")
        failure = FailureInfo(
            repository=repo,
            package_name="test-pkg",
            ecosystem="npm",
            versions=["1.0.0"],
            error="Dependency graph not enabled",
            error_type=ErrorType.PERMANENT,
        )

        assert failure.repository == repo
        assert failure.package_name == "test-pkg"
        assert failure.ecosystem == "npm"
        assert failure.versions == ["1.0.0"]
        assert failure.error == "Dependency graph not enabled"
        assert failure.error_type == ErrorType.PERMANENT

    def test_failure_info_to_dict(self):
        """Test converting failure info to dict."""
        repo = GitHubRepository(owner="test", repo="repo")
        failure = FailureInfo(
            repository=repo,
            package_name="test-pkg",
            ecosystem="npm",
            versions=["1.0.0", "1.0.1"],
            error="HTTP 500",
            error_type=ErrorType.TRANSIENT,
        )

        result = failure.to_dict()
        assert result["repo"] == "test/repo"
        assert result["package"] == "test-pkg"
        assert result["ecosystem"] == "npm"
        assert result["versions"] == ["1.0.0", "1.0.1"]
        assert result["error"] == "HTTP 500"
        assert result["error_type"] == "transient"


class TestFetcherResult:
    """Tests for FetcherResult model."""

    def test_create_fetcher_result(self):
        """Test creating fetcher result."""
        stats = FetcherStats()
        result = FetcherResult(stats=stats, packages=[], failed_downloads=[], version_mapping={})

        assert result.stats == stats
        assert result.packages == []
        assert result.failed_downloads == []
        assert result.version_mapping == {}
        assert result.unmapped_packages == []

    def test_fetcher_result_success(self):
        """Test success property."""
        stats = FetcherStats(sboms_failed_permanent=0, sboms_failed_transient=0)
        result = FetcherResult(stats=stats, packages=[], failed_downloads=[], version_mapping={})
        assert result.success is True

    def test_fetcher_result_failure(self):
        """Test success property with failures."""
        stats = FetcherStats(sboms_failed_permanent=1)
        result = FetcherResult(stats=stats, packages=[], failed_downloads=[], version_mapping={})
        assert result.success is False

    def test_github_repository_validation_empty_owner(self):
        """Test GitHubRepository validation fails for empty owner."""
        import pytest

        with pytest.raises(ValueError, match="Owner and repo must be non-empty"):
            GitHubRepository(owner="", repo="test")

    def test_package_dependency_validation_empty_name(self):
        """Test PackageDependency validation fails for empty name."""
        import pytest

        with pytest.raises(ValueError, match="Package name cannot be empty"):
            PackageDependency(name="", version="1.0.0", ecosystem="npm", purl="pkg:npm/test@1.0.0")

    def test_package_dependency_validation_empty_purl(self):
        """Test PackageDependency validation fails for empty purl."""
        import pytest

        with pytest.raises(ValueError, match="PURL cannot be empty"):
            PackageDependency(name="test", version="1.0.0", ecosystem="npm", purl="")

    def test_package_dependency_validation_empty_ecosystem(self):
        """Test PackageDependency validation fails for empty ecosystem."""
        import pytest

        with pytest.raises(ValueError, match="Ecosystem cannot be empty"):
            PackageDependency(name="test", version="1.0.0", ecosystem="", purl="pkg:npm/test@1.0.0")
