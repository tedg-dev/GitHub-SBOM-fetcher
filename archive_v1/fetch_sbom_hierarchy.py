#!/usr/bin/env python3
"""Fetch SBOMs from GitHub repositories and their dependencies."""

import argparse
import datetime
import json
import logging
import os
import sys
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

import requests

# Configure logging
logger = logging.getLogger(__name__)

# GitHub API endpoints
GITHUB_API = "https://api.github.com"
SBOM_API = f"{GITHUB_API}/repos/{{owner}}/{{repo}}/dependency-graph/sbom"
DEPS_API = f"{GITHUB_API}/repos/{{owner}}/{{repo}}/dependencies"

# SPDX SBOM format constants
SPDX_VERSION = "SPDX-2.3"
DATA_LICENSE = "CC0-1.0"


@dataclass
class GitHubDependency:
    """Represents a GitHub repository dependency."""
    owner: str
    repo: str
    version: str = ""
    source: str = ""  # Where this dependency was found


class GitHubAPIError(Exception):
    """Raised when GitHub API returns an error."""
    pass


class GitHubSBOMFetcher:
    """Fetches SBOMs from GitHub repositories."""

    def __init__(self, github_token: str):
        """Initialize the GitHub SBOM fetcher."""
        self.github_token = github_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SBOM-Fetcher/1.0"
        })
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0
        self.repo_sha = ""

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make a request to the GitHub API with rate limiting."""
        # Check rate limit
        if self.rate_limit_remaining < 10:
            wait_time = max(0, self.rate_limit_reset - time.time() + 1)
            if wait_time > 0:
                logger.warning("Rate limit low, waiting %d seconds", wait_time)
                time.sleep(wait_time)

        try:
            response = self.session.request(method, url, **kwargs)
            # Update rate limit info
            self.rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))

            if response.status_code == 403:
                if "rate limit" in response.text.lower():
                    raise GitHubAPIError("Rate limit exceeded")
                else:
                    raise GitHubAPIError(f"Access forbidden: {response.text}")
            elif response.status_code == 404:
                raise GitHubAPIError(f"Not found: {url}")
            elif response.status_code >= 400:
                raise GitHubAPIError(f"API error {response.status_code}: {response.text}")

            return response

        except requests.RequestException as e:
            raise GitHubAPIError(f"Request failed: {e}")

    def get_sbom(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Fetch the SBOM for a repository."""
        url = SBOM_API.format(owner=owner, repo=repo)
        logger.debug("Fetching SBOM from %s", url)

        try:
            response = self._make_request("GET", url)
            sbom_data = response.json()
            logger.debug("Successfully fetched SBOM for %s/%s", owner, repo)
            return sbom_data
        except GitHubAPIError as e:
            # Check if this is a 404 for dependency-graph/sbom (repo doesn't have SBOM feature)
            if "Not found:" in str(e) and "/dependency-graph/sbom" in str(e):
                logger.debug("Repository %s/%s does not have dependency graph SBOM feature enabled", owner, repo)
            else:
                logger.error("Failed to fetch SBOM for %s/%s: %s", owner, repo, e)
            return None

    def get_dependencies(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Fetch the dependency graph for a repository."""
        url = DEPS_API.format(owner=owner, repo=repo)
        logger.debug("Fetching dependencies from %s", url)

        try:
            response = self._make_request("GET", url)
            deps_data = response.json()
            logger.debug("Successfully fetched dependencies for %s/%s", owner, repo)
            return deps_data
        except GitHubAPIError as e:
            logger.error("Failed to fetch dependencies for %s/%s: %s", owner, repo, e)
            return None

    def _get_github_repo_from_npm(
        self, package_name: str, version: str
    ) -> Tuple[str, str] | None:
        """Get GitHub repository URL from npm package.
        
        Tries the specific version first, then falls back to latest version
        if the specific version's repository doesn't exist.
        """
        # Handle special case: node-uuid was renamed to uuid and moved
        if package_name == "node-uuid":
            logger.debug("Mapping node-uuid to uuidjs/uuid (renamed package)")
            if self._repository_exists("uuidjs", "uuid"):
                return ("uuidjs", "uuid")
        
        # First try with the specific version
        result = self._get_github_repo_from_npm_version(package_name, version)
        if result:
            # Verify the repository actually exists
            owner, repo = result
            if self._repository_exists(owner, repo):
                return result
            else:
                logger.debug("Repository %s/%s doesn't exist, trying alternatives", owner, repo)
                # Try generic fallbacks
                fallbacks = self._get_fallback_repos(owner, repo, package_name)
                for fallback_owner, fallback_repo in fallbacks:
                    if self._repository_exists(fallback_owner, fallback_repo):
                        logger.debug("Found fallback repository: %s/%s", fallback_owner, fallback_repo)
                        return (fallback_owner, fallback_repo)
        
        # Try with latest version
        result = self._get_github_repo_from_npm_version(package_name, None)
        if result:
            owner, repo = result
            if self._repository_exists(owner, repo):
                return result
            else:
                logger.debug("Latest version repository %s/%s also doesn't exist", owner, repo)
                # Try generic fallbacks for latest version
                fallbacks = self._get_fallback_repos(owner, repo, package_name)
                for fallback_owner, fallback_repo in fallbacks:
                    if self._repository_exists(fallback_owner, fallback_repo):
                        logger.debug("Found fallback repository for latest: %s/%s", fallback_owner, fallback_repo)
                        return (fallback_owner, fallback_repo)
        
        return None
    
    def _get_fallback_repos(self, owner: str, repo: str, package_name: str) -> List[Tuple[str, str]]:
        """Generate fallback repository combinations to try.
        
        This handles cases where the npm package repository name differs
        from the actual GitHub repository name.
        """
        fallbacks = []
        
        # Try common patterns:
        # 1. If owner matches package name, try owner/package-name
        if owner == package_name:
            fallbacks.append((owner, f"{package_name}"))
        
        # 2. Try owner/node-package-name (common for Node.js packages)
        if not package_name.startswith("node-"):
            fallbacks.append((owner, f"node-{package_name}"))
        
        # 3. Try owner/js-package-name
        if not package_name.endswith("-js") and not package_name.endswith(".js"):
            fallbacks.append((owner, f"{package_name}-js"))
        
        # 4. Try owner/package-name-js
        if not package_name.endswith("-js"):
            fallbacks.append((owner, f"{package_name}-js"))
        
        # 5. Try removing common prefixes/suffixes from repo name
        if repo.startswith("node-"):
            fallbacks.append((owner, repo[5:]))  # Remove 'node-' prefix
        if repo.endswith(".js"):
            fallbacks.append((owner, repo[:-3]))  # Remove '.js' suffix
        if repo.endswith("-js"):
            fallbacks.append((owner, repo[:-3]))  # Remove '-js' suffix
        
        # 6. Try adding common prefixes/suffixes to repo name
        if not repo.startswith("node-"):
            fallbacks.append((owner, f"node-{repo}"))
        if not repo.endswith(".js"):
            fallbacks.append((owner, f"{repo}.js"))
        
        # 7. Try using package name as repo with various prefixes
        fallbacks.append((owner, f"node-{package_name}"))
        fallbacks.append((owner, f"{package_name}.js"))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_fallbacks = []
        for fallback in fallbacks:
            if fallback not in seen and fallback != (owner, repo):
                seen.add(fallback)
                unique_fallbacks.append(fallback)
        
        return unique_fallbacks
    
    def _get_github_repo_from_npm_version(
        self, package_name: str, version: str
    ) -> Tuple[str, str] | None:
        """Get GitHub repository URL from npm package for a specific version."""
        try:
            # Handle scoped packages
            encoded = package_name
            if package_name.startswith('@'):
                encoded = package_name.replace('/', '%2F')
            
            # Try to get package info with version first
            if version:
                url = f'https://registry.npmjs.org/{encoded}/{version}'
            else:
                url = f'https://registry.npmjs.org/{encoded}/latest'
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Check multiple fields for repository URL
                repo_url = None
                
                # First check repository field
                repo = data.get('repository')
                if repo:
                    if isinstance(repo, dict):
                        repo_url = repo.get('url')
                    elif isinstance(repo, str):
                        repo_url = repo
                
                # If not found, check url field
                if not repo_url:
                    repo_url = data.get('url')
                
                # If still not found, check homepage
                if not repo_url:
                    repo_url = data.get('homepage')
                
                if not repo_url:
                    return None
                
                logger.debug("Raw repository URL for %s@%s: %s", package_name, version, repo_url)
                        
                # Clean up the URL
                if repo_url.startswith('git+'):
                    repo_url = repo_url[4:]
                if repo_url.startswith('git://'):
                    repo_url = repo_url.replace('git://', 'https://')
                if repo_url.startswith('http://'):
                    repo_url = repo_url.replace('http://', 'https://')
                if repo_url.endswith('.git'):
                    repo_url = repo_url[:-4]
                
                logger.debug("Cleaned repository URL: %s", repo_url)
                
                # Extract owner and repo from GitHub URL
                if 'github.com/' in repo_url:
                    parts = repo_url.split('github.com/')[-1].split('/')
                    if len(parts) >= 2:
                        owner = parts[0]
                        repo = parts[1]
                        # Remove .git suffix if present
                        if repo.endswith('.git'):
                            repo = repo[:-4]
                        logger.debug("Extracted owner='%s', repo='%s'", owner, repo)
                        return owner, repo
                    else:
                        logger.debug("Invalid GitHub URL format: %s", repo_url)
                else:
                    logger.debug("No github.com/ found in URL: %s", repo_url)
            return None
        except Exception as e:
            logger.debug("Error getting repo for %s@%s: %s", package_name, version, e)
            return None
    
    def _repository_exists(self, owner: str, repo: str) -> bool:
        """Check if a GitHub repository exists."""
        try:
            url = f"{GITHUB_API}/repos/{owner}/{repo}"
            response = self._make_request("GET", url)
            return response.status_code == 200
        except GitHubAPIError as e:
            if "Not found:" in str(e):
                return False
            # For other errors, assume the repo might exist
            logger.debug("Error checking if %s/%s exists: %s", owner, repo, e)
            return True

    def extract_dependencies(
        self, sbom_data: Dict[str, Any], owner: str, repo: str
    ) -> List[GitHubDependency]:
        """Extract dependencies from SBOM data."""
        dependencies = []

        if not isinstance(sbom_data, dict) or "sbom" not in sbom_data:
            logger.warning("Invalid SBOM data format")
            return []

        sbom = sbom_data["sbom"]
        logger.debug("SBOM keys: %s", list(sbom.keys()))

        # Get repository information from the SBOM
        self.repo_sha = ""
        if "creationInfo" in sbom and "created" in sbom["creationInfo"]:
            # Extract commit SHA from the document namespace if available
            doc_ns = sbom.get("documentNamespace", "")
            if "/" in doc_ns:
                self.repo_sha = doc_ns.split("/")[-1].split("-")[-1]

        # Handle SPDX format SBOM - extract ALL dependencies, not just npm
        if "packages" in sbom:
            logger.debug("Found %d packages in SBOM", len(sbom["packages"]))
            npm_packages = []
            github_deps = []  # Track direct GitHub dependencies
            
            # First, extract all packages and categorize them
            for pkg in sbom.get("packages", []):
                if not isinstance(pkg, dict):
                    continue

                # Skip the main package
                pkg_name = pkg.get("name", "")
                if pkg_name == f"com.github.{owner}/{repo}":
                    continue

                # Extract version
                version = pkg.get("versionInfo", "")

                # Check for npm packages in external references
                for ref in pkg.get("externalRefs", []):
                    if not isinstance(ref, dict):
                        continue

                    # Check for package URLs in purl format
                    if ref.get("referenceType") == "purl":
                        purl = ref.get("referenceLocator", "")

                        # Handle npm packages
                        if "pkg:npm/" in purl:
                            # Extract package name and version from purl
                            # Format: pkg:npm/package-name@version
                            # Need to URL decode the package name and version
                            
                            # Remove pkg:npm/ prefix
                            package_part = purl.split("pkg:npm/")[-1]
                            
                            # URL decode the entire package part
                            decoded_part = urllib.parse.unquote(package_part)
                            
                            # Split on @ to separate name and version
                            parts = decoded_part.split("@")
                            if len(parts) >= 1:
                                npm_name = parts[0]
                                npm_version = parts[1] if len(parts) > 1 else version
                                npm_packages.append((npm_name, npm_version))

            logger.info("Found %d npm packages", len(npm_packages))
            
            # Debug: Log first few npm packages found
            if npm_packages:
                logger.debug("First 5 npm packages found:")
                for i, (name, version) in enumerate(npm_packages[:5]):
                    logger.debug("  %d. %s@%s", i+1, name, version)
            
            # Track mapping statistics
            mapped_count = 0
            unmapped_packages = []
            
            # Now map each npm package to its GitHub repository
            for npm_name, npm_version in npm_packages:
                try:
                    github_repo = self._get_github_repo_from_npm(npm_name, npm_version)
                    if github_repo:
                        owner, repo = github_repo
                        dependencies.append(GitHubDependency(
                            owner=owner,
                            repo=repo,
                            version=npm_version,
                            source="npm_to_github"
                        ))
                        mapped_count += 1
                        logger.debug("Mapped %s@%s to %s/%s", npm_name, npm_version, owner, repo)
                    else:
                        unmapped_packages.append((npm_name, npm_version))
                        logger.warning("Could not find GitHub repo for %s@%s", npm_name, npm_version)
                except Exception as e:
                    unmapped_packages.append((npm_name, npm_version))
                    logger.warning("Error mapping %s@%s to GitHub: %s", npm_name, npm_version, e)
                    # Generic debug for first few unmapped packages
                    if len(unmapped_packages) <= 5:
                        logger.debug("Attempting to debug %s@%s mapping:", npm_name, npm_version)
                        try:
                            # Try to get the npm registry info directly
                            encoded = npm_name
                            if npm_name.startswith('@'):
                                encoded = npm_name.replace('/', '%2F')
                            url = f'https://registry.npmjs.org/{encoded}/{npm_version}'
                            response = requests.get(url, timeout=10)
                            if response.status_code == 200:
                                data = response.json()
                                logger.debug("  Available fields: %s", list(data.keys()))
                                for field in ['repository', 'url', 'homepage']:
                                    if field in data:
                                        logger.debug("  %s field: %s", field, data[field])
                            else:
                                logger.debug("  Could not fetch npm registry data: %s", response.status_code)
                        except Exception as debug_e:
                            logger.debug("  Debug error: %s", debug_e)
            
            # Report mapping summary
            logger.info("Successfully mapped %d of %d npm packages to GitHub repositories", 
                       mapped_count, len(npm_packages))
            if unmapped_packages:
                logger.warning("Failed to map %d npm packages (listed below):", len(unmapped_packages))
                for npm_name, npm_version in unmapped_packages[:10]:  # Show first 10
                    logger.warning("  - %s@%s", npm_name, npm_version)
                if len(unmapped_packages) > 10:
                    logger.warning("  ... and %d more", len(unmapped_packages) - 10)
        
        # Also extract dependencies from relationships (this should catch all dependencies)
        if "relationships" in sbom:
            logger.debug("Processing %d relationships for additional dependencies", len(sbom["relationships"]))
            rel_count = 0
            vcs_found = 0
            npm_found = 0
            other_types = 0
            
            for rel in sbom.get("relationships", []):
                if not isinstance(rel, dict) or rel.get("relationshipType") != "DEPENDS_ON":
                    continue
                
                rel_count += 1
                
                # Get the related element (the dependency)
                related = rel.get("relatedSpdxElement", "")
                logger.debug("Relationship %d: related=%s", rel_count, related)
                
                if isinstance(related, str):
                    # This is a reference to a package in the packages section
                    # It might start with # or be an SPDXRef directly
                    if related.startswith("#"):
                        ref_id = related[1:]  # Remove # prefix
                    else:
                        ref_id = related  # Use as-is
                    
                    # Find the corresponding package
                    for pkg in sbom.get("packages", []):
                        if pkg.get("SPDXID") == ref_id:
                            pkg_name = pkg.get("name", "")
                            version = pkg.get("versionInfo", "")
                            logger.debug("  Found package: %s@%s", pkg_name, version)
                            
                            # Check external refs for any GitHub references
                            has_github_vcs = False
                            has_npm_purl = False
                            
                            for ext_ref in pkg.get("externalRefs", []):
                                ref_type = ext_ref.get("referenceType", "")
                                ref_locator = ext_ref.get("referenceLocator", "")
                                logger.debug("    External ref type=%s, locator=%s", ref_type, ref_locator[:100] if len(ref_locator) > 100 else ref_locator)
                                
                                if ref_type == "vcs" and "github.com" in ref_locator:
                                    # Extract GitHub repo info
                                    repo_url = ref_locator
                                    match = re.search(r'github\.com/([^/]+)/([^/.]+)', repo_url)
                                    if match:
                                        dep_owner, dep_repo = match.groups()
                                        dependencies.append(GitHubDependency(
                                            owner=dep_owner,
                                            repo=dep_repo,
                                            version=version,
                                            source="vcs_direct"
                                        ))
                                        vcs_found += 1
                                        has_github_vcs = True
                                        logger.info("✅ Added direct GitHub dependency: %s/%s (from VCS ref)", dep_owner, dep_repo)
                                elif ref_type == "purl" and ref_locator.startswith("pkg:npm/"):
                                    has_npm_purl = True
                                    npm_found += 1
                                    
                                    # Extract npm package name and version from purl
                                    # Format: pkg:npm/package-name@version
                                    package_part = ref_locator.split("pkg:npm/")[-1]
                                    decoded_part = urllib.parse.unquote(package_part)
                                    parts = decoded_part.split("@")
                                    if len(parts) >= 1:
                                        npm_name = parts[0]
                                        npm_version = parts[1] if len(parts) > 1 else version
                                        
                                        # Try to map this npm package to GitHub
                                        try:
                                            github_repo = self._get_github_repo_from_npm(npm_name, npm_version)
                                            if github_repo:
                                                dep_owner, dep_repo = github_repo
                                                dependencies.append(GitHubDependency(
                                                    owner=dep_owner,
                                                    repo=dep_repo,
                                                    version=npm_version,
                                                    source="npm_from_relationships"
                                                ))
                                                vcs_found += 1  # Count as successful mapping
                                                logger.debug("  Mapped npm %s@%s from relationship to %s/%s", npm_name, npm_version, dep_owner, dep_repo)
                                        except Exception as e:
                                            logger.debug("  Failed to map npm %s@%s from relationship: %s", npm_name, npm_version, e)
                            
                            if not has_github_vcs and not has_npm_purl:
                                other_types += 1
                                logger.warning("  ⚠️  Package %s@%s has no GitHub VCS or npm purl reference", pkg_name, version)
                            break
                else:
                    logger.debug("  Relationship related field is not a package reference: %s", related)
            
            logger.info("Relationship summary: %d total, %d with GitHub VCS, %d with npm purl, %d other", 
                       rel_count, vcs_found, npm_found, other_types)

        # Remove duplicates while preserving order
        seen = set()
        unique_deps = []
        duplicates = 0
        for dep in dependencies:
            key = (dep.owner.lower(), dep.repo.lower())
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)
            else:
                duplicates += 1
        
        logger.info("Dependency deduplication: %d total, %d duplicates removed, %d unique", 
                   len(dependencies), duplicates, len(unique_deps))
        
        # Show total from SBOM relationships for comparison
        total_relationships = 0
        if "relationships" in sbom:
            for rel in sbom["relationships"]:
                if rel.get("relationshipType") == "DEPENDS_ON":
                    total_relationships += 1
        
        logger.info("SBOM contains %d DEPENDS_ON relationships, extracted %d unique dependencies", 
                   total_relationships, len(unique_deps))

        return unique_deps

    def save_sbom(self, owner: str, repo: str, sbom_data: Dict[str, Any],
                  output_dir: str, version: str = "") -> str:
        """Save SBOM data to a file."""
        os.makedirs(output_dir, exist_ok=True)

        # Create filename with version if available
        # Replace slashes with underscores to avoid creating subdirectories
        safe_owner = owner.replace('/', '_')
        safe_repo = repo.replace('/', '_')
        if version:
            # Also sanitize version to prevent directory creation
            safe_version = version.replace('/', '_').replace('\\', '_')
            filename = f"{safe_owner}_{safe_repo}_{safe_version}.json"
        else:
            filename = f"{safe_owner}_{safe_repo}.json"

        filepath = os.path.join(output_dir, filename)

        # Write SBOM data atomically
        temp_file = filepath + ".tmp"
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(sbom_data, f, indent=2, ensure_ascii=False)
            os.rename(temp_file, filepath)
            logger.debug("Saved SBOM to %s", filepath)
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise

        return filepath

    def get_all_repositories(self) -> List[Tuple[str, str]]:
        """Get all repositories for the authenticated user."""
        url = f"{GITHUB_API}/user/repos"
        params = {
            "per_page": 100,
            "sort": "updated",
            "direction": "desc"
        }

        all_repos = []
        page = 1

        while True:
            params["page"] = page
            try:
                response = self._make_request("GET", url, params=params)
                repos = response.json()

                if not repos:
                    break

                for repo in repos:
                    all_repos.append((repo["owner"]["login"], repo["name"]))

                page += 1

            except GitHubAPIError as e:
                logger.error("Failed to fetch repositories: %s", e)
                break

        return all_repos

    def get_first_repository(self) -> Tuple[str, str]:
        """Get the first repository for the authenticated user."""
        url = f"{GITHUB_API}/user/repos?per_page=1"
        response = self._make_request("GET", url)
        if response.status_code == 200:
            repos = response.json()
            if repos:
                return repos[0]["owner"]["login"], repos[0]["name"]
        return None

    def _process_dependencies(self, sbom_data, owner, repo, output_dir):
        """Process dependencies for a repository."""
        deps_dir = os.path.join(output_dir, "dependencies")
        os.makedirs(deps_dir, exist_ok=True)
        
        # Extract and process dependencies
        dependencies = self.extract_dependencies(sbom_data, owner, repo)
        if not dependencies:
            logger.info("No dependencies found")
            return
        
        logger.info("Found %d GitHub repository dependencies", len(dependencies))
        
        # Process each dependency
        success_count = 0
        for i, dep in enumerate(dependencies, 1):
            logger.info("\n[%d/%d] Processing dependency: %s/%s", 
                      i, len(dependencies), dep.owner, dep.repo)
            
            try:
                # Get and save dependency SBOM
                dep_sbom = self.get_sbom(dep.owner, dep.repo)
                if dep_sbom:
                    dep_sbom_path = self.save_sbom(
                        dep.owner,
                        dep.repo,
                        dep_sbom,
                        deps_dir,
                        version=dep.version or ""
                    )
                    logger.info("  ✅ Saved dependency SBOM: %s", 
                              os.path.relpath(dep_sbom_path, os.getcwd()))
                    success_count += 1
                else:
                    logger.warning("  ⚠️  No SBOM data for %s/%s", 
                                 dep.owner, dep.repo)
                    
            except GitHubAPIError as e:
                logger.error("  ❌ Failed to process %s/%s: %s", 
                            dep.owner, dep.repo, e)
        
        logger.info("\nProcessed %d/%d dependencies successfully", 
                   success_count, len(dependencies))

    def get_all_repositories(self) -> List[Dict[str, Any]]:
        """Get all repositories for the authenticated user."""
        url = f"{GITHUB_API}/user/repos"
        params = {
            "per_page": 100,
            "sort": "updated",
            "direction": "desc"
        }
        
        all_repos = []
        page = 1
        
        try:
            while True:
                params["page"] = page
                response = self._make_request("GET", url, params=params)
                repos = response.json()
                
                if not repos:
                    break
                    
                all_repos.extend(repos)
                
                # Check if we've reached the last page
                if len(repos) < params["per_page"]:
                    break
                    
                page += 1
                time.sleep(1)  # Be nice to the GitHub API
                
            return all_repos
            
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise GitHubAPIError("Failed to parse repository data") from e


def main() -> int:
    """Main function to fetch and process SBOMs from GitHub repositories.

    This script will:
    1. Load GitHub accounts from keys.json.
    2. Get repositories for the first account.
    3. Download SBOMs for each repository.
    4. Extract all direct dependencies as GitHub repositories.
    5. Download SBOMs for these dependencies.
    6. Save all SBOMs in a structured directory.
    """
    parser = argparse.ArgumentParser(description="Fetch and process SBOMs from GitHub repositories.")
    parser.add_argument("--gh-user", type=str, required=True,
                      help="GitHub username (e.g., tedg-dev)")
    parser.add_argument("--gh-repo", type=str, required=True,
                      help="GitHub repository name (e.g., beatBot)")
    parser.add_argument("--key-file", type=str, default="keys.json",
                      help="Path to JSON file containing GitHub credentials (default: keys.json; keys.json is also accepted)")
    parser.add_argument("--output-dir", type=str, default="sboms",
                      help="Base directory to save SBOM files (default: sboms)")
    parser.add_argument("--debug", action="store_true",
                      help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    try:
        # Load GitHub credentials
        try:
            with open(args.key_file, 'r') as f:
                credentials = json.load(f)

            # Handle both formats: single token or accounts array
            token = None
            if 'github_token' in credentials:
                token = credentials['github_token']
            elif 'accounts' in credentials and isinstance(credentials['accounts'], list):
                # Use the first account with a valid token
                for account in credentials['accounts']:
                    if 'token' in account and account['token'] and account['token'] != '<PASTE_TOKEN_HERE>':
                        token = account['token']
                        break

            if not token:
                logger.error("No valid GitHub token found in credentials file")
                return 1
        except Exception as e:
            logger.error("Failed to load credentials: %s", e)
            return 1

        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)

        # Initialize GitHub client
        fetcher = GitHubSBOMFetcher(token)

        # Create timestamped output directory
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_output_dir = os.path.join(args.output_dir, f"sbom_export_{timestamp}")
        os.makedirs(base_output_dir, exist_ok=True)
        logger.info("Created output directory: %s", base_output_dir)

        # Process the specified repository
        owner = args.gh_user
        repo = args.gh_repo
        
        logger.info("\n=== Processing repository: %s/%s ===", owner, repo)
        
        # Create repository directory structure
        repo_output_dir = os.path.join(base_output_dir, f"{owner}_{repo}")
        os.makedirs(repo_output_dir, exist_ok=True)
        
        try:
            # Process the repository
            sbom_data = fetcher.get_sbom(owner, repo)
            if not sbom_data:
                logger.error("No SBOM data found for %s/%s", owner, repo)
                return 1

            # Save main SBOM
            main_sbom_path = fetcher.save_sbom(
                owner, 
                repo, 
                sbom_data, 
                repo_output_dir,
                version=""
            )
            logger.info("✅ Main SBOM saved: %s", os.path.relpath(main_sbom_path, os.getcwd()))
            
            # Process dependencies
            fetcher._process_dependencies(sbom_data, owner, repo, repo_output_dir)

            logger.info("\n=== Processing Complete ===")
            logger.info("Output directory: %s", os.path.abspath(base_output_dir))
            return 0

        except (IndexError, GitHubAPIError) as e:
            logger.error("Failed to process repository: %s", e, exc_info=True)
            return 1

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return 1



if __name__ == "__main__":
    sys.exit(main())
