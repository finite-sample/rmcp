"""
Structured logging configuration for RMCP MCP Server.

Every record -- whether emitted through structlog or through plain ``logging``
-- is rendered once, by a single ``ProcessorFormatter``, into one envelope:

    {"event": ..., "level": ..., "component": ..., "timestamp": ...,
     "service": "rmcp", "protocol": "mcp", "request_id": ...}

Fields stay top-level and therefore queryable. Anything logged while serving a
request also carries ``request_id``, which is what ties a tool call to the R
execution underneath it.

Output goes to stderr: stdout carries the JSON-RPC stream in stdio mode and
must not be written to.
"""

import contextvars
import logging
import logging.config
import sys
import uuid
from pathlib import Path
from typing import Any

import structlog

#: Set once per request by ``SDKServerAdapter._create_context``. asyncio copies
#: the context when a task is created, so every line logged while serving a
#: request carries the id -- which is what makes a tool call and its R
#: execution correlatable.
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def add_correlation_context(
    logger: structlog.BoundLogger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Attach the current request id, when one is in scope."""
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id

    return event_dict


def add_mcp_context(
    logger: structlog.BoundLogger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add MCP-specific context fields."""
    if "component" not in event_dict:
        # structlog.stdlib.add_logger_name runs first and sets this for both
        # structlog-native and plain-stdlib records.
        logger_name = event_dict.get("logger") or "unknown"
        event_dict["component"] = logger_name.removeprefix("rmcp.")

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

    # Applied to structlog-native records and, via foreign_pre_chain below, to
    # records from the modules that still use plain `logging` -- so both end up
    # with the same envelope instead of two incompatible shapes.
    #
    # filter_by_level is deliberately absent: it needs a structlog logger and
    # would fail on foreign records. It goes in the structlog chain only, and
    # first, so dropped events skip the work below.
    shared_processors = [
        structlog.stdlib.add_logger_name,
        add_correlation_context,
        add_mcp_context,
        structlog.processors.TimeStamper(fmt="ISO", utc=True),
        structlog.processors.add_log_level,
        structlog.dev.set_exc_info,
    ]

    # structlog hands the event dict to the stdlib handler rather than
    # rendering it itself. Rendering happens once, in the formatter below.
    # Previously structlog rendered JSON and a second formatter nested that
    # string under "message", so no field was ever queryable.
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    if development_mode and enable_console:
        renderer: Any = structlog.dev.ConsoleRenderer(colors=True)
        render_chain = [renderer]
    else:
        renderer = structlog.processors.JSONRenderer()
        render_chain = [structlog.processors.dict_tracebacks, renderer]

    # foreign_pre_chain is what gives records from the plain-`logging` modules
    # the same envelope as structlog ones, without touching those modules.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *render_chain,
        ],
    )

    # Configure standard library logging
    handlers = []

    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True,  # Override existing configuration
    )

    # Set specific logger levels for better control
    logging.getLogger("uvicorn").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger for the given module."""
    return structlog.get_logger(name)


def set_request_id(request_id: str | None = None) -> str:
    """Set request ID for individual operations. Returns the set ID."""
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


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
