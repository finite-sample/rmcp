"""
Real Claude Desktop End-to-End Integration Tests

These tests validate actual Claude Desktop integration by:
1. Testing real MCP communication with Claude Desktop app
2. Validating configuration files and setup
3. Testing real-world user workflows
4. Performance and reliability testing

Requirements:
- Claude Desktop app installed and configured
- RMCP configured in Claude Desktop
- R environment available
"""

import asyncio
import json
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

# Mark entire module as local-only for CI skipping
pytestmark = pytest.mark.skipif(
    bool(os.getenv("CI")) or bool(os.getenv("GITHUB_ACTIONS")),
    reason="Claude Desktop integration tests require local environment",
)


class TestClaudeDesktopRealIntegration:
    """Test real Claude Desktop application integration."""

    def get_claude_config_path(self):
        """Get Claude Desktop config file path for current platform."""
        system = platform.system()
        if system == "Darwin":  # macOS
            return (
                Path.home()
                / "Library/Application Support/Claude/claude_desktop_config.json"
            )
        elif system == "Windows":
            return Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json"
        else:  # Linux
            return Path.home() / ".config/claude/claude_desktop_config.json"

    def test_claude_desktop_installed(self):
        """Test that Claude Desktop is installed and accessible."""
        config_path = self.get_claude_config_path()

        if not config_path.exists():
            pytest.skip(f"Claude Desktop not found. Config path: {config_path}")

        print(f"✅ Claude Desktop config found at: {config_path}")

    def test_rmcp_configured_in_claude(self):
        """Test that RMCP is properly configured in Claude Desktop."""
        config_path = self.get_claude_config_path()

        if not config_path.exists():
            pytest.skip("Claude Desktop config not found")

        with open(config_path) as f:
            config = json.load(f)

        assert "mcpServers" in config, "No mcpServers section in Claude config"

        mcp_servers = config["mcpServers"]
        rmcp_config = None

        # Look for RMCP configuration
        for server_name, server_config in mcp_servers.items():
            if "rmcp" in server_name.lower():
                rmcp_config = server_config
                break

        assert rmcp_config is not None, "RMCP not configured in Claude Desktop"
        assert "command" in rmcp_config, "RMCP config missing command"
        assert "args" in rmcp_config, "RMCP config missing args"

        print(f"✅ RMCP configured: {rmcp_config}")

    def test_rmcp_command_accessibility(self):
        """Test that the RMCP command configured in Claude Desktop works."""
        config_path = self.get_claude_config_path()

        if not config_path.exists():
            pytest.skip("Claude Desktop config not found")

        with open(config_path) as f:
            config = json.load(f)

        rmcp_config = None
        for server_name, server_config in config["mcpServers"].items():
            if "rmcp" in server_name.lower():
                rmcp_config = server_config
                break

        if not rmcp_config:
            pytest.skip("RMCP not configured in Claude Desktop")

        # Test the exact command Claude Desktop would use
        command = rmcp_config["command"]
        rmcp_config["args"]
        env = rmcp_config.get("env", {})

        # Set up environment as Claude Desktop would
        test_env = os.environ.copy()
        test_env.update(env)

        # Test command accessibility
        try:
            result = subprocess.run(
                [command] + ["--version"],
                env=test_env,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                print(f"✅ RMCP command accessible: {result.stdout.strip()}")
            else:
                pytest.fail(f"RMCP command failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            pytest.fail("RMCP command timeout")
        except FileNotFoundError:
            pytest.fail(f"RMCP command not found: {command}")

    def test_real_mcp_communication(self):
        """Test real MCP communication as Claude Desktop would perform it."""
        config_path = self.get_claude_config_path()

        if not config_path.exists():
            pytest.skip("Claude Desktop config not found")

        with open(config_path) as f:
            config = json.load(f)

        rmcp_config = None
        for server_name, server_config in config["mcpServers"].items():
            if "rmcp" in server_name.lower():
                rmcp_config = server_config
                break

        if not rmcp_config:
            pytest.skip("RMCP not configured")

        command = rmcp_config["command"]
        args = rmcp_config["args"]
        env = rmcp_config.get("env", {})

        test_env = os.environ.copy()
        test_env.update(env)

        # Test exact MCP communication flow
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "Claude Desktop", "version": "1.0.0"},
            },
        }

        process = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=test_env,
        )

        try:
            stdout, stderr = process.communicate(
                input=json.dumps(init_request) + "\n", timeout=15
            )

            # Validate MCP response
            response_found = False
            for line in stdout.strip().split("\n"):
                if line.startswith('{"jsonrpc"') and '"result"' in line:
                    response = json.loads(line)
                    if (
                        response.get("jsonrpc") == "2.0"
                        and "result" in response
                        and response.get("id") == 1
                    ):
                        server_info = response.get("result", {}).get("serverInfo", {})
                        print("✅ Real MCP communication successful")
                        print(f"   Server: {server_info.get('name', 'Unknown')}")
                        print(f"   Version: {server_info.get('version', 'Unknown')}")
                        response_found = True
                        break

            assert response_found, (
                f"No valid MCP response. stdout: {stdout[:300]}, stderr: {stderr[:300]}"
            )

        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("Real MCP communication timeout")
        finally:
            if process.poll() is None:
                process.terminate()

    def test_claude_desktop_tools_availability(self):
        """Test that all expected tools are available to Claude Desktop."""
        config_path = self.get_claude_config_path()

        if not config_path.exists():
            pytest.skip("Claude Desktop config not found")

        with open(config_path) as f:
            config = json.load(f)

        rmcp_config = None
        for server_name, server_config in config["mcpServers"].items():
            if "rmcp" in server_name.lower():
                rmcp_config = server_config
                break

        if not rmcp_config:
            pytest.skip("RMCP not configured")

        command = rmcp_config["command"]
        args = rmcp_config["args"]
        env = rmcp_config.get("env", {})

        test_env = os.environ.copy()
        test_env.update(env)

        # Drive the server with the official MCP client (handles the full
        # handshake and waits for responses instead of racing stdin EOF).
        from tests.utils import run_mcp_stdio_workflow

        try:
            _, tool_names, _ = run_mcp_stdio_workflow(
                command=command, args=args, env=test_env, timeout=30.0
            )
        except Exception as exc:
            pytest.fail(f"Tools list request failed: {exc}")

        print(f"✅ Tools available to Claude Desktop: {len(tool_names)}")
        expected_tools = ["linear_model", "summary_stats", "read_csv", "scatter_plot"]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, (
                f"Expected tool {expected_tool} not found"
            )
        print(f"   Key tools verified: {expected_tools}")


class TestClaudeDesktopWorkflows:
    """Test realistic Claude Desktop user workflows."""

    def get_rmcp_config(self):
        """Get RMCP config from Claude Desktop."""
        config_path = self.get_claude_config_path()

        if not config_path.exists():
            pytest.skip("Claude Desktop config not found")

        with open(config_path) as f:
            config = json.load(f)

        for server_name, server_config in config["mcpServers"].items():
            if "rmcp" in server_name.lower():
                return server_config

        pytest.skip("RMCP not configured")

    def get_claude_config_path(self):
        """Get Claude Desktop config path."""
        system = platform.system()
        if system == "Darwin":
            return (
                Path.home()
                / "Library/Application Support/Claude/claude_desktop_config.json"
            )
        elif system == "Windows":
            return Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json"
        else:
            return Path.home() / ".config/claude/claude_desktop_config.json"

    def get_rmcp_launch(self):
        """Return (command, args, env) for launching RMCP as Claude Desktop would."""
        rmcp_config = self.get_rmcp_config()
        command = rmcp_config["command"]
        args = rmcp_config["args"]
        env = rmcp_config.get("env", {})
        test_env = os.environ.copy()
        test_env.update(env)
        return command, args, test_env

    def test_data_analysis_workflow(self):
        """Test complete data analysis workflow as Claude Desktop user would do."""
        from tests.utils import run_mcp_stdio_workflow

        command, args, test_env = self.get_rmcp_launch()

        tool_calls = [
            (
                "load_example",
                {"dataset_name": "survey", "size": "small"},
            ),
            (
                "summary_stats",
                {
                    "data": {"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]},
                    "variables": ["x", "y"],
                },
            ),
        ]

        try:
            _, _, results = run_mcp_stdio_workflow(
                command=command,
                args=args,
                env=test_env,
                tool_calls=tool_calls,
                timeout=30.0,
            )
        except Exception as exc:
            pytest.fail(f"Data analysis workflow failed: {exc}")

        assert len(results) == 2, f"Expected 2 responses, got {len(results)}"
        summary_result = results[1]
        assert not summary_result.get("isError"), (
            f"Data analysis workflow failed: {summary_result}"
        )
        print("✅ Data analysis workflow completed successfully")

    def test_file_workflow_with_temp_data(self):
        """Test file-based workflow with temporary data file."""
        from tests.utils import run_mcp_stdio_workflow

        command, args, test_env = self.get_rmcp_launch()

        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("x,y,category\n")
            f.write("1,2,A\n")
            f.write("2,4,B\n")
            f.write("3,6,A\n")
            f.write("4,8,B\n")
            f.write("5,10,A\n")
            temp_file = f.name

        try:
            tool_calls = [
                ("read_csv", {"file_path": temp_file}),
                (
                    "correlation_analysis",
                    {
                        "data": {"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]},
                        "variables": ["x", "y"],
                        "method": "pearson",
                    },
                ),
            ]

            try:
                _, _, results = run_mcp_stdio_workflow(
                    command=command,
                    args=args,
                    env=test_env,
                    tool_calls=tool_calls,
                    timeout=30.0,
                )
            except Exception as exc:
                pytest.fail(f"File workflow failed: {exc}")

            file_result, correlation_result = results
            assert not file_result.get("isError"), (
                f"File read operation failed: {file_result}"
            )
            assert not correlation_result.get("isError"), (
                f"Correlation analysis failed: {correlation_result}"
            )
            print("✅ File-based workflow completed successfully")
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass


class TestClaudeDesktopPerformance:
    """Test Claude Desktop integration performance and reliability."""

    def test_startup_performance(self):
        """Test RMCP startup time for Claude Desktop."""
        config_path = (
            Path.home()
            / "Library/Application Support/Claude/claude_desktop_config.json"
        )

        if not config_path.exists():
            pytest.skip("Claude Desktop config not found")

        with open(config_path) as f:
            config = json.load(f)

        rmcp_config = None
        for server_name, server_config in config["mcpServers"].items():
            if "rmcp" in server_name.lower():
                rmcp_config = server_config
                break

        if not rmcp_config:
            pytest.skip("RMCP not configured")

        command = rmcp_config["command"]
        args = rmcp_config["args"]
        env = rmcp_config.get("env", {})

        test_env = os.environ.copy()
        test_env.update(env)

        # Measure startup time
        start_time = time.time()

        process = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=test_env,
        )

        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "Performance Test", "version": "1.0.0"},
            },
        }

        try:
            stdout, stderr = process.communicate(
                input=json.dumps(init_request) + "\n", timeout=20
            )

            end_time = time.time()
            startup_time = end_time - start_time

            # Validate response received
            response_received = False
            for line in stdout.strip().split("\n"):
                if line.startswith('{"jsonrpc"') and '"result"' in line:
                    response_received = True
                    break

            assert response_received, "No initialize response received"
            assert startup_time < 10.0, f"Startup took too long: {startup_time:.2f}s"

            print(f"✅ Startup performance: {startup_time:.2f}s")

        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("Startup performance test timeout")
        finally:
            if process.poll() is None:
                process.terminate()

    def test_concurrent_requests(self):
        """Test handling multiple concurrent requests like Claude Desktop might send."""
        print("🤖 Testing concurrent request handling...")

        from rmcp.cli import _register_builtin_tools
        from rmcp.core.server import create_server
        from rmcp.transport.sdk import create_streamable_http_app

        from tests.utils import (
            initialize_streamable_session,
            parse_streamable_response,
            streamable_http_client,
        )

        async def run_concurrent_test():
            server = create_server()
            _register_builtin_tools(server)
            app = create_streamable_http_app(server, manage_server_lifecycle=False)

            async with streamable_http_client(app) as client:
                _, headers = await initialize_streamable_session(client)

                async def run_tool_call(tool_name, arguments, request_id):
                    start_time = time.time()
                    try:
                        response = await client.post(
                            "/mcp",
                            json={
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "method": "tools/call",
                                "params": {"name": tool_name, "arguments": arguments},
                            },
                            headers=headers,
                            timeout=60.0,
                        )
                        message = parse_streamable_response(response)
                        succeeded = (
                            response.status_code == 200
                            and message is not None
                            and "result" in message
                            and not message["result"].get("isError")
                        )
                        return {
                            "id": request_id,
                            "tool": tool_name,
                            "success": succeeded,
                            "duration": time.time() - start_time,
                        }
                    except Exception as e:
                        return {
                            "id": request_id,
                            "tool": tool_name,
                            "success": False,
                            "duration": time.time() - start_time,
                            "error": str(e),
                        }

                # Test 1: Rapid burst of identical requests
                print("   📡 Test 1: Rapid sequential requests...")
                sequential_results = await asyncio.gather(
                    *[
                        run_tool_call(
                            "load_example", {"dataset_name": "sales"}, 100 + i
                        )
                        for i in range(5)
                    ]
                )
                successful_sequential = sum(
                    1 for r in sequential_results if r["success"]
                )
                avg_sequential_time = sum(
                    r["duration"] for r in sequential_results
                ) / len(sequential_results)
                print(
                    f"   ✅ Sequential: {successful_sequential}/{len(sequential_results)} successful"
                )

                # Test 2: Concurrent different tools
                print("   📡 Test 2: Concurrent different tools...")
                concurrent_start = time.time()
                concurrent_results = await asyncio.gather(
                    run_tool_call("load_example", {"dataset_name": "sales"}, 200),
                    run_tool_call("load_example", {"dataset_name": "timeseries"}, 201),
                    run_tool_call("validate_data", {"data": {"x": [1, 2, 3]}}, 202),
                    return_exceptions=True,
                )
                valid_concurrent = [
                    r for r in concurrent_results if isinstance(r, dict)
                ]
                successful_concurrent = sum(
                    1 for r in valid_concurrent if r.get("success", False)
                )
                total_concurrent_time = time.time() - concurrent_start
                print(f"   ✅ Concurrent: {successful_concurrent}/3 successful")

                # Test 3: Stress test with many rapid requests
                print("   📡 Test 3: Stress test (10 rapid requests)...")
                stress_results = await asyncio.gather(
                    *[
                        run_tool_call(
                            "load_example", {"dataset_name": "sales"}, 300 + i
                        )
                        for i in range(10)
                    ],
                    return_exceptions=True,
                )
                valid_stress = [r for r in stress_results if isinstance(r, dict)]
                successful_stress = sum(
                    1 for r in valid_stress if r.get("success", False)
                )
                print(f"   ✅ Stress test: {successful_stress}/10 successful")

                assert successful_sequential >= 4, (
                    f"Sequential requests: {successful_sequential}/5 successful (expected ≥4)"
                )
                assert successful_concurrent >= 2, (
                    f"Concurrent requests: {successful_concurrent}/3 successful (expected ≥2)"
                )
                assert successful_stress >= 7, (
                    f"Stress test: {successful_stress}/10 successful (expected ≥7)"
                )
                assert avg_sequential_time < 5.0, (
                    f"Sequential avg time {avg_sequential_time:.2f}s too slow (expected <5s)"
                )
                assert total_concurrent_time < 10.0, (
                    f"Concurrent time {total_concurrent_time:.2f}s too slow (expected <10s)"
                )

                print("🎉 All concurrent request tests passed!")

        asyncio.run(run_concurrent_test())


if __name__ == "__main__":
    print("🤖 Real Claude Desktop E2E Integration Tests")
    print("=" * 60)
    print("These tests validate actual Claude Desktop integration")
    print("Make sure Claude Desktop is installed and RMCP is configured")
    print()

    # Run with pytest
    pytest.main([__file__, "-v"])
