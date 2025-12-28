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
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from ..core.context import Context
from ..core.schemas import SchemaError, validate_schema

logger = logging.getLogger(__name__)


class ToolHandler(Protocol):
    """Protocol for tool handler functions with MCP metadata."""

    _mcp_tool_name: str
    _mcp_tool_input_schema: dict[str, Any]
    _mcp_tool_output_schema: dict[str, Any] | None
    _mcp_tool_title: str | None
    _mcp_tool_description: str | None
    _mcp_tool_annotations: dict[str, Any] | None

    def __call__(
        self, context: Context, params: dict[str, Any]
    ) -> Awaitable[dict[str, Any]]: ...


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
            elif not isinstance(result, dict | list | str | int | float | bool):
                result = {"error": "Tool returned invalid result type"}

            # Extract formatting information before validation (schema-safe approach)
            formatting_info = None
            if isinstance(result, dict) and "_formatting" in result:
                extracted = result.pop("_formatting")  # Remove from result
                if isinstance(extracted, dict):
                    formatting_info = extracted

            # Validate output schema if provided (re-enabled for safety)
            if tool_def.output_schema:
                validate_schema(result, tool_def.output_schema, f"tool '{name}' output")

            await context.info(f"Tool completed: {name}")
            return self._format_tool_response(tool_def, result, formatting_info)
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
        self, tool_def: ToolDefinition, result: Any, formatting_info: dict | None = None
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
        elif not base_payload and not isinstance(base_payload, list | dict):
            base_payload = {"status": "completed"}
        summary = self._build_summary(tool_def, base_payload, formatting_info)
        content: list[dict[str, Any]] = []
        structured_content: list[dict[str, Any]] = []
        # Build human-readable content (text summaries)
        if summary:
            content.append(
                {
                    "type": "text",
                    "text": summary,
                    "annotations": {"mimeType": "text/markdown"},
                }
            )
        # Add JSON as text when no summary is available
        if isinstance(base_payload, str) and not summary:
            content.append(
                {
                    "type": "text",
                    "text": base_payload,
                    "annotations": {"mimeType": "text/markdown"},
                }
            )
        elif not summary and base_payload:
            content.append(
                {
                    "type": "text",
                    "text": json.dumps(base_payload, indent=2, default=str),
                    "annotations": {"mimeType": "application/json"},
                }
            )
        # Build structured content (machine-readable data)
        if isinstance(base_payload, dict | list) and base_payload:
            # Check if this is a large dataset that should be stored as a resource
            resource_uri = self._check_for_large_data_and_create_resource(base_payload)
            if resource_uri:
                # Large dataset - provide resource link instead of inline data
                structured_content.append(
                    {
                        "type": "resource_link",
                        "resource": {
                            "uri": resource_uri,
                            "mimeType": "application/json",
                            "name": "Large Dataset",
                            "description": f"Dataset with {self._estimate_data_size(base_payload)} items",
                        },
                        "annotations": {"large_data": True},
                    }
                )
                # Add summary in content for human readability
                data_summary = self._create_data_summary(base_payload)
                if data_summary:
                    content.append(
                        {
                            "type": "text",
                            "text": f"📊 **Large Dataset Created**\n\n{data_summary}\n\n*Full dataset available via resource link.*",
                            "annotations": {"mimeType": "text/markdown"},
                        }
                    )
            else:
                # Normal sized data - include inline
                structured_content.append(
                    {
                        "type": "json",
                        "json": base_payload,
                        "annotations": {"mimeType": "application/json"},
                    }
                )
        # Add images to both content streams
        if image_data:
            image_block = {
                "type": "image",
                "data": image_data,
                "mimeType": image_mime_type,
            }
            content.append(image_block)
            structured_content.append(image_block)
        # Prepare response
        response: dict[str, Any] = {"content": content}
        if structured_content:
            # MCP specification requires structuredContent to be an object, not an array
            if len(structured_content) == 1:
                # Single item - use it directly as the object
                response["structuredContent"] = structured_content[0]
            else:
                # Multiple items - wrap in proper object structure
                response["structuredContent"] = {
                    "items": structured_content,
                    "count": len(structured_content),
                    "type": "multi_content",
                }
        return response

    def _build_summary(
        self,
        tool_def: ToolDefinition,
        payload: Any,
        formatting_info: dict | None = None,
    ) -> str:
        """Create a concise markdown summary for human readers."""
        title = tool_def.title or tool_def.name

        # Prefer formatted summaries provided by formatting_info
        if formatting_info:
            # Use the formatted summary when available
            if "summary" in formatting_info and formatting_info["summary"]:
                # formatted_summary already includes interpretation, so just return it
                return formatting_info["summary"]

            # Use the interpretation text when no formatted_summary is present
            if (
                "interpretation" in formatting_info
                and formatting_info["interpretation"]
            ):
                return f"## {title} Results\n\n{formatting_info['interpretation']}"

        # Fallback to the default summary logic
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
                if isinstance(value, str | int | float):
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

    def _check_for_large_data_and_create_resource(self, data: Any) -> str | None:
        """
        Check if data is large and should be stored as a resource.
        Returns resource URI if data should be stored as resource, None otherwise.
        """
        # Thresholds for considering data "large"
        MAX_ROWS = 1000
        MAX_SIZE_BYTES = 50 * 1024  # 50KB
        try:
            # Estimate data size
            data_json = json.dumps(data, default=str)
            size_bytes = len(data_json.encode("utf-8"))
            # Check if it's a table-like structure with many rows
            is_large_table = False
            if isinstance(data, dict):
                # Check for column-wise data format {col1: [values], col2: [values]}
                if self._is_tabular_data(data):
                    num_rows = self._count_table_rows(data)
                    is_large_table = num_rows > MAX_ROWS
                # Check for array of objects format [{col1: val, col2: val}, ...]
                elif "data" in data and isinstance(data["data"], list):
                    is_large_table = len(data["data"]) > MAX_ROWS
            elif isinstance(data, list) and len(data) > MAX_ROWS:
                is_large_table = True
            # Create resource if data is large
            if size_bytes > MAX_SIZE_BYTES or is_large_table:
                resource_id = str(uuid.uuid4())
                resource_uri = f"rmcp://data/{resource_id}"
                # Store data in server's resource registry
                # This is a simplified implementation - in production you might want
                # to store in a proper cache/database
                if not hasattr(self, "_large_data_store"):
                    self._large_data_store = {}
                self._large_data_store[resource_id] = {
                    "data": data,
                    "content_type": "application/json",
                    "size_bytes": size_bytes,
                }
                return resource_uri
        except Exception:
            # If we can't serialize or analyze the data, just return None
            # and let it be handled as normal inline data
            pass
        return None

    def _is_tabular_data(self, data: dict) -> bool:
        """Check if data is in tabular format (column-wise)."""
        if not isinstance(data, dict):
            return False
        # Look for data key containing column-wise structure
        if "data" in data and isinstance(data["data"], dict):
            data_obj = data["data"]
        else:
            data_obj = data
        # Check if all values are lists of similar length
        if not data_obj:
            return False
        list_values = [v for v in data_obj.values() if isinstance(v, list)]
        if len(list_values) < 2:  # Need at least 2 columns to be considered tabular
            return False
        # Check if all lists have similar lengths (within 10% of each other)
        lengths = [len(lst) for lst in list_values]
        if not lengths:
            return False
        min_len, max_len = min(lengths), max(lengths)
        return max_len - min_len <= max(1, min_len * 0.1)

    def _count_table_rows(self, data: dict) -> int:
        """Count rows in tabular data."""
        if "data" in data and isinstance(data["data"], dict):
            data_obj = data["data"]
        else:
            data_obj = data
        # Find the first list value to get row count
        for value in data_obj.values():
            if isinstance(value, list):
                return len(value)
        return 0

    def _estimate_data_size(self, data: Any) -> str:
        """Create a human-readable estimate of data size."""
        if isinstance(data, dict):
            if self._is_tabular_data(data):
                rows = self._count_table_rows(data)
                cols = len([v for v in data.values() if isinstance(v, list)])
                return f"{rows:,} rows × {cols} columns"
            else:
                return f"{len(data)} fields"
        elif isinstance(data, list):
            return f"{len(data):,} items"
        else:
            return "large dataset"

    def _create_data_summary(self, data: Any) -> str:
        """Create a summary of large dataset for human readers."""
        summary_parts = []
        if isinstance(data, dict):
            if self._is_tabular_data(data):
                rows = self._count_table_rows(data)
                # Get column info
                if "data" in data and isinstance(data["data"], dict):
                    columns = list(data["data"].keys())
                else:
                    columns = [k for k, v in data.items() if isinstance(v, list)]
                summary_parts.append(
                    f"**Dimensions**: {rows:,} rows × {len(columns)} columns"
                )
                if columns:
                    col_preview = ", ".join(columns[:5])
                    if len(columns) > 5:
                        col_preview += f", ... ({len(columns) - 5} more)"
                    summary_parts.append(f"**Columns**: {col_preview}")
                # Show preview of first few rows if available
                if rows > 0:
                    summary_parts.append(
                        "**Preview**: First few rows available via resource"
                    )
            else:
                summary_parts.append(f"**Type**: Dictionary with {len(data)} fields")
        elif isinstance(data, list):
            summary_parts.append(f"**Type**: Array with {len(data):,} items")
        return "\n".join(summary_parts)


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

    def decorator(
        func: Callable[[Context, dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> ToolHandler:
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
        return func  # type: ignore

    return decorator


def register_tool_functions(registry: ToolsRegistry, *functions: ToolHandler) -> None:
    """Register multiple functions decorated with @tool."""
    for func in functions:
        registry.register(
            name=func._mcp_tool_name,
            handler=func,
            input_schema=func._mcp_tool_input_schema,
            output_schema=func._mcp_tool_output_schema,
            title=func._mcp_tool_title,
            description=func._mcp_tool_description,
            annotations=func._mcp_tool_annotations,
        )
