"""Package-to-GitHub mapping strategies (Strategy pattern)."""

import logging
from typing import Optional
from urllib.parse import urlparse

import requests

from ..domain.models import GitHubRepository
from ..infrastructure.config import Config

logger = logging.getLogger(__name__)


def search_github_for_package(
    package_name: str, ecosystem: str, github_token: Optional[str] = None
) -> Optional[GitHubRepository]:
    """
    Search GitHub for a repository matching the package name.

    This is a generic fallback when registry metadata is missing or stale.

    Args:
        package_name: Name of the package to search for
        ecosystem: Package ecosystem (npm, pypi)
        github_token: Optional GitHub token for authenticated requests

    Returns:
        GitHubRepository if found, None otherwise
    """
    try:
        # Clean package name for search
        search_name = package_name
        if search_name.startswith("@"):
            # For scoped packages like @ffmpeg-installer/win32-x64,
            # use the scope name (ffmpeg-installer) which is usually the repo name
            parts = search_name.split("/")
            if len(parts) >= 2:
                scope_name = parts[0][1:]  # ffmpeg-installer (without @)
                # Search for repos matching the scope name
                search_name = scope_name

        # Build search query - look for repos with matching name
        # Note: Language filters are optional to avoid empty results for niche packages
        query = f"{search_name} in:name"

        headers = {"Accept": "application/vnd.github+json"}
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&per_page=5"
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code != 200:
            logger.debug("GitHub search returned %d for %s", resp.status_code, package_name)
            return None

        data = resp.json()
        items = data.get("items", [])

        if not items:
            return None

        # Return the top result (most stars)
        top_result = items[0]
        owner = top_result["owner"]["login"]
        repo = top_result["name"]

        logger.debug(
            "GitHub search found %s/%s for package %s (stars: %d)",
            owner,
            repo,
            package_name,
            top_result.get("stargazers_count", 0),
        )

        return GitHubRepository(owner=owner, repo=repo)

    except Exception as e:
        logger.debug("Error searching GitHub for %s: %s", package_name, e)
        return None


class PackageMapper:
    """Base interface for package mappers (Strategy pattern)."""

    def map_to_github(self, package_name: str) -> Optional[GitHubRepository]:
        """Map package name to GitHub repository."""
        raise NotImplementedError


class NPMPackageMapper(PackageMapper):
    """Maps NPM packages to GitHub repositories."""

    def __init__(self, config: Config, github_token: Optional[str] = None):
        """
        Initialize NPM mapper.

        Args:
            config: Application configuration
            github_token: Optional GitHub token for search fallback
        """
        self._config = config
        self._github_token = github_token

    def map_to_github(self, package_name: str) -> Optional[GitHubRepository]:
        """
        Map npm package to its GitHub repository using npm registry API.

        Preserves exact behavior from original map_npm_package_to_github.

        Args:
            package_name: NPM package name

        Returns:
            GitHubRepository or None if not found
        """
        try:
            # URL encode package name (especially important for scoped packages like @org/pkg)
            from urllib.parse import quote

            encoded_name = quote(package_name, safe="")
            url = f"{self._config.npm_registry_url}/{encoded_name}"
            resp = requests.get(url, timeout=10)

            if resp.status_code != 200:
                logger.debug("npm registry returned %d for %s", resp.status_code, package_name)
                return None

            data = resp.json()
            repo_info = data.get("repository")

            # Handle null/missing repository field - try GitHub search fallback
            if repo_info is None:
                logger.debug(
                    "Package %s has no repository field, trying GitHub search", package_name
                )
                return search_github_for_package(package_name, "npm", self._github_token)

            # Handle both dict and string formats
            if isinstance(repo_info, dict):
                repo_url = repo_info.get("url", "")
            elif isinstance(repo_info, str):
                repo_url = repo_info
                # Handle shorthand format: "owner/repo"
                if "/" in repo_url and "://" not in repo_url and "github" not in repo_url.lower():
                    parts = repo_url.split("/")
                    if len(parts) == 2:
                        return GitHubRepository(owner=parts[0], repo=parts[1])
            else:
                return None

            if not repo_url:
                logger.debug(
                    "Package %s has empty repository URL, trying GitHub search", package_name
                )
                return search_github_for_package(package_name, "npm", self._github_token)

            # Extract GitHub owner/repo from URL
            # Formats: git+https://github.com/owner/repo.git
            #          https://github.com/owner/repo
            #          git://github.com/owner/repo.git
            repo_url_lower = repo_url.lower()

            if "github.com" not in repo_url_lower:
                logger.debug(
                    "Package %s repository is not GitHub: %s, trying GitHub search",
                    package_name,
                    repo_url,
                )
                return search_github_for_package(package_name, "npm", self._github_token)

            repo_url = repo_url_lower

            # Clean up URL
            repo_url = (
                repo_url.replace("git+", "")
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
                logger.debug("Successfully mapped %s → %s/%s", package_name, owner, repo)
                return GitHubRepository(owner=owner, repo=repo)

            logger.debug(
                "Package %s: Could not extract owner/repo from path: %s", package_name, path
            )
            # Fallback to GitHub search
            return search_github_for_package(package_name, "npm", self._github_token)

        except Exception as e:
            logger.debug("Error mapping npm package %s: %s", package_name, e)
            return None


class PyPIPackageMapper(PackageMapper):
    """Maps PyPI packages to GitHub repositories."""

    def __init__(self, config: Config, github_token: Optional[str] = None):
        """
        Initialize PyPI mapper.

        Args:
            config: Application configuration
            github_token: Optional GitHub token for search fallback
        """
        self._config = config
        self._github_token = github_token

    def map_to_github(self, package_name: str) -> Optional[GitHubRepository]:
        """
        Map PyPI package to its GitHub repository using PyPI API.

        Preserves exact behavior from original map_pypi_package_to_github.

        Args:
            package_name: PyPI package name

        Returns:
            GitHubRepository or None if not found
        """
        try:
            url = f"{self._config.pypi_api_url}/{package_name}/json"
            resp = requests.get(url, timeout=10)

            if resp.status_code != 200:
                return None

            data = resp.json()
            info = data.get("info", {})

            # Check project_urls for Source or Repository (with flexible matching)
            project_urls = info.get("project_urls") or {}
            github_url = ""

            # Try exact matches first (preferred)
            for key in ["Source", "Repository", "Source Code", "Sources", "Code"]:
                if key in project_urls and "github.com" in project_urls[key].lower():
                    github_url = project_urls[key]
                    break

            # If not found, try case-insensitive partial matching
            if not github_url:
                for key, value in project_urls.items():
                    key_lower = key.lower()
                    if "source" in key_lower or "repository" in key_lower or "code" in key_lower:
                        if "github.com" in value.lower():
                            github_url = value
                            break

            # Fallback to Homepage or home_page if they point to GitHub
            if not github_url:
                homepage = project_urls.get("Homepage") or info.get("home_page") or ""
                if "github.com" in homepage.lower():
                    github_url = homepage

            if not github_url or "github.com" not in github_url.lower():
                logger.debug("Package %s has no GitHub URL, trying GitHub search", package_name)
                return search_github_for_package(package_name, "pypi", self._github_token)

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
                return GitHubRepository(owner=owner, repo=repo)

            return None

        except Exception as e:
            logger.debug("Error mapping PyPI package %s: %s", package_name, e)
            return None


class NullMapper(PackageMapper):
    """Null object pattern for unsupported ecosystems."""

    def map_to_github(self, package_name: str) -> None:
        """Always returns None for unsupported ecosystems."""
        return None
