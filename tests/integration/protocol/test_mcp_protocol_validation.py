#!/usr/bin/env python3
"""
MCP Protocol validation tests for all RMCP tools.
Tests complete MCP protocol integration flow for each tool with mocked R responses,
ensuring all tool paths work end-to-end without requiring R environment.
"""
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio

# Add rmcp to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from rmcp.core.context import Context
from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions

# Import all tools
from rmcp.tools.descriptive import frequency_table, outlier_detection, summary_stats
from rmcp.tools.econometrics import instrumental_variables, panel_regression, var_model
from rmcp.tools.fileops import (
    data_info,
    filter_data,
    read_csv,
    read_excel,
    read_json,
    write_csv,
    write_excel,
    write_json,
)
from rmcp.tools.formula_builder import build_formula, validate_formula
from rmcp.tools.helpers import load_example, suggest_fix, validate_data
from rmcp.tools.machine_learning import decision_tree, kmeans_clustering, random_forest
from rmcp.tools.regression import (
    correlation_analysis,
    linear_model,
    logistic_regression,
)
from rmcp.tools.statistical_tests import (
    anova,
    chi_square_test,
    normality_test,
    t_test,
)
from rmcp.tools.timeseries import (
    arima_model,
    decompose_timeseries,
    stationarity_test,
)
from rmcp.tools.transforms import (
    difference,
    lag_lead,
    standardize,
    winsorize,
)
from rmcp.tools.visualization import (
    boxplot,
    correlation_heatmap,
    histogram,
    regression_plot,
    scatter_plot,
    time_series_plot,
)
from tests.utils import extract_json_content, extract_text_summary

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
        "n_obs": 5,
        "degrees_freedom": 3,
        "formula": "y ~ x",
        "variables": ["x", "y"],
    },
    "correlation_analysis": {
        "correlation_matrix": {"x": [1.0, 0.99], "y": [0.99, 1.0]},
        "p_values": {"x": [0.0, 0.001], "y": [0.001, 0.0]},
        "n_obs": 5,
        "method": "pearson",
        "variables": ["x", "y"],
    },
    "logistic_regression": {
        "coefficients": {"(Intercept)": -1.0, "predictor": 0.5},
        "odds_ratios": {"(Intercept)": 0.37, "predictor": 1.65},
        "p_values": {"(Intercept)": 0.1, "predictor": 0.05},
        "accuracy": 0.8,
        "deviance": 5.2,
        "aic": 7.4,
        "n_obs": 5,
    },
    # Statistical tests
    "t_test": {
        "statistic": 2.5,
        "p_value": 0.03,
        "confidence_interval": {"lower": 0.1, "upper": 3.9, "level": 0.95},
        "mean": 2.0,
        "alternative": "two.sided",
        "test_type": "one_sample",
        "variable": "x",
    },
    "anova": {
        "f_statistic": 15.2,
        "p_value": 0.01,
        "df_between": 2,
        "df_within": 12,
        "sum_sq": [100, 50],
        "mean_sq": [50, 4.2],
        "anova_table": {"p_value": {"1": 0.01}},
        "formula": "y ~ group",
    },
    "chi_square_test": {
        "statistic": 8.5,
        "p_value": 0.02,
        "df": 2,
        "test_type": "independence",
        "observed": [[10, 5], [8, 12]],
        "expected": [[9, 6], [9, 11]],
        "expected_frequencies": [[9, 6], [9, 11]],
    },
    "normality_test": {
        "test": "shapiro",
        "statistic": 0.95,
        "p_value": 0.7,
        "is_normal": True,
        "interpretation": "Data appears normally distributed",
        "test_name": "Shapiro-Wilk",
        "variable": "x",
    },
    # Add other mock responses with required fields...
    "summary_stats": {
        "statistics": {
            "x": {"mean": 3.0, "sd": 1.58, "min": 1, "max": 5},
            "y": {"mean": 6.0, "sd": 3.16, "min": 2, "max": 10},
        },
        "n_obs": 5,
        "variables": ["x", "y"],
    },
    "outlier_detection": {
        "outliers": [5],
        "outlier_indices": [4],
        "method": "iqr",
        "threshold": 1.5,
        "n_outliers": 1,
        "variable": "x",
        "n_obs": 5,
    },
    "frequency_table": {
        "frequency_tables": {"category": {"A": 3, "B": 2}},
        "percentages": {"category": {"A": 60.0, "B": 40.0}},
        "n_total": 5,
        "variables": ["category"],
    },
}


@pytest_asyncio.fixture
async def test_server():
    """Create server with all tools registered."""
    server = create_server()
    # Register all tools exactly as in CLI
    register_tool_functions(
        server.tools,
        # Regression tools
        linear_model,
        correlation_analysis,
        logistic_regression,
        # Statistical tests
        t_test,
        anova,
        chi_square_test,
        normality_test,
        # Descriptive statistics
        summary_stats,
        outlier_detection,
        frequency_table,
        # Data transformations
        lag_lead,
        winsorize,
        difference,
        standardize,
        # Time series analysis
        arima_model,
        decompose_timeseries,
        stationarity_test,
        # Machine learning
        kmeans_clustering,
        decision_tree,
        random_forest,
        # Econometrics
        panel_regression,
        instrumental_variables,
        var_model,
        # Visualization
        scatter_plot,
        histogram,
        boxplot,
        time_series_plot,
        correlation_heatmap,
        regression_plot,
        # File operations
        read_csv,
        write_csv,
        data_info,
        filter_data,
        read_excel,
        read_json,
        write_csv,
        write_excel,
        write_json,
        # Natural language tools
        build_formula,
        validate_formula,
        # Helper tools
        suggest_fix,
        validate_data,
        load_example,
    )
    return server


@pytest.fixture
def mock_r_patches():
    """Create mock patches for R execution."""
    patches = [
        patch(
            "rmcp.tools.statistical_tests.execute_r_script_async",
            side_effect=lambda r_script, params: MOCK_RESPONSES.get(
                params.get("tool_name", "generic"), {"status": "mocked"}
            ),
        ),
        patch(
            "rmcp.tools.descriptive.execute_r_script_async",
            side_effect=lambda r_script, params: MOCK_RESPONSES.get(
                params.get("tool_name", "generic"), {"status": "mocked"}
            ),
        ),
        patch(
            "rmcp.tools.regression.execute_r_script_async",
            side_effect=lambda r_script, params: MOCK_RESPONSES.get(
                params.get("tool_name", "generic"), {"status": "mocked"}
            ),
        ),
        # Add other patches as needed
    ]
    return patches


async def run_tool_protocol_test(server, tool_name, test_data, mock_patches):
    """Test individual tool through MCP protocol."""
    # Create MCP request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {**test_data, "tool_name": tool_name},
        },
    }

    try:
        # Apply mock patches and execute
        with ExitStack() as stack:
            for patch_obj in mock_patches:
                stack.enter_context(patch_obj)

            response = await server.handle_request(request)

            # Validate response structure
            if "result" not in response:
                return False, f"No result in response: {response}"
            if "content" not in response["result"]:
                return False, f"No content in result: {response['result']}"

            content = response["result"]["content"]
            if not isinstance(content, list) or len(content) == 0:
                return False, f"Invalid content format: {content}"

            # Verify we get human-readable summary
            summary = extract_text_summary(response)
            if not summary.strip():
                return False, "No human-readable summary returned"

            return True, "Protocol validation successful"

    except Exception as e:
        return False, f"Tool execution failed: {str(e)}"


# Individual test cases for different tool categories
@pytest.mark.asyncio
async def test_regression_tools_protocol(test_server, mock_r_patches):
    """Test regression tools MCP protocol compliance."""
    test_cases = [
        ("linear_model", {"data": BASIC_DATA, "formula": "y ~ x"}),
        ("correlation_analysis", {"data": BASIC_DATA, "variables": ["x", "y"]}),
        (
            "logistic_regression",
            {"data": BINARY_DATA, "formula": "outcome ~ predictor"},
        ),
    ]

    for tool_name, test_data in test_cases:
        success, result = await run_tool_protocol_test(
            test_server, tool_name, test_data, mock_r_patches
        )
        assert success, f"{tool_name} protocol test failed: {result}"


@pytest.mark.asyncio
async def test_statistical_tests_protocol(test_server, mock_r_patches):
    """Test statistical tests MCP protocol compliance."""
    test_cases = [
        ("t_test", {"data": BASIC_DATA, "variable": "x"}),
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
        ("normality_test", {"data": BASIC_DATA, "variable": "x"}),
    ]

    for tool_name, test_data in test_cases:
        success, result = await run_tool_protocol_test(
            test_server, tool_name, test_data, mock_r_patches
        )
        assert success, f"{tool_name} protocol test failed: {result}"


@pytest.mark.asyncio
async def test_descriptive_stats_protocol(test_server, mock_r_patches):
    """Test descriptive statistics MCP protocol compliance."""
    test_cases = [
        ("summary_stats", {"data": BASIC_DATA, "variables": ["x", "y"]}),
        ("outlier_detection", {"data": BASIC_DATA, "variable": "x"}),
        ("frequency_table", {"data": CATEGORICAL_DATA, "variables": ["category"]}),
    ]

    for tool_name, test_data in test_cases:
        success, result = await run_tool_protocol_test(
            test_server, tool_name, test_data, mock_r_patches
        )
        assert success, f"{tool_name} protocol test failed: {result}"


# Add a comprehensive test that validates the overall protocol
@pytest.mark.asyncio
async def test_mcp_protocol_comprehensive_validation(test_server, mock_r_patches):
    """Comprehensive MCP protocol validation across all tool categories."""
    # Test server basic functionality
    context = Context.create("test", "test", test_server.lifespan_state)
    tools_list = await test_server.tools.list_tools(context)

    # Verify we have tools registered
    assert len(tools_list["tools"]) > 0, "No tools registered in server"

    # Test basic MCP protocol compliance with a simple tool
    success, result = await run_tool_protocol_test(
        test_server,
        "summary_stats",
        {"data": BASIC_DATA, "variables": ["x", "y"]},
        mock_r_patches,
    )
    assert success, f"Basic MCP protocol test failed: {result}"
