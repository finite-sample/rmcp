import json

import pytest

from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions
from rmcp.tools.helpers import load_example


@pytest.mark.asyncio
async def test_catalog_resource_lists_registered_tools(monkeypatch):
    """rmcp://catalog exposes tool metadata with minimal examples."""
    server = create_server()
    register_tool_functions(server.tools, load_example)

    async def fake_execute(script: str, params: dict, context=None):
        return {
            "data": {"value": [1, 2, 3]},
            "metadata": {
                "name": params["dataset_name"],
                "description": "stub",
                "size": params.get("size", "small"),
                "rows": 3,
                "columns": 1,
                "has_noise": params.get("add_noise", False),
            },
            "statistics": {},
            "suggested_analyses": [],
            "variable_info": {
                "numeric_variables": [],
                "categorical_variables": [],
                "variable_types": {},
            },
        }

    monkeypatch.setattr("rmcp.tools.helpers.execute_r_script_async", fake_execute)
    context = server.create_context("res-cat", "resources/read")
    result = await server.resources.read_resource(context, "rmcp://catalog")
    markdown = result["contents"][0]["text"]
    assert "load_example" in markdown
    assert '"tool": "load_example"' in markdown


@pytest.mark.asyncio
async def test_environment_resource_reports_versions(monkeypatch):
    """rmcp://env returns R and Python environment details."""

    async def fake_env(script: str, params: dict, context=None):
        return {
            "rVersion": "R 4.3.2",
            "platform": "x86_64-pc-linux-gnu",
            "packages": [{"name": "jsonlite", "installed": True, "version": "1.8.8"}],
        }

    monkeypatch.setattr("rmcp.registries.resources.execute_r_script_async", fake_env)
    server = create_server()
    context = server.create_context("res-env", "resources/read")
    result = await server.resources.read_resource(context, "rmcp://env")
    payload = json.loads(result["contents"][0]["text"])
    assert payload["rVersion"] == "R 4.3.2"
    assert payload["packages"][0]["name"] == "jsonlite"
    assert "python" in payload
    assert payload["rmcp"]["readOnly"] is True


@pytest.mark.asyncio
async def test_dataset_resource_streams_example(monkeypatch):
    """rmcp://dataset/{name} proxies the load_example tool output."""

    async def fake_execute(script: str, params: dict, context=None):
        name = params["dataset_name"]
        size = params.get("size", "small")
        return {
            "data": {"value": [1, 2]},
            "metadata": {
                "name": name,
                "description": f"Example dataset: {name}",
                "size": size,
                "rows": 2,
                "columns": 1,
                "has_noise": params.get("add_noise", False),
            },
            "statistics": {},
            "suggested_analyses": [],
            "variable_info": {
                "numeric_variables": [],
                "categorical_variables": [],
                "variable_types": {},
            },
        }

    monkeypatch.setattr("rmcp.tools.helpers.execute_r_script_async", fake_execute)
    server = create_server()
    register_tool_functions(server.tools, load_example)
    context = server.create_context("res-data", "resources/read")
    result = await server.resources.read_resource(
        context, "rmcp://dataset/sales?size=medium&add_noise=true"
    )
    payload = json.loads(result["contents"][0]["text"])
    assert payload["metadata"]["name"] == "sales"
    assert payload["metadata"]["size"] == "medium"
    assert payload["metadata"]["has_noise"] is True
    assert payload["data"]["value"] == [1, 2]
