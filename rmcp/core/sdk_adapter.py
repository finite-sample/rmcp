"""
Bridge between RMCP's registries and the official MCP Python SDK.

The registries (tools/resources/prompts) remain the domain layer and keep
returning spec-shaped dicts; this module exposes them through the SDK's
low-level ``Server`` so that protocol lifecycle, capabilities, and transports
(stdio, Streamable HTTP) are handled by the SDK instead of hand-rolled code.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from typing import TYPE_CHECKING, Any

import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from ..logging_config import set_request_id
from .context import Context

if TYPE_CHECKING:
    from .server import MCPServer

logger = logging.getLogger(__name__)


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
        # Sessions that issued resources/subscribe
        self._subscribed_sessions: set[Any] = set()
        # mcp 2.x takes handlers as constructor arguments; the decorator
        # registration API (@server.list_tools() and friends) was removed.
        self.sdk_server: Server = _RMCPSDKServer(
            name=rmcp_server.name,
            version=rmcp_server.version,
            instructions=rmcp_server.description or None,
            on_list_tools=self._on_list_tools,
            on_call_tool=self._on_call_tool,
            on_list_resources=self._on_list_resources,
            on_list_resource_templates=self._on_list_resource_templates,
            on_read_resource=self._on_read_resource,
            on_subscribe_resource=self._on_subscribe_resource,
            on_unsubscribe_resource=self._on_unsubscribe_resource,
            on_list_prompts=self._on_list_prompts,
            on_get_prompt=self._on_get_prompt,
        )
        rmcp_server.add_list_changed_listener(self._on_list_changed)

    # ------------------------------------------------------------------
    # Context plumbing
    # ------------------------------------------------------------------
    def _create_context(self, ctx: Any, method: str) -> Context:
        """Create an RMCP context whose feedback flows through the SDK session.

        mcp 2.x hands the request context to the handler, so there is no
        contextvar lookup to fail; ``ctx`` is always present.
        """
        session = getattr(ctx, "session", None)
        request_id = str(getattr(ctx, "request_id", None) or uuid.uuid4())
        progress_token: str | int | None = None
        meta = getattr(ctx, "meta", None)
        if meta is not None:
            progress_token = getattr(meta, "progressToken", None)

        # Publish these so every line logged while serving this request carries
        # them. asyncio copies the context into child tasks, so the R execution
        # under a tool call is correlatable with the call itself.
        set_request_id(request_id)

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
            logger.log(
                getattr(logging, level.upper(), logging.INFO),
                "%s: %s %s",
                request_id,
                message,
                data,
            )

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
    #
    # mcp 2.x hands each handler ``(ctx, params)`` and expects a typed result,
    # where 1.x passed unpacked arguments and accepted bare lists.
    # ------------------------------------------------------------------
    async def _on_list_tools(
        self, ctx: Any, params: Any = None
    ) -> types.ListToolsResult:
        context = self._create_context(ctx, "tools/list")
        try:
            cursor = getattr(params, "cursor", None) if params is not None else None
            result = await self.rmcp_server.tools.list_tools(context, cursor=cursor)
            return types.ListToolsResult.model_validate(result)
        finally:
            self._finish(context)

    async def _on_call_tool(self, ctx: Any, params: Any) -> types.CallToolResult:
        # Input validation stays in the registry, for a single error shape.
        context = self._create_context(ctx, "tools/call")
        try:
            result = await self.rmcp_server.tools.call_tool(
                context, params.name, params.arguments or {}
            )
            return types.CallToolResult.model_validate(result)
        except Exception as exc:
            # The registry converts handler failures to isError itself, but an
            # unknown tool raises before that. 1.x's decorator turned it into an
            # isError result; 2.x would propagate it as a protocol error. Keep
            # the shape clients already see.
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=str(exc))],
                is_error=True,
            )
        finally:
            self._finish(context)

    async def _on_list_resources(
        self, ctx: Any, params: Any = None
    ) -> types.ListResourcesResult:
        context = self._create_context(ctx, "resources/list")
        try:
            cursor = getattr(params, "cursor", None) if params is not None else None
            result = await self.rmcp_server.resources.list_resources(
                context, cursor=cursor
            )
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

    async def _on_list_resource_templates(
        self, ctx: Any, params: Any = None
    ) -> types.ListResourceTemplatesResult:
        return types.ListResourceTemplatesResult(
            resource_templates=[
                types.ResourceTemplate(
                    uri_template=uri_template,
                    name=meta.get("name", uri_template),
                    description=meta.get("description"),
                )
                for uri_template, meta in sorted(
                    self.rmcp_server.resources.iter_templates()
                )
            ]
        )

    async def _on_read_resource(
        self, ctx: Any, params: Any
    ) -> types.ReadResourceResult:
        context = self._create_context(ctx, "resources/read")
        try:
            result = await self.rmcp_server.resources.read_resource(
                context, str(params.uri)
            )
            contents: list[Any] = []
            for item in result.get("contents", []):
                entry: dict[str, Any] = {"uri": item.get("uri", str(params.uri))}
                if item.get("mimeType"):
                    entry["mimeType"] = item["mimeType"]
                if "blob" in item:
                    entry["blob"] = item["blob"]
                else:
                    entry["text"] = item.get("text", "")
                contents.append(entry)
            return types.ReadResourceResult.model_validate({"contents": contents})
        finally:
            self._finish(context)

    async def _on_subscribe_resource(self, ctx: Any, params: Any) -> types.EmptyResult:
        session = getattr(ctx, "session", None)
        if session is not None:
            self._subscribed_sessions.add(session)
        return types.EmptyResult()

    async def _on_unsubscribe_resource(
        self, ctx: Any, params: Any
    ) -> types.EmptyResult:
        session = getattr(ctx, "session", None)
        if session is not None:
            self._subscribed_sessions.discard(session)
        return types.EmptyResult()

    async def _on_list_prompts(
        self, ctx: Any, params: Any = None
    ) -> types.ListPromptsResult:
        context = self._create_context(ctx, "prompts/list")
        try:
            cursor = getattr(params, "cursor", None) if params is not None else None
            result = await self.rmcp_server.prompts.list_prompts(context, cursor=cursor)
            prompts = [
                _convert_prompt_entry(entry) for entry in result.get("prompts", [])
            ]
            payload: dict[str, Any] = {"prompts": prompts}
            if result.get("nextCursor") is not None:
                payload["nextCursor"] = result["nextCursor"]
            return types.ListPromptsResult.model_validate(payload)
        finally:
            self._finish(context)

    async def _on_get_prompt(self, ctx: Any, params: Any) -> types.GetPromptResult:
        context = self._create_context(ctx, "prompts/get")
        try:
            result = await self.rmcp_server.prompts.get_prompt(
                context, params.name, params.arguments or {}
            )
            return types.GetPromptResult.model_validate(result)
        finally:
            self._finish(context)

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
