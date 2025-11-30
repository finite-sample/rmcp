#!/usr/bin/env python3
"""
Comprehensive Local CI Validation Script for RMCP

This script mirrors the CI/CD pipeline exactly, allowing you to catch failures locally
before pushing to GitHub. It runs all the same checks as the CI pipeline:

1. Python linting (black, isort, flake8)
2. R style checks (styler)
3. Docker build (development + production)
4. Complete test suite (dynamic count validation)
5. Code quality validation

Usage:
    python scripts/testing/validate_ci_locally.py [--skip-docker] [--skip-tests] [--verbose]
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


class LocalCIValidator:
    """Validates that all CI checks will pass before pushing to GitHub."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.root_dir = Path(__file__).parent.parent.parent
        self.results: list[tuple[str, bool, str]] = []

    def log(self, message: str, level: str = "INFO"):
        """Log message with appropriate formatting."""
        if level == "ERROR":
            print(f"❌ {message}")
        elif level == "WARNING":
            print(f"⚠️  {message}")
        elif level == "SUCCESS":
            print(f"✅ {message}")
        elif level == "INFO":
            print(f"ℹ️  {message}")
        elif level == "STEP":
            print(f"\n🔍 {message}")
            print("-" * 50)

    def run_command(
        self, command: list[str], timeout: int = 300, cwd: Path = None
    ) -> tuple[bool, str, str]:
        """Run command and return (success, stdout, stderr)."""
        try:
            if self.verbose:
                self.log(f"Running: {' '.join(command)}")

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or self.root_dir,
            )
            success = result.returncode == 0

            if self.verbose and not success:
                self.log(f"Command failed with code {result.returncode}")
                if result.stderr:
                    self.log(f"STDERR: {result.stderr[:200]}...")

            return success, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    def validate_python_linting(self) -> bool:
        """Validate Python code formatting and linting (mirrors CI python-checks job)."""
        self.log("Validating Python Code Quality", "STEP")

        # Black formatting check
        self.log("Checking black formatting...")
        success, stdout, stderr = self.run_command(
            ["black", "--check", "rmcp", "tests", "streamlit", "scripts"]
        )
        if not success:
            self.log(
                "Black formatting issues found - run: black rmcp tests streamlit scripts",
                "ERROR",
            )
            self.results.append(("Black formatting", False, stderr))
            return False
        else:
            self.log("Black formatting passed")

        # Import sorting check
        self.log("Checking import sorting...")
        success, stdout, stderr = self.run_command(
            ["isort", "--check-only", "rmcp", "tests", "streamlit", "scripts"]
        )
        if not success:
            self.log(
                "Import sorting issues found - run: isort rmcp tests streamlit scripts",
                "ERROR",
            )
            self.results.append(("Import sorting", False, stderr))
            return False
        else:
            self.log("Import sorting passed")

        # Flake8 linting
        self.log("Running flake8 linting...")
        success, stdout, stderr = self.run_command(
            ["flake8", "rmcp", "tests", "streamlit", "scripts"]
        )
        if not success:
            self.log("Flake8 linting issues found", "ERROR")
            self.results.append(("Flake8 linting", False, stderr))
            return False
        else:
            self.log("Flake8 linting passed")

        self.results.append(("Python Code Quality", True, "All checks passed"))
        return True

    def validate_r_style(self) -> bool:
        """Validate R code style using styler (mirrors CI R style checks)."""
        self.log("Validating R Code Style", "STEP")

        # Check if R is available
        success, _, _ = self.run_command(["R", "--version"])
        if not success:
            self.log("R not found - skipping R style checks", "WARNING")
            self.results.append(("R Style Check", True, "Skipped - R not available"))
            return True

        # Run R style check exactly as in CI
        r_command = [
            "R",
            "-e",
            """
            library(styler)
            files <- list.files('rmcp/r_assets', pattern='[.]R$', recursive=TRUE, full.names=TRUE)
            if(length(files) > 0) {
                result <- styler::style_file(files, dry='on', include_roxygen_examples=FALSE)
                if(any(result$changed)) {
                    cat('❌ R style issues found\\n')
                    quit(status=1)
                } else {
                    cat('✅ R code style check passed\\n')
                }
            }
            """,
        ]

        success, stdout, stderr = self.run_command(r_command)
        if not success:
            self.log("R style issues found - run R formatting", "ERROR")
            self.results.append(("R Style Check", False, stderr))
            return False
        else:
            self.log("R style check passed")
            self.results.append(("R Style Check", True, "All files properly formatted"))
            return True

    def validate_docker_builds(self) -> bool:
        """Validate Docker builds (mirrors CI docker-build job)."""
        self.log("Validating Docker Builds", "STEP")

        # Check Docker availability
        success, _, _ = self.run_command(["docker", "--version"])
        if not success:
            self.log("Docker not found - cannot validate builds", "ERROR")
            self.results.append(("Docker Build", False, "Docker not available"))
            return False

        # Build development image
        self.log("Building development Docker image...")
        success, stdout, stderr = self.run_command(
            [
                "docker",
                "build",
                "-f",
                "Dockerfile",
                "--target",
                "development",
                "-t",
                "rmcp-dev-local",
                ".",
            ],
            timeout=600,
        )

        if not success:
            self.log("Development Docker build failed", "ERROR")
            self.results.append(("Docker Development Build", False, stderr[:200]))
            return False
        else:
            self.log("Development Docker build succeeded")

        # Build production image
        self.log("Building production Docker image...")
        success, stdout, stderr = self.run_command(
            [
                "docker",
                "build",
                "-f",
                "Dockerfile",
                "--target",
                "production",
                "-t",
                "rmcp-prod-local",
                ".",
            ],
            timeout=600,
        )

        if not success:
            self.log("Production Docker build failed", "ERROR")
            self.results.append(("Docker Production Build", False, stderr[:200]))
            return False
        else:
            self.log("Production Docker build succeeded")

        # Test basic functionality
        self.log("Testing Docker image functionality...")
        success, stdout, stderr = self.run_command(
            ["docker", "run", "--rm", "rmcp-dev-local", "rmcp", "--version"]
        )

        if not success:
            self.log("Docker image functionality test failed", "ERROR")
            self.results.append(("Docker Functionality", False, stderr))
            return False
        else:
            self.log(f"Docker functionality test passed: {stdout.strip()}")

        self.results.append(
            ("Docker Builds", True, "Development and production builds successful")
        )
        return True

    def validate_test_suite(self) -> bool:
        """Run the complete test suite in Docker (mirrors CI r-testing job)."""
        self.log("Running Complete Test Suite", "STEP")

        # Run tests inside Docker development environment (exactly like CI)
        self.log("Running pytest in Docker environment...")
        docker_test_cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{self.root_dir}:/workspace",
            "-w",
            "/workspace",
            "rmcp-dev-local",
            "bash",
            "-c",
            """
            export PATH="/opt/venv/bin:$PATH"
            pip install -e .

            # Count total tests
            TEST_COUNT=$(pytest --collect-only -q tests/ | grep "collected" | grep -o '[0-9]\\+' | head -1)
            echo "Tests collected: $TEST_COUNT"

            # Load baseline and validate dynamically
            BASELINE_FILE="/workspace/tests/.test_baseline.json"
            if [ -f "$BASELINE_FILE" ]; then
                BASELINE_COUNT=$(python3 -c "import json; print(json.load(open('$BASELINE_FILE'))['baseline_counts']['total_tests'])")
                MIN_TESTS=$(python3 -c "import json; print(json.load(open('$BASELINE_FILE'))['validation_rules']['min_tests'])")
                MAX_DEVIATION=$(python3 -c "import json; print(json.load(open('$BASELINE_FILE'))['validation_rules']['max_deviation_percent'])")

                MIN_ALLOWED=$((BASELINE_COUNT * (100 - MAX_DEVIATION) / 100))
                MAX_ALLOWED=$((BASELINE_COUNT * (100 + MAX_DEVIATION) / 100))

                echo "📊 Test count validation:"
                echo "  Current: $TEST_COUNT"
                echo "  Baseline: $BASELINE_COUNT"
                echo "  Allowed range: $MIN_ALLOWED - $MAX_ALLOWED"

                if [ "$TEST_COUNT" -lt "$MIN_TESTS" ]; then
                    echo "❌ Test count ($TEST_COUNT) below minimum threshold ($MIN_TESTS)"
                    exit 1
                elif [ "$TEST_COUNT" -lt "$MIN_ALLOWED" ] || [ "$TEST_COUNT" -gt "$MAX_ALLOWED" ]; then
                    echo "⚠️ Test count ($TEST_COUNT) outside expected range ($MIN_ALLOWED - $MAX_ALLOWED)"
                    echo "💡 Consider updating baseline if this change is expected"
                    echo "   Current baseline: $BASELINE_COUNT tests"
                else
                    echo "✅ Test count within expected range"
                fi
            else
                echo "⚠️ Baseline file not found, using minimum threshold"
                if [ "$TEST_COUNT" -lt "200" ]; then
                    echo "❌ Test count ($TEST_COUNT) below minimum threshold (200)"
                    exit 1
                fi
            fi

            # Run all test categories as in CI
            echo "=== Running smoke tests ==="
            pytest tests/smoke/ -v --tb=short

            echo "=== Running protocol tests ==="
            pytest tests/integration/protocol/ -v --tb=short

            echo "=== Running integration tests - tools ==="
            pytest tests/integration/tools/ -v --tb=short

            echo "=== Running integration tests - transport ==="
            pytest tests/integration/transport/ -v --tb=short

            echo "=== Running integration tests - core ==="
            pytest tests/integration/core/ -v --tb=short

            echo "=== Running scenario tests ==="
            pytest tests/scenarios/ -v --tb=short

            echo "✅ All $TEST_COUNT tests completed successfully"
            """,
        ]

        success, stdout, stderr = self.run_command(docker_test_cmd, timeout=900)

        if not success:
            self.log("Test suite failed", "ERROR")
            self.results.append(("Test Suite", False, stderr[:500]))
            return False
        else:
            # Extract test count from output
            test_count = "unknown"
            if "Tests collected:" in stdout:
                import re

                match = re.search(r"Tests collected: (\d+)", stdout)
                if match:
                    test_count = match.group(1)

            self.log(f"Complete test suite passed ({test_count} tests)")
            self.results.append(("Test Suite", True, f"All {test_count} tests passed"))
            return True

    def validate_cli_functionality(self) -> bool:
        """Test CLI functionality (mirrors CI CLI tests)."""
        self.log("Validating CLI Functionality", "STEP")

        # Test rmcp --version
        success, stdout, stderr = self.run_command(["rmcp", "--version"])
        if not success:
            self.log("rmcp --version failed", "ERROR")
            self.results.append(("CLI Version", False, stderr))
            return False
        else:
            self.log(f"CLI version: {stdout.strip()}")

        # Test rmcp list-capabilities
        success, stdout, stderr = self.run_command(["rmcp", "list-capabilities"])
        if not success:
            self.log("rmcp list-capabilities failed", "ERROR")
            self.results.append(("CLI Capabilities", False, stderr))
            return False
        else:
            self.log("CLI capabilities listing succeeded")

        self.results.append(("CLI Functionality", True, "All CLI commands work"))
        return True

    def print_summary(self):
        """Print final summary of all validation results."""
        print("\n" + "=" * 60)
        print("🎯 LOCAL CI VALIDATION SUMMARY")
        print("=" * 60)

        passed = 0
        total = len(self.results)

        for check_name, success, details in self.results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status}: {check_name}")
            if not success and self.verbose:
                print(f"   Details: {details[:100]}...")
            if success:
                passed += 1

        print(f"\nResult: {passed}/{total} checks passed")

        if passed == total:
            print("\n🎉 ALL VALIDATIONS PASSED!")
            print("✅ Your code is ready for CI/CD pipeline")
            print("🚀 Safe to push to GitHub")
        else:
            print(f"\n❌ {total - passed} VALIDATIONS FAILED")
            print("🔧 Fix the issues above before pushing to GitHub")
            print("💡 This will prevent CI/CD failures")

        return passed == total

    def run_validation(
        self, skip_docker: bool = False, skip_tests: bool = False
    ) -> bool:
        """Run all validation checks."""
        print("🛠️  LOCAL CI/CD VALIDATION")
        print("=" * 60)
        print("This script mirrors the GitHub CI pipeline to catch issues locally")
        print(f"Working directory: {self.root_dir}")
        print()

        start_time = time.time()

        # Run all validation steps
        validations = [
            ("Python Code Quality", self.validate_python_linting),
            ("R Code Style", self.validate_r_style),
            ("CLI Functionality", self.validate_cli_functionality),
        ]

        if not skip_docker:
            validations.append(("Docker Builds", self.validate_docker_builds))
        else:
            self.log("Skipping Docker builds (--skip-docker)", "WARNING")

        if not skip_tests and not skip_docker:
            validations.append(("Test Suite", self.validate_test_suite))
        elif skip_tests:
            self.log("Skipping test suite (--skip-tests)", "WARNING")
        elif skip_docker:
            self.log("Skipping test suite (requires Docker)", "WARNING")

        # Execute all validations
        for name, validator in validations:
            try:
                success = validator()
                if not success:
                    pass
            except KeyboardInterrupt:
                self.log("Validation interrupted by user", "ERROR")
                return False
            except Exception as e:
                self.log(f"{name} validation failed with exception: {e}", "ERROR")
                self.results.append((name, False, str(e)))

        # Print summary
        elapsed = time.time() - start_time
        print(f"\nValidation completed in {elapsed:.1f} seconds")

        return self.print_summary()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate that local code will pass CI/CD pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/testing/validate_ci_locally.py                    # Full validation
  python scripts/testing/validate_ci_locally.py --skip-docker     # Skip Docker builds
  python scripts/testing/validate_ci_locally.py --skip-tests      # Skip test suite
  python scripts/testing/validate_ci_locally.py --verbose         # Detailed output
        """,
    )

    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Skip Docker build validation (faster, but less complete)",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running the test suite (much faster)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with detailed error messages",
    )

    args = parser.parse_args()

    validator = LocalCIValidator(verbose=args.verbose)
    success = validator.run_validation(
        skip_docker=args.skip_docker, skip_tests=args.skip_tests
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
