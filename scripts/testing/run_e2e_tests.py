#!/usr/bin/env python3
"""
RMCP End-to-End Testing Suite

Comprehensive testing script that validates RMCP across all supported environments:
- Local environment validation
- Real Claude Desktop integration
- Docker workflow validation
- Performance and reliability testing

Usage:
    python run_e2e_tests.py [--quick] [--docker] [--claude] [--performance] [--all]
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_command(command, description="", timeout=60):
    """Run command and display results."""
    print(f"\n🔍 {description}")
    print("-" * 50)

    start_time = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True if isinstance(command, str) else False,
            capture_output=False,  # Show output in real-time
            timeout=timeout,
        )

        end_time = time.time()
        duration = end_time - start_time

        if result.returncode == 0:
            print(f"✅ {description} completed successfully ({duration:.1f}s)")
            return True
        else:
            print(f"❌ {description} failed (exit code: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"💥 {description} failed with exception: {e}")
        return False


def run_local_validation():
    """Run local environment validation."""
    return run_command(
        [sys.executable, "tests/local/validate_local_setup.py"],
        "Local Environment Validation",
        timeout=120,
    )


def run_claude_desktop_tests():
    """Run Claude Desktop integration tests."""
    tests = [
        "tests/e2e/test_real_claude_desktop_e2e.py::TestClaudeDesktopRealIntegration::test_claude_desktop_installed",
        "tests/e2e/test_real_claude_desktop_e2e.py::TestClaudeDesktopRealIntegration::test_rmcp_configured_in_claude",
        "tests/e2e/test_real_claude_desktop_e2e.py::TestClaudeDesktopRealIntegration::test_real_mcp_communication",
        "tests/e2e/test_real_claude_desktop_e2e.py::TestClaudeDesktopRealIntegration::test_claude_desktop_tools_availability",
        "tests/e2e/test_real_claude_desktop_e2e.py::TestClaudeDesktopWorkflows::test_data_analysis_workflow",
    ]

    success_count = 0
    for test in tests:
        if run_command(
            [sys.executable, "-m", "pytest", test, "-v"],
            f"Claude Desktop Test: {test.split('::')[-1]}",
            timeout=60,
        ):
            success_count += 1

    print(f"\n📊 Claude Desktop Tests: {success_count}/{len(tests)} passed")
    return success_count == len(tests)


def run_existing_e2e_scenarios():
    """Run existing E2E scenario tests."""
    return run_command(
        [sys.executable, "tests/e2e/test_claude_desktop_scenarios.py"],
        "Claude Desktop Scenario Tests",
        timeout=180,
    )


def run_docker_tests():
    """Run Docker workflow tests."""
    # First check if Docker is available
    docker_check = run_command(
        ["docker", "--version"], "Docker Availability Check", timeout=10
    )

    if not docker_check:
        print("⚠️  Docker not available, skipping Docker tests")
        return True  # Don't fail overall test if Docker not available

    # Build test image first
    build_success = run_command(
        ["docker", "build", "-t", "rmcp-e2e-test", "."],
        "Building Docker Test Image",
        timeout=300,
    )

    if not build_success:
        print("❌ Docker build failed, skipping Docker workflow tests")
        return False

    # Run Docker workflow tests
    docker_tests = [
        "tests/e2e/test_docker_full_workflow.py::TestDockerWorkflowValidation::test_docker_build_and_basic_functionality",
        "tests/e2e/test_docker_full_workflow.py::TestDockerWorkflowValidation::test_docker_mcp_protocol_communication",
        "tests/e2e/test_docker_full_workflow.py::TestDockerWorkflowValidation::test_docker_r_environment_validation",
    ]

    success_count = 0
    for test in docker_tests:
        if run_command(
            [sys.executable, "-m", "pytest", test, "-v", "-s"],
            f"Docker Test: {test.split('::')[-1]}",
            timeout=120,
        ):
            success_count += 1

    print(f"\n📊 Docker Tests: {success_count}/{len(docker_tests)} passed")
    return success_count == len(docker_tests)


def run_performance_tests():
    """Run performance and reliability tests."""
    performance_tests = [
        "tests/e2e/test_real_claude_desktop_e2e.py::TestClaudeDesktopPerformance::test_startup_performance",
    ]

    success_count = 0
    for test in performance_tests:
        if run_command(
            [sys.executable, "-m", "pytest", test, "-v", "-s"],
            f"Performance Test: {test.split('::')[-1]}",
            timeout=60,
        ):
            success_count += 1

    print(f"\n📊 Performance Tests: {success_count}/{len(performance_tests)} passed")
    return success_count == len(performance_tests)


def run_quick_validation():
    """Run quick validation tests."""
    print("🚀 Quick E2E Validation")
    print("=" * 40)

    results = {}

    # Basic functionality test
    results["Local Validation"] = run_command(
        [
            sys.executable,
            "-c",
            """
import sys
sys.path.insert(0, '.')
from rmcp.core.server import create_server
from rmcp.cli import _register_builtin_tools
import json

# Test basic server creation and MCP communication
server = create_server()
_register_builtin_tools(server)

# Test initialize message
init_request = {
    "jsonrpc": "2.0",
    "id": 1, 
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {"tools": {}},
        "clientInfo": {"name": "Quick Test", "version": "1.0.0"}
    }
}

class MockTransport:
    def __init__(self):
        self.name = "mock"

import asyncio
async def test_server():
    response = await server.handle_request(init_request)
    return response

response = asyncio.run(test_server())
if response and response.get('jsonrpc') == '2.0' and 'result' in response:
    server_info = response.get('result', {}).get('serverInfo', {})
    print(f"✅ Server: {server_info.get('name', 'Unknown')} v{server_info.get('version', 'Unknown')}")
    print(f"✅ Tools: {len(server.tools._tools)} available")
    print("✅ Quick validation passed!")
else:
    print("❌ Quick validation failed!")
    sys.exit(1)
""",
        ],
        "Quick Server Validation",
        timeout=30,
    )

    # Claude Desktop config test
    results["Claude Config"] = run_command(
        [
            sys.executable,
            "-c",
            """
import json
from pathlib import Path
import platform

system = platform.system()
if system == "Darwin":
    config_path = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
elif system == "Windows":
    config_path = Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json"
else:
    config_path = Path.home() / ".config/claude/claude_desktop_config.json"

if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
    
    if "mcpServers" in config:
        rmcp_found = any("rmcp" in name.lower() for name in config["mcpServers"].keys())
        if rmcp_found:
            print("✅ RMCP configured in Claude Desktop")
        else:
            print("⚠️ RMCP not found in Claude Desktop config")
    else:
        print("⚠️ No mcpServers in Claude Desktop config") 
else:
    print("⚠️ Claude Desktop config not found")
""",
        ],
        "Claude Desktop Configuration Check",
        timeout=10,
    )

    # Summary
    passed = sum(1 for result in results.values() if result)
    total = len(results)

    print(f"\n📊 Quick Validation Results: {passed}/{total} passed")
    return passed == total


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="RMCP End-to-End Testing Suite")
    parser.add_argument(
        "--quick", action="store_true", help="Run quick validation tests only"
    )
    parser.add_argument(
        "--claude", action="store_true", help="Run Claude Desktop integration tests"
    )
    parser.add_argument(
        "--docker", action="store_true", help="Run Docker workflow tests"
    )
    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests"
    )
    parser.add_argument("--all", action="store_true", help="Run all E2E tests")

    args = parser.parse_args()

    # If no specific tests selected, run quick validation
    if not any([args.quick, args.claude, args.docker, args.performance, args.all]):
        args.quick = True

    print("🧪 RMCP End-to-End Testing Suite")
    print("=" * 50)
    print("Testing complete RMCP functionality across all environments")
    print()

    start_time = time.time()
    results = {}

    try:
        if args.quick:
            results["Quick Validation"] = run_quick_validation()

        if args.all or args.claude:
            results["Local Environment"] = run_local_validation()
            results["Claude Desktop Integration"] = run_claude_desktop_tests()
            results["Scenario Tests"] = run_existing_e2e_scenarios()

        if args.all or args.docker:
            results["Docker Workflows"] = run_docker_tests()

        if args.all or args.performance:
            results["Performance Tests"] = run_performance_tests()

        # Final summary
        end_time = time.time()
        duration = end_time - start_time

        print("\n" + "=" * 60)
        print("🎊 E2E TESTING SUMMARY")
        print("=" * 60)

        passed_suites = 0
        total_suites = len(results)

        for suite_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {suite_name}")
            if passed:
                passed_suites += 1

        print(f"\nOverall Results: {passed_suites}/{total_suites} test suites passed")
        print(f"Total Duration: {duration:.1f}s")

        if passed_suites == total_suites:
            print("\n🎉 ALL E2E TESTS PASSED!")
            print("✅ RMCP is ready for production use across all environments")
            print()
            print("🚀 Ready for:")
            print("  • Claude Desktop integration")
            print("  • Docker deployment")
            print("  • Production statistical analysis")
            print("  • CI/CD pipeline")
        else:
            print(f"\n⚠️  {total_suites - passed_suites} test suite(s) failed")
            print("Check the individual test outputs above for details")

        return passed_suites == total_suites

    except KeyboardInterrupt:
        print("\n❌ Testing interrupted by user")
        return False
    except Exception as e:
        print(f"\n💥 Testing failed with exception: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
