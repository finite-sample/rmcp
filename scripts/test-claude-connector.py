#!/usr/bin/env python3
"""
Test script for RMCP remote connector integration (Claude web / OpenAI).

Simulates the requests a remote MCP client makes against the Streamable HTTP
endpoint: initialize handshake, initialized notification, tools/list, and
tool execution. Optionally validates end-to-end Claude API integration via
the MCP connector.

Usage:
    python scripts/test-claude-connector.py [server_url]

Environment:
    RMCP_API_KEY    Bearer token for the /mcp endpoint (if the server requires auth)
    CLAUDE_API_KEY  Anthropic API key for the optional end-to-end test
"""

import json
import os
import sys
from typing import Any

import requests

PROTOCOL_VERSION = "2025-11-25"


class ConnectorTester:
    """Test RMCP connector integration over MCP Streamable HTTP."""

    def __init__(
        self, server_url: str = "https://rmcp-server-394229601724.us-central1.run.app"
    ):
        self.server_url = server_url.rstrip("/")
        self.mcp_url = f"{self.server_url}/mcp"
        self.session_id: str | None = None
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": PROTOCOL_VERSION,
            }
        )
        api_key = os.getenv("RMCP_API_KEY")
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"

    def _post(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """POST a JSON-RPC message; parse JSON or SSE-framed response."""
        headers = {}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        response = self.session.post(
            self.mcp_url, json=payload, headers=headers, timeout=60
        )
        response.raise_for_status()
        if response.status_code == 202 or not response.content:
            return None
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("text/event-stream"):
            message = None
            for line in response.text.splitlines():
                if line.startswith("data:"):
                    message = json.loads(line[len("data:") :].strip())
            return message
        if "mcp-session-id" in response.headers:
            self.session_id = response.headers["mcp-session-id"]
        return response.json()

    def test_health_check(self) -> bool:
        """Test server health endpoint."""
        try:
            response = self.session.get(f"{self.server_url}/health", timeout=30)
            if response.ok:
                print(f"✅ Health Check: {response.json()}")
                return True
            print(f"❌ Health Check Failed: {response.status_code}")
            return False
        except Exception as e:
            print(f"❌ Health Check Error: {e}")
            return False

    def test_mcp_initialization(self) -> bool:
        """Run the initialize handshake as a remote connector would."""
        try:
            response = self.session.post(
                self.mcp_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {
                            "name": "claude-web-connector-test",
                            "version": "1.0",
                        },
                    },
                },
                timeout=60,
            )
            if not response.ok:
                print(f"❌ MCP Initialization Failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
            self.session_id = response.headers.get("mcp-session-id")
            content_type = response.headers.get("content-type", "")
            if content_type.startswith("text/event-stream"):
                message = None
                for line in response.text.splitlines():
                    if line.startswith("data:"):
                        message = json.loads(line[len("data:") :].strip())
            else:
                message = response.json()
            result = message["result"]
            print(f"✅ MCP Initialization: Session ID = {self.session_id}")
            print(f"   Protocol: {result['protocolVersion']}")
            print(f"   Server Info: {result['serverInfo']}")
            # Complete the handshake per spec
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
            return True
        except Exception as e:
            print(f"❌ MCP Initialization Error: {e}")
            return False

    def test_tools_list(self) -> dict[str, Any]:
        """List tools over the connector endpoint."""
        try:
            message = self._post({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            tools = message["result"]["tools"]
            print(f"✅ Tools List: Found {len(tools)} tools")
            return {tool["name"]: tool for tool in tools}
        except Exception as e:
            print(f"❌ Tools List Error: {e}")
            return {}

    def test_tool_execution(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Execute a tool and return its result payload."""
        if not self.session_id:
            print("❌ No session; run initialization first")
            return None
        try:
            message = self._post(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                }
            )
            if message is None or "error" in message:
                print(f"❌ Tool {tool_name} Failed: {message}")
                return None
            result = message["result"]
            if result.get("isError"):
                print(f"❌ Tool {tool_name} returned error: {result['content']}")
                return {"error": result["content"]}
            print(f"✅ Tool {tool_name} Success")
            return result
        except Exception as e:
            print(f"❌ Tool {tool_name} Error: {e}")
            return None

    def test_claude_api_integration(self, claude_api_key: str | None = None) -> bool:
        """Test actual Claude API integration with the RMCP connector."""
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
                    "anthropic-beta": "mcp-client-2025-11-20",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-opus-4-8",
                    "max_tokens": 1000,
                    "mcp_servers": [
                        {
                            "type": "url",
                            "url": self.mcp_url,
                            "name": "rmcp-statistics",
                            **(
                                {
                                    "authorization_token": os.getenv("RMCP_API_KEY"),
                                }
                                if os.getenv("RMCP_API_KEY")
                                else {}
                            ),
                        }
                    ],
                    "tools": [
                        {"type": "mcp_toolset", "mcp_server_name": "rmcp-statistics"}
                    ],
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Test RMCP connector by analyzing correlation between "
                                "sales [100,120,115,140] and marketing [10,15,12,18]"
                            ),
                        }
                    ],
                },
                timeout=120,
            )
            if response.ok:
                claude_response = response.json()
                print("✅ Claude API Integration: Success")
                print(
                    f"   Claude Response: {claude_response.get('content', 'No content')}"
                )
                return True
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
        print("🧪 RMCP Remote Connector Integration Test")
        print("=" * 50)
        results = {}

        print("\n1. Testing Server Health...")
        results["health"] = self.test_health_check()

        print("\n2. Testing MCP Initialization...")
        results["initialization"] = self.test_mcp_initialization()

        print("\n3. Testing Tools List...")
        results["tools_list"] = bool(self.test_tools_list())

        print("\n4. Testing Tool Execution...")
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

        print("\n5. Testing Claude API Integration...")
        results["claude_api"] = self.test_claude_api_integration(claude_api_key)

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
            print("\n🎉 ALL TESTS PASSED! Connector is ready for remote integration.")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Review issues above.")
        return results


def main():
    """Main test execution."""
    server_url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://rmcp-server-394229601724.us-central1.run.app"
    )
    claude_api_key = os.getenv("CLAUDE_API_KEY")
    tester = ConnectorTester(server_url)
    tester.run_comprehensive_test(claude_api_key)


if __name__ == "__main__":
    main()
