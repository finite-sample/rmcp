"""
Tests for configuration data models.
"""

import pytest
from rmcp.config.models import (
    HTTPConfig,
    LoggingConfig,
    PerformanceConfig,
    RConfig,
    RMCPConfig,
    SecurityConfig,
)


class TestHTTPConfig:
    """Test HTTPConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HTTPConfig()
        assert config.host == "localhost"
        assert config.port == 8000
        assert config.ssl_keyfile is None
        assert config.ssl_certfile is None
        assert config.ssl_keyfile_password is None
        assert "http://localhost:*" in config.cors_origins

    def test_custom_values(self):
        """Test custom configuration values."""
        config = HTTPConfig(
            host="0.0.0.0", port=9000, cors_origins=["https://example.com"]
        )
        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.cors_origins == ["https://example.com"]

    def test_ssl_configuration(self):
        """Test SSL configuration values."""
        config = HTTPConfig(
            ssl_keyfile="/path/to/key.pem",
            ssl_certfile="/path/to/cert.pem",
            ssl_keyfile_password="secret123",
        )
        assert config.ssl_keyfile == "/path/to/key.pem"
        assert config.ssl_certfile == "/path/to/cert.pem"
        assert config.ssl_keyfile_password == "secret123"


class TestRConfig:
    """Test RConfig model."""

    def test_default_values(self):
        """Test default R configuration values."""
        config = RConfig()
        assert config.timeout == 120
        assert config.session_timeout == 3600
        assert config.max_sessions == 10
        assert config.binary_path is None
        assert config.version_check_timeout == 30

    def test_custom_values(self):
        """Test custom R configuration values."""
        config = RConfig(
            timeout=180,
            session_timeout=7200,
            max_sessions=20,
            binary_path="/usr/local/bin/R",
            version_check_timeout=60,
        )
        assert config.timeout == 180
        assert config.session_timeout == 7200
        assert config.max_sessions == 20
        assert config.binary_path == "/usr/local/bin/R"
        assert config.version_check_timeout == 60


class TestSecurityConfig:
    """Test SecurityConfig model."""

    def test_default_values(self):
        """Test default security configuration values."""
        config = SecurityConfig()
        assert config.vfs_max_file_size == 50 * 1024 * 1024
        assert config.vfs_allowed_paths == []
        assert config.vfs_read_only is True
        assert "text/csv" in config.vfs_allowed_mime_types

    def test_custom_values(self):
        """Test custom security configuration values."""
        config = SecurityConfig(
            vfs_max_file_size=100 * 1024 * 1024,
            vfs_allowed_paths=["/data", "/tmp"],
            vfs_read_only=False,
            vfs_allowed_mime_types=["text/plain"],
        )
        assert config.vfs_max_file_size == 100 * 1024 * 1024
        assert config.vfs_allowed_paths == ["/data", "/tmp"]
        assert config.vfs_read_only is False
        assert config.vfs_allowed_mime_types == ["text/plain"]


class TestPerformanceConfig:
    """Test PerformanceConfig model."""

    def test_default_values(self):
        """Test default performance configuration values."""
        config = PerformanceConfig()
        assert config.threadpool_max_workers == 2
        assert config.callback_timeout == 300
        assert config.process_cleanup_timeout == 5

    def test_custom_values(self):
        """Test custom performance configuration values."""
        config = PerformanceConfig(
            threadpool_max_workers=4, callback_timeout=600, process_cleanup_timeout=10
        )
        assert config.threadpool_max_workers == 4
        assert config.callback_timeout == 600
        assert config.process_cleanup_timeout == 10


class TestLoggingConfig:
    """Test LoggingConfig model."""

    def test_default_values(self):
        """Test default logging configuration values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert "%(asctime)s" in config.format
        assert config.stderr_output is True

    def test_custom_values(self):
        """Test custom logging configuration values."""
        config = LoggingConfig(
            level="DEBUG", format="%(levelname)s: %(message)s", stderr_output=False
        )
        assert config.level == "DEBUG"
        assert config.format == "%(levelname)s: %(message)s"
        assert config.stderr_output is False


class TestRMCPConfig:
    """Test main RMCPConfig model."""

    def test_default_values(self):
        """Test default main configuration values."""
        config = RMCPConfig()
        assert isinstance(config.http, HTTPConfig)
        assert isinstance(config.r, RConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.performance, PerformanceConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert config.debug is False

    def test_custom_values(self):
        """Test custom main configuration values."""
        http_config = HTTPConfig(port=9000)
        r_config = RConfig(timeout=180)
        config = RMCPConfig(http=http_config, r=r_config, debug=True)
        assert config.http.port == 9000
        assert config.r.timeout == 180
        assert config.debug is True

    def test_validation_valid_config(self):
        """Test that valid configuration passes validation."""
        config = RMCPConfig()
        # Should not raise any exceptions
        assert config is not None

    def test_validation_invalid_port(self):
        """Test validation of invalid port numbers."""
        with pytest.raises(ValueError, match="HTTP port must be between 1-65535"):
            RMCPConfig(http=HTTPConfig(port=0))

        with pytest.raises(ValueError, match="HTTP port must be between 1-65535"):
            RMCPConfig(http=HTTPConfig(port=70000))

    def test_validation_invalid_timeout(self):
        """Test validation of invalid timeout values."""
        with pytest.raises(ValueError, match="R timeout must be positive"):
            RMCPConfig(r=RConfig(timeout=0))

        with pytest.raises(ValueError, match="R timeout must be positive"):
            RMCPConfig(r=RConfig(timeout=-1))

    def test_validation_invalid_session_timeout(self):
        """Test validation of invalid session timeout values."""
        with pytest.raises(ValueError, match="R session timeout must be positive"):
            RMCPConfig(r=RConfig(session_timeout=0))

    def test_validation_invalid_max_sessions(self):
        """Test validation of invalid max sessions values."""
        with pytest.raises(ValueError, match="R max sessions must be positive"):
            RMCPConfig(r=RConfig(max_sessions=0))

    def test_validation_invalid_file_size(self):
        """Test validation of invalid file size values."""
        with pytest.raises(ValueError, match="VFS max file size must be positive"):
            RMCPConfig(security=SecurityConfig(vfs_max_file_size=0))

    def test_validation_invalid_workers(self):
        """Test validation of invalid worker count."""
        with pytest.raises(ValueError, match="Threadpool max workers must be positive"):
            RMCPConfig(performance=PerformanceConfig(threadpool_max_workers=0))

    def test_validation_invalid_callback_timeout(self):
        """Test validation of invalid callback timeout."""
        with pytest.raises(ValueError, match="Callback timeout must be positive"):
            RMCPConfig(performance=PerformanceConfig(callback_timeout=0))

    def test_validation_invalid_log_level(self):
        """Test validation of invalid log level."""
        with pytest.raises(ValueError, match="Log level must be one of"):
            RMCPConfig(logging=LoggingConfig(level="INVALID"))

    def test_ssl_validation_missing_certfile(self):
        """Test SSL validation when keyfile is provided without certfile."""
        with pytest.raises(
            ValueError,
            match="SSL certificate file is required when SSL key is specified",
        ):
            RMCPConfig(http=HTTPConfig(ssl_keyfile="/path/to/key.pem"))

    def test_ssl_validation_missing_keyfile(self):
        """Test SSL validation when certfile is provided without keyfile."""
        with pytest.raises(
            ValueError,
            match="SSL key file is required when SSL certificate is specified",
        ):
            RMCPConfig(http=HTTPConfig(ssl_certfile="/path/to/cert.pem"))

    def test_ssl_validation_file_not_found(self):
        """Test SSL validation when files don't exist."""
        with pytest.raises(ValueError, match="SSL key file not found"):
            RMCPConfig(
                http=HTTPConfig(
                    ssl_keyfile="/nonexistent/key.pem",
                    ssl_certfile="/nonexistent/cert.pem",
                )
            )

    def test_ssl_validation_both_none(self):
        """Test SSL validation when both keyfile and certfile are None."""
        config = RMCPConfig(http=HTTPConfig(ssl_keyfile=None, ssl_certfile=None))
        assert config.http.ssl_keyfile is None
        assert config.http.ssl_certfile is None
