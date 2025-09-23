"""Test helpers for parsing MCP tool responses."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def _get_content_items(result: Dict[str, Any]) -> List[Dict[str, Any]]:
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


def extract_text_summary(response: Dict[str, Any]) -> str:
    """Return concatenated human-readable text blocks from a tool response."""
    result = response.get("result", response)
    texts: List[str] = []
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


def extract_json_content(response: Dict[str, Any]) -> Any:
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
            if "items" in structured:
                # Multi-content wrapped format
                items_to_check = structured["items"]
            else:
                # Single content object format
                items_to_check = [structured]

        for item in items_to_check:
            if item.get("type") == "json":
                return item.get("json")

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
