"""Test helpers for parsing MCP tool responses and driving Streamable HTTP."""

from __future__ import annotations

import contextlib
import json
from typing import Any

STREAMABLE_HTTP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
    "MCP-Protocol-Version": "2025-11-25",
}


def parse_streamable_response(response: Any) -> dict[str, Any] | None:
    """Parse a Streamable HTTP POST response (JSON body or SSE stream)."""
    content_type = response.headers.get("content-type", "")
    if response.status_code == 202 or not response.content:
        return None
    if content_type.startswith("application/json"):
        return response.json()
    if content_type.startswith("text/event-stream"):
        message = None
        for line in response.text.splitlines():
            if line.startswith("data:"):
                message = json.loads(line[len("data:") :].strip())
        return message
    raise AssertionError(f"Unexpected content type: {content_type}")


@contextlib.asynccontextmanager
async def streamable_http_client(app: Any, *, headers: dict[str, str] | None = None):
    """Run a Starlette app's lifespan and yield an in-process httpx client."""
    import httpx

    merged_headers = dict(STREAMABLE_HTTP_HEADERS)
    if headers:
        merged_headers.update(headers)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver", headers=merged_headers
        ) as client:
            yield client


async def initialize_streamable_session(
    client: Any, *, protocol_version: str = "2025-11-25"
) -> tuple[dict[str, Any], dict[str, str]]:
    """Run the initialize handshake; return (result, follow-up headers)."""
    response = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "rmcp-tests", "version": "0.0.0"},
            },
        },
    )
    assert response.status_code == 200, response.text
    message = parse_streamable_response(response)
    assert message is not None and "result" in message, message
    headers: dict[str, str] = {}
    session_id = response.headers.get("mcp-session-id")
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    initialized = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers=headers,
    )
    assert initialized.status_code in (200, 202), initialized.text
    return message["result"], headers


def _get_content_items(result: dict[str, Any]) -> list[dict[str, Any]]:
    # Return both content and structuredContent items
    items = list(result.get("content", []))

    # Handle new MCP-compliant structuredContent format (object, not array)
    structured_content = result.get("structuredContent")
    if structured_content:
        if isinstance(structured_content, list):
            # Legacy array format
            items.extend(structured_content)
        elif isinstance(structured_content, dict):
            # New MCP-compliant object format
            if "items" in structured_content:
                # Multi-content wrapped format
                items.extend(structured_content["items"])
            else:
                # Single content object format
                items.append(structured_content)

    return items


def extract_text_summary(response: dict[str, Any]) -> str:
    """Return concatenated human-readable text blocks from a tool response."""
    result = response.get("result", response)
    texts: list[str] = []
    for item in _get_content_items(result):
        if item.get("type") != "text":
            continue
        annotations = item.get("annotations") or {}
        if annotations.get("mimeType") == "application/json":
            continue
        text = item.get("text")
        if text:
            texts.append(text)
    return "\n".join(texts)


def extract_json_content(response: dict[str, Any]) -> Any:
    """Return the first JSON payload embedded in a tool response."""
    result = response.get("result", response)

    # Check structuredContent first (new MCP-compliant format)
    structured = result.get("structuredContent")
    if structured:
        # Handle different structuredContent formats
        items_to_check = []
        if isinstance(structured, list):
            # Legacy array format
            items_to_check = structured
        elif isinstance(structured, dict):
            if "items" in structured and isinstance(structured["items"], list):
                # Multi-content wrapped format
                items_to_check = structured["items"]
            else:
                # Single content object format
                items_to_check = [structured]

        for item in items_to_check:
            if isinstance(item, dict) and item.get("type") == "json":
                return item.get("json")
        # Raw payload format: structuredContent IS the tool result object
        if isinstance(structured, dict) and "type" not in structured:
            return structured

    # Then check content items (legacy format)
    for item in _get_content_items(result):
        if item.get("type") == "json":
            return item.get("json")
        annotations = item.get("annotations") or {}
        if annotations.get("mimeType") == "application/json":
            text = item.get("text", "")
            if text:
                return json.loads(text)

    # Fallback: attempt to parse any text block as JSON
    for item in _get_content_items(result):
        if item.get("type") == "text" and item.get("text"):
            try:
                return json.loads(item["text"])
            except json.JSONDecodeError:
                continue

    raise AssertionError("No JSON content found in response")
