#!/usr/bin/env python3
"""
Basic test to ensure RMCP server core functionality works.
This test verifies the server can start and respond to basic requests.
"""
import subprocess
import sys
from pathlib import Path


def test_dependencies():
    """Test that required dependencies are available."""
    print("🔍 Testing Dependencies")
    print("-" * 40)
    try:
        import click

        print("✅ click available")
    except ImportError:
        print("❌ click missing - install with: pip install click")
        return False
    try:
        import jsonschema

        print("✅ jsonschema available")
    except ImportError:
        print("❌ jsonschema missing - install with: pip install jsonschema")
        return False
    return True


def test_r_availability():
    """Test that R is available for statistical computations."""
    print("\n🔍 Testing R Installation")
    print("-" * 40)
    try:
        result = subprocess.run(
            ["R", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            version_line = result.stdout.split("\n")[0]
            print(f"✅ R is available: {version_line}")
            return True
        else:
            print("❌ R not working properly")
            return False
    except subprocess.TimeoutExpired:
        print("❌ R command timed out")
        return False
    except FileNotFoundError:
        print("❌ R not found - install R to use RMCP")
        return False


def test_basic_server_import():
    """Test that the server can be imported without errors."""
    print("\n🔍 Testing Server Import")
    print("-" * 40)
    # Add rmcp to path - adjusted for new location
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    try:
        # Try to import core components
        from rmcp.core.context import Context, LifespanState

        print("✅ Core context imported")
        from rmcp.core.server import create_server

        print("✅ Server creation imported")
        # Try to create basic server
        server = create_server()
        print("✅ Server created successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Server creation failed: {e}")
        return False


def test_cli_basic():
    """Test basic CLI functionality."""
    print("\n🔍 Testing CLI")
    print("-" * 40)
    try:
        # Test version command
        result = subprocess.run(
            [sys.executable, "-m", "rmcp", "version"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent.parent,
        )
        if result.returncode == 0:
            print(f"✅ CLI version: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ CLI failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ CLI command timed out")
        return False
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False


def main():
    """Run all basic server tests."""
    print("🧪 RMCP Server Basic Functionality Test")
    print("=" * 50)
    tests = [
        ("Dependencies", test_dependencies),
        ("R Installation", test_r_availability),
        ("Server Import", test_basic_server_import),
        ("CLI Basic", test_cli_basic),
    ]
    passed = 0
    total = len(tests)
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"\n❌ {name} test failed")
        except Exception as e:
            print(f"\n❌ {name} test error: {e}")
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    if passed == total:
        print("✅ RMCP server is ready to use!")
        return True
    else:
        print("❌ RMCP server has issues that need to be fixed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
