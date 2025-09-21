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
from typing import Any, Awaitable, Callable, Sequence

from ..core.context import Context
from ..core.schemas import SchemaError, statistical_result_schema, validate_schema

logger = logging.getLogger(__name__)


def _paginate_items(
    items: list[Any], cursor: str | None, limit: int | None
) -> tuple[list[Any], str | None]:
    """Return a slice of items based on cursor/limit pagination."""

    total_items = len(items)
    start_index = 0

    if cursor is not None:
        if not isinstance(cursor, str):
            raise ValueError("cursor must be a string if provided")

        try:
            start_index = int(cursor)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError("cursor must be an integer string") from exc

        if start_index < 0 or start_index > total_items:
            raise ValueError("cursor is out of range")

    if limit is not None:
        try:
            limit_value = int(limit)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError("limit must be an integer") from exc

        if limit_value <= 0:
            raise ValueError("limit must be a positive integer")
    else:
        limit_value = total_items - start_index

    end_index = min(start_index + limit_value, total_items)
    next_cursor = str(end_index) if end_index < total_items else None

    return items[start_index:end_index], next_cursor


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

    def __init__(
        self,
        on_list_changed: Callable[[list[str] | None], None] | None = None,
    ):
        self._tools: dict[str, ToolDefinition] = {}
        self._on_list_changed = on_list_changed

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

        self._emit_list_changed([name])

    async def list_tools(
        self,
        context: Context,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """List available tools for MCP tools/list."""

        ordered_tools = sorted(self._tools.values(), key=lambda tool: tool.name)
        page, next_cursor = _paginate_items(ordered_tools, cursor, limit)

        tools: list[dict[str, Any]] = []
        for tool_def in page:
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

        await context.info(
            "Listed tools",
            count=len(tools),
            total=len(ordered_tools),
            next_cursor=next_cursor,
        )

        response: dict[str, Any] = {"tools": tools}
        if next_cursor is not None:
            response["nextCursor"] = next_cursor

        return response

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

            return self._format_tool_response(tool_def, result)

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

    def _emit_list_changed(self, item_ids: list[str] | None = None) -> None:
        """Emit list changed notification when available."""

        if not self._on_list_changed:
            return

        try:
            self._on_list_changed(item_ids)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("List changed callback failed for tools: %s", exc)

    def _format_tool_response(
        self, tool_def: ToolDefinition, result: Any
    ) -> dict[str, Any]:
        """Convert tool output into rich MCP content."""

        if (
            isinstance(result, dict)
            and "content" in result
            and isinstance(result["content"], Sequence)
        ):
            return result

        image_data = None
        image_mime_type = "image/png"
        base_payload: Any = result

        if isinstance(result, dict) and "image_data" in result:
            image_data = result.get("image_data")
            image_mime_type = result.get("image_mime_type", "image/png")
            base_payload = {
                k: v
                for k, v in result.items()
                if k not in {"image_data", "image_mime_type"}
            }

        if isinstance(base_payload, str) and base_payload.strip() == "":
            base_payload = {"status": "completed"}
        elif not base_payload and not isinstance(base_payload, (list, dict)):
            base_payload = {"status": "completed"}

        summary = self._build_summary(tool_def, base_payload)
        content: list[dict[str, Any]] = []

        if summary:
            content.append(
                {
                    "type": "text",
                    "text": summary,
                    "annotations": {"mimeType": "text/markdown"},
                }
            )

        if isinstance(base_payload, (dict, list)):
            content.append(
                {
                    "type": "text",
                    "text": json.dumps(base_payload, indent=2, default=str),
                    "annotations": {"mimeType": "application/json"},
                }
            )
        elif isinstance(base_payload, str) and not summary:
            content.append(
                {
                    "type": "text",
                    "text": base_payload,
                    "annotations": {"mimeType": "text/markdown"},
                }
            )
        elif not summary:
            content.append(
                {
                    "type": "text",
                    "text": json.dumps(base_payload, default=str),
                }
            )

        if image_data:
            content.append(
                {"type": "image", "data": image_data, "mimeType": image_mime_type}
            )

        return {"content": content}

    def _build_summary(self, tool_def: ToolDefinition, payload: Any) -> str:
        """Create a concise markdown summary for human readers."""

        title = tool_def.title or tool_def.name

        if isinstance(payload, str):
            return payload

        if isinstance(payload, list):
            return (
                f"**{title}** produced {len(payload)} "
                f"item{'s' if len(payload) != 1 else ''}."
            )

        if isinstance(payload, dict):
            bullets = []
            for key, value in list(payload.items())[:8]:
                if isinstance(value, (str, int, float)):
                    bullets.append(f"- **{key}**: {value}")
                elif isinstance(value, bool):
                    bullets.append(f"- **{key}**: {'yes' if value else 'no'}")
                elif value is None:
                    bullets.append(f"- **{key}**: null")
                elif isinstance(value, list):
                    bullets.append(
                        f"- **{key}**: {len(value)} item{'s' if len(value) != 1 else ''}"
                    )
                elif isinstance(value, dict):
                    bullets.append(
                        f"- **{key}**: {len(value)} field{'s' if len(value) != 1 else ''}"
                    )
                else:
                    bullets.append(f"- **{key}**: {type(value).__name__}")

            if not bullets:
                return f"**{title}** completed without additional details."

            bullet_text = "\n".join(bullets)
            return f"**{title}** summary:\n{bullet_text}"

        return f"**{title}** returned {payload}"


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
