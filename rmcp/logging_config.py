"""
Structured logging configuration for RMCP MCP Server.

Provides JSON-formatted structured logging optimized for:
- MCP protocol observability and debugging
- Request correlation across tool chains and R execution
- Integration with modern monitoring platforms (ELK, Grafana, Datadog)
- Performance monitoring of statistical workflows

Key Features:
- Correlation ID propagation through context vars
- MCP-specific structured fields (tool_name, session_id, execution_time)
- Security event logging (operation approval, VFS access)
- Development vs production logging modes
"""

import contextvars
import json
import logging
import logging.config
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import structlog

# Context variables for request correlation
correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
session_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "session_id", default=None
)
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

# Performance tracking
request_start_time_var: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "request_start_time", default=None
)


def add_correlation_context(
    logger: structlog.BoundLogger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add correlation IDs and request context to all log entries."""
    # Add correlation identifiers
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    session_id = session_id_var.get()
    if session_id:
        event_dict["session_id"] = session_id

    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id

    # Add execution timing if available
    start_time = request_start_time_var.get()
    if start_time:
        event_dict["execution_time_ms"] = int((time.time() - start_time) * 1000)

    return event_dict


def add_mcp_context(
    logger: structlog.BoundLogger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add MCP-specific context fields."""
    # Ensure component field is set
    if "component" not in event_dict:
        # Try to get logger name from the underlying logger
        if hasattr(logger, "_logger") and hasattr(logger._logger, "name"):
            logger_name = logger._logger.name
        elif hasattr(logger, "name"):
            logger_name = logger.name
        else:
            logger_name = "unknown"

        if "rmcp." in logger_name:
            event_dict["component"] = logger_name.replace("rmcp.", "")
        else:
            event_dict["component"] = logger_name

    # Add service identification
    event_dict["service"] = "rmcp"
    event_dict["protocol"] = "mcp"

    return event_dict


def configure_structured_logging(
    level: str = "INFO",
    development_mode: bool = False,
    log_file: Path | None = None,
    enable_console: bool = True,
) -> None:
    """
    Configure structured logging for RMCP.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        development_mode: If True, uses pretty console formatting for dev
        log_file: Optional file path for log output
        enable_console: Whether to enable console logging
    """
    # Clear existing configuration
    structlog.reset_defaults()

    # Shared processors for all loggers
    shared_processors = [
        # Add correlation and MCP context
        add_correlation_context,
        add_mcp_context,
        # Filter for log level
        structlog.stdlib.filter_by_level,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="ISO", utc=True),
        # Add stack info for errors
        structlog.dev.set_exc_info,
        structlog.processors.add_log_level,
    ]

    if development_mode and enable_console:
        # Pretty console output for development
        processors = shared_processors + [structlog.dev.ConsoleRenderer(colors=True)]
        formatter = None
    else:
        # JSON output for production
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

        class JSONFormatter(logging.Formatter):
            """Custom JSON formatter for standard library logging."""

            def format(self, record: logging.LogRecord) -> str:
                log_entry = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "component": record.name.replace("rmcp.", "")
                    if "rmcp." in record.name
                    else record.name,
                    "message": record.getMessage(),
                    "service": "rmcp",
                    "protocol": "mcp",
                }

                # Add correlation context if available
                correlation_id = correlation_id_var.get()
                if correlation_id:
                    log_entry["correlation_id"] = correlation_id

                session_id = session_id_var.get()
                if session_id:
                    log_entry["session_id"] = session_id

                request_id = request_id_var.get()
                if request_id:
                    log_entry["request_id"] = request_id

                # Add exception info if present
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)

                return json.dumps(log_entry, default=str)

        formatter = JSONFormatter()

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    handlers = []

    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        if formatter:
            console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        if formatter:
            file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True,  # Override existing configuration
    )

    # Set specific logger levels for better control
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger for the given module."""
    return structlog.get_logger(name)


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set correlation ID for request tracking. Returns the set ID."""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


def set_session_id(session_id: str | None = None) -> str:
    """Set session ID for multi-request workflows. Returns the set ID."""
    if session_id is None:
        session_id = str(uuid.uuid4())
    session_id_var.set(session_id)
    return session_id


def set_request_id(request_id: str | None = None) -> str:
    """Set request ID for individual operations. Returns the set ID."""
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


def start_request_timing() -> None:
    """Start timing for current request."""
    request_start_time_var.set(time.time())


def get_execution_time_ms() -> int | None:
    """Get execution time in milliseconds if timing was started."""
    start_time = request_start_time_var.get()
    if start_time:
        return int((time.time() - start_time) * 1000)
    return None


class LogContext:
    """Context manager for scoped logging context."""

    def __init__(
        self,
        correlation_id: str | None = None,
        session_id: str | None = None,
        request_id: str | None = None,
        start_timing: bool = True,
    ):
        self.correlation_id = correlation_id
        self.session_id = session_id
        self.request_id = request_id
        self.start_timing = start_timing
        self._tokens = []

    def __enter__(self):
        """Enter logging context and set context variables."""
        if self.correlation_id:
            token = correlation_id_var.set(self.correlation_id)
            self._tokens.append(("correlation_id", token))

        if self.session_id:
            token = session_id_var.set(self.session_id)
            self._tokens.append(("session_id", token))

        if self.request_id:
            token = request_id_var.set(self.request_id)
            self._tokens.append(("request_id", token))

        if self.start_timing:
            token = request_start_time_var.set(time.time())
            self._tokens.append(("start_time", token))

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit logging context and reset context variables."""
        for var_name, token in reversed(self._tokens):
            if var_name == "correlation_id":
                correlation_id_var.set(token.old_value)
            elif var_name == "session_id":
                session_id_var.set(token.old_value)
            elif var_name == "request_id":
                request_id_var.set(token.old_value)
            elif var_name == "start_time":
                request_start_time_var.set(token.old_value)


def log_tool_execution(
    logger: structlog.BoundLogger,
    tool_name: str,
    parameters: dict[str, Any],
    execution_time_ms: int | None = None,
    r_packages_used: list | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> None:
    """Log structured tool execution event."""
    log_data = {
        "tool_name": tool_name,
        "success": success,
    }

    if execution_time_ms is not None:
        log_data["execution_time_ms"] = execution_time_ms

    if r_packages_used:
        log_data["r_packages_used"] = r_packages_used

    if parameters:
        # Log parameter structure without sensitive data
        log_data["parameter_count"] = len(parameters)
        log_data["parameter_keys"] = list(parameters.keys())

    if success:
        logger.info("Tool execution completed", **log_data)
    else:
        if error_message:
            log_data["error_message"] = error_message
        logger.error("Tool execution failed", **log_data)


def log_security_event(
    logger: structlog.BoundLogger,
    event_type: str,
    operation: str,
    approved: bool,
    security_level: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Log security-related events (approvals, VFS access, etc.)."""
    log_data = {
        "event_type": event_type,
        "operation": operation,
        "approved": approved,
    }

    if security_level:
        log_data["security_level"] = security_level

    if details:
        log_data.update(details)

    if approved:
        logger.info("Security operation approved", **log_data)
    else:
        logger.warning("Security operation denied", **log_data)


def log_r_execution(
    logger: structlog.BoundLogger,
    r_command: str,
    execution_time_ms: int,
    packages_loaded: list | None = None,
    memory_usage_mb: float | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> None:
    """Log R script execution details."""
    log_data = {
        "command_length": len(r_command),
        "execution_time_ms": execution_time_ms,
        "success": success,
    }

    if packages_loaded:
        log_data["packages_loaded"] = packages_loaded
        log_data["package_count"] = len(packages_loaded)

    if memory_usage_mb is not None:
        log_data["memory_usage_mb"] = memory_usage_mb

    if success:
        logger.info("R execution completed", **log_data)
    else:
        if error_message:
            log_data["error_message"] = error_message
        logger.error("R execution failed", **log_data)


def log_http_request(
    logger: structlog.BoundLogger,
    method: str,
    path: str,
    status_code: int,
    response_time_ms: int,
    user_agent: str | None = None,
    content_length: int | None = None,
) -> None:
    """Log HTTP transport requests."""
    log_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
    }

    if user_agent:
        log_data["user_agent"] = user_agent

    if content_length is not None:
        log_data["content_length"] = content_length

    if 200 <= status_code < 400:
        logger.info("HTTP request processed", **log_data)
    elif 400 <= status_code < 500:
        logger.warning("HTTP client error", **log_data)
    else:
        logger.error("HTTP server error", **log_data)
