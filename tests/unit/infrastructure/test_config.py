"""Unit tests for configuration."""

import os
from unittest.mock import patch

from sbom_fetcher.infrastructure.config import Config


class TestConfig:
    """Tests for Config class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()

        assert config.github_api_url == "https://api.github.com"
        assert config.npm_registry_url == "https://registry.npmjs.org"
        assert config.pypi_api_url == "https://pypi.org/pypi"
        assert config.timeout == 30
        assert config.rate_limit_pause == 0.5
        assert config.log_level == "INFO"

    def test_config_with_env_vars(self):
        """Test configuration from environment variables."""
        with patch.dict(
            os.environ,
            {
                "SBOM_FETCHER_GITHUB_API_URL": "https://custom.github.com",
                "SBOM_FETCHER_TIMEOUT": "60",
                "SBOM_FETCHER_LOG_LEVEL": "DEBUG",
            },
        ):
            config = Config.from_env()

            assert config.github_api_url == "https://custom.github.com"
            assert config.timeout == 60
            assert config.log_level == "DEBUG"

    def test_config_with_custom_values(self):
        """Test creating config with custom values."""
        config = Config(github_api_url="https://test.github.com", timeout=45, log_level="WARNING")

        assert config.github_api_url == "https://test.github.com"
        assert config.timeout == 45
        assert config.log_level == "WARNING"

    def test_config_fields(self):
        """Test config has all required fields."""
        config = Config()

        assert hasattr(config, "github_api_url")
        assert hasattr(config, "npm_registry_url")
        assert hasattr(config, "pypi_api_url")
        assert hasattr(config, "timeout")
        assert hasattr(config, "max_retries")
        assert hasattr(config, "rate_limit_pause")

    def test_config_validation(self):
        """Test configuration validation."""
        config = Config()

        # Should have valid timeout
        assert config.timeout > 0
        assert config.max_retries >= 0

        # Should have valid URLs
        assert config.github_api_url.startswith("https://")
        assert config.npm_registry_url.startswith("https://")
        assert config.pypi_api_url.startswith("https://")
