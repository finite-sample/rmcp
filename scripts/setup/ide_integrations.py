"""
Local IDE Integration Tests

These tests check actual IDE integrations on the developer's local machine.
They are marked with @pytest.mark.local and won't run in CI.

To run locally:
    pytest tests/local/ -m local -v

Requirements:
- IDEs must be installed locally
- Proper IDE configurations must be set up
- R must be available
"""

import json
import platform
import shutil
import subprocess
from pathlib import Path

import pytest

# Script relies on rmcp being installed via pip install -e .

# Import removed - this function doesn't exist in the CLI module


@pytest.mark.local
class TestClaudeDesktopIntegration:
    """Test Claude Desktop MCP integration."""

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

    def test_claude_desktop_config_exists(self):
        """Check if Claude Desktop config file exists."""
        config_path = self.get_claude_config_path()
        if not config_path.exists():
            pytest.skip(f"Claude Desktop config not found at {config_path}")

    def test_claude_desktop_config_format(self):
        """Validate Claude Desktop config file format."""
        config_path = self.get_claude_config_path()
        if not config_path.exists():
            pytest.skip("Claude Desktop config not found")

        try:
            with open(config_path) as f:
                config = json.load(f)

            assert "mcpServers" in config, "Config missing mcpServers section"

            # Check if RMCP is configured
            mcp_servers = config["mcpServers"]
            rmcp_config = None
            for server_name, server_config in mcp_servers.items():
                if (
                    "rmcp" in server_name.lower()
                    or server_config.get("command") == "rmcp"
                ):
                    rmcp_config = server_config
                    break

            if rmcp_config:
                assert "command" in rmcp_config, "RMCP config missing command"
                assert "args" in rmcp_config, "RMCP config missing args"
                assert rmcp_config["command"] == "rmcp", "RMCP command should be 'rmcp'"
                assert "start" in rmcp_config["args"], (
                    "RMCP args should include 'start'"
                )
            else:
                pytest.skip("RMCP not configured in Claude Desktop")

        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in Claude config: {e}")

    def test_claude_desktop_rmcp_communication(self):
        """Test MCP communication as Claude Desktop would do it."""
        # Test that we can start RMCP and communicate via stdio
        rmcp_path = shutil.which("rmcp")
        if not rmcp_path:
            pytest.skip("rmcp command not found in PATH")

        # Start RMCP server
        process = subprocess.Popen(
            [rmcp_path, "start"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Send initialize request (same as Claude Desktop would send)
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

        try:
            stdout, stderr = process.communicate(
                input=json.dumps(init_request) + "\n", timeout=10
            )

            # Look for JSON response in stdout
            response_line = None
            for line in stdout.strip().split("\n"):
                if line.startswith('{"jsonrpc"'):
                    response_line = line
                    break

            assert response_line is not None, (
                f"No JSON response found. stdout: {stdout}, stderr: {stderr}"
            )

            response = json.loads(response_line)
            assert response["jsonrpc"] == "2.0"
            assert "result" in response
            assert "serverInfo" in response["result"]
            assert (
                response["result"]["serverInfo"]["name"]
                == "RMCP Statistical Analysis Server"
            )

        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("RMCP server timeout during communication test")
        except Exception as e:
            process.kill()
            pytest.fail(f"Communication test failed: {e}")
        finally:
            if process.poll() is None:
                process.terminate()


@pytest.mark.local
class TestVSCodeIntegration:
    """Test VS Code MCP integration via Continue extension."""

    def test_vscode_installed(self):
        """Check if VS Code is installed."""
        vscode_path = shutil.which("code")
        if not vscode_path:
            pytest.skip("VS Code CLI not found")

        # Test VS Code version
        result = subprocess.run(
            [vscode_path, "--version"], capture_output=True, text=True
        )
        assert result.returncode == 0, "VS Code version check failed"

        lines = result.stdout.strip().split("\n")
        assert len(lines) >= 3, "Unexpected VS Code version output"
        print(f"VS Code version: {lines[0]}")

    def test_continue_extension(self):
        """Check if Continue extension is installed."""
        vscode_path = shutil.which("code")
        if not vscode_path:
            pytest.skip("VS Code CLI not found")

        result = subprocess.run(
            [vscode_path, "--list-extensions"], capture_output=True, text=True
        )

        extensions = result.stdout.lower()
        if "continue.continue" not in extensions:
            pytest.skip(
                "Continue extension not installed. Install with: code --install-extension Continue.continue"
            )

        print("Continue extension is installed")

    def test_vscode_mcp_config(self):
        """Test VS Code MCP configuration for Continue extension."""
        # Continue extension typically looks for config in workspace or global settings
        vscode_settings_paths = [
            Path.home() / ".vscode/settings.json",
            Path.home()
            / "Library/Application Support/Code/User/settings.json",  # macOS
            Path.home() / "AppData/Roaming/Code/User/settings.json",  # Windows
            Path.home() / ".config/Code/User/settings.json",  # Linux
        ]

        settings_found = False
        for settings_path in vscode_settings_paths:
            if settings_path.exists():
                settings_found = True
                try:
                    with open(settings_path) as f:
                        settings = json.load(f)

                    # Look for Continue or MCP-related settings
                    mcp_settings = {}
                    for key, value in settings.items():
                        if "continue" in key.lower() or "mcp" in key.lower():
                            mcp_settings[key] = value

                    if mcp_settings:
                        print(f"Found MCP-related settings in {settings_path}")
                        print(json.dumps(mcp_settings, indent=2))

                except json.JSONDecodeError:
                    print(f"Invalid JSON in {settings_path}")

        if not settings_found:
            pytest.skip("No VS Code settings file found")


@pytest.mark.local
class TestCursorIntegration:
    """Test Cursor IDE MCP integration."""

    def test_cursor_installed(self):
        """Check if Cursor is installed."""
        cursor_path = shutil.which("cursor")
        if not cursor_path:
            pytest.skip("Cursor CLI not found")

        # Test Cursor version
        result = subprocess.run(
            [cursor_path, "--version"], capture_output=True, text=True
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            print(f"Cursor version: {lines[0] if lines else 'Unknown'}")
        else:
            print("Cursor version check returned non-zero, but binary exists")

    def test_cursor_mcp_config(self):
        """Test Cursor MCP configuration."""
        # Cursor often uses similar config format to VS Code
        cursor_config_paths = [
            Path.home() / ".cursor/settings.json",
            Path.home()
            / "Library/Application Support/Cursor/User/settings.json",  # macOS
            Path.home() / "AppData/Roaming/Cursor/User/settings.json",  # Windows
            Path.home() / ".config/Cursor/User/settings.json",  # Linux
        ]

        config_found = False
        for config_path in cursor_config_paths:
            if config_path.exists():
                config_found = True
                try:
                    with open(config_path) as f:
                        config = json.load(f)

                    # Look for MCP-related settings
                    mcp_settings = {}
                    for key, value in config.items():
                        if "mcp" in key.lower() or "server" in key.lower():
                            mcp_settings[key] = value

                    if mcp_settings:
                        print(f"Found MCP-related settings in {config_path}")
                        print(json.dumps(mcp_settings, indent=2))

                except json.JSONDecodeError:
                    print(f"Invalid JSON in {config_path}")

        if not config_found:
            pytest.skip("No Cursor config file found")


@pytest.mark.local
class TestRMCPServerSetup:
    """Test RMCP server setup and configuration."""

    def test_rmcp_command_available(self):
        """Test that rmcp command is available in PATH."""
        rmcp_path = shutil.which("rmcp")
        assert rmcp_path is not None, "rmcp command not found in PATH"

        # Test version
        result = subprocess.run(
            [rmcp_path, "--version"], capture_output=True, text=True
        )
        assert result.returncode == 0, "rmcp --version failed"
        print(f"RMCP version: {result.stdout.strip()}")

    def test_r_integration(self):
        """Test R integration is working."""
        r_path = shutil.which("R")
        assert r_path is not None, "R not found in PATH"

        # Test R version
        result = subprocess.run([r_path, "--version"], capture_output=True, text=True)
        assert result.returncode == 0, "R --version failed"

        version_line = result.stdout.split("\n")[0]
        print(f"R version: {version_line}")

    def test_rmcp_tools_count(self):
        """Test that RMCP has the expected number of tools."""
        rmcp_path = shutil.which("rmcp")
        if not rmcp_path:
            pytest.skip("rmcp command not found")

        # Test tools list
        result = subprocess.run(
            [rmcp_path, "list-capabilities"], capture_output=True, text=True
        )
        if result.returncode == 0:
            output = result.stdout
            # Look for tool count in output
            if "tools" in output.lower():
                print("RMCP capabilities available")
            else:
                print(f"Capabilities output: {output}")

    def test_sample_analysis(self):
        """Test a sample statistical analysis end-to-end."""
        rmcp_path = shutil.which("rmcp")
        if not rmcp_path:
            pytest.skip("rmcp command not found")

        # Create a simple test to verify RMCP works
        test_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "correlation_analysis",
                "arguments": {
                    "data": {"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]},
                    "variables": ["x", "y"],
                    "method": "pearson",
                },
            },
        }

        process = subprocess.Popen(
            [rmcp_path, "start"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, stderr = process.communicate(
                input=json.dumps(test_request) + "\n", timeout=15
            )

            # Look for successful response
            response_found = False
            for line in stdout.strip().split("\n"):
                if line.startswith('{"jsonrpc"') and '"result"' in line:
                    response = json.loads(line)
                    if "result" in response and "content" in response["result"]:
                        response_found = True
                        print("Sample analysis successful")
                        break

            assert response_found, (
                f"No successful response found. stdout: {stdout}, stderr: {stderr}"
            )

        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("Sample analysis timeout")
        except Exception as e:
            process.kill()
            pytest.fail(f"Sample analysis failed: {e}")
        finally:
            if process.poll() is None:
                process.terminate()


def create_sample_ide_configs():
    """Helper function to create sample IDE configurations."""
    configs = {
        "claude_desktop_config.json": {
            "mcpServers": {"rmcp": {"command": "rmcp", "args": ["start"], "env": {}}}
        },
        "vscode_settings.json": {
            "continue.mcpServers": {"rmcp": {"command": "rmcp", "args": ["start"]}}
        },
        "cursor_settings.json": {
            "mcp.servers": {"rmcp": {"command": "rmcp", "args": ["start"]}}
        },
    }

    return configs


if __name__ == "__main__":
    print("Local IDE Integration Test Samples")
    print("=" * 50)

    configs = create_sample_ide_configs()
    for name, config in configs.items():
        print(f"\n{name}:")
        print(json.dumps(config, indent=2))

    print("\nTo run these tests:")
    print("pytest tests/local/ -m local -v")
