"""
Default configuration values for RMCP.

Centralized location for all default settings that can be overridden
through environment variables or configuration files.
"""

from pathlib import Path
from typing import Any

# Default configuration as a dictionary for easy serialization
DEFAULT_CONFIG: dict[str, Any] = {
    "http": {
        "host": "localhost",
        "port": 8000,
        "ssl_keyfile": None,
        "ssl_certfile": None,
        "ssl_keyfile_password": None,
        "cors_origins": ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"],
    },
    "r": {
        "timeout": 120,
        "session_timeout": 3600,
        "max_sessions": 10,
        "binary_path": None,
        "version_check_timeout": 30,
    },
    "security": {
        "vfs_max_file_size": 50 * 1024 * 1024,  # 50MB
        "vfs_allowed_paths": [],
        "vfs_read_only": True,
        "vfs_allowed_mime_types": [
            "text/plain",
            "text/csv",
            "application/json",
            "application/xml",
            "text/xml",
            "application/pdf",
            "text/tab-separated-values",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ],
    },
    "performance": {
        "threadpool_max_workers": 2,
        "callback_timeout": 300,
        "process_cleanup_timeout": 5,
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "stderr_output": True,
    },
    "debug": False,
}

# Standard configuration file locations (in order of precedence)
CONFIG_FILE_LOCATIONS = [
    Path.home() / ".rmcp" / "config.json",  # User config
    Path("/etc/rmcp/config.json"),  # System config (Unix)
    Path("/usr/local/etc/rmcp/config.json"),  # System config (Unix alt)
]

# Environment variable prefix
ENV_PREFIX = "RMCP_"

# Environment variable mappings to config paths
ENV_MAPPINGS = {
    "RMCP_HTTP_HOST": "http.host",
    "RMCP_HTTP_PORT": "http.port",
    "RMCP_HTTP_SSL_KEYFILE": "http.ssl_keyfile",
    "RMCP_HTTP_SSL_CERTFILE": "http.ssl_certfile",
    "RMCP_HTTP_SSL_KEYFILE_PASSWORD": "http.ssl_keyfile_password",
    "RMCP_HTTP_CORS_ORIGINS": "http.cors_origins",
    "RMCP_R_TIMEOUT": "r.timeout",
    "RMCP_R_SESSION_TIMEOUT": "r.session_timeout",
    "RMCP_R_MAX_SESSIONS": "r.max_sessions",
    "RMCP_R_BINARY_PATH": "r.binary_path",
    "RMCP_R_VERSION_CHECK_TIMEOUT": "r.version_check_timeout",
    "RMCP_VFS_MAX_FILE_SIZE": "security.vfs_max_file_size",
    "RMCP_VFS_ALLOWED_PATHS": "security.vfs_allowed_paths",
    "RMCP_VFS_READ_ONLY": "security.vfs_read_only",
    "RMCP_THREADPOOL_MAX_WORKERS": "performance.threadpool_max_workers",
    "RMCP_CALLBACK_TIMEOUT": "performance.callback_timeout",
    "RMCP_PROCESS_CLEANUP_TIMEOUT": "performance.process_cleanup_timeout",
    "RMCP_LOG_LEVEL": "logging.level",
    "RMCP_LOG_FORMAT": "logging.format",
    "RMCP_DEBUG": "debug",
}
