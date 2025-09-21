"""
Integration tests for new features in v0.3.6.
Tests how the new tools work together and with existing tools.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add rmcp to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions
from rmcp.tools.fileops import read_excel, read_json
from rmcp.tools.formula_builder import build_formula, validate_formula
from rmcp.tools.helpers import load_example, suggest_fix, validate_data
from rmcp.tools.regression import correlation_analysis, linear_model


async def create_integration_server():
    """Create server with new and existing tools for integration testing."""
    server = create_server()

    # Register both new and existing tools
    register_tool_functions(
        server.tools,
        # New tools
        build_formula,
        validate_formula,
        suggest_fix,
        validate_data,
        load_example,
        read_json,
        read_excel,
        # Existing tools
        linear_model,
        correlation_analysis,
    )

    return server


async def test_formula_to_analysis_workflow():
    """Test complete workflow: natural language → formula → validation → analysis."""
    print("\n🔄 Testing Formula-to-Analysis Workflow")
    print("-" * 50)

    server = await create_integration_server()

    # Step 1: Build formula from natural language
    formula_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "build_formula",
            "arguments": {
                "description": "predict satisfaction from purchase frequency"
            },
        },
    }

    response = await server.handle_request(formula_request)
    assert "result" in response
    assert "content" in response["result"]
    assert len(response["result"]["content"]) > 0

    content_text = response["result"]["content"][0]["text"]
    if not content_text or content_text.strip() == "":
        raise ValueError("Empty response from formula builder")

    formula_result = json.loads(content_text)
    formula = formula_result["formula"]
    print(f"   ✅ Formula built: {formula}")

    # Step 2: Load example dataset
    data_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "load_example",
            "arguments": {"dataset_name": "survey", "size": "small"},
        },
    }

    response = await server.handle_request(data_request)
    assert "result" in response
    assert "content" in response["result"]
    assert len(response["result"]["content"]) > 0

    content_text = response["result"]["content"][0]["text"]
    if not content_text or content_text.strip() == "":
        raise ValueError("Empty response from load_example")

    data_result = json.loads(content_text)
    dataset = data_result["data"]
    print(f"   ✅ Dataset loaded: {data_result['metadata']['rows']} rows")

    # Step 3: Validate formula against data
    validation_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "validate_formula",
            "arguments": {
                "formula": "satisfaction ~ purchase_frequency",
                "data": dataset,
            },
        },
    }

    response = await server.handle_request(validation_request)
    assert "result" in response
    assert "content" in response["result"]
    assert len(response["result"]["content"]) > 0

    content_text = response["result"]["content"][0]["text"]
    if not content_text or content_text.strip() == "":
        raise ValueError("Empty response from validate_formula")

    validation_result = json.loads(content_text)
    print(f"   ✅ Formula validated: {'✓' if validation_result['is_valid'] else '✗'}")

    # Step 4: Run correlation analysis
    analysis_request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "correlation_analysis",
            "arguments": {"data": dataset, "method": "pearson"},
        },
    }

    response = await server.handle_request(analysis_request)
    assert "result" in response
    assert "content" in response["result"]
    assert len(response["result"]["content"]) > 0

    content_text = response["result"]["content"][0]["text"]
    if not content_text or content_text.strip() == "":
        raise ValueError("Empty response from correlation_analysis")

    analysis_result = json.loads(content_text)
    print(
        f"   ✅ Analysis completed: {len(analysis_result.get('correlation_matrix', {}))} correlations"
    )

    return True


async def test_error_recovery_workflow():
    """Test error recovery helping with actual problems."""
    print("\n🔧 Testing Error Recovery Workflow")
    print("-" * 50)

    server = await create_integration_server()

    # Simulate common errors and test recovery suggestions
    error_scenarios = [
        {
            "error": "there is no package called 'forecast'",
            "tool": "arima_model",
            "expected_type": "missing_package",
        },
        {
            "error": "object 'sales' not found",
            "tool": "linear_model",
            "expected_type": "missing_variable",
        },
        {
            "error": "invalid formula syntax",
            "tool": "correlation_analysis",
            "expected_type": "formula_syntax",
        },
    ]

    for i, scenario in enumerate(error_scenarios, 1):
        request = {
            "jsonrpc": "2.0",
            "id": i,
            "method": "tools/call",
            "params": {
                "name": "suggest_fix",
                "arguments": {
                    "error_message": scenario["error"],
                    "tool_name": scenario["tool"],
                },
            },
        }

        response = await server.handle_request(request)
        assert "result" in response
        assert "content" in response["result"]
        assert len(response["result"]["content"]) > 0

        content_text = response["result"]["content"][0]["text"]
        if not content_text or content_text.strip() == "":
            raise ValueError(f"Empty response from suggest_fix for scenario {i}")

        result = json.loads(content_text)
        assert result["error_type"] == scenario["expected_type"]
        print(f"   ✅ Error {i} diagnosed: {result['error_type']}")

    return True


async def test_data_validation_integration():
    """Test data validation with different analysis types."""
    print("\n🔍 Testing Data Validation Integration")
    print("-" * 50)

    server = await create_integration_server()

    # Load different datasets and validate for different analysis types
    datasets = ["sales", "customers", "economics"]
    analysis_types = ["regression", "classification", "correlation"]

    for dataset_name, analysis_type in zip(datasets, analysis_types):
        # Load dataset
        data_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "load_example",
                "arguments": {"dataset_name": dataset_name, "size": "small"},
            },
        }

        response = await server.handle_request(data_request)
        assert "result" in response
        assert "content" in response["result"]
        assert len(response["result"]["content"]) > 0

        content_text = response["result"]["content"][0]["text"]
        if not content_text or content_text.strip() == "":
            raise ValueError(f"Empty response from load_example for {dataset_name}")

        data_result = json.loads(content_text)
        dataset = data_result["data"]

        # Validate for specific analysis type
        validation_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "validate_data",
                "arguments": {"data": dataset, "analysis_type": analysis_type},
            },
        }

        response = await server.handle_request(validation_request)
        assert "result" in response
        assert "content" in response["result"]
        assert len(response["result"]["content"]) > 0

        content_text = response["result"]["content"][0]["text"]
        if not content_text or content_text.strip() == "":
            raise ValueError(f"Empty response from validate_data for {dataset_name}")

        validation_result = json.loads(content_text)
        print(
            f"   ✅ {dataset_name} validated for {analysis_type}: {'✓' if validation_result['is_valid'] else '⚠'}"
        )

    return True


async def main():
    """Run all integration tests."""
    print("🔗 RMCP New Features Integration Tests")
    print("=" * 60)

    tests = [
        ("Formula-to-Analysis Workflow", test_formula_to_analysis_workflow),
        ("Error Recovery Workflow", test_error_recovery_workflow),
        ("Data Validation Integration", test_data_validation_integration),
    ]

    passed = 0
    for test_name, test_func in tests:
        print(f"\n🎯 {test_name}")
        try:
            success = await test_func()
            if success:
                passed += 1
                print(f"✅ PASSED: {test_name}")
            else:
                print(f"❌ FAILED: {test_name}")
        except Exception as e:
            print(f"💥 ERROR: {test_name} - {e}")

    print(f"\n📊 Integration Test Results: {passed}/{len(tests)} passed")

    if passed == len(tests):
        print("🎊 ALL INTEGRATION TESTS PASSED!")
        return True
    else:
        print("⚠️ Some integration tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
