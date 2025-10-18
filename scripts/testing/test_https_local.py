#!/usr/bin/env python3
"""
Local HTTPS testing script for RMCP.

Tests HTTPS functionality including certificate generation, server startup,
endpoint validation, and performance comparison between HTTP and HTTPS.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rmcp.transport.http import HTTPTransport


def print_status(message, success=True):
    """Print status message with emoji."""
    emoji = "✅" if success else "❌"
    print(f"{emoji} {message}")


def print_info(message):
    """Print info message."""
    print(f"🔍 {message}")


def print_warning(message):
    """Print warning message."""
    print(f"⚠️  {message}")


class HTTPSLocalTester:
    """Local HTTPS testing utility."""

    def __init__(self, cert_dir=None, verbose=False):
        self.cert_dir = Path(cert_dir) if cert_dir else Path.cwd() / "certs"
        self.verbose = verbose
        self.cert_file = self.cert_dir / "localhost.pem"
        self.key_file = self.cert_dir / "localhost-key.pem"

    def check_prerequisites(self):
        """Check if required tools are available."""
        print_info("Checking prerequisites...")

        # Check mkcert
        try:
            result = subprocess.run(
                ["mkcert", "-version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                print_status("mkcert is available")
                return True
            else:
                print_status("mkcert is not working", False)
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print_warning(
                "mkcert not found. Run ./scripts/setup/setup_https_dev.sh first"
            )
            return False

    def check_certificates(self):
        """Check if certificates exist and are valid."""
        print_info("Checking SSL certificates...")

        if not self.cert_file.exists():
            print_warning(f"Certificate file not found: {self.cert_file}")
            return False

        if not self.key_file.exists():
            print_warning(f"Key file not found: {self.key_file}")
            return False

        # Check certificate validity
        try:
            result = subprocess.run(
                [
                    "openssl",
                    "x509",
                    "-in",
                    str(self.cert_file),
                    "-noout",
                    "-checkend",
                    "86400",  # Check if valid for next 24 hours
                ],
                capture_output=True,
                timeout=10,
            )

            if result.returncode == 0:
                print_status("Certificates are valid")
                return True
            else:
                print_warning("Certificates may be expired or invalid")
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print_warning("openssl not available for certificate validation")
            return True  # Assume valid if we can't check

    def generate_certificates(self):
        """Generate test certificates using mkcert."""
        print_info("Generating test certificates...")

        self.cert_dir.mkdir(exist_ok=True)

        try:
            result = subprocess.run(
                [
                    "mkcert",
                    "-cert-file",
                    str(self.cert_file),
                    "-key-file",
                    str(self.key_file),
                    "localhost",
                    "127.0.0.1",
                    "::1",
                ],
                cwd=self.cert_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print_status("Test certificates generated successfully")
                return True
            else:
                print_status(f"Certificate generation failed: {result.stderr}", False)
                return False
        except subprocess.TimeoutExpired:
            print_status("Certificate generation timed out", False)
            return False

    async def test_https_server(self, port=8443):
        """Test HTTPS server functionality."""
        print_info(f"Testing HTTPS server on port {port}...")

        # Create HTTPS transport
        transport = HTTPTransport(
            host="127.0.0.1",
            port=port,
            ssl_keyfile=str(self.key_file),
            ssl_certfile=str(self.cert_file),
        )

        # Mock message handler
        async def mock_handler(message):
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "status": "ok",
                    "method": message.get("method"),
                    "timestamp": time.time(),
                },
            }

        transport.set_message_handler(mock_handler)

        # Start server
        server_task = asyncio.create_task(transport.run())

        try:
            # Wait for server to start
            await asyncio.sleep(1.0)

            # Test endpoints
            await self._test_https_endpoints(port)

            print_status("HTTPS server test completed successfully")
            return True

        except Exception as e:
            print_status(f"HTTPS server test failed: {e}", False)
            return False
        finally:
            # Clean up
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    async def _test_https_endpoints(self, port):
        """Test individual HTTPS endpoints."""
        base_url = f"https://127.0.0.1:{port}"

        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:

            # Test health endpoint
            print_info("Testing /health endpoint...")
            response = await client.get(f"{base_url}/health")
            assert response.status_code == 200
            health_data = response.json()
            assert health_data["status"] == "healthy"
            print_status("Health endpoint working")

            # Test MCP endpoint
            print_info("Testing /mcp endpoint...")
            mcp_response = await client.post(
                f"{base_url}/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                headers={"Content-Type": "application/json"},
            )
            assert mcp_response.status_code == 200
            mcp_data = mcp_response.json()
            assert mcp_data["jsonrpc"] == "2.0"
            assert mcp_data["result"]["status"] == "ok"
            print_status("MCP endpoint working")

            # Test SSE endpoint (just check it responds)
            print_info("Testing /mcp/sse endpoint...")
            async with client.stream("GET", f"{base_url}/mcp/sse") as sse_response:
                assert sse_response.status_code == 200
                assert "text/plain" in sse_response.headers.get("content-type", "")
                print_status("SSE endpoint accessible")

    async def performance_comparison(
        self, http_port=8080, https_port=8443, requests=10
    ):
        """Compare HTTP vs HTTPS performance."""
        print_info(f"Running performance comparison ({requests} requests each)...")

        # Test HTTP performance
        http_transport = HTTPTransport(host="127.0.0.1", port=http_port)
        https_transport = HTTPTransport(
            host="127.0.0.1",
            port=https_port,
            ssl_keyfile=str(self.key_file),
            ssl_certfile=str(self.cert_file),
        )

        async def mock_handler(message):
            return {"jsonrpc": "2.0", "id": message.get("id"), "result": "ok"}

        http_transport.set_message_handler(mock_handler)
        https_transport.set_message_handler(mock_handler)

        # Start servers
        http_task = asyncio.create_task(http_transport.run())
        https_task = asyncio.create_task(https_transport.run())

        try:
            await asyncio.sleep(1.0)  # Wait for servers to start

            # Measure HTTP performance
            http_times = []
            async with httpx.AsyncClient(timeout=10.0) as client:
                for _ in range(requests):
                    start = time.time()
                    response = await client.get(f"http://127.0.0.1:{http_port}/health")
                    end = time.time()
                    if response.status_code == 200:
                        http_times.append(end - start)

            # Measure HTTPS performance
            https_times = []
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                for _ in range(requests):
                    start = time.time()
                    response = await client.get(
                        f"https://127.0.0.1:{https_port}/health"
                    )
                    end = time.time()
                    if response.status_code == 200:
                        https_times.append(end - start)

            # Calculate and display results
            if http_times and https_times:
                http_avg = sum(http_times) / len(http_times) * 1000
                https_avg = sum(https_times) / len(https_times) * 1000
                overhead = (
                    ((https_avg - http_avg) / http_avg) * 100 if http_avg > 0 else 0
                )

                print_info("Performance Results:")
                print(f"  HTTP average:  {http_avg:.2f}ms")
                print(f"  HTTPS average: {https_avg:.2f}ms")
                print(f"  SSL overhead:  {overhead:.1f}%")

                if overhead < 50:  # Less than 50% overhead is reasonable
                    print_status("SSL overhead is within acceptable range")
                else:
                    print_warning("SSL overhead is higher than expected")

        finally:
            # Clean up
            http_task.cancel()
            https_task.cancel()
            try:
                await asyncio.gather(http_task, https_task, return_exceptions=True)
            except:
                pass

    def test_certificate_details(self):
        """Display certificate details."""
        print_info("Certificate Details:")

        try:
            # Get certificate info
            result = subprocess.run(
                ["openssl", "x509", "-in", str(self.cert_file), "-text", "-noout"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                output = result.stdout

                # Extract key information
                for line in output.split("\n"):
                    line = line.strip()
                    if "Subject:" in line:
                        print(f"  {line}")
                    elif "DNS:" in line or "IP Address:" in line:
                        print(f"  {line}")
                    elif "Not Before:" in line:
                        print(f"  {line}")
                    elif "Not After:" in line:
                        print(f"  {line}")

                print_status("Certificate details displayed")
            else:
                print_warning("Could not read certificate details")

        except (FileNotFoundError, subprocess.TimeoutExpired):
            print_warning("openssl not available")

    async def run_full_test(self):
        """Run complete HTTPS test suite."""
        print("🔐 RMCP HTTPS Local Testing")
        print("=" * 50)

        # Check prerequisites
        if not self.check_prerequisites():
            print_status("Prerequisites check failed", False)
            return False

        # Check or generate certificates
        if not self.check_certificates():
            if not self.generate_certificates():
                print_status("Certificate setup failed", False)
                return False

        # Display certificate details
        self.test_certificate_details()

        # Test HTTPS functionality
        if not await self.test_https_server():
            print_status("HTTPS server test failed", False)
            return False

        # Performance comparison
        try:
            await self.performance_comparison()
        except Exception as e:
            print_warning(f"Performance comparison failed: {e}")

        print_status("All HTTPS tests completed successfully! 🎉")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test RMCP HTTPS functionality locally"
    )
    parser.add_argument(
        "--cert-dir", help="Directory containing SSL certificates (default: ./certs)"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--performance-only",
        action="store_true",
        help="Run only performance comparison (requires existing setup)",
    )
    parser.add_argument(
        "--port", type=int, default=8443, help="HTTPS port to test (default: 8443)"
    )

    args = parser.parse_args()

    tester = HTTPSLocalTester(cert_dir=args.cert_dir, verbose=args.verbose)

    if args.performance_only:
        # Run only performance test
        if not tester.check_certificates():
            print_status("Certificates not found for performance test", False)
            return 1

        asyncio.run(tester.performance_comparison())
        return 0

    # Run full test suite
    success = asyncio.run(tester.run_full_test())
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
