"""End-to-end tests of the SDK adapter using the official in-memory client."""

import mcp.types as types
import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from rmcp.core.sdk_adapter import build_sdk_server
from rmcp.core.server import create_server
from rmcp.registries.prompts import (
    register_prompt_functions,
    statistical_workflow_prompt,
)


def _make_server(tmp_path):
    server = create_server()
    server.configure(allowed_paths=[str(tmp_path)], read_only=True)

    async def echo_handler(context, params):
        return {
            "echoed": params.get("message", ""),
            "length": len(params.get("message", "")),
        }

    server.tools.register(
        name="echo",
        handler=echo_handler,
        input_schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "echoed": {"type": "string"},
                "length": {"type": "integer"},
            },
            "required": ["echoed", "length"],
            "additionalProperties": False,
        },
        description="Echo a message back",
    )

    async def fail_handler(context, params):
        raise RuntimeError("deliberate failure")

    server.tools.register(
        name="always_fails",
        handler=fail_handler,
        input_schema={"type": "object", "properties": {}},
        description="Always raises",
    )

    register_prompt_functions(server.prompts, statistical_workflow_prompt)
    return server


@pytest.fixture
def rmcp_server(tmp_path):
    return _make_server(tmp_path)


async def test_initialize_and_capabilities(rmcp_server):
    adapter = build_sdk_server(rmcp_server)
    options = adapter.initialization_options()
    assert options.server_name == rmcp_server.name
    assert options.server_version == rmcp_server.version
    caps = options.capabilities
    assert caps.tools is not None
    assert caps.resources is not None and caps.resources.listChanged
    assert caps.prompts is not None
    assert caps.logging is not None


async def test_list_and_call_tool(rmcp_server):
    adapter = build_sdk_server(rmcp_server)
    async with create_connected_server_and_client_session(
        adapter.sdk_server
    ) as session:
        tools = await session.list_tools()
        names = [tool.name for tool in tools.tools]
        assert "echo" in names
        echo = next(tool for tool in tools.tools if tool.name == "echo")
        assert echo.outputSchema is not None

        result = await session.call_tool("echo", {"message": "hello"})
        assert result.isError is not True
        # structuredContent is the raw payload and conforms to outputSchema
        assert result.structuredContent == {"echoed": "hello", "length": 5}


async def test_call_tool_error_shape(rmcp_server):
    adapter = build_sdk_server(rmcp_server)
    async with create_connected_server_and_client_session(
        adapter.sdk_server
    ) as session:
        result = await session.call_tool("always_fails", {})
        assert result.isError is True
        assert "deliberate failure" in result.content[0].text

        unknown = await session.call_tool("does_not_exist", {})
        assert unknown.isError is True


async def test_input_validation_error(rmcp_server):
    adapter = build_sdk_server(rmcp_server)
    async with create_connected_server_and_client_session(
        adapter.sdk_server
    ) as session:
        result = await session.call_tool("echo", {"message": 42})
        assert result.isError is True


async def test_list_tools_pagination(rmcp_server):
    adapter = build_sdk_server(rmcp_server)
    async with create_connected_server_and_client_session(
        adapter.sdk_server
    ) as session:
        first = await session.send_request(
            types.ClientRequest(
                types.ListToolsRequest(
                    method="tools/list",
                    params=types.PaginatedRequestParams(cursor=None),
                )
            ),
            types.ListToolsResult,
        )
        assert len(first.tools) >= 2


async def test_prompts_round_trip(rmcp_server):
    adapter = build_sdk_server(rmcp_server)
    async with create_connected_server_and_client_session(
        adapter.sdk_server
    ) as session:
        prompts = await session.list_prompts()
        names = [prompt.name for prompt in prompts.prompts]
        assert "statistical_workflow" in names
        workflow = next(p for p in prompts.prompts if p.name == "statistical_workflow")
        # argumentsSchema converted to spec arguments list
        assert workflow.arguments, "expected prompt arguments to be exposed"

        args = {arg.name: "test" for arg in workflow.arguments if arg.required}
        rendered = await session.get_prompt("statistical_workflow", args)
        assert rendered.messages
        assert rendered.messages[0].role == "user"


async def test_resources_round_trip(rmcp_server):
    adapter = build_sdk_server(rmcp_server)
    async with create_connected_server_and_client_session(
        adapter.sdk_server
    ) as session:
        resources = await session.list_resources()
        uris = [str(resource.uri) for resource in resources.resources]
        # Templates must not leak into resources/list
        assert not any("{" in uri for uri in uris)
        assert any(uri.startswith("rmcp://") for uri in uris)

        templates = await session.list_resource_templates()
        template_uris = [t.uriTemplate for t in templates.resourceTemplates]
        assert "rmcp://dataset/{name}" in template_uris

        readme = await session.read_resource("rmcp://docs/readme")
        assert readme.contents
        first = readme.contents[0]
        assert isinstance(first, types.TextResourceContents)
        assert "RMCP" in first.text or "rmcp" in first.text


async def test_logging_set_level(rmcp_server):
    adapter = build_sdk_server(rmcp_server)
    async with create_connected_server_and_client_session(
        adapter.sdk_server
    ) as session:
        await session.set_logging_level("debug")
        assert rmcp_server.lifespan_state.current_log_level == "debug"
