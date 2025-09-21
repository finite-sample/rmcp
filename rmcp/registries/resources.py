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
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union
from urllib.parse import urlparse

from ..core.context import Context
from ..security.vfs import VFS, VFSError

logger = logging.getLogger(__name__)


def _paginate_items(
    items: List[Dict[str, Any]], cursor: Optional[str], limit: Optional[int]
) -> tuple[List[Dict[str, Any]], Optional[str]]:
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
        on_list_changed: Optional[Callable[[Optional[List[str]]], None]] = None,
    ):
        self._static_resources: Dict[str, Dict[str, Any]] = {}
        self._memory_objects: Dict[str, Any] = {}
        self._resource_templates: Dict[str, Dict[str, Any]] = {}
        self._on_list_changed = on_list_changed

    def register_static_resource(
        self,
        uri: str,
        name: str,
        description: Optional[str] = None,
        mime_type: Optional[str] = None,
        content_loader: Optional[
            Union[str, bytes, Callable[[], Any], Callable[[], Awaitable[Any]]]
        ] = None,
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
        description: Optional[str] = None,
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
        description: Optional[str] = None,
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
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List available resources for MCP resources/list."""
        resources: List[Dict[str, Any]] = []
        for uri, resource_info in sorted(self._static_resources.items()):
            entry: Dict[str, Any] = {"uri": uri, "name": resource_info["name"]}
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
        response: Dict[str, Any] = {"resources": page}
        if next_cursor is not None:
            response["nextCursor"] = next_cursor
        return response

    async def read_resource(self, context: Context, uri: str) -> Dict[str, Any]:
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

    async def _read_file_resource(self, context: Context, parsed_uri) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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

    async def _read_static_resource(self, context: Context, uri: str) -> Dict[str, Any]:
        """Read a pre-registered static resource."""
        resource_info = self._static_resources[uri]
        loader = resource_info.get("loader")
        mime_type = resource_info.get("mimeType") or "text/plain"
        content: Any
        if loader is None:
            content = resource_info.get(
                "description", f"Static resource: {resource_info['name']}"
            )
        elif isinstance(loader, (str, bytes)):
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

    async def _read_rmcp_resource(self, context: Context, parsed_uri) -> Dict[str, Any]:
        """Read rmcp:// resource for large dataset access."""
        # Extract resource ID from URI path (rmcp://data/{resource_id})
        path_parts = parsed_uri.path.strip("/").split("/")
        if len(path_parts) != 2 or path_parts[0] != "data":
            raise ValueError(f"Invalid RMCP resource URI format: {parsed_uri.geturl()}")
        resource_id = path_parts[1]
        # Get tools registry from server context
        # This is a simplified approach - in production you might want a dedicated data store
        server = getattr(context, "_server", None)
        if not server:
            raise ValueError("Server context not available for RMCP resource access")
        tools_registry = getattr(server, "tools", None)
        if not tools_registry:
            raise ValueError("Tools registry not available for RMCP resource access")
        # Check if the resource exists in the large data store
        if not hasattr(tools_registry, "_large_data_store"):
            raise ValueError(f"RMCP resource not found: {resource_id}")
        data_store = tools_registry._large_data_store
        if resource_id not in data_store:
            raise ValueError(f"RMCP resource not found: {resource_id}")
        # Retrieve the stored data
        stored_resource = data_store[resource_id]
        data = stored_resource["data"]
        content_type = stored_resource.get("content_type", "application/json")
        # Convert data to JSON string
        import json

        json_content = json.dumps(data, indent=2, default=str)
        await context.info(
            f"Retrieved RMCP resource: {resource_id}",
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

    def _emit_list_changed(self, item_ids: Optional[List[str]] = None) -> None:
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
    description: Optional[str] = None,
    mime_type: Optional[str] = None,
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
