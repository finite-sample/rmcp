"""
Bridge between RMCP's registries and the official MCP Python SDK.

The registries (tools/resources/prompts) remain the domain layer and keep
returning spec-shaped dicts; this module exposes them through the SDK's
low-level ``Server`` so that protocol lifecycle, capabilities, and transports
(stdio, Streamable HTTP) are handled by the SDK instead of hand-rolled code.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import logging
import uuid
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl

from .context import Context

if TYPE_CHECKING:
    from .server import MCPServer

logger = logging.getLogger(__name__)

_MCP_TO_PYTHON_LOG_LEVEL = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "notice": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "alert": logging.CRITICAL,
    "emergency": logging.CRITICAL,
}

_PYTHON_TO_MCP_LOG_LEVEL: dict[str, types.LoggingLevel] = {
    "debug": "debug",
    "info": "info",
    "warning": "warning",
    "error": "error",
    "critical": "critical",
}


class _RMCPSDKServer(Server):
    """SDK server that advertises resource list_changed by default.

    Transports like the Streamable HTTP session manager call
    ``create_initialization_options()`` with no arguments; this default keeps
    the advertised capabilities consistent across transports.
    """

    def create_initialization_options(
        self,
        notification_options: NotificationOptions | None = None,
        experimental_capabilities: dict[str, dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> InitializationOptions:
        return super().create_initialization_options(
            notification_options or NotificationOptions(resources_changed=True),
            experimental_capabilities,
            **kwargs,
        )


class SDKServerAdapter:
    """Wraps an :class:`MCPServer` and exposes it as an SDK ``Server``."""

    def __init__(self, rmcp_server: MCPServer):
        self.rmcp_server = rmcp_server
        self.sdk_server: Server = _RMCPSDKServer(
            name=rmcp_server.name,
            version=rmcp_server.version,
            instructions=rmcp_server.description or None,
        )
        # Sessions that issued resources/subscribe
        self._subscribed_sessions: set[Any] = set()
        self._register_handlers()
        rmcp_server.add_list_changed_listener(self._on_list_changed)

    # ------------------------------------------------------------------
    # Context plumbing
    # ------------------------------------------------------------------
    def _create_context(self, method: str) -> Context:
        """Create an RMCP context whose feedback flows through the SDK session."""
        session = None
        request_id = str(uuid.uuid4())
        progress_token: str | int | None = None
        try:
            rc = self.sdk_server.request_context
            session = rc.session
            request_id = str(rc.request_id)
            if rc.meta is not None:
                progress_token = rc.meta.progressToken
        except LookupError:
            pass

        async def progress_callback(message: str, current: int, total: int) -> None:
            if session is None or progress_token is None:
                logger.info(
                    "Progress %s: %s (%s/%s)", request_id, message, current, total
                )
                return
            try:
                await session.send_progress_notification(
                    progress_token, float(current), total=float(total), message=message
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to send progress notification: %s", exc)

        async def log_callback(level: str, message: str, data: dict[str, Any]) -> None:
            mcp_level = _PYTHON_TO_MCP_LOG_LEVEL.get(level.lower(), "info")
            if session is None:
                logger.log(
                    _MCP_TO_PYTHON_LOG_LEVEL.get(mcp_level, logging.INFO),
                    "%s: %s %s",
                    request_id,
                    message,
                    data,
                )
                return
            try:
                await session.send_log_message(
                    level=mcp_level,
                    data={"message": message, **data},
                    logger="rmcp",
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to send log notification: %s", exc)

        context = Context.create(
            request_id=request_id,
            method=method,
            lifespan_state=self.rmcp_server.lifespan_state,
            progress_token=str(progress_token) if progress_token is not None else None,
            progress_callback=progress_callback,
            log_callback=log_callback,
        )
        context._server = self.rmcp_server
        self.rmcp_server._active_requests[request_id] = context.request
        return context

    def _finish(self, context: Context) -> None:
        self.rmcp_server.finish_request(context.request.request_id)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _register_handlers(self) -> None:
        sdk = self.sdk_server
        rmcp = self.rmcp_server

        @sdk.list_tools()
        async def list_tools(req: types.ListToolsRequest) -> types.ListToolsResult:
            context = self._create_context("tools/list")
            try:
                cursor = req.params.cursor if req is not None and req.params else None
                result = await rmcp.tools.list_tools(context, cursor=cursor)
                return types.ListToolsResult.model_validate(result)
            finally:
                self._finish(context)

        # Input validation is handled by the registry (single error shape).
        @sdk.call_tool(validate_input=False)
        async def call_tool(
            name: str, arguments: dict[str, Any]
        ) -> types.CallToolResult:
            context = self._create_context("tools/call")
            try:
                result = await rmcp.tools.call_tool(context, name, arguments)
                return types.CallToolResult.model_validate(result)
            finally:
                self._finish(context)

        @sdk.list_resources()
        async def list_resources(
            req: types.ListResourcesRequest,
        ) -> types.ListResourcesResult:
            context = self._create_context("resources/list")
            try:
                cursor = req.params.cursor if req is not None and req.params else None
                result = await rmcp.resources.list_resources(context, cursor=cursor)
                # URI templates are exposed via resources/templates/list instead.
                entries = [
                    entry
                    for entry in result.get("resources", [])
                    if "{" not in entry.get("uri", "")
                ]
                payload: dict[str, Any] = {"resources": entries}
                if result.get("nextCursor") is not None:
                    payload["nextCursor"] = result["nextCursor"]
                return types.ListResourcesResult.model_validate(payload)
            finally:
                self._finish(context)

        @sdk.list_resource_templates()
        async def list_resource_templates() -> list[types.ResourceTemplate]:
            return [
                types.ResourceTemplate(
                    uriTemplate=uri_template,
                    name=meta.get("name", uri_template),
                    description=meta.get("description"),
                )
                for uri_template, meta in sorted(rmcp.resources.iter_templates())
            ]

        @sdk.read_resource()
        async def read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
            context = self._create_context("resources/read")
            try:
                result = await rmcp.resources.read_resource(context, str(uri))
                contents: list[ReadResourceContents] = []
                for item in result.get("contents", []):
                    mime_type = item.get("mimeType")
                    if "blob" in item:
                        data: str | bytes = base64.b64decode(item["blob"])
                    else:
                        data = item.get("text", "")
                    contents.append(
                        ReadResourceContents(content=data, mime_type=mime_type)
                    )
                return contents
            finally:
                self._finish(context)

        @sdk.subscribe_resource()
        async def subscribe_resource(uri: AnyUrl) -> None:
            with contextlib.suppress(LookupError):
                self._subscribed_sessions.add(sdk.request_context.session)

        @sdk.unsubscribe_resource()
        async def unsubscribe_resource(uri: AnyUrl) -> None:
            with contextlib.suppress(LookupError):
                self._subscribed_sessions.discard(sdk.request_context.session)

        @sdk.list_prompts()
        async def list_prompts(
            req: types.ListPromptsRequest,
        ) -> types.ListPromptsResult:
            context = self._create_context("prompts/list")
            try:
                cursor = req.params.cursor if req is not None and req.params else None
                result = await rmcp.prompts.list_prompts(context, cursor=cursor)
                prompts = [
                    _convert_prompt_entry(entry) for entry in result.get("prompts", [])
                ]
                payload: dict[str, Any] = {"prompts": prompts}
                if result.get("nextCursor") is not None:
                    payload["nextCursor"] = result["nextCursor"]
                return types.ListPromptsResult.model_validate(payload)
            finally:
                self._finish(context)

        @sdk.get_prompt()
        async def get_prompt(
            name: str, arguments: dict[str, str] | None
        ) -> types.GetPromptResult:
            context = self._create_context("prompts/get")
            try:
                result = await rmcp.prompts.get_prompt(context, name, arguments or {})
                return types.GetPromptResult.model_validate(result)
            finally:
                self._finish(context)

        @sdk.set_logging_level()
        async def set_logging_level(level: types.LoggingLevel) -> None:
            await rmcp._handle_set_log_level(level)

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _on_list_changed(self, kind: str, item_ids: list[str] | None) -> None:
        """Forward registry list_changed events to subscribed SDK sessions."""
        if kind != "resources" or not self._subscribed_sessions:
            return
        sessions = list(self._subscribed_sessions)

        async def _notify() -> None:
            for session in sessions:
                try:
                    await session.send_resource_list_changed()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.debug("Dropping resource notification: %s", exc)
                    self._subscribed_sessions.discard(session)

        # Registry events fire either at startup (no loop -> nothing to notify)
        # or from within a running request handler on the event loop.
        with contextlib.suppress(RuntimeError):
            asyncio.get_running_loop().create_task(_notify())

    # ------------------------------------------------------------------
    # Initialization options
    # ------------------------------------------------------------------
    def initialization_options(self) -> InitializationOptions:
        return self.sdk_server.create_initialization_options()


def _convert_prompt_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Convert registry prompt info (argumentsSchema) to spec Prompt shape."""
    prompt: dict[str, Any] = {
        "name": entry["name"],
        "title": entry.get("title"),
        "description": entry.get("description"),
    }
    schema = entry.get("argumentsSchema") or {}
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    if properties:
        prompt["arguments"] = [
            {
                "name": arg_name,
                "description": arg_schema.get("description"),
                "required": arg_name in required,
            }
            for arg_name, arg_schema in properties.items()
        ]
    return prompt


def build_sdk_server(rmcp_server: MCPServer) -> SDKServerAdapter:
    """Create an SDK adapter for the given RMCP server."""
    return SDKServerAdapter(rmcp_server)
