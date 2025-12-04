"""Main SBOM fetching service orchestrator."""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests

from ..domain.models import ErrorType, FailureInfo, FetcherResult, FetcherStats, PackageDependency
from ..infrastructure.config import Config
from ..infrastructure.filesystem import SBOMRepository
from .github_client import GitHubClient
from .mapper_factory import MapperFactory
from .parsers import SBOMParser
from .reporters import MarkdownReporter

logger = logging.getLogger(__name__)


class SBOMFetcherService:
    """
    Main service orchestrating SBOM fetching workflow.

    Preserves exact behavior from original main() function.
    """

    def __init__(
        self,
        github_client: GitHubClient,
        mapper_factory: MapperFactory,
        repository: SBOMRepository,
        reporter: MarkdownReporter,
        config: Config,
    ):
        """
        Initialize SBOM fetcher service.

        Args:
            github_client: GitHub API client
            mapper_factory: Factory for package mappers
            repository: SBOM storage repository
            reporter: Report generator
            config: Application configuration
        """
        self._github_client = github_client
        self._mapper_factory = mapper_factory
        self._repository = repository
        self._reporter = reporter
        self._config = config
        self._parser = SBOMParser()

    def fetch_all_sboms(self, owner: str, repo: str, session: requests.Session) -> FetcherResult:
        """
        Main workflow: fetch root SBOM and all dependency SBOMs.

        Preserves exact behavior from original main() function.

        Args:
            owner: GitHub repository owner
            repo: GitHub repository name
            session: Authenticated requests session

        Returns:
            FetcherResult with stats and collected data
        """
        stats = FetcherStats()

        # Create output directory with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        output_base = Path(self._config.output_dir) / f"sbom_export_{timestamp}" / f"{owner}_{repo}"
        output_base.mkdir(parents=True, exist_ok=True)

        deps_dir = output_base / "dependencies"
        deps_dir.mkdir(exist_ok=True)

        logger.info("Output directory: %s", output_base)

        # Step 1: Fetch root SBOM
        logger.info("\n" + "=" * 70)
        logger.info("STEP 1: Fetching Root SBOM")
        logger.info("=" * 70)

        sbom_data = self._github_client.fetch_root_sbom(owner, repo)
        if not sbom_data:
            logger.error("Failed to fetch root SBOM. Exiting.")
            # Return empty result
            return FetcherResult(stats=stats, packages=[], failed_downloads=[], version_mapping={})

        # Save root SBOM
        save_root_sbom(sbom_data, str(output_base), owner, repo)

        # Step 2: Parse packages from SBOM
        logger.info("\n" + "=" * 70)
        logger.info("STEP 2: Parsing Dependency Packages")
        logger.info("=" * 70)

        packages = self._parser.extract_packages(sbom_data, owner, repo)
        stats.packages_in_sbom = len(packages)

        if not packages:
            logger.warning("No packages found in SBOM")
            return FetcherResult(stats=stats, packages=[], failed_downloads=[], version_mapping={})

        # Step 3: Map packages to GitHub repositories
        logger.info("\n" + "=" * 70)
        logger.info("STEP 3: Mapping Packages to GitHub Repositories")
        logger.info("=" * 70)

        for i, pkg in enumerate(packages, 1):
            if i % 20 == 0:
                logger.info("Mapping progress: %d/%d", i, len(packages))

            if self._mapper_factory.map_package_to_github(pkg):
                stats.github_repos_mapped += 1
            else:
                stats.packages_without_github += 1

            # Rate limiting for registry APIs
            if i % 10 == 0:
                time.sleep(0.5)

        logger.info("Mapped %d packages to GitHub repos", stats.github_repos_mapped)
        logger.info("Packages without GitHub repos: %d", stats.packages_without_github)

        # Step 4: Download SBOMs for dependencies (with deduplication)
        logger.info("\n" + "=" * 70)
        logger.info("STEP 4: Downloading Dependency SBOMs (Deduplicated)")
        logger.info("=" * 70)

        mapped_packages = [p for p in packages if p.github_repository]

        # Deduplicate: Track by repository, not version
        repo_to_packages: Dict[str, List[PackageDependency]] = {}
        for pkg in mapped_packages:
            repo_key = str(pkg.github_repository)
            if repo_key not in repo_to_packages:
                repo_to_packages[repo_key] = []
            repo_to_packages[repo_key].append(pkg)

        stats.unique_repos = len(repo_to_packages)
        logger.info("Total packages: %d", len(mapped_packages))
        logger.info("Unique repositories: %d", stats.unique_repos)
        logger.info("Duplicates to skip: %d", len(mapped_packages) - stats.unique_repos)
        logger.info("")

        # Download one SBOM per repository
        version_mapping: Dict[str, Any] = {}
        failed_sboms: List[FailureInfo] = []

        for i, (repo_key, pkgs) in enumerate(repo_to_packages.items(), 1):
            pkg = pkgs[0]  # Use first package for download
            versions = [p.version for p in pkgs]

            logger.info(
                "[%d/%d] Fetching SBOM for %s (versions: %s)",
                i,
                len(repo_to_packages),
                repo_key,
                (
                    ", ".join(versions)
                    if len(versions) <= 3
                    else f"{', '.join(versions[:3])}, +{len(versions)-3} more"
                ),
            )

            if self._github_client.download_dependency_sbom(session, pkg, str(deps_dir)):
                stats.sboms_downloaded += 1
                # Track version mapping
                version_mapping[repo_key] = {
                    "sbom_file": f"{pkg.github_repository.owner}_{pkg.github_repository.repo}_current.json",
                    "package_name": pkg.name,
                    "ecosystem": pkg.ecosystem,
                    "versions_in_dependency_tree": sorted(set(versions)),
                    "note": "SBOM represents current repository state (default branch), not historical versions",
                }
            else:
                error_msg = pkg.error or "Unknown error"
                error_type = pkg.error_type or ErrorType.UNKNOWN

                # Track by failure type
                if error_type == ErrorType.PERMANENT:
                    stats.sboms_failed_permanent += 1
                elif error_type == ErrorType.TRANSIENT:
                    stats.sboms_failed_transient += 1
                else:
                    stats.sboms_failed_permanent += 1  # Default to permanent

                failed_sboms.append(
                    FailureInfo(
                        repository=pkg.github_repository,
                        package_name=pkg.name,
                        ecosystem=pkg.ecosystem,
                        versions=sorted(set(versions)),
                        error=error_msg,
                        error_type=error_type,
                    )
                )
                logger.warning("  Failed (%s): %s", error_type.value, error_msg)

            # Count skipped duplicates
            if len(pkgs) > 1:
                stats.duplicates_skipped += len(pkgs) - 1

            # Rate limiting
            if i % 10 == 0:
                time.sleep(1)

        # Save version mapping
        mapping_file = output_base / "version_mapping.json"
        with open(mapping_file, "w") as f:
            json.dump(version_mapping, f, indent=2)
        logger.info("\nSaved version mapping: version_mapping.json")

        # Generate Markdown execution report
        md_filename = self._reporter.generate(
            output_base, owner, repo, stats, packages, version_mapping, failed_sboms
        )
        logger.info("Generated execution report: %s", md_filename)

        # Print summary
        self._print_summary(stats, str(output_base), failed_sboms)

        return FetcherResult(
            stats=stats,
            packages=packages,
            failed_downloads=failed_sboms,
            version_mapping=version_mapping,
        )

    def _print_summary(
        self, stats: FetcherStats, output_base: str, failed_sboms: List[FailureInfo]
    ) -> None:
        """Print summary to console (preserves exact format from original)."""
        logger.info("\n" + "=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Packages in root SBOM: %d", stats.packages_in_sbom)
        logger.info("Mapped to GitHub repos: %d", stats.github_repos_mapped)
        logger.info("Unique repositories: %d", stats.unique_repos)
        logger.info("Duplicate versions skipped: %d", stats.duplicates_skipped)
        logger.info("Packages without GitHub repos: %d", stats.packages_without_github)
        logger.info("")
        logger.info("SBOMs downloaded successfully: %d", stats.sboms_downloaded)
        logger.info("SBOMs failed (permanent): %d", stats.sboms_failed_permanent)
        logger.info("SBOMs failed (transient): %d", stats.sboms_failed_transient)
        logger.info("SBOMs failed (total): %d", stats.sboms_failed)
        logger.info("Elapsed time: %s", stats.elapsed_time())
        logger.info("Output directory: %s", os.path.abspath(output_base))
        logger.info("")
        logger.info("NOTE: GitHub's SBOM API only provides SBOMs for the current state")
        logger.info("      of repositories (default branch), not for specific versions.")
        logger.info("      See version_mapping.json for details on version deduplication.")
        logger.info("")

        # Failed SBOMs report
        if failed_sboms:
            logger.info("=" * 70)
            logger.info("Failed SBOM Downloads")
            logger.info("=" * 70)
            logger.info("")

            permanent_failures = [f for f in failed_sboms if f.error_type == ErrorType.PERMANENT]
            transient_failures = [f for f in failed_sboms if f.error_type == ErrorType.TRANSIENT]

            if permanent_failures:
                logger.info("🔴 PERMANENT FAILURES (%d):", len(permanent_failures))
                logger.info("   (These will consistently fail until fixed)")
                logger.info("")
                for failure in permanent_failures:
                    logger.info("  ❌ %s", failure.repository)
                    logger.info("     Package: %s (%s)", failure.package_name, failure.ecosystem)
                    logger.info("     Versions: %s", ", ".join(failure.versions))
                    logger.info("     Error: %s", failure.error)
                    logger.info("")

            if transient_failures:
                logger.info("⚠️  TRANSIENT FAILURES (%d):", len(transient_failures))
                logger.info("   (These may succeed on retry)")
                logger.info("")
                for failure in transient_failures:
                    logger.info("  ⚠️  %s", failure.repository)
                    logger.info("     Package: %s (%s)", failure.package_name, failure.ecosystem)
                    logger.info("     Versions: %s", ", ".join(failure.versions))
                    logger.info("     Error: %s", failure.error)
                    logger.info("")


def save_root_sbom(sbom_data: Dict[str, Any], output_dir: str, owner: str, repo: str) -> None:
    """Save the root repository's SBOM (preserves original v1 naming)."""
    filename = f"{owner}_{repo}_root.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        json.dump(sbom_data, f, indent=2)

    logger.info("Saved root SBOM: %s", filename)
