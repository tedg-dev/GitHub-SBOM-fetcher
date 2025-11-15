#!/usr/bin/env python3
"""Fetch SBOMs from GitHub repositories and their dependencies."""

import argparse
import json
import logging
import os
import sys
import time
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

    def __init__(self, token: str):
        """Initialize the GitHub SBOM fetcher.
        
        Args:
            token: GitHub personal access token
        """
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
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
        """Get GitHub repository URL from npm package."""
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
                repo = data.get('repository')
                if repo:
                    if isinstance(repo, dict):
                        repo_url = repo.get('url')
                    else:
                        repo_url = repo
                    
                    if repo_url:
                        # Clean up the URL
                        if repo_url.startswith('git+'):
                            repo_url = repo_url[4:]
                        if repo_url.startswith('git://'):
                            repo_url = repo_url.replace('git://', 'https://')
                        if repo_url.endswith('.git'):
                            repo_url = repo_url[:-4]
                        
                        # Extract owner and repo from GitHub URL
                        if 'github.com/' in repo_url:
                            parts = repo_url.split('github.com/')[-1].split('/')
                            if len(parts) >= 2:
                                owner = parts[0]
                                repo = parts[1]
                                return owner, repo
            return None
        except Exception as e:
            logger.debug("Error getting repo for %s@%s: %s", package_name, version, e)
            return None

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

        # Handle SPDX format SBOM - extract npm packages and map to GitHub repos
        if "packages" in sbom:
            logger.debug("Found %d packages in SBOM", len(sbom["packages"]))
            npm_packages = []
            
            # First, extract all npm packages
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
                            parts = purl.split("pkg:npm/")[-1].split("@")
                            if len(parts) >= 1:
                                npm_name = parts[0]
                                npm_version = parts[1] if len(parts) > 1 else version
                                npm_packages.append((npm_name, npm_version))

            logger.info("Found %d npm packages to map to GitHub repositories", len(npm_packages))
            
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
                        logger.debug("Mapped %s@%s to %s/%s", npm_name, npm_version, owner, repo)
                    else:
                        logger.debug("Could not find GitHub repo for %s@%s", npm_name, npm_version)
                except Exception as e:
                    logger.warning("Error mapping %s@%s to GitHub: %s", npm_name, npm_version, e)

        # Remove duplicates while preserving order
        seen = set()
        unique_deps = []
        for dep in dependencies:
            key = (dep.owner.lower(), dep.repo.lower())
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)

        return unique_deps

    def save_sbom(self, owner: str, repo: str, sbom_data: Dict[str, Any],
                  output_dir: str, version: str = "") -> str:
        """Save SBOM data to a file."""
        os.makedirs(output_dir, exist_ok=True)

        # Create filename with version if available
        if version:
            filename = f"{owner}_{repo}_{version}.json"
        else:
            filename = f"{owner}_{repo}.json"

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
        url = f"{GITHUB_API}/user/repos"
        params = {
            "per_page": 1,
            "sort": "updated",
            "direction": "desc"
        }

        try:
            response = self._make_request("GET", url, params=params)
            repos = response.json()

            if not repos:
                raise GitHubAPIError("No repositories found for the account")

            return repos[0]["owner"]["login"], repos[0]["name"]

        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise GitHubAPIError("Failed to parse repository data") from e


def main(argv: Optional[List[str]] = None) -> int:
    """Main function to fetch and process SBOMs from GitHub repositories.

    This script will:
    1. Load the first GitHub account from key.json.
    2. Get the first repository for that account.
    3. Download its SBOM.
    4. Extract all direct dependencies as GitHub repositories.
    5. Download SBOMs for these dependencies.
    6. Save all SBOMs in the parent output directory.
    """
    parser = argparse.ArgumentParser(description="Fetch and process SBOMs from GitHub repositories.")
    parser.add_argument("--key-file", type=str, default="key.json",
                      help="Path to JSON file containing GitHub credentials (default: key.json)")
    parser.add_argument("--output-dir", type=str, default="sboms",
                      help="Base directory to save SBOM files (default: sboms)")
    parser.add_argument("--debug", action="store_true",
                      help="Enable debug logging")

    args = parser.parse_args(argv)

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

        # Use the specific repository tedg-dev/beatBot as requested
        try:
            owner = "tedg-dev"
            repo = "beatBot"
            logger.info("\n=== Processing repository: %s/%s ===", owner, repo)

            # Create repository directory structure
            repo_output_dir = os.path.join(base_output_dir, f"tedg-dev_beatBot")
            deps_dir = os.path.join(repo_output_dir, "dependencies")
            os.makedirs(repo_output_dir, exist_ok=True)
            os.makedirs(deps_dir, exist_ok=True)

            # Process the main repository
            sbom_data = fetcher.get_sbom(owner, repo)
            if not sbom_data:
                logger.error("No SBOM data found for %s/%s", owner, repo)
                return 1

            # Save main SBOM in the tedg-dev_beatBot folder
            main_sbom_path = fetcher.save_sbom(
                owner, 
                repo, 
                sbom_data, 
                repo_output_dir,  # Save in tedg-dev_beatBot folder
                version=""
            )
            logger.info("✅ Main SBOM saved: %s", os.path.relpath(main_sbom_path, os.getcwd()))

            # Extract and process dependencies
            dependencies = fetcher.extract_dependencies(sbom_data, owner, repo)
            logger.info("\nFound %d GitHub repository dependencies", len(dependencies))

            # Process each dependency
            success_count = 0
            error_count = 0
            for i, dep in enumerate(dependencies, 1):
                logger.info("\n[%d/%d] Processing dependency: %s/%s", 
                          i, len(dependencies), dep.owner, dep.repo)

                try:
                    # Get and save dependency SBOM in dependencies folder
                    dep_sbom = fetcher.get_sbom(dep.owner, dep.repo)
                    if dep_sbom:
                        dep_sbom_path = fetcher.save_sbom(
                            dep.owner,
                            dep.repo,
                            dep_sbom,
                            deps_dir,  # Save in dependencies subfolder
                            version=dep.version or ""
                        )
                        logger.info("  ✅ Saved dependency SBOM: %s", 
                                  os.path.relpath(dep_sbom_path, os.getcwd()))
                        success_count += 1
                    else:
                        logger.warning("  ⚠️  No SBOM data for %s/%s", 
                                     dep.owner, dep.repo)
                        error_count += 1

                except GitHubAPIError as e:
                    logger.error("  ❌ Failed to process %s/%s: %s", 
                                dep.owner, dep.repo, e)
                    error_count += 1

            logger.info("\n=== Processing Complete ===")
            logger.info("Main repository: %s/%s", owner, repo)
            logger.info("Dependencies processed successfully: %d", success_count)
            if error_count > 0:
                logger.warning("Dependencies with errors: %d", error_count)

            logger.info("\nOutput directory: %s", os.path.abspath(base_output_dir))

            if success_count > 0 or error_count == 0:
                return 0
            return 1

        except (IndexError, GitHubAPIError) as e:
            logger.error("Failed to process repository: %s", e, exc_info=True)
            return 1

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
