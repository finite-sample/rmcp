"""
Resources registry for MCP server.
Implements mature MCP patterns:
- Read-only endpoints for files and in-memory objects
- URI-based addressing (file://, mem://)
- Resource templates for parameterized access
- VFS integration for security
Following the principle: "Keeps data access explicit and auditable."
"""

import base64
import inspect
import json
import logging
import platform
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from ..core.context import Context
from ..r_integration import execute_r_script_async
from ..security import VFSError
from ..tools.helpers import load_example

logger = logging.getLogger(__name__)

_REQUIRED_R_PACKAGES: tuple[str, ...] = (
    "jsonlite",
    "plm",
    "lmtest",
    "sandwich",
    "AER",
    "dplyr",
    "forecast",
    "vars",
    "urca",
    "tseries",
    "nortest",
    "car",
    "rpart",
    "randomForest",
    "ggplot2",
    "gridExtra",
    "tidyr",
    "rlang",
    "base64enc",
    "reshape2",
    "readxl",
    "knitr",
)


def _paginate_items(
    items: list[dict[str, Any]], cursor: str | None, limit: int | None
) -> tuple[list[dict[str, Any]], str | None]:
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


class ResourcesRegistry:
    """Registry for MCP resources with VFS security."""

    def __init__(
        self,
        on_list_changed: Callable[[list[str] | None], None] | None = None,
    ):
        self._static_resources: dict[str, dict[str, Any]] = {}
        self._memory_objects: dict[str, Any] = {}
        self._resource_templates: dict[str, dict[str, Any]] = {}
        self._on_list_changed = on_list_changed

    def register_static_resource(
        self,
        uri: str,
        name: str,
        description: str | None = None,
        mime_type: str | None = None,
        content_loader: str
        | bytes
        | Callable[[], Any]
        | Callable[[], Awaitable[Any]]
        | None = None,
    ) -> None:
        """Register a static resource."""
        self._static_resources[uri] = {
            "uri": uri,
            "name": name,
            "description": description or f"Resource: {name}",
            "mimeType": mime_type,
            "loader": content_loader,
        }
        logger.debug(f"Registered static resource: {uri}")
        self._emit_list_changed([uri])

    def register_memory_object(
        self,
        name: str,
        data: Any,
        description: str | None = None,
        mime_type: str = "application/json",
    ) -> None:
        """Register an in-memory object as a resource."""
        uri = f"mem://object/{name}"
        self._memory_objects[name] = data
        self._static_resources[uri] = {
            "uri": uri,
            "name": name,
            "description": description or f"Memory object: {name}",
            "mimeType": mime_type,
        }
        logger.debug(f"Registered memory object: {name}")
        self._emit_list_changed([uri])

    def register_resource_template(
        self,
        uri_template: str,
        name: str,
        description: str | None = None,
    ) -> None:
        """Register a parameterized resource template."""
        self._resource_templates[uri_template] = {
            "name": name,
            "description": description or f"Template: {name}",
        }
        logger.debug(f"Registered resource template: {uri_template}")
        self._emit_list_changed([uri_template])

    async def list_resources(
        self,
        context: Context,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """List available resources for MCP resources/list."""
        resources: list[dict[str, Any]] = []
        for uri, resource_info in sorted(self._static_resources.items()):
            entry: dict[str, Any] = {"uri": uri, "name": resource_info["name"]}
            if resource_info.get("description"):
                entry["description"] = resource_info["description"]
            if resource_info.get("mimeType"):
                entry["mimeType"] = resource_info["mimeType"]
            resources.append(entry)
        for uri_template, metadata in sorted(self._resource_templates.items()):
            entry = {"uri": uri_template, "name": metadata["name"]}
            if metadata.get("description"):
                entry["description"] = metadata["description"]
            resources.append(entry)
        if hasattr(context.lifespan, "vfs") and context.lifespan.vfs:
            for mount_name, mount_path in sorted(
                context.lifespan.resource_mounts.items()
            ):
                resources.append(
                    {
                        "uri": f"file://{mount_name}/",
                        "name": f"Files: {mount_name}",
                        "description": f"File system mount: {mount_path}",
                    }
                )
        page, next_cursor = _paginate_items(resources, cursor, limit)
        await context.info(
            "Listed resources",
            count=len(page),
            total=len(resources),
            next_cursor=next_cursor,
        )
        response: dict[str, Any] = {"resources": page}
        if next_cursor is not None:
            response["nextCursor"] = next_cursor
        return response

    async def read_resource(self, context: Context, uri: str) -> dict[str, Any]:
        """Read a resource for MCP resources/read."""
        try:
            parsed_uri = urlparse(uri)
            scheme = parsed_uri.scheme
            if scheme == "file":
                return await self._read_file_resource(context, parsed_uri)
            elif scheme == "mem":
                return await self._read_memory_resource(context, parsed_uri)
            elif scheme == "rmcp":
                return await self._read_rmcp_resource(context, parsed_uri)
            else:
                # Check static resources
                if uri in self._static_resources:
                    return await self._read_static_resource(context, uri)
                else:
                    raise ValueError(
                        f"Unsupported resource scheme or unknown URI: {uri}"
                    )
        except Exception as e:
            await context.error(f"Failed to read resource {uri}: {e}")
            raise

    async def _read_file_resource(self, context: Context, parsed_uri) -> dict[str, Any]:
        """Read file:// resource using VFS."""
        # Extract path from URI
        file_path = Path(parsed_uri.path)
        try:
            # Use VFS for secure file access
            if hasattr(context.lifespan, "vfs") and context.lifespan.vfs:
                vfs = context.lifespan.vfs
            else:
                # Fallback to direct path validation
                context.require_path_access(file_path)
                content = file_path.read_bytes()
                mime_type = "application/octet-stream"
            if "vfs" in locals():
                content = vfs.read_file(file_path)
                file_info = vfs.file_info(file_path)
                mime_type = file_info.get("mime_type", "application/octet-stream")
            # Determine if content should be base64 encoded
            is_text = mime_type and mime_type.startswith("text/")
            if is_text:
                try:
                    text_content = content.decode("utf-8")
                    return {
                        "contents": [
                            {
                                "uri": str(parsed_uri.geturl()),
                                "mimeType": mime_type,
                                "text": text_content,
                            }
                        ]
                    }
                except UnicodeDecodeError:
                    # Fall back to binary
                    pass
            # Binary content
            b64_content = base64.b64encode(content).decode("ascii")
            return {
                "contents": [
                    {
                        "uri": str(parsed_uri.geturl()),
                        "mimeType": mime_type,
                        "blob": b64_content,
                    }
                ]
            }
        except (VFSError, PermissionError, FileNotFoundError) as e:
            raise ValueError(f"File access error: {e}")

    async def _read_memory_resource(
        self, context: Context, parsed_uri
    ) -> dict[str, Any]:
        """Read mem:// resource from memory objects."""
        # Extract object name from URI path
        path_parts = parsed_uri.path.strip("/").split("/")
        if len(path_parts) < 2 or path_parts[0] != "object":
            raise ValueError(f"Invalid memory resource URI: {parsed_uri.geturl()}")
        object_name = path_parts[1]
        if object_name not in self._memory_objects:
            raise ValueError(f"Memory object not found: {object_name}")
        data = self._memory_objects[object_name]
        # Serialize object to JSON text
        import json

        try:
            text_content = json.dumps(data, indent=2, default=str)
            return {
                "contents": [
                    {
                        "uri": parsed_uri.geturl(),
                        "mimeType": "application/json",
                        "text": text_content,
                    }
                ]
            }
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize memory object {object_name}: {e}")

    async def _read_static_resource(self, context: Context, uri: str) -> dict[str, Any]:
        """Read a pre-registered static resource."""
        resource_info = self._static_resources[uri]
        loader = resource_info.get("loader")
        mime_type = resource_info.get("mimeType") or "text/plain"
        content: Any
        if loader is None:
            content = resource_info.get(
                "description", f"Static resource: {resource_info['name']}"
            )
        elif isinstance(loader, str | bytes):
            content = loader
        else:
            result = loader()
            if inspect.isawaitable(result):
                content = await result
            else:
                content = result
        if isinstance(content, bytes):
            b64_content = base64.b64encode(content).decode("ascii")
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": mime_type,
                        "blob": b64_content,
                    }
                ]
            }
        if not isinstance(content, str):
            content = str(content)
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": mime_type,
                    "text": content,
                }
            ]
        }

    async def _read_rmcp_resource(self, context: Context, parsed_uri) -> dict[str, Any]:
        """Read rmcp:// resource for catalog, env, datasets, or stored data."""
        target = parsed_uri.netloc
        server = getattr(context, "_server", None)
        if not server:
            raise ValueError("Server context not available for RMCP resource access")
        if target == "catalog":
            return await self._generate_catalog_resource(context, server, parsed_uri)
        if target == "env":
            return await self._generate_environment_resource(context, parsed_uri)
        if target == "dataset":
            return await self._generate_dataset_resource(context, server, parsed_uri)
        if target == "data":
            return await self._read_stored_rmcp_data(context, server, parsed_uri)
        raise ValueError(f"Unsupported RMCP resource URI: {parsed_uri.geturl()}")

    async def _read_stored_rmcp_data(
        self, context: Context, server: Any, parsed_uri
    ) -> dict[str, Any]:
        """Read previously stored RMCP data resources (rmcp://data/{id})."""
        path_parts = parsed_uri.path.strip("/").split("/")
        if len(path_parts) != 1 or not path_parts[0]:
            raise ValueError(f"Invalid RMCP data URI: {parsed_uri.geturl()}")
        resource_id = path_parts[0]
        tools_registry = getattr(server, "tools", None)
        if not tools_registry or not hasattr(tools_registry, "_large_data_store"):
            raise ValueError(f"RMCP resource not found: {resource_id}")
        data_store = tools_registry._large_data_store
        if resource_id not in data_store:
            raise ValueError(f"RMCP resource not found: {resource_id}")
        stored_resource = data_store[resource_id]
        data = stored_resource["data"]
        content_type = stored_resource.get("content_type", "application/json")
        json_content = json.dumps(data, indent=2, default=str)
        await context.info(
            "Retrieved stored RMCP resource",
            resource_id=resource_id,
            size_bytes=stored_resource.get("size_bytes", 0),
        )
        return {
            "contents": [
                {
                    "uri": parsed_uri.geturl(),
                    "mimeType": content_type,
                    "text": json_content,
                }
            ]
        }

    async def _generate_catalog_resource(
        self, context: Context, server: Any, parsed_uri
    ) -> dict[str, Any]:
        """Build Markdown catalog describing registered tools and minimal usage."""
        tools_registry = getattr(server, "tools", None)
        if not tools_registry:
            raise ValueError("Tools registry not available for catalog resource")
        tool_defs = getattr(tools_registry, "_tools", {})
        lines: list[str] = [
            "# RMCP Tool Catalog",
            "",
            "Each entry lists the tool's purpose and a minimal JSON-RPC call example.",
            "",
        ]
        for tool_name in sorted(tool_defs):
            tool_def = tool_defs[tool_name]
            minimal_arguments = self._build_minimal_arguments(tool_def.input_schema)
            example_payload = {"tool": tool_name, "arguments": minimal_arguments}
            example_json = json.dumps(example_payload, indent=2)
            description = tool_def.description or f"Execute {tool_name}"
            lines.extend(
                [
                    f"## {tool_name}",
                    "",
                    f"**Purpose:** {description}",
                    "",
                    "```json",
                    example_json,
                    "```",
                    "",
                ]
            )
        catalog_markdown = "\n".join(lines).strip() + "\n"
        await context.info("Generated tool catalog resource", tool_count=len(tool_defs))
        return {
            "contents": [
                {
                    "uri": parsed_uri.geturl(),
                    "mimeType": "text/markdown",
                    "text": catalog_markdown,
                }
            ]
        }

    def _build_minimal_arguments(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Create minimal argument payload based on required schema fields."""
        if not schema:
            return {}
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])
        minimal_arguments: dict[str, Any] = {}
        for field in required_fields:
            field_schema = properties.get(field, {})
            minimal_arguments[field] = self._example_value_for_schema(field_schema)
        return minimal_arguments

    def _example_value_for_schema(self, schema: dict[str, Any]) -> Any:
        """Generate a representative value for a schema node."""
        if not schema:
            return "<value>"
        if "default" in schema:
            return schema["default"]
        enum_values = schema.get("enum")
        if isinstance(enum_values, list) and enum_values:
            return enum_values[0]
        schema_type = schema.get("type")
        if isinstance(schema_type, list):
            schema_type = next((t for t in schema_type if t != "null"), schema_type[0])
        if schema_type == "string":
            fmt = schema.get("format")
            if fmt == "date-time":
                return "2024-01-01T00:00:00Z"
            if fmt == "date":
                return "2024-01-01"
            return schema.get("pattern", "<text>")
        if schema_type == "number":
            return schema.get("minimum", 0)
        if schema_type == "integer":
            return int(schema.get("minimum", 0))
        if schema_type == "boolean":
            return False
        if schema_type == "array":
            items_schema = schema.get("items", {})
            return [self._example_value_for_schema(items_schema)]
        if schema_type == "object":
            nested = schema.get("properties", {})
            required = schema.get("required", [])
            example_obj: dict[str, Any] = {}
            for key in required:
                example_obj[key] = self._example_value_for_schema(nested.get(key, {}))
            return example_obj
        return "<value>"

    async def _generate_environment_resource(
        self, context: Context, parsed_uri
    ) -> dict[str, Any]:
        """Collect environment metadata including R and Python details."""
        package_vector = ", ".join(f'"{pkg}"' for pkg in _REQUIRED_R_PACKAGES)
        r_script = f"""
packages <- c({package_vector})
package_details <- lapply(packages, function(pkg) {{
  available <- requireNamespace(pkg, quietly = TRUE)
  version <- if (available) as.character(packageVersion(pkg)) else NA_character_
  list(
    name = pkg,
    installed = available,
    version = version
  )
}})
result <- list(
  rVersion = R.version$version.string,
  platform = R.version$platform,
  packages = package_details
)
"""
        r_environment = await execute_r_script_async(r_script, {}, context)
        python_info = {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": sys.platform,
        }
        rmcp_info = {
            "readOnly": context.lifespan.read_only,
            "allowedPaths": [str(p) for p in context.lifespan.allowed_paths],
        }
        r_environment["python"] = python_info
        r_environment["rmcp"] = rmcp_info
        json_content = json.dumps(r_environment, indent=2, default=str)
        await context.info(
            "Generated environment resource",
            r_version=r_environment.get("rVersion"),
            package_count=len(r_environment.get("packages", [])),
        )
        return {
            "contents": [
                {
                    "uri": parsed_uri.geturl(),
                    "mimeType": "application/json",
                    "text": json_content,
                }
            ]
        }

    async def _generate_dataset_resource(
        self, context: Context, server: Any, parsed_uri
    ) -> dict[str, Any]:
        """Expose built-in datasets via rmcp://dataset/{name}."""
        dataset_name = parsed_uri.path.strip("/")
        if not dataset_name:
            raise ValueError(
                f"Dataset resource must specify a name: {parsed_uri.geturl()}"
            )
        query = parse_qs(parsed_uri.query)
        tool_arguments: dict[str, Any] = {"dataset_name": dataset_name}
        if "size" in query and query["size"]:
            tool_arguments["size"] = query["size"][0]
        if "add_noise" in query and query["add_noise"]:
            add_noise_value = query["add_noise"][0].lower()
            tool_arguments["add_noise"] = add_noise_value in {
                "1",
                "true",
                "yes",
                "on",
            }
        tools_registry = getattr(server, "tools", None)
        if tools_registry and "load_example" not in tools_registry._tools:
            from ..registries.tools import register_tool_functions

            register_tool_functions(tools_registry, load_example)
        load_tool = None
        if tools_registry:
            load_tool = tools_registry._tools.get("load_example")
        if not load_tool:
            raise ValueError("load_example tool is not registered")
        await context.info(
            "Resolving dataset resource",
            dataset=dataset_name,
            size=tool_arguments.get("size", "small"),
        )
        result = await load_tool.handler(context, tool_arguments)
        if isinstance(result, dict) and "_formatting" in result:
            result = {k: v for k, v in result.items() if k != "_formatting"}
        json_content = json.dumps(result, indent=2, default=str)
        await context.info(
            "Served dataset resource",
            dataset=dataset_name,
            keys=list(result.keys()),
        )
        return {
            "contents": [
                {
                    "uri": parsed_uri.geturl(),
                    "mimeType": "application/json",
                    "text": json_content,
                }
            ]
        }

    def _emit_list_changed(self, item_ids: list[str] | None = None) -> None:
        """Emit list changed notification when available."""
        if not self._on_list_changed:
            return
        try:
            self._on_list_changed(item_ids)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("List changed callback failed for resources: %s", exc)


def resource(
    uri: str,
    name: str,
    description: str | None = None,
    mime_type: str | None = None,
):
    """
    Decorator to register a static resource.

    Usage:
        @resource(
            uri="static://example",
            name="Example Resource",
            description="An example static resource"
        )
        def example_resource():
            return "resource content"
    """

    def decorator(func):
        func._mcp_resource_uri = uri
        func._mcp_resource_name = name
        func._mcp_resource_description = description
        func._mcp_resource_mime_type = mime_type
        return func

    return decorator
