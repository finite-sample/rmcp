"""
Configuration data models for RMCP.

Defines the configuration structure with type hints, defaults, and validation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass(slots=True)
class HTTPConfig:
    """HTTP transport configuration."""

    host: str = "localhost"
    port: int = 8000
    # SSL/TLS configuration
    ssl_keyfile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile_password: Optional[str] = None
    cors_origins: List[str] = field(
        default_factory=lambda: [
            "http://localhost:*",
            "http://127.0.0.1:*",
            "http://[::1]:*",
        ]
    )


@dataclass(slots=True)
class RConfig:
    """R process configuration."""

    timeout: int = 120  # R script execution timeout (seconds)
    session_timeout: int = 3600  # R session lifetime (seconds)
    max_sessions: int = 10  # Maximum concurrent R sessions
    binary_path: Optional[str] = None  # Custom R binary path (auto-detect if None)
    version_check_timeout: int = 30  # R version check timeout (seconds)


@dataclass(slots=True)
class SecurityConfig:
    """Security and filesystem configuration."""

    vfs_max_file_size: int = 50 * 1024 * 1024  # 50MB default
    vfs_allowed_paths: List[str] = field(default_factory=list)
    vfs_read_only: bool = True
    vfs_allowed_mime_types: List[str] = field(
        default_factory=lambda: [
            "text/plain",
            "text/csv",
            "application/json",
            "application/xml",
            "text/xml",
            "application/pdf",
            "text/tab-separated-values",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]
    )


@dataclass(slots=True)
class PerformanceConfig:
    """Performance and resource configuration."""

    threadpool_max_workers: int = 2  # Max workers for stdio transport
    callback_timeout: int = 300  # Bidirectional callback timeout (seconds)
    process_cleanup_timeout: int = 5  # Process cleanup timeout (seconds)


@dataclass(slots=True)
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    stderr_output: bool = True  # Log to stderr (required for MCP)


@dataclass(slots=True)
class RMCPConfig:
    """Main RMCP configuration."""

    http: HTTPConfig = field(default_factory=HTTPConfig)
    r: RConfig = field(default_factory=RConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Global settings
    config_file: Optional[Path] = None
    debug: bool = False

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate configuration values."""
        # Network validation
        if not (1 <= self.http.port <= 65535):
            raise ValueError(
                f"HTTP port must be between 1-65535, got: {self.http.port}"
            )

        # SSL validation - if one SSL file is specified, both must be provided
        ssl_keyfile = self.http.ssl_keyfile
        ssl_certfile = self.http.ssl_certfile
        if ssl_keyfile or ssl_certfile:
            if not ssl_keyfile:
                raise ValueError(
                    "SSL key file is required when SSL certificate is specified"
                )
            if not ssl_certfile:
                raise ValueError(
                    "SSL certificate file is required when SSL key is specified"
                )
            # Validate files exist if paths are provided
            if ssl_keyfile and not Path(ssl_keyfile).is_file():
                raise ValueError(f"SSL key file not found: {ssl_keyfile}")
            if ssl_certfile and not Path(ssl_certfile).is_file():
                raise ValueError(f"SSL certificate file not found: {ssl_certfile}")

        # R configuration validation
        if self.r.timeout <= 0:
            raise ValueError(f"R timeout must be positive, got: {self.r.timeout}")

        if self.r.session_timeout <= 0:
            raise ValueError(
                f"R session timeout must be positive, got: {self.r.session_timeout}"
            )

        if self.r.max_sessions <= 0:
            raise ValueError(
                f"R max sessions must be positive, got: {self.r.max_sessions}"
            )

        # Security validation
        if self.security.vfs_max_file_size <= 0:
            raise ValueError(
                f"VFS max file size must be positive, got: {self.security.vfs_max_file_size}"
            )

        # Performance validation
        if self.performance.threadpool_max_workers <= 0:
            raise ValueError(
                f"Threadpool max workers must be positive, got: {self.performance.threadpool_max_workers}"
            )

        if self.performance.callback_timeout <= 0:
            raise ValueError(
                f"Callback timeout must be positive, got: {self.performance.callback_timeout}"
            )

        # Logging validation
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.logging.level.upper() not in valid_levels:
            raise ValueError(
                f"Log level must be one of {valid_levels}, got: {self.logging.level}"
            )
