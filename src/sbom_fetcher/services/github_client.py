"""GitHub API client."""

import logging
import time
from typing import Any, Dict, Optional

import requests

from ..domain.exceptions import GitHubAPIError
from ..domain.models import ErrorType, PackageDependency
from ..infrastructure.config import Config
from ..infrastructure.http_client import HTTPClient

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub API client for SBOM operations."""

    def __init__(self, http_client: HTTPClient, token: str, config: Config):
        """
        Initialize GitHub client.

        Args:
            http_client: HTTP client for making requests
            token: GitHub API token
            config: Application configuration
        """
        self._http_client = http_client
        self._token = token
        self._config = config
        self._sbom_api_template = (
            f"{config.github_api_url}/repos/{{owner}}/{{repo}}/dependency-graph/sbom"
        )

    def fetch_root_sbom(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the root repository's SBOM via GitHub API.

        Preserves exact behavior from original: returns None on any failure.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            SBOM data as dict, or None if unavailable
        """
        url = self._sbom_api_template.format(owner=owner, repo=repo)
        logger.info("Fetching root SBOM: %s/%s", owner, repo)

        try:
            # Create a requests session with auth for this call
            session = requests.Session()
            session.headers.update(
                {
                    "Authorization": f"token {self._token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "github-sbom-api-fetcher/1.0",
                }
            )

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

    def download_dependency_sbom(
        self, session: requests.Session, pkg: PackageDependency, output_dir: str
    ) -> bool:
        """
        Download SBOM for a dependency's GitHub repository.

        Preserves exact behavior from original including retry logic,
        error types, and error messages.

        Args:
            session: Requests session (with auth headers)
            pkg: Package dependency to download SBOM for
            output_dir: Directory to save SBOM file

        Returns:
            True if successful, False otherwise (sets pkg.error and pkg.error_type)
        """
        if not pkg.github_repository:
            pkg.error = "No GitHub repository mapped"
            return False

        url = self._sbom_api_template.format(
            owner=pkg.github_repository.owner, repo=pkg.github_repository.repo
        )

        max_retries = self._config.max_retries

        for attempt in range(max_retries):
            try:
                resp = session.get(url, timeout=30)

                if resp.status_code == 200:
                    # Save SBOM (use _current.json since GitHub API only
                    # returns current state, not version-specific)
                    import json
                    import os

                    filename = (
                        f"{pkg.github_repository.owner}_"
                        f"{pkg.github_repository.repo}_current.json"
                    )
                    filepath = os.path.join(output_dir, filename)

                    with open(filepath, "w") as f:
                        json.dump(resp.json(), f, indent=2)

                    pkg.sbom_downloaded = True
                    return True

                elif resp.status_code == 404:
                    pkg.error = "Dependency graph not enabled"
                    pkg.error_type = ErrorType.PERMANENT
                    return False
                elif resp.status_code == 403:
                    pkg.error = "Access forbidden"
                    pkg.error_type = ErrorType.PERMANENT
                    return False
                elif resp.status_code == 429:
                    # Rate limited
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        logger.debug("Rate limited, waiting %ds...", wait_time)
                        time.sleep(wait_time)
                        continue
                    pkg.error = "Rate limited"
                    pkg.error_type = ErrorType.TRANSIENT
                    return False
                else:
                    pkg.error = f"HTTP {resp.status_code}"
                    pkg.error_type = ErrorType.PERMANENT
                    return False

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                pkg.error = str(e)
                pkg.error_type = ErrorType.TRANSIENT
                return False

        return False
