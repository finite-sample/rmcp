"""
Tools registry for MCP server.

Provides:
- @tool decorator for declarative tool registration
- Schema validation with proper error codes
- Tool discovery and dispatch
- Context-aware execution

Following the principle: "Registries are discoverable and testable."
"""

import inspect
import json
import logging
from dataclasses import dataclass
from functools import wraps
from typing import Any, Awaitable, Callable

from ..core.context import Context
from ..core.schemas import SchemaError, statistical_result_schema, validate_schema

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Tool metadata and handler."""

    name: str
    handler: Callable[[Context, dict[str, Any]], Awaitable[dict[str, Any]]]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    title: str | None = None
    description: str | None = None
    annotations: dict[str, Any] | None = None


class ToolsRegistry:
    """Registry for MCP tools with schema validation."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        handler: Callable[[Context, dict[str, Any]], Awaitable[dict[str, Any]]],
        input_schema: dict[str, Any],
        output_schema: dict[str, Any] | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: dict[str, Any] | None = None,
    ) -> None:
        """Register a tool with the registry."""

        if name in self._tools:
            logger.warning(f"Tool '{name}' already registered, overwriting")

        self._tools[name] = ToolDefinition(
            name=name,
            handler=handler,
            input_schema=input_schema,
            output_schema=output_schema,
            title=title or name,
            description=description or f"Execute {name}",
            annotations=annotations or {},
        )

        logger.debug(f"Registered tool: {name}")

    async def list_tools(self, context: Context) -> dict[str, Any]:
        """List available tools for MCP tools/list."""

        tools = []
        for tool_def in self._tools.values():
            tool_info = {
                "name": tool_def.name,
                "title": tool_def.title,
                "description": tool_def.description,
                "inputSchema": tool_def.input_schema,
            }

            if tool_def.output_schema:
                tool_info["outputSchema"] = tool_def.output_schema

            if tool_def.annotations:
                tool_info["annotations"] = tool_def.annotations

            tools.append(tool_info)

        await context.info(f"Listed {len(tools)} available tools")

        return {"tools": tools}

    async def call_tool(
        self, context: Context, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a tool with validation."""

        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")

        tool_def = self._tools[name]

        try:
            # Validate input schema
            validate_schema(
                arguments, tool_def.input_schema, f"tool '{name}' arguments"
            )

            await context.info(f"Calling tool: {name}", arguments=arguments)

            # Check cancellation before execution
            context.check_cancellation()

            # Execute tool handler
            result = await tool_def.handler(context, arguments)

            # Handle None or empty results
            if result is None:
                result = {}
            elif not isinstance(result, (dict, list, str, int, float, bool)):
                result = {"error": "Tool returned invalid result type"}

            # Validate output schema if provided
            if tool_def.output_schema:
                validate_schema(result, tool_def.output_schema, f"tool '{name}' output")

            await context.info(f"Tool completed: {name}")

            # Handle multiple content types (text + optional image)
            if isinstance(result, dict) and "image_data" in result:
                # Create content array with both text and image
                content = []

                # Text content (exclude image-specific fields)
                text_result = {
                    k: v
                    for k, v in result.items()
                    if k not in ["image_data", "image_mime_type"]
                }

                # Ensure we have valid text content
                if not text_result:
                    text_result = {"status": "completed"}

                content.append(
                    {"type": "text", "text": json.dumps(text_result, default=str)}
                )

                # Image content
                image_data = result.get("image_data")
                mime_type = result.get("image_mime_type", "image/png")

                if image_data:
                    content.append(
                        {"type": "image", "data": image_data, "mimeType": mime_type}
                    )

                return {"content": content}
            else:
                # Standard text-only response
                # Ensure we always have valid JSON content
                if isinstance(result, str) and result.strip() == "":
                    result = {"status": "completed"}
                elif not result and not isinstance(result, (list, dict)):
                    result = {"status": "completed"}

                return {
                    "content": [
                        {"type": "text", "text": json.dumps(result, default=str)}
                    ]
                }

        except SchemaError as e:
            await context.error(f"Schema validation failed for tool '{name}': {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True,
            }

        except Exception as e:
            await context.error(f"Tool execution failed for '{name}': {e}")
            return {
                "content": [{"type": "text", "text": f"Tool execution error: {e}"}],
                "isError": True,
            }


def tool(
    name: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any] | None = None,
    title: str | None = None,
    description: str | None = None,
    annotations: dict[str, Any] | None = None,
):
    """
    Decorator to register a function as an MCP tool.

    Usage:
        @tool(
            name="analyze_data",
            input_schema={
                "type": "object",
                "properties": {
                    "data": table_schema(),
                    "method": choice_schema(["mean", "median", "mode"])
                },
                "required": ["data"]
            },
            description="Analyze dataset with specified method"
        )
        async def analyze_data(context: Context, params: dict[str, Any]) -> dict[str, Any]:
            # Tool implementation
            return {"result": "analysis complete"}
    """

    def decorator(func: Callable[[Context, dict[str, Any]], Awaitable[dict[str, Any]]]):

        # Ensure function is async
        if not inspect.iscoroutinefunction(func):
            raise ValueError(f"Tool handler '{name}' must be an async function")

        # Store tool metadata on function for registration
        func._mcp_tool_name = name
        func._mcp_tool_input_schema = input_schema
        func._mcp_tool_output_schema = output_schema
        func._mcp_tool_title = title
        func._mcp_tool_description = description
        func._mcp_tool_annotations = annotations

        return func

    return decorator


def register_tool_functions(registry: ToolsRegistry, *functions) -> None:
    """Register multiple functions decorated with @tool."""

    for func in functions:
        if hasattr(func, "_mcp_tool_name"):
            registry.register(
                name=func._mcp_tool_name,
                handler=func,
                input_schema=func._mcp_tool_input_schema,
                output_schema=func._mcp_tool_output_schema,
                title=func._mcp_tool_title,
                description=func._mcp_tool_description,
                annotations=func._mcp_tool_annotations,
            )
        else:
            logger.warning(
                f"Function {func.__name__} not decorated with @tool, skipping"
            )
