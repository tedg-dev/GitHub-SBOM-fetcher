"""Comprehensive unit tests for SBOM parsers - 100% Coverage."""

import pytest

from sbom_fetcher.domain.exceptions import ValidationError
from sbom_fetcher.domain.models import PackageDependency
from sbom_fetcher.services.parsers import PURLParser, SBOMParser


class TestPURLParserComprehensive:
    """Comprehensive tests for PURL parser."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PURLParser()

    def test_parse_npm_package(self, parser):
        """Test parsing npm package PURL."""
        purl = "pkg:npm/lodash@4.17.21"
        ecosystem, name, version = parser.parse(purl)

        assert ecosystem == "npm"
        assert name == "lodash"
        assert version == "4.17.21"

    def test_parse_pypi_package(self, parser):
        """Test parsing PyPI package PURL."""
        purl = "pkg:pypi/requests@2.31.0"
        ecosystem, name, version = parser.parse(purl)

        assert ecosystem == "pypi"
        assert name == "requests"
        assert version == "2.31.0"

    def test_parse_scoped_npm_package(self, parser):
        """Test parsing scoped npm package."""
        purl = "pkg:npm/%40babel/core@7.22.0"
        ecosystem, name, version = parser.parse(purl)

        assert ecosystem == "npm"
        assert name == "%40babel/core"
        assert version == "7.22.0"

    def test_parse_scoped_package_no_version(self, parser):
        """Test parsing scoped package without version."""
        purl = "pkg:npm/%40types/node"
        ecosystem, name, version = parser.parse(purl)

        assert ecosystem == "npm"
        assert name == "%40types/node"
        assert version == ""

    def test_parse_package_without_version(self, parser):
        """Test parsing PURL without version."""
        purl = "pkg:npm/lodash"
        ecosystem, name, version = parser.parse(purl)

        assert ecosystem == "npm"
        assert name == "lodash"
        assert version == ""

    def test_parse_invalid_purl(self, parser):
        """Test parsing invalid PURL returns unknown."""
        ecosystem, name, version = parser.parse("invalid-purl")

        assert ecosystem == "unknown"
        assert name == ""
        assert version == ""

    def test_parse_empty_purl(self, parser):
        """Test parsing empty PURL."""
        ecosystem, name, version = parser.parse("")

        assert ecosystem == "unknown"
        assert name == ""
        assert version == ""

    def test_parse_none_purl(self, parser):
        """Test parsing None PURL."""
        ecosystem, name, version = parser.parse(None)

        assert ecosystem == "unknown"
        assert name == ""
        assert version == ""

    def test_parse_purl_without_slash(self, parser):
        """Test parsing PURL without slash (invalid format)."""
        purl = "pkg:npm"
        ecosystem, name, version = parser.parse(purl)

        assert ecosystem == "unknown"
        assert name == ""
        assert version == ""

    def test_parse_golang_package(self, parser):
        """Test parsing golang package."""
        purl = "pkg:golang/github.com/sirupsen/logrus@v1.9.0"
        ecosystem, name, version = parser.parse(purl)

        assert ecosystem == "golang"
        assert name == "github.com/sirupsen/logrus"
        assert version == "v1.9.0"

    def test_parse_maven_package(self, parser):
        """Test parsing Maven package."""
        purl = "pkg:maven/org.springframework/spring-core@5.3.20"
        ecosystem, name, version = parser.parse(purl)

        assert ecosystem == "maven"
        assert name == "org.springframework/spring-core"
        assert version == "5.3.20"

    def test_parse_scoped_package_incomplete(self, parser):
        """Test parsing incomplete scoped package."""
        purl = "pkg:npm/@babel"
        ecosystem, name, version = parser.parse(purl)

        assert ecosystem == "npm"
        assert name == ""
        assert version == ""

    def test_parse_github_package(self, parser):
        """Test parsing GitHub package PURL."""
        purl = "pkg:github/owner/repo@v1.0.0"
        ecosystem, name, version = parser.parse(purl)

        assert ecosystem == "github"
        assert name == "owner/repo"
        assert version == "v1.0.0"


class TestSBOMParserComprehensive:
    """Comprehensive tests for SBOM parser."""

    @pytest.fixture
    def parser(self):
        """Create SBOM parser instance."""
        return SBOMParser()

    @pytest.fixture
    def valid_sbom(self):
        """Valid SBOM data fixture in pure SPDX format."""
        return {
            "spdxVersion": "SPDX-2.3",
            "SPDXID": "SPDXRef-DOCUMENT",
            "packages": [
                {
                    "SPDXID": "SPDXRef-Package-lodash",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/lodash@4.17.21",
                        }
                    ],
                },
                {
                    "SPDXID": "SPDXRef-Package-requests",
                    "name": "requests",
                    "versionInfo": "2.31.0",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:pypi/requests@2.31.0",
                        }
                    ],
                },
            ],
        }

    def test_extract_packages_from_valid_sbom(self, parser, valid_sbom):
        """Test extracting packages from valid SBOM."""
        packages = parser.extract_packages(valid_sbom)

        assert len(packages) == 2
        assert packages[0].name == "lodash"
        assert packages[0].version == "4.17.21"
        assert packages[0].ecosystem == "npm"
        assert packages[1].name == "requests"
        assert packages[1].version == "2.31.0"
        assert packages[1].ecosystem == "pypi"

    def test_extract_packages_filters_root(self, parser, valid_sbom):
        """Test that root repository package is filtered out."""
        valid_sbom["packages"].append(
            {
                "SPDXID": "SPDXRef-Package-root",
                "name": "my-repo",
                "versionInfo": "1.0.0",
                "externalRefs": [
                    {
                        "referenceType": "purl",
                        "referenceLocator": "pkg:github/owner/my-repo@1.0.0",
                    }
                ],
            }
        )

        packages = parser.extract_packages(valid_sbom, owner="owner", repo="my-repo")

        # Should exclude the root package
        assert len(packages) == 2
        assert all(pkg.name != "my-repo" for pkg in packages)

    def test_extract_packages_skips_document_spdx(self, parser):
        """Test that SPDXRef-DOCUMENT is skipped."""
        sbom = {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "SPDXID": "SPDXRef-DOCUMENT",
                    "name": "document",
                    "versionInfo": "1.0.0",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/document@1.0.0",
                        }
                    ],
                },
                {
                    "SPDXID": "SPDXRef-Package-lodash",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/lodash@4.17.21",
                        }
                    ],
                },
            ],
        }

        packages = parser.extract_packages(sbom)

        assert len(packages) == 1
        assert packages[0].name == "lodash"

    def test_extract_packages_skips_without_purl(self, parser):
        """Test that packages without PURL are skipped."""
        sbom = {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "SPDXID": "SPDXRef-Package-nopurl",
                    "name": "no-purl",
                    "versionInfo": "1.0.0",
                    "externalRefs": [],
                },
                {
                    "SPDXID": "SPDXRef-Package-lodash",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/lodash@4.17.21",
                        }
                    ],
                },
            ],
        }

        packages = parser.extract_packages(sbom)

        assert len(packages) == 1
        assert packages[0].name == "lodash"

    def test_extract_packages_handles_empty_sbom(self, parser):
        """Test handling empty SBOM."""
        sbom = {"spdxVersion": "SPDX-2.3", "packages": []}

        packages = parser.extract_packages(sbom)

        assert len(packages) == 0

    def test_extract_packages_handles_missing_packages_key(self, parser):
        """Test handling SBOM without packages key."""
        sbom = {"spdxVersion": "SPDX-2.3"}

        packages = parser.extract_packages(sbom)

        assert len(packages) == 0

    def test_extract_packages_handles_empty_dict(self, parser):
        """Test handling empty dict."""
        sbom = {}

        packages = parser.extract_packages(sbom)

        assert len(packages) == 0

    def test_extract_packages_invalid_sbom_data(self, parser):
        """Test that non-dict SBOM raises ValidationError."""
        with pytest.raises(ValidationError, match="SBOM data must be a dictionary"):
            parser.extract_packages("not a dict")

    def test_extract_packages_invalid_sbom_list(self, parser):
        """Test that list SBOM raises ValidationError."""
        with pytest.raises(ValidationError):
            parser.extract_packages([])

    def test_extract_packages_invalid_sbom_none(self, parser):
        """Test that None SBOM raises ValidationError."""
        with pytest.raises(ValidationError):
            parser.extract_packages(None)

    def test_extract_packages_uses_parsed_name_when_missing(self, parser):
        """Test that parser fills in name from PURL if missing."""
        sbom = {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "SPDXID": "SPDXRef-Package-noname",
                    "name": "",
                    "versionInfo": "",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/lodash@4.17.21",
                        }
                    ],
                }
            ],
        }

        packages = parser.extract_packages(sbom)

        assert len(packages) == 1
        assert packages[0].name == "lodash"
        assert packages[0].version == "4.17.21"

    def test_extract_packages_uses_parsed_version_when_missing(self, parser):
        """Test that parser fills in version from PURL if missing."""
        sbom = {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "SPDXID": "SPDXRef-Package-lodash",
                    "name": "lodash",
                    "versionInfo": "",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/lodash@4.17.21",
                        }
                    ],
                }
            ],
        }

        packages = parser.extract_packages(sbom)

        assert len(packages) == 1
        assert packages[0].version == "4.17.21"

    def test_extract_packages_handles_multiple_external_refs(self, parser):
        """Test handling package with multiple external references."""
        sbom = {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "SPDXID": "SPDXRef-Package-lodash",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "externalRefs": [
                        {"referenceType": "homepage", "referenceLocator": "https://lodash.com"},
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/lodash@4.17.21",
                        },
                    ],
                }
            ],
        }

        packages = parser.extract_packages(sbom)

        assert len(packages) == 1
        assert packages[0].purl == "pkg:npm/lodash@4.17.21"

    def test_extract_packages_scoped_npm(self, parser):
        """Test extracting scoped npm package."""
        sbom = {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "SPDXID": "SPDXRef-Package-babel",
                    "name": "@babel/core",
                    "versionInfo": "7.22.0",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/%40babel/core@7.22.0",
                        }
                    ],
                }
            ],
        }

        packages = parser.extract_packages(sbom)

        assert len(packages) == 1
        assert packages[0].name == "@babel/core"
        assert packages[0].ecosystem == "npm"

    def test_extract_packages_without_owner_repo(self, parser, valid_sbom):
        """Test extracting without owner/repo filter."""
        packages = parser.extract_packages(valid_sbom, owner="", repo="")

        # Should include all packages since no root filtering
        assert len(packages) == 2
