#!/usr/bin/env python3
"""
Comprehensive test runner for RMCP.
Runs all tests in the correct order: unit -> integration -> e2e
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description, cwd=None):
    """Run a command and return success status."""
    print(f"\n🔧 {description}")
    print("-" * 60)
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd or Path(__file__).parent,
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"💥 {description} - ERROR: {e}")
        return False


def main():
    """Run all tests in organized sequence."""
    print("🧪 RMCP Comprehensive Test Suite")
    print("=" * 70)
    print("Running tests in logical order: unit → integration → e2e")
    
    # Track results
    results = []
    
    # Phase 1: Unit Tests
    print(f"\n🎯 PHASE 1: Unit Tests")
    print("=" * 40)
    
    unit_tests = [
        ("python tests/unit/test_new_tools.py", "New Tools Unit Tests"),
        ("python tests/unit/test_server_basic.py", "Server Basic Tests")
    ]
    
    for cmd, desc in unit_tests:
        success = run_command(cmd, desc)
        results.append((desc, success))
    
    # Phase 2: Integration Tests
    print(f"\n🎯 PHASE 2: Integration Tests") 
    print("=" * 40)
    
    integration_tests = [
        ("python tests/integration/test_mcp_interface.py", "MCP Protocol Interface"),
        ("python tests/integration/test_new_features_integration.py", "New Features Integration"),
        ("python tests/integration/test_direct_capabilities.py", "Direct Tool Capabilities")
    ]
    
    for cmd, desc in integration_tests:
        success = run_command(cmd, desc)
        results.append((desc, success))
    
    # Phase 3: End-to-End Tests
    print(f"\n🎯 PHASE 3: End-to-End Tests")
    print("=" * 40)
    
    e2e_tests = [
        ("python tests/e2e/realistic_scenarios.py", "Realistic User Scenarios"),
        ("python tests/e2e/test_claude_desktop_scenarios.py", "Claude Desktop Scenarios"),
        ("python tests/e2e/test_docker_simulation.py", "Docker Environment Simulation")
    ]
    
    for cmd, desc in e2e_tests:
        success = run_command(cmd, desc)
        results.append((desc, success))
    
    # Phase 4: Verification Tests
    print(f"\n🎯 PHASE 4: Verification Tests")
    print("=" * 40)
    
    # Tool count verification
    tool_count_cmd = '''
    python -c "
import sys
sys.path.insert(0, '.')
from rmcp.core.server import create_server
from rmcp.cli import _register_builtin_tools
import asyncio

async def verify():
    server = create_server()
    _register_builtin_tools(server)
    ctx = server.create_context('test', 'tools/list')
    result = await server.tools.list_tools(ctx)
    count = len(result['tools'])
    print(f'Registered tools: {count}')
    assert count >= 39, f'Expected at least 39 tools, got {count}'
    print('✅ Tool count verification passed')

asyncio.run(verify())
"'''
    
    success = run_command(tool_count_cmd, "Tool Count Verification")
    results.append(("Tool Count Verification", success))
    
    # Final Results
    print("\n" + "=" * 70)
    print("🎉 FINAL TEST RESULTS")
    print("=" * 70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"📊 Overall Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("\n📋 Detailed Results:")
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    if passed == total:
        print("\n🎊 ALL TESTS PASSED!")
        print("🚀 RMCP is ready for production deployment")
        return True
    elif passed >= total * 0.8:
        print("\n✨ Most tests passed - Good overall health")
        print(f"⚠️  {total - passed} test(s) need attention")
        return False
    else:
        print("\n⚠️  Multiple test failures detected")
        print("🔧 Significant issues need resolution")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Test run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        sys.exit(1)