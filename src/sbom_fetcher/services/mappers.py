"""Package-to-GitHub mapping strategies (Strategy pattern)."""

import logging
from typing import Optional
from urllib.parse import urlparse

import requests

from ..domain.models import GitHubRepository
from ..infrastructure.config import Config

logger = logging.getLogger(__name__)


class PackageMapper:
    """Base interface for package mappers (Strategy pattern)."""

    def map_to_github(self, package_name: str) -> Optional[GitHubRepository]:
        """Map package name to GitHub repository."""
        raise NotImplementedError


class NPMPackageMapper(PackageMapper):
    """Maps NPM packages to GitHub repositories."""

    def __init__(self, config: Config):
        """
        Initialize NPM mapper.

        Args:
            config: Application configuration
        """
        self._config = config

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
            encoded_name = quote(package_name, safe='')
            url = f"{self._config.npm_registry_url}/{encoded_name}"
            resp = requests.get(url, timeout=10)

            if resp.status_code != 200:
                return None

            data = resp.json()
            repo_info = data.get("repository")
            
            # Handle null/missing repository field
            if repo_info is None:
                return None

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
                return GitHubRepository(owner=owner, repo=repo)

            return None

        except Exception as e:
            logger.debug("Error mapping npm package %s: %s", package_name, e)
            return None


class PyPIPackageMapper(PackageMapper):
    """Maps PyPI packages to GitHub repositories."""

    def __init__(self, config: Config):
        """
        Initialize PyPI mapper.

        Args:
            config: Application configuration
        """
        self._config = config

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
