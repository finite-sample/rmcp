"""
Local Environment Validation Script

This script validates and auto-configures local development/testing environment:
1. Checks Claude Desktop installation and configuration
2. Validates R environment and packages
3. Tests Docker environment
4. Verifies IDE integrations (VS Code, Cursor)
5. Auto-configures missing components where possible
6. Generates setup recommendations

Usage:
    python validate_local_setup.py [--auto-fix] [--verbose]
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class LocalEnvironmentValidator:
    """Validates and configures local RMCP development environment."""

    def __init__(self, auto_fix: bool = False, verbose: bool = False):
        self.auto_fix = auto_fix
        self.verbose = verbose
        self.system = platform.system()
        self.results = {}
        self.recommendations = []

    def log(self, message: str, level: str = "INFO"):
        """Log message with appropriate formatting."""
        if level == "ERROR":
            print(f"❌ {message}")
        elif level == "WARNING":
            print(f"⚠️  {message}")
        elif level == "SUCCESS":
            print(f"✅ {message}")
        elif level == "INFO" and self.verbose:
            print(f"ℹ️  {message}")

    def run_command(
        self, command: List[str], timeout: int = 30
    ) -> Tuple[bool, str, str]:
        """Run command and return (success, stdout, stderr)."""
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return False, "", str(e)

    def check_python_environment(self) -> bool:
        """Check Python environment and RMCP installation."""
        self.log("Checking Python environment...", "INFO")

        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 10):
            self.log(
                f"Python {python_version.major}.{python_version.minor} found, but 3.10+ required",
                "ERROR",
            )
            self.recommendations.append("Upgrade Python to 3.10 or higher")
            return False

        self.log(
            f"Python {python_version.major}.{python_version.minor}.{python_version.micro} OK",
            "SUCCESS",
        )

        # Check RMCP installation
        try:
            import rmcp

            self.log(f"RMCP {rmcp.__version__} installed", "SUCCESS")
        except ImportError:
            self.log("RMCP not installed", "ERROR")
            if self.auto_fix:
                self.log("Auto-installing RMCP...", "INFO")
                success, _, _ = self.run_command(
                    [sys.executable, "-m", "pip", "install", "-e", "."]
                )
                if success:
                    self.log("RMCP installed successfully", "SUCCESS")
                else:
                    self.log("Failed to auto-install RMCP", "ERROR")
                    self.recommendations.append("Run: pip install -e .")
                    return False
            else:
                self.recommendations.append("Run: pip install -e .")
                return False

        # Check RMCP CLI availability
        success, stdout, _ = self.run_command(["rmcp", "--version"])
        if success:
            self.log(f"RMCP CLI available: {stdout.strip()}", "SUCCESS")
        else:
            self.log("RMCP CLI not in PATH", "WARNING")
            self.recommendations.append("Add RMCP to PATH or use 'python -m rmcp.cli'")

        return True

    def check_r_environment(self) -> bool:
        """Check R installation and required packages."""
        self.log("Checking R environment...", "INFO")

        # Check R installation
        success, stdout, _ = self.run_command(["R", "--version"])
        if not success:
            self.log("R not found in PATH", "ERROR")
            self.recommendations.append("Install R from https://www.r-project.org/")
            return False

        version_line = stdout.split("\n")[0]
        self.log(f"R found: {version_line}", "SUCCESS")

        # Check R version (should be 4.4+)
        if "R version 4." not in version_line:
            self.log("R version may be outdated (recommend 4.4+)", "WARNING")
            self.recommendations.append(
                "Consider upgrading R to 4.4+ for best compatibility"
            )

        # Check critical R packages
        required_packages = [
            "jsonlite",
            "dplyr",
            "ggplot2",
            "forecast",
            "plm",
            "lmtest",
            "sandwich",
            "AER",
            "vars",
            "tseries",
            "nortest",
            "car",
            "rpart",
            "randomForest",
            "gridExtra",
            "tidyr",
            "rlang",
            "readxl",
            "base64enc",
            "reshape2",
            "knitr",
            "broom",
        ]

        missing_packages = []
        for package in required_packages:
            r_script = f'if (!require("{package}", quietly = TRUE)) cat("MISSING") else cat("OK")'
            success, stdout, _ = self.run_command(["R", "-e", r_script], timeout=10)

            if success and "OK" in stdout:
                if self.verbose:
                    self.log(f"R package {package} available", "SUCCESS")
            else:
                missing_packages.append(package)

        if missing_packages:
            self.log(
                f"Missing R packages: {', '.join(missing_packages[:5])}{'...' if len(missing_packages) > 5 else ''}",
                "ERROR",
            )

            if self.auto_fix:
                self.log("Auto-installing missing R packages...", "INFO")
                package_list = '", "'.join(missing_packages)
                r_install_cmd = f'install.packages(c("{package_list}"), repos="https://cran.rstudio.com/")'
                success, _, stderr = self.run_command(
                    ["R", "-e", r_install_cmd], timeout=300
                )

                if success:
                    self.log("R packages installed successfully", "SUCCESS")
                else:
                    self.log(f"Failed to install R packages: {stderr[:100]}", "ERROR")
                    self.recommendations.append(
                        f'Install R packages manually: install.packages(c("{package_list}"))'
                    )
            else:
                self.recommendations.append(
                    f"Install missing R packages: install.packages(c(\"{'", "'.join(missing_packages[:10])}\"))"
                )
                return False
        else:
            self.log("All required R packages available", "SUCCESS")

        return True

    def check_claude_desktop(self) -> bool:
        """Check Claude Desktop installation and configuration."""
        self.log("Checking Claude Desktop configuration...", "INFO")

        # Get config path for platform
        if self.system == "Darwin":
            config_path = (
                Path.home()
                / "Library/Application Support/Claude/claude_desktop_config.json"
            )
        elif self.system == "Windows":
            config_path = (
                Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json"
            )
        else:
            config_path = Path.home() / ".config/claude/claude_desktop_config.json"

        if not config_path.exists():
            self.log(f"Claude Desktop config not found at {config_path}", "WARNING")

            if self.auto_fix:
                self.log("Creating Claude Desktop configuration...", "INFO")
                config_path.parent.mkdir(parents=True, exist_ok=True)

                # Create basic RMCP configuration
                config = {
                    "mcpServers": {
                        "rmcp": {"command": "rmcp", "args": ["start"], "env": {}}
                    }
                }

                # If RMCP is not in PATH, use Python module approach
                success, _, _ = self.run_command(["rmcp", "--version"])
                if not success:
                    config["mcpServers"]["rmcp"] = {
                        "command": "python3",
                        "args": ["-m", "rmcp.cli", "start"],
                        "env": {"PYTHONPATH": str(Path.cwd())},
                    }

                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)

                self.log(f"Created Claude Desktop config at {config_path}", "SUCCESS")
            else:
                self.recommendations.append(
                    f"Create Claude Desktop config at {config_path}"
                )
                self.recommendations.append(
                    "See: https://modelcontextprotocol.io/clients#claude-desktop"
                )
                return False

        # Validate existing configuration
        try:
            with open(config_path) as f:
                config = json.load(f)

            if "mcpServers" not in config:
                self.log("Claude Desktop config missing mcpServers section", "ERROR")
                self.recommendations.append(
                    "Add mcpServers section to Claude Desktop config"
                )
                return False

            # Check for RMCP configuration
            rmcp_configured = False
            for server_name, server_config in config["mcpServers"].items():
                if "rmcp" in server_name.lower():
                    rmcp_configured = True
                    self.log(
                        f"RMCP configured in Claude Desktop as '{server_name}'",
                        "SUCCESS",
                    )

                    # Validate command is accessible
                    command = server_config.get("command", "")
                    args = server_config.get("args", [])
                    env = server_config.get("env", {})

                    test_env = os.environ.copy()
                    test_env.update(env)

                    success, stdout, _ = self.run_command(
                        [command, "--version"], timeout=10
                    )
                    if success:
                        self.log(
                            f"RMCP command accessible: {stdout.strip()}", "SUCCESS"
                        )
                    else:
                        self.log(f"RMCP command not accessible: {command}", "WARNING")
                        self.recommendations.append(
                            f"Check RMCP command path in Claude Desktop config: {command}"
                        )

                    break

            if not rmcp_configured:
                self.log("RMCP not configured in Claude Desktop", "ERROR")
                self.recommendations.append(
                    "Add RMCP server to Claude Desktop mcpServers configuration"
                )
                return False

        except json.JSONDecodeError:
            self.log("Claude Desktop config is not valid JSON", "ERROR")
            self.recommendations.append("Fix JSON syntax in Claude Desktop config")
            return False

        return rmcp_configured

    def check_docker_environment(self) -> bool:
        """Check Docker installation and functionality."""
        self.log("Checking Docker environment...", "INFO")

        # Check Docker installation
        success, stdout, _ = self.run_command(["docker", "--version"])
        if not success:
            self.log("Docker not found", "WARNING")
            self.recommendations.append("Install Docker from https://www.docker.com/")
            return False

        self.log(f"Docker found: {stdout.strip()}", "SUCCESS")

        # Check Docker daemon
        success, _, _ = self.run_command(["docker", "ps"], timeout=10)
        if not success:
            self.log("Docker daemon not running", "WARNING")
            self.recommendations.append("Start Docker daemon")
            return False

        self.log("Docker daemon running", "SUCCESS")

        # Test Docker build capability (quick test)
        test_dockerfile = "FROM alpine:latest\\nRUN echo 'Docker test'"
        temp_dir = Path.cwd() / "temp_docker_test"

        try:
            temp_dir.mkdir(exist_ok=True)
            (temp_dir / "Dockerfile").write_text(test_dockerfile.replace("\\n", "\n"))

            success, _, stderr = self.run_command(
                ["docker", "build", "-t", "rmcp-docker-test", str(temp_dir)], timeout=60
            )

            if success:
                self.log("Docker build capability verified", "SUCCESS")
                # Clean up test image
                self.run_command(["docker", "rmi", "rmcp-docker-test"])
            else:
                self.log(f"Docker build test failed: {stderr[:100]}", "WARNING")
                self.recommendations.append(
                    "Check Docker build permissions and disk space"
                )
                return False

        finally:
            # Clean up
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

        return True

    def check_ide_integrations(self) -> bool:
        """Check IDE installations and MCP support."""
        self.log("Checking IDE integrations...", "INFO")

        ides_found = []

        # Check VS Code
        vs_code_commands = [
            "code",
            "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
        ]
        for cmd in vs_code_commands:
            success, stdout, _ = self.run_command([cmd, "--version"])
            if success:
                version = stdout.split("\n")[0] if stdout else "Unknown"
                self.log(f"VS Code found: {version}", "SUCCESS")
                ides_found.append("VS Code")

                # Check Continue extension
                success, stdout, _ = self.run_command([cmd, "--list-extensions"])
                if success and "continue.continue" in stdout.lower():
                    self.log("Continue extension installed", "SUCCESS")
                else:
                    self.log("Continue extension not found", "WARNING")
                    self.recommendations.append(
                        "Install Continue extension: code --install-extension Continue.continue"
                    )
                break

        # Check Cursor
        cursor_commands = [
            "cursor",
            "/Applications/Cursor.app/Contents/Resources/app/bin/cursor",
        ]
        for cmd in cursor_commands:
            success, stdout, _ = self.run_command([cmd, "--version"])
            if success:
                version = stdout.split("\n")[0] if stdout else "Unknown"
                self.log(f"Cursor found: {version}", "SUCCESS")
                ides_found.append("Cursor")
                break

        if not ides_found:
            self.log("No supported IDEs found", "WARNING")
            self.recommendations.append("Install VS Code or Cursor for IDE integration")
            self.recommendations.append("VS Code: https://code.visualstudio.com/")
            self.recommendations.append("Cursor: https://cursor.sh/")
            return False

        return True

    def test_end_to_end_functionality(self) -> bool:
        """Test complete RMCP functionality end-to-end."""
        self.log("Testing end-to-end functionality...", "INFO")

        # Test MCP server startup and basic communication
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "Local Validation", "version": "1.0.0"},
            },
        }

        # Try different RMCP command approaches
        commands_to_try = [
            ["rmcp", "start"],
            ["python3", "-m", "rmcp.cli", "start"],
            [sys.executable, "-m", "rmcp.cli", "start"],
        ]

        for command in commands_to_try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                stdout, stderr = process.communicate(
                    input=json.dumps(init_request) + "\n", timeout=20
                )

                # Look for valid MCP response
                for line in stdout.strip().split("\n"):
                    if line.startswith('{"jsonrpc"') and '"result"' in line:
                        try:
                            response = json.loads(line)
                            if (
                                response.get("jsonrpc") == "2.0"
                                and "result" in response
                                and response.get("id") == 1
                            ):
                                server_info = response.get("result", {}).get(
                                    "serverInfo", {}
                                )
                                self.log(
                                    "End-to-end functionality test passed", "SUCCESS"
                                )
                                self.log(
                                    f"Server: {server_info.get('name', 'Unknown')} v{server_info.get('version', 'Unknown')}",
                                    "INFO",
                                )
                                return True
                        except:
                            continue

            except subprocess.TimeoutExpired:
                process.kill()
                continue
            finally:
                if process.poll() is None:
                    process.terminate()

        self.log("End-to-end functionality test failed", "ERROR")
        self.recommendations.append("RMCP server not responding to MCP requests")
        self.recommendations.append("Check R installation and RMCP configuration")
        return False

    def generate_setup_report(self) -> str:
        """Generate comprehensive setup report."""
        report = ["", "🔍 RMCP Local Environment Validation Report", "=" * 50]

        # System information
        report.append(f"System: {platform.system()} {platform.release()}")
        report.append(f"Python: {sys.version}")
        report.append("")

        # Results summary
        passed_checks = sum(1 for result in self.results.values() if result)
        total_checks = len(self.results)

        report.append("📊 Validation Results:")
        for check_name, passed in self.results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            report.append(f"  {status}: {check_name}")

        report.append(f"\nOverall: {passed_checks}/{total_checks} checks passed")

        # Recommendations
        if self.recommendations:
            report.append("\n💡 Recommendations:")
            for i, rec in enumerate(self.recommendations, 1):
                report.append(f"  {i}. {rec}")

        # Next steps
        if passed_checks == total_checks:
            report.append(
                "\n🎉 All checks passed! Your local environment is ready for RMCP development."
            )
            report.append("\nNext steps:")
            report.append(
                "  1. Try running: pytest tests/e2e/test_real_claude_desktop_e2e.py"
            )
            report.append("  2. Open Claude Desktop and test RMCP integration")
            report.append(
                "  3. Run Docker tests: pytest tests/e2e/test_docker_full_workflow.py"
            )
        else:
            report.append("\n⚠️  Some issues found. Address the recommendations above.")
            report.append("Run this script with --auto-fix to attempt automatic fixes.")

        return "\n".join(report)

    def run_validation(self) -> bool:
        """Run complete validation suite."""
        print("🔍 RMCP Local Environment Validation")
        print("=" * 50)

        checks = [
            ("Python Environment", self.check_python_environment),
            ("R Environment", self.check_r_environment),
            ("Claude Desktop", self.check_claude_desktop),
            ("Docker Environment", self.check_docker_environment),
            ("IDE Integrations", self.check_ide_integrations),
            ("End-to-End Functionality", self.test_end_to_end_functionality),
        ]

        for check_name, check_func in checks:
            print(f"\n📋 {check_name}:")
            print("-" * 30)
            try:
                result = check_func()
                self.results[check_name] = result
            except Exception as e:
                self.log(f"Check failed with exception: {e}", "ERROR")
                self.results[check_name] = False

        # Generate and display report
        report = self.generate_setup_report()
        print(report)

        return all(self.results.values())


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate RMCP local environment")
    parser.add_argument(
        "--auto-fix", action="store_true", help="Attempt to automatically fix issues"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    validator = LocalEnvironmentValidator(auto_fix=args.auto_fix, verbose=args.verbose)
    success = validator.run_validation()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
