"""Comprehensive unit tests for configuration - Complete Coverage."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from sbom_fetcher.domain.exceptions import InvalidConfigError
from sbom_fetcher.infrastructure.config import Config


class TestConfigDefaults:
    """Tests for default configuration values."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()

        assert config.github_api_url == "https://api.github.com"
        assert config.npm_registry_url == "https://registry.npmjs.org"
        assert config.pypi_api_url == "https://pypi.org/pypi"
        assert config.output_dir == Path("sboms")
        assert config.key_file == Path("keys.json")
        assert config.max_retries == 2
        assert config.timeout == 30
        assert config.rate_limit_pause == 0.5
        assert config.log_level == "INFO"

    def test_config_with_custom_values(self):
        """Test creating config with custom values."""
        config = Config(
            github_api_url="https://custom.github.com",
            npm_registry_url="https://custom.npm.org",
            timeout=45,
            max_retries=5,
            log_level="DEBUG",
        )

        assert config.github_api_url == "https://custom.github.com"
        assert config.npm_registry_url == "https://custom.npm.org"
        assert config.timeout == 45
        assert config.max_retries == 5
        assert config.log_level == "DEBUG"


class TestConfigFromEnv:
    """Tests for loading configuration from environment variables."""

    def test_from_env_no_vars_set(self):
        """Test from_env with no environment variables set."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_env()

            # Should use defaults
            assert config.github_api_url == "https://api.github.com"
            assert config.timeout == 30

    def test_from_env_github_api_url(self):
        """Test loading GitHub API URL from environment."""
        with patch.dict(os.environ, {"SBOM_FETCHER_GITHUB_API_URL": "https://custom.github.com"}):
            config = Config.from_env()

            assert config.github_api_url == "https://custom.github.com"

    def test_from_env_npm_registry_url(self):
        """Test loading NPM registry URL from environment."""
        with patch.dict(os.environ, {"SBOM_FETCHER_NPM_REGISTRY_URL": "https://custom.npm.org"}):
            config = Config.from_env()

            assert config.npm_registry_url == "https://custom.npm.org"

    def test_from_env_pypi_api_url(self):
        """Test loading PyPI API URL from environment."""
        with patch.dict(os.environ, {"SBOM_FETCHER_PYPI_API_URL": "https://custom.pypi.org"}):
            config = Config.from_env()

            assert config.pypi_api_url == "https://custom.pypi.org"

    def test_from_env_output_dir(self):
        """Test loading output directory from environment."""
        with patch.dict(os.environ, {"SBOM_FETCHER_OUTPUT_DIR": "/custom/path"}):
            config = Config.from_env()

            assert config.output_dir == Path("/custom/path")

    def test_from_env_key_file(self):
        """Test loading key file from environment."""
        with patch.dict(os.environ, {"SBOM_FETCHER_KEY_FILE": "/path/to/keys.json"}):
            config = Config.from_env()

            assert config.key_file == Path("/path/to/keys.json")

    def test_from_env_max_retries(self):
        """Test loading max retries from environment."""
        with patch.dict(os.environ, {"SBOM_FETCHER_MAX_RETRIES": "5"}):
            config = Config.from_env()

            assert config.max_retries == 5

    def test_from_env_timeout(self):
        """Test loading timeout from environment."""
        with patch.dict(os.environ, {"SBOM_FETCHER_TIMEOUT": "60"}):
            config = Config.from_env()

            assert config.timeout == 60

    def test_from_env_rate_limit_pause(self):
        """Test loading rate limit pause from environment."""
        with patch.dict(os.environ, {"SBOM_FETCHER_RATE_LIMIT_PAUSE": "1.5"}):
            config = Config.from_env()

            assert config.rate_limit_pause == 1.5

    def test_from_env_log_level(self):
        """Test loading log level from environment."""
        with patch.dict(os.environ, {"SBOM_FETCHER_LOG_LEVEL": "DEBUG"}):
            config = Config.from_env()

            assert config.log_level == "DEBUG"

    def test_from_env_multiple_vars(self):
        """Test loading multiple environment variables."""
        with patch.dict(
            os.environ,
            {
                "SBOM_FETCHER_GITHUB_API_URL": "https://custom.github.com",
                "SBOM_FETCHER_TIMEOUT": "60",
                "SBOM_FETCHER_LOG_LEVEL": "DEBUG",
                "SBOM_FETCHER_MAX_RETRIES": "5",
            },
        ):
            config = Config.from_env()

            assert config.github_api_url == "https://custom.github.com"
            assert config.timeout == 60
            assert config.log_level == "DEBUG"
            assert config.max_retries == 5

    def test_from_env_invalid_int(self):
        """Test error handling for invalid integer value."""
        with patch.dict(os.environ, {"SBOM_FETCHER_MAX_RETRIES": "invalid"}):
            with pytest.raises(InvalidConfigError, match="Invalid value"):
                Config.from_env()

    def test_from_env_invalid_float(self):
        """Test error handling for invalid float value."""
        with patch.dict(os.environ, {"SBOM_FETCHER_RATE_LIMIT_PAUSE": "invalid"}):
            with pytest.raises(InvalidConfigError, match="Invalid value"):
                Config.from_env()


class TestConfigLoad:
    """Tests for load method."""

    def test_load_no_config_file(self):
        """Test load with no config file."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config.load()

            assert config.github_api_url == "https://api.github.com"
            assert config.timeout == 30

    def test_load_with_env_vars(self):
        """Test load respects environment variables."""
        with patch.dict(
            os.environ,
            {
                "SBOM_FETCHER_GITHUB_API_URL": "https://custom.github.com",
                "SBOM_FETCHER_TIMEOUT": "60",
            },
        ):
            config = Config.load()

            assert config.github_api_url == "https://custom.github.com"
            assert config.timeout == 60

    def test_load_with_config_file_parameter(self):
        """Test load accepts config_file parameter (not yet implemented)."""
        config_file = Path("/path/to/config.yaml")
        config = Config.load(config_file=config_file)

        # Should still work, just ignores the file for now
        assert isinstance(config, Config)


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_validate_valid_config(self):
        """Test validation passes for valid config."""
        config = Config()
        config.validate()  # Should not raise

    def test_validate_negative_max_retries(self):
        """Test validation fails for negative max_retries."""
        config = Config(max_retries=-1)

        with pytest.raises(InvalidConfigError, match="max_retries must be non-negative"):
            config.validate()

    def test_validate_zero_timeout(self):
        """Test validation fails for zero timeout."""
        config = Config(timeout=0)

        with pytest.raises(InvalidConfigError, match="timeout must be positive"):
            config.validate()

    def test_validate_negative_timeout(self):
        """Test validation fails for negative timeout."""
        config = Config(timeout=-10)

        with pytest.raises(InvalidConfigError, match="timeout must be positive"):
            config.validate()

    def test_validate_negative_rate_limit_pause(self):
        """Test validation fails for negative rate_limit_pause."""
        config = Config(rate_limit_pause=-1.0)

        with pytest.raises(InvalidConfigError, match="rate_limit_pause must be non-negative"):
            config.validate()

    def test_validate_zero_rate_limit_pause_allowed(self):
        """Test validation allows zero rate_limit_pause."""
        config = Config(rate_limit_pause=0.0)
        config.validate()  # Should not raise

    def test_validate_zero_max_retries_allowed(self):
        """Test validation allows zero max_retries."""
        config = Config(max_retries=0)
        config.validate()  # Should not raise
