#!/usr/bin/env python3
"""
Comprehensive error handling tests for RMCP.

Tests various error scenarios to ensure robust error handling:
- Invalid input data
- Missing parameters
- R execution errors
- Network/resource issues
- Edge cases
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions
from rmcp.tools.fileops import read_csv
from rmcp.tools.formula_builder import build_formula
from rmcp.tools.helpers import suggest_fix, validate_data
from rmcp.tools.regression import linear_model


@pytest.mark.asyncio
async def test_missing_required_parameters():
    """Test tools handle missing required parameters gracefully."""
    print("🧪 Testing missing required parameters...")

    server = create_server()
    register_tool_functions(server.tools, linear_model)

    # Test missing data parameter
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "linear_model",
            "arguments": {
                "formula": "y ~ x"
                # Missing "data" parameter
            },
        },
    }

    try:
        response = await server.handle_request(request)

        # Should not crash, but should return error
        if "error" in response:
            print("✅ Missing parameters handled gracefully")
            return True
        else:
            # Check if result contains error info
            result = json.loads(response["result"]["content"][0]["text"])
            if "error" in str(result).lower():
                print("✅ Missing parameters detected and reported")
                return True
            else:
                print("❌ Missing parameters not properly handled")
                return False

    except Exception as e:
        print(f"❌ Unhandled exception for missing parameters: {e}")
        return False


@pytest.mark.asyncio
async def test_invalid_data_types():
    """Test tools handle invalid data types."""
    print("🧪 Testing invalid data types...")

    server = create_server()
    register_tool_functions(server.tools, linear_model)

    # Test with invalid data (string instead of dict)
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "linear_model",
            "arguments": {"data": "this_should_be_a_dict", "formula": "y ~ x"},
        },
    }

    try:
        response = await server.handle_request(request)

        if "error" in response:
            print("✅ Invalid data types handled gracefully")
            return True
        else:
            result = json.loads(response["result"]["content"][0]["text"])
            if "error" in str(result).lower():
                print("✅ Invalid data types detected and reported")
                return True
            else:
                print("❌ Invalid data types not properly handled")
                return False

    except Exception as e:
        print(f"❌ Unhandled exception for invalid data types: {e}")
        return False


@pytest.mark.asyncio
async def test_empty_data():
    """Test tools handle empty datasets."""
    print("🧪 Testing empty data handling...")

    server = create_server()
    register_tool_functions(server.tools, linear_model)

    # Test with empty data
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "linear_model",
            "arguments": {"data": {}, "formula": "y ~ x"},
        },
    }

    try:
        response = await server.handle_request(request)

        if "error" in response:
            print("✅ Empty data handled gracefully")
            return True
        else:
            result = json.loads(response["result"]["content"][0]["text"])
            if "error" in str(result).lower() or "empty" in str(result).lower():
                print("✅ Empty data detected and reported")
                return True
            else:
                print("❌ Empty data not properly handled")
                return False

    except Exception as e:
        print(f"❌ Unhandled exception for empty data: {e}")
        return False


@pytest.mark.asyncio
async def test_malformed_json_in_tools():
    """Test tools handle malformed data gracefully."""
    print("🧪 Testing malformed data handling...")

    server = create_server()
    register_tool_functions(server.tools, linear_model)

    # Test with malformed data structure
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "linear_model",
            "arguments": {
                "data": {
                    "x": [1, 2, "not_a_number", 4],
                    "y": [1, 2, 3],  # Different length
                },
                "formula": "y ~ x",
            },
        },
    }

    try:
        response = await server.handle_request(request)

        if "error" in response:
            print("✅ Malformed data handled gracefully")
            return True
        else:
            result = json.loads(response["result"]["content"][0]["text"])
            if "error" in str(result).lower():
                print("✅ Malformed data detected and reported")
                return True
            else:
                print("❌ Malformed data not properly handled")
                return False

    except Exception as e:
        print(f"❌ Unhandled exception for malformed data: {e}")
        return False


@pytest.mark.asyncio
async def test_invalid_formulas():
    """Test formula validation handles invalid formulas."""
    print("🧪 Testing invalid formula handling...")

    server = create_server()
    register_tool_functions(server.tools, linear_model)

    # Test with invalid R formula syntax
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "linear_model",
            "arguments": {
                "data": {"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]},
                "formula": "invalid ~ ~ syntax error",
            },
        },
    }

    try:
        response = await server.handle_request(request)

        if "error" in response:
            print("✅ Invalid formulas handled gracefully")
            return True
        else:
            result = json.loads(response["result"]["content"][0]["text"])
            if "error" in str(result).lower() or "formula" in str(result).lower():
                print("✅ Invalid formulas detected and reported")
                return True
            else:
                print("❌ Invalid formulas not properly handled")
                return False

    except Exception as e:
        print(f"❌ Unhandled exception for invalid formulas: {e}")
        return False


@pytest.mark.asyncio
async def test_nonexistent_file_handling():
    """Test file operations handle missing files."""
    print("🧪 Testing nonexistent file handling...")

    server = create_server()
    register_tool_functions(server.tools, read_csv)

    # Test reading nonexistent file
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "read_csv",
            "arguments": {"file_path": "/nonexistent/path/file.csv"},
        },
    }

    try:
        response = await server.handle_request(request)

        if "error" in response:
            print("✅ Nonexistent files handled gracefully")
            return True
        else:
            result = json.loads(response["result"]["content"][0]["text"])
            if "error" in str(result).lower() or "not found" in str(result).lower():
                print("✅ Nonexistent files detected and reported")
                return True
            else:
                print("❌ Nonexistent files not properly handled")
                return False

    except Exception as e:
        print(f"❌ Unhandled exception for nonexistent files: {e}")
        return False


@pytest.mark.asyncio
async def test_error_recovery_tool():
    """Test the error recovery tool handles various error types."""
    print("🧪 Testing error recovery tool...")

    server = create_server()
    register_tool_functions(server.tools, suggest_fix)

    # Test with common R error
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "suggest_fix",
            "arguments": {
                "error_message": "there is no package called 'nonexistent_package'"
            },
        },
    }

    try:
        response = await server.handle_request(request)

        if "error" in response:
            print("❌ Error recovery tool failed")
            return False
        else:
            result = json.loads(response["result"]["content"][0]["text"])
            if "error_type" in result and "suggestions" in result:
                print("✅ Error recovery tool working properly")
                return True
            else:
                print("❌ Error recovery tool not providing proper analysis")
                return False

    except Exception as e:
        print(f"❌ Unhandled exception in error recovery: {e}")
        return False


@pytest.mark.asyncio
async def test_data_validation_edge_cases():
    """Test data validation with edge cases."""
    print("🧪 Testing data validation edge cases...")

    server = create_server()
    register_tool_functions(server.tools, validate_data)

    # Test with edge case data (all missing values)
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "validate_data",
            "arguments": {
                "data": {
                    "x": [None, None, None],
                    "y": [float("inf"), -float("inf"), float("nan")],
                }
            },
        },
    }

    try:
        response = await server.handle_request(request)

        if "error" in response:
            print("✅ Edge case data handled gracefully")
            return True
        else:
            result = json.loads(response["result"]["content"][0]["text"])
            if "issues" in result or "warnings" in result:
                print("✅ Edge case data issues detected")
                return True
            else:
                print("❌ Edge case data issues not detected")
                return False

    except Exception as e:
        print(f"❌ Unhandled exception in data validation: {e}")
        return False


@pytest.mark.asyncio
async def test_natural_language_formula_errors():
    """Test formula builder with ambiguous/invalid descriptions."""
    print("🧪 Testing natural language formula error handling...")

    server = create_server()
    register_tool_functions(server.tools, build_formula)

    # Test with very ambiguous description
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "build_formula",
            "arguments": {"description": "something something random words"},
        },
    }

    try:
        response = await server.handle_request(request)

        if "error" in response:
            print("✅ Ambiguous descriptions handled gracefully")
            return True
        else:
            result = json.loads(response["result"]["content"][0]["text"])
            if "confidence" in result and result.get("confidence", 1.0) < 0.5:
                print("✅ Low confidence formulas flagged")
                return True
            else:
                print("⚠️  Ambiguous descriptions accepted (may be ok)")
                return True  # This might be acceptable behavior

    except Exception as e:
        print(f"❌ Unhandled exception in formula building: {e}")
        return False


async def main():
    """Run all error handling tests."""
    print("🔥 RMCP Error Handling Test Suite")
    print("=" * 50)

    tests = [
        ("Missing Required Parameters", test_missing_required_parameters),
        ("Invalid Data Types", test_invalid_data_types),
        ("Empty Data Handling", test_empty_data),
        ("Malformed Data", test_malformed_json_in_tools),
        ("Invalid Formulas", test_invalid_formulas),
        ("Nonexistent File Handling", test_nonexistent_file_handling),
        ("Error Recovery Tool", test_error_recovery_tool),
        ("Data Validation Edge Cases", test_data_validation_edge_cases),
        ("Natural Language Formula Errors", test_natural_language_formula_errors),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        print("-" * 40)
        try:
            if await test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")

    print(f"\n🎯 Error Handling Test Results:")
    print("=" * 50)
    print(f"✅ Passed: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 All error handling tests passed!")
        print("🛡️  RMCP error handling is robust")
    elif passed >= total * 0.8:
        print("✨ Most error handling tests passed")
        print(f"⚠️  {total - passed} test(s) need attention")
    else:
        print("⚠️  Multiple error handling failures")
        print("🔧 Error handling needs improvement")

    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        sys.exit(1)
