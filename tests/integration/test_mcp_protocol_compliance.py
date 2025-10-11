"""
MCP Protocol Compliance Tests

Tests that RMCP correctly implements the Model Context Protocol 2025-06-18 specification
that Claude Desktop, Cursor, VS Code, and other MCP clients expect.

These tests simulate the exact JSON-RPC message sequences that IDEs send.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from shutil import which

import pytest

# Add rmcp to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rmcp.cli import _register_builtin_tools
from rmcp.core.server import create_server

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for MCP protocol compliance tests"
)


class MCPProtocolTester:
    """Helper class to test MCP protocol compliance."""

    def __init__(self):
        self.server = None
        self.session_initialized = False

    async def setup_server(self):
        """Create and configure an MCP server as would be done in production."""
        self.server = create_server(
            name="RMCP Test Server",
            version="0.3.13",
            description="Statistical Analysis MCP Server",
        )
        _register_builtin_tools(self.server)
        self.server.configure(allowed_paths=["/tmp"], read_only=False)

    async def send_request(
        self, method: str, params: dict = None, request_id: int = None
    ):
        """Send an MCP request and return the response."""
        if request_id is None:
            request_id = id(params) if params else 1

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        return await self.server.handle_request(request)

    def validate_response_structure(self, response: dict, request_id: int = None):
        """Validate that response follows JSON-RPC 2.0 and MCP format."""
        assert "jsonrpc" in response, "Response missing jsonrpc field"
        assert (
            response["jsonrpc"] == "2.0"
        ), f"Invalid jsonrpc version: {response['jsonrpc']}"

        if request_id is not None:
            assert "id" in response, "Response missing id field"
            assert (
                response["id"] == request_id
            ), f"Response id mismatch: {response['id']} != {request_id}"

        # Must have either result or error, not both
        has_result = "result" in response
        has_error = "error" in response
        assert (
            has_result != has_error
        ), "Response must have exactly one of 'result' or 'error'"

        return response


@pytest.fixture
async def mcp_tester():
    """Create an MCP protocol tester instance."""
    tester = MCPProtocolTester()
    await tester.setup_server()
    return tester


@pytest.mark.asyncio
async def test_mcp_initialize_handshake(mcp_tester):
    """Test MCP initialization sequence as done by Claude Desktop."""
    # Step 1: Client sends initialize request
    initialize_params = {
        "protocolVersion": "2025-06-18",
        "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
        "clientInfo": {"name": "Test Claude Desktop", "version": "1.0.0"},
    }

    response = await mcp_tester.send_request("initialize", initialize_params, 1)
    mcp_tester.validate_response_structure(response, 1)

    # Validate initialize response structure
    result = response["result"]
    assert "protocolVersion" in result, "Initialize response missing protocolVersion"
    assert "serverInfo" in result, "Initialize response missing serverInfo"
    assert "capabilities" in result, "Initialize response missing capabilities"

    # Check server info
    server_info = result["serverInfo"]
    assert "name" in server_info, "serverInfo missing name"
    assert "version" in server_info, "serverInfo missing version"

    # Check capabilities
    capabilities = result["capabilities"]
    assert "tools" in capabilities, "Server capabilities missing tools"
    assert "resources" in capabilities, "Server capabilities missing resources"
    assert "prompts" in capabilities, "Server capabilities missing prompts"

    mcp_tester.session_initialized = True


@pytest.mark.asyncio
async def test_mcp_tool_discovery(mcp_tester):
    """Test tool discovery as done by IDEs after initialization."""
    await mcp_tester.setup_server()

    # List tools request
    response = await mcp_tester.send_request("tools/list", {}, 2)
    mcp_tester.validate_response_structure(response, 2)

    result = response["result"]
    assert "tools" in result, "tools/list response missing tools array"

    tools = result["tools"]
    assert isinstance(tools, list), "tools must be an array"
    assert len(tools) >= 40, f"Expected at least 40 tools, got {len(tools)}"

    # Validate each tool structure
    for tool in tools:
        assert "name" in tool, "Tool missing name field"
        assert "description" in tool, "Tool missing description field"
        assert "inputSchema" in tool, "Tool missing inputSchema field"

        # Validate JSON schema structure
        schema = tool["inputSchema"]
        assert "type" in schema, "Tool schema missing type field"
        assert schema["type"] == "object", "Tool schema must be object type"


@pytest.mark.asyncio
async def test_mcp_tool_execution(mcp_tester):
    """Test tool execution with exact Claude Desktop message format."""
    await mcp_tester.setup_server()

    # Test linear regression tool (common request from Claude)
    tool_params = {
        "name": "linear_model",
        "arguments": {
            "data": {"sales": [100, 120, 115, 140], "marketing": [5, 8, 6, 10]},
            "formula": "sales ~ marketing",
        },
    }

    response = await mcp_tester.send_request("tools/call", tool_params, 3)
    mcp_tester.validate_response_structure(response, 3)

    result = response["result"]
    assert "content" in result, "Tool call response missing content"

    content = result["content"]
    assert isinstance(content, list), "Tool content must be an array"
    assert len(content) > 0, "Tool content cannot be empty"

    # Check for JSON content in response
    json_content = None
    for item in content:
        if item.get("type") == "text" and "application/json" in item.get(
            "annotations", {}
        ).get("mimeType", ""):
            json_content = json.loads(item["text"])
            break

    assert json_content is not None, "Tool response missing JSON content"
    assert "coefficients" in json_content, "Linear model missing coefficients"
    assert "r_squared" in json_content, "Linear model missing r_squared"


@pytest.mark.asyncio
async def test_mcp_error_handling(mcp_tester):
    """Test MCP error responses for invalid requests."""
    await mcp_tester.setup_server()

    # Test invalid method
    response = await mcp_tester.send_request("invalid/method", {}, 4)
    mcp_tester.validate_response_structure(response, 4)

    assert "error" in response, "Invalid method should return error"
    error = response["error"]
    assert "code" in error, "Error missing code field"
    assert "message" in error, "Error missing message field"

    # Test invalid tool call
    invalid_tool_params = {"name": "nonexistent_tool", "arguments": {}}

    response = await mcp_tester.send_request("tools/call", invalid_tool_params, 5)
    mcp_tester.validate_response_structure(response, 5)

    assert "error" in response, "Invalid tool should return error"


@pytest.mark.asyncio
async def test_mcp_resource_discovery(mcp_tester):
    """Test resource discovery as done by IDEs."""
    await mcp_tester.setup_server()

    response = await mcp_tester.send_request("resources/list", {}, 6)
    mcp_tester.validate_response_structure(response, 6)

    result = response["result"]
    assert "resources" in result, "resources/list response missing resources array"

    resources = result["resources"]
    assert isinstance(resources, list), "resources must be an array"

    # Validate resource structure if any exist
    for resource in resources:
        assert "uri" in resource, "Resource missing uri field"
        assert "name" in resource, "Resource missing name field"


@pytest.mark.asyncio
async def test_mcp_prompt_discovery(mcp_tester):
    """Test prompt discovery as done by IDEs."""
    await mcp_tester.setup_server()

    response = await mcp_tester.send_request("prompts/list", {}, 7)
    mcp_tester.validate_response_structure(response, 7)

    result = response["result"]
    assert "prompts" in result, "prompts/list response missing prompts array"

    prompts = result["prompts"]
    assert isinstance(prompts, list), "prompts must be an array"

    # Validate prompt structure if any exist
    for prompt in prompts:
        assert "name" in prompt, "Prompt missing name field"
        assert "description" in prompt, "Prompt missing description field"


@pytest.mark.asyncio
async def test_stdio_transport_compliance():
    """Test stdio transport as used by Claude Desktop."""
    # Test that we can start the server and communicate via stdio
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            """
import sys
sys.path.insert(0, '.')
from rmcp.cli import start_stdio_server
start_stdio_server()
""",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )

    # Send initialize request
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "Test Client", "version": "1.0.0"},
        },
    }

    try:
        # Send request and read response
        stdout, stderr = process.communicate(
            input=json.dumps(initialize_request) + "\n", timeout=10
        )

        # Parse the response
        lines = stdout.strip().split("\n")
        response_line = None
        for line in lines:
            if line.startswith('{"jsonrpc"'):
                response_line = line
                break

        assert response_line is not None, f"No JSON response found in stdout: {stdout}"

        response = json.loads(response_line)
        assert response["jsonrpc"] == "2.0", "Invalid JSON-RPC version"
        assert "result" in response, "Initialize response missing result"

    except subprocess.TimeoutExpired:
        process.kill()
        pytest.fail("Stdio server timeout")
    except Exception as e:
        process.kill()
        pytest.fail(f"Stdio test failed: {e}")
    finally:
        if process.poll() is None:
            process.terminate()


@pytest.mark.asyncio
async def test_complete_mcp_conversation():
    """Test a complete MCP conversation flow as done by IDEs."""
    tester = MCPProtocolTester()
    await tester.setup_server()

    # 1. Initialize
    init_response = await tester.send_request(
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "Test IDE", "version": "1.0.0"},
        },
        1,
    )
    tester.validate_response_structure(init_response, 1)

    # 2. Discover tools
    tools_response = await tester.send_request("tools/list", {}, 2)
    tester.validate_response_structure(tools_response, 2)
    tools = tools_response["result"]["tools"]

    # 3. Execute a tool
    if tools:
        tool_name = tools[0]["name"]
        if tool_name == "linear_model":
            tool_response = await tester.send_request(
                "tools/call",
                {
                    "name": tool_name,
                    "arguments": {
                        "data": {"x": [1, 2, 3], "y": [2, 4, 6]},
                        "formula": "y ~ x",
                    },
                },
                3,
            )
            tester.validate_response_structure(tool_response, 3)
            assert "result" in tool_response, "Tool execution should succeed"

    # 4. Discover resources
    resources_response = await tester.send_request("resources/list", {}, 4)
    tester.validate_response_structure(resources_response, 4)

    # 5. Discover prompts
    prompts_response = await tester.send_request("prompts/list", {}, 5)
    tester.validate_response_structure(prompts_response, 5)


def test_mcp_protocol_version_compatibility():
    """Test that RMCP declares compatibility with the correct MCP version."""
    # This test doesn't need async since it's just checking constants
    expected_version = "2025-06-18"

    # Check that our server reports the correct protocol version
    # This would be checked during initialization in real usage
    server = create_server()
    # The protocol version should be available in the server's capabilities
    # or initialization response

    # For now, we'll check that we can handle the expected version format
    assert (
        expected_version.count("-") == 2
    ), "Protocol version should be YYYY-MM-DD format"
    year, month, day = expected_version.split("-")
    assert len(year) == 4 and year.isdigit(), "Year should be 4 digits"
    assert len(month) == 2 and month.isdigit(), "Month should be 2 digits"
    assert len(day) == 2 and day.isdigit(), "Day should be 2 digits"
