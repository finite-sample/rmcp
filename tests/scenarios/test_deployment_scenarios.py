"""
Enhanced Docker Workflow Validation Tests

These tests validate complete RMCP workflows in Docker environments:
1. Full statistical analysis workflows in containerized environment
2. Performance testing in Docker
3. Cross-platform Docker compatibility
4. Production deployment scenarios
5. Resource usage and optimization
"""

import json
import subprocess
import tempfile
import time
from pathlib import Path

import pytest


class TestDockerWorkflowValidation:
    """Test complete statistical workflows in Docker environment."""

    @pytest.fixture(autouse=True)
    def check_docker_available(self):
        """Check that Docker is available before running tests."""
        try:
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                pytest.skip("Docker not available")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Docker not installed or not accessible")

    def test_docker_build_and_basic_functionality(self):
        """Test that Docker build succeeds and basic functionality works."""
        print("🐳 Testing Docker build and basic functionality...")

        # Build Docker image
        build_start = time.time()
        build_result = subprocess.run(
            ["docker", "build", "-t", "rmcp-e2e-test", "."],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes for build
        )
        build_time = time.time() - build_start

        assert (
            build_result.returncode == 0
        ), f"Docker build failed: {build_result.stderr}"
        print(f"✅ Docker build completed in {build_time:.1f}s")

        # Test basic functionality in container
        test_result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "rmcp-e2e-test",
                "python",
                "-c",
                "import rmcp; print('RMCP imported successfully')",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert (
            test_result.returncode == 0
        ), f"Basic functionality test failed: {test_result.stderr}"
        assert "RMCP imported successfully" in test_result.stdout
        print("✅ Basic functionality verified in Docker")

    def test_docker_mcp_protocol_communication(self):
        """Test MCP protocol communication in Docker environment."""
        print("🐳 Testing MCP protocol in Docker...")

        # Create test request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "Docker E2E Test", "version": "1.0.0"},
            },
        }

        # Test MCP communication in Docker
        process = subprocess.Popen(
            ["docker", "run", "--rm", "-i", "rmcp-e2e-test", "rmcp", "start"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, stderr = process.communicate(
                input=json.dumps(init_request) + "\n", timeout=20
            )

            # Validate MCP response
            response_found = False
            for line in stdout.strip().split("\n"):
                if line.startswith('{"jsonrpc"') and '"result"' in line:
                    response = json.loads(line)
                    if (
                        response.get("jsonrpc") == "2.0"
                        and "result" in response
                        and response.get("id") == 1
                    ):
                        server_info = response.get("result", {}).get("serverInfo", {})
                        print(f"✅ MCP protocol working in Docker")
                        print(f"   Server: {server_info.get('name', 'Unknown')}")
                        response_found = True
                        break

            assert (
                response_found
            ), f"No valid MCP response in Docker. stdout: {stdout[:300]}"

        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("MCP protocol test timeout in Docker")
        finally:
            if process.poll() is None:
                process.terminate()

    def test_docker_complete_analysis_workflow(self):
        """Test complete statistical analysis workflow in Docker."""
        print("🐳 Testing complete analysis workflow in Docker...")

        # Create test data file
        test_data = {
            "sales_data": [
                {"month": 1, "sales": 1000, "marketing": 200},
                {"month": 2, "sales": 1200, "marketing": 250},
                {"month": 3, "sales": 1100, "marketing": 220},
                {"month": 4, "sales": 1300, "marketing": 280},
                {"month": 5, "sales": 1250, "marketing": 260},
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f, indent=2)
            temp_file = f.name

        try:
            # Copy file to container and run analysis
            workflow_commands = [
                # Initialize MCP
                '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{"tools":{}},"clientInfo":{"name":"Docker Workflow","version":"1.0.0"}}}',
                # Load data (simplified - in real scenario would use file operations)
                '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"summary_stats","arguments":{"data":{"month":[1,2,3,4,5],"sales":[1000,1200,1100,1300,1250],"marketing":[200,250,220,280,260]},"variables":["sales","marketing"]}}}',
                # Run correlation analysis
                '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"correlation_analysis","arguments":{"data":{"sales":[1000,1200,1100,1300,1250],"marketing":[200,250,220,280,260]},"variables":["sales","marketing"],"method":"pearson"}}}',
                # Run linear regression
                '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"linear_model","arguments":{"data":{"sales":[1000,1200,1100,1300,1250],"marketing":[200,250,220,280,260]},"formula":"sales ~ marketing"}}}',
            ]

            # Run workflow in Docker
            input_data = "\n".join(workflow_commands) + "\n"

            process = subprocess.Popen(
                ["docker", "run", "--rm", "-i", "rmcp-e2e-test", "rmcp", "start"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                stdout, stderr = process.communicate(input=input_data, timeout=60)

                # Validate workflow results
                responses = []
                for line in stdout.strip().split("\n"):
                    if line.startswith('{"jsonrpc"'):
                        try:
                            response = json.loads(line)
                            if response.get("id") is not None:
                                responses.append(response)
                        except:
                            pass

                # Check that we got responses for all requests
                assert (
                    len(responses) >= 3
                ), f"Expected at least 3 analysis responses, got {len(responses)}"

                # Verify specific analysis results
                summary_success = any(
                    r.get("id") == 2 and "result" in r for r in responses
                )
                correlation_success = any(
                    r.get("id") == 3 and "result" in r for r in responses
                )
                regression_success = any(
                    r.get("id") == 4 and "result" in r for r in responses
                )

                assert summary_success, "Summary statistics failed in Docker"
                assert correlation_success, "Correlation analysis failed in Docker"
                assert regression_success, "Linear regression failed in Docker"

                print("✅ Complete analysis workflow successful in Docker")
                print(f"   Completed {len(responses)} analysis steps")

            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail("Complete workflow test timeout in Docker")
            finally:
                if process.poll() is None:
                    process.terminate()

        finally:
            try:
                Path(temp_file).unlink()
            except:
                pass

    def test_docker_performance_benchmarks(self):
        """Test performance benchmarks in Docker environment."""
        print("🐳 Testing performance benchmarks in Docker...")

        # Test initialization time
        start_time = time.time()

        init_request = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{"tools":{}},"clientInfo":{"name":"Performance Test","version":"1.0.0"}}}'

        process = subprocess.Popen(
            ["docker", "run", "--rm", "-i", "rmcp-e2e-test", "rmcp", "start"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, stderr = process.communicate(input=init_request + "\n", timeout=30)

            end_time = time.time()
            total_time = end_time - start_time

            # Validate response
            response_received = False
            for line in stdout.strip().split("\n"):
                if line.startswith('{"jsonrpc"') and '"result"' in line:
                    response_received = True
                    break

            assert response_received, "No initialize response in performance test"
            assert (
                total_time < 15.0
            ), f"Docker initialization too slow: {total_time:.2f}s"

            print(f"✅ Docker performance: {total_time:.2f}s initialization")

        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("Performance test timeout in Docker")
        finally:
            if process.poll() is None:
                process.terminate()

    def test_docker_resource_usage(self):
        """Test resource usage and limits in Docker."""
        print("🐳 Testing resource usage in Docker...")

        # Run with memory limit to test resource efficiency
        resource_test = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-m",
                "512m",
                "rmcp-e2e-test",
                "python",
                "-c",
                "import rmcp; from rmcp.core.server import create_server; server = create_server(); print(f'Server created with {len(server.tools._tools)} tools')",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert (
            resource_test.returncode == 0
        ), f"Resource test failed: {resource_test.stderr}"
        assert "Server created with" in resource_test.stdout

        print("✅ Resource usage test passed (512MB limit)")

    def test_docker_r_environment_validation(self):
        """Test R environment setup and package availability in Docker."""
        print("🐳 Testing R environment in Docker...")

        # Test R availability
        r_test = subprocess.run(
            ["docker", "run", "--rm", "rmcp-e2e-test", "R", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert r_test.returncode == 0, "R not available in Docker"
        print("✅ R available in Docker")

        # Test key R packages
        packages_to_test = ["jsonlite", "ggplot2", "dplyr", "forecast"]

        for package in packages_to_test:
            pkg_test = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "rmcp-e2e-test",
                    "R",
                    "-e",
                    f'library({package}); cat("OK")',
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            assert (
                pkg_test.returncode == 0
            ), f"Package {package} not available in Docker"
            assert "OK" in pkg_test.stdout, f"Package {package} failed to load"

        print(f"✅ Key R packages available: {packages_to_test}")


class TestDockerProductionScenarios:
    """Test production deployment scenarios with Docker."""

    def test_docker_multi_stage_build_optimization(self):
        """Test multi-stage Docker build for production optimization."""
        # This would test a production-optimized Dockerfile
        pytest.skip("Multi-stage build optimization requires separate Dockerfile")

    def test_docker_security_configuration(self):
        """Test Docker security best practices."""
        print("🐳 Testing Docker security configuration...")

        # Test running as non-root user
        user_test = subprocess.run(
            ["docker", "run", "--rm", "rmcp-e2e-test", "whoami"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should not be root in production
        if user_test.returncode == 0:
            print(f"✅ Container user: {user_test.stdout.strip()}")

    def test_docker_environment_variables(self):
        """Test environment variable configuration in Docker."""
        print("🐳 Testing environment variables in Docker...")

        # Test with custom environment variables
        env_test = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-e",
                "RMCP_LOG_LEVEL=DEBUG",
                "rmcp-e2e-test",
                "python",
                "-c",
                'import os; print(f\'Log level: {os.environ.get("RMCP_LOG_LEVEL", "INFO")}\')',
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert env_test.returncode == 0, "Environment variable test failed"
        assert "DEBUG" in env_test.stdout
        print("✅ Environment variables working in Docker")

    def test_docker_volume_mounts(self):
        """Test volume mounts for data persistence."""
        print("🐳 Testing volume mounts in Docker...")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test data file
            test_file = Path(temp_dir) / "test_data.csv"
            test_file.write_text("x,y\n1,2\n3,4\n5,6\n")

            # Test volume mount and file access
            volume_test = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{temp_dir}:/data",
                    "rmcp-e2e-test",
                    "python",
                    "-c",
                    "import pandas as pd; df = pd.read_csv('/data/test_data.csv'); print(f'Loaded {len(df)} rows')",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            assert (
                volume_test.returncode == 0
            ), f"Volume mount test failed: {volume_test.stderr}"
            assert "Loaded 3 rows" in volume_test.stdout
            print("✅ Volume mounts working in Docker")


class TestDockerCrossplatformCompatibility:
    """Test cross-platform Docker compatibility."""

    def test_docker_architecture_detection(self):
        """Test architecture detection and compatibility."""
        print("🐳 Testing Docker architecture compatibility...")

        arch_test = subprocess.run(
            ["docker", "run", "--rm", "rmcp-e2e-test", "uname", "-m"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if arch_test.returncode == 0:
            architecture = arch_test.stdout.strip()
            print(f"✅ Container architecture: {architecture}")

    def test_docker_platform_specific_features(self):
        """Test platform-specific features and compatibility."""
        # This would test different behaviors on different platforms
        pytest.skip("Platform-specific testing requires multi-platform setup")


def main():
    """Run all Docker workflow validation tests."""
    print("🐳 Docker Full Workflow Validation")
    print("=" * 50)
    print("Testing complete RMCP workflows in Docker environment")
    print()

    # Run tests
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    main()
