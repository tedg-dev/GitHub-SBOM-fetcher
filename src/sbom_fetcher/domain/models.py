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
class FetcherResult:
    """Result of SBOM fetching operation."""

    stats: FetcherStats
    packages: List[PackageDependency]
    failed_downloads: List[FailureInfo]
    version_mapping: Dict[str, Any]

    @property
    def success(self) -> bool:
        """Whether the operation completed without failures."""
        return self.stats.sboms_failed == 0
