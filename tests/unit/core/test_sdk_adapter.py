"""End-to-end tests of the SDK adapter using the official in-memory client."""

import contextlib

import anyio
import mcp.types as types
import pytest
from mcp import ClientSession
from mcp.shared.memory import create_client_server_memory_streams
from rmcp.core.sdk_adapter import build_sdk_server
from rmcp.core.server import create_server
from rmcp.registries.prompts import (
    register_prompt_functions,
    statistical_workflow_prompt,
)


@contextlib.asynccontextmanager
async def create_connected_server_and_client_session(server):
    """In-memory client wired to `server`.

    Replaces mcp 1.x's helper of the same name, removed in 2.x.
    """
    async with create_client_server_memory_streams() as (
        (client_read, client_write),
        (server_read, server_write),
    ):
        async with anyio.create_task_group() as tg:

            async def _serve() -> None:
                with contextlib.suppress(Exception):
                    await server.run(
                        server_read,
                        server_write,
                        server.create_initialization_options(),
                        raise_exceptions=True,
                    )

            tg.start_soon(_serve)
            async with ClientSession(client_read, client_write) as session:
                await session.initialize()
                yield session
            tg.cancel_scope.cancel()


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
    assert caps.resources is not None and caps.resources.list_changed
    assert caps.prompts is not None
    assert caps.logging is None


async def test_list_and_call_tool(rmcp_server):
    adapter = build_sdk_server(rmcp_server)
    async with create_connected_server_and_client_session(
        adapter.sdk_server
    ) as session:
        tools = await session.list_tools()
        names = [tool.name for tool in tools.tools]
        assert "echo" in names
        echo = next(tool for tool in tools.tools if tool.name == "echo")
        # outputSchema is not advertised: it dominated the tools/list payload
        # without telling the model anything the first result doesn't.
        assert echo.output_schema is None

        result = await session.call_tool("echo", {"message": "hello"})
        assert result.is_error is not True
        # ...but results are still validated against it server-side
        assert result.structured_content == {"echoed": "hello", "length": 5}


async def test_call_tool_error_shape(rmcp_server):
    adapter = build_sdk_server(rmcp_server)
    async with create_connected_server_and_client_session(
        adapter.sdk_server
    ) as session:
        result = await session.call_tool("always_fails", {})
        assert result.is_error is True
        assert "deliberate failure" in result.content[0].text

        unknown = await session.call_tool("does_not_exist", {})
        assert unknown.is_error is True


async def test_input_validation_error(rmcp_server):
    adapter = build_sdk_server(rmcp_server)
    async with create_connected_server_and_client_session(
        adapter.sdk_server
    ) as session:
        result = await session.call_tool("echo", {"message": 42})
        assert result.is_error is True


async def test_list_tools_pagination(rmcp_server):
    adapter = build_sdk_server(rmcp_server)
    async with create_connected_server_and_client_session(
        adapter.sdk_server
    ) as session:
        # ClientRequest is a union in mcp 2.x, so raw request construction is
        # gone; the client takes pagination params directly.
        first = await session.list_tools(
            params=types.PaginatedRequestParams(cursor=None)
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
        template_uris = [t.uri_template for t in templates.resource_templates]
        assert "rmcp://dataset/{name}" in template_uris

        readme = await session.read_resource("rmcp://docs/readme")
        assert readme.contents
        first = readme.contents[0]
        assert isinstance(first, types.TextResourceContents)
        assert "RMCP" in first.text or "rmcp" in first.text
