"""Comprehensive unit tests for VersionLocationReporter - 100% Coverage."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from sbom_fetcher.domain.models import (
    PackageVersionMap,
    SBOMDuplicateEntry,
    VersionLocation,
)
from sbom_fetcher.services.reporters import VersionLocationReporter


class TestVersionLocation:
    """Tests for VersionLocation dataclass."""

    def test_create_version_location(self):
        """Test creating a VersionLocation instance."""
        vl = VersionLocation(
            package_name="lodash",
            version="4.17.21",
            ecosystem="npm",
        )
        assert vl.package_name == "lodash"
        assert vl.version == "4.17.21"
        assert vl.ecosystem == "npm"
        assert vl.sbom_files == []

    def test_add_location(self):
        """Test adding SBOM file locations."""
        vl = VersionLocation(
            package_name="lodash",
            version="4.17.21",
            ecosystem="npm",
        )
        vl.add_location("root_sbom.json")
        vl.add_location("dep_sbom.json")

        assert len(vl.sbom_files) == 2
        assert "root_sbom.json" in vl.sbom_files
        assert "dep_sbom.json" in vl.sbom_files

    def test_add_location_no_duplicates(self):
        """Test that duplicate locations are not added."""
        vl = VersionLocation(
            package_name="lodash",
            version="4.17.21",
            ecosystem="npm",
        )
        vl.add_location("root_sbom.json")
        vl.add_location("root_sbom.json")

        assert len(vl.sbom_files) == 1


class TestPackageVersionMap:
    """Tests for PackageVersionMap dataclass."""

    def test_create_package_version_map(self):
        """Test creating a PackageVersionMap instance."""
        pvm = PackageVersionMap(
            package_name="lodash",
            ecosystem="npm",
        )
        assert pvm.package_name == "lodash"
        assert pvm.ecosystem == "npm"
        assert pvm.versions == {}

    def test_add_version(self):
        """Test adding versions to the map."""
        pvm = PackageVersionMap(
            package_name="lodash",
            ecosystem="npm",
        )
        pvm.add_version("4.17.21", "root_sbom.json")
        pvm.add_version("4.17.20", "dep_sbom.json")

        assert "4.17.21" in pvm.versions
        assert "4.17.20" in pvm.versions
        assert len(pvm.versions) == 2

    def test_add_version_same_version_multiple_sboms(self):
        """Test adding same version from multiple SBOMs."""
        pvm = PackageVersionMap(
            package_name="lodash",
            ecosystem="npm",
        )
        pvm.add_version("4.17.21", "root_sbom.json")
        pvm.add_version("4.17.21", "dep_sbom.json")

        assert len(pvm.versions) == 1
        assert len(pvm.versions["4.17.21"].sbom_files) == 2

    def test_has_multiple_versions_false(self):
        """Test has_multiple_versions returns False for single version."""
        pvm = PackageVersionMap(
            package_name="lodash",
            ecosystem="npm",
        )
        pvm.add_version("4.17.21", "root_sbom.json")

        assert pvm.has_multiple_versions is False

    def test_has_multiple_versions_true(self):
        """Test has_multiple_versions returns True for multiple versions."""
        pvm = PackageVersionMap(
            package_name="lodash",
            ecosystem="npm",
        )
        pvm.add_version("4.17.21", "root_sbom.json")
        pvm.add_version("4.17.20", "dep_sbom.json")

        assert pvm.has_multiple_versions is True

    def test_version_count(self):
        """Test version_count property."""
        pvm = PackageVersionMap(
            package_name="lodash",
            ecosystem="npm",
        )
        assert pvm.version_count == 0

        pvm.add_version("4.17.21", "root_sbom.json")
        assert pvm.version_count == 1

        pvm.add_version("4.17.20", "dep_sbom.json")
        assert pvm.version_count == 2


class TestSBOMDuplicateEntry:
    """Tests for SBOMDuplicateEntry dataclass."""

    def test_create_sbom_duplicate_entry(self):
        """Test creating an SBOMDuplicateEntry instance."""
        entry = SBOMDuplicateEntry(
            sbom_file="root_sbom.json",
            package_name="lodash",
            ecosystem="npm",
            versions=["4.17.21", "4.17.20"],
        )
        assert entry.sbom_file == "root_sbom.json"
        assert entry.package_name == "lodash"
        assert entry.ecosystem == "npm"
        assert entry.versions == ["4.17.21", "4.17.20"]

    def test_create_sbom_duplicate_entry_default_versions(self):
        """Test creating SBOMDuplicateEntry with default empty versions."""
        entry = SBOMDuplicateEntry(
            sbom_file="root_sbom.json",
            package_name="lodash",
            ecosystem="npm",
        )
        assert entry.versions == []


class TestVersionLocationReporter:
    """Comprehensive tests for VersionLocationReporter."""

    @pytest.fixture
    def reporter(self):
        """Create reporter instance."""
        return VersionLocationReporter()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_sbom_wrapped(self):
        """Sample SBOM in wrapped GitHub API format."""
        return {
            "sbom": {
                "packages": [
                    {
                        "SPDXID": "SPDXRef-npm-lodash-4.17.21",
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
                        "SPDXID": "SPDXRef-npm-lodash-4.17.20",
                        "name": "lodash",
                        "versionInfo": "4.17.20",
                        "externalRefs": [
                            {
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/lodash@4.17.20",
                            }
                        ],
                    },
                    {
                        "SPDXID": "SPDXRef-npm-express-4.18.0",
                        "name": "express",
                        "versionInfo": "4.18.0",
                        "externalRefs": [
                            {
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/express@4.18.0",
                            }
                        ],
                    },
                ]
            }
        }

    @pytest.fixture
    def sample_sbom_pure(self):
        """Sample SBOM in pure SPDX format."""
        return {
            "packages": [
                {
                    "SPDXID": "SPDXRef-pypi-requests-2.31.0",
                    "name": "requests",
                    "versionInfo": "2.31.0",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:pypi/requests@2.31.0",
                        }
                    ],
                },
                {
                    "SPDXID": "SPDXRef-pypi-urllib3-1.26.0",
                    "name": "urllib3",
                    "versionInfo": "1.26.0",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:pypi/urllib3@1.26.0",
                        }
                    ],
                },
            ]
        }

    def test_analyze_wrapped_sbom(self, reporter, sample_sbom_wrapped):
        """Test analyzing SBOM in wrapped format."""
        reporter.analyze_sbom(sample_sbom_wrapped, "root_sbom.json")

        packages = reporter.get_packages_with_multiple_versions()
        assert len(packages) == 1
        assert packages[0].package_name == "lodash"
        assert packages[0].version_count == 2

    def test_analyze_pure_sbom(self, reporter, sample_sbom_pure):
        """Test analyzing SBOM in pure SPDX format."""
        reporter.analyze_sbom(sample_sbom_pure, "dep_sbom.json")

        # Neither package has multiple versions
        packages = reporter.get_packages_with_multiple_versions()
        assert len(packages) == 0

    def test_analyze_multiple_sboms(self, reporter, sample_sbom_wrapped, sample_sbom_pure):
        """Test analyzing multiple SBOMs."""
        reporter.analyze_sbom(sample_sbom_wrapped, "root_sbom.json")
        reporter.analyze_sbom(sample_sbom_pure, "dep_sbom.json")

        # Add another SBOM with lodash 4.17.21 in a different location
        another_sbom = {
            "packages": [
                {
                    "SPDXID": "SPDXRef-npm-lodash-4.17.21",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/lodash@4.17.21",
                        }
                    ],
                },
            ]
        }
        reporter.analyze_sbom(another_sbom, "another_sbom.json")

        packages = reporter.get_packages_with_multiple_versions()
        lodash_map = [p for p in packages if p.package_name == "lodash"][0]

        # Check that lodash 4.17.21 appears in both root and another sbom
        assert "root_sbom.json" in lodash_map.versions["4.17.21"].sbom_files
        assert "another_sbom.json" in lodash_map.versions["4.17.21"].sbom_files

    def test_detect_sbom_duplicates(self, reporter, sample_sbom_wrapped):
        """Test detection of duplicate packages within a single SBOM."""
        reporter.analyze_sbom(sample_sbom_wrapped, "root_sbom.json")

        duplicates = reporter.get_sbom_duplicates()
        assert len(duplicates) == 1
        assert duplicates[0].sbom_file == "root_sbom.json"
        assert duplicates[0].package_name == "lodash"
        assert "4.17.21" in duplicates[0].versions
        assert "4.17.20" in duplicates[0].versions

    def test_analyze_empty_sbom(self, reporter):
        """Test analyzing an empty SBOM."""
        reporter.analyze_sbom({}, "empty_sbom.json")

        packages = reporter.get_packages_with_multiple_versions()
        assert len(packages) == 0

        duplicates = reporter.get_sbom_duplicates()
        assert len(duplicates) == 0

    def test_analyze_sbom_without_packages(self, reporter):
        """Test analyzing SBOM without packages key."""
        sbom = {"name": "test", "version": "1.0"}
        reporter.analyze_sbom(sbom, "no_packages_sbom.json")

        packages = reporter.get_packages_with_multiple_versions()
        assert len(packages) == 0

    def test_analyze_sbom_with_document_entry(self, reporter):
        """Test that SPDXRef-DOCUMENT is skipped."""
        sbom = {
            "packages": [
                {
                    "SPDXID": "SPDXRef-DOCUMENT",
                    "name": "root",
                    "versionInfo": "1.0",
                },
                {
                    "SPDXID": "SPDXRef-npm-lodash",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/lodash@4.17.21",
                        }
                    ],
                },
            ]
        }
        reporter.analyze_sbom(sbom, "test_sbom.json")

        # Should only have lodash, not the DOCUMENT entry
        assert len(reporter._package_map) == 1
        assert "npm:lodash" in reporter._package_map

    def test_analyze_sbom_without_purl(self, reporter):
        """Test that packages without PURL are skipped."""
        sbom = {
            "packages": [
                {
                    "SPDXID": "SPDXRef-npm-lodash",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "externalRefs": [],
                },
            ]
        }
        reporter.analyze_sbom(sbom, "test_sbom.json")

        assert len(reporter._package_map) == 0

    def test_analyze_sbom_without_name(self, reporter):
        """Test that packages without name are skipped."""
        sbom = {
            "packages": [
                {
                    "SPDXID": "SPDXRef-npm-lodash",
                    "versionInfo": "4.17.21",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/lodash@4.17.21",
                        }
                    ],
                },
            ]
        }
        reporter.analyze_sbom(sbom, "test_sbom.json")

        assert len(reporter._package_map) == 0

    def test_parse_ecosystem_from_purl(self, reporter):
        """Test ecosystem parsing from PURL."""
        assert reporter._parse_ecosystem_from_purl("pkg:npm/lodash@4.17.21") == "npm"
        assert reporter._parse_ecosystem_from_purl("pkg:pypi/requests@2.31.0") == "pypi"
        assert reporter._parse_ecosystem_from_purl("pkg:github/owner/repo@1.0") == "github"
        assert reporter._parse_ecosystem_from_purl("") == "unknown"
        assert reporter._parse_ecosystem_from_purl("invalid") == "unknown"
        assert reporter._parse_ecosystem_from_purl(None) == "unknown"

    def test_version_sort_key(self, reporter):
        """Test version sorting key generation."""
        # Simple semver
        assert reporter._version_sort_key("1.0.0") == (1, 0, 0)
        assert reporter._version_sort_key("2.1.3") == (2, 1, 3)

        # With pre-release
        key = reporter._version_sort_key("1.0.0-beta.1")
        assert key[0] == 1
        assert key[1] == 0
        assert key[2] == 0

        # Empty version - treated as non-numeric
        assert reporter._version_sort_key("") == (999999,)

        # Non-numeric parts
        key = reporter._version_sort_key("1.0.abc")
        assert key[0] == 1
        assert key[1] == 0
        assert key[2] == 999999  # Non-numeric sorted last

    def test_generate_empty_report(self, reporter, temp_dir):
        """Test generating report with no data."""
        filename = reporter.generate(temp_dir, "owner", "repo")

        assert filename == "owner_repo_version_location_report.md"
        report_path = temp_dir / filename
        assert report_path.exists()

        content = report_path.read_text()
        assert "# Version Location Report" in content
        assert "owner/repo" in content
        assert "No packages with multiple versions were found" in content
        assert "No SBOMs contain multiple instances" in content

    def test_generate_report_with_multiple_versions(
        self, reporter, temp_dir, sample_sbom_wrapped
    ):
        """Test generating report with packages having multiple versions."""
        reporter.analyze_sbom(sample_sbom_wrapped, "root_sbom.json")

        filename = reporter.generate(temp_dir, "owner", "repo")
        content = (temp_dir / filename).read_text()

        assert "## Packages with Multiple Versions" in content
        assert "### lodash" in content
        assert "**Ecosystem:** npm" in content
        assert "**Distinct Versions:** 2" in content
        assert "| Version | Found In |" in content
        assert "| 4.17.20 |" in content
        assert "| 4.17.21 |" in content

    def test_generate_report_with_sbom_duplicates(
        self, reporter, temp_dir, sample_sbom_wrapped
    ):
        """Test generating report with SBOM internal duplicates."""
        reporter.analyze_sbom(sample_sbom_wrapped, "root_sbom.json")

        filename = reporter.generate(temp_dir, "owner", "repo")
        content = (temp_dir / filename).read_text()

        assert "## SBOM Internal Duplicates" in content
        assert "`root_sbom.json`" in content
        assert "| lodash | npm |" in content

    def test_generate_report_overview_section(
        self, reporter, temp_dir, sample_sbom_wrapped, sample_sbom_pure
    ):
        """Test report overview section."""
        reporter.analyze_sbom(sample_sbom_wrapped, "root_sbom.json")
        reporter.analyze_sbom(sample_sbom_pure, "dep_sbom.json")

        filename = reporter.generate(temp_dir, "owner", "repo")
        content = (temp_dir / filename).read_text()

        assert "## Overview" in content
        assert "**Packages with multiple versions:**" in content
        assert "**SBOMs with duplicate package instances:**" in content
        assert "**Total unique packages tracked:**" in content

    def test_generate_report_summary_statistics(
        self, reporter, temp_dir, sample_sbom_wrapped
    ):
        """Test report summary statistics section."""
        reporter.analyze_sbom(sample_sbom_wrapped, "root_sbom.json")

        filename = reporter.generate(temp_dir, "owner", "repo")
        content = (temp_dir / filename).read_text()

        assert "## Summary Statistics" in content
        assert "**Total SBOMs analyzed:**" in content
        assert "**Total unique packages:**" in content
        assert "**Total package-version combinations:**" in content
        assert "**Packages with version conflicts:**" in content
        assert "**SBOMs with internal duplicates:**" in content

    def test_generate_report_includes_metadata(self, reporter, temp_dir):
        """Test report includes execution metadata."""
        with patch("sbom_fetcher.services.reporters.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 15, 14, 30, 0)
            mock_dt.strftime = datetime.strftime

            filename = reporter.generate(temp_dir, "test-owner", "test-repo")
            content = (temp_dir / filename).read_text()

            assert "**Repository:** `test-owner/test-repo`" in content
            assert "**Generated:** 2024-01-15 14:30:00" in content
            assert f"**Output Directory:** `{temp_dir}`" in content

    def test_generate_report_includes_footer(self, reporter, temp_dir):
        """Test report includes footer."""
        filename = reporter.generate(temp_dir, "owner", "repo")
        content = (temp_dir / filename).read_text()

        assert "Generated by GitHub SBOM API Fetcher" in content
        assert "For more information, see README.md" in content

    def test_generate_report_about_section(self, reporter, temp_dir):
        """Test report includes about section."""
        filename = reporter.generate(temp_dir, "owner", "repo")
        content = (temp_dir / filename).read_text()

        assert "### About This Report" in content
        assert "packages that appear with multiple versions" in content

    def test_multiple_sboms_with_same_package_different_versions(self, reporter, temp_dir):
        """Test tracking same package with different versions across SBOMs."""
        sbom1 = {
            "packages": [
                {
                    "SPDXID": "SPDXRef-1",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "externalRefs": [
                        {"referenceType": "purl", "referenceLocator": "pkg:npm/lodash@4.17.21"}
                    ],
                }
            ]
        }
        sbom2 = {
            "packages": [
                {
                    "SPDXID": "SPDXRef-2",
                    "name": "lodash",
                    "versionInfo": "4.17.20",
                    "externalRefs": [
                        {"referenceType": "purl", "referenceLocator": "pkg:npm/lodash@4.17.20"}
                    ],
                }
            ]
        }

        reporter.analyze_sbom(sbom1, "sbom1.json")
        reporter.analyze_sbom(sbom2, "sbom2.json")

        packages = reporter.get_packages_with_multiple_versions()
        assert len(packages) == 1

        lodash = packages[0]
        assert lodash.package_name == "lodash"
        assert "4.17.21" in lodash.versions
        assert "4.17.20" in lodash.versions
        assert "sbom1.json" in lodash.versions["4.17.21"].sbom_files
        assert "sbom2.json" in lodash.versions["4.17.20"].sbom_files

        filename = reporter.generate(temp_dir, "owner", "repo")
        content = (temp_dir / filename).read_text()

        assert "`sbom1.json`" in content
        assert "`sbom2.json`" in content

    def test_scoped_npm_package(self, reporter):
        """Test handling of scoped npm packages."""
        sbom = {
            "packages": [
                {
                    "SPDXID": "SPDXRef-1",
                    "name": "@types/node",
                    "versionInfo": "18.0.0",
                    "externalRefs": [
                        {
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/%40types/node@18.0.0",
                        }
                    ],
                }
            ]
        }
        reporter.analyze_sbom(sbom, "test_sbom.json")

        assert len(reporter._package_map) == 1
        assert "npm:@types/node" in reporter._package_map

    def test_no_external_refs_key(self, reporter):
        """Test package without externalRefs key."""
        sbom = {
            "packages": [
                {
                    "SPDXID": "SPDXRef-1",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                }
            ]
        }
        reporter.analyze_sbom(sbom, "test_sbom.json")

        assert len(reporter._package_map) == 0

    def test_non_purl_external_refs(self, reporter):
        """Test package with non-purl external refs."""
        sbom = {
            "packages": [
                {
                    "SPDXID": "SPDXRef-1",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "externalRefs": [
                        {
                            "referenceType": "cpe23Type",
                            "referenceLocator": "cpe:2.3:a:lodash:lodash:4.17.21:*:*:*:*:*:*:*",
                        }
                    ],
                }
            ]
        }
        reporter.analyze_sbom(sbom, "test_sbom.json")

        assert len(reporter._package_map) == 0

    def test_multiple_duplicates_in_report(self, reporter, temp_dir):
        """Test report with multiple SBOM duplicates."""
        sbom1 = {
            "packages": [
                {
                    "SPDXID": "SPDXRef-1",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "externalRefs": [
                        {"referenceType": "purl", "referenceLocator": "pkg:npm/lodash@4.17.21"}
                    ],
                },
                {
                    "SPDXID": "SPDXRef-2",
                    "name": "lodash",
                    "versionInfo": "4.17.20",
                    "externalRefs": [
                        {"referenceType": "purl", "referenceLocator": "pkg:npm/lodash@4.17.20"}
                    ],
                },
            ]
        }
        sbom2 = {
            "packages": [
                {
                    "SPDXID": "SPDXRef-3",
                    "name": "express",
                    "versionInfo": "4.18.0",
                    "externalRefs": [
                        {"referenceType": "purl", "referenceLocator": "pkg:npm/express@4.18.0"}
                    ],
                },
                {
                    "SPDXID": "SPDXRef-4",
                    "name": "express",
                    "versionInfo": "4.17.0",
                    "externalRefs": [
                        {"referenceType": "purl", "referenceLocator": "pkg:npm/express@4.17.0"}
                    ],
                },
            ]
        }

        reporter.analyze_sbom(sbom1, "sbom1.json")
        reporter.analyze_sbom(sbom2, "sbom2.json")

        duplicates = reporter.get_sbom_duplicates()
        assert len(duplicates) == 2

        filename = reporter.generate(temp_dir, "owner", "repo")
        content = (temp_dir / filename).read_text()

        assert "`sbom1.json`" in content
        assert "`sbom2.json`" in content
        assert "| lodash | npm |" in content
        assert "| express | npm |" in content
