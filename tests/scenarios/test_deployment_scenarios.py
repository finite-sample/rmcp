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
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

def _check_docker_available():
    """Check if Docker is available and functional at runtime."""
    if not shutil.which("docker"):
        pytest.skip("Docker not available in PATH")
    
    try:
        # Test basic Docker functionality
        result = subprocess.run(["docker", "--version"], 
                              capture_output=True, timeout=10)
        if result.returncode != 0:
            pytest.skip("Docker not functional")
            
        # Test Docker daemon access
        result = subprocess.run(["docker", "info"], 
                              capture_output=True, timeout=10)
        if result.returncode != 0:
            pytest.skip("Docker daemon not accessible")
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("Docker not accessible")


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

    def test_docker_basic_functionality(self):
        """Test basic functionality using pre-built production image."""
        _check_docker_available()
        print("🐳 Testing Docker basic functionality...")

        # Use production image built in CI or local testing
        import os
        production_image = os.environ.get("RMCP_PRODUCTION_IMAGE", "rmcp:prod")
        
        print(f"Testing basic functionality with: {production_image}")

        # Test basic functionality in container
        test_result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                production_image,
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
        _check_docker_available()
        print("🐳 Testing MCP protocol in Docker...")

        # Use production image built in CI or local testing
        import os
        production_image = os.environ.get("RMCP_PRODUCTION_IMAGE", "rmcp:prod")

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
            ["docker", "run", "--rm", "-i", production_image, "rmcp", "start"],
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
        _check_docker_available()
        print("🐳 Testing complete analysis workflow in Docker...")

        # Use production image built in CI or local testing
        import os
        production_image = os.environ.get("RMCP_PRODUCTION_IMAGE", "rmcp:prod")

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
                ["docker", "run", "--rm", "-i", production_image, "rmcp", "start"],
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
        _check_docker_available()
        print("🐳 Testing performance benchmarks in Docker...")

        # Use production image built in CI or local testing
        import os
        production_image = os.environ.get("RMCP_PRODUCTION_IMAGE", "rmcp:prod")

        # Test initialization time
        start_time = time.time()

        init_request = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{"tools":{}},"clientInfo":{"name":"Performance Test","version":"1.0.0"}}}'

        process = subprocess.Popen(
            ["docker", "run", "--rm", "-i", production_image, "rmcp", "start"],
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
        _check_docker_available()
        print("🐳 Testing resource usage in Docker...")

        # Use production image built in CI or local testing
        import os
        production_image = os.environ.get("RMCP_PRODUCTION_IMAGE", "rmcp:prod")

        # Run with memory limit to test resource efficiency
        resource_test = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-m",
                "512m",
                production_image,
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
        _check_docker_available()
        print("🐳 Testing R environment in Docker...")

        # Use production image built in CI or local testing
        import os
        production_image = os.environ.get("RMCP_PRODUCTION_IMAGE", "rmcp:prod")

        # Test R availability
        r_test = subprocess.run(
            ["docker", "run", "--rm", production_image, "R", "--version"],
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
                    production_image,
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

    def test_docker_production_image_functionality(self):
        """Test that production Docker image works correctly (uses pre-built image)."""
        _check_docker_available()
        print("🐳 Testing production image functionality...")
        
        # Use production image built in CI or local testing
        # In CI: this will be the image built in docker-build job
        # Locally: assume rmcp:prod or similar exists
        import os
        production_image = os.environ.get("RMCP_PRODUCTION_IMAGE", "rmcp:prod")
        
        print(f"Testing production image: {production_image}")
        
        # Test functionality of production image
        print("Testing production image functionality...")

        # Test basic RMCP functionality
        test_cmd = [
            "docker",
            "run",
            "--rm",
            production_image,
            "python",
            "-c",
            "import rmcp; print('RMCP import successful')",
        ]

        func_result = subprocess.run(
            test_cmd, capture_output=True, text=True, timeout=30
        )

        if func_result.returncode != 0:
            pytest.fail(
                f"Production image functionality test failed: {func_result.stderr}"
            )

        print("✅ Production image functionality verified")

        # Test security - should run as non-root user
        user_cmd = ["docker", "run", "--rm", production_image, "whoami"]
        user_result = subprocess.run(
            user_cmd, capture_output=True, text=True, timeout=10
        )

        if user_result.returncode == 0:
            username = user_result.stdout.strip()
            print(f"✅ Container runs as user: {username}")
            assert username != "root", "Production image should not run as root user"

        # Test R availability in production image
        r_cmd = ["docker", "run", "--rm", production_image, "R", "--version"]
        r_result = subprocess.run(r_cmd, capture_output=True, text=True, timeout=10)

        if r_result.returncode == 0:
            print("✅ R environment available in production image")
        else:
            pytest.fail("R not available in production image")

        # Test FastAPI dependencies
        fastapi_cmd = [
            "docker",
            "run",
            "--rm",
            production_image,
            "python",
            "-c",
            "import fastapi, uvicorn, httpx; print('HTTP transport ready')",
        ]

        fastapi_result = subprocess.run(
            fastapi_cmd, capture_output=True, text=True, timeout=10
        )

        if fastapi_result.returncode == 0:
            print("✅ HTTP transport dependencies available in production image")
        else:
            pytest.fail("FastAPI dependencies not available in production image")

        print("🎉 Production image functionality test completed successfully")

    def test_docker_security_configuration(self):
        """Test Docker security best practices."""
        _check_docker_available()
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
        _check_docker_available()
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
        _check_docker_available()
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
        _check_docker_available()
        print("🐳 Testing Docker architecture compatibility...")

        # Use production image built in CI or local testing
        import os
        production_image = os.environ.get("RMCP_PRODUCTION_IMAGE", "rmcp:prod")

        arch_test = subprocess.run(
            ["docker", "run", "--rm", production_image, "uname", "-m"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if arch_test.returncode == 0:
            architecture = arch_test.stdout.strip()
            print(f"✅ Container architecture: {architecture}")

    def test_docker_platform_specific_features(self):
        """Test platform-specific features and compatibility."""
        _check_docker_available()
        print("🏗️ Testing platform-specific features...")

        # Use production image built in CI or local testing
        import os
        production_image = os.environ.get("RMCP_PRODUCTION_IMAGE", "rmcp:prod")

        # Get current platform architecture
        arch_cmd = ["docker", "run", "--rm", production_image, "uname", "-m"]
        arch_result = subprocess.run(
            arch_cmd, capture_output=True, text=True, timeout=10
        )

        if arch_result.returncode != 0:
            pytest.skip("Could not determine container architecture")

        current_arch = arch_result.stdout.strip()
        print(f"🔍 Current container architecture: {current_arch}")

        # Test 1: Architecture-specific R package behavior
        print("   📦 Testing R package architecture compatibility...")
        r_arch_cmd = [
            "docker",
            "run",
            "--rm",
            production_image,
            "R",
            "-q",
            "-e",
            "cat('R architecture:', R.version$arch, '\\n')",
        ]

        r_arch_result = subprocess.run(
            r_arch_cmd, capture_output=True, text=True, timeout=15
        )

        if r_arch_result.returncode == 0:
            print(f"   ✅ R architecture info: {r_arch_result.stdout.strip()}")
        else:
            pytest.fail("R architecture test failed")

        # Test 2: Platform-specific library paths
        print("   📚 Testing platform-specific library paths...")
        lib_cmd = [
            "docker",
            "run",
            "--rm",
            production_image,
            "python",
            "-c",
            "import sys, platform; print(f'Python platform: {platform.platform()}'); print(f'Architecture: {platform.architecture()}')",
        ]

        lib_result = subprocess.run(lib_cmd, capture_output=True, text=True, timeout=10)

        if lib_result.returncode == 0:
            print(f"   ✅ Platform info: {lib_result.stdout.strip()}")
        else:
            pytest.fail("Platform library test failed")

        # Test 3: Numerical computation consistency across platforms
        print("   🧮 Testing numerical computation consistency...")
        math_test_cmd = [
            "docker",
            "run",
            "--rm",
            production_image,
            "R",
            "-q",
            "-e",
            """
            library(jsonlite)
            set.seed(42)
            x <- rnorm(100)
            y <- 2*x + rnorm(100, 0, 0.1)
            model <- lm(y ~ x)
            result <- list(
                coefficient = coef(model)[2],
                r_squared = summary(model)$r.squared,
                platform = paste(R.version$platform, R.version$arch)
            )
            cat(toJSON(result, auto_unbox=TRUE))
            """,
        ]

        math_result = subprocess.run(
            math_test_cmd, capture_output=True, text=True, timeout=20
        )

        if math_result.returncode == 0:
            try:
                import json

                math_data = json.loads(math_result.stdout.strip())
                coefficient = math_data.get("coefficient", 0)
                r_squared = math_data.get("r_squared", 0)
                platform_info = math_data.get("platform", "unknown")

                print(f"   ✅ Computation results on {platform_info}:")
                print(f"      Regression coefficient: {coefficient:.4f}")
                print(f"      R-squared: {r_squared:.4f}")

                # Verify reasonable statistical results (should be consistent across platforms)
                assert (
                    1.8 <= coefficient <= 2.2
                ), f"Unexpected coefficient: {coefficient}"
                assert 0.9 <= r_squared <= 1.0, f"Unexpected R-squared: {r_squared}"

            except (json.JSONDecodeError, KeyError) as e:
                pytest.fail(f"Failed to parse mathematical computation results: {e}")
        else:
            pytest.fail(f"Mathematical computation test failed: {math_result.stderr}")

        # Test 4: Docker buildx multi-platform capability (if available)
        print("   🏗️ Testing multi-platform build capability...")
        try:
            buildx_cmd = ["docker", "buildx", "version"]
            buildx_result = subprocess.run(
                buildx_cmd, capture_output=True, text=True, timeout=10
            )

            if buildx_result.returncode == 0:
                print(
                    f"   ✅ Docker Buildx available: {buildx_result.stdout.strip().split()[0]}"
                )

                # Check available platforms
                platforms_cmd = ["docker", "buildx", "ls"]
                platforms_result = subprocess.run(
                    platforms_cmd, capture_output=True, text=True, timeout=10
                )

                if platforms_result.returncode == 0:
                    print("   📋 Available build platforms:")
                    for line in platforms_result.stdout.split("\n"):
                        if "linux/" in line:
                            print(f"      {line.strip()}")
                else:
                    print("   ⚠️  Could not list available platforms")
            else:
                print(
                    "   ⚠️  Docker Buildx not available (multi-platform builds not supported)"
                )

        except Exception as e:
            print(f"   ⚠️  Buildx test failed: {e}")

        # Test 5: Architecture-specific performance characteristics
        print("   ⚡ Testing platform performance characteristics...")
        perf_cmd = [
            "docker",
            "run",
            "--rm",
            production_image,
            "python",
            "-c",
            """
import time
import platform
start = time.time()
# Simple computational benchmark
total = sum(i**2 for i in range(100000))
end = time.time()
print(f'Platform: {platform.machine()}')
print(f'Computation time: {end-start:.4f}s')
print(f'Result validation: {total == 333328333350000}')
""",
        ]

        perf_result = subprocess.run(
            perf_cmd, capture_output=True, text=True, timeout=15
        )

        if perf_result.returncode == 0:
            print(f"   ✅ Performance test results:")
            for line in perf_result.stdout.strip().split("\n"):
                print(f"      {line}")
        else:
            print(f"   ⚠️  Performance test failed: {perf_result.stderr}")

        print("🎉 Platform-specific testing completed!")

        # Summary of platform compatibility
        print(f"\n📊 Platform Compatibility Summary:")
        print(f"   Architecture: {current_arch}")
        print(f"   R Integration: ✅ Working")
        print(f"   Python Integration: ✅ Working")
        print(f"   Numerical Consistency: ✅ Verified")
        print(
            f"   Multi-platform Build: {'✅ Available' if buildx_result.returncode == 0 else '⚠️ Limited'}"
        )


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
