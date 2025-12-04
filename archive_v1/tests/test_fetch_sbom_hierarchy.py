"""Extensive PyTest test suite for fetch_sbom_hierarchy.py."""

import json
import os
import requests
import time
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import pytest

from github_sbom_fetcher import fetch_sbom_hierarchy as mod


class FakeResponse:
    """Fake HTTP response for testing."""

    def __init__(
        self,
        status_code: int,
        json_data: Any = None,
        text: str = "",
        headers: Optional[Dict[str, str]] = None,
    ):
        self.status_code = status_code
        self._json = json_data
        self.text = text or (
            json.dumps(json_data) if json_data is not None else ""
        )
        self.headers = headers or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class FakeSession:
    """Fake requests session for testing."""

    def __init__(self, handler):
        self.handler = handler
        self.headers: Dict[str, str] = {}

    def request(self, method: str, url: str, **kwargs):
        return self.handler(method, url, **kwargs)

    def get(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 60,
    ):
        return self.handler(url, params or {})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Disable sleep in tests."""
    monkeypatch.setattr(time, "sleep", lambda *_: None)


def write_key(tmp_path, token: str = "tkn", username: Optional[str] = "user") -> str:
    """Write a test key file."""
    key_data = {"github_token": token}
    if username:
        key_data["username"] = username
    key_file = tmp_path / "keys.json"
    key_file.write_text(json.dumps(key_data), encoding="utf-8")
    return str(key_file)


def write_multi_key(
    tmp_path, accounts: List[Tuple[str, str]]
) -> str:
    """Write a test key file with multiple accounts."""
    key_data = {
        "accounts": [
            {"username": user, "token": token} for user, token in accounts
        ]
    }
    key_file = tmp_path / "keys.json"
    key_file.write_text(json.dumps(key_data), encoding="utf-8")
    return str(key_file)


def create_sample_sbom() -> Dict[str, Any]:
    """Create a sample SBOM for testing."""
    return {
        "sbom": {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": "com.github.tedg-dev/beatBot",
            "documentNamespace": "https://github.com/tedg-dev/beatBot/dependency-graph/sbom-sha256-abc123",
            "creationInfo": {
                "created": "2023-01-01T00:00:00Z",
            },
            "packages": [
                {
                    "name": "com.github.tedg-dev/beatBot",
                    "SPDXID": "SPDXRef-Package-main",
                    "versionInfo": "1.0.0",
                    "externalRefs": [
                        {
                            "referenceCategory": "PACKAGE-MANAGER",
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/express@4.18.0",
                        }
                    ],
                },
                {
                    "name": "pkg:npm/express",
                    "SPDXID": "SPDXRef-Package-express",
                    "versionInfo": "4.18.0",
                    "externalRefs": [
                        {
                            "referenceCategory": "PACKAGE-MANAGER",
                            "referenceType": "purl",
                            "referenceLocator": "pkg:npm/express@4.18.0",
                        }
                    ],
                },
            ],
            "relationships": [
                {
                    "spdxElementId": "SPDXRef-Package-main",
                    "relationshipType": "DEPENDS_ON",
                    "relatedSpdxElementId": "SPDXRef-Package-express",
                }
            ],
        }
    }


def create_npm_registry_response(
    repo_url: Optional[str] = None
) -> Dict[str, Any]:
    """Create a sample npm registry response."""
    response = {"name": "test-package", "version": "1.0.0"}
    if repo_url:
        response["repository"] = {"url": repo_url}
    return response


class TestGitHubDependency:
    """Test GitHubDependency dataclass."""

    def test_github_dependency_creation(self):
        """Test creating a GitHubDependency."""
        dep = mod.GitHubDependency(
            owner="test-owner",
            repo="test-repo",
            version="1.0.0",
            source="test",
        )
        assert dep.owner == "test-owner"
        assert dep.repo == "test-repo"
        assert dep.version == "1.0.0"
        assert dep.source == "test"

    def test_github_dependency_defaults(self):
        """Test GitHubDependency with default values."""
        dep = mod.GitHubDependency(owner="owner", repo="repo")
        assert dep.version == ""
        assert dep.source == ""


class TestGitHubAPIError:
    """Test GitHubAPIError exception."""

    def test_github_api_error_creation(self):
        """Test creating a GitHubAPIError."""
        error = mod.GitHubAPIError("Test error")
        assert str(error) == "Test error"

    def test_github_api_error_inheritance(self):
        """Test GitHubAPIError inherits from Exception."""
        error = mod.GitHubAPIError("Test")
        assert isinstance(error, Exception)


class TestGitHubSBOMFetcher:
    """Test GitHubSBOMFetcher class."""

    def test_init(self):
        """Test GitHubSBOMFetcher initialization."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        assert fetcher.token == "test-token"
        assert fetcher.session is not None
        assert fetcher.rate_limit_remaining == 5000
        assert fetcher.rate_limit_reset == 0
        assert fetcher.repo_sha == ""

    def test_make_request_success(self, monkeypatch):
        """Test successful API request."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        test_data = {"key": "value"}

        def handler(url, kwargs):
            return FakeResponse(200, test_data)

        monkeypatch.setattr(fetcher, "_make_request", handler)

        result = fetcher._make_request("GET", "https://api.github.com/test")
        assert isinstance(result, FakeResponse)
        assert result.status_code == 200
        assert result.json() == test_data

    def test_make_request_rate_limit(self, monkeypatch):
        """Test rate limit handling."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        
        # Create a mock response for the session's request method
        def mock_request(method, url, **kwargs):
            response = requests.Response()
            response.status_code = 403
            # Match the exact case that _make_request checks for
            response._content = b'{"message": "rate limit exceeded"}'
            response.headers = {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + 60)
            }
            return response

        # Mock the session's request method
        monkeypatch.setattr(fetcher.session, "request", mock_request)
        
        # Test that the error is raised
        with pytest.raises(mod.GitHubAPIError, match="Rate limit exceeded"):
            fetcher._make_request("GET", "https://api.github.com/test")

    def test_make_request_403_forbidden(self, monkeypatch):
        """Test 403 forbidden error."""
        fetcher = mod.GitHubSBOMFetcher("test-token")

        def handler(url, kwargs):
            return FakeResponse(403, text="access forbidden")

        monkeypatch.setattr(fetcher.session, "request", handler)

        with pytest.raises(mod.GitHubAPIError, match="Access forbidden"):
            fetcher._make_request("GET", "https://api.github.com/test")

    def test_make_request_404(self, monkeypatch):
        """Test 404 not found error."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        
        def mock_request(method, url, **kwargs):
            return FakeResponse(404, text="not found")
        
        monkeypatch.setattr(fetcher.session, 'request', mock_request)
        
        with pytest.raises(mod.GitHubAPIError, match="Not found"):
            fetcher._make_request("GET", "https://api.github.com/test")

    def test_make_request_422(self, monkeypatch):
        """Test 422 unprocessable entity error."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        
        def handler(url, kwargs):
            return FakeResponse(422, text="unprocessable entity")
        
        monkeypatch.setattr(fetcher, "_make_request", handler)
        
        with pytest.raises(mod.GitHubAPIError, match="API error 422"):
            fetcher._make_request("GET", "https://api.github.com/test")

    def test_make_request_500(self, monkeypatch):
        """Test 500 server error."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        
        def handler(url, kwargs):
            return FakeResponse(500, text="server error")
        
        monkeypatch.setattr(fetcher, "_make_request", handler)
        
        with pytest.raises(mod.GitHubAPIError, match="API error 500"):
            fetcher._make_request("GET", "https://api.github.com/test")

    def test_get_sbom_success(self, monkeypatch):
        """Test successful SBOM retrieval."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = create_sample_sbom()
        
        def handler(method, url, **kwargs):
            if "dependency-graph/sbom" in url:
                return FakeResponse(200, sbom_data)
            return FakeResponse(404)
        
        monkeypatch.setattr(fetcher, '_make_request', handler)
        
        result = fetcher.get_sbom("owner", "repo")
        assert result == sbom_data

    def test_get_sbom_missing_sbom_key(self, monkeypatch):
        """Test SBOM response missing sbom key."""
        fetcher = mod.GitHubSBOMFetcher("test-token")

        def handler(method, url, **kwargs):
            return FakeResponse(
                200,
                {"error": "Invalid format"},
            )

        monkeypatch.setattr(fetcher, "_make_request", handler)

        result = fetcher.get_sbom("owner", "repo")
        assert result is None

    def test_get_sbom_404_dependency_graph(self, monkeypatch, caplog):
        """Test that 404 for dependency-graph/sbom logs debug, not error."""
        import logging
        fetcher = mod.GitHubSBOMFetcher("test-token")
        
        def handler(method, url, **kwargs):
            if "/dependency-graph/sbom" in url:
                return FakeResponse(404, text="Not found")
            return FakeResponse(404)
        
        monkeypatch.setattr(fetcher, '_make_request', handler)
        
        # Capture logs
        with caplog.at_level(logging.DEBUG):
            result = fetcher.get_sbom("substack", "minimist")
        
        assert result is None
        # Should log debug message, not error
        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        error_messages = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        
        assert any("does not have dependency graph SBOM feature enabled" in msg for msg in debug_messages)
        assert not any("Failed to fetch SBOM" in msg for msg in error_messages)

    def test_get_sbom_404_other_endpoint(self, monkeypatch, caplog):
        """Test that 404 for non-dependency-graph endpoints still logs error."""
        import logging
        fetcher = mod.GitHubSBOMFetcher("test-token")
        
        def handler(method, url, **kwargs):
            return FakeResponse(404, text="Not found")
        
        monkeypatch.setattr(fetcher, '_make_request', handler)
        
        # Capture logs
        with caplog.at_level(logging.DEBUG):
            result = fetcher.get_sbom("nonexistent", "repo")
        
        assert result is None
        # Should log error message
        error_messages = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        assert any("Failed to fetch SBOM" in msg for msg in error_messages)

    
    def test_npm_fallback_mechanism(self, monkeypatch):
        """Test that npm fallback mechanism works when old version points to non-existent repo."""
        import requests
        from unittest.mock import patch, MagicMock
        
        fetcher = mod.GitHubSBOMFetcher("test-token")
        
        # Mock npm registry response for old version (points to non-existent repo)
        old_version_response = MagicMock()
        old_version_response.status_code = 200
        old_version_response.json.return_value = {
            "repository": {
                "url": "git://github.com/substack/minimist.git"
            }
        }
        
        # Mock npm registry response for latest version (points to active repo)
        latest_version_response = MagicMock()
        latest_version_response.status_code = 200
        latest_version_response.json.return_value = {
            "repository": {
                "url": "git://github.com/minimistjs/minimist.git"
            }
        }
        
        # Mock GitHub API responses
        def mock_make_request(method, url, **kwargs):
            if "/repos/substack/minimist" in url:
                # Simulate 404 for non-existent repo
                raise mod.GitHubAPIError("Not found: https://api.github.com/repos/substack/minimist")
            elif "/repos/minimistjs/minimist" in url:
                # Simulate successful repo check
                return FakeResponse(200, {"name": "minimist"})
            return FakeResponse(404)
        
        with patch('requests.get') as mock_get:
            # Configure mock to return different responses for different URLs
            def get_side_effect(url, **kwargs):
                if "minimist/0.0.8" in url:
                    return old_version_response
                elif "minimist/latest" in url:
                    return latest_version_response
                return MagicMock(status_code=404)
            
            mock_get.side_effect = get_side_effect
            monkeypatch.setattr(fetcher, '_make_request', mock_make_request)
            
            # Test the fallback mechanism
            result = fetcher._get_github_repo_from_npm("minimist", "0.0.8")
            
            # Should fallback to minimistjs/minimist
            assert result == ("minimistjs", "minimist"), f"Expected minimistjs/minimist, got {result}"
    
    def test_get_all_repositories(self, monkeypatch):
        """Test getting all repositories."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        repos = [
            {"name": "repo1", "owner": {"login": "owner1"}, "archived": False},
            {"name": "repo2", "owner": {"login": "owner2"}, "archived": True},
        ]
        
        def handler(method, url, **kwargs):
            if "/user/repos" in url:
                return FakeResponse(200, repos)
            return FakeResponse(404)
        
        monkeypatch.setattr(fetcher, '_make_request', handler)
        
        result = fetcher.get_all_repositories()
        assert len(result) == 1  # Only non-archived
        assert result[0] == ("owner1", "repo1")

    def test_get_all_repositories_empty(self, monkeypatch):
        """Test getting repositories when none exist."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        
        def handler(method, url, **kwargs):
            if "/user/repos" in url:
                return FakeResponse(200, [])
            return FakeResponse(404)
        
        monkeypatch.setattr(fetcher, '_make_request', handler)
        
        result = fetcher.get_all_repositories()
        assert result == []

    def test_get_github_repo_from_npm_success(
        self, monkeypatch
    ):
        """Test successful GitHub repo extraction from npm."""
        import requests
        
        fetcher = mod.GitHubSBOMFetcher("test-token")
        npm_response = create_npm_registry_response("git+https://github.com/owner/repo.git")
        
        def handler(url, **kwargs):
            if "registry.npmjs.org" in url:
                return FakeResponse(200, npm_response)
            return FakeResponse(404)
        
        monkeypatch.setattr(requests, "get", handler)
        
        result = fetcher._get_github_repo_from_npm("package", "1.0.0")
        assert result == ("owner", "repo")

    def test_get_github_repo_from_npm_ssh_url(
        self, monkeypatch
    ):
        """Test GitHub repo extraction from npm SSH URL."""
        import requests
        
        fetcher = mod.GitHubSBOMFetcher("test-token")
        npm_response = create_npm_registry_response(
            "git@github.com:owner/repo.git"
        )
        
        def handler(url, **kwargs):
            if "registry.npmjs.org" in url:
                return FakeResponse(200, npm_response)
            return FakeResponse(404)
        
        monkeypatch.setattr(requests, "get", handler)
        
        result = fetcher._get_github_repo_from_npm("package", "1.0.0")
        assert result == ("owner", "repo")

    def test_get_github_repo_from_npm_no_repository(
        self, monkeypatch
    ):
        """Test npm package with no repository field."""
        import requests
        
        fetcher = mod.GitHubSBOMFetcher("test-token")
        npm_response = {"name": "test-package", "version": "1.0.0"}
        
        def handler(url, **kwargs):
            if "registry.npmjs.org" in url:
                return FakeResponse(200, npm_response)
            return FakeResponse(404)
        
        monkeypatch.setattr(requests, "get", handler)
        
        result = fetcher._get_github_repo_from_npm("package", "1.0.0")
        assert result is None

    def test_get_github_repo_from_npm_not_github(
        self, monkeypatch
    ):
        """Test npm package not hosted on GitHub."""
        import requests
        
        fetcher = mod.GitHubSBOMFetcher("test-token")
        npm_response = create_npm_registry_response(
            "git+https://gitlab.com/owner/repo.git"
        )
        
        def handler(url, **kwargs):
            if "registry.npmjs.org" in url:
                return FakeResponse(200, npm_response)
            return FakeResponse(404)
        
        monkeypatch.setattr(requests, "get", handler)
        
        result = fetcher._get_github_repo_from_npm("package", "1.0.0")
        assert result is None

    def test_get_github_repo_from_npm_invalid_response(
        self, monkeypatch
    ):
        """Test npm registry response with invalid JSON."""
        import requests
        
        fetcher = mod.GitHubSBOMFetcher("test-token")

        def handler(url, **kwargs):
            class BadResponse:
                def json(self):
                    raise ValueError("bad json")
                status_code = 200

            return BadResponse()

        monkeypatch.setattr(requests, "get", handler)
        
        result = fetcher._get_github_repo_from_npm("package", "1.0.0")
        assert result is None

    def test_extract_dependencies_npm_packages(self, monkeypatch):
        """Test extracting dependencies from npm packages."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = create_sample_sbom()
        
        def handler(package_name, version):
            if package_name == "express":
                return ("expressjs", "express")
            return None
        
        monkeypatch.setattr(fetcher, "_get_github_repo_from_npm", handler)
        
        dependencies = fetcher.extract_dependencies(sbom_data, "tedg-dev", "beatBot")
        assert len(dependencies) == 1
        assert dependencies[0].owner == "expressjs"
        assert dependencies[0].repo == "express"
        assert dependencies[0].version == "4.18.0"

    def test_extract_dependencies_no_packages(self):
        """Test extracting dependencies with no packages."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = {"sbom": {"packages": []}}
        
        dependencies = fetcher.extract_dependencies(sbom_data, "owner", "repo")
        assert dependencies == []

    def test_extract_dependencies_invalid_sbom(self):
        """Test extracting dependencies from invalid SBOM."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = {"invalid": "data"}
        
        dependencies = fetcher.extract_dependencies(sbom_data, "owner", "repo")
        assert dependencies == []

    def test_save_sbom(self, tmp_path):
        """Test SBOM file saving."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = create_sample_sbom()
        
        result = fetcher.save_sbom(sbom_data, "owner", "repo", str(tmp_path))
        assert result is True
        
        # Check file was created
        expected_file = tmp_path / "owner_repo_sbom.json"
        assert expected_file.exists()
        
        # Check file content
        with open(expected_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        assert saved_data == sbom_data

    def test_save_sbom_no_version(self, tmp_path):
        """Test saving SBOM without version."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = create_sample_sbom()
        
        result = fetcher.save_sbom(sbom_data, "owner", "repo", str(tmp_path))
        
        # Check file was created with name including version
        expected_file = tmp_path / "owner_repo_1.0.0_sbom.json"
        assert expected_file.exists()

    def test_save_sbom_atomic_write(self, tmp_path):
        """Test atomic write behavior."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = create_sample_sbom()
        
        result = fetcher.save_sbom(sbom_data, "owner", "repo", str(tmp_path))
        
        expected_file = tmp_path / "owner_repo_1.0.0_sbom.json"
        assert expected_file.exists()
        assert result is True


class TestMainFunction:
    """Test main function."""

    def test_main_success(self, monkeypatch, tmp_path):
        """Test successful main execution."""
        key_path = write_key(tmp_path, "test-token")
        sbom_data = create_sample_sbom()
        
        def session_handler(method, url, **kwargs):
            if "repos/tedg-dev/beatBot/dependency-graph/sbom" in url:
                return FakeResponse(200, sbom_data)
            elif "repos/expressjs/express/dependency-graph/sbom" in url:
                # Return empty SBOM for dependency
                return FakeResponse(200, {"sbom": {}})
            return FakeResponse(404)
        
        def npm_handler(url, **kwargs):
            if "registry.npmjs.org" in url:
                npm_response = create_npm_registry_response("git+https://github.com/expressjs/express.git")
                return FakeResponse(200, npm_response)
            return FakeResponse(404)
        
        monkeypatch.setattr(mod.requests, "Session", lambda: FakeSession(session_handler))
        monkeypatch.setattr(mod.requests, "get", npm_handler)
        
        rc = mod.main(["--key-file", key_path, "--output-dir", str(tmp_path)])
        assert rc == 0
        
        # Check output structure
        export_dirs = list(tmp_path.glob("sbom_export_*"))
        assert len(export_dirs) == 1
        
        repo_dir = export_dirs[0] / "tedg-dev_beatBot"
        assert repo_dir.exists()
        assert (repo_dir / "tedg-dev_beatBot.json").exists()
        
        deps_dir = repo_dir / "dependencies"
        assert deps_dir.exists()
        assert len(list(deps_dir.glob("*.json"))) > 0

    def test_main_invalid_key_file(self, tmp_path, capsys):
        """Test main with invalid key file."""
        key_path = tmp_path / "invalid.json"
        key_path.write_text("invalid json")
        
        rc = mod.main(["--key-file", str(key_path), "--output-dir", str(tmp_path)])
        assert rc == 1
        assert "Failed to load credentials" in capsys.readouterr().err

    def test_main_missing_key_file(self, tmp_path, capsys):
        """Test main with missing key file."""
        rc = mod.main(["--key-file", "missing.json", "--output-dir", str(tmp_path)])
        assert rc == 1
        assert "Failed to load credentials" in capsys.readouterr().err

    def test_main_no_token(self, tmp_path, capsys):
        """Test main with no token in key file."""
        key_path = tmp_path / "keys.json"
        key_path.write_text(json.dumps({"username": "user"}))
        
        rc = mod.main(["--key-file", key_path, "--output-dir", str(tmp_path)])
        assert rc == 1
        assert "No valid GitHub token found" in capsys.readouterr().err

    def test_main_debug_flag(self, tmp_path):
        """Test main with debug flag."""
        key_path = write_key(tmp_path, "test-token")
        
        def handler(url, kwargs):
            return FakeResponse(404)
        
        with patch("mod.requests.Session", lambda: FakeSession(handler)):
            with patch('logging.basicConfig') as mock_config:
                rc = mod.main(["--key-file", key_path, "--output-dir", str(tmp_path), "--debug"])
                mock_config.assert_called_once()
                call_args = mock_config.call_args
                assert call_args[1]['level'] == 10  # DEBUG level

    def test_main_sbom_fetch_failure(self, monkeypatch, tmp_path, capsys):
        """Test main when SBOM fetch fails."""
        key_path = write_key(tmp_path, "test-token")
        
        def handler(url, kwargs):
            if "dependency-graph/sbom" in url:
                return FakeResponse(404)
            return FakeResponse(404)
        
        monkeypatch.setattr(mod.requests, "Session", lambda: FakeSession(handler))
        
        rc = mod.main(["--key-file", key_path, "--output-dir", str(tmp_path)])
        assert rc == 1
        assert "No SBOM data found" in capsys.readouterr().err

    def test_main_dependency_errors(self, monkeypatch, tmp_path):
        """Test main with some dependency errors."""
        key_path = write_key(tmp_path, "test-token")
        sbom_data = create_sample_sbom()
        
        call_count = {"sbom": 0, "npm": 0}
        
        def handler(url, kwargs):
            if "dependency-graph/sbom" in url:
                call_count["sbom"] += 1
                if call_count["sbom"] == 1:
                    return FakeResponse(200, sbom_data)
                return FakeResponse(404)
            if "registry.npmjs.org" in url:
                call_count["npm"] += 1
                if call_count["npm"] == 1:
                    npm_response = create_npm_registry_response("git+https://github.com/expressjs/express.git")
                    return FakeResponse(200, npm_response)
                return FakeResponse(404)
            return FakeResponse(404)
        
        monkeypatch.setattr(mod.requests, "Session", lambda: FakeSession(handler))
        
        rc = mod.main(["--key-file", key_path, "--output-dir", str(tmp_path)])
        assert rc == 0  # Should still succeed with partial failures

    def test_main_unexpected_error(self, monkeypatch, tmp_path, capsys):
        """Test main with unexpected error."""
        key_path = write_key(tmp_path, "test-token")
        
        def handler(url, kwargs):
            raise Exception("Unexpected error")
        
        monkeypatch.setattr(mod.requests, "Session", lambda: FakeSession(handler))
        
        rc = mod.main(["--key-file", key_path, "--output-dir", str(tmp_path)])
        assert rc == 1
        assert "Unexpected error" in capsys.readouterr().err

    def test_main_default_output_dir(self, tmp_path):
        """Test main with default output directory."""
        key_path = write_key(tmp_path, "test-token")
        
        def handler(url, kwargs):
            return FakeResponse(404)
        
        with patch("mod.requests.Session", lambda: FakeSession(handler)):
            with patch("os.makedirs") as mock_makedirs:
                rc = mod.main(["--key-file", key_path])
                mock_makedirs.assert_called_with("sboms", exist_ok=True)

    def test_main_help(self, capsys):
        """Test main help output."""
        with patch("sys.exit") as mock_exit:
            rc = mod.main(["--help"])
            mock_exit.assert_called_with(0)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_sbom_packages(self, monkeypatch):
        """Test with empty packages list."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = {"sbom": {"packages": [], "relationships": []}}
        
        dependencies = fetcher.extract_dependencies(sbom_data, "owner", "repo")
        assert dependencies == []

    def test_malformed_purl(self, monkeypatch):
        """Test with malformed purl."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = {
            "sbom": {
                "packages": [
                    {
                        "name": "test",
                        "SPDXID": "SPDXRef-Package-test",
                        "versionInfo": "1.0.0",
                        "externalRefs": [
                            {
                                "referenceCategory": "PACKAGE-MANAGER",
                                "referenceType": "purl",
                                "referenceLocator": "invalid-purl"
                            }
                        ]
                    }
                ]
            }
        }
        
        dependencies = fetcher.extract_dependencies(sbom_data, "owner", "repo")
        assert dependencies == []

    def test_missing_external_refs(self, monkeypatch):
        """Test package without external refs."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = {
            "sbom": {
                "packages": [
                    {
                        "name": "test",
                        "SPDXID": "SPDXRef-Package-test",
                        "versionInfo": "1.0.0"
                    }
                ]
            }
        }
        
        dependencies = fetcher.extract_dependencies(sbom_data, "owner", "repo")
        assert dependencies == []

    def test_duplicate_dependencies(self, monkeypatch):
        """Test handling of duplicate dependencies."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = {
            "sbom": {
                "packages": [
                    {
                        "name": "pkg:npm/express",
                        "SPDXID": "SPDXRef-Package-express1",
                        "versionInfo": "4.18.0",
                        "externalRefs": [
                            {
                                "referenceCategory": "PACKAGE-MANAGER",
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/express@4.18.0"
                            }
                        ]
                    },
                    {
                        "name": "pkg:npm/express",
                        "SPDXID": "SPDXRef-Package-express2",
                        "versionInfo": "4.18.0",
                        "externalRefs": [
                            {
                                "referenceCategory": "PACKAGE-MANAGER",
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/express@4.18.0"
                            }
                        ]
                    }
                ]
            }
        }
        
        def handler(url, kwargs):
            if "registry.npmjs.org" in url:
                npm_response = create_npm_registry_response("git+https://github.com/expressjs/express.git")
                return FakeResponse(200, npm_response)
            return FakeResponse(404)
        
        monkeypatch.setattr(fetcher, "_get_github_repo_from_npm", handler)
        
        dependencies = fetcher.extract_dependencies(sbom_data, "owner", "repo")
        # Should deduplicate
        assert len(dependencies) == 1

    def test_very_long_repo_name(self, tmp_path):
        """Test with very long repository name."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = create_sample_sbom()
        
        long_owner = "a" * 50
        long_repo = "b" * 50
        
        result = fetcher.save_sbom(long_owner, long_repo, sbom_data, str(tmp_path))
        assert os.path.exists(result)

    def test_special_characters_in_repo_name(self, tmp_path):
        """Test with special characters in repository name."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = create_sample_sbom()
        
        # GitHub doesn't allow these, but test defensive programming
        special_owner = "owner-with-dash"
        special_repo = "repo_with_underscore"
        
        result = fetcher.save_sbom(special_owner, special_repo, sbom_data, str(tmp_path))
        assert os.path.exists(result)


class TestErrorRecovery:
    """Test error recovery and resilience."""

    def test_network_timeout(self, monkeypatch):
        """Test handling of network timeouts."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        
        def handler(url, kwargs):
            raise TimeoutError("Network timeout")
        
        monkeypatch.setattr(fetcher, "_make_request", handler)
        
        result = fetcher.get_sbom("owner", "repo")
        assert result is None

    def test_partial_npm_response(self, monkeypatch):
        """Test handling of partial npm responses."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        
        def handler(url, kwargs):
            if "registry.npmjs.org" in url:
                return FakeResponse(200, {"name": "package"})  # Missing repository field
            return FakeResponse(404)
        
        monkeypatch.setattr(fetcher, "_get_github_repo_from_npm", handler)
        
        result = fetcher._get_github_repo_from_npm("package", "1.0.0")
        assert result is None

    def test_json_decode_error(self, monkeypatch):
        """Test handling of JSON decode errors."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        
        def handler(url, kwargs):
            response = FakeResponse(200, text="invalid json")
            response.json = lambda: json.decoder.JSONDecodeError("Invalid JSON", "", 0)
            return response
        
        monkeypatch.setattr(fetcher, "_make_request", handler)
        
        with pytest.raises(mod.GitHubAPIError):
            fetcher.get_sbom("owner", "repo")

    def test_file_permission_error(self, tmp_path, monkeypatch):
        """Test handling of file permission errors."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = create_sample_sbom()
        
        # Mock open to raise permission error
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                fetcher.save_sbom("owner", "repo", sbom_data, str(tmp_path))

    def test_disk_full_error(self, tmp_path, monkeypatch):
        """Test handling of disk full errors."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = create_sample_sbom()
        
        # Mock write to raise OS error (disk full)
        with patch("json.dump", side_effect=OSError("No space left on device")):
            with pytest.raises(OSError):
                fetcher.save_sbom("owner", "repo", sbom_data, str(tmp_path))


class TestConcurrency:
    """Test concurrent access scenarios."""

    def test_concurrent_sbom_saves(self, tmp_path):
        """Test concurrent SBOM saves."""
        fetcher = mod.GitHubSBOMFetcher("test-token")
        sbom_data = create_sample_sbom()
        
        import threading
        results = []
        errors = []
        
        def save_sbom_thread(i):
            try:
                result = fetcher.save_sbom("owner", f"repo{i}", sbom_data, str(tmp_path))
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=save_sbom_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 5
        for result in results:
            assert os.path.exists(result)


if __name__ == "__main__":
    pytest.main([__file__])
