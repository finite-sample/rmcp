"""
Resources registry for MCP server.

Implements mature MCP patterns:
- Read-only endpoints for files and in-memory objects
- URI-based addressing (file://, mem://)
- Resource templates for parameterized access
- VFS integration for security

Following the principle: "Keeps data access explicit and auditable."
"""

from typing import Any, Dict, List, Optional, Union, Callable, Awaitable
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import base64
import logging

from ..core.context import Context
from ..security.vfs import VFS, VFSError

logger = logging.getLogger(__name__)


class ResourcesRegistry:
    """Registry for MCP resources with VFS security."""
    
    def __init__(self):
        self._static_resources: Dict[str, Dict[str, Any]] = {}
        self._memory_objects: Dict[str, Any] = {}
        self._resource_templates: Dict[str, str] = {}
    
    def register_static_resource(
        self,
        uri: str,
        name: str,
        description: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> None:
        """Register a static resource."""
        
        self._static_resources[uri] = {
            "uri": uri,
            "name": name, 
            "description": description or f"Resource: {name}",
            "mimeType": mime_type,
        }
        
        logger.debug(f"Registered static resource: {uri}")
    
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
    
    def register_resource_template(
        self,
        uri_template: str,
        name: str,
        description: Optional[str] = None,
    ) -> None:
        """Register a parameterized resource template."""
        
        self._resource_templates[uri_template] = name
        
        logger.debug(f"Registered resource template: {uri_template}")
    
    async def list_resources(self, context: Context) -> Dict[str, Any]:
        """List available resources for MCP resources/list."""
        
        resources = []
        
        # Static resources
        for resource_info in self._static_resources.values():
            resources.append(resource_info)
        
        # Resource templates
        for uri_template, name in self._resource_templates.items():
            resources.append({
                "uri": uri_template,
                "name": name,
                "description": f"Template: {name}",
            })
        
        # File system resources (if VFS configured)
        if hasattr(context.lifespan, 'vfs') and context.lifespan.vfs:
            for mount_name, mount_path in context.lifespan.resource_mounts.items():
                resources.append({
                    "uri": f"file://{mount_name}/",
                    "name": f"Files: {mount_name}",
                    "description": f"File system mount: {mount_path}",
                })
        
        await context.info(f"Listed {len(resources)} available resources")
        
        return {"resources": resources}
    
    async def read_resource(self, context: Context, uri: str) -> Dict[str, Any]:
        """Read a resource for MCP resources/read."""
        
        try:
            parsed_uri = urlparse(uri)
            scheme = parsed_uri.scheme
            
            if scheme == "file":
                return await self._read_file_resource(context, parsed_uri)
            elif scheme == "mem":
                return await self._read_memory_resource(context, parsed_uri)
            else:
                # Check static resources
                if uri in self._static_resources:
                    return await self._read_static_resource(context, uri)
                else:
                    raise ValueError(f"Unsupported resource scheme or unknown URI: {uri}")
        
        except Exception as e:
            await context.error(f"Failed to read resource {uri}: {e}")
            raise
    
    async def _read_file_resource(self, context: Context, parsed_uri) -> Dict[str, Any]:
        """Read file:// resource using VFS."""
        
        # Extract path from URI
        file_path = Path(parsed_uri.path)
        
        try:
            # Use VFS for secure file access
            if hasattr(context.lifespan, 'vfs') and context.lifespan.vfs:
                vfs = context.lifespan.vfs
            else:
                # Fallback to direct path validation
                context.require_path_access(file_path)
                content = file_path.read_bytes()
                mime_type = "application/octet-stream"
            
            if 'vfs' in locals():
                content = vfs.read_file(file_path)
                file_info = vfs.file_info(file_path)
                mime_type = file_info.get("mime_type", "application/octet-stream")
            
            # Determine if content should be base64 encoded
            is_text = mime_type and mime_type.startswith("text/")
            
            if is_text:
                try:
                    text_content = content.decode('utf-8')
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
            b64_content = base64.b64encode(content).decode('ascii')
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
    
    async def _read_memory_resource(self, context: Context, parsed_uri) -> Dict[str, Any]:
        """Read mem:// resource from memory objects."""
        
        # Extract object name from URI path
        path_parts = parsed_uri.path.strip('/').split('/')
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
        
        # Static resources would need their content defined somewhere
        # For now, return placeholder
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": resource_info.get("mimeType", "text/plain"),
                    "text": f"Static resource: {resource_info['name']}",
                }
            ]
        }


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