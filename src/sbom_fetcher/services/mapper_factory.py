"""Mapper factory for creating package mappers (Factory pattern)."""

import logging
from typing import Dict, Optional

from ..domain.models import PackageDependency
from ..infrastructure.config import Config
from .mappers import (
    NPMPackageMapper,
    NullMapper,
    PackageMapper,
    PyPIPackageMapper,
    search_org_for_package,
)

logger = logging.getLogger(__name__)


class MapperFactory:
    """Factory for creating package mappers based on ecosystem."""

    def __init__(
        self,
        config: Config,
        github_token: Optional[str] = None,
        root_org: Optional[str] = None,
    ):
        """
        Initialize mapper factory.

        Args:
            config: Application configuration
            github_token: Optional GitHub token for search fallback
            root_org: Optional GitHub org to search for internal packages
        """
        self._config = config
        self._github_token = github_token
        self._root_org = root_org
        self._mappers: Dict[str, PackageMapper] = {
            "npm": NPMPackageMapper(config, github_token),
            "pypi": PyPIPackageMapper(config, github_token),
        }
        self._null_mapper = NullMapper()

    def create_mapper(self, ecosystem: str) -> PackageMapper:
        """
        Create appropriate mapper for the given ecosystem.

        Args:
            ecosystem: Package ecosystem (npm, pypi, etc.)

        Returns:
            PackageMapper instance (or NullMapper for unsupported ecosystems)
        """
        return self._mappers.get(ecosystem.lower(), self._null_mapper)

    def map_package_to_github(self, pkg: PackageDependency) -> bool:
        """
        Map a package to its GitHub repository based on ecosystem.

        Preserves exact behavior from original map_package_to_github function.
        Updates pkg.github_repository if found.

        Args:
            pkg: Package dependency to map

        Returns:
            True if mapping successful, False otherwise
        """
        mapper = self.create_mapper(pkg.ecosystem)
        result = mapper.map_to_github(pkg.name)

        if result:
            pkg.github_repository = result
            logger.debug("Mapped %s → %s", pkg.name, result)
            return True

        # Fallback: Search in root org for internal packages
        if self._root_org:
            result = search_org_for_package(pkg.name, self._root_org, self._github_token)
            if result:
                pkg.github_repository = result
                logger.debug("Mapped %s → %s (via org search)", pkg.name, result)
                return True

        logger.debug("Unsupported ecosystem or mapping failed: %s for %s", pkg.ecosystem, pkg.name)
        return False
