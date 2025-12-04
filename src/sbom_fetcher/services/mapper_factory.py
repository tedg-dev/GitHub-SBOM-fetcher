"""Mapper factory for creating package mappers (Factory pattern)."""

import logging
from typing import Dict

from ..domain.models import PackageDependency
from ..infrastructure.config import Config
from .mappers import NPMPackageMapper, NullMapper, PackageMapper, PyPIPackageMapper

logger = logging.getLogger(__name__)


class MapperFactory:
    """Factory for creating package mappers based on ecosystem."""

    def __init__(self, config: Config):
        """
        Initialize mapper factory.

        Args:
            config: Application configuration
        """
        self._config = config
        self._mappers: Dict[str, PackageMapper] = {
            "npm": NPMPackageMapper(config),
            "pypi": PyPIPackageMapper(config),
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

        logger.debug("Unsupported ecosystem or mapping failed: %s for %s", pkg.ecosystem, pkg.name)
        return False
