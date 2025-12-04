"""Configuration management."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..domain.exceptions import InvalidConfigError


@dataclass
class Config:
    """Application configuration with defaults."""

    # API endpoints
    github_api_url: str = "https://api.github.com"
    npm_registry_url: str = "https://registry.npmjs.org"
    pypi_api_url: str = "https://pypi.org/pypi"

    # File paths
    output_dir: Path = field(default_factory=lambda: Path("sboms_api"))
    key_file: Path = field(default_factory=lambda: Path("keys.json"))

    # Behavior
    max_retries: int = 2
    timeout: int = 30
    rate_limit_pause: float = 0.5

    # Logging
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        kwargs = {}

        # Map environment variables to config fields
        env_mappings = {
            "SBOM_FETCHER_GITHUB_API_URL": ("github_api_url", str),
            "SBOM_FETCHER_NPM_REGISTRY_URL": ("npm_registry_url", str),
            "SBOM_FETCHER_PYPI_API_URL": ("pypi_api_url", str),
            "SBOM_FETCHER_OUTPUT_DIR": ("output_dir", Path),
            "SBOM_FETCHER_KEY_FILE": ("key_file", Path),
            "SBOM_FETCHER_MAX_RETRIES": ("max_retries", int),
            "SBOM_FETCHER_TIMEOUT": ("timeout", int),
            "SBOM_FETCHER_RATE_LIMIT_PAUSE": ("rate_limit_pause", float),
            "SBOM_FETCHER_LOG_LEVEL": ("log_level", str),
        }

        for env_var, (field_name, field_type) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    if field_type == Path:
                        kwargs[field_name] = Path(value)
                    elif field_type == int:
                        kwargs[field_name] = int(value)
                    elif field_type == float:
                        kwargs[field_name] = float(value)
                    else:
                        kwargs[field_name] = value
                except (ValueError, TypeError) as e:
                    raise InvalidConfigError(f"Invalid value for {env_var}: {value}") from e

        return cls(**kwargs)

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> "Config":
        """
        Load configuration with precedence: env vars > defaults.

        Args:
            config_file: Optional config file (not implemented yet, for future use)

        Returns:
            Configured instance
        """
        # Start with env vars (which will use defaults if not set)
        config = cls.from_env()

        # Future: could load from YAML/TOML file here if config_file provided

        return config

    def validate(self) -> None:
        """Validate configuration values."""
        if self.max_retries < 0:
            raise InvalidConfigError("max_retries must be non-negative")
        if self.timeout <= 0:
            raise InvalidConfigError("timeout must be positive")
        if self.rate_limit_pause < 0:
            raise InvalidConfigError("rate_limit_pause must be non-negative")
