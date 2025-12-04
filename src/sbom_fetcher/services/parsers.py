"""SBOM parsing logic."""

import logging
from typing import Any, Dict, List, Tuple

from ..domain.exceptions import ValidationError
from ..domain.models import PackageDependency

logger = logging.getLogger(__name__)


class PURLParser:
    """Parser for Package URLs (PURL)."""

    @staticmethod
    def parse(purl: str) -> Tuple[str, str, str]:
        """
        Parse Package URL to extract ecosystem, name, and version.

        Example: pkg:npm/lodash@4.17.5 → ('npm', 'lodash', '4.17.5')

        Args:
            purl: Package URL string

        Returns:
            Tuple of (ecosystem, name, version)
        """
        if not purl or not purl.startswith("pkg:"):
            return ("unknown", "", "")

        purl = purl[4:]  # Remove pkg: prefix

        # Split ecosystem and rest
        parts = purl.split("/", 1)
        if len(parts) < 2:
            return ("unknown", "", "")

        ecosystem = parts[0]
        rest = parts[1]

        # Handle namespace (e.g., pkg:npm/@types/node@14.0.0)
        if rest.startswith("@"):
            scope_parts = rest.split("/", 1)
            if len(scope_parts) < 2:
                return (ecosystem, "", "")
            name_version = f"{scope_parts[0]}/{scope_parts[1]}"
        else:
            name_version = rest

        # Split name and version
        if "@" in name_version:
            if name_version.startswith("@"):
                # Scoped package
                second_at = name_version.find("@", 1)
                if second_at > 0:
                    name = name_version[:second_at]
                    version = name_version[second_at + 1 :]
                else:
                    name = name_version
                    version = ""
            else:
                last_at = name_version.rfind("@")
                name = name_version[:last_at]
                version = name_version[last_at + 1 :]
        else:
            name = name_version
            version = ""

        return (ecosystem, name, version)


class SBOMParser:
    """Parser for SBOM data."""

    def __init__(self) -> None:
        """Initialize parser."""
        self._purl_parser = PURLParser()
        self._logger = logging.getLogger(__name__)

    def extract_packages(self, sbom_data: Dict[str, Any]) -> List[PackageDependency]:
        """
        Extract package dependencies from SBOM data.

        Args:
            sbom_data: Full SBOM response from GitHub API

        Returns:
            List of PackageDependency objects

        Raises:
            ValidationError: If SBOM structure is invalid
        """
        if not isinstance(sbom_data, dict):
            raise ValidationError("SBOM data must be a dictionary")

        packages = []
        sbom = sbom_data.get("sbom", {})
        package_list = sbom.get("packages", [])

        self._logger.info(f"Parsing SBOM with {len(package_list)} packages...")

        for pkg in package_list:
            if pkg.get("SPDXID") == "SPDXRef-DOCUMENT":
                continue

            name = pkg.get("name", "")
            version = pkg.get("versionInfo", "")

            purl = ""
            external_refs = pkg.get("externalRefs", [])
            for ref in external_refs:
                if ref.get("referenceType") == "purl":
                    purl = ref.get("referenceLocator", "")
                    break

            if not purl:
                self._logger.debug(f"No purl for package: {name}")
                continue

            ecosystem, parsed_name, parsed_version = self._purl_parser.parse(purl)

            if not name:
                name = parsed_name
            if not version:
                version = parsed_version

            if name:
                try:
                    packages.append(
                        PackageDependency(
                            name=name, version=version, purl=purl, ecosystem=ecosystem
                        )
                    )
                except ValueError as e:
                    self._logger.warning(f"Skipping invalid package {name}: {e}")
                    continue

        self._logger.info(f"Found {len(packages)} valid packages in SBOM")
        return packages
