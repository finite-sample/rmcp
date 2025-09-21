"""Test helpers for parsing MCP tool responses."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def _get_content_items(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(result.get("content", []))


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
