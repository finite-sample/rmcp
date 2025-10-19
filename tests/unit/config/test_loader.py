"""
Tests for configuration loading functionality.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from rmcp.config.loader import ConfigError, ConfigLoader
from rmcp.config.models import RMCPConfig


class TestConfigLoader:
    """Test configuration loading functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.loader = ConfigLoader()

    def test_load_defaults(self):
        """Test loading default configuration."""
        config = self.loader.load_config(validate=False)
        assert isinstance(config, RMCPConfig)
        assert config.http.host == "localhost"
        assert config.http.port == 8000
        assert config.r.timeout == 120

    def test_load_config_file(self, tmp_path):
        """Test loading configuration from file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "http": {"host": "0.0.0.0", "port": 9000},
            "r": {"timeout": 180},
            "logging": {"level": "DEBUG"},
        }
        config_file.write_text(json.dumps(config_data))

        config = self.loader.load_config(config_file=config_file, validate=False)
        assert config.http.host == "0.0.0.0"
        assert config.http.port == 9000
        assert config.r.timeout == 180
        assert config.logging.level == "DEBUG"

    def test_load_invalid_config_file(self, tmp_path):
        """Test loading invalid configuration file."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{invalid json")

        with pytest.raises(ConfigError, match="Failed to load config file"):
            self.loader.load_config(config_file=config_file)

    def test_load_nonexistent_config_file(self, tmp_path):
        """Test loading nonexistent configuration file."""
        config_file = tmp_path / "nonexistent.json"

        with pytest.raises(ConfigError, match="Config file not found"):
            self.loader.load_config(config_file=config_file)

    def test_environment_variables(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "RMCP_HTTP_HOST": "0.0.0.0",
            "RMCP_HTTP_PORT": "9000",
            "RMCP_R_TIMEOUT": "180",
            "RMCP_LOG_LEVEL": "DEBUG",
            "RMCP_DEBUG": "true",
        }

        with patch.dict(os.environ, env_vars):
            config = self.loader.load_config(validate=False)

        assert config.http.host == "0.0.0.0"
        assert config.http.port == 9000
        assert config.r.timeout == 180
        assert config.logging.level == "DEBUG"
        assert config.debug is True

    def test_environment_boolean_conversion(self):
        """Test boolean environment variable conversion."""
        test_cases = [
            ("true", True),
            ("false", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
            ("on", True),
            ("off", False),
            ("TRUE", True),
            ("FALSE", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"RMCP_DEBUG": env_value}):
                config = self.loader.load_config(validate=False)
                assert config.debug == expected, f"Failed for {env_value}"

    def test_environment_integer_conversion(self):
        """Test integer environment variable conversion."""
        with patch.dict(os.environ, {"RMCP_HTTP_PORT": "9000"}):
            config = self.loader.load_config(validate=False)
            assert config.http.port == 9000
            assert isinstance(config.http.port, int)

    def test_environment_invalid_integer(self):
        """Test invalid integer environment variable."""
        with patch.dict(os.environ, {"RMCP_HTTP_PORT": "invalid"}):
            with pytest.raises(ConfigError, match="Invalid integer value"):
                self.loader.load_config(validate=False)

    def test_environment_list_conversion(self):
        """Test list environment variable conversion."""
        with patch.dict(
            os.environ,
            {"RMCP_HTTP_CORS_ORIGINS": "http://localhost:3000,https://example.com"},
        ):
            config = self.loader.load_config(validate=False)
            assert config.http.cors_origins == [
                "http://localhost:3000",
                "https://example.com",
            ]

    def test_configuration_hierarchy(self, tmp_path):
        """Test configuration hierarchy (overrides)."""
        # Create config file
        config_file = tmp_path / "config.json"
        config_data = {
            "http": {"host": "file_host", "port": 8001},
            "r": {"timeout": 150},
        }
        config_file.write_text(json.dumps(config_data))

        # Set environment variables
        env_vars = {"RMCP_HTTP_HOST": "env_host", "RMCP_R_TIMEOUT": "200"}

        # Set overrides
        overrides = {"http": {"host": "override_host"}}

        with patch.dict(os.environ, env_vars):
            config = self.loader.load_config(
                config_file=config_file, overrides=overrides, validate=False
            )

        # Check hierarchy: overrides > env > file > defaults
        assert config.http.host == "override_host"  # Override wins
        assert config.http.port == 8001  # From file (no env/override)
        assert config.r.timeout == 200  # From env (no override)

    def test_merge_nested_config(self):
        """Test merging of nested configuration dictionaries."""
        base = {"http": {"host": "localhost", "port": 8000}, "r": {"timeout": 120}}
        override = {"http": {"host": "0.0.0.0"}, "logging": {"level": "DEBUG"}}

        result = self.loader._merge_config(base, override)

        assert result["http"]["host"] == "0.0.0.0"  # Overridden
        assert result["http"]["port"] == 8000  # Preserved
        assert result["r"]["timeout"] == 120  # Preserved
        assert result["logging"]["level"] == "DEBUG"  # Added

    def test_set_nested_value(self):
        """Test setting nested dictionary values."""
        config_dict = {}
        self.loader._set_nested_value(config_dict, "http.host", "0.0.0.0")
        self.loader._set_nested_value(config_dict, "r.timeout", 180)

        assert config_dict["http"]["host"] == "0.0.0.0"
        assert config_dict["r"]["timeout"] == 180

    @pytest.mark.skipif(
        not hasattr(pytest, "importorskip")
        or not pytest.importorskip("jsonschema", reason="jsonschema not available"),
        reason="jsonschema not available",
    )
    def test_config_validation_success(self):
        """Test successful configuration validation."""
        config_dict = {
            "http": {"host": "localhost", "port": 8000},
            "r": {"timeout": 120},
        }
        # Should not raise
        self.loader._validate_config(config_dict)

    @pytest.mark.skipif(
        not hasattr(pytest, "importorskip")
        or not pytest.importorskip("jsonschema", reason="jsonschema not available"),
        reason="jsonschema not available",
    )
    def test_config_validation_failure(self):
        """Test configuration validation failure."""
        config_dict = {"http": {"port": "invalid"}}  # Should be integer
        with pytest.raises(ConfigError, match="Configuration validation failed"):
            self.loader._validate_config(config_dict)

    def test_convert_env_value_types(self):
        """Test environment value type conversion."""
        # Boolean conversion
        assert self.loader._convert_env_value("RMCP_VFS_READ_ONLY", "true") is True
        assert self.loader._convert_env_value("RMCP_DEBUG", "false") is False

        # Integer conversion
        assert self.loader._convert_env_value("RMCP_HTTP_PORT", "9000") == 9000
        assert self.loader._convert_env_value("RMCP_R_TIMEOUT", "180") == 180

        # List conversion
        result = self.loader._convert_env_value("RMCP_HTTP_CORS_ORIGINS", "a,b,c")
        assert result == ["a", "b", "c"]

        # String conversion (default)
        assert (
            self.loader._convert_env_value("RMCP_R_BINARY_PATH", "/usr/bin/R")
            == "/usr/bin/R"
        )

    def test_dict_to_config_success(self):
        """Test successful conversion from dict to RMCPConfig."""
        config_dict = {
            "http": {"host": "localhost", "port": 8000},
            "r": {"timeout": 120},
            "security": {"vfs_read_only": True},
            "performance": {"threadpool_max_workers": 2},
            "logging": {"level": "INFO"},
            "debug": False,
        }

        config = self.loader._dict_to_config(config_dict)
        assert isinstance(config, RMCPConfig)
        assert config.http.host == "localhost"
        assert config.http.port == 8000

    def test_dict_to_config_failure(self):
        """Test failed conversion from dict to RMCPConfig."""
        config_dict = {"http": {"invalid_field": "value"}}  # Invalid field

        with pytest.raises(ConfigError, match="Failed to create configuration object"):
            self.loader._dict_to_config(config_dict)


class TestGlobalConfig:
    """Test global configuration functions."""

    def test_get_config(self):
        """Test getting global configuration."""
        from rmcp.config import get_config

        config = get_config()
        assert isinstance(config, RMCPConfig)

    def test_load_config_function(self):
        """Test load_config function."""
        from rmcp.config import load_config

        config = load_config(validate=False)
        assert isinstance(config, RMCPConfig)
