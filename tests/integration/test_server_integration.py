#!/usr/bin/env python3
"""
Integration tests for RMCP server functionality that requires R.
Tests R availability, CLI functionality, and full server integration.
"""
import subprocess
import sys
from pathlib import Path
from shutil import which

import pytest

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for server integration tests"
)


def test_r_availability():
    """Test that R is available for statistical computations."""
    print("\n🔍 Testing R Installation")
    print("-" * 40)
    try:
        result = subprocess.run(
            ["R", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            version_line = result.stdout.split("\n")[0]
            print(f"✅ R is available: {version_line}")
        else:
            print("❌ R not working properly")
            assert False, "R not working properly"
    except subprocess.TimeoutExpired:
        print("❌ R command timed out")
        assert False, "R command timed out"
    except FileNotFoundError:
        print("❌ R not found - install R to use RMCP")
        assert False, "R not found"


def test_cli_basic():
    """Test basic CLI functionality with R integration."""
    print("\n🔍 Testing CLI")
    print("-" * 40)

    # Try direct command first (works in Docker/CI), then fallback to poetry (local dev)
    commands_to_try = [
        (["rmcp", "--version"], "direct command"),
        (["poetry", "run", "rmcp", "--version"], "poetry run command"),
    ]

    for command, description in commands_to_try:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=Path(__file__).parent.parent.parent,
            )
            if result.returncode == 0:
                print(f"✅ CLI version ({description}): {result.stdout.strip()}")
                return  # Success, exit the test
            else:
                print(f"⚠️  {description} failed: {result.stderr}")
                continue  # Try next command
        except FileNotFoundError:
            print(f"⚠️  {description} not available (command not found)")
            continue  # Try next command
        except subprocess.TimeoutExpired:
            print(f"❌ {description} timed out")
            assert False, f"{description} timed out"
        except Exception as e:
            print(f"⚠️  {description} failed: {e}")
            continue  # Try next command

    # If we get here, none of the commands worked
    assert (
        False
    ), "All CLI test commands failed - neither 'rmcp --version' nor 'poetry run rmcp --version' worked"


def test_server_with_r_integration():
    """Test server creation with R tools integration."""
    print("\n🔍 Testing Server with R Integration")
    print("-" * 40)

    # Add rmcp to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    try:
        from rmcp.core.server import create_server
        from rmcp.cli import _register_builtin_tools

        # Create server and register R-dependent tools
        server = create_server()
        _register_builtin_tools(server)

        # Check that R-dependent tools are registered
        tool_count = len(server.tools._tools)
        assert tool_count >= 40, f"Expected at least 40 tools, got {tool_count}"

        # Check for key R-dependent tools
        tool_names = set(server.tools._tools.keys())
        required_r_tools = {"linear_model", "summary_stats", "read_csv", "arima_model"}
        missing_tools = required_r_tools - tool_names
        assert not missing_tools, f"Missing R-dependent tools: {missing_tools}"

        print(f"✅ Server created with {tool_count} R-integrated tools")

    except Exception as e:
        print(f"❌ Server R integration failed: {e}")
        assert False, f"Server R integration failed: {e}"


def main():
    """Run all server integration tests."""
    print("🧪 RMCP Server Integration Tests")
    print("=" * 50)
    tests = [
        ("R Installation", test_r_availability),
        ("CLI Basic", test_cli_basic),
        ("Server R Integration", test_server_with_r_integration),
    ]
    passed = 0
    total = len(tests)
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"✅ {name} test passed")
        except Exception as e:
            print(f"❌ {name} test error: {e}")
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    if passed == total:
        print("✅ RMCP server integration is ready!")
        return True
    else:
        print("❌ RMCP server integration has issues")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
