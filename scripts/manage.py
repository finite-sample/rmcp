#!/usr/bin/env python3
"""
RMCP Script Management Utility

Provides centralized management for all RMCP development scripts:
- Script discovery and validation
- Dependency checking
- Execution orchestration
- Performance monitoring
- Maintenance automation

Usage:
    python scripts/manage.py list
    python scripts/manage.py run <script_name> [args...]
    python scripts/manage.py validate
    python scripts/manage.py health-check
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ScriptManager:
    """Manages RMCP development scripts."""

    def __init__(self):
        self.scripts_dir = Path(__file__).parent
        self.project_root = self.scripts_dir.parent
        self.script_registry = self._discover_scripts()

    def _discover_scripts(self) -> Dict[str, Dict]:
        """Discover and catalog all scripts."""
        registry = {}

        # Testing scripts
        testing_dir = self.scripts_dir / "testing"
        registry.update(
            {
                "e2e-tests": {
                    "path": testing_dir / "run_e2e_tests.py",
                    "type": "python",
                    "category": "testing",
                    "description": "Comprehensive E2E testing suite",
                    "dependencies": ["python", "docker?", "claude-desktop?"],
                    "args": [
                        "--quick",
                        "--claude",
                        "--docker",
                        "--performance",
                        "--all",
                    ],
                },
                "test-local": {
                    "path": testing_dir / "test-local.sh",
                    "type": "shell",
                    "category": "testing",
                    "description": "Local Docker testing validation",
                    "dependencies": ["docker"],
                    "args": [],
                },
            }
        )

        # Debugging scripts
        debugging_dir = self.scripts_dir / "debugging"
        registry.update(
            {
                "debug-mcp": {
                    "path": debugging_dir / "debug-mcp-protocol.sh",
                    "type": "shell",
                    "category": "debugging",
                    "description": "MCP protocol communication debugging",
                    "dependencies": ["docker"],
                    "args": [],
                }
            }
        )

        # Integration testing scripts
        integration_dir = testing_dir / "integration"
        registry.update(
            {
                "claude-desktop-e2e": {
                    "path": integration_dir / "claude_desktop_e2e.py",
                    "type": "python",
                    "category": "integration",
                    "description": "Real Claude Desktop integration testing",
                    "dependencies": ["python", "claude-desktop?"],
                    "args": ["--quick", "--verbose"],
                },
                "docker-workflows": {
                    "path": integration_dir / "docker_workflows.py",
                    "type": "python",
                    "category": "integration",
                    "description": "Complete Docker workflow validation",
                    "dependencies": ["python", "docker"],
                    "args": ["--verbose"],
                },
                "realistic-scenarios": {
                    "path": integration_dir / "realistic_scenarios.py",
                    "type": "python",
                    "category": "integration",
                    "description": "Real-world usage scenario testing",
                    "dependencies": ["python", "docker?", "claude-desktop?"],
                    "args": [],
                },
            }
        )

        # Setup and validation scripts
        setup_dir = self.scripts_dir / "setup"
        registry.update(
            {
                "validate-local": {
                    "path": setup_dir / "validate_local_setup.py",
                    "type": "python",
                    "category": "setup",
                    "description": "Local environment validation and auto-fix",
                    "dependencies": ["python"],
                    "args": ["--auto-fix", "--verbose"],
                },
                "setup-automation": {
                    "path": setup_dir / "setup_automation.py",
                    "type": "python",
                    "category": "setup",
                    "description": "Automated setup for new users and environments",
                    "dependencies": ["python"],
                    "args": [
                        "--claude-desktop",
                        "--vscode",
                        "--docker",
                        "--r-packages",
                        "--all",
                    ],
                },
                "ide-integrations": {
                    "path": setup_dir / "ide_integrations.py",
                    "type": "python",
                    "category": "setup",
                    "description": "IDE integration testing and validation",
                    "dependencies": ["python"],
                    "args": [],
                },
                "validate-ide-configs": {
                    "path": setup_dir / "validate_ide_configs.py",
                    "type": "python",
                    "category": "setup",
                    "description": "IDE configuration validation",
                    "dependencies": ["python"],
                    "args": [],
                },
            }
        )

        return registry

    def list_scripts(self) -> None:
        """List all available scripts."""
        print("📋 RMCP Development Scripts")
        print("=" * 50)

        by_category = {}
        for name, info in self.script_registry.items():
            category = info["category"]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append((name, info))

        for category, scripts in by_category.items():
            print(f"\n{category.title()} Scripts:")
            print("-" * 30)
            for name, info in scripts:
                status = "✅" if info["path"].exists() else "❌"
                print(f"  {status} {name:<15} - {info['description']}")
                if info["args"]:
                    print(f"      Args: {', '.join(info['args'])}")

    def validate_dependencies(self, script_name: str) -> Tuple[bool, List[str]]:
        """Validate script dependencies."""
        if script_name not in self.script_registry:
            return False, [f"Script '{script_name}' not found"]

        script_info = self.script_registry[script_name]
        missing_deps = []

        for dep in script_info["dependencies"]:
            optional = dep.endswith("?")
            dep_name = dep.rstrip("?")

            if dep_name == "python":
                if sys.version_info < (3, 10):
                    missing_deps.append("Python 3.10+")
            elif dep_name == "docker":
                result = subprocess.run(
                    ["docker", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0 and not optional:
                    missing_deps.append("Docker")
            elif dep_name == "claude-desktop":
                # Check for Claude Desktop config
                import platform

                system = platform.system()
                if system == "Darwin":
                    config_path = (
                        Path.home()
                        / "Library/Application Support/Claude/claude_desktop_config.json"
                    )
                elif system == "Windows":
                    config_path = (
                        Path.home()
                        / "AppData/Roaming/Claude/claude_desktop_config.json"
                    )
                else:
                    config_path = (
                        Path.home() / ".config/claude/claude_desktop_config.json"
                    )

                if not config_path.exists() and not optional:
                    missing_deps.append("Claude Desktop configuration")

        return len(missing_deps) == 0, missing_deps

    def run_script(self, script_name: str, args: List[str] = None) -> bool:
        """Run a specific script."""
        if script_name not in self.script_registry:
            print(f"❌ Script '{script_name}' not found")
            return False

        script_info = self.script_registry[script_name]
        script_path = script_info["path"]

        if not script_path.exists():
            print(f"❌ Script file not found: {script_path}")
            return False

        # Validate dependencies
        deps_ok, missing_deps = self.validate_dependencies(script_name)
        if not deps_ok:
            print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
            return False

        print(f"🚀 Running {script_name}: {script_info['description']}")
        print(f"   Path: {script_path}")

        # Prepare command
        if script_info["type"] == "python":
            command = [sys.executable, str(script_path)]
        elif script_info["type"] == "shell":
            command = [str(script_path)]
        else:
            print(f"❌ Unknown script type: {script_info['type']}")
            return False

        if args:
            command.extend(args)

        # Execute script
        start_time = time.time()
        try:
            result = subprocess.run(
                command, cwd=self.project_root, timeout=600  # 10 minutes max
            )
            end_time = time.time()
            duration = end_time - start_time

            if result.returncode == 0:
                print(f"✅ Script completed successfully ({duration:.1f}s)")
                return True
            else:
                print(f"❌ Script failed (exit code: {result.returncode})")
                return False

        except subprocess.TimeoutExpired:
            print("⏰ Script timed out (10 minutes)")
            return False
        except Exception as e:
            print(f"💥 Script execution failed: {e}")
            return False

    def health_check(self) -> bool:
        """Perform health check on all scripts."""
        print("🔍 RMCP Scripts Health Check")
        print("=" * 40)

        all_healthy = True
        for script_name, script_info in self.script_registry.items():
            print(f"\n📋 Checking {script_name}:")

            # Check file exists
            if not script_info["path"].exists():
                print(f"  ❌ File not found: {script_info['path']}")
                all_healthy = False
                continue

            # Check executable permissions for shell scripts
            if script_info["type"] == "shell":
                if not script_info["path"].stat().st_mode & 0o111:
                    print(f"  ⚠️  Not executable (run: chmod +x {script_info['path']})")

            # Check dependencies
            deps_ok, missing_deps = self.validate_dependencies(script_name)
            if not deps_ok:
                print(f"  ⚠️  Missing dependencies: {', '.join(missing_deps)}")
                # Don't mark as unhealthy for optional dependencies
                if any(not dep.endswith("?") for dep in missing_deps):
                    all_healthy = False
            else:
                print("  ✅ Dependencies satisfied")

        print(
            f"\n📊 Overall Health: {'✅ HEALTHY' if all_healthy else '⚠️  ISSUES FOUND'}"
        )
        return all_healthy

    def generate_usage_report(self) -> None:
        """Generate usage report for scripts."""
        print("📊 Script Usage Report")
        print("=" * 30)

        for category in ["testing", "debugging", "integration", "setup", "development"]:
            scripts = [
                (name, info)
                for name, info in self.script_registry.items()
                if info["category"] == category
            ]

            if scripts:
                print(f"\n{category.title()} ({len(scripts)} scripts):")
                for name, info in scripts:
                    print(f"  • {name}: {info['description']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="RMCP Script Management Utility")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    subparsers.add_parser("list", help="List all available scripts")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a specific script")
    run_parser.add_argument("script_name", help="Name of script to run")
    run_parser.add_argument("args", nargs="*", help="Arguments to pass to the script")

    # Validate command
    subparsers.add_parser("validate", help="Validate all scripts and dependencies")

    # Health check command
    subparsers.add_parser("health-check", help="Perform health check on all scripts")

    # Report command
    subparsers.add_parser("report", help="Generate usage report")

    args = parser.parse_args()

    manager = ScriptManager()

    if args.command == "list":
        manager.list_scripts()
    elif args.command == "run":
        success = manager.run_script(args.script_name, args.args)
        sys.exit(0 if success else 1)
    elif args.command == "validate" or args.command == "health-check":
        healthy = manager.health_check()
        sys.exit(0 if healthy else 1)
    elif args.command == "report":
        manager.generate_usage_report()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
