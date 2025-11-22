"""
JSON Schema for RMCP configuration validation.

Defines the schema used to validate configuration files and ensure
proper structure and types.
"""

from typing import Any

# JSON Schema for RMCP configuration
CONFIG_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "RMCP Configuration Schema",
    "description": "Configuration schema for R Model Context Protocol (RMCP) server",
    "type": "object",
    "properties": {
        "http": {
            "type": "object",
            "description": "HTTP transport configuration",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "HTTP server binding address",
                    "default": "localhost",
                },
                "port": {
                    "type": "integer",
                    "description": "HTTP server port",
                    "minimum": 1,
                    "maximum": 65535,
                    "default": 8000,
                },
                "ssl_keyfile": {
                    "type": ["string", "null"],
                    "description": "Path to SSL/TLS private key file",
                    "default": None,
                },
                "ssl_certfile": {
                    "type": ["string", "null"],
                    "description": "Path to SSL/TLS certificate file",
                    "default": None,
                },
                "ssl_keyfile_password": {
                    "type": ["string", "null"],
                    "description": "Password for encrypted SSL/TLS private key",
                    "default": None,
                },
                "cors_origins": {
                    "type": "array",
                    "description": "Allowed CORS origins",
                    "items": {"type": "string"},
                    "default": [
                        "http://localhost:*",
                        "http://127.0.0.1:*",
                        "http://[::1]:*",
                    ],
                },
            },
            "additionalProperties": False,
        },
        "r": {
            "type": "object",
            "description": "R process configuration",
            "properties": {
                "timeout": {
                    "type": "integer",
                    "description": "R script execution timeout in seconds",
                    "minimum": 1,
                    "default": 120,
                },
                "session_timeout": {
                    "type": "integer",
                    "description": "R session lifetime in seconds",
                    "minimum": 1,
                    "default": 3600,
                },
                "max_sessions": {
                    "type": "integer",
                    "description": "Maximum concurrent R sessions",
                    "minimum": 1,
                    "default": 10,
                },
                "binary_path": {
                    "type": ["string", "null"],
                    "description": "Custom R binary path (auto-detect if null)",
                    "default": None,
                },
                "version_check_timeout": {
                    "type": "integer",
                    "description": "R version check timeout in seconds",
                    "minimum": 1,
                    "default": 30,
                },
            },
            "additionalProperties": False,
        },
        "security": {
            "type": "object",
            "description": "Security and filesystem configuration",
            "properties": {
                "vfs_max_file_size": {
                    "type": "integer",
                    "description": "Maximum file size for VFS operations in bytes",
                    "minimum": 1,
                    "default": 52428800,
                },
                "vfs_allowed_paths": {
                    "type": "array",
                    "description": "Additional allowed filesystem paths",
                    "items": {"type": "string"},
                    "default": [],
                },
                "vfs_read_only": {
                    "type": "boolean",
                    "description": "Enable VFS read-only mode",
                    "default": True,
                },
                "vfs_allowed_mime_types": {
                    "type": "array",
                    "description": "Allowed MIME types for file operations",
                    "items": {"type": "string"},
                },
            },
            "additionalProperties": False,
        },
        "performance": {
            "type": "object",
            "description": "Performance and resource configuration",
            "properties": {
                "threadpool_max_workers": {
                    "type": "integer",
                    "description": "Maximum workers for stdio transport threadpool",
                    "minimum": 1,
                    "default": 2,
                },
                "callback_timeout": {
                    "type": "integer",
                    "description": "Bidirectional callback timeout in seconds",
                    "minimum": 1,
                    "default": 300,
                },
                "process_cleanup_timeout": {
                    "type": "integer",
                    "description": "Process cleanup timeout in seconds",
                    "minimum": 1,
                    "default": 5,
                },
            },
            "additionalProperties": False,
        },
        "logging": {
            "type": "object",
            "description": "Logging configuration",
            "properties": {
                "level": {
                    "type": "string",
                    "description": "Logging level",
                    "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    "default": "INFO",
                },
                "format": {
                    "type": "string",
                    "description": "Log message format string",
                    "default": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "stderr_output": {
                    "type": "boolean",
                    "description": "Enable stderr output (required for MCP)",
                    "default": True,
                },
            },
            "additionalProperties": False,
        },
        "debug": {
            "type": "boolean",
            "description": "Enable debug mode",
            "default": False,
        },
    },
    "additionalProperties": False,
}
