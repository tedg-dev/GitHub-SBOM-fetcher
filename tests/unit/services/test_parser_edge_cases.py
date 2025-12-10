"""Tests for edge cases in PURL parsing."""

import pytest

from sbom_fetcher.services.parsers import PURLParser, SBOMParser


class TestPURLParserEdgeCases:
    """Test edge cases in PURL parsing."""

    def test_parse_purl_scoped_npm_short_format(self):
        """Test parsing scoped npm package with short format (missing second part)."""
        # This covers line 46: when scope_parts has less than 2 elements
        ecosystem, name, version = PURLParser.parse("pkg:npm/@scope")
        assert ecosystem == "npm"
        assert name == ""
        assert version == ""

    def test_parse_purl_scoped_package_with_at_no_version(self):
        """Test parsing scoped package starting with @ but no version separator."""
        # This covers lines 54-60: scoped package with @ at start but no second @
        ecosystem, name, version = PURLParser.parse("pkg:npm/@scope/package")
        assert ecosystem == "npm"
        assert name == "@scope/package"
        assert version == ""

    def test_parse_purl_scoped_package_with_single_at(self):
        """Test parsing scoped package with @ at start, no second @."""
        # This covers the else branch on lines 58-60
        # When there's only one @, the parser treats it as scoped but returns empty name
        ecosystem, name, version = PURLParser.parse("pkg:pypi/@mypackage")
        assert ecosystem == "pypi"
        # With only one @ at start and no version separator, name is empty per parser logic
        assert name == ""
        assert version == ""

    def test_parse_purl_scoped_with_version_using_at(self):
        """Test parsing scoped npm package with version using @ separator."""
        # This covers lines 56-57: scoped package with second @ for version
        ecosystem, name, version = PURLParser.parse("pkg:npm/@scope/package@1.2.3")
        assert ecosystem == "npm"
        assert name == "@scope/package"
        assert version == "1.2.3"


class TestSBOMParserEdgeCases:
    """Test edge cases in SBOM parsing."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return SBOMParser()

    def test_extract_packages_with_invalid_package_data(self, parser):
        """Test that invalid packages are skipped with warning."""
        # This covers lines 148-150: ValueError exception handling
        sbom_data = {
            "sbom": {
                "packages": [
                    {
                        "name": "valid-package",
                        "SPDXID": "SPDXRef-Package-valid",
                        "versionInfo": "1.0.0",
                        "externalRefs": [
                            {
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/valid-package@1.0.0",
                            }
                        ],
                    },
                    {
                        # Invalid: missing required fields - will trigger ValueError
                        "name": "",  # Empty name
                        "SPDXID": "SPDXRef-Package-invalid",
                        "externalRefs": [],
                    },
                ]
            }
        }

        packages = parser.extract_packages(sbom_data)
        # Should only get the valid package, invalid one skipped
        assert len(packages) == 1
        assert packages[0].name == "valid-package"
