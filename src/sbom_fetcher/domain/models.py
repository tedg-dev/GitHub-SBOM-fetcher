"""Core domain models for SBOM fetcher."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorType(str, Enum):
    """Classification of error types."""

    PERMANENT = "permanent"
    TRANSIENT = "transient"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class GitHubRepository:
    """Immutable GitHub repository identifier."""

    owner: str
    repo: str

    def __str__(self) -> str:
        """Return string representation as owner/repo."""
        return f"{self.owner}/{self.repo}"

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.owner or not self.repo:
            raise ValueError("Owner and repo must be non-empty strings")


@dataclass
class PackageDependency:
    """Represents a package dependency from SBOM."""

    name: str
    version: str
    purl: str
    ecosystem: str
    github_repository: Optional[GitHubRepository] = None
    sbom_downloaded: bool = False
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.name:
            raise ValueError("Package name cannot be empty")
        if not self.purl:
            raise ValueError("PURL cannot be empty")
        if not self.ecosystem:
            raise ValueError("Ecosystem cannot be empty")


@dataclass
class FetcherStats:
    """Track statistics for the fetching process."""

    packages_in_sbom: int = 0
    github_repos_mapped: int = 0
    unique_repos: int = 0
    sboms_downloaded: int = 0
    sboms_failed_permanent: int = 0
    sboms_failed_transient: int = 0
    duplicates_skipped: int = 0
    packages_without_github: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def sboms_failed(self) -> int:
        """Total failures (permanent + transient)."""
        return self.sboms_failed_permanent + self.sboms_failed_transient

    def elapsed_time(self) -> str:
        """Get elapsed time as formatted string."""
        elapsed = time.time() - self.start_time
        mins, secs = divmod(int(elapsed), 60)
        return f"{mins}m {secs}s" if mins > 0 else f"{secs}s"


@dataclass
class FailureInfo:
    """Information about a failed SBOM download."""

    repository: GitHubRepository
    package_name: str
    ecosystem: str
    versions: List[str]
    error: str
    error_type: ErrorType

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "repo": str(self.repository),
            "package": self.package_name,
            "ecosystem": self.ecosystem,
            "versions": self.versions,
            "error": self.error,
            "error_type": self.error_type.value,
        }


@dataclass
class VersionLocation:
    """Tracks where a specific package version appears across SBOMs."""

    package_name: str
    version: str
    ecosystem: str
    sbom_files: List[str] = field(default_factory=list)

    def add_location(self, sbom_file: str) -> None:
        """Add an SBOM file where this version was found."""
        if sbom_file not in self.sbom_files:
            self.sbom_files.append(sbom_file)


@dataclass
class PackageVersionMap:
    """Maps a package to all its versions and their locations."""

    package_name: str
    ecosystem: str
    versions: Dict[str, VersionLocation] = field(default_factory=dict)

    def add_version(self, version: str, sbom_file: str) -> None:
        """Add or update a version location."""
        if version not in self.versions:
            self.versions[version] = VersionLocation(
                package_name=self.package_name,
                version=version,
                ecosystem=self.ecosystem,
            )
        self.versions[version].add_location(sbom_file)

    @property
    def has_multiple_versions(self) -> bool:
        """Check if this package has multiple versions."""
        return len(self.versions) > 1

    @property
    def version_count(self) -> int:
        """Get the number of distinct versions."""
        return len(self.versions)


@dataclass
class SBOMDuplicateEntry:
    """Tracks when a single SBOM has multiple instances of the same package."""

    sbom_file: str
    package_name: str
    ecosystem: str
    versions: List[str] = field(default_factory=list)


@dataclass
class FetcherResult:
    """Result of SBOM fetching operation."""

    stats: FetcherStats
    packages: List[PackageDependency]
    failed_downloads: List[FailureInfo]
    version_mapping: Dict[str, Any]
    unmapped_packages: List[PackageDependency] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether the operation completed without failures."""
        return self.stats.sboms_failed == 0
