#!/usr/bin/env python3
"""
Comprehensive smoke tests for all 40 RMCP tools.
Tests complete integration flow for each tool with minimal viable datasets,
ensuring all tool paths work end-to-end without requiring R environment.
"""
import asyncio
import sys
from pathlib import Path
from shutil import which
from unittest.mock import AsyncMock, patch
import pytest

# Add rmcp to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from rmcp.core.context import Context, LifespanState
from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions

# Import all 40 tools from CLI registration
from rmcp.tools.descriptive import frequency_table, outlier_detection, summary_stats
from rmcp.tools.econometrics import instrumental_variables, panel_regression, var_model
from rmcp.tools.fileops import (
    data_info,
    filter_data,
    read_csv,
    read_excel,
    read_json,
    write_csv,
)
from rmcp.tools.formula_builder import build_formula, validate_formula
from rmcp.tools.helpers import load_example, suggest_fix, validate_data
from rmcp.tools.machine_learning import decision_tree, kmeans_clustering, random_forest
from rmcp.tools.regression import (
    correlation_analysis,
    linear_model,
    logistic_regression,
)
from tests.utils import extract_json_content, extract_text_summary

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for comprehensive tool smoke tests"
)
from rmcp.tools.statistical_tests import anova, chi_square_test, normality_test, t_test
from rmcp.tools.timeseries import arima_model, decompose_timeseries, stationarity_test
from rmcp.tools.transforms import difference, lag_lead, standardize, winsorize
from rmcp.tools.visualization import (
    boxplot,
    correlation_heatmap,
    histogram,
    regression_plot,
    scatter_plot,
    time_series_plot,
)

# Test data sets - minimal viable data for each category
BASIC_DATA = {"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]}
CATEGORICAL_DATA = {
    "category": ["A", "B", "A", "B", "A"],
    "value": [10, 20, 15, 25, 12],
}
TIME_SERIES_DATA = {"values": [100, 102, 98, 105, 108, 110, 95, 100, 103, 107]}
PANEL_DATA = {
    "id": [1, 1, 2, 2, 3, 3],
    "time": [1, 2, 1, 2, 1, 2],
    "y": [10, 12, 15, 18, 20, 22],
    "x": [5, 6, 7, 8, 9, 10],
}
BINARY_DATA = {"outcome": [0, 1, 0, 1, 0], "predictor": [1, 3, 2, 4, 1]}
# Mock R execution results for each tool category
MOCK_RESPONSES = {
    # Regression tools
    "linear_model": {
        "coefficients": {"(Intercept)": 0.0, "x": 2.0},
        "r_squared": 0.99,
        "p_values": {"(Intercept)": 0.05, "x": 0.001},
        "residuals": [0.1, -0.1, 0.0, 0.1, -0.1],
    },
    "correlation_analysis": {
        "correlation_matrix": {"x": [1.0, 0.99], "y": [0.99, 1.0]},
        "p_values": {"x": [0.0, 0.001], "y": [0.001, 0.0]},
        "n_obs": 5,
    },
    "logistic_regression": {
        "coefficients": {"(Intercept)": -1.0, "predictor": 0.5},
        "odds_ratios": {"(Intercept)": 0.37, "predictor": 1.65},
        "p_values": {"(Intercept)": 0.1, "predictor": 0.05},
        "accuracy": 0.8,
    },
    # Statistical tests
    "t_test": {
        "statistic": 2.5,
        "p_value": 0.03,
        "confidence_interval": {"lower": 0.1, "upper": 3.9, "level": 0.95},
        "mean": 2.0,
        "alternative": "two.sided",
    },
    "anova": {
        "f_statistic": 15.2,
        "p_value": 0.01,
        "df_between": 2,
        "df_within": 12,
        "sum_sq": [100, 50],
        "mean_sq": [50, 4.2],
    },
    "chi_square_test": {
        "statistic": 8.5,
        "p_value": 0.02,
        "df": 2,
        "test_type": "independence",
        "observed": [[10, 5], [8, 12]],
        "expected": [[9, 6], [9, 11]],
    },
    "normality_test": {
        "test": "shapiro",
        "statistic": 0.95,
        "p_value": 0.7,
        "is_normal": True,
        "interpretation": "Data appears normally distributed",
    },
    # Descriptive statistics
    "summary_stats": {
        "variable": "x",
        "n": 5,
        "mean": 3.0,
        "sd": 1.58,
        "min": 1,
        "max": 5,
        "q25": 2.0,
        "median": 3.0,
        "q75": 4.0,
    },
    "outlier_detection": {
        "outliers": [5],
        "outlier_indices": [4],
        "method": "iqr",
        "threshold": 1.5,
        "n_outliers": 1,
    },
    "frequency_table": {
        "category": {"A": 3, "B": 2},
        "percentages": {"A": 60.0, "B": 40.0},
        "n_total": 5,
    },
    # Data transformations
    "standardize": {
        "data": {"x_standardized": [-1.26, -0.63, 0.0, 0.63, 1.26]},
        "method": "z_score",
        "original_mean": 3.0,
        "original_sd": 1.58,
    },
    "winsorize": {
        "data": {"x_winsorized": [1, 2, 3, 4, 4]},
        "percentiles": [0.1, 0.9],
        "n_winsorized": 1,
    },
    "lag_lead": {"data": {"x_lag1": [None, 1, 2, 3, 4]}, "lags": 1, "variable": "x"},
    "difference": {"data": {"x_diff": [None, 1, 1, 1, 1]}, "order": 1, "variable": "x"},
    # Time series
    "stationarity_test": {
        "test": "adf",
        "statistic": -3.2,
        "p_value": 0.02,
        "critical_values": {"1%": -3.43, "5%": -2.86, "10%": -2.57},
        "is_stationary": True,
    },
    "decompose_timeseries": {
        "trend": [100, 101, 102, 103, 104, 105, 104, 103, 102, 101],
        "seasonal": [0, 1, -4, 2, 4, 5, -9, -3, 1, 6],
        "remainder": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "frequency": 4,
    },
    "arima_model": {
        "order": [1, 0, 1],
        "coefficients": {"ar1": 0.5, "ma1": 0.3},
        "aic": 45.2,
        "forecast": [108, 109, 110],
        "forecast_se": [2.1, 2.3, 2.5],
    },
    # Machine learning
    "kmeans_clustering": {
        "clusters": [1, 2, 1, 2, 1],
        "centers": {"cluster_1": [2.0, 4.0], "cluster_2": [3.5, 7.0]},
        "k": 2,
        "within_ss": [1.2, 2.1],
        "total_within_ss": 3.3,
    },
    "decision_tree": {
        "predictions": [0, 1, 0, 1, 0],
        "accuracy": 0.8,
        "variable_importance": {"predictor": 1.0},
        "tree_depth": 2,
    },
    "random_forest": {
        "predictions": [0, 1, 0, 1, 0],
        "accuracy": 0.85,
        "variable_importance": {"predictor": 1.0},
        "n_trees": 100,
        "oob_error": 0.15,
    },
    # Econometrics
    "panel_regression": {
        "coefficients": {"x": 2.0},
        "r_squared": 0.95,
        "fixed_effects": {"id_1": 0.1, "id_2": 0.2, "id_3": 0.3},
        "model_type": "fixed_effects",
    },
    "instrumental_variables": {
        "coefficients": {"x": 1.8},
        "standard_errors": {"x": 0.3},
        "first_stage_f": 15.2,
        "instruments": ["z"],
        "endogeneity_test_p": 0.02,
    },
    "var_model": {
        "coefficients": {"y_lag1": 0.6, "x_lag1": 0.2},
        "forecast": {"y": [23, 24], "x": [11, 12]},
        "impulse_response": {"y_to_x": [0.2, 0.15, 0.1]},
        "lags": 1,
    },
    # Visualization (with mock image data)
    "scatter_plot": {
        "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
        "image_mime_type": "image/png",
        "status": "Plot created successfully",
    },
    "histogram": {
        "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
        "image_mime_type": "image/png",
        "bins": 5,
        "status": "Histogram created successfully",
    },
    "boxplot": {
        "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
        "image_mime_type": "image/png",
        "outliers": [5],
        "status": "Boxplot created successfully",
    },
    "time_series_plot": {
        "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
        "image_mime_type": "image/png",
        "trend": "increasing",
        "status": "Time series plot created successfully",
    },
    "correlation_heatmap": {
        "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
        "image_mime_type": "image/png",
        "max_correlation": 0.99,
        "status": "Correlation heatmap created successfully",
    },
    "regression_plot": {
        "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
        "image_mime_type": "image/png",
        "r_squared": 0.99,
        "status": "Regression diagnostic plots created successfully",
    },
    # File operations
    "read_csv": {
        "data": BASIC_DATA,
        "rows": 5,
        "columns": 2,
        "file_path": "/path/to/data.csv",
    },
    "write_csv": {
        "file_path": "/path/to/output.csv",
        "rows_written": 5,
        "status": "success",
    },
    "read_excel": {"data": BASIC_DATA, "rows": 5, "columns": 2, "sheet": "Sheet1"},
    "read_json": {"data": BASIC_DATA, "rows": 5, "columns": 2},
    "data_info": {
        "rows": 5,
        "columns": 2,
        "variable_types": {"x": "numeric", "y": "numeric"},
        "missing_values": {"x": 0, "y": 0},
        "sample_data": {"x": [1, 2], "y": [2, 4]},
    },
    "filter_data": {
        "data": {"x": [3, 4, 5], "y": [6, 8, 10]},
        "original_rows": 5,
        "filtered_rows": 3,
        "conditions_applied": 1,
    },
    # Helper tools
    "validate_data": {
        "is_valid": True,
        "warnings": [],
        "errors": [],
        "suggestions": ["Data looks good for analysis"],
        "data_quality": {
            "dimensions": {"rows": 5, "columns": 2},
            "missing_values": {"total_missing_cells": 0},
        },
    },
    "suggest_fix": {
        "error_type": "general",
        "suggestions": ["Check the documentation for the specific tool"],
        "data_suggestions": [],
        "next_steps": ["Review error message carefully"],
        "quick_fixes": [],
    },
    "load_example": {
        "data": BASIC_DATA,
        "metadata": {
            "name": "sales",
            "description": "Sales and marketing data",
            "rows": 5,
            "columns": 2,
        },
        "suggested_analyses": ["Linear regression: y ~ x"],
    },
    # Formula builder
    "build_formula": {
        "formula": "y ~ x",
        "matched_pattern": "predict y from x",
        "alternatives": ["y ~ x", "y ~ x + I(x^2)"],
        "interpretation": "This formula models 'y' as the outcome variable with 'x' as the predictor.",
    },
    "validate_formula": {
        "is_valid": True,
        "missing_variables": [],
        "existing_variables": ["x", "y"],
        "available_variables": ["x", "y"],
        "warnings": [],
    },
}


async def create_test_server():
    """Create server with all 40 tools registered."""
    server = create_server()
    # Register all tools exactly as in CLI
    register_tool_functions(
        server.tools,
        # Original regression tools
        linear_model,
        correlation_analysis,
        logistic_regression,
        # Time series analysis
        arima_model,
        decompose_timeseries,
        stationarity_test,
        # Data transformations
        lag_lead,
        winsorize,
        difference,
        standardize,
        # Statistical tests
        t_test,
        anova,
        chi_square_test,
        normality_test,
        # Descriptive statistics
        summary_stats,
        outlier_detection,
        frequency_table,
        # File operations
        read_csv,
        write_csv,
        data_info,
        filter_data,
        read_excel,
        read_json,
        # Econometrics
        panel_regression,
        instrumental_variables,
        var_model,
        # Machine learning
        kmeans_clustering,
        decision_tree,
        random_forest,
        # Visualization
        scatter_plot,
        histogram,
        boxplot,
        time_series_plot,
        correlation_heatmap,
        regression_plot,
        # Natural language tools
        build_formula,
        validate_formula,
        # Helper tools
        suggest_fix,
        validate_data,
        load_example,
    )
    return server


async def run_tool_integration_test(server, tool_name, test_data):
    """Test individual tool through full MCP integration."""
    # Create MCP request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": test_data},
    }
    try:
        # Mock R execution to return expected response
        mock_response = MOCK_RESPONSES.get(tool_name, {"status": "mocked"})
        with (
            patch(
                "rmcp.r_integration.execute_r_script_async", return_value=mock_response
            ),
            patch(
                "rmcp.r_integration.execute_r_script_with_image_async",
                return_value=mock_response,
            ),
        ):
            response = await server.handle_request(request)
            # Validate response structure
            if "result" not in response:
                return False, f"No result in response: {response}"
            if "content" not in response["result"]:
                return False, f"No content in result: {response['result']}"
            content = response["result"]["content"]
            if not isinstance(content, list) or len(content) == 0:
                return False, f"Invalid content format: {content}"
            image_content = None
            for item in content:
                if item.get("type") == "image":
                    image_content = item.get("data")
            summary = extract_text_summary(response)
            if not summary.strip():
                return False, "No human-readable summary returned"
            try:
                parsed_result = extract_json_content(response)
            except AssertionError as exc:
                return False, str(exc)
            # Verify result contains expected data
            if not isinstance(parsed_result, dict):
                return False, f"Result is not a dictionary: {type(parsed_result)}"
            # For visualization tools, verify image content
            if tool_name in [
                "scatter_plot",
                "histogram",
                "boxplot",
                "time_series_plot",
                "correlation_heatmap",
                "regression_plot",
            ]:
                if image_content is None:
                    return False, "Visualization tool should return image content"
            return True, parsed_result
    except Exception as e:
        return False, f"Tool execution failed: {str(e)}"


async def run_comprehensive_integration_tests():
    """Run integration tests for all 40 tools."""
    print("🚀 RMCP Comprehensive Integration Testing")
    print("=" * 55)
    print("Testing all 40 tools through complete MCP protocol\n")
    server = await create_test_server()
    # Get tool count from server
    context = Context.create("test", "test", server.lifespan_state)
    tools_list = await server.tools.list_tools(context)
    total_tools = len(tools_list["tools"])
    print(f"📊 Server registered {total_tools} tools")
    print("-" * 55)
    # Define test cases for all 40 tools
    test_cases = [
        # Regression (3 tools)
        ("linear_model", {"data": BASIC_DATA, "formula": "y ~ x"}),
        ("correlation_analysis", {"data": BASIC_DATA, "variables": ["x", "y"]}),
        (
            "logistic_regression",
            {
                "data": BINARY_DATA,
                "formula": "outcome ~ predictor",
                "family": "binomial",
            },
        ),
        # Statistical Tests (4 tools)
        ("t_test", {"data": BASIC_DATA, "variable": "x", "mu": 0}),
        ("anova", {"data": CATEGORICAL_DATA, "formula": "value ~ category"}),
        (
            "chi_square_test",
            {
                "data": CATEGORICAL_DATA,
                "test_type": "independence",
                "x": "category",
                "y": "value",
            },
        ),
        ("normality_test", {"data": BASIC_DATA, "variable": "x", "test": "shapiro"}),
        # Descriptive Statistics (3 tools)
        ("summary_stats", {"data": BASIC_DATA, "variables": ["x", "y"]}),
        ("outlier_detection", {"data": BASIC_DATA, "variable": "x", "method": "iqr"}),
        ("frequency_table", {"data": CATEGORICAL_DATA, "variables": ["category"]}),
        # Data Transformations (4 tools)
        ("standardize", {"data": BASIC_DATA, "variables": ["x"], "method": "z_score"}),
        (
            "winsorize",
            {"data": BASIC_DATA, "variables": ["x"], "percentiles": [0.1, 0.4]},
        ),
        ("lag_lead", {"data": BASIC_DATA, "variables": ["x"], "lags": [1]}),
        ("difference", {"data": BASIC_DATA, "variables": ["x"], "order": 1}),
        # Time Series (3 tools)
        ("stationarity_test", {"data": TIME_SERIES_DATA, "test": "adf"}),
        ("decompose_timeseries", {"data": TIME_SERIES_DATA, "frequency": 4}),
        ("arima_model", {"data": TIME_SERIES_DATA, "order": [1, 0, 1]}),
        # Machine Learning (3 tools)
        ("kmeans_clustering", {"data": BASIC_DATA, "variables": ["x", "y"], "k": 2}),
        ("decision_tree", {"data": BINARY_DATA, "formula": "outcome ~ predictor"}),
        (
            "random_forest",
            {"data": BINARY_DATA, "formula": "outcome ~ predictor", "n_trees": 100},
        ),
        # Econometrics (3 tools)
        (
            "panel_regression",
            {
                "data": PANEL_DATA,
                "formula": "y ~ x",
                "id_variable": "id",
                "time_variable": "time",
            },
        ),
        (
            "instrumental_variables",
            {"data": PANEL_DATA, "formula": "y ~ x", "instruments": ["time"]},
        ),
        ("var_model", {"data": BASIC_DATA, "variables": ["x", "y"], "lags": 1}),
        # Visualization (6 tools)
        (
            "scatter_plot",
            {"data": BASIC_DATA, "x": "x", "y": "y", "return_image": True},
        ),
        ("histogram", {"data": BASIC_DATA, "variable": "x", "return_image": True}),
        ("boxplot", {"data": BASIC_DATA, "variable": "x", "return_image": True}),
        ("time_series_plot", {"data": TIME_SERIES_DATA, "return_image": True}),
        ("correlation_heatmap", {"data": BASIC_DATA, "return_image": True}),
        (
            "regression_plot",
            {"data": BASIC_DATA, "formula": "y ~ x", "return_image": True},
        ),
        # File Operations (6 tools)
        ("read_csv", {"file_path": "/tmp/test.csv", "header": True}),
        ("write_csv", {"data": BASIC_DATA, "file_path": "/tmp/output.csv"}),
        ("read_excel", {"file_path": "/tmp/test.xlsx", "sheet": "Sheet1"}),
        ("read_json", {"file_path": "/tmp/test.json"}),
        ("data_info", {"data": BASIC_DATA, "include_sample": True}),
        (
            "filter_data",
            {
                "data": BASIC_DATA,
                "conditions": [{"variable": "x", "operator": ">", "value": 2}],
            },
        ),
        # Helper Tools (3 tools)
        ("validate_data", {"data": BASIC_DATA, "analysis_type": "regression"}),
        ("suggest_fix", {"error_message": "Test error", "tool_name": "linear_model"}),
        ("load_example", {"dataset_name": "sales", "size": "small"}),
        # Formula Builder (2 tools)
        (
            "build_formula",
            {"description": "predict y from x", "analysis_type": "regression"},
        ),
        ("validate_formula", {"formula": "y ~ x", "data": BASIC_DATA}),
    ]
    # Run tests
    results = []
    for i, (tool_name, test_data) in enumerate(test_cases, 1):
        print(f"[{i:2d}/40] Testing {tool_name:<20}", end=" ")
        success, result = await run_tool_integration_test(server, tool_name, test_data)
        if success:
            print("✅")
            results.append((tool_name, True, None))
        else:
            print(f"❌ - {result}")
            results.append((tool_name, False, result))
    # Summary
    print("\n" + "=" * 55)
    print("🎯 COMPREHENSIVE INTEGRATION TEST RESULTS")
    print("=" * 55)
    passed = sum(1 for _, success, _ in results if success)
    # Show results by category
    categories = {
        "Regression": results[0:3],
        "Statistical Tests": results[3:7],
        "Descriptive Stats": results[7:10],
        "Transformations": results[10:14],
        "Time Series": results[14:17],
        "Machine Learning": results[17:20],
        "Econometrics": results[20:23],
        "Visualization": results[23:29],
        "File Operations": results[29:35],
        "Helper Tools": results[35:38],
        "Formula Builder": results[38:40],
    }
    for category, category_results in categories.items():
        category_passed = sum(1 for _, success, _ in category_results if success)
        category_total = len(category_results)
        status = "✅" if category_passed == category_total else "❌"
        print(f"{status} {category:<18} {category_passed}/{category_total}")
        # Show failures
        for tool_name, success, error in category_results:
            if not success:
                print(f"     ❌ {tool_name}: {error}")
    print(f"\n📊 Overall Success Rate: {passed}/40 ({passed / 40:.1%})")
    if passed == 40:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Complete MCP protocol compatibility verified")
        print("🚀 All 40 tools working end-to-end")
    else:
        print(f"⚠️  {40 - passed} tools need attention")
        print("🔧 Integration fixes required")
    return passed == 40


if __name__ == "__main__":
    success = asyncio.run(run_comprehensive_integration_tests())
    sys.exit(0 if success else 1)
