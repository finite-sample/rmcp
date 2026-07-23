"""
HTTPS integration tests for the Streamable HTTP transport.

Tests SSL/TLS functionality: certificate validation, a real HTTPS
server boot, and CLI security behavior (auth refusal on remote binds,
SSL configuration plumb-through).
"""

import asyncio
import ssl
import subprocess
import tempfile
from pathlib import Path

import httpx
import pytest
from click.testing import CliRunner
from rmcp.cli import cli
from rmcp.core.server import create_server
from rmcp.transport.sdk import create_streamable_http_app, run_streamable_http


@pytest.fixture
def temp_cert_dir():
    """Create temporary directory for test certificates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def https_certificates(temp_cert_dir):
    """Generate test certificates using mkcert or openssl."""
    cert_file = temp_cert_dir / "test.pem"
    key_file = temp_cert_dir / "test-key.pem"
    try:
        subprocess.run(
            ["mkcert", "-version"], capture_output=True, check=True, timeout=10
        )
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
        caroot = subprocess.run(
            ["mkcert", "-CAROOT"],
            capture_output=True,
            check=True,
            timeout=10,
            text=True,
        ).stdout.strip()
        return {
            "cert_file": str(cert_file),
            "key_file": str(key_file),
            "ca_file": str(Path(caroot) / "rootCA.pem"),
        }
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
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
                    "-addext",
                    "subjectAltName=DNS:localhost,IP:127.0.0.1",
                ],
                capture_output=True,
                check=True,
                timeout=30,
            )
            # Self-signed: the certificate is its own trust anchor
            return {
                "cert_file": str(cert_file),
                "key_file": str(key_file),
                "ca_file": str(cert_file),
            }
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            pytest.skip("Neither mkcert nor openssl available for test certificates")


def _light_server(tmp_path):
    server = create_server()
    server.configure(allowed_paths=[str(tmp_path)], read_only=True)
    return server


class TestSSLValidation:
    """SSL configuration validation in run_streamable_http."""

    def test_missing_cert_file(self, temp_cert_dir, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            run_streamable_http(
                _light_server(tmp_path),
                ssl_keyfile=str(temp_cert_dir / "missing-key.pem"),
                ssl_certfile=str(temp_cert_dir / "missing-cert.pem"),
            )

    def test_missing_key_file(self, https_certificates, temp_cert_dir, tmp_path):
        with pytest.raises(FileNotFoundError, match="keyfile"):
            run_streamable_http(
                _light_server(tmp_path),
                ssl_keyfile=str(temp_cert_dir / "nope-key.pem"),
                ssl_certfile=https_certificates["cert_file"],
            )

    def test_partial_ssl_configuration_rejected(self, https_certificates, tmp_path):
        with pytest.raises(ValueError, match="Both"):
            run_streamable_http(
                _light_server(tmp_path),
                ssl_keyfile=https_certificates["key_file"],
            )
        with pytest.raises(ValueError, match="Both"):
            run_streamable_http(
                _light_server(tmp_path),
                ssl_certfile=https_certificates["cert_file"],
            )


class TestHTTPSServer:
    """Boot a real uvicorn HTTPS server and hit it."""

    @pytest.mark.asyncio
    async def test_https_health_endpoint(self, https_certificates, tmp_path):
        import uvicorn

        app = create_streamable_http_app(
            _light_server(tmp_path), manage_server_lifecycle=False
        )
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=0,
            ssl_keyfile=https_certificates["key_file"],
            ssl_certfile=https_certificates["cert_file"],
            log_level="error",
        )
        server = uvicorn.Server(config)
        task = asyncio.create_task(server.serve())
        try:
            for _ in range(100):
                if server.started:
                    break
                await asyncio.sleep(0.05)
            assert server.started, "HTTPS server failed to start"
            port = server.servers[0].sockets[0].getsockname()[1]
            ssl_context = ssl.create_default_context(
                cafile=https_certificates["ca_file"]
            )
            async with httpx.AsyncClient(verify=ssl_context) as client:
                response = await client.get(f"https://localhost:{port}/health")
                assert response.status_code == 200
                assert response.json()["status"] == "healthy"
        finally:
            server.should_exit = True
            await task


class TestCLISecurity:
    """serve-http CLI security behavior (transport is mocked out)."""

    def _invoke(self, monkeypatch, args, env=None):
        captured = {}

        def fake_run(server, **kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("rmcp.cli.run_streamable_http", fake_run)
        runner = CliRunner()
        result = runner.invoke(cli, ["serve-http", *args], env=env or {})
        return result, captured

    def test_remote_bind_without_key_refused(self, monkeypatch):
        monkeypatch.delenv("RMCP_API_KEY", raising=False)
        result, captured = self._invoke(monkeypatch, ["--host", "0.0.0.0"])
        assert result.exit_code == 1
        assert "Refusing to serve" in result.output
        assert not captured

    def test_remote_bind_with_allow_unauthenticated(self, monkeypatch):
        monkeypatch.delenv("RMCP_API_KEY", raising=False)
        result, captured = self._invoke(
            monkeypatch, ["--host", "0.0.0.0", "--allow-unauthenticated"]
        )
        assert result.exit_code == 0
        assert captured["api_keys"] == set()

    def test_localhost_bind_without_key_allowed(self, monkeypatch):
        monkeypatch.delenv("RMCP_API_KEY", raising=False)
        result, captured = self._invoke(monkeypatch, ["--host", "127.0.0.1"])
        assert result.exit_code == 0

    def test_api_key_flag_and_env_merge(self, monkeypatch):
        result, captured = self._invoke(
            monkeypatch,
            ["--host", "0.0.0.0", "--api-key", "flag-key"],
            env={"RMCP_API_KEY": "env-key-1, env-key-2"},
        )
        assert result.exit_code == 0
        assert captured["api_keys"] == {"flag-key", "env-key-1", "env-key-2"}

    def test_ssl_options_forwarded(self, monkeypatch, https_certificates):
        result, captured = self._invoke(
            monkeypatch,
            [
                "--host",
                "127.0.0.1",
                "--ssl-keyfile",
                https_certificates["key_file"],
                "--ssl-certfile",
                https_certificates["cert_file"],
            ],
        )
        assert result.exit_code == 0
        assert captured["ssl_keyfile"] == https_certificates["key_file"]
        assert captured["ssl_certfile"] == https_certificates["cert_file"]
        assert "🔒" in result.output
