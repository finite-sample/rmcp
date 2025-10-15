#!/usr/bin/env python3
"""
IDE Configuration Validator

This script validates IDE configurations for RMCP integration and provides
setup guidance for Claude Desktop, VS Code, and Cursor.

Usage:
    python tests/local/validate_ide_configs.py
    python tests/local/validate_ide_configs.py --create-samples
    python tests/local/validate_ide_configs.py --ide claude
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class IDEConfigValidator:
    """Validates and helps setup IDE configurations for RMCP."""

    def __init__(self):
        self.system = platform.system()
        self.rmcp_available = shutil.which("rmcp") is not None
        self.r_available = shutil.which("R") is not None

    def get_config_paths(self) -> Dict[str, List[Path]]:
        """Get potential config file paths for each IDE."""
        home = Path.home()

        if self.system == "Darwin":  # macOS
            paths = {
                "claude": [
                    home
                    / "Library/Application Support/Claude/claude_desktop_config.json"
                ],
                "vscode": [
                    home / "Library/Application Support/Code/User/settings.json",
                    home / ".vscode/settings.json",
                ],
                "cursor": [
                    home / "Library/Application Support/Cursor/User/settings.json",
                    home / ".cursor/settings.json",
                ],
            }
        elif self.system == "Windows":
            paths = {
                "claude": [home / "AppData/Roaming/Claude/claude_desktop_config.json"],
                "vscode": [
                    home / "AppData/Roaming/Code/User/settings.json",
                    home / ".vscode/settings.json",
                ],
                "cursor": [
                    home / "AppData/Roaming/Cursor/User/settings.json",
                    home / ".cursor/settings.json",
                ],
            }
        else:  # Linux
            paths = {
                "claude": [home / ".config/claude/claude_desktop_config.json"],
                "vscode": [
                    home / ".config/Code/User/settings.json",
                    home / ".vscode/settings.json",
                ],
                "cursor": [
                    home / ".config/Cursor/User/settings.json",
                    home / ".cursor/settings.json",
                ],
            }

        return paths

    def validate_claude_desktop(self) -> Tuple[bool, str, Dict]:
        """Validate Claude Desktop configuration."""
        config_paths = self.get_config_paths()["claude"]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = json.load(f)

                    if "mcpServers" not in config:
                        return False, f"No mcpServers section in {config_path}", {}

                    # Look for RMCP configuration
                    mcp_servers = config["mcpServers"]
                    rmcp_config = None
                    rmcp_name = None

                    for server_name, server_config in mcp_servers.items():
                        if (
                            "rmcp" in server_name.lower()
                            or server_config.get("command") == "rmcp"
                        ):
                            rmcp_config = server_config
                            rmcp_name = server_name
                            break

                    if not rmcp_config:
                        return False, f"RMCP not configured in {config_path}", config

                    # Validate RMCP configuration
                    if rmcp_config.get("command") != "rmcp":
                        return (
                            False,
                            f"Invalid command in RMCP config: {rmcp_config.get('command')}",
                            config,
                        )

                    if "start" not in rmcp_config.get("args", []):
                        return False, "RMCP config missing 'start' argument", config

                    return (
                        True,
                        f"RMCP properly configured as '{rmcp_name}' in {config_path}",
                        config,
                    )

                except json.JSONDecodeError as e:
                    return False, f"Invalid JSON in {config_path}: {e}", {}
                except Exception as e:
                    return False, f"Error reading {config_path}: {e}", {}

        return False, "Claude Desktop config file not found", {}

    def validate_vscode(self) -> Tuple[bool, str, Dict]:
        """Validate VS Code configuration."""
        config_paths = self.get_config_paths()["vscode"]

        # Check if VS Code is installed
        if not shutil.which("code"):
            return False, "VS Code CLI not found in PATH", {}

        # Check for Continue extension
        try:
            result = subprocess.run(
                ["code", "--list-extensions"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            extensions = result.stdout.lower()
            if "continue.continue" not in extensions:
                return (
                    False,
                    "Continue extension not installed. Run: code --install-extension Continue.continue",
                    {},
                )
        except Exception as e:
            return False, f"Could not check VS Code extensions: {e}", {}

        # Check configuration files
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = json.load(f)

                    # Look for Continue or MCP configuration
                    mcp_config = {}
                    for key, value in config.items():
                        if "continue" in key.lower() and "mcp" in key.lower():
                            mcp_config[key] = value

                    if mcp_config:
                        return True, f"MCP configuration found in {config_path}", config

                except json.JSONDecodeError as e:
                    return False, f"Invalid JSON in {config_path}: {e}", {}
                except Exception as e:
                    return False, f"Error reading {config_path}: {e}", {}

        return False, "No MCP configuration found in VS Code settings", {}

    def validate_cursor(self) -> Tuple[bool, str, Dict]:
        """Validate Cursor configuration."""
        config_paths = self.get_config_paths()["cursor"]

        # Check if Cursor is installed
        if not shutil.which("cursor"):
            return False, "Cursor CLI not found in PATH", {}

        # Check configuration files
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = json.load(f)

                    # Look for MCP configuration
                    mcp_config = {}
                    for key, value in config.items():
                        if "mcp" in key.lower():
                            mcp_config[key] = value

                    if mcp_config:
                        return True, f"MCP configuration found in {config_path}", config

                except json.JSONDecodeError as e:
                    return False, f"Invalid JSON in {config_path}: {e}", {}
                except Exception as e:
                    return False, f"Error reading {config_path}: {e}", {}

        return False, "No MCP configuration found in Cursor settings", {}

    def test_rmcp_server(self) -> Tuple[bool, str]:
        """Test that RMCP server can start and respond."""
        if not self.rmcp_available:
            return False, "rmcp command not found in PATH"

        try:
            # Test version
            result = subprocess.run(
                ["rmcp", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return False, f"rmcp --version failed: {result.stderr}"

            version = result.stdout.strip()

            # Test basic server communication
            test_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "Config Validator", "version": "1.0.0"},
                },
            }

            process = subprocess.Popen(
                ["rmcp", "start"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = process.communicate(
                input=json.dumps(test_request) + "\n", timeout=10
            )

            # Look for JSON response
            for line in stdout.strip().split("\n"):
                if line.startswith('{"jsonrpc"'):
                    response = json.loads(line)
                    if response.get("jsonrpc") == "2.0" and "result" in response:
                        return True, f"RMCP server working (version: {version})"

            return (
                False,
                f"No valid JSON response from RMCP server. stdout: {stdout}, stderr: {stderr}",
            )

        except subprocess.TimeoutExpired:
            return False, "RMCP server timeout"
        except Exception as e:
            return False, f"RMCP server test failed: {e}"

    def create_sample_configs(self) -> Dict[str, str]:
        """Create sample configuration files."""
        configs = {
            "claude_desktop_config.json": {
                "mcpServers": {
                    "rmcp": {"command": "rmcp", "args": ["start"], "env": {}}
                }
            },
            "vscode_continue_settings.json": {
                "continue.mcpServers": {"rmcp": {"command": "rmcp", "args": ["start"]}}
            },
            "cursor_mcp_settings.json": {
                "mcp.servers": {"rmcp": {"command": "rmcp", "args": ["start"]}}
            },
        }

        samples_dir = Path("ide_config_samples")
        samples_dir.mkdir(exist_ok=True)

        created_files = {}
        for filename, config in configs.items():
            file_path = samples_dir / filename
            with open(file_path, "w") as f:
                json.dump(config, f, indent=2)
            created_files[filename] = str(file_path)

        return created_files

    def get_setup_instructions(self, ide: str) -> str:
        """Get setup instructions for a specific IDE."""
        if ide == "claude":
            config_path = self.get_config_paths()["claude"][0]
            return f"""
Claude Desktop Setup Instructions:
==================================

1. Install Claude Desktop from: https://claude.ai/download

2. Create or edit config file: {config_path}

3. Add this configuration:
{{
  "mcpServers": {{
    "rmcp": {{
      "command": "rmcp",
      "args": ["start"],
      "env": {{}}
    }}
  }}
}}

4. Restart Claude Desktop

5. Test by asking Claude: "What statistical tools do you have available?"
"""

        elif ide == "vscode":
            return """
VS Code Setup Instructions:
===========================

1. Install VS Code from: https://code.visualstudio.com/

2. Install Continue extension:
   code --install-extension Continue.continue

3. Add to VS Code settings.json:
{
  "continue.mcpServers": {
    "rmcp": {
      "command": "rmcp",
      "args": ["start"]
    }
  }
}

4. Restart VS Code

5. Use Continue extension to interact with RMCP statistical tools
"""

        elif ide == "cursor":
            return """
Cursor Setup Instructions:
==========================

1. Install Cursor from: https://cursor.sh/

2. Add to Cursor settings.json:
{
  "mcp.servers": {
    "rmcp": {
      "command": "rmcp",
      "args": ["start"]
    }
  }
}

3. Restart Cursor

4. Use Cursor's AI features to interact with RMCP statistical tools
"""

        else:
            return "Unknown IDE. Supported IDEs: claude, vscode, cursor"

    def run_full_validation(self) -> Dict[str, any]:
        """Run validation for all IDEs and components."""
        results = {
            "system_info": {
                "platform": f"{self.system} {platform.release()}",
                "python": sys.version.split()[0],
                "rmcp_available": self.rmcp_available,
                "r_available": self.r_available,
            },
            "rmcp_server": {},
            "ides": {},
        }

        # Test RMCP server
        server_valid, server_msg = self.test_rmcp_server()
        results["rmcp_server"] = {"valid": server_valid, "message": server_msg}

        # Test each IDE
        for ide_name, validator_func in [
            ("claude", self.validate_claude_desktop),
            ("vscode", self.validate_vscode),
            ("cursor", self.validate_cursor),
        ]:
            try:
                valid, message, config = validator_func()
                results["ides"][ide_name] = {
                    "valid": valid,
                    "message": message,
                    "config_found": bool(config),
                }
            except Exception as e:
                results["ides"][ide_name] = {
                    "valid": False,
                    "message": f"Validation error: {e}",
                    "config_found": False,
                }

        return results


def main():
    parser = argparse.ArgumentParser(description="Validate IDE configurations for RMCP")
    parser.add_argument(
        "--ide",
        choices=["claude", "vscode", "cursor"],
        help="Validate specific IDE only",
    )
    parser.add_argument(
        "--create-samples",
        action="store_true",
        help="Create sample configuration files",
    )
    parser.add_argument(
        "--setup-instructions", metavar="IDE", help="Show setup instructions for IDE"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    validator = IDEConfigValidator()

    if args.create_samples:
        print("Creating sample configuration files...")
        created = validator.create_sample_configs()
        for filename, path in created.items():
            print(f"Created: {path}")
        return

    if args.setup_instructions:
        print(validator.get_setup_instructions(args.setup_instructions))
        return

    if args.ide:
        # Validate specific IDE
        if args.ide == "claude":
            valid, message, config = validator.validate_claude_desktop()
        elif args.ide == "vscode":
            valid, message, config = validator.validate_vscode()
        elif args.ide == "cursor":
            valid, message, config = validator.validate_cursor()

        if args.json:
            print(
                json.dumps(
                    {
                        "ide": args.ide,
                        "valid": valid,
                        "message": message,
                        "config_found": bool(config),
                    },
                    indent=2,
                )
            )
        else:
            status = "✅ VALID" if valid else "❌ INVALID"
            print(f"{args.ide.title()}: {status}")
            print(f"Message: {message}")
    else:
        # Run full validation
        results = validator.run_full_validation()

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("RMCP IDE Configuration Validation")
            print("=" * 40)

            # System info
            info = results["system_info"]
            print(f"Platform: {info['platform']}")
            print(f"Python: {info['python']}")
            print(f"RMCP Available: {'✅' if info['rmcp_available'] else '❌'}")
            print(f"R Available: {'✅' if info['r_available'] else '❌'}")
            print()

            # RMCP server
            server = results["rmcp_server"]
            status = "✅ WORKING" if server["valid"] else "❌ FAILED"
            print(f"RMCP Server: {status}")
            print(f"  {server['message']}")
            print()

            # IDEs
            print("IDE Configurations:")
            for ide_name, ide_result in results["ides"].items():
                status = "✅ VALID" if ide_result["valid"] else "❌ INVALID"
                print(f"  {ide_name.title()}: {status}")
                print(f"    {ide_result['message']}")

            print("\nFor setup instructions, run:")
            print("  python validate_ide_configs.py --setup-instructions <ide>")


if __name__ == "__main__":
    main()
