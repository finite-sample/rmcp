#!/usr/bin/env python3
"""
Test script for RMCP Claude web connector integration.

This script tests the RMCP server's compatibility with Claude's MCP connector system
by simulating the requests that Claude would make when using RMCP as a connector.
"""

import os
from typing import Any

import requests


class ClaudeConnectorTester:
    """Test RMCP connector integration with Claude web."""

    def __init__(
        self, server_url: str = "https://rmcp-server-394229601724.us-central1.run.app"
    ):
        self.server_url = server_url
        self.mcp_url = f"{server_url}/mcp"
        self.session_id = None
        self.session = requests.Session()

    def test_health_check(self) -> bool:
        """Test server health endpoint."""
        try:
            response = self.session.get(f"{self.server_url}/health")
            if response.ok:
                health_data = response.json()
                print(f"✅ Health Check: {health_data}")
                return True
            else:
                print(f"❌ Health Check Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health Check Error: {e}")
            return False

    def test_mcp_initialization(self) -> bool:
        """Test MCP session initialization (as Claude would do)."""
        try:
            response = self.session.post(
                self.mcp_url,
                headers={
                    "Content-Type": "application/json",
                    "MCP-Protocol-Version": "2025-11-25",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "claude-web-connector-test",
                            "version": "1.0",
                        },
                    },
                },
            )

            if response.ok:
                self.session_id = response.headers.get("Mcp-Session-Id")
                init_data = response.json()
                print(f"✅ MCP Initialization: Session ID = {self.session_id}")
                print(f"   Server Info: {init_data['result']['serverInfo']}")
                return True
            else:
                print(f"❌ MCP Initialization Failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ MCP Initialization Error: {e}")
            return False

    def test_tools_list(self) -> dict[str, Any]:
        """Test tools/list endpoint (as Claude would call)."""
        if not self.session_id:
            print("❌ No session ID available for tools/list test")
            return {}

        try:
            response = self.session.post(
                self.mcp_url,
                headers={
                    "Content-Type": "application/json",
                    "MCP-Protocol-Version": "2025-11-25",
                    "MCP-Session-Id": self.session_id,
                },
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            )

            if response.ok:
                tools_data = response.json()
                tools = tools_data.get("result", {}).get("tools", [])
                print(f"✅ Tools List: Found {len(tools)} tools")

                # Print first few tools for verification
                for i, tool in enumerate(tools[:5]):
                    print(
                        f"   Tool {i + 1}: {tool.get('name')} - {tool.get('description', 'No description')}"
                    )

                return tools_data
            else:
                print(f"❌ Tools List Failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return {}

        except Exception as e:
            print(f"❌ Tools List Error: {e}")
            return {}

    def test_tool_execution(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Test individual tool execution (as Claude would call)."""
        if not self.session_id:
            print(f"❌ No session ID available for {tool_name} test")
            return {}

        try:
            response = self.session.post(
                self.mcp_url,
                headers={
                    "Content-Type": "application/json",
                    "MCP-Protocol-Version": "2025-11-25",
                    "MCP-Session-Id": self.session_id,
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
            )

            if response.ok:
                result_data = response.json()
                if "error" in result_data:
                    print(
                        f"❌ Tool {tool_name} Error: {result_data['error']['message']}"
                    )
                    return result_data
                else:
                    print(f"✅ Tool {tool_name} Success")
                    # Print formatted text result
                    content = result_data.get("result", {}).get("content", [])
                    if content and len(content) > 0:
                        text_content = content[0].get("text", "")
                        # Show first few lines of output
                        lines = text_content.split("\n")[:5]
                        for line in lines:
                            if line.strip():
                                print(f"   {line.strip()}")
                    return result_data
            else:
                print(f"❌ Tool {tool_name} Failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return {}

        except Exception as e:
            print(f"❌ Tool {tool_name} Error: {e}")
            return {}

    def test_claude_api_integration(self, claude_api_key: str | None = None) -> bool:
        """Test actual Claude API integration with RMCP connector."""
        if not claude_api_key:
            print(
                "⚠️  Claude API key not provided, skipping Claude API integration test"
            )
            return True

        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": claude_api_key,
                    "anthropic-version": "2023-06-01",
                    "anthropic-beta": "mcp-client-2025-04-04",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 1000,
                    "mcp_servers": [
                        {"type": "url", "url": self.mcp_url, "name": "rmcp-statistics"}
                    ],
                    "messages": [
                        {
                            "role": "user",
                            "content": "Test RMCP connector by analyzing correlation between sales [100,120,115,140] and marketing [10,15,12,18]",
                        }
                    ],
                },
            )

            if response.ok:
                claude_response = response.json()
                print("✅ Claude API Integration: Success")
                print(
                    f"   Claude Response: {claude_response.get('content', 'No content')}"
                )
                return True
            else:
                print(f"❌ Claude API Integration Failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Claude API Integration Error: {e}")
            return False

    def run_comprehensive_test(
        self, claude_api_key: str | None = None
    ) -> dict[str, bool]:
        """Run all connector tests."""
        print("🧪 RMCP Claude Connector Integration Test")
        print("=" * 50)

        results = {}

        # Test 1: Health Check
        print("\n1. Testing Server Health...")
        results["health"] = self.test_health_check()

        # Test 2: MCP Initialization
        print("\n2. Testing MCP Initialization...")
        results["initialization"] = self.test_mcp_initialization()

        # Test 3: Tools List
        print("\n3. Testing Tools List...")
        tools_result = self.test_tools_list()
        results["tools_list"] = bool(tools_result)

        # Test 4: Tool Execution Examples
        print("\n4. Testing Tool Execution...")

        # Test linear_model
        print("\n   4a. Testing linear_model...")
        linear_result = self.test_tool_execution(
            "linear_model",
            {
                "formula": "sales ~ marketing",
                "data": {
                    "sales": [100, 120, 115, 140, 135],
                    "marketing": [10, 15, 12, 18, 16],
                },
            },
        )
        results["linear_model"] = bool(linear_result and "error" not in linear_result)

        # Test correlation_analysis
        print("\n   4b. Testing correlation_analysis...")
        corr_result = self.test_tool_execution(
            "correlation_analysis",
            {
                "data": {
                    "sales": [100, 120, 115, 140],
                    "marketing": [10, 15, 12, 18],
                    "satisfaction": [8.0, 8.5, 8.2, 9.0],
                },
                "method": "pearson",
            },
        )
        results["correlation_analysis"] = bool(
            corr_result and "error" not in corr_result
        )

        # Test build_formula
        print("\n   4c. Testing build_formula...")
        formula_result = self.test_tool_execution(
            "build_formula",
            {
                "description": "predict revenue from advertising spend and customer rating"
            },
        )
        results["build_formula"] = bool(
            formula_result and "error" not in formula_result
        )

        # Test 5: Claude API Integration (optional)
        print("\n5. Testing Claude API Integration...")
        results["claude_api"] = self.test_claude_api_integration(claude_api_key)

        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)

        passed = sum(results.values())
        total = len(results)

        for test_name, passed_test in results.items():
            status = "✅ PASS" if passed_test else "❌ FAIL"
            print(f"{test_name:20} : {status}")

        print(f"\nOverall: {passed}/{total} tests passed ({passed / total * 100:.1f}%)")

        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Connector is ready for Claude integration.")
        else:
            print(
                f"\n⚠️  {total - passed} test(s) failed. Review issues before submission."
            )

        return results


def main():
    """Main test execution."""
    # Get Claude API key from environment (optional)
    claude_api_key = os.getenv("CLAUDE_API_KEY")

    # Run tests
    tester = ClaudeConnectorTester()
    results = tester.run_comprehensive_test(claude_api_key)

    # Generate connector validation report
    if all(results.values()):
        print("\n📋 CONNECTOR VALIDATION REPORT")
        print("=" * 50)
        print("✅ Server Health: Operational")
        print("✅ MCP Protocol: Compliant")
        print("✅ Tool Discovery: Functional")
        print("✅ Tool Execution: Working")
        print("✅ Session Management: Proper")
        if claude_api_key:
            print("✅ Claude API Integration: Validated")
        else:
            print("⚠️  Claude API Integration: Not tested (no API key)")

        print("\n🚀 READY FOR SUBMISSION TO ANTHROPIC CONNECTORS DIRECTORY")
        print("\nNext steps:")
        print("1. Submit connector-manifest.json to Anthropic")
        print("2. Provide connector specification document")
        print("3. Complete Anthropic's security review process")
        print("4. Launch in Claude connectors directory")


if __name__ == "__main__":
    main()
