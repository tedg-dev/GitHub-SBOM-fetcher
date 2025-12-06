"""Comprehensive unit tests for filesystem repository - Complete Coverage."""

import json
import tempfile
from pathlib import Path

import pytest

from sbom_fetcher.domain.exceptions import StorageError
from sbom_fetcher.infrastructure.filesystem import (
    FilesystemSBOMRepository,
    InMemorySBOMRepository,
)


class TestFilesystemSBOMRepository:
    """Tests for FilesystemSBOMRepository."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def repository(self, temp_dir):
        """Create filesystem repository."""
        return FilesystemSBOMRepository(temp_dir)

    def test_initialization(self, temp_dir):
        """Test repository initialization creates directory."""
        repo = FilesystemSBOMRepository(temp_dir)

        assert repo._base_dir == temp_dir
        assert temp_dir.exists()

    def test_initialization_creates_directory(self):
        """Test repository creates non-existent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "subdir" / "nested"
            repo = FilesystemSBOMRepository(new_dir)

            assert new_dir.exists()
            assert repo._base_dir == new_dir

    def test_save_sbom_success(self, repository, temp_dir):
        """Test successfully saving SBOM."""
        sbom_data = {"sbom": {"packages": []}}

        filepath = repository.save_sbom(sbom_data, "test-sbom")

        assert filepath.exists()
        assert filepath == temp_dir / "test-sbom.json"

        with open(filepath) as f:
            loaded_data = json.load(f)
            assert loaded_data == sbom_data

    def test_save_sbom_with_subdirectory(self, repository, temp_dir):
        """Test saving SBOM to subdirectory."""
        sbom_data = {"test": "data"}

        filepath = repository.save_sbom(sbom_data, "test", subdirectory="deps")

        assert filepath.exists()
        assert filepath == temp_dir / "deps" / "test.json"
        assert (temp_dir / "deps").exists()

    def test_save_sbom_creates_subdirectory(self, repository, temp_dir):
        """Test saving SBOM creates nested subdirectories."""
        sbom_data = {"test": "data"}

        filepath = repository.save_sbom(sbom_data, "test", subdirectory="level1/level2/level3")

        assert filepath.exists()
        assert (temp_dir / "level1" / "level2" / "level3").exists()

    def test_save_mapping_success(self, repository, temp_dir):
        """Test successfully saving mapping."""
        mapping = {"repo1": {"versions": ["1.0.0", "1.0.1"]}}

        filepath = repository.save_mapping(mapping, "version-mapping")

        assert filepath.exists()
        assert filepath == temp_dir / "version-mapping.json"

        with open(filepath) as f:
            loaded_data = json.load(f)
            assert loaded_data == mapping

    def test_save_report_success(self, repository, temp_dir):
        """Test successfully saving report."""
        report_content = "# Test Report\n\nThis is a test."

        filepath = repository.save_report(report_content, "test-report")

        assert filepath.exists()
        assert filepath == temp_dir / "test-report.md"

        with open(filepath) as f:
            loaded_content = f.read()
            assert loaded_content == report_content

    def test_save_report_custom_format(self, repository, temp_dir):
        """Test saving report with custom format."""
        report_content = "Test content"

        filepath = repository.save_report(report_content, "test", format="txt")

        assert filepath.exists()
        assert filepath == temp_dir / "test.txt"

    def test_save_sbom_io_error(self, repository):
        """Test save_sbom handles IO errors."""
        # Create a file where we want to save
        bad_path = repository._base_dir / "readonly"
        bad_path.mkdir()
        bad_path.chmod(0o444)  # Read-only

        sbom_data = {"test": "data"}

        try:
            with pytest.raises(StorageError, match="Failed to save SBOM"):
                repository.save_sbom(sbom_data, "test", subdirectory="readonly")
        finally:
            bad_path.chmod(0o755)  # Restore permissions for cleanup

    def test_save_mapping_io_error(self, repository):
        """Test save_mapping handles IO errors."""
        # Temporarily make directory read-only
        repository._base_dir.chmod(0o444)

        try:
            with pytest.raises(StorageError, match="Failed to save mapping"):
                repository.save_mapping({"test": "data"}, "test")
        finally:
            repository._base_dir.chmod(0o755)

    def test_save_report_io_error(self, repository):
        """Test save_report handles IO errors."""
        repository._base_dir.chmod(0o444)

        try:
            with pytest.raises(StorageError, match="Failed to save report"):
                repository.save_report("content", "test")
        finally:
            repository._base_dir.chmod(0o755)


class TestInMemorySBOMRepository:
    """Tests for InMemorySBOMRepository."""

    @pytest.fixture
    def repository(self):
        """Create in-memory repository."""
        return InMemorySBOMRepository()

    def test_initialization(self, repository):
        """Test repository initialization."""
        assert isinstance(repository._sboms, dict)
        assert isinstance(repository._mappings, dict)
        assert isinstance(repository._reports, dict)
        assert len(repository._sboms) == 0
        assert len(repository._mappings) == 0
        assert len(repository._reports) == 0

    def test_save_sbom(self, repository):
        """Test saving SBOM to memory."""
        sbom_data = {"sbom": {"packages": []}}

        filepath = repository.save_sbom(sbom_data, "test-sbom")

        assert filepath == Path("/mock/test-sbom.json")
        assert "test-sbom" in repository._sboms
        assert repository._sboms["test-sbom"] == sbom_data

    def test_save_sbom_with_subdirectory(self, repository):
        """Test saving SBOM with subdirectory."""
        sbom_data = {"test": "data"}

        filepath = repository.save_sbom(sbom_data, "test", subdirectory="deps")

        assert filepath == Path("/mock/deps/test.json")
        assert "deps/test" in repository._sboms
        assert repository._sboms["deps/test"] == sbom_data

    def test_save_mapping(self, repository):
        """Test saving mapping to memory."""
        mapping = {"repo1": {"versions": ["1.0.0"]}}

        filepath = repository.save_mapping(mapping, "version-mapping")

        assert filepath == Path("/mock/version-mapping.json")
        assert "version-mapping" in repository._mappings
        assert repository._mappings["version-mapping"] == mapping

    def test_save_report(self, repository):
        """Test saving report to memory."""
        report_content = "# Test Report"

        filepath = repository.save_report(report_content, "test-report")

        assert filepath == Path("/mock/test-report.md")
        assert "test-report" in repository._reports
        assert repository._reports["test-report"] == report_content

    def test_save_report_custom_format(self, repository):
        """Test saving report with custom format."""
        report_content = "Test"

        filepath = repository.save_report(report_content, "test", format="txt")

        assert filepath == Path("/mock/test.txt")
        assert repository._reports["test"] == report_content

    def test_get_sbom(self, repository):
        """Test getting SBOM from memory."""
        sbom_data = {"test": "data"}
        repository.save_sbom(sbom_data, "test-sbom")

        result = repository.get_sbom("test-sbom")

        assert result == sbom_data

    def test_get_sbom_not_found(self, repository):
        """Test getting non-existent SBOM returns None."""
        result = repository.get_sbom("nonexistent")

        assert result is None

    def test_get_mapping(self, repository):
        """Test getting mapping from memory."""
        mapping = {"test": "mapping"}
        repository.save_mapping(mapping, "test-mapping")

        result = repository.get_mapping("test-mapping")

        assert result == mapping

    def test_get_mapping_not_found(self, repository):
        """Test getting non-existent mapping returns None."""
        result = repository.get_mapping("nonexistent")

        assert result is None

    def test_get_report(self, repository):
        """Test getting report from memory."""
        report = "Test report content"
        repository.save_report(report, "test-report")

        result = repository.get_report("test-report")

        assert result == report

    def test_get_report_not_found(self, repository):
        """Test getting non-existent report returns None."""
        result = repository.get_report("nonexistent")

        assert result is None

    def test_multiple_operations(self, repository):
        """Test multiple save and get operations."""
        # Save multiple items
        repository.save_sbom({"sbom": "1"}, "sbom1")
        repository.save_sbom({"sbom": "2"}, "sbom2")
        repository.save_mapping({"map": "1"}, "map1")
        repository.save_report("report1", "report1")

        # Verify all stored
        assert len(repository._sboms) == 2
        assert len(repository._mappings) == 1
        assert len(repository._reports) == 1

        # Verify retrieval
        assert repository.get_sbom("sbom1") == {"sbom": "1"}
        assert repository.get_sbom("sbom2") == {"sbom": "2"}
        assert repository.get_mapping("map1") == {"map": "1"}
        assert repository.get_report("report1") == "report1"
