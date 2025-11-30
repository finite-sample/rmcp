#!/usr/bin/env python3
"""
Integration tests for resource registry functionality.
Tests resource endpoints using real R execution instead of mocks.
"""

import json
from shutil import which

import pytest
from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions
from rmcp.tools.helpers import load_example

# Add rmcp to path


pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for resource registry tests"
)


@pytest.mark.asyncio
async def test_catalog_resource_lists_registered_tools():
    """rmcp://catalog exposes tool metadata with real R execution."""
    server = create_server()
    register_tool_functions(server.tools, load_example)

    # No mocking - use real R execution for load_example tool
    context = server.create_context("res-cat", "resources/read")
    result = await server.resources.read_resource(context, "rmcp://catalog")
    markdown = result["contents"][0]["text"]
    assert "load_example" in markdown
    assert '"tool": "load_example"' in markdown


@pytest.mark.asyncio
async def test_environment_resource_reports_versions():
    """rmcp://env returns real R and Python environment details."""
    server = create_server()
    context = server.create_context("res-env", "resources/read")
    result = await server.resources.read_resource(context, "rmcp://env")
    payload = json.loads(result["contents"][0]["text"])

    # Verify real R environment information
    assert "rVersion" in payload
    assert "R" in payload["rVersion"]  # Should contain actual R version
    assert "platform" in payload
    assert "packages" in payload
    assert isinstance(payload["packages"], list)
    assert "python" in payload
    assert "rmcp" in payload
    assert payload["rmcp"]["readOnly"] is True


@pytest.mark.asyncio
async def test_dataset_resource_streams_example():
    """rmcp://dataset/{name} proxies real load_example tool output."""
    server = create_server()
    register_tool_functions(server.tools, load_example)
    context = server.create_context("res-data", "resources/read")

    # Use real R execution for load_example
    result = await server.resources.read_resource(
        context, "rmcp://dataset/sales?size=medium&add_noise=true"
    )
    payload = json.loads(result["contents"][0]["text"])

    # Verify real dataset generation
    assert payload["metadata"]["name"] == "sales"
    assert payload["metadata"]["size"] == "medium"
    assert payload["metadata"]["has_noise"] is True
    assert "data" in payload
    assert isinstance(payload["data"], dict)
    assert "metadata" in payload
    assert payload["metadata"]["rows"] > 0  # Real data should have rows
