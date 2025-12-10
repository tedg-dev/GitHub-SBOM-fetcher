"""Report generation (Builder pattern)."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..domain.models import ErrorType, FailureInfo, FetcherStats, PackageDependency


class MarkdownReporter:
    """Generates Markdown execution reports."""

    def generate(
        self,
        output_dir: Path,
        owner: str,
        repo: str,
        stats: FetcherStats,
        packages: List[PackageDependency],
        version_mapping: Dict[str, Any],
        failed_sboms: List[FailureInfo],
        unmapped_packages: List[PackageDependency],
        root_component_count: int = 0,
        dependency_component_counts: Dict[str, int] = None,
    ) -> str:
        """
        Generate a Markdown report with execution details.

        Preserves exact format and content from original generate_markdown_report.

        Args:
            output_dir: Output directory path
            owner: Repository owner
            repo: Repository name
            stats: Fetcher statistics
            packages: List of package dependencies
            version_mapping: Version mapping dictionary
            failed_sboms: List of failed downloads
            unmapped_packages: Packages without GitHub repository mappings

        Returns:
            Filename of generated report
        """
        md_filename = f"{owner}_{repo}_execution_report.md"
        md_path = output_dir / md_filename

        # Prepare data
        repos_with_multiple_versions = [
            (repo_key, data)
            for repo_key, data in version_mapping.items()
            if len(data.get("versions_in_dependency_tree", [])) > 1
        ]

        # Build Markdown content
        md_content = []

        # Header
        md_content.append("# GitHub SBOM API Fetcher - Execution Report\n")

        # Metadata
        exec_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        md_content.append(f"**Repository:** `{owner}/{repo}`  ")
        md_content.append(f"**Execution Date:** {exec_date}  ")
        md_content.append(f"**Output Directory:** `{output_dir}`\n")

        # Summary Section
        md_content.append("## Summary\n")
        md_content.append(f"- **Root SBOM dependency repositories:** {stats.packages_in_sbom}")
        md_content.append(f"- **Mapped to GitHub repos:** {stats.github_repos_mapped}")
        md_content.append(f"- **Unique repositories:** {stats.unique_repos}")
        md_content.append(f"- **Duplicate versions skipped:** {stats.duplicates_skipped}")
        md_content.append(f"- **Packages without GitHub repos:** {stats.packages_without_github}\n")
        md_content.append(f"- **SBOMs downloaded successfully:** ✅ **{stats.sboms_downloaded}**")
        md_content.append(f"- **SBOMs failed (permanent):** 🔴 **{stats.sboms_failed_permanent}**")
        md_content.append(f"- **SBOMs failed (transient):** ⚠️ **{stats.sboms_failed_transient}**")
        md_content.append(f"- **SBOMs failed (total):** ❌ **{stats.sboms_failed}**")
        md_content.append(f"- **Elapsed time:** {stats.elapsed_time()}\n")

        # Important Note
        md_content.append("### ⚠️ Important Note\n")
        md_content.append(
            "> GitHub's SBOM API only provides SBOMs for the current state "
            "of repositories (default branch), not for specific versions."
        )
        md_content.append("> See `version_mapping.json` for details on version deduplication.\n")

        # Component Count Analysis
        if dependency_component_counts is None:
            dependency_component_counts = {}

        if root_component_count > 0 or dependency_component_counts:
            md_content.append("## Component Count Analysis\n")
            md_content.append(
                "This section shows the total number of components (packages/dependencies) "
                "found in the root SBOM and each dependency SBOM.\n"
            )

            # Root SBOM components
            md_content.append(f"### Root SBOM: `{owner}/{repo}`\n")
            md_content.append(f"- **Components:** {root_component_count}\n")

            # Dependency SBOM components
            if dependency_component_counts:
                md_content.append("### Dependency SBOMs\n")
                md_content.append(
                    "Each dependency repository's SBOM contains the following number of components:\n"
                )

                # Sort by component count (descending)
                sorted_deps = sorted(
                    dependency_component_counts.items(), key=lambda x: x[1], reverse=True
                )

                for repo_key, count in sorted_deps:
                    # Get package info from version_mapping if available
                    pkg_info = version_mapping.get(repo_key, {})
                    pkg_name = pkg_info.get("package_name", "")
                    ecosystem = pkg_info.get("ecosystem", "")

                    if pkg_name and ecosystem:
                        md_content.append(
                            f"- **{repo_key}** ({ecosystem}: `{pkg_name}`): {count} components"
                        )
                    else:
                        md_content.append(f"- **{repo_key}**: {count} components")

                # Grand total
                total_dependency_components = sum(dependency_component_counts.values())
                grand_total = root_component_count + total_dependency_components

                md_content.append("\n### Grand Total\n")
                md_content.append(f"- **Root SBOM components:** {root_component_count}")
                md_content.append(
                    f"- **1st level dependency SBOM components:** {total_dependency_components}"
                )
                md_content.append(
                    f"- **🎯 Grand Total (Root + 1st level Dependencies):** "
                    f"**{grand_total} components**\n"
                )

        # Failed SBOMs - separate permanent and transient
        if failed_sboms:
            permanent_failures = [f for f in failed_sboms if f.error_type == ErrorType.PERMANENT]
            transient_failures = [f for f in failed_sboms if f.error_type == ErrorType.TRANSIENT]

            md_content.append("## Failed SBOM Downloads\n")
            md_content.append(
                f"**Total failures:** {len(failed_sboms)} "
                f"({len(permanent_failures)} permanent, "
                f"{len(transient_failures)} transient)\n"
            )

            if permanent_failures:
                md_content.append("### 🔴 Permanent Failures\n")
                md_content.append(
                    "*These will consistently fail until the underlying issue "
                    "is fixed (e.g., dependency graph not enabled).*\n"
                )
                for failure in permanent_failures:
                    md_content.append(f"#### {failure.repository}\n")
                    md_content.append(f"- **Package:** {failure.package_name}")
                    md_content.append(f"- **Ecosystem:** {failure.ecosystem}")
                    md_content.append(f"- **Versions:** {', '.join(failure.versions)}")
                    md_content.append(f"- **Error:** `{failure.error}`\n")

            if transient_failures:
                md_content.append("### ⚠️ Transient Failures\n")
                md_content.append(
                    "*These may succeed on retry (e.g., timeouts, rate limits, "
                    "network issues).*\n"
                )
                for failure in transient_failures:
                    md_content.append(f"#### {failure.repository}\n")
                    md_content.append(f"- **Package:** {failure.package_name}")
                    md_content.append(f"- **Ecosystem:** {failure.ecosystem}")
                    md_content.append(f"- **Versions:** {', '.join(failure.versions)}")
                    md_content.append(f"- **Error:** `{failure.error}`\n")

        # Old simple section removed - replaced by detailed diagnostic section below

        # Repositories with Multiple Versions
        if repos_with_multiple_versions:
            md_content.append("## Repositories with Multiple Versions\n")
            md_content.append(
                f"**Total:** {len(repos_with_multiple_versions)} "
                "repositories used with multiple versions\n"
            )

            # Sort by number of versions (most to least)
            repos_with_multiple_versions.sort(
                key=lambda x: len(x[1].get("versions_in_dependency_tree", [])),
                reverse=True,
            )

            for repo_key, data in repos_with_multiple_versions[:10]:
                versions = data.get("versions_in_dependency_tree", [])
                md_content.append(f"### {repo_key}\n")
                md_content.append(f"- **Package:** {data.get('package_name', 'N/A')}")
                md_content.append(f"- **Ecosystem:** {data.get('ecosystem', 'N/A')}")
                md_content.append(f"- **Versions:** {', '.join(versions)}")
                md_content.append(f"- **SBOM file:** `{data.get('sbom_file', 'N/A')}`\n")

            if len(repos_with_multiple_versions) > 10:
                remaining = len(repos_with_multiple_versions) - 10
                md_content.append(
                    f"*... and {remaining} more repositories. "
                    "See `version_mapping.json` for complete details.*\n"
                )

        # Unmapped Packages Section
        if unmapped_packages:
            md_content.append("## Packages That Could Not Be Mapped to GitHub\n")
            md_content.append(
                f"**Total:** {len(unmapped_packages)} packages could not be mapped "
                "to GitHub repositories.\n"
            )
            md_content.append("### How Package Mapping Works\n")
            md_content.append(
                "This tool maps packages to GitHub repositories using the following process:\n"
            )
            md_content.append(
                "1. **Query Package Registry**: For npm packages, query "
                "`https://registry.npmjs.org/{package-name}`"
            )
            md_content.append(
                '2. **Extract Repository Field**: Look for the `"repository"` field in the package metadata'
            )
            md_content.append(
                "3. **Validate GitHub URL**: If found, verify it's a GitHub URL and extract owner/repo"
            )
            md_content.append("4. **Fetch SBOM**: Download the SBOM from GitHub's API\n")
            md_content.append("### Why Mapping Fails\n")
            md_content.append(
                "Packages fail to map when the package registry metadata **does not include** "
                'a repository field or includes `"repository": null`. This commonly occurs with:\n'
            )
            md_content.append(
                "- **Old/unmaintained packages**: Published before repository fields were standard"
            )
            md_content.append(
                "- **Platform-specific binaries**: Wrap native binaries, no source code to link"
            )
            md_content.append(
                "- **Publisher oversight**: Package maintainer didn't include repository metadata"
            )
            md_content.append(
                "- **Private/internal packages**: Repository intentionally not disclosed\n"
            )
            md_content.append(
                "**Important**: Some packages listed below may have GitHub repositories, "
                "but the package registry metadata does not link to them. "
                "Without this metadata, the tool cannot discover the repository location.\n"
            )
            md_content.append("### Unmapped Packages Detail\n")

            for pkg in unmapped_packages:
                md_content.append(f"#### {pkg.name} (v{pkg.version})\n")
                md_content.append(f"- **Ecosystem:** {pkg.ecosystem}")
                md_content.append(f"- **PURL:** `{pkg.purl}`")
                md_content.append(
                    f"- **Package Registry Query:** `https://registry.npmjs.org/{pkg.name}`"
                )
                md_content.append(
                    '- **Registry Response:** Package metadata contains `"repository": null` '
                    "or no repository field"
                )
                md_content.append(
                    "- **Result:** ❌ Cannot determine GitHub repository location from package metadata"
                )
                md_content.append(
                    "- **GitHub SBOM:** ❌ Not available (repository location unknown from registry)\n"
                )

            md_content.append("### Important Note\n")
            md_content.append(
                "The absence of repository metadata in the package registry **does not necessarily mean** "
                "the package has no GitHub repository. It means the package publisher did not include "
                "this information in the package metadata. To fix this:\n"
            )
            md_content.append(
                "1. Contact the package maintainer to add repository field to `package.json`"
            )
            md_content.append(
                "2. Use alternative SBOM tools like `syft` or `grype` that analyze package files directly"
            )
            md_content.append(
                "3. If you know the repository URL, fetch the SBOM manually via GitHub API\n"
            )

        # Statistics Breakdown
        md_content.append("## Statistics Breakdown\n")

        # Deduplication savings
        md_content.append("### Deduplication Impact\n")
        total_packages = stats.github_repos_mapped
        unique_repos = stats.unique_repos
        duplicates = stats.duplicates_skipped
        if unique_repos > 0:
            dedup_pct = (duplicates / total_packages * 100) if total_packages > 0 else 0
            md_content.append(f"- **Packages mapped:** {total_packages}")
            md_content.append(f"- **Unique repositories:** {unique_repos}")
            md_content.append(f"- **Duplicates avoided:** {duplicates} ({dedup_pct:.1f}%)")
            md_content.append(f"- **Storage savings:** ~{dedup_pct:.0f}%")
        md_content.append("")

        # Files Generated
        md_content.append("## Files Generated\n")
        root_file = f"{owner}_{repo}_root.json"
        md_content.append(f"- `{root_file}` - Root repository SBOM")
        md_content.append("- `version_mapping.json` - Version-to-SBOM mapping")
        md_content.append(f"- `{md_filename}` - This execution report")
        md_content.append(
            f"- `dependencies/` - Directory with {stats.sboms_downloaded} " "dependency SBOMs\n"
        )

        # Footer
        md_content.append("---\n")
        md_content.append("*Generated by GitHub SBOM API Fetcher*  ")
        md_content.append("*For more information, see README.md*")

        # Write to file
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))

        return md_filename
