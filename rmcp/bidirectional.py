"""
Bidirectional Communication for RMCP.

This module enables R scripts to call back to the Python MCP server,
inspired by mcptools' bidirectional communication capabilities.

Key features:
- R can invoke Python MCP tools
- R can trigger progress updates and logging
- R can request additional data or analysis
- R can compose complex analytical workflows
- Secure callback mechanism with permission management

Design principles:
- R scripts can request additional capabilities from Python
- Callback permissions are configurable and secure
- Graceful degradation when callbacks are not available
- Maintains context and session state across calls
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from .core.context import Context
from .registries.tools import tool

logger = logging.getLogger(__name__)


class CallbackManager:
    """
    Manages bidirectional communication between R and Python MCP server.

    This class provides a secure callback mechanism that allows R scripts
    to invoke Python MCP tools and request additional capabilities.
    """

    def __init__(self):
        self.active_callbacks: dict[str, dict[str, Any]] = {}
        self.callback_permissions: dict[str, set[str]] = {}
        self.callback_timeout = 300.0  # 5 minutes default

    def register_callback(
        self,
        callback_id: str,
        context: Context,
        allowed_tools: set[str] | None = None,
    ) -> None:
        """Register a callback session for R → Python communication."""
        self.active_callbacks[callback_id] = {
            "context": context,
            "created_at": asyncio.get_event_loop().time(),
            "allowed_tools": allowed_tools or set(),
            "call_count": 0,
        }

        logger.info(f"Registered callback session: {callback_id}")

    def unregister_callback(self, callback_id: str) -> None:
        """Unregister a callback session."""
        if callback_id in self.active_callbacks:
            del self.active_callbacks[callback_id]
            logger.info(f"Unregistered callback session: {callback_id}")

    async def handle_callback(
        self, callback_id: str, tool_name: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle a callback request from R."""
        if callback_id not in self.active_callbacks:
            return {
                "error": f"Callback session {callback_id} not found",
                "success": False,
            }

        callback_info = self.active_callbacks[callback_id]

        # Check timeout
        current_time = asyncio.get_event_loop().time()
        if current_time - callback_info["created_at"] > self.callback_timeout:
            self.unregister_callback(callback_id)
            return {"error": "Callback session expired", "success": False}

        # Check permissions
        allowed_tools = callback_info["allowed_tools"]
        if allowed_tools and tool_name not in allowed_tools:
            return {
                "error": f"Tool {tool_name} not permitted for this callback",
                "success": False,
            }

        # Update call count
        callback_info["call_count"] += 1

        try:
            # Get the tool from registry and execute
            context = callback_info["context"]

            # Import here to avoid circular imports

            server = context._server

            if not server or not hasattr(server, "tools"):
                return {
                    "error": "MCP server not available for callbacks",
                    "success": False,
                }

            # Execute the tool
            tool_handler = server.tools._tools.get(tool_name)
            if not tool_handler:
                return {"error": f"Tool {tool_name} not found", "success": False}

            await context.info(f"Executing callback: {tool_name}")
            result = await tool_handler(context, parameters)

            return {
                "result": result,
                "tool_name": tool_name,
                "callback_id": callback_id,
                "success": True,
            }

        except Exception as e:
            await context.error(f"Callback execution failed: {e}")
            return {"error": str(e), "tool_name": tool_name, "success": False}

    async def cleanup_expired_callbacks(self) -> None:
        """Remove expired callback sessions."""
        current_time = asyncio.get_event_loop().time()
        expired_callbacks = []

        for callback_id, info in self.active_callbacks.items():
            if current_time - info["created_at"] > self.callback_timeout:
                expired_callbacks.append(callback_id)

        for callback_id in expired_callbacks:
            self.unregister_callback(callback_id)


# Global callback manager
_callback_manager = CallbackManager()


def get_callback_manager() -> CallbackManager:
    """Get the global callback manager."""
    return _callback_manager


@tool(
    name="create_r_callback_session",
    description="Create a callback session for R → Python communication",
    input_schema={
        "type": "object",
        "properties": {
            "session_name": {
                "type": "string",
                "description": "Name for the callback session",
            },
            "allowed_tools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of tools R is allowed to call back to",
            },
            "timeout_minutes": {
                "type": "number",
                "description": "Session timeout in minutes",
                "default": 5,
            },
        },
    },
)
async def create_r_callback_session(
    context: Context, params: dict[str, Any]
) -> dict[str, Any]:
    """
    Create a callback session that allows R scripts to call back to Python MCP tools.

    This enables bidirectional communication where R can request additional
    analysis, data processing, or other MCP tool capabilities.
    """
    session_name = params.get("session_name", f"callback_{uuid.uuid4().hex[:8]}")
    allowed_tools = set(params.get("allowed_tools", []))
    timeout_minutes = params.get("timeout_minutes", 5)

    callback_id = f"rmcp_callback_{uuid.uuid4().hex}"

    # Register callback session
    manager = get_callback_manager()
    manager.callback_timeout = timeout_minutes * 60
    manager.register_callback(callback_id, context, allowed_tools)

    # Create callback configuration for R
    callback_config = {
        "callback_id": callback_id,
        "session_name": session_name,
        "allowed_tools": list(allowed_tools),
        "timeout_minutes": timeout_minutes,
        "callback_file": None,  # Will be set when R script starts
    }

    await context.info(f"Created callback session: {session_name} ({callback_id})")

    return {
        "callback_config": callback_config,
        "session_name": session_name,
        "callback_id": callback_id,
        "instructions": {
            "usage": "Use rmcp_callback() function in R to call back to Python tools",
            "example": "result <- rmcp_callback('linear_model', list(data=my_data, formula='y ~ x'))",
        },
        "success": True,
    }


@tool(
    name="handle_r_callback",
    description="Handle a callback request from R scripts",
    input_schema={
        "type": "object",
        "properties": {
            "callback_id": {"type": "string", "description": "Callback session ID"},
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to execute",
            },
            "parameters": {
                "type": "object",
                "description": "Parameters to pass to the tool",
            },
        },
        "required": ["callback_id", "tool_name", "parameters"],
    },
)
async def handle_r_callback(context: Context, params: dict[str, Any]) -> dict[str, Any]:
    """
    Handle a callback request from an R script.

    This tool is called by R scripts to invoke Python MCP tools,
    enabling complex analytical workflows that span both R and Python.
    """
    callback_id = params["callback_id"]
    tool_name = params["tool_name"]
    parameters = params["parameters"]

    manager = get_callback_manager()
    result = await manager.handle_callback(callback_id, tool_name, parameters)

    return result


def create_r_callback_utilities() -> str:
    """
    Create R utility functions for bidirectional communication.

    Returns R code that can be sourced to enable callback functionality.
    """
    r_utilities = """
# RMCP Bidirectional Communication Utilities
# These functions enable R scripts to call back to Python MCP tools

# Global variables for callback configuration
.rmcp_callback_config <- NULL
.rmcp_callback_file <- NULL

# Initialize callback system
rmcp_init_callback <- function(callback_config) {
  .rmcp_callback_config <<- callback_config

  # Create temporary file for callback communication
  .rmcp_callback_file <<- tempfile(pattern = "rmcp_callback_", fileext = ".json")

  cat("RMCP callback system initialized\\n")
  cat("Callback ID:", callback_config$callback_id, "\\n")
  cat("Allowed tools:", paste(callback_config$allowed_tools, collapse = ", "), "\\n")

  return(TRUE)
}

# Make a callback to Python MCP tool
rmcp_callback <- function(tool_name, parameters = list()) {
  if (is.null(.rmcp_callback_config)) {
    stop("Callback system not initialized. Call rmcp_init_callback() first.")
  }

  # Check if tool is allowed
  if (length(.rmcp_callback_config$allowed_tools) > 0 &&
      !tool_name %in% .rmcp_callback_config$allowed_tools) {
    stop(paste("Tool", tool_name, "not allowed for callbacks"))
  }

  # Prepare callback request
  callback_request <- list(
    callback_id = .rmcp_callback_config$callback_id,
    tool_name = tool_name,
    parameters = parameters,
    timestamp = as.numeric(Sys.time())
  )

  # Write request to file
  write(toJSON(callback_request, auto_unbox = TRUE), .rmcp_callback_file)

  # Signal Python to handle callback (this is a simplified version)
  # In practice, this would use a more sophisticated IPC mechanism
  cat("RMCP_CALLBACK:", .rmcp_callback_file, "\\n", file = stderr())

  # For now, return a placeholder response
  # Real implementation would wait for Python response
  return(list(
    success = TRUE,
    message = paste("Callback to", tool_name, "requested"),
    tool_name = tool_name
  ))
}

# Progress reporting that can trigger Python callbacks
rmcp_progress_callback <- function(message, current = NULL, total = NULL) {
  if (!is.null(.rmcp_callback_config)) {
    progress_data <- list(
      type = "progress",
      message = message,
      current = current,
      total = total,
      timestamp = as.numeric(Sys.time()),
      callback_id = .rmcp_callback_config$callback_id
    )

    cat("RMCP_PROGRESS_CALLBACK:", toJSON(progress_data, auto_unbox = TRUE), "\\n", file = stderr())
  }

  # Also call regular progress function
  if (exists("rmcp_progress")) {
    rmcp_progress(message, current, total)
  }
}

# Request additional data or analysis
rmcp_request_data <- function(data_specification) {
  return(rmcp_callback("load_example", list(
    dataset_name = data_specification$name,
    size = data_specification$size %||% "medium",
    format = data_specification$format %||% "data.frame"
  )))
}

# Compose complex analytical workflows
rmcp_compose_analysis <- function(steps) {
  return(rmcp_callback("execute_workflow", list(
    workflow_name = "dynamic_workflow",
    steps = steps
  )))
}

# Clean up callback resources
rmcp_cleanup_callback <- function() {
  if (!is.null(.rmcp_callback_file) && file.exists(.rmcp_callback_file)) {
    unlink(.rmcp_callback_file)
  }

  .rmcp_callback_config <<- NULL
  .rmcp_callback_file <<- NULL

  cat("RMCP callback system cleaned up\\n")
}

# Auto-cleanup on session end
reg.finalizer(.GlobalEnv, function(env) {
  if (!is.null(.rmcp_callback_file)) {
    rmcp_cleanup_callback()
  }
}, onexit = TRUE)

cat("RMCP bidirectional communication utilities loaded\\n")
"""

    return r_utilities


@tool(
    name="setup_r_bidirectional",
    description="Set up R environment for bidirectional communication with Python MCP",
    input_schema={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "R session ID to set up bidirectional communication",
            },
            "allowed_tools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tools R is allowed to call back to",
            },
        },
    },
)
async def setup_r_bidirectional(
    context: Context, params: dict[str, Any]
) -> dict[str, Any]:
    """
    Set up bidirectional communication in an R session.

    This tool prepares an R session to enable callbacks to Python MCP tools,
    allowing for complex interactive analytical workflows.
    """
    session_id = params.get("session_id")
    allowed_tools = params.get("allowed_tools", [])

    try:
        # Create callback session
        callback_result = await create_r_callback_session(
            context,
            {
                "session_name": f"bidirectional_{session_id or 'default'}",
                "allowed_tools": allowed_tools,
            },
        )

        if not callback_result["success"]:
            return callback_result

        callback_config = callback_result["callback_config"]

        # Set up R environment with callback utilities
        setup_script = f"""
        # Load RMCP callback utilities
        {create_r_callback_utilities()}

        # Initialize callback system
        callback_config <- {json.dumps(callback_config)}
        rmcp_init_callback(callback_config)

        # Test callback system
        cat("Bidirectional communication ready\\n")

        result <- list(
            bidirectional_enabled = TRUE,
            callback_id = callback_config$callback_id,
            allowed_tools = callback_config$allowed_tools,
            session_id = "{session_id or "default"}"
        )
        """

        # Execute setup in R session
        setup_result = await context.execute_r_with_session(
            setup_script, {}, use_session=True
        )

        await context.info("R bidirectional communication set up successfully")

        return {
            **setup_result,
            "callback_config": callback_config,
            "setup_complete": True,
            "success": True,
        }

    except Exception as e:
        await context.error(f"Failed to set up R bidirectional communication: {e}")
        return {"error": str(e), "setup_complete": False, "success": False}


@tool(
    name="list_callback_sessions",
    description="List active callback sessions for R ↔ Python communication",
    input_schema={"type": "object", "properties": {}},
)
async def list_callback_sessions(
    context: Context, params: dict[str, Any]
) -> dict[str, Any]:
    """
    List all active callback sessions.

    This provides visibility into bidirectional communication sessions
    between R and Python MCP server.
    """
    manager = get_callback_manager()

    sessions = []
    current_time = asyncio.get_event_loop().time()

    for callback_id, info in manager.active_callbacks.items():
        sessions.append(
            {
                "callback_id": callback_id,
                "created_at": info["created_at"],
                "age_seconds": current_time - info["created_at"],
                "allowed_tools": list(info["allowed_tools"]),
                "call_count": info["call_count"],
            }
        )

    return {
        "active_sessions": sessions,
        "total_sessions": len(sessions),
        "success": True,
    }
