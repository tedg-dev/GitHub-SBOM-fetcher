"""Shared pytest fixtures for all tests."""

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def sample_sbom_data() -> Dict[str, Any]:
    """Sample SBOM data for testing."""
    return {
        "sbom": {
            "SPDXID": "SPDXRef-DOCUMENT",
            "spdxVersion": "SPDX-2.3",
            "creationInfo": {
                "created": "2024-12-04T00:00:00Z"
            },
            "name": "test-repo",
            "dataLicense": "CC0-1.0",
            "packages": [
                {
                    "SPDXID": "SPDXRef-Package-lodash",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "externalRefs": [
                        {
                            "referenceCategory": "PACKAGE-MANAGER",
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/lodash@4.17.21"
                        }
                    ]
                },
                {
                    "SPDXID": "SPDXRef-Package-requests",
                    "name": "requests",
                    "versionInfo": "2.31.0",
                    "externalRefs": [
                        {
                            "referenceCategory": "PACKAGE-MANAGER",
                            "referenceType": "purl",
                            "referenceLocator": "pkg:pypi/requests@2.31.0"
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def npm_registry_response_with_repo() -> Dict[str, Any]:
    """Sample npm registry response with GitHub repository."""
    return {
        "name": "lodash",
        "version": "4.17.21",
        "repository": {
            "type": "git",
            "url": "git+https://github.com/lodash/lodash.git"
        }
    }


@pytest.fixture
def npm_registry_response_without_repo() -> Dict[str, Any]:
    """Sample npm registry response without repository field."""
    return {
        "name": "some-package",
        "version": "1.0.0",
        "repository": None
    }


@pytest.fixture
def pypi_registry_response_with_repo() -> Dict[str, Any]:
    """Sample PyPI registry response with GitHub repository."""
    return {
        "info": {
            "name": "requests",
            "version": "2.31.0",
            "project_urls": {
                "Source": "https://github.com/psf/requests"
            }
        }
    }


@pytest.fixture
def pypi_registry_response_without_repo() -> Dict[str, Any]:
    """Sample PyPI registry response without repository."""
    return {
        "info": {
            "name": "some-package",
            "version": "1.0.0",
            "project_urls": {}
        }
    }


@pytest.fixture
def github_sbom_response() -> Dict[str, Any]:
    """Sample GitHub SBOM API response."""
    return {
        "sbom": {
            "SPDXID": "SPDXRef-DOCUMENT",
            "spdxVersion": "SPDX-2.3",
            "name": "test-repo",
            "packages": []
        }
    }


@pytest.fixture
def mock_http_client() -> Mock:
    """Mock HTTP client."""
    client = Mock()
    client.get.return_value = Mock(
        status_code=200,
        json=lambda: {"test": "data"}
    )
    return client


@pytest.fixture
def mock_github_client() -> Mock:
    """Mock GitHub client."""
    client = Mock()
    client.fetch_root_sbom.return_value = {"sbom": {"packages": []}}
    client.download_dependency_sboms.return_value = ([], [])
    return client


@pytest.fixture
def mock_config() -> Mock:
    """Mock configuration."""
    config = Mock()
    config.github_token = "test_token"
    config.github_api_base = "https://api.github.com"
    config.npm_registry_base = "https://registry.npmjs.org"
    config.pypi_registry_base = "https://pypi.org/pypi"
    config.timeout = 30
    config.rate_limit_pause = 0.5
    config.log_level = "INFO"
    return config


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Temporary output directory for testing."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_package_dependency() -> Dict[str, Any]:
    """Sample package dependency for testing."""
    return {
        "name": "lodash",
        "version": "4.17.21",
        "ecosystem": "npm",
        "purl": "pkg:npm/lodash@4.17.21"
    }


@pytest.fixture
def mock_filesystem_repo() -> Mock:
    """Mock filesystem repository."""
    repo = Mock()
    repo.create_output_directory.return_value = Path("/tmp/test")
    repo.save_sbom.return_value = None
    repo.save_version_mapping.return_value = None
    return repo


@pytest.fixture
def sample_failed_download() -> Dict[str, Any]:
    """Sample failed download for testing."""
    return {
        "repository": "owner/repo",
        "package_name": "test-package",
        "ecosystem": "npm",
        "versions": ["1.0.0"],
        "error": "Dependency graph not enabled",
        "error_type": "PERMANENT"
    }
