#!/usr/bin/env python3
"""
Unit tests for RMCP server core functionality (Python-only).
Tests that don't require R execution.
"""
import sys
from pathlib import Path

import pytest


def test_dependencies():
    """Test that required Python dependencies are available."""
    print("🔍 Testing Dependencies")
    print("-" * 40)
    try:
        import click

        print("✅ click available")
    except ImportError:
        print("❌ click missing - install with: pip install click")
        assert False, "click missing"
    try:
        import jsonschema

        print("✅ jsonschema available")
    except ImportError:
        print("❌ jsonschema missing - install with: pip install jsonschema")
        assert False, "jsonschema missing"


def test_basic_server_import():
    """Test that the server can be imported without errors."""
    print("\n🔍 Testing Server Import")
    print("-" * 40)
    try:
        # Try to import core components
        from rmcp.core.context import Context, LifespanState

        print("✅ Core context imported")
        from rmcp.core.server import create_server

        print("✅ Server creation imported")
        # Try to create basic server
        server = create_server()
        print("✅ Server created successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        assert False, f"Import error: {e}"
    except Exception as e:
        print(f"❌ Server creation failed: {e}")
        assert False, f"Server creation failed: {e}"


# R-dependent tests and CLI tests moved to tests/integration/test_server_integration.py


def main():
    """Run Python-only server tests."""
    print("🧪 RMCP Server Python-Only Tests")
    print("=" * 50)
    tests = [
        ("Dependencies", test_dependencies),
        ("Server Import", test_basic_server_import),
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
        print("✅ RMCP Python components work!")
        return True
    else:
        print("❌ RMCP Python components have issues")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
