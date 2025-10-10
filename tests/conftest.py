"""Shared pytest fixtures for RMCP tests."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from rmcp.core.context import Context  # noqa: E402
from rmcp.core.server import create_server  # noqa: E402
from rmcp.registries.tools import register_tool_functions  # noqa: E402


@pytest.fixture
def server_factory() -> Callable[..., Any]:
    """Return a factory that creates MCP servers with optional tool registration."""

    def _factory(*tools: Any) -> Any:
        server = create_server()
        if tools:
            register_tool_functions(server.tools, *tools)
        return server

    return _factory


@pytest.fixture
def context_factory() -> Callable[..., Context]:
    """Return a factory that creates request contexts for a server."""

    def _factory(
        server: Any,
        *,
        request_id: str = "test",
        method: str = "test",
    ) -> Context:
        return Context.create(request_id, method, server.lifespan_state)

    return _factory
