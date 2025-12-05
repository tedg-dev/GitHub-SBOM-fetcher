"""Unit tests for configuration."""

import os
from unittest.mock import patch

from sbom_fetcher.infrastructure.config import Config


class TestConfig:
    """Tests for Config class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()

        assert config.github_api_base == "https://api.github.com"
        assert config.npm_registry_base == "https://registry.npmjs.org"
        assert config.pypi_registry_base == "https://pypi.org/pypi"
        assert config.timeout == 30
        assert config.rate_limit_pause == 0.5
        assert config.log_level == "INFO"

    def test_config_with_env_vars(self):
        """Test configuration from environment variables."""
        with patch.dict(os.environ, {
            "GITHUB_API_BASE": "https://custom.github.com",
            "TIMEOUT": "60",
            "LOG_LEVEL": "DEBUG"
        }):
            config = Config()

            assert config.github_api_base == "https://custom.github.com"
            assert config.timeout == 60
            assert config.log_level == "DEBUG"

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "github_api_base": "https://test.github.com",
            "timeout": 45,
            "log_level": "WARNING"
        }
        config = Config.from_dict(config_dict)

        assert config.github_api_base == "https://test.github.com"
        assert config.timeout == 45
        assert config.log_level == "WARNING"

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = Config()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "github_api_base" in config_dict
        assert "timeout" in config_dict
        assert config_dict["github_api_base"] == config.github_api_base

    def test_config_validation(self):
        """Test configuration validation."""
        config = Config()

        # Should have valid timeout
        assert config.timeout > 0

        # Should have valid URLs
        assert config.github_api_base.startswith("https://")
        assert config.npm_registry_base.startswith("https://")
        assert config.pypi_registry_base.startswith("https://")
