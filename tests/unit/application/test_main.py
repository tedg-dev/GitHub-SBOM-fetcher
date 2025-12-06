"""Comprehensive unit tests for main application - Complete Coverage."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from sbom_fetcher.application.main import (
    build_session,
    create_service,
    load_token,
    main,
)
from sbom_fetcher.domain.exceptions import TokenLoadError
from sbom_fetcher.infrastructure.config import Config


class TestLoadToken:
    """Tests for load_token function."""

    def test_load_token_github_token_key(self, tmp_path):
        """Test loading token with 'github_token' key."""
        key_file = tmp_path / "keys.json"
        key_file.write_text(json.dumps({"github_token": "test_token_123"}))

        token = load_token(key_file)

        assert token == "test_token_123"

    def test_load_token_token_key(self, tmp_path):
        """Test loading token with 'token' key."""
        key_file = tmp_path / "keys.json"
        key_file.write_text(json.dumps({"token": "test_token_456"}))

        token = load_token(key_file)

        assert token == "test_token_456"

    def test_load_token_accounts_format(self, tmp_path):
        """Test loading token from accounts array."""
        key_file = tmp_path / "keys.json"
        key_file.write_text(json.dumps({"accounts": [{"token": "test_token_789"}]}))

        token = load_token(key_file)

        assert token == "test_token_789"

    def test_load_token_file_not_found(self, tmp_path):
        """Test error when keys file doesn't exist."""
        key_file = tmp_path / "nonexistent.json"

        with pytest.raises(TokenLoadError, match="not found"):
            load_token(key_file)

    def test_load_token_invalid_json(self, tmp_path):
        """Test error with invalid JSON."""
        key_file = tmp_path / "keys.json"
        key_file.write_text("{ invalid json }")

        with pytest.raises(TokenLoadError, match="Invalid JSON"):
            load_token(key_file)

    def test_load_token_no_token_found(self, tmp_path):
        """Test error when no token key found."""
        key_file = tmp_path / "keys.json"
        key_file.write_text(json.dumps({"other_key": "value"}))

        with pytest.raises(TokenLoadError, match="No GitHub token found"):
            load_token(key_file)

    def test_load_token_empty_accounts(self, tmp_path):
        """Test with empty accounts array."""
        key_file = tmp_path / "keys.json"
        key_file.write_text(json.dumps({"accounts": []}))

        with pytest.raises(TokenLoadError, match="No GitHub token found"):
            load_token(key_file)

    def test_load_token_priority_github_token(self, tmp_path):
        """Test github_token takes priority over token."""
        key_file = tmp_path / "keys.json"
        key_file.write_text(
            json.dumps({"github_token": "priority_token", "token": "secondary_token"})
        )

        token = load_token(key_file)

        assert token == "priority_token"


class TestBuildSession:
    """Tests for build_session function."""

    def test_build_session_creates_session(self):
        """Test building session with token."""
        token = "test_token_123"

        session = build_session(token)

        assert isinstance(session, requests.Session)
        assert session.headers["Authorization"] == "token test_token_123"
        assert session.headers["Accept"] == "application/vnd.github+json"
        assert session.headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert "github-sbom-api-fetcher" in session.headers["User-Agent"]

    def test_build_session_headers(self):
        """Test all required headers are set."""
        token = "my_token"

        session = build_session(token)

        required_headers = {
            "Authorization",
            "Accept",
            "X-GitHub-Api-Version",
            "User-Agent",
        }
        assert required_headers.issubset(session.headers.keys())


class TestCreateService:
    """Tests for create_service function."""

    def test_create_service(self):
        """Test creating service with dependencies."""
        config = Config()
        token = "test_token"

        with tempfile.TemporaryDirectory() as tmpdir:
            config.output_dir = Path(tmpdir)
            service = create_service(config, token)

            assert service is not None
            assert service._config == config
            assert service._github_client is not None
            assert service._mapper_factory is not None
            assert service._repository is not None
            assert service._reporter is not None

    def test_create_service_components(self):
        """Test all service components are created."""
        config = Config()
        token = "test_token"

        with tempfile.TemporaryDirectory() as tmpdir:
            config.output_dir = Path(tmpdir)
            service = create_service(config, token)

            # Verify all components exist
            assert hasattr(service, "_github_client")
            assert hasattr(service, "_mapper_factory")
            assert hasattr(service, "_repository")
            assert hasattr(service, "_reporter")
            assert hasattr(service, "_parser")


class TestMain:
    """Tests for main function."""

    @patch("sbom_fetcher.application.main.create_service")
    @patch("sbom_fetcher.application.main.build_session")
    @patch("sbom_fetcher.application.main.load_token")
    @patch("sbom_fetcher.application.main.Config")
    @patch("sbom_fetcher.application.cli.parse_arguments")
    @patch("sbom_fetcher.application.cli.setup_logging")
    def test_main_success(
        self,
        mock_setup_logging,
        mock_parse_args,
        mock_config_class,
        mock_load_token,
        mock_build_session,
        mock_create_service,
    ):
        """Test successful main execution."""
        # Setup mocks
        mock_args = Mock()
        mock_args.debug = False
        mock_args.output_dir = None
        mock_args.key_file = None
        mock_args.gh_user = "test-user"
        mock_args.gh_repo = "test-repo"
        mock_parse_args.return_value = mock_args

        mock_config = Mock()
        mock_config.key_file = Path("keys.json")
        mock_config_class.load.return_value = mock_config

        mock_load_token.return_value = "test_token"
        mock_session = Mock()
        mock_build_session.return_value = mock_session

        mock_service = Mock()
        mock_result = Mock()
        mock_service.fetch_all_sboms.return_value = mock_result
        mock_create_service.return_value = mock_service

        # Execute
        exit_code = main()

        # Verify
        assert exit_code == 0
        mock_setup_logging.assert_called_once_with(False)
        mock_load_token.assert_called_once()
        mock_build_session.assert_called_once_with("test_token")
        mock_service.fetch_all_sboms.assert_called_once_with("test-user", "test-repo", mock_session)

    @patch("sbom_fetcher.application.main.load_token")
    @patch("sbom_fetcher.application.main.Config")
    @patch("sbom_fetcher.application.cli.parse_arguments")
    @patch("sbom_fetcher.application.cli.setup_logging")
    def test_main_token_load_error(
        self, mock_setup_logging, mock_parse_args, mock_config_class, mock_load_token
    ):
        """Test main handles TokenLoadError."""
        mock_args = Mock()
        mock_args.debug = False
        mock_args.output_dir = None
        mock_args.key_file = None
        mock_parse_args.return_value = mock_args

        mock_config = Mock()
        mock_config.key_file = Path("keys.json")
        mock_config_class.load.return_value = mock_config

        mock_load_token.side_effect = TokenLoadError("Token not found")

        exit_code = main()

        assert exit_code == 1

    @patch("sbom_fetcher.application.main.Config")
    @patch("sbom_fetcher.application.cli.parse_arguments")
    @patch("sbom_fetcher.application.cli.setup_logging")
    def test_main_keyboard_interrupt(
        self, mock_setup_logging, mock_parse_args, mock_config_class
    ):
        """Test main handles KeyboardInterrupt."""
        mock_args = Mock()
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_config_class.load.side_effect = KeyboardInterrupt()

        exit_code = main()

        assert exit_code == 130

    @patch("sbom_fetcher.application.main.Config")
    @patch("sbom_fetcher.application.cli.parse_arguments")
    @patch("sbom_fetcher.application.cli.setup_logging")
    def test_main_general_exception(self, mock_setup_logging, mock_parse_args, mock_config_class):
        """Test main handles general exceptions."""
        mock_args = Mock()
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_config_class.load.side_effect = Exception("General error")

        exit_code = main()

        assert exit_code == 1

    @patch("sbom_fetcher.application.main.create_service")
    @patch("sbom_fetcher.application.main.build_session")
    @patch("sbom_fetcher.application.main.load_token")
    @patch("sbom_fetcher.application.main.Config")
    @patch("sbom_fetcher.application.cli.parse_arguments")
    @patch("sbom_fetcher.application.cli.setup_logging")
    def test_main_with_custom_paths(
        self,
        mock_setup_logging,
        mock_parse_args,
        mock_config_class,
        mock_load_token,
        mock_build_session,
        mock_create_service,
    ):
        """Test main with custom output and key file paths."""
        mock_args = Mock()
        mock_args.debug = True
        mock_args.output_dir = "/custom/output"
        mock_args.key_file = "/custom/keys.json"
        mock_args.gh_user = "user"
        mock_args.gh_repo = "repo"
        mock_parse_args.return_value = mock_args

        mock_config = Mock()
        mock_config.key_file = Path("keys.json")
        mock_config_class.load.return_value = mock_config

        mock_load_token.return_value = "token"
        mock_session = Mock()
        mock_build_session.return_value = mock_session

        mock_service = Mock()
        mock_service.fetch_all_sboms.return_value = Mock()
        mock_create_service.return_value = mock_service

        exit_code = main()

        assert exit_code == 0
        assert mock_config.output_dir == Path("/custom/output")
        assert mock_config.key_file == Path("/custom/keys.json")
        mock_setup_logging.assert_called_once_with(True)
