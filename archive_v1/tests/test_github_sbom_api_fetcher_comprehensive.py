"""
Comprehensive tests to achieve 80%+ code coverage.

This test file covers all previously untested functions:
- build_session
- fetch_root_sbom
- parse_purl
- map_npm_package_to_github
- map_pypi_package_to_github
- map_package_to_github
"""

import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from github_sbom_api_fetcher import (
    PackageDependency,
    build_session,
    fetch_root_sbom,
    parse_purl,
    extract_packages_from_sbom,
    map_npm_package_to_github,
    map_pypi_package_to_github,
    map_package_to_github,
)


class TestBuildSession:
    """Test session building with authentication."""
    
    def test_build_session_creates_session(self):
        """Test that build_session creates a properly configured session."""
        token = "ghp_test123456789"
        
        session = build_session(token)
        
        assert isinstance(session, requests.Session)
        assert session.headers["Authorization"] == f"token {token}"
        assert session.headers["Accept"] == "application/vnd.github+json"
        assert session.headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert "User-Agent" in session.headers
    
    def test_build_session_with_different_tokens(self):
        """Test session building with various token formats."""
        tokens = [
            "ghp_short",
            "ghp_" + "a" * 50,
            "github_pat_1234567890"
        ]
        
        for token in tokens:
            session = build_session(token)
            assert session.headers["Authorization"] == f"token {token}"


class TestFetchRootSBOM:
    """Test fetching root repository SBOM."""
    
    def test_fetch_root_sbom_success(self):
        """Test successful SBOM fetch."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sbom": {"packages": []}}
        mock_session.get.return_value = mock_response
        
        result = fetch_root_sbom(mock_session, "owner", "repo")
        
        assert result is not None
        assert "sbom" in result
        mock_session.get.assert_called_once()
    
    def test_fetch_root_sbom_404(self):
        """Test SBOM fetch when dependency graph not enabled."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response
        
        result = fetch_root_sbom(mock_session, "owner", "repo")
        
        assert result is None
    
    def test_fetch_root_sbom_403(self):
        """Test SBOM fetch with forbidden access."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 403
        mock_session.get.return_value = mock_response
        
        result = fetch_root_sbom(mock_session, "owner", "repo")
        
        assert result is None
    
    def test_fetch_root_sbom_other_error(self):
        """Test SBOM fetch with other HTTP errors."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_session.get.return_value = mock_response
        
        result = fetch_root_sbom(mock_session, "owner", "repo")
        
        assert result is None
    
    def test_fetch_root_sbom_network_error(self):
        """Test SBOM fetch with network exception."""
        mock_session = Mock()
        mock_session.get.side_effect = requests.RequestException("Network error")
        
        result = fetch_root_sbom(mock_session, "owner", "repo")
        
        assert result is None


class TestParsePurl:
    """Test Package URL parsing."""
    
    def test_parse_purl_basic_npm(self):
        """Test parsing basic npm purl."""
        ecosystem, name, version = parse_purl("pkg:npm/lodash@4.17.21")
        
        assert ecosystem == "npm"
        assert name == "lodash"
        assert version == "4.17.21"
    
    def test_parse_purl_scoped_npm(self):
        """Test parsing scoped npm package."""
        ecosystem, name, version = parse_purl("pkg:npm/@types/node@14.0.0")
        
        assert ecosystem == "npm"
        assert name == "@types/node"
        assert version == "14.0.0"
    
    def test_parse_purl_pypi(self):
        """Test parsing PyPI purl."""
        ecosystem, name, version = parse_purl("pkg:pypi/requests@2.28.1")
        
        assert ecosystem == "pypi"
        assert name == "requests"
        assert version == "2.28.1"
    
    def test_parse_purl_no_version(self):
        """Test parsing purl without version."""
        ecosystem, name, version = parse_purl("pkg:npm/some-package")
        
        assert ecosystem == "npm"
        assert name == "some-package"
        assert version == ""
    
    def test_parse_purl_invalid_format(self):
        """Test parsing invalid purl."""
        ecosystem, name, version = parse_purl("not-a-purl")
        
        assert ecosystem == "unknown"
        assert name == ""
        assert version == ""
    
    def test_parse_purl_empty(self):
        """Test parsing empty purl."""
        ecosystem, name, version = parse_purl("")
        
        assert ecosystem == "unknown"
        assert name == ""
        assert version == ""
    
    def test_parse_purl_malformed(self):
        """Test parsing malformed purl."""
        ecosystem, name, version = parse_purl("pkg:")
        
        assert ecosystem == "unknown"
        assert name == ""
        assert version == ""
    
    def test_parse_purl_complex_scoped(self):
        """Test parsing complex scoped package."""
        ecosystem, name, version = parse_purl("pkg:npm/@babel/core@7.20.0")
        
        assert ecosystem == "npm"
        assert name == "@babel/core"
        assert version == "7.20.0"


class TestExtractPackagesComprehensive:
    """Comprehensive tests for package extraction."""
    
    def test_extract_packages_skips_root_document(self):
        """Test that root document is skipped."""
        sbom_data = {
            "sbom": {
                "packages": [
                    {
                        "SPDXID": "SPDXRef-DOCUMENT",
                        "name": "root",
                        "versionInfo": "1.0.0"
                    },
                    {
                        "name": "lodash",
                        "versionInfo": "4.17.21",
                        "externalRefs": [
                            {
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/lodash@4.17.21"
                            }
                        ]
                    }
                ]
            }
        }
        
        packages = extract_packages_from_sbom(sbom_data)
        
        assert len(packages) == 1
        assert packages[0].name == "lodash"
    
    def test_extract_packages_uses_parsed_name_when_missing(self):
        """Test that parsed purl name is used when package name missing."""
        sbom_data = {
            "sbom": {
                "packages": [
                    {
                        "externalRefs": [
                            {
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/lodash@4.17.21"
                            }
                        ]
                    }
                ]
            }
        }
        
        packages = extract_packages_from_sbom(sbom_data)
        
        assert len(packages) == 1
        assert packages[0].name == "lodash"
        assert packages[0].version == "4.17.21"
    
    def test_extract_packages_scoped_npm(self):
        """Test extracting scoped npm packages."""
        sbom_data = {
            "sbom": {
                "packages": [
                    {
                        "name": "@types/node",
                        "versionInfo": "14.0.0",
                        "externalRefs": [
                            {
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/@types/node@14.0.0"
                            }
                        ]
                    }
                ]
            }
        }
        
        packages = extract_packages_from_sbom(sbom_data)
        
        assert len(packages) == 1
        assert packages[0].name == "@types/node"
        assert packages[0].ecosystem == "npm"


class TestMapNpmPackageToGitHub:
    """Test npm package to GitHub mapping."""
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_npm_success_with_git_url(self, mock_get):
        """Test successful npm mapping with git+https URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repository": {
                "url": "git+https://github.com/lodash/lodash.git"
            }
        }
        mock_get.return_value = mock_response
        
        result = map_npm_package_to_github("lodash")
        
        assert result == ("lodash", "lodash")
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_npm_success_with_https_url(self, mock_get):
        """Test successful npm mapping with https URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repository": {
                "url": "https://github.com/owner/repo"
            }
        }
        mock_get.return_value = mock_response
        
        result = map_npm_package_to_github("package")
        
        assert result == ("owner", "repo")
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_npm_success_with_git_protocol(self, mock_get):
        """Test successful npm mapping with git:// protocol."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repository": {
                "url": "git://github.com/owner/repo.git"
            }
        }
        mock_get.return_value = mock_response
        
        result = map_npm_package_to_github("package")
        
        assert result == ("owner", "repo")
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_npm_no_repository(self, mock_get):
        """Test npm mapping when no repository field."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response
        
        result = map_npm_package_to_github("package")
        
        assert result is None
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_npm_404(self, mock_get):
        """Test npm mapping when package not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = map_npm_package_to_github("nonexistent")
        
        assert result is None
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_npm_network_error(self, mock_get):
        """Test npm mapping with network error."""
        mock_get.side_effect = requests.RequestException("Timeout")
        
        result = map_npm_package_to_github("package")
        
        assert result is None
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_npm_non_github_repo(self, mock_get):
        """Test npm mapping with non-GitHub repository."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repository": {
                "url": "https://gitlab.com/owner/repo"
            }
        }
        mock_get.return_value = mock_response
        
        result = map_npm_package_to_github("package")
        
        assert result is None


class TestMapPypiPackageToGitHub:
    """Test PyPI package to GitHub mapping."""
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_pypi_success_with_source(self, mock_get):
        """Test successful PyPI mapping with Source URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "project_urls": {
                    "Source": "https://github.com/psf/requests"
                }
            }
        }
        mock_get.return_value = mock_response
        
        result = map_pypi_package_to_github("requests")
        
        assert result == ("psf", "requests")
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_pypi_success_with_homepage(self, mock_get):
        """Test successful PyPI mapping with Homepage fallback."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "project_urls": {
                    "Homepage": "https://github.com/owner/repo"
                }
            }
        }
        mock_get.return_value = mock_response
        
        result = map_pypi_package_to_github("package")
        
        assert result == ("owner", "repo")
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_pypi_success_with_repository(self, mock_get):
        """Test successful PyPI mapping with Repository URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "project_urls": {
                    "Repository": "https://github.com/owner/repo"
                }
            }
        }
        mock_get.return_value = mock_response
        
        result = map_pypi_package_to_github("package")
        
        assert result == ("owner", "repo")
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_pypi_no_project_urls(self, mock_get):
        """Test PyPI mapping with no project_urls."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {}}
        mock_get.return_value = mock_response
        
        result = map_pypi_package_to_github("package")
        
        assert result is None
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_pypi_404(self, mock_get):
        """Test PyPI mapping when package not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = map_pypi_package_to_github("nonexistent")
        
        assert result is None
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_map_pypi_network_error(self, mock_get):
        """Test PyPI mapping with network error."""
        mock_get.side_effect = requests.RequestException("Connection timeout")
        
        result = map_pypi_package_to_github("package")
        
        assert result is None


class TestMapPackageToGitHub:
    """Test generic package to GitHub mapping."""
    
    def test_map_package_npm_success(self):
        """Test mapping npm package successfully."""
        pkg = PackageDependency(
            name="lodash",
            version="4.17.21",
            purl="pkg:npm/lodash@4.17.21",
            ecosystem="npm"
        )
        
        with patch('github_sbom_api_fetcher.map_npm_package_to_github',
                   return_value=("lodash", "lodash")):
            result = map_package_to_github(pkg)
        
        assert result is True
        assert pkg.github_owner == "lodash"
        assert pkg.github_repo == "lodash"
    
    def test_map_package_pypi_success(self):
        """Test mapping PyPI package successfully."""
        pkg = PackageDependency(
            name="requests",
            version="2.28.1",
            purl="pkg:pypi/requests@2.28.1",
            ecosystem="pypi"
        )
        
        with patch('github_sbom_api_fetcher.map_pypi_package_to_github',
                   return_value=("psf", "requests")):
            result = map_package_to_github(pkg)
        
        assert result is True
        assert pkg.github_owner == "psf"
        assert pkg.github_repo == "requests"
    
    def test_map_package_npm_failure(self):
        """Test npm package mapping failure."""
        pkg = PackageDependency(
            name="unknown",
            version="1.0.0",
            purl="pkg:npm/unknown@1.0.0",
            ecosystem="npm"
        )
        
        with patch('github_sbom_api_fetcher.map_npm_package_to_github',
                   return_value=None):
            result = map_package_to_github(pkg)
        
        assert result is False
        assert pkg.github_owner is None
    
    def test_map_package_unsupported_ecosystem(self):
        """Test mapping package from unsupported ecosystem."""
        pkg = PackageDependency(
            name="artifact",
            version="1.0.0",
            purl="pkg:maven/group/artifact@1.0.0",
            ecosystem="maven"
        )
        
        result = map_package_to_github(pkg)
        
        assert result is False
        assert pkg.github_owner is None


class TestGitHubURLParsing:
    """Test various GitHub URL parsing scenarios."""
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_parse_ssh_url(self, mock_get):
        """Test parsing git+ssh URL format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repository": {
                "url": "git+ssh://git@github.com/owner/repo.git"
            }
        }
        mock_get.return_value = mock_response
        
        result = map_npm_package_to_github("package")
        
        assert result == ("owner", "repo")
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_parse_url_with_path(self, mock_get):
        """Test parsing URL with additional path."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repository": {
                "url": "https://github.com/owner/repo/issues"
            }
        }
        mock_get.return_value = mock_response
        
        result = map_npm_package_to_github("package")
        
        assert result == ("owner", "repo")
    
    @patch('github_sbom_api_fetcher.requests.get')
    def test_parse_url_with_dot_git(self, mock_get):
        """Test parsing URL ending with .git."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repository": {
                "url": "https://github.com/owner/repo.git"
            }
        }
        mock_get.return_value = mock_response
        
        result = map_npm_package_to_github("package")
        
        assert result == ("owner", "repo")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=github_sbom_api_fetcher",
                 "--cov-report=term"])
