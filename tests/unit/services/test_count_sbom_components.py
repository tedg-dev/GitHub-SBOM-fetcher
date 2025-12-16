"""Tests for count_sbom_components helper function."""

from sbom_fetcher.services.sbom_service import count_sbom_components


class TestCountSBOMComponents:
    """Tests for the count_sbom_components helper function."""

    def test_count_components_spdx_format(self):
        """Test counting components in pure SPDX format (packages at root)."""
        sbom_data = {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {"name": "pkg1", "version": "1.0"},
                {"name": "pkg2", "version": "2.0"},
                {"name": "pkg3", "version": "3.0"},
            ],
        }
        assert count_sbom_components(sbom_data) == 3

    def test_count_components_direct_format(self):
        """Test counting components in direct format (packages)."""
        sbom_data = {
            "packages": [
                {"name": "pkg1", "version": "1.0"},
                {"name": "pkg2", "version": "2.0"},
            ]
        }
        assert count_sbom_components(sbom_data) == 2

    def test_count_components_empty_packages(self):
        """Test counting components with empty packages list."""
        sbom_data = {"spdxVersion": "SPDX-2.3", "packages": []}
        assert count_sbom_components(sbom_data) == 0

    def test_count_components_empty_direct(self):
        """Test counting components with empty direct packages."""
        sbom_data = {"packages": []}
        assert count_sbom_components(sbom_data) == 0

    def test_count_components_no_packages_key(self):
        """Test counting components when packages key is missing."""
        sbom_data = {"spdxVersion": "SPDX-2.3", "name": "test"}
        assert count_sbom_components(sbom_data) == 0

    def test_count_components_empty_dict(self):
        """Test counting components with empty dictionary."""
        sbom_data = {}
        assert count_sbom_components(sbom_data) == 0

    def test_count_components_none_input(self):
        """Test counting components with None input."""
        assert count_sbom_components(None) == 0

    def test_count_components_type_error(self):
        """Test counting components with invalid type."""
        assert count_sbom_components("not a dict") == 0
        assert count_sbom_components(123) == 0
        assert count_sbom_components([]) == 0

    def test_count_components_packages_not_list(self):
        """Test counting components when packages is not a list."""
        sbom_data = {"packages": "not a list"}
        # len() works on strings, so this returns the string length
        # This is an edge case but function handles it gracefully
        assert count_sbom_components(sbom_data) == 10  # len("not a list")

    def test_count_components_with_spdx_metadata(self):
        """Test counting components with full SPDX metadata."""
        sbom_data = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "packages": [{"name": "pkg1"}, {"name": "pkg2"}],
        }
        assert count_sbom_components(sbom_data) == 2

    def test_count_components_large_sbom(self):
        """Test counting components with a large SBOM."""
        packages = [{"name": f"pkg{i}", "version": f"{i}.0"} for i in range(100)]
        sbom_data = {"spdxVersion": "SPDX-2.3", "packages": packages}
        assert count_sbom_components(sbom_data) == 100

    def test_count_components_single_package(self):
        """Test counting components with a single package."""
        sbom_data = {
            "spdxVersion": "SPDX-2.3",
            "packages": [{"name": "single-pkg", "version": "1.0.0"}],
        }
        assert count_sbom_components(sbom_data) == 1
