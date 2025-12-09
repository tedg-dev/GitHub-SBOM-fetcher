"""Tests for count_sbom_components helper function."""

from sbom_fetcher.services.sbom_service import count_sbom_components


class TestCountSBOMComponents:
    """Tests for the count_sbom_components helper function."""

    def test_count_components_nested_format(self):
        """Test counting components in nested SBOM format (sbom.packages)."""
        sbom_data = {
            "sbom": {
                "packages": [
                    {"name": "pkg1", "version": "1.0"},
                    {"name": "pkg2", "version": "2.0"},
                    {"name": "pkg3", "version": "3.0"},
                ]
            }
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

    def test_count_components_empty_nested(self):
        """Test counting components with empty nested packages."""
        sbom_data = {"sbom": {"packages": []}}
        assert count_sbom_components(sbom_data) == 0

    def test_count_components_empty_direct(self):
        """Test counting components with empty direct packages."""
        sbom_data = {"packages": []}
        assert count_sbom_components(sbom_data) == 0

    def test_count_components_no_packages_key(self):
        """Test counting components when packages key is missing."""
        sbom_data = {"sbom": {"metadata": "some data"}}
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

    def test_count_components_nested_packages_not_list(self):
        """Test counting components when nested packages is not a list."""
        sbom_data = {"sbom": {"packages": "not a list"}}
        # len() works on strings, so this returns the string length
        assert count_sbom_components(sbom_data) == 10  # len("not a list")

    def test_count_components_large_sbom(self):
        """Test counting components with a large SBOM."""
        packages = [{"name": f"pkg{i}", "version": f"{i}.0"} for i in range(100)]
        sbom_data = {"sbom": {"packages": packages}}
        assert count_sbom_components(sbom_data) == 100

    def test_count_components_prefers_nested_format(self):
        """Test that nested format takes precedence over direct format."""
        # If both exist, nested should be used
        sbom_data = {
            "sbom": {"packages": [{"name": "pkg1"}, {"name": "pkg2"}]},
            "packages": [{"name": "pkg3"}],  # This should be ignored
        }
        assert count_sbom_components(sbom_data) == 2  # Uses nested format
