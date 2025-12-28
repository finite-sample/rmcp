"""
Configuration data models for RMCP.

This module defines the complete configuration structure for RMCP with type hints,
defaults, and validation. Configuration values are resolved in hierarchical order:

1. Command-line arguments (highest priority)
2. Environment variables (``RMCP_*`` prefix)
3. User configuration file (``~/.rmcp/config.json``)
4. System configuration file (``/etc/rmcp/config.json``)
5. Built-in defaults (lowest priority)

Examples:
    Environment variable configuration::

        export RMCP_HTTP_HOST=0.0.0.0
        export RMCP_HTTP_PORT=9000
        export RMCP_R_TIMEOUT=180

    Configuration file (``~/.rmcp/config.json``)::

        {
          "http": {"host": "0.0.0.0", "port": 9000},
          "r": {"timeout": 180, "max_sessions": 20},
          "logging": {"level": "DEBUG"}
        }

    Command-line override::

        rmcp --config custom.json --debug start
"""

from dataclasses import dataclass, field
from pathlib import Path

from ..types import CORSOrigin, LogLevel


@dataclass(slots=True)
class HTTPConfig:
    """HTTP transport configuration.

    Controls the HTTP server behavior for RMCP when running in HTTP mode.

    Environment Variables:
        * ``RMCP_HTTP_HOST`` - Server binding address
        * ``RMCP_HTTP_PORT`` - Server port number
        * ``RMCP_HTTP_CORS_ORIGINS`` - Allowed CORS origins (comma-separated)
        * ``RMCP_HTTP_SSL_KEYFILE`` - SSL private key file path
        * ``RMCP_HTTP_SSL_CERTFILE`` - SSL certificate file path

    Security Considerations:
        * Default binding to ``localhost`` for security
        * Set ``host="0.0.0.0"`` for remote access (implement authentication)
        * Configure ``cors_origins`` appropriately for web clients
        * SSL files must both be provided if either is specified

    Examples:
        Development configuration::

            http = HTTPConfig(
                host="localhost",
                port=8000
            )

        Production with SSL::

            http = HTTPConfig(
                host="0.0.0.0",
                port=443,
                ssl_keyfile="/etc/ssl/private/rmcp.key",
                ssl_certfile="/etc/ssl/certs/rmcp.crt",
                cors_origins=["https://myapp.example.com"]
            )
    """

    host: str = "localhost"
    """Server binding address. Default: ``localhost`` for security. Use ``0.0.0.0`` for remote access."""

    port: int = 8000
    """Server port number. Must be between 1-65535."""

    ssl_keyfile: str | None = None
    """SSL private key file path. Required if ssl_certfile is specified."""

    ssl_certfile: str | None = None
    """SSL certificate file path. Required if ssl_keyfile is specified."""

    ssl_keyfile_password: str | None = None
    """SSL private key password if the key file is encrypted."""

    cors_origins: list[CORSOrigin] = field(
        default_factory=lambda: [
            "http://localhost:*",
            "http://127.0.0.1:*",
            "http://[::1]:*",
        ]
    )
    """Allowed CORS origins for cross-origin requests. Supports wildcards."""


@dataclass(slots=True)
class RConfig:
    """R process configuration.

    Controls R process execution, session management, and resource limits.

    Environment Variables:
        * ``RMCP_R_TIMEOUT`` - R script execution timeout (seconds)
        * ``RMCP_R_SESSION_TIMEOUT`` - R session lifetime (seconds)
        * ``RMCP_R_MAX_SESSIONS`` - Maximum concurrent R sessions
        * ``RMCP_R_BINARY_PATH`` - Custom R binary path
        * ``RMCP_R_VERSION_CHECK_TIMEOUT`` - R version check timeout

    Resource Considerations:
        * Limit ``max_sessions`` based on available memory (R sessions consume ~100-200MB each)
        * Set reasonable ``timeout`` to prevent runaway processes
        * Use ``session_timeout`` to free resources from idle sessions

    Examples:
        Development configuration::

            r = RConfig(
                timeout=300,
                max_sessions=5
            )

        Production configuration::

            r = RConfig(
                timeout=120,
                session_timeout=1800,
                max_sessions=50,
                binary_path="/usr/local/bin/R"
            )
    """

    timeout: int = 120
    """R script execution timeout in seconds. Prevents runaway processes."""

    session_timeout: int = 3600
    """R session lifetime in seconds. Sessions are cleaned up after this time."""

    max_sessions: int = 10
    """Maximum concurrent R sessions. Limit based on available memory."""

    binary_path: str | None = None
    """Custom R binary path. Auto-detected if None."""

    version_check_timeout: int = 30
    """R version check timeout in seconds during startup."""


@dataclass(slots=True)
class SecurityConfig:
    """Security and filesystem configuration.

    Controls Virtual File System (VFS) security boundaries and access controls.

    Environment Variables:
        * ``RMCP_VFS_MAX_FILE_SIZE`` - Maximum file size in bytes
        * ``RMCP_VFS_ALLOWED_PATHS`` - Additional allowed paths (comma-separated)
        * ``RMCP_VFS_READ_ONLY`` - Enable read-only mode (true/false)

    Security Considerations:
        * Keep ``vfs_read_only=True`` in production to prevent file modification
        * Restrict ``vfs_allowed_paths`` to necessary directories only
        * Set appropriate ``vfs_max_file_size`` limits to prevent resource exhaustion
        * Only trusted file types are allowed by default

    Examples:
        Production security (read-only)::

            security = SecurityConfig(
                vfs_max_file_size=104857600,  # 100MB
                vfs_read_only=True,
                vfs_allowed_paths=["/data/readonly"]
            )

        Development (write access)::

            security = SecurityConfig(
                vfs_read_only=False,
                vfs_allowed_paths=["/tmp", "/home/user/datasets"]
            )
    """

    vfs_max_file_size: int = 50 * 1024 * 1024
    """Maximum file size for VFS operations in bytes. Default: 50MB."""

    vfs_allowed_paths: list[str] = field(default_factory=list)
    """Additional filesystem paths accessible via VFS. Empty = temp directory only."""

    vfs_read_only: bool = True
    """Enable VFS read-only mode. Prevents file modification in production."""

    vfs_allowed_mime_types: list[str] = field(
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
    """Allowed MIME types for file operations. Only trusted formats by default."""


@dataclass(slots=True)
class PerformanceConfig:
    """Performance and resource configuration.

    Controls concurrency, timeouts, and resource management.

    Environment Variables:
        * ``RMCP_THREADPOOL_MAX_WORKERS`` - Max workers for stdio transport
        * ``RMCP_CALLBACK_TIMEOUT`` - Bidirectional callback timeout (seconds)
        * ``RMCP_PROCESS_CLEANUP_TIMEOUT`` - Process cleanup timeout (seconds)

    Performance Tuning:
        * Adjust ``threadpool_max_workers`` based on CPU cores
        * Increase ``callback_timeout`` for slow operations
        * Keep ``process_cleanup_timeout`` low for faster resource cleanup

    Examples:
        High-performance server::

            performance = PerformanceConfig(
                threadpool_max_workers=8,
                callback_timeout=600
            )

        Resource-constrained environment::

            performance = PerformanceConfig(
                threadpool_max_workers=1,
                callback_timeout=120
            )
    """

    threadpool_max_workers: int = 2
    """Maximum workers for stdio transport. Adjust based on CPU cores."""

    callback_timeout: int = 300
    """Bidirectional callback timeout in seconds. For slow operations."""

    process_cleanup_timeout: int = 5
    """Process cleanup timeout in seconds. Keep low for faster cleanup."""


@dataclass(slots=True)
class LoggingConfig:
    """Logging configuration.

    Controls log output format and verbosity.

    Environment Variables:
        * ``RMCP_LOG_LEVEL`` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        * ``RMCP_LOG_FORMAT`` - Log message format string

    Log Levels:
        * ``DEBUG`` - Detailed debugging information
        * ``INFO`` - General operational messages
        * ``WARNING`` - Warning messages about potential issues
        * ``ERROR`` - Error messages for failed operations
        * ``CRITICAL`` - Critical errors that may cause shutdown

    Examples:
        Development logging::

            logging = LoggingConfig(
                level="DEBUG",
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )

        Production logging::

            logging = LoggingConfig(
                level="INFO",
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
    """

    level: LogLevel = "INFO"
    """Logging level. Must be DEBUG, INFO, WARNING, ERROR, or CRITICAL."""

    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    """Log message format string. Python logging format."""

    stderr_output: bool = True
    """Log to stderr. Required for MCP protocol compliance."""


@dataclass(slots=True)
class RMCPConfig:
    """Main RMCP configuration.

    Root configuration object containing all subsystem configurations.
    Provides validation and hierarchical configuration loading.

    Environment Variables:
        * ``RMCP_DEBUG`` - Enable debug mode (true/false)

    Configuration Loading:
        1. Command-line arguments (highest priority)
        2. Environment variables (``RMCP_*`` prefix)
        3. User config file (``~/.rmcp/config.json``)
        4. System config file (``/etc/rmcp/config.json``)
        5. Built-in defaults (lowest priority)

    Examples:
        Complete configuration::

            config = RMCPConfig(
                http=HTTPConfig(host="0.0.0.0", port=8000),
                r=RConfig(timeout=180, max_sessions=20),
                security=SecurityConfig(vfs_read_only=True),
                debug=True
            )

        Minimal configuration (uses defaults)::

            config = RMCPConfig(debug=True)
    """

    http: HTTPConfig = field(default_factory=HTTPConfig)
    """HTTP transport configuration."""

    r: RConfig = field(default_factory=RConfig)
    """R process configuration."""

    security: SecurityConfig = field(default_factory=SecurityConfig)
    """Security and VFS configuration."""

    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    """Performance and resource configuration."""

    logging: LoggingConfig = field(default_factory=LoggingConfig)
    """Logging configuration."""

    config_file: Path | None = None
    """Path to configuration file that was loaded."""

    debug: bool = False
    """Enable debug mode for verbose logging and configuration details."""

    def __post_init__(self):
        """Validate configuration after initialization.

        Automatically called after dataclass initialization to ensure
        all configuration values are valid and consistent.

        Raises:
            ValueError: If any configuration value is invalid or inconsistent.
        """
        self._validate()

    def _validate(self):
        """Validate configuration values.

        Performs comprehensive validation of all configuration settings:

        * Network values: Ports must be between 1-65535
        * Timeouts: Must be positive integers
        * File sizes: Must be positive integers
        * Log levels: Must be valid Python logging levels
        * SSL configuration: Both key and cert files required if either specified
        * Path validation: SSL files must exist if specified

        Raises:
            ValueError: If any configuration value is invalid with descriptive message.
        """
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
