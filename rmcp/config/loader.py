"""
Configuration loading and management for RMCP.

This module implements hierarchical configuration loading with support for
multiple configuration sources in priority order:

1. **Command-line arguments** (highest priority)
2. **Environment variables** (``RMCP_*`` prefix)
3. **User configuration file** (``~/.rmcp/config.json``)
4. **System configuration file** (``/etc/rmcp/config.json``)
5. **Built-in defaults** (lowest priority)

Features:
    * Automatic environment variable mapping with ``RMCP_*`` prefix
    * JSON configuration file validation with schema
    * Type conversion and validation
    * Configuration caching for performance
    * Detailed error reporting with helpful messages

Environment Variable Mapping:
    All configuration options can be set via environment variables:

    * ``RMCP_HTTP_HOST`` → ``http.host``
    * ``RMCP_HTTP_PORT`` → ``http.port``
    * ``RMCP_R_TIMEOUT`` → ``r.timeout``
    * ``RMCP_LOG_LEVEL`` → ``logging.level``
    * ``RMCP_DEBUG`` → ``debug``

Configuration File Format:
    JSON files with nested structure matching the configuration model::

        {
          "http": {"host": "0.0.0.0", "port": 8000},
          "r": {"timeout": 180, "max_sessions": 20},
          "security": {"vfs_read_only": true},
          "logging": {"level": "DEBUG"},
          "debug": true
        }

Examples:
    Load configuration with custom file::

        loader = ConfigLoader()
        config = loader.load_config(config_file="/path/to/config.json")

    Load with environment variables::

        os.environ["RMCP_HTTP_PORT"] = "9000"
        os.environ["RMCP_DEBUG"] = "true"
        config = loader.load_config()

    Load with CLI overrides::

        config = loader.load_config(
            cli_overrides={"debug": True, "http": {"host": "0.0.0.0"}}
        )
"""

import copy
import json
import os
from pathlib import Path
from typing import Any

try:
    import jsonschema

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

from .defaults import CONFIG_FILE_LOCATIONS, DEFAULT_CONFIG, ENV_MAPPINGS
from .models import (
    HTTPConfig,
    LoggingConfig,
    PerformanceConfig,
    RConfig,
    RMCPConfig,
    SecurityConfig,
)
from .schema import CONFIG_SCHEMA


class ConfigError(Exception):
    """Configuration-related errors.

    Raised when configuration loading, validation, or parsing fails.
    Provides detailed error messages to help users fix configuration issues.
    """

    pass


class ConfigLoader:
    """Handles loading and merging configuration from multiple sources.

    The ConfigLoader implements the hierarchical configuration system for RMCP,
    automatically discovering and merging configuration from multiple sources
    in priority order.

    Features:
        * Configuration caching for performance
        * Automatic environment variable discovery
        * JSON schema validation
        * Detailed error reporting
        * Type conversion and validation

    Usage:
        The loader is typically used as a singleton to ensure consistent
        configuration across the application::

            loader = ConfigLoader()
            config = loader.load_config()

        For custom configuration scenarios::

            config = loader.load_config(
                config_file="/custom/path/config.json",
                cli_overrides={"debug": True}
            )
    """

    def __init__(self):
        """Initialize the configuration loader.

        Creates a new configuration loader with empty cache.
        The cache will be populated on first load_config() call.
        """
        self._config_cache: RMCPConfig | None = None

    def load_config(
        self,
        config_file: str | Path | None = None,
        overrides: dict[str, Any] | None = None,
        validate: bool = True,
    ) -> RMCPConfig:
        """
        Load configuration from all sources in priority order:
        1. Overrides (highest priority)
        2. Environment variables
        3. Specified config file or auto-discovered files
        4. Defaults (lowest priority)

        Args:
            config_file: Explicit config file path
            overrides: Dictionary of override values
            validate: Whether to validate against JSON schema

        Returns:
            Loaded and validated RMCPConfig instance
        """
        # Start with defaults
        config_dict = copy.deepcopy(DEFAULT_CONFIG)

        # Load from config file
        file_config = self._load_config_file(config_file)
        if file_config:
            config_dict = self._merge_config(config_dict, file_config)

        # Load from environment variables
        env_config = self._load_environment_config()
        if env_config:
            config_dict = self._merge_config(config_dict, env_config)

        # Apply overrides
        if overrides:
            config_dict = self._merge_config(config_dict, overrides)

        # Validate configuration
        if validate and JSONSCHEMA_AVAILABLE:
            self._validate_config(config_dict)

        # Convert to typed configuration object
        return self._dict_to_config(config_dict)

    def _load_config_file(
        self, config_file: str | Path | None = None
    ) -> dict[str, Any] | None:
        """Load configuration from JSON file."""
        config_paths = []

        if config_file:
            # Use explicitly specified file
            config_paths = [Path(config_file)]
        else:
            # Auto-discover config files
            config_paths = CONFIG_FILE_LOCATIONS

        for config_path in config_paths:
            if config_path.exists() and config_path.is_file():
                try:
                    with open(config_path, encoding="utf-8") as f:
                        config_data = json.load(f)
                    return config_data
                except (OSError, json.JSONDecodeError) as e:
                    if config_file:
                        # If explicitly specified, raise error
                        raise ConfigError(
                            f"Failed to load config file {config_path}: {e}"
                        )
                    # Otherwise, continue to next file
                    continue
            elif config_file:
                # If explicitly specified file doesn't exist, raise error
                raise ConfigError(f"Config file not found: {config_path}")

        return None

    def _load_environment_config(self) -> dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}

        for env_var, config_path in ENV_MAPPINGS.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                # Convert value to appropriate type
                converted_value = self._convert_env_value(env_var, env_value)
                self._set_nested_value(env_config, config_path, converted_value)

        return env_config

    def _convert_env_value(self, env_var: str, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        match env_var:
            case var if var.endswith(("_READ_ONLY", "_DEBUG", "_STDERR_OUTPUT")):
                # Boolean conversion
                return value.lower() in ("true", "1", "yes", "on")
            case var if var.endswith(
                ("_PORT", "_TIMEOUT", "_MAX_SESSIONS", "_MAX_WORKERS", "_MAX_FILE_SIZE")
            ):
                # Integer conversion
                try:
                    return int(value)
                except ValueError:
                    raise ConfigError(f"Invalid integer value for {env_var}: {value}")
            case var if var.endswith(("_ORIGINS", "_PATHS", "_MIME_TYPES")):
                # List conversion (comma-separated)
                return [item.strip() for item in value.split(",") if item.strip()]
            case _:
                # String value
                return value

    def _set_nested_value(self, config_dict: dict[str, Any], path: str, value: Any):
        """Set a nested dictionary value using dot notation."""
        keys = path.split(".")
        current = config_dict

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _merge_config(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = copy.deepcopy(base)

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_config(self, config_dict: dict[str, Any]):
        """Validate configuration against JSON schema."""
        try:
            jsonschema.validate(config_dict, CONFIG_SCHEMA)
        except jsonschema.ValidationError as e:
            raise ConfigError(f"Configuration validation failed: {e.message}")

    def _dict_to_config(self, config_dict: dict[str, Any]) -> RMCPConfig:
        """Convert configuration dictionary to typed RMCPConfig object."""
        try:
            http_config = HTTPConfig(**config_dict.get("http", {}))
            r_config = RConfig(**config_dict.get("r", {}))
            security_config = SecurityConfig(**config_dict.get("security", {}))
            performance_config = PerformanceConfig(**config_dict.get("performance", {}))
            logging_config = LoggingConfig(**config_dict.get("logging", {}))

            return RMCPConfig(
                http=http_config,
                r=r_config,
                security=security_config,
                performance=performance_config,
                logging=logging_config,
                debug=config_dict.get("debug", False),
            )
        except TypeError as e:
            raise ConfigError(f"Failed to create configuration object: {e}")


# Global configuration instance
_config_loader = ConfigLoader()
_global_config: RMCPConfig | None = None


def get_config(reload: bool = False) -> RMCPConfig:
    """
    Get the global RMCP configuration instance.

    Args:
        reload: Force reload configuration from sources

    Returns:
        Global RMCPConfig instance
    """
    global _global_config

    if _global_config is None or reload:
        _global_config = _config_loader.load_config()

    return _global_config


def load_config(
    config_file: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
    validate: bool = True,
) -> RMCPConfig:
    """
    Load a new configuration instance (does not affect global config).

    Args:
        config_file: Path to configuration file
        overrides: Configuration overrides
        validate: Whether to validate configuration

    Returns:
        New RMCPConfig instance
    """
    return _config_loader.load_config(config_file, overrides, validate)
