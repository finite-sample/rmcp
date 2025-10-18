"""
RMCP Automated Setup Scripts

Provides automated setup for new users and development environments:
1. Auto-configure Claude Desktop
2. Install and configure VS Code + Continue extension
3. Set up Docker development environment
4. Install R packages
5. Create sample configurations

Usage:
    python setup_automation.py [--claude-desktop] [--vscode] [--docker] [--r-packages] [--all]
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class RMCPSetupAutomation:
    """Automated setup for RMCP development environment."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.system = platform.system()

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

    def run_command(
        self, command: List[str], timeout: int = 30
    ) -> tuple[bool, str, str]:
        """Run command and return (success, stdout, stderr)."""
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return False, "", str(e)

    def setup_claude_desktop(self) -> bool:
        """Auto-configure Claude Desktop for RMCP."""
        self.log("Setting up Claude Desktop configuration...", "INFO")

        # Get platform-specific config path
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

        # Create directory if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine best RMCP command approach
        rmcp_config = None

        # Test if rmcp command is in PATH
        success, _, _ = self.run_command(["rmcp", "--version"])
        if success:
            rmcp_config = {"command": "rmcp", "args": ["start"], "env": {}}
            self.log("Using 'rmcp' command from PATH", "INFO")
        else:
            # Fall back to Python module approach
            rmcp_config = {
                "command": "python3",
                "args": ["-m", "rmcp.cli", "start"],
                "env": {"PYTHONPATH": str(Path.cwd())},
            }
            self.log("Using Python module approach for RMCP", "INFO")

        # Create or update configuration
        config = {"mcpServers": {"rmcp": rmcp_config}}

        # If config already exists, merge with existing
        if config_path.exists():
            try:
                with open(config_path) as f:
                    existing_config = json.load(f)

                if "mcpServers" in existing_config:
                    existing_config["mcpServers"]["rmcp"] = rmcp_config
                    config = existing_config
                else:
                    existing_config["mcpServers"] = {"rmcp": rmcp_config}
                    config = existing_config

                self.log("Updated existing Claude Desktop configuration", "INFO")
            except json.JSONDecodeError:
                self.log("Existing config invalid, creating new one", "WARNING")

        # Write configuration
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        self.log(f"Claude Desktop configured at: {config_path}", "SUCCESS")

        # Test the configuration
        command = rmcp_config["command"]
        env = os.environ.copy()
        env.update(rmcp_config.get("env", {}))

        success, stdout, _ = self.run_command([command, "--version"], timeout=10)
        if success:
            self.log(f"Configuration test passed: {stdout.strip()}", "SUCCESS")
            return True
        else:
            self.log("Configuration test failed - command not accessible", "WARNING")
            return False

    def setup_vscode(self) -> bool:
        """Install and configure VS Code with Continue extension."""
        self.log("Setting up VS Code integration...", "INFO")

        # Check if VS Code is installed
        vs_code_commands = [
            "code",
            "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
        ]
        vs_code_cmd = None

        for cmd in vs_code_commands:
            success, _, _ = self.run_command([cmd, "--version"])
            if success:
                vs_code_cmd = cmd
                self.log("VS Code found", "SUCCESS")
                break

        if not vs_code_cmd:
            self.log("VS Code not found", "ERROR")
            self.log("Install VS Code from: https://code.visualstudio.com/", "INFO")
            return False

        # Install Continue extension
        self.log("Installing Continue extension...", "INFO")
        success, stdout, stderr = self.run_command(
            [vs_code_cmd, "--install-extension", "Continue.continue"]
        )

        if success:
            self.log("Continue extension installed successfully", "SUCCESS")
        elif "already installed" in stderr.lower():
            self.log("Continue extension already installed", "SUCCESS")
        else:
            self.log(f"Failed to install Continue extension: {stderr}", "ERROR")
            return False

        # Create sample Continue configuration
        continue_config_path = Path.home() / ".continue/config.json"
        continue_config_path.parent.mkdir(exist_ok=True)

        if not continue_config_path.exists():
            sample_config = {
                "models": [
                    {
                        "title": "Claude 3.5 Sonnet",
                        "provider": "anthropic",
                        "model": "claude-3-5-sonnet-20241022",
                        "apiKey": "your-api-key-here",
                    }
                ],
                "mcpServers": {
                    "rmcp": {
                        "command": "rmcp" if shutil.which("rmcp") else "python3",
                        "args": (
                            ["start"]
                            if shutil.which("rmcp")
                            else ["-m", "rmcp.cli", "start"]
                        ),
                        "env": (
                            {}
                            if shutil.which("rmcp")
                            else {"PYTHONPATH": str(Path.cwd())}
                        ),
                    }
                },
            }

            with open(continue_config_path, "w") as f:
                json.dump(sample_config, f, indent=2)

            self.log(
                f"Sample Continue config created at: {continue_config_path}", "SUCCESS"
            )
            self.log("Edit the config to add your API key", "INFO")

        return True

    def setup_docker_environment(self) -> bool:
        """Set up Docker development environment."""
        self.log("Setting up Docker environment...", "INFO")

        # Check Docker availability
        success, stdout, _ = self.run_command(["docker", "--version"])
        if not success:
            self.log("Docker not found", "ERROR")
            self.log("Install Docker from: https://www.docker.com/", "INFO")
            return False

        self.log(f"Docker found: {stdout.strip()}", "SUCCESS")

        # Check if Dockerfile exists
        dockerfile_path = Path.cwd() / "docker" / "Dockerfile"
        if not dockerfile_path.exists():
            self.log("Dockerfile not found in docker/ directory", "ERROR")
            return False

        # Build development Docker image
        self.log("Building RMCP Docker image...", "INFO")
        success, stdout, stderr = self.run_command(
            [
                "docker",
                "build",
                "-f",
                "docker/Dockerfile",
                "--target",
                "development",
                "-t",
                "rmcp-dev",
                ".",
            ],
            timeout=300,
        )

        if success:
            self.log("RMCP Docker image built successfully", "SUCCESS")

            # Test the image
            self.log("Testing Docker image...", "INFO")
            success, stdout, _ = self.run_command(
                ["docker", "run", "--rm", "rmcp-dev", "rmcp", "--version"], timeout=30
            )

            if success:
                self.log(f"Docker image test passed: {stdout.strip()}", "SUCCESS")
                return True
            else:
                self.log("Docker image test failed", "WARNING")
                return False
        else:
            self.log(f"Docker build failed: {stderr[:200]}", "ERROR")
            return False

    def setup_r_packages(self) -> bool:
        """Install required R packages."""
        self.log("Setting up R packages...", "INFO")

        # Check R availability
        success, stdout, _ = self.run_command(["R", "--version"])
        if not success:
            self.log("R not found", "ERROR")
            self.log("Install R from: https://www.r-project.org/", "INFO")
            return False

        self.log("R found", "SUCCESS")

        # Install required packages
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

        self.log(f"Installing {len(required_packages)} R packages...", "INFO")

        package_list = '", "'.join(required_packages)
        r_install_cmd = (
            f'install.packages(c("{package_list}"), repos="https://cran.rstudio.com/")'
        )

        success, stdout, stderr = self.run_command(
            ["R", "-e", r_install_cmd], timeout=600
        )

        if success:
            self.log("R packages installed successfully", "SUCCESS")
            return True
        else:
            self.log(f"R package installation failed: {stderr[:200]}", "ERROR")
            self.log("You may need to install packages manually in R", "INFO")
            return False

    def create_sample_configurations(self) -> bool:
        """Create sample configuration files."""
        self.log("Creating sample configuration files...", "INFO")

        samples_dir = Path.cwd() / "sample_configs"
        samples_dir.mkdir(exist_ok=True)

        # Claude Desktop config
        claude_config = {
            "mcpServers": {"rmcp": {"command": "rmcp", "args": ["start"], "env": {}}}
        }

        with open(samples_dir / "claude_desktop_config.json", "w") as f:
            json.dump(claude_config, f, indent=2)

        # VS Code settings
        vscode_settings = {
            "continue.mcpServers": {"rmcp": {"command": "rmcp", "args": ["start"]}}
        }

        with open(samples_dir / "vscode_settings.json", "w") as f:
            json.dump(vscode_settings, f, indent=2)

        # Docker compose for development
        docker_compose = """version: '3.8'
services:
  rmcp:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - "./data:/data"
    environment:
      - RMCP_LOG_LEVEL=DEBUG
    command: rmcp serve-http --host 0.0.0.0 --port 8000
"""

        with open(samples_dir / "docker-compose.yml", "w") as f:
            f.write(docker_compose)

        # README for samples
        readme = """# RMCP Sample Configurations

This directory contains sample configuration files for various RMCP integrations:

## Claude Desktop (`claude_desktop_config.json`)
Copy to:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`
- Linux: `~/.config/claude/claude_desktop_config.json`

## VS Code (`vscode_settings.json`)
Add to your VS Code settings.json file.

## Docker Development (`docker-compose.yml`)
Use for local development with Docker:
```bash
docker-compose up
```

## Usage Notes
- Replace `rmcp` command with `python3 -m rmcp.cli` if RMCP is not in PATH
- Add appropriate PYTHONPATH environment variables as needed
- Modify ports and paths according to your setup
"""

        with open(samples_dir / "README.md", "w") as f:
            f.write(readme)

        self.log(f"Sample configurations created in: {samples_dir}", "SUCCESS")
        return True

    def run_setup(self, components: List[str]) -> bool:
        """Run setup for specified components."""
        print("🛠️ RMCP Automated Setup")
        print("=" * 40)

        results = {}

        if "claude-desktop" in components or "all" in components:
            results["Claude Desktop"] = self.setup_claude_desktop()

        if "vscode" in components or "all" in components:
            results["VS Code"] = self.setup_vscode()

        if "docker" in components or "all" in components:
            results["Docker"] = self.setup_docker_environment()

        if "r-packages" in components or "all" in components:
            results["R Packages"] = self.setup_r_packages()

        if "samples" in components or "all" in components:
            results["Sample Configs"] = self.create_sample_configurations()

        # Results summary
        print("\n📊 Setup Results:")
        print("=" * 20)

        success_count = 0
        for component, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{status}: {component}")
            if success:
                success_count += 1

        print(
            f"\nOverall: {success_count}/{len(results)} components set up successfully"
        )

        if success_count == len(results):
            print("\n🎉 Setup completed successfully!")
            print("\nNext steps:")
            print("1. Restart Claude Desktop to load new configuration")
            print("2. Test RMCP integration in Claude Desktop")
            print("3. Run: python tests/local/validate_local_setup.py")
        else:
            print("\n⚠️  Some setup steps failed. Check the errors above.")

        return success_count == len(results)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Automated RMCP setup")
    parser.add_argument(
        "--claude-desktop",
        action="store_true",
        help="Set up Claude Desktop configuration",
    )
    parser.add_argument(
        "--vscode", action="store_true", help="Set up VS Code with Continue extension"
    )
    parser.add_argument(
        "--docker", action="store_true", help="Set up Docker environment"
    )
    parser.add_argument("--r-packages", action="store_true", help="Install R packages")
    parser.add_argument(
        "--samples", action="store_true", help="Create sample configuration files"
    )
    parser.add_argument("--all", action="store_true", help="Set up all components")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # If no specific components selected, show help
    if not any(
        [
            args.claude_desktop,
            args.vscode,
            args.docker,
            args.r_packages,
            args.samples,
            args.all,
        ]
    ):
        parser.print_help()
        return

    components = []
    if args.claude_desktop:
        components.append("claude-desktop")
    if args.vscode:
        components.append("vscode")
    if args.docker:
        components.append("docker")
    if args.r_packages:
        components.append("r-packages")
    if args.samples:
        components.append("samples")
    if args.all:
        components = ["all"]

    setup = RMCPSetupAutomation(verbose=args.verbose)
    success = setup.run_setup(components)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
