"""Unit tests for SBOM parsers - Fixed version."""

import pytest

from sbom_fetcher.domain.models import PackageDependency
from sbom_fetcher.services.parsers import PURLParser, SBOMParser


class TestPURLParser:
    """Tests for PURL parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = PURLParser()

    def test_parse_npm_package(self):
        """Test parsing npm package PURL."""
        purl = "pkg:npm/lodash@4.17.21"
        ecosystem, name, version = self.parser.parse(purl)

        assert ecosystem == "npm"
        assert name == "lodash"
        assert version == "4.17.21"

    def test_parse_pypi_package(self):
        """Test parsing PyPI package PURL."""
        purl = "pkg:pypi/requests@2.31.0"
        ecosystem, name, version = self.parser.parse(purl)

        assert ecosystem == "pypi"
        assert name == "requests"
        assert version == "2.31.0"

    def test_parse_scoped_npm_package(self):
        """Test parsing scoped npm package."""
        purl = "pkg:npm/%40babel/core@7.22.0"
        ecosystem, name, version = self.parser.parse(purl)

        assert ecosystem == "npm"
        # Parser returns URL-encoded name (will be decoded by mappers if needed)
        assert name == "%40babel/core"
        assert version == "7.22.0"

    def test_parse_invalid_purl(self):
        """Test parsing invalid PURL returns unknown."""
        ecosystem, name, version = self.parser.parse("invalid-purl")

        assert ecosystem == "unknown"
        assert name == ""
        assert version == ""

    def test_parse_purl_without_version(self):
        """Test parsing PURL without version."""
        purl = "pkg:npm/lodash"
        ecosystem, name, version = self.parser.parse(purl)

        assert ecosystem == "npm"
        assert name == "lodash"
        assert version == ""


class TestSBOMParser:
    """Tests for SBOM parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SBOMParser()

    def test_extract_packages_from_sbom(self, sample_sbom_data):
        """Test extracting packages from SBOM data."""
        packages = self.parser.extract_packages(sample_sbom_data, "test-owner", "test-repo")

        assert len(packages) == 2
        assert all(isinstance(pkg, PackageDependency) for pkg in packages)

    def test_extract_npm_package(self):
        """Test extracting npm package."""
        sbom_data = {
            "sbom": {
                "packages": [
                    {
                        "SPDXID": "SPDXRef-Package-lodash",
                        "name": "lodash",
                        "versionInfo": "4.17.21",
                        "externalRefs": [
                            {
                                "referenceCategory": "PACKAGE-MANAGER",
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/lodash@4.17.21",
                            }
                        ],
                    }
                ]
            }
        }

        packages = self.parser.extract_packages(sbom_data, "owner", "repo")

        assert len(packages) == 1
        pkg = packages[0]
        assert pkg.name == "lodash"
        assert pkg.version == "4.17.21"
        assert pkg.ecosystem == "npm"
        assert pkg.purl == "pkg:npm/lodash@4.17.21"

    def test_skip_package_without_purl(self):
        """Test skipping package without PURL."""
        sbom_data = {
            "sbom": {
                "packages": [
                    {
                        "SPDXID": "SPDXRef-Package-nopurl",
                        "name": "nopurl",
                        "versionInfo": "1.0.0",
                        "externalRefs": [],
                    },
                    {
                        "SPDXID": "SPDXRef-Package-lodash",
                        "name": "lodash",
                        "versionInfo": "4.17.21",
                        "externalRefs": [
                            {
                                "referenceCategory": "PACKAGE-MANAGER",
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/lodash@4.17.21",
                            }
                        ],
                    },
                ]
            }
        }

        packages = self.parser.extract_packages(sbom_data, "owner", "repo")

        # Should only return lodash
        assert len(packages) == 1
        assert packages[0].name == "lodash"

    def test_handle_empty_sbom(self):
        """Test handling empty SBOM."""
        sbom_data = {"sbom": {"packages": []}}

        packages = self.parser.extract_packages(sbom_data, "owner", "repo")

        assert len(packages) == 0

    def test_handle_missing_packages_key(self):
        """Test handling SBOM without packages key."""
        sbom_data = {"sbom": {}}

        packages = self.parser.extract_packages(sbom_data, "owner", "repo")

        assert len(packages) == 0
