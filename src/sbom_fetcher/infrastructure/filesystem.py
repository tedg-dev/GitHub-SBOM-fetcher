"""Filesystem operations using Repository pattern."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from ..domain.exceptions import StorageError

logger = logging.getLogger(__name__)


class SBOMRepository(Protocol):
    """Repository interface for SBOM storage operations."""

    def save_sbom(
        self, sbom_data: Dict[str, Any], identifier: str, subdirectory: Optional[str] = None
    ) -> Path:
        """Save SBOM data to storage."""
        ...

    def save_mapping(self, mapping: Dict[str, Any], identifier: str) -> Path:
        """Save version mapping to storage."""
        ...

    def save_report(self, report_content: str, identifier: str, format: str = "md") -> Path:
        """Save report to storage."""
        ...


class FilesystemSBOMRepository:
    """Filesystem-based SBOM storage (Repository pattern)."""

    def __init__(self, base_directory: Path):
        """Initialize repository with base directory."""
        self._base_dir = Path(base_directory)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized filesystem repository at {self._base_dir}")

    def save_sbom(
        self, sbom_data: Dict[str, Any], identifier: str, subdirectory: Optional[str] = None
    ) -> Path:
        """Save SBOM to filesystem."""
        target_dir = self._base_dir
        if subdirectory:
            target_dir = target_dir / subdirectory
            target_dir.mkdir(parents=True, exist_ok=True)

        filepath = target_dir / f"{identifier}.json"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(sbom_data, f, indent=2)
            logger.debug(f"Saved SBOM to {filepath}")
            return filepath
        except IOError as e:
            raise StorageError(f"Failed to save SBOM to {filepath}: {e}") from e

    def save_mapping(self, mapping: Dict[str, Any], identifier: str) -> Path:
        """Save version mapping to filesystem."""
        filepath = self._base_dir / f"{identifier}.json"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(mapping, f, indent=2)
            logger.debug(f"Saved mapping to {filepath}")
            return filepath
        except IOError as e:
            raise StorageError(f"Failed to save mapping to {filepath}: {e}") from e

    def save_report(self, report_content: str, identifier: str, format: str = "md") -> Path:
        """Save report to filesystem."""
        filepath = self._base_dir / f"{identifier}.{format}"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report_content)
            logger.debug(f"Saved report to {filepath}")
            return filepath
        except IOError as e:
            raise StorageError(f"Failed to save report to {filepath}: {e}") from e


class InMemorySBOMRepository:
    """In-memory SBOM storage for testing."""

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self._sboms: Dict[str, Dict[str, Any]] = {}
        self._mappings: Dict[str, Dict[str, Any]] = {}
        self._reports: Dict[str, str] = {}

    def save_sbom(
        self, sbom_data: Dict[str, Any], identifier: str, subdirectory: Optional[str] = None
    ) -> Path:
        """Save SBOM to memory."""
        key = f"{subdirectory}/{identifier}" if subdirectory else identifier
        self._sboms[key] = sbom_data
        return Path(f"/mock/{key}.json")

    def save_mapping(self, mapping: Dict[str, Any], identifier: str) -> Path:
        """Save mapping to memory."""
        self._mappings[identifier] = mapping
        return Path(f"/mock/{identifier}.json")

    def save_report(self, report_content: str, identifier: str, format: str = "md") -> Path:
        """Save report to memory."""
        self._reports[identifier] = report_content
        return Path(f"/mock/{identifier}.{format}")

    def get_sbom(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get SBOM from memory (test helper)."""
        return self._sboms.get(identifier)

    def get_mapping(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get mapping from memory (test helper)."""
        return self._mappings.get(identifier)

    def get_report(self, identifier: str) -> Optional[str]:
        """Get report from memory (test helper)."""
        return self._reports.get(identifier)
