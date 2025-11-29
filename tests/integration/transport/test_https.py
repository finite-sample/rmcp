"""
HTTPS integration tests for HTTP transport.

Tests SSL/TLS functionality including certificate validation,
HTTPS endpoints, and security configurations.
"""

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path

import httpx
import pytest
from rmcp.transport.http import HTTPTransport


@pytest.fixture
def temp_cert_dir():
    """Create temporary directory for test certificates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cert_dir = Path(tmpdir)
        yield cert_dir


@pytest.fixture
def https_certificates(temp_cert_dir):
    """Generate test certificates using mkcert if available."""
    cert_file = temp_cert_dir / "test.pem"
    key_file = temp_cert_dir / "test-key.pem"

    # Try to use mkcert if available
    try:
        # Check if mkcert is available
        subprocess.run(
            ["mkcert", "-version"], capture_output=True, check=True, timeout=10
        )

        # Generate certificates
        subprocess.run(
            [
                "mkcert",
                "-cert-file",
                str(cert_file),
                "-key-file",
                str(key_file),
                "localhost",
                "127.0.0.1",
            ],
            cwd=temp_cert_dir,
            capture_output=True,
            check=True,
            timeout=30,
        )

        return {
            "cert_file": str(cert_file),
            "key_file": str(key_file),
            "has_mkcert": True,
        }
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        # Fallback: generate self-signed certificate using openssl
        try:
            subprocess.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-keyout",
                    str(key_file),
                    "-out",
                    str(cert_file),
                    "-days",
                    "1",
                    "-nodes",
                    "-subj",
                    "/CN=localhost",
                ],
                capture_output=True,
                check=True,
                timeout=30,
            )

            return {
                "cert_file": str(cert_file),
                "key_file": str(key_file),
                "has_mkcert": False,
            }
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            pytest.skip(
                "Neither mkcert nor openssl available for generating test certificates"
            )


class TestHTTPSTransportIntegration:
    """Test HTTPS functionality in HTTP transport."""

    def test_https_transport_initialization(self, https_certificates):
        """Test HTTPS transport initializes correctly with SSL certificates."""
        transport = HTTPTransport(
            host="localhost",
            port=8443,
            ssl_keyfile=https_certificates["key_file"],
            ssl_certfile=https_certificates["cert_file"],
        )

        assert transport.is_https is True
        assert transport.ssl_keyfile == https_certificates["key_file"]
        assert transport.ssl_certfile == https_certificates["cert_file"]

    def test_http_transport_no_ssl(self):
        """Test HTTP transport without SSL certificates."""
        transport = HTTPTransport(host="localhost", port=8000)

        assert transport.is_https is False
        assert transport.ssl_keyfile is None
        assert transport.ssl_certfile is None

    def test_ssl_certificate_validation_missing_cert(self, temp_cert_dir):
        """Test that missing certificate file is caught during validation."""
        temp_cert_dir / "nonexistent.pem"
        nonexistent_key = temp_cert_dir / "nonexistent-key.pem"

        # Create key file but not cert file
        nonexistent_key.write_text("dummy key content")

        with pytest.raises(ValueError, match="SSL certificate file is required"):
            HTTPTransport(
                host="localhost",
                port=8443,
                ssl_keyfile=str(nonexistent_key),
                ssl_certfile=None,
            )

    def test_ssl_certificate_validation_missing_key(self, temp_cert_dir):
        """Test that missing key file is caught during validation."""
        nonexistent_cert = temp_cert_dir / "nonexistent.pem"

        # Create cert file but not key file
        nonexistent_cert.write_text("dummy cert content")

        with pytest.raises(ValueError, match="SSL key file is required"):
            HTTPTransport(
                host="localhost",
                port=8443,
                ssl_keyfile=None,
                ssl_certfile=str(nonexistent_cert),
            )

    @pytest.mark.asyncio
    async def test_https_server_startup_and_shutdown(self, https_certificates):
        """Test HTTPS server can start up and shut down properly."""
        transport = HTTPTransport(
            host="localhost",
            port=8443,
            ssl_keyfile=https_certificates["key_file"],
            ssl_certfile=https_certificates["cert_file"],
        )

        # Mock message handler
        async def mock_handler(message):
            return {"jsonrpc": "2.0", "id": message.get("id"), "result": "ok"}

        transport.set_message_handler(mock_handler)

        # Test startup
        await transport.startup()

        # Test shutdown
        await transport.shutdown()

    @pytest.mark.asyncio
    async def test_https_endpoint_functionality(self, https_certificates):
        """Test HTTPS endpoints work correctly."""
        transport = HTTPTransport(
            host="127.0.0.1",  # Use IP to avoid DNS issues
            port=8444,  # Use different port to avoid conflicts
            ssl_keyfile=https_certificates["key_file"],
            ssl_certfile=https_certificates["cert_file"],
        )

        # Mock message handler
        async def mock_handler(message):
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {"status": "ok", "method": message.get("method")},
            }

        transport.set_message_handler(mock_handler)

        # Start server in background
        server_task = asyncio.create_task(transport.run())

        try:
            # Wait a moment for server to start
            await asyncio.sleep(0.5)

            # Create HTTPS client that accepts self-signed certificates
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                # Test health endpoint
                health_response = await client.get("https://127.0.0.1:8444/health")
                assert health_response.status_code == 200
                health_data = health_response.json()
                assert health_data["status"] == "healthy"
                assert health_data["transport"] == "HTTP"

                # First initialize the session
                init_response = await client.post(
                    "https://127.0.0.1:8444/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "clientInfo": {"name": "test-client", "version": "1.0.0"},
                        },
                    },
                    headers={
                        "Content-Type": "application/json",
                        "MCP-Protocol-Version": "2025-11-25",
                    },
                )
                assert init_response.status_code == 200

                # Get session ID from response headers
                session_id = init_response.headers.get("mcp-session-id")
                assert session_id is not None

                # Then test MCP endpoint with tools/list using the same session
                mcp_response = await client.post(
                    "https://127.0.0.1:8444/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list",
                        "params": {},
                    },
                    headers={
                        "Content-Type": "application/json",
                        "MCP-Protocol-Version": "2025-11-25",
                        "mcp-session-id": session_id,
                    },
                )
                assert mcp_response.status_code == 200
                mcp_data = mcp_response.json()
                assert mcp_data["jsonrpc"] == "2.0"
                assert mcp_data["id"] == 2
                assert mcp_data["result"]["status"] == "ok"
                assert mcp_data["result"]["method"] == "tools/list"

        finally:
            # Clean up: cancel server task
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    def test_cors_configuration_with_https(self, https_certificates):
        """Test that CORS origins are configured correctly for HTTPS."""
        transport = HTTPTransport(
            host="localhost",
            port=8443,
            ssl_keyfile=https_certificates["key_file"],
            ssl_certfile=https_certificates["cert_file"],
        )

        # Check that FastAPI app has CORS middleware configured
        from fastapi.middleware.cors import CORSMiddleware

        # Debug: Print actual middleware structure
        middleware_info = []
        for m in transport.app.user_middleware:
            if hasattr(m, "cls"):
                middleware_info.append(m.cls)
            else:
                middleware_info.append(type(m))

        # Check if CORSMiddleware is configured (could be in middleware stack)
        has_cors = any(
            cls == CORSMiddleware
            or (hasattr(cls, "__name__") and "CORSMiddleware" in cls.__name__)
            for cls in middleware_info
        )

        assert has_cors, f"CORS middleware not found. Found: {middleware_info}"

    def test_security_warning_for_remote_http(self, caplog):
        """Test that security warning is issued for remote HTTP binding."""
        import logging

        caplog.set_level(logging.WARNING)

        # Create HTTP transport bound to all interfaces (insecure)
        HTTPTransport(host="0.0.0.0", port=8000)

        # Check that warning was logged
        assert any("SECURITY WARNING" in record.message for record in caplog.records)
        assert any("without SSL/TLS" in record.message for record in caplog.records)

    def test_no_security_warning_for_remote_https(self, https_certificates, caplog):
        """Test that no security warning is issued for remote HTTPS binding."""
        import logging

        caplog.set_level(logging.INFO)

        # Create HTTPS transport bound to all interfaces (secure)
        HTTPTransport(
            host="0.0.0.0",
            port=8443,
            ssl_keyfile=https_certificates["key_file"],
            ssl_certfile=https_certificates["cert_file"],
        )

        # Check that HTTPS info message was logged but no warning
        assert any("HTTPS enabled" in record.message for record in caplog.records)
        assert not any(
            "SECURITY WARNING" in record.message for record in caplog.records
        )


class TestHTTPSConfigurationIntegration:
    """Test HTTPS configuration integration."""

    def test_environment_variable_ssl_configuration(
        self, https_certificates, monkeypatch
    ):
        """Test SSL configuration through environment variables."""
        # Set environment variables
        monkeypatch.setenv("RMCP_HTTP_SSL_KEYFILE", https_certificates["key_file"])
        monkeypatch.setenv("RMCP_HTTP_SSL_CERTFILE", https_certificates["cert_file"])

        # Import after setting environment variables and force reload
        from rmcp.config import get_config

        config = get_config(reload=True)

        # Verify configuration picked up environment variables
        assert config.http.ssl_keyfile == https_certificates["key_file"]
        assert config.http.ssl_certfile == https_certificates["cert_file"]

    def test_config_file_ssl_configuration(self, https_certificates, temp_cert_dir):
        """Test SSL configuration through config file."""
        config_file = temp_cert_dir / "test-config.json"
        config_data = {
            "http": {
                "host": "localhost",
                "port": 8443,
                "ssl_keyfile": https_certificates["key_file"],
                "ssl_certfile": https_certificates["cert_file"],
            }
        }

        config_file.write_text(json.dumps(config_data, indent=2))

        # Load configuration from file
        from rmcp.config import load_config

        config = load_config(config_file=config_file)

        # Verify configuration was loaded correctly
        assert config.http.ssl_keyfile == https_certificates["key_file"]
        assert config.http.ssl_certfile == https_certificates["cert_file"]
        assert config.http.port == 8443


class TestHTTPSEdgeCases:
    """Test edge cases and error conditions for HTTPS."""

    def test_partial_ssl_configuration_cli_keyfile_only(self, https_certificates):
        """Test error when only keyfile is provided via CLI."""
        # Clear config cache to avoid fallback values from previous tests
        from rmcp.config import get_config

        get_config(reload=True)

        with pytest.raises(ValueError, match="SSL certificate file is required"):
            HTTPTransport(
                host="localhost",
                port=8443,
                ssl_keyfile=https_certificates["key_file"],
                ssl_certfile=None,
            )

    def test_partial_ssl_configuration_cli_certfile_only(self, https_certificates):
        """Test error when only certfile is provided via CLI."""
        # Clear config cache to avoid fallback values from previous tests
        from rmcp.config import get_config

        get_config(reload=True)

        with pytest.raises(ValueError, match="SSL key file is required"):
            HTTPTransport(
                host="localhost",
                port=8443,
                ssl_keyfile=None,
                ssl_certfile=https_certificates["cert_file"],
            )

    def test_invalid_certificate_file_path(self, temp_cert_dir):
        """Test error when certificate file doesn't exist."""
        key_file = temp_cert_dir / "valid-key.pem"
        key_file.write_text("dummy key content")

        nonexistent_cert = temp_cert_dir / "nonexistent.pem"

        with pytest.raises(ValueError, match="SSL certificate file not found"):
            HTTPTransport(
                host="localhost",
                port=8443,
                ssl_keyfile=str(key_file),
                ssl_certfile=str(nonexistent_cert),
            )

    def test_invalid_key_file_path(self, temp_cert_dir):
        """Test error when key file doesn't exist."""
        cert_file = temp_cert_dir / "valid-cert.pem"
        cert_file.write_text("dummy cert content")

        nonexistent_key = temp_cert_dir / "nonexistent-key.pem"

        with pytest.raises(ValueError, match="SSL key file not found"):
            HTTPTransport(
                host="localhost",
                port=8443,
                ssl_keyfile=str(nonexistent_key),
                ssl_certfile=str(cert_file),
            )


class TestHTTPSDockerIntegration:
    """Test HTTPS functionality in Docker environment."""

    @pytest.mark.skipif(
        not os.path.exists("/.dockerenv"),
        reason="Docker-specific tests only run in Docker containers",
    )
    def test_mkcert_available_in_docker(self):
        """Test that mkcert is available in Docker development environment."""
        result = subprocess.run(
            ["mkcert", "-version"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        assert result.stdout.strip().startswith("v")

    @pytest.mark.skipif(
        not os.path.exists("/.dockerenv"),
        reason="Docker-specific tests only run in Docker containers",
    )
    def test_generate_certificates_in_docker(self, temp_cert_dir):
        """Test certificate generation in Docker environment."""
        cert_file = temp_cert_dir / "docker-test.pem"
        key_file = temp_cert_dir / "docker-test-key.pem"

        # Generate certificates using mkcert
        result = subprocess.run(
            [
                "mkcert",
                "-cert-file",
                str(cert_file),
                "-key-file",
                str(key_file),
                "localhost",
                "127.0.0.1",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert cert_file.exists()
        assert key_file.exists()
        assert cert_file.stat().st_size > 0
        assert key_file.stat().st_size > 0
