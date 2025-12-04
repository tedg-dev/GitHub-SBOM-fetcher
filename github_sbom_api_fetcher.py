#!/usr/bin/env python3
"""
GitHub SBOM API-Based Dependency Fetcher

A robust, API-driven alternative to HTML scraping for collecting SBOMs.
Uses GitHub's SBOM API + package registry APIs to discover and download
all dependency SBOMs.

Advantages over HTML scraping:
- More complete (finds ALL dependencies in SBOM, typically 3-5% more)
- Stable (uses versioned APIs, not fragile HTML parsing)
- Works for private repos (doesn't need web UI access)
- Faster (direct JSON APIs, no HTML parsing)
- Maintainable (industry-standard SPDX format)

Author: GitHub SBOM Fetcher Team
License: MIT
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import requests

# GitHub API endpoints
GITHUB_API = "https://api.github.com"
SBOM_API = f"{GITHUB_API}/repos/{{owner}}/{{repo}}/dependency-graph/sbom"

# Package registry APIs
NPM_REGISTRY = "https://registry.npmjs.org"
PYPI_API = "https://pypi.org/pypi"

logger = logging.getLogger(__name__)


@dataclass
class PackageDependency:
    """Represents a package dependency from SBOM."""
    name: str
    version: str
    purl: str  # Package URL (e.g., pkg:npm/lodash@4.17.5)
    ecosystem: str  # npm, pypi, maven, etc.
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    sbom_downloaded: bool = False
    error: Optional[str] = None


@dataclass
class FetcherStats:
    """Track statistics for the fetching process."""
    packages_in_sbom: int = 0
    github_repos_mapped: int = 0
    unique_repos: int = 0
    sboms_downloaded: int = 0
    sboms_failed: int = 0
    duplicates_skipped: int = 0
    packages_without_github: int = 0
    start_time: float = field(default_factory=time.time)
    
    def elapsed_time(self) -> str:
        """Get elapsed time as formatted string."""
        elapsed = time.time() - self.start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        return f"{mins}m {secs}s" if mins > 0 else f"{secs}s"


def load_token(key_file: str = "keys.json") -> str:
    """Load GitHub token from keys file."""
    try:
        with open(key_file, "r") as f:
            data = json.load(f)
        
        # Try different key formats
        token = (
            data.get("github_token")
            or data.get("token")
            or (data.get("accounts", [{}])[0].get("token") if data.get("accounts") else None)
        )
        
        if not token:
            raise ValueError("No GitHub token found in keys file")
        
        return token
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Keys file '{key_file}' not found. "
            "Create it with your GitHub token."
        )
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in keys file '{key_file}'")


def build_session(token: str) -> requests.Session:
    """Build requests session with GitHub authentication."""
    s = requests.Session()
    s.headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-sbom-api-fetcher/1.0",
    })
    return s


def fetch_root_sbom(
    session: requests.Session,
    owner: str,
    repo: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch the root repository's SBOM via GitHub API.
    
    Returns:
        SBOM data as dict, or None if unavailable
    """
    url = SBOM_API.format(owner=owner, repo=repo)
    logger.info("Fetching root SBOM: %s/%s", owner, repo)
    
    try:
        resp = session.get(url, timeout=30)
        
        if resp.status_code == 200:
            sbom_data = resp.json()
            logger.info("✅ Root SBOM fetched successfully")
            return sbom_data
        elif resp.status_code == 404:
            logger.error("❌ SBOM not available: Dependency graph likely not enabled")
            logger.error("   Enable at: https://github.com/%s/%s/settings", owner, repo)
            return None
        elif resp.status_code == 403:
            logger.error("❌ Access forbidden (403): Check token permissions")
            return None
        else:
            logger.error("❌ Failed to fetch SBOM: HTTP %d", resp.status_code)
            return None
            
    except requests.RequestException as e:
        logger.error("❌ Request error: %s", e)
        return None


def parse_purl(purl: str) -> Tuple[str, str, str]:
    """
    Parse Package URL (purl) to extract ecosystem, name, and version.
    
    Example: pkg:npm/lodash@4.17.5 → ('npm', 'lodash', '4.17.5')
    
    Returns:
        Tuple of (ecosystem, name, version)
    """
    if not purl or not purl.startswith("pkg:"):
        return ("unknown", "", "")
    
    # Remove pkg: prefix
    purl = purl[4:]
    
    # Split ecosystem and rest
    parts = purl.split("/", 1)
    if len(parts) < 2:
        return ("unknown", "", "")
    
    ecosystem = parts[0]
    rest = parts[1]
    
    # Handle namespace (e.g., pkg:npm/@types/node@14.0.0)
    if rest.startswith("@"):
        # Scoped package
        scope_parts = rest.split("/", 1)
        if len(scope_parts) < 2:
            return (ecosystem, "", "")
        name_version = f"{scope_parts[0]}/{scope_parts[1]}"
    else:
        name_version = rest
    
    # Split name and version
    if "@" in name_version:
        # Split on last @ to handle scoped packages
        last_at = name_version.rfind("@")
        if name_version.startswith("@"):
            # Scoped package, need to find @ after the scope
            second_at = name_version.find("@", 1)
            if second_at > 0:
                name = name_version[:second_at]
                version = name_version[second_at + 1:]
            else:
                name = name_version
                version = ""
        else:
            name = name_version[:last_at]
            version = name_version[last_at + 1:]
    else:
        name = name_version
        version = ""
    
    return (ecosystem, name, version)


def extract_packages_from_sbom(sbom_data: Dict[str, Any]) -> List[PackageDependency]:
    """
    Extract package dependencies from SBOM data.
    
    Args:
        sbom_data: Full SBOM response from GitHub API
        
    Returns:
        List of PackageDependency objects
    """
    packages = []
    sbom = sbom_data.get("sbom", {})
    package_list = sbom.get("packages", [])
    
    logger.info("Parsing SBOM packages...")
    
    for pkg in package_list:
        name = pkg.get("name", "")
        version = pkg.get("versionInfo", "")
        
        # Skip the root document package
        if pkg.get("SPDXID") == "SPDXRef-DOCUMENT":
            continue
        
        # Extract purl from externalRefs
        purl = ""
        external_refs = pkg.get("externalRefs", [])
        for ref in external_refs:
            if ref.get("referenceType") == "purl":
                purl = ref.get("referenceLocator", "")
                break
        
        if not purl:
            logger.debug("No purl for package: %s", name)
            continue
        
        ecosystem, parsed_name, parsed_version = parse_purl(purl)
        
        # Use parsed values if package name/version are missing
        if not name:
            name = parsed_name
        if not version:
            version = parsed_version
        
        if name:
            packages.append(PackageDependency(
                name=name,
                version=version,
                purl=purl,
                ecosystem=ecosystem
            ))
    
    logger.info("Found %d packages in SBOM", len(packages))
    return packages


def map_npm_package_to_github(
    package_name: str,
    timeout: int = 10
) -> Optional[Tuple[str, str]]:
    """
    Map npm package to its GitHub repository using npm registry API.
    
    Returns:
        Tuple of (owner, repo) or None if not found
    """
    try:
        url = f"{NPM_REGISTRY}/{package_name}"
        resp = requests.get(url, timeout=timeout)
        
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        repo_info = data.get("repository", {})
        
        # Handle both dict and string formats
        if isinstance(repo_info, dict):
            repo_url = repo_info.get("url", "")
        else:
            repo_url = repo_info
        
        if not repo_url:
            return None
        
        # Extract GitHub owner/repo from URL
        # Formats: git+https://github.com/owner/repo.git
        #          https://github.com/owner/repo
        #          git://github.com/owner/repo.git
        repo_url = repo_url.lower()
        
        if "github.com" not in repo_url:
            return None
        
        # Clean up URL
        repo_url = (
            repo_url
            .replace("git+", "")
            .replace("git://", "https://")
            .replace(".git", "")
            .replace("ssh://git@", "https://")
        )
        
        # Parse URL
        parsed = urlparse(repo_url)
        path = parsed.path.strip("/")
        
        # Remove branch/tag references (e.g., #master)
        if "#" in path:
            path = path.split("#")[0]
        
        # Split into owner/repo
        parts = path.split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            return (owner, repo)
        
        return None
        
    except Exception as e:
        logger.debug("Error mapping npm package %s: %s", package_name, e)
        return None


def map_pypi_package_to_github(
    package_name: str,
    timeout: int = 10
) -> Optional[Tuple[str, str]]:
    """
    Map PyPI package to its GitHub repository using PyPI API.
    
    Returns:
        Tuple of (owner, repo) or None if not found
    """
    try:
        url = f"{PYPI_API}/{package_name}/json"
        resp = requests.get(url, timeout=timeout)
        
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        info = data.get("info", {})
        
        # Check project_urls for Source or Repository
        project_urls = info.get("project_urls") or {}
        github_url = (
            project_urls.get("Source")
            or project_urls.get("Repository")
            or project_urls.get("Homepage")
            or info.get("home_page")
            or ""
        )
        
        if not github_url or "github.com" not in github_url.lower():
            return None
        
        # Parse GitHub URL
        parsed = urlparse(github_url)
        path = parsed.path.strip("/")
        
        # Remove .git and branch refs
        if path.endswith(".git"):
            path = path[:-4]
        if "#" in path:
            path = path.split("#")[0]
        
        parts = path.split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            return (owner, repo)
        
        return None
        
    except Exception as e:
        logger.debug("Error mapping PyPI package %s: %s", package_name, e)
        return None


def map_package_to_github(pkg: PackageDependency) -> bool:
    """
    Map a package to its GitHub repository based on ecosystem.
    
    Updates pkg.github_owner and pkg.github_repo if found.
    
    Returns:
        True if mapping successful, False otherwise
    """
    if pkg.ecosystem == "npm":
        result = map_npm_package_to_github(pkg.name)
    elif pkg.ecosystem == "pypi":
        result = map_pypi_package_to_github(pkg.name)
    else:
        logger.debug("Unsupported ecosystem: %s for %s", pkg.ecosystem, pkg.name)
        return False
    
    if result:
        pkg.github_owner, pkg.github_repo = result
        logger.debug("Mapped %s → %s/%s", pkg.name, pkg.github_owner, pkg.github_repo)
        return True
    
    return False


def download_dependency_sbom(
    session: requests.Session,
    pkg: PackageDependency,
    output_dir: str,
    max_retries: int = 2
) -> bool:
    """
    Download SBOM for a dependency's GitHub repository.
    
    Returns:
        True if successful, False otherwise
    """
    if not pkg.github_owner or not pkg.github_repo:
        pkg.error = "No GitHub repository mapped"
        return False
    
    url = SBOM_API.format(owner=pkg.github_owner, repo=pkg.github_repo)
    
    for attempt in range(max_retries):
        try:
            resp = session.get(url, timeout=30)
            
            if resp.status_code == 200:
                # Save SBOM (use _current.json since GitHub API only
                # returns current state, not version-specific)
                filename = f"{pkg.github_owner}_{pkg.github_repo}_current.json"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, "w") as f:
                    json.dump(resp.json(), f, indent=2)
                
                pkg.sbom_downloaded = True
                return True
                
            elif resp.status_code == 404:
                pkg.error = "Dependency graph not enabled"
                return False
            elif resp.status_code == 403:
                pkg.error = "Access forbidden"
                return False
            elif resp.status_code == 429:
                # Rate limited
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    logger.debug("Rate limited, waiting %ds...", wait_time)
                    time.sleep(wait_time)
                    continue
                pkg.error = "Rate limited"
                return False
            else:
                pkg.error = f"HTTP {resp.status_code}"
                return False
                
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            pkg.error = str(e)
            return False
    
    return False


def save_root_sbom(sbom_data: Dict[str, Any], output_dir: str, owner: str, repo: str) -> None:
    """Save the root repository's SBOM."""
    filename = f"{owner}_{repo}_root.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, "w") as f:
        json.dump(sbom_data, f, indent=2)
    
    logger.info("Saved root SBOM: %s", filename)


def generate_rtf_report(
    output_dir: str,
    owner: str,
    repo: str,
    stats: 'FetcherStats',
    packages: List['PackageDependency'],
    version_mapping: Dict[str, Dict[str, Any]]
) -> str:
    """Generate an RTF report with execution details."""
    rtf_filename = f"{owner}_{repo}_execution_report.rtf"
    rtf_path = os.path.join(output_dir, rtf_filename)

    # Prepare data
    no_github = [p for p in packages if not p.github_owner]
    repos_with_multiple_versions = [
        (repo_key, data) for repo_key, data in version_mapping.items()
        if len(data.get('versions_in_dependency_tree', [])) > 1
    ]

    # RTF escape function
    def rtf_escape(text: str) -> str:
        """Escape special RTF characters."""
        return (text.replace('\\', '\\\\')
                .replace('{', '\\{')
                .replace('}', '\\}'))

    # Build RTF content
    rtf_content = r"{\rtf1\ansi\deff0\nouicompat"
    rtf_content += (r"{\fonttbl{\f0\fnil\fcharset0 Courier New;}"
                    r"{\f1\fnil\fcharset0 Arial;}}")
    rtf_content += (r"{\colortbl ;\red0\green0\blue255;"
                    r"\red0\green128\blue0;\red255\green0\blue0;}")
    rtf_content += "\n\n"

    # Header
    rtf_content += (r"\f1\fs32\b GitHub SBOM API Fetcher - "
                    r"Execution Report\b0\fs20\par" + "\n")
    rtf_content += r"\par" + "\n"

    # Metadata
    rtf_content += (r"\b Repository:\b0 " +
                    rtf_escape(f"{owner}/{repo}") + r"\par" + "\n")
    exec_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rtf_content += (r"\b Execution Date:\b0 " +
                    exec_date + r"\par" + "\n")
    rtf_content += (r"\b Output Directory:\b0 " +
                    rtf_escape(output_dir) + r"\par" + "\n")
    rtf_content += r"\par" + "\n"

    # Summary Section
    rtf_content += r"\fs28\b SUMMARY\b0\fs20\par" + "\n"
    rtf_content += "="*70 + r"\par" + "\n"
    rtf_content += r"\par" + "\n"

    rtf_content += (r"\b Packages in root SBOM:\b0 " +
                    str(stats.packages_in_sbom) + r"\par" + "\n")
    rtf_content += (r"\b Mapped to GitHub repos:\b0 " +
                    str(stats.github_repos_mapped) + r"\par" + "\n")
    rtf_content += (r"\b Unique repositories:\b0 " +
                    str(stats.unique_repos) + r"\par" + "\n")
    rtf_content += (r"\b Duplicate versions skipped:\b0 " +
                    str(stats.duplicates_skipped) + r"\par" + "\n")
    rtf_content += (r"\b Packages without GitHub repos:\b0 " +
                    str(stats.packages_without_github) + r"\par" + "\n")
    rtf_content += r"\par" + "\n"
    rtf_content += (r"\b SBOMs downloaded successfully:\b0 \cf2 " +
                    str(stats.sboms_downloaded) + r"\cf0\par" + "\n")
    rtf_content += (r"\b SBOMs failed:\b0 \cf3 " +
                    str(stats.sboms_failed) + r"\cf0\par" + "\n")
    rtf_content += (r"\b Elapsed time:\b0 " +
                    stats.elapsed_time() + r"\par" + "\n")
    rtf_content += r"\par" + "\n"

    # Important Note
    rtf_content += r"\fs24\b\i NOTE\i0\b0\fs20\par" + "\n"
    rtf_content += ("GitHub's SBOM API only provides SBOMs for the "
                    "current state of " + r"\par" + "\n")
    rtf_content += ("repositories (default branch), not for specific "
                    "versions. " + r"\par" + "\n")
    rtf_content += ("See version_mapping.json for details on version "
                    "deduplication." + r"\par" + "\n")
    rtf_content += r"\par" + "\n"
    
    # Packages Without GitHub Repositories
    if no_github:
        rtf_content += (r"\fs28\b PACKAGES WITHOUT GITHUB REPOSITORIES"
                        r"\b0\fs20\par" + "\n")
        rtf_content += "="*70 + r"\par" + "\n"
        rtf_content += r"\par" + "\n"

        for pkg in no_github[:50]:  # Include up to 50 in report
            pkg_info = f"{pkg.name} ({pkg.ecosystem}) @ {pkg.version}"
            rtf_content += (r"  \f0 " + rtf_escape(pkg_info) +
                            r"\f1\par" + "\n")

        if len(no_github) > 50:
            rtf_content += (r"  ... and " + str(len(no_github) - 50) +
                            " more" + r"\par" + "\n")
        rtf_content += r"\par" + "\n"
    
    # Repositories with Multiple Versions
    if repos_with_multiple_versions:
        rtf_content += (r"\fs28\b REPOSITORIES WITH MULTIPLE VERSIONS"
                        r"\b0\fs20\par" + "\n")
        rtf_content += "="*70 + r"\par" + "\n"
        rtf_content += r"\par" + "\n"
        total_text = (f"Total: {len(repos_with_multiple_versions)} "
                      "repositories used with multiple versions")
        rtf_content += total_text + r"\par" + "\n"
        rtf_content += r"\par" + "\n"

        # Sort by number of versions (most to least)
        repos_with_multiple_versions.sort(
            key=lambda x: len(x[1].get('versions_in_dependency_tree', [])),
            reverse=True)

        for repo_key, data in repos_with_multiple_versions[:30]:
            versions = data.get('versions_in_dependency_tree', [])
            rtf_content += (r"\b " + rtf_escape(repo_key) +
                            r"\b0\par" + "\n")
            rtf_content += (r"  Package: " +
                            rtf_escape(data.get('package_name', 'N/A')) +
                            r"\par" + "\n")
            rtf_content += (r"  Ecosystem: " +
                            rtf_escape(data.get('ecosystem', 'N/A')) +
                            r"\par" + "\n")
            rtf_content += (r"  Versions: " +
                            rtf_escape(", ".join(versions)) +
                            r"\par" + "\n")
            rtf_content += (r"  SBOM file: \f0 " +
                            rtf_escape(data.get('sbom_file', 'N/A')) +
                            r"\f1\par" + "\n")
            rtf_content += r"\par" + "\n"

        if len(repos_with_multiple_versions) > 30:
            remaining = len(repos_with_multiple_versions) - 30
            rtf_content += (r"... and " + str(remaining) +
                            " more repositories" + r"\par" + "\n")
        rtf_content += r"\par" + "\n"
    
    # Statistics Breakdown
    rtf_content += (r"\fs28\b STATISTICS BREAKDOWN\b0\fs20\par" + "\n")
    rtf_content += "="*70 + r"\par" + "\n"
    rtf_content += r"\par" + "\n"

    # Ecosystem distribution
    ecosystem_counts = {}
    for pkg in packages:
        eco = pkg.ecosystem
        ecosystem_counts[eco] = ecosystem_counts.get(eco, 0) + 1

    rtf_content += r"\b Package Ecosystems:\b0\par" + "\n"
    for ecosystem, count in sorted(ecosystem_counts.items(),
                                   key=lambda x: x[1],
                                   reverse=True):
        rtf_content += (f"  {rtf_escape(ecosystem)}: {count}" +
                        r"\par" + "\n")
    rtf_content += r"\par" + "\n"

    # Deduplication savings
    rtf_content += r"\b Deduplication Impact:\b0\par" + "\n"
    total_packages = stats.github_repos_mapped
    unique_repos = stats.unique_repos
    duplicates = stats.duplicates_skipped
    if unique_repos > 0:
        dedup_pct = ((duplicates / total_packages * 100)
                     if total_packages > 0 else 0)
        rtf_content += (f"  Packages mapped: {total_packages}" +
                        r"\par" + "\n")
        rtf_content += (f"  Unique repositories: {unique_repos}" +
                        r"\par" + "\n")
        rtf_content += (f"  Duplicates avoided: {duplicates} "
                        f"({dedup_pct:.1f}%)" + r"\par" + "\n")
        rtf_content += (f"  Storage savings: ~{dedup_pct:.0f}%" +
                        r"\par" + "\n")
    rtf_content += r"\par" + "\n"
    
    # Files Generated
    rtf_content += r"\fs28\b FILES GENERATED\b0\fs20\par" + "\n"
    rtf_content += "="*70 + r"\par" + "\n"
    rtf_content += r"\par" + "\n"
    root_file = f"{owner}_{repo}_root.json"
    rtf_content += (r"\f0 " + rtf_escape(root_file) +
                    r"\f1  - Root repository SBOM" + r"\par" + "\n")
    rtf_content += (r"\f0 version_mapping.json\f1  - "
                    "Version-to-SBOM mapping" + r"\par" + "\n")
    rtf_content += (r"\f0 " + rtf_escape(rtf_filename) +
                    r"\f1  - This execution report" + r"\par" + "\n")
    rtf_content += (r"\f0 dependencies/\f1  - Directory with " +
                    str(stats.sboms_downloaded) +
                    " dependency SBOMs" + r"\par" + "\n")
    rtf_content += r"\par" + "\n"

    # Footer
    rtf_content += r"\par" + "\n"
    rtf_content += "="*70 + r"\par" + "\n"
    rtf_content += (r"\fs18\i Generated by GitHub SBOM API Fetcher"
                    r"\i0\fs20\par" + "\n")
    rtf_content += (r"\i For more information, see README.md\i0\par" +
                    "\n")

    # Close RTF
    rtf_content += "}"

    # Write to file
    with open(rtf_path, "w", encoding="utf-8") as f:
        f.write(rtf_content)
    
    return rtf_filename


def main() -> int:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="API-based GitHub SBOM dependency fetcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch dependencies for a repository
  python github_sbom_api_fetcher.py --gh-user tedg-dev --gh-repo beatBot
  
  # With debug logging
  python github_sbom_api_fetcher.py --gh-user tedg-dev --gh-repo beatBot --debug
  
  # Custom output directory
  python github_sbom_api_fetcher.py --gh-user tedg-dev --gh-repo beatBot --output-dir ./my_sboms
        """
    )
    
    parser.add_argument("--gh-user", required=True, help="GitHub repository owner")
    parser.add_argument("--gh-repo", required=True, help="GitHub repository name")
    parser.add_argument("--key-file", default="keys.json", help="Path to keys.json file")
    parser.add_argument("--output-dir", default="sboms_api", help="Base output directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    stats = FetcherStats()
    
    try:
        # Load token and create session
        logger.info("Loading GitHub token...")
        token = load_token(args.key_file)
        session = build_session(token)
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        output_base = os.path.join(
            args.output_dir,
            f"sbom_api_export_{timestamp}",
            f"{args.gh_user}_{args.gh_repo}"
        )
        os.makedirs(output_base, exist_ok=True)
        
        deps_dir = os.path.join(output_base, "dependencies")
        os.makedirs(deps_dir, exist_ok=True)
        
        logger.info("Output directory: %s", output_base)
        
        # Step 1: Fetch root SBOM
        logger.info("\n" + "="*70)
        logger.info("STEP 1: Fetching Root SBOM")
        logger.info("="*70)
        
        sbom_data = fetch_root_sbom(session, args.gh_user, args.gh_repo)
        if not sbom_data:
            logger.error("Failed to fetch root SBOM. Exiting.")
            return 1
        
        # Save root SBOM
        save_root_sbom(sbom_data, output_base, args.gh_user, args.gh_repo)
        
        # Step 2: Parse packages from SBOM
        logger.info("\n" + "="*70)
        logger.info("STEP 2: Parsing Dependency Packages")
        logger.info("="*70)
        
        packages = extract_packages_from_sbom(sbom_data)
        stats.packages_in_sbom = len(packages)
        
        if not packages:
            logger.warning("No packages found in SBOM")
            return 0
        
        # Step 3: Map packages to GitHub repositories
        logger.info("\n" + "="*70)
        logger.info("STEP 3: Mapping Packages to GitHub Repositories")
        logger.info("="*70)
        
        for i, pkg in enumerate(packages, 1):
            if i % 20 == 0:
                logger.info("Mapping progress: %d/%d", i, len(packages))
            
            if map_package_to_github(pkg):
                stats.github_repos_mapped += 1
            else:
                stats.packages_without_github += 1
            
            # Rate limiting for registry APIs
            if i % 10 == 0:
                time.sleep(0.5)
        
        logger.info("Mapped %d packages to GitHub repos", stats.github_repos_mapped)
        logger.info("Packages without GitHub repos: %d", stats.packages_without_github)
        
        # Step 4: Download SBOMs for dependencies (with deduplication)
        logger.info("\n" + "="*70)
        logger.info("STEP 4: Downloading Dependency SBOMs (Deduplicated)")
        logger.info("="*70)
        
        mapped_packages = [p for p in packages if p.github_owner and p.github_repo]
        
        # Deduplicate: Track by repository, not version
        # GitHub's SBOM API only returns current state, not version-specific
        repo_to_packages = {}  # Maps "owner/repo" -> [list of packages]
        for pkg in mapped_packages:
            repo_key = f"{pkg.github_owner}/{pkg.github_repo}"
            if repo_key not in repo_to_packages:
                repo_to_packages[repo_key] = []
            repo_to_packages[repo_key].append(pkg)
        
        stats.unique_repos = len(repo_to_packages)
        logger.info("Total packages: %d", len(mapped_packages))
        logger.info("Unique repositories: %d", stats.unique_repos)
        logger.info("Duplicates to skip: %d", len(mapped_packages) - stats.unique_repos)
        logger.info("")
        
        # Download one SBOM per repository
        version_mapping = {}  # Track which versions map to each SBOM
        
        for i, (repo_key, pkgs) in enumerate(repo_to_packages.items(), 1):
            # Use first package for download (all versions map to same repo)
            pkg = pkgs[0]
            versions = [p.version for p in pkgs]
            
            logger.info(
                "[%d/%d] Fetching SBOM for %s (versions: %s)",
                i,
                len(repo_to_packages),
                repo_key,
                ", ".join(versions) if len(versions) <= 3 else f"{', '.join(versions[:3])}, +{len(versions)-3} more"
            )
            
            if download_dependency_sbom(session, pkg, deps_dir):
                stats.sboms_downloaded += 1
                # Track version mapping
                version_mapping[repo_key] = {
                    "sbom_file": f"{pkg.github_owner}_{pkg.github_repo}_current.json",
                    "package_name": pkg.name,
                    "ecosystem": pkg.ecosystem,
                    "versions_in_dependency_tree": sorted(set(versions)),
                    "note": "SBOM represents current repository state (default branch), not historical versions"
                }
            else:
                stats.sboms_failed += 1
                if pkg.error:
                    logger.debug("  Failed: %s", pkg.error)
            
            # Count skipped duplicates
            if len(pkgs) > 1:
                stats.duplicates_skipped += len(pkgs) - 1
            
            # Rate limiting
            if i % 10 == 0:
                time.sleep(1)
        
        # Save version mapping
        mapping_file = os.path.join(output_base, "version_mapping.json")
        with open(mapping_file, "w") as f:
            json.dump(version_mapping, f, indent=2)
        logger.info("\nSaved version mapping: version_mapping.json")
        
        # Generate RTF execution report
        rtf_filename = generate_rtf_report(
            output_base,
            args.gh_user,
            args.gh_repo,
            stats,
            packages,
            version_mapping
        )
        logger.info("Generated execution report: %s", rtf_filename)
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("SUMMARY")
        logger.info("="*70)
        logger.info("")
        logger.info("Packages in root SBOM: %d", stats.packages_in_sbom)
        logger.info("Mapped to GitHub repos: %d", stats.github_repos_mapped)
        logger.info("Unique repositories: %d", stats.unique_repos)
        logger.info("Duplicate versions skipped: %d", stats.duplicates_skipped)
        logger.info("Packages without GitHub repos: %d", stats.packages_without_github)
        logger.info("")
        logger.info("SBOMs downloaded successfully: %d", stats.sboms_downloaded)
        logger.info("SBOMs failed: %d", stats.sboms_failed)
        logger.info("Elapsed time: %s", stats.elapsed_time())
        logger.info("Output directory: %s", os.path.abspath(output_base))
        logger.info("")
        logger.info("NOTE: GitHub's SBOM API only provides SBOMs for the current state")
        logger.info("      of repositories (default branch), not for specific versions.")
        logger.info("      See version_mapping.json for details on version deduplication.")
        logger.info("")
        
        # Detailed report
        if stats.packages_without_github > 0:
            logger.info("="*70)
            logger.info("Packages Without GitHub Repositories")
            logger.info("="*70)
            logger.info("")
            
            no_github = [p for p in packages if not p.github_owner]
            for pkg in no_github[:20]:  # Show first 20
                logger.info("  %s (%s) @ %s", pkg.name, pkg.ecosystem, pkg.version)
            
            if len(no_github) > 20:
                logger.info("  ... and %d more", len(no_github) - 20)
            logger.info("")
        
        logger.info("✅ Done!")
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n\n❌ Interrupted by user")
        return 130
    except Exception as e:
        logger.error("❌ Fatal error: %s", e, exc_info=args.debug)
        return 1


if __name__ == "__main__":
    sys.exit(main())
