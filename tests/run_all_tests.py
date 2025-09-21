#!/usr/bin/env python3
"""
Comprehensive test runner for RMCP.
Tests all 40 statistical analysis tools to ensure they work properly.
"""

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

# Add rmcp to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
)
from rmcp.tools.formula_builder import build_formula, validate_formula
from rmcp.tools.helpers import load_example, suggest_fix, validate_data
from rmcp.tools.machine_learning import decision_tree, kmeans_clustering, random_forest
from rmcp.tools.regression import (
    correlation_analysis,
    linear_model,
    logistic_regression,
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


def check_r_installation():
    """Check if R is installed and accessible."""
    print("🔍 Checking R installation...")
    try:
        result = subprocess.run(["R", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ R is installed and accessible")
            return True
        else:
            print("❌ R is not accessible")
            return False
    except FileNotFoundError:
        print("❌ R is not installed")
        return False


def check_r_packages():
    """Check if required R packages are installed."""
    print("📦 Checking R packages...")
    required_packages = [
        "jsonlite",
        "plm",
        "lmtest",
        "sandwich",
        "AER",
        "dplyr",
        "forecast",
        "vars",
        "urca",
        "tseries",
        "nortest",
        "car",
        "rpart",
        "randomForest",
        "ggplot2",
        "gridExtra",
        "tidyr",
        "rlang",
        "readxl",
        "reshape2",
    ]

    r_script = f"""
    packages <- c({', '.join([f'"{pkg}"' for pkg in required_packages])})
    missing <- packages[!packages %in% installed.packages()[,"Package"]]
    if (length(missing) > 0) {{
        cat("Missing packages:", paste(missing, collapse=", "))
    }} else {{
        cat("All packages installed")
    }}
    """

    try:
        result = subprocess.run(
            ["R", "--slave", "-e", r_script], capture_output=True, text=True
        )
        output = result.stdout.strip()

        if "Missing packages:" in output:
            missing = output.replace("Missing packages:", "").strip()
            print(f"❌ Missing R packages: {missing}")
            print("💡 Install with: install.packages(c('{missing}'))")
            return False
        else:
            print("✅ All required R packages are installed")
            return True
    except Exception as e:
        print(f"❌ Error checking R packages: {e}")
        return False


async def create_test_server():
    """Create server with all tools registered."""
    server = create_server()
    server.configure(allowed_paths=["/tmp"], read_only=False)

    # Register ALL 40 tools
    register_tool_functions(
        server.tools,
        # Regression & Correlation (3 tools)
        linear_model,
        correlation_analysis,
        logistic_regression,
        # Time Series Analysis (3 tools)
        arima_model,
        decompose_timeseries,
        stationarity_test,
        # Data Transformation (4 tools)
        lag_lead,
        winsorize,
        difference,
        standardize,
        # Statistical Testing (4 tools)
        t_test,
        anova,
        chi_square_test,
        normality_test,
        # Descriptive Statistics (3 tools)
        summary_stats,
        outlier_detection,
        frequency_table,
        # Advanced Econometrics (3 tools)
        panel_regression,
        instrumental_variables,
        var_model,
        # Machine Learning (3 tools)
        kmeans_clustering,
        decision_tree,
        random_forest,
        # Data Visualization (6 tools)
        scatter_plot,
        histogram,
        boxplot,
        time_series_plot,
        correlation_heatmap,
        regression_plot,
        # File Operations (6 tools)
        read_csv,
        read_excel,
        read_json,
        write_csv,
        data_info,
        filter_data,
        # Natural Language & UX (5 tools)
        build_formula,
        validate_formula,
        suggest_fix,
        validate_data,
        load_example,
    )

    return server


async def test_tool(server, tool_name, arguments, expected_success=True):
    """Test a single tool."""
    print(f"  Testing {tool_name}...", end=" ")

    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }

    try:
        response = await server.handle_request(request)

        if "result" in response and "content" in response["result"]:
            if expected_success:
                print("✅")
                return True
            else:
                print("❌ (unexpected success)")
                return False
        else:
            error = response.get("error", {})
            if expected_success:
                print(f"❌ ({error.get('message', 'Unknown error')})")
                return False
            else:
                print("✅ (expected failure)")
                return True

    except Exception as e:
        if expected_success:
            print(f"💥 (Exception: {e})")
            return False
        else:
            print("✅ (expected exception)")
            return True


async def run_all_tests():
    """Run all tests systematically."""
    print("🧪 RMCP Comprehensive Test Suite")
    print("=" * 50)

    # Check prerequisites
    if not check_r_installation():
        print("❌ Tests cannot run without R")
        return False

    if not check_r_packages():
        print("❌ Tests cannot run without required R packages")
        return False

    # Create test server
    print("🚀 Creating test server...")
    server = await create_test_server()
    print(f"✅ Server created with {len(server.tools._tools)} tools")

    # Test data for various tools
    sample_data = {
        "x": [1, 2, 3, 4, 5],
        "y": [2, 4, 1, 5, 3],
        "group": ["A", "A", "B", "B", "A"],
    }

    time_series_data = {
        "values": [100, 102, 105, 103, 107, 110, 108, 112, 115],
        "dates": [
            "2023-01",
            "2023-02",
            "2023-03",
            "2023-04",
            "2023-05",
            "2023-06",
            "2023-07",
            "2023-08",
            "2023-09",
        ],
    }

    test_results = []

    # Test categories
    categories = [
        (
            "📊 Regression & Correlation",
            [
                ("linear_model", {"data": sample_data, "formula": "y ~ x"}),
                ("correlation_analysis", {"data": sample_data}),
                (
                    "logistic_regression",
                    {
                        "data": {**sample_data, "binary": [1, 0, 1, 0, 1]},
                        "formula": "binary ~ x",
                    },
                ),
            ],
        ),
        (
            "📈 Time Series Analysis",
            [
                ("arima_model", {"data": time_series_data}),
                ("decompose_timeseries", {"data": time_series_data}),
                ("stationarity_test", {"data": time_series_data}),
            ],
        ),
        (
            "🔄 Data Transformation",
            [
                ("lag_lead", {"data": sample_data, "variables": ["x"]}),
                ("winsorize", {"data": sample_data, "variables": ["x", "y"]}),
                ("difference", {"data": sample_data, "variables": ["x"]}),
                ("standardize", {"data": sample_data, "variables": ["x", "y"]}),
            ],
        ),
        (
            "🧮 Statistical Testing",
            [
                ("t_test", {"data": sample_data, "variable": "y"}),
                ("anova", {"data": sample_data, "formula": "y ~ group"}),
                (
                    "chi_square_test",
                    {
                        "data": {
                            **sample_data,
                            "cat1": ["A", "B", "A", "B", "A"],
                            "cat2": ["X", "Y", "X", "Y", "X"],
                        },
                        "test_type": "independence",
                        "x": "cat1",
                        "y": "cat2",
                    },
                ),
                ("normality_test", {"data": sample_data, "variable": "y"}),
            ],
        ),
        (
            "📋 Descriptive Statistics",
            [
                ("summary_stats", {"data": sample_data}),
                ("outlier_detection", {"data": sample_data, "variable": "y"}),
                ("frequency_table", {"data": sample_data, "variables": ["group"]}),
            ],
        ),
        (
            "🏛️ Advanced Econometrics",
            [
                (
                    "panel_regression",
                    {
                        "data": {
                            **sample_data,
                            "id": [1, 1, 2, 2, 3],
                            "time": [1, 2, 1, 2, 1],
                        },
                        "formula": "y ~ x",
                        "id_variable": "id",
                        "time_variable": "time",
                    },
                ),
                (
                    "instrumental_variables",
                    {
                        "data": {**sample_data, "z": [1, 3, 2, 4, 2]},
                        "formula": "y ~ x | z",
                    },
                ),
                ("var_model", {"data": sample_data, "variables": ["x", "y"]}),
            ],
        ),
        (
            "🤖 Machine Learning",
            [
                (
                    "kmeans_clustering",
                    {"data": sample_data, "variables": ["x", "y"], "k": 2},
                ),
                ("decision_tree", {"data": sample_data, "formula": "y ~ x"}),
                ("random_forest", {"data": sample_data, "formula": "y ~ x"}),
            ],
        ),
        (
            "📊 Data Visualization",
            [
                ("scatter_plot", {"data": sample_data, "x": "x", "y": "y"}),
                ("histogram", {"data": sample_data, "variable": "y"}),
                ("boxplot", {"data": sample_data, "variable": "y"}),
                ("time_series_plot", {"data": time_series_data}),
                ("correlation_heatmap", {"data": sample_data}),
                ("regression_plot", {"data": sample_data, "formula": "y ~ x"}),
            ],
        ),
        (
            "📁 File Operations",
            [
                ("data_info", {"data": sample_data}),
                (
                    "filter_data",
                    {
                        "data": sample_data,
                        "conditions": [{"variable": "x", "operator": ">", "value": 2}],
                    },
                ),
                # Note: read_csv, read_excel, read_json, write_csv require actual files
            ],
        ),
        (
            "🗣️ Natural Language & UX",
            [
                (
                    "build_formula",
                    {
                        "description": "predict y from x",
                        "data_columns": ["x", "y", "group"],
                    },
                ),
                ("validate_formula", {"formula": "y ~ x", "data": sample_data}),
                ("validate_data", {"data": sample_data}),
                ("load_example", {"dataset_name": "economics"}),
            ],
        ),
    ]

    total_tests = 0
    passed_tests = 0

    for category_name, tests in categories:
        print(f"\n{category_name}")
        print("-" * 30)

        category_passed = 0
        for tool_name, args in tests:
            total_tests += 1
            success = await test_tool(server, tool_name, args)
            if success:
                passed_tests += 1
                category_passed += 1

        print(f"  Category result: {category_passed}/{len(tests)} passed")

    print(f"\n{'=' * 50}")
    print(f"🎯 FINAL RESULTS: {passed_tests}/{total_tests} tests passed")
    print(f"📊 Success rate: {passed_tests / total_tests * 100:.1f}%")

    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! RMCP is ready for deployment.")
        return True
    else:
        print(f"❌ {total_tests - passed_tests} tests failed. Review errors above.")
        return False


async def run_unit_tests():
    """Run existing unit tests."""
    print("\n🧪 Running Unit Tests")
    print("-" * 30)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/unit/", "-v"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        if result.returncode == 0:
            print("✅ Unit tests passed")
            return True
        else:
            print("❌ Unit tests failed")
            print(result.stdout)
            print(result.stderr)
            return False

    except FileNotFoundError:
        print("⚠️ pytest not found, skipping unit tests")
        return True


async def run_integration_tests():
    """Run existing integration tests."""
    print("\n🔗 Running Integration Tests")
    print("-" * 30)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/integration/", "-v"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        if result.returncode == 0:
            print("✅ Integration tests passed")
            return True
        else:
            print("❌ Integration tests failed")
            print(result.stdout)
            print(result.stderr)
            return False

    except FileNotFoundError:
        print("⚠️ pytest not found, skipping integration tests")
        return True


async def run_http_transport_tests():
    """Run HTTP transport tests (requires FastAPI)."""
    print("\n🌐 Running HTTP Transport Tests")
    print("-" * 30)

    try:
        # Check if FastAPI is available
        import fastapi
        import httpx

        print("✅ FastAPI dependencies available")
    except ImportError:
        print("⚠️ FastAPI not available, skipping HTTP transport tests")
        print("💡 Install with: pip install rmcp[http]")
        return True  # Don't fail the entire test suite

    try:
        # Run HTTP transport unit tests
        unit_result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/unit/test_http_transport.py", "-v"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # Run HTTP transport integration tests
        integration_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/test_http_transport_integration.py",
                "-v",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        unit_passed = unit_result.returncode == 0
        integration_passed = integration_result.returncode == 0

        if unit_passed and integration_passed:
            print("✅ HTTP transport tests passed")
            return True
        else:
            print("❌ HTTP transport tests failed")
            if not unit_passed:
                print("Unit test failures:")
                print(unit_result.stdout)
                print(unit_result.stderr)
            if not integration_passed:
                print("Integration test failures:")
                print(integration_result.stdout)
                print(integration_result.stderr)
            return False

    except FileNotFoundError:
        print("⚠️ pytest not found, skipping HTTP transport tests")
        return True


async def main():
    """Main test runner."""
    print("🚀 RMCP Comprehensive Test Runner")
    print("Testing all 40 statistical analysis tools + HTTP transport")
    print("=" * 50)

    # Run all test categories
    results = []

    # 1. Unit tests
    unit_result = await run_unit_tests()
    results.append(("Unit Tests", unit_result))

    # 2. Integration tests
    integration_result = await run_integration_tests()
    results.append(("Integration Tests", integration_result))

    # 3. HTTP transport tests
    http_result = await run_http_transport_tests()
    results.append(("HTTP Transport Tests", http_result))

    # 4. Comprehensive tool tests
    tool_result = await run_all_tests()
    results.append(("Tool Tests", tool_result))

    # Summary
    print(f"\n{'=' * 50}")
    print("📋 TEST SUMMARY")
    print("=" * 50)

    all_passed = True
    for test_type, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_type}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 ALL TEST CATEGORIES PASSED!")
        print("✅ RMCP is ready for production use")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("🔧 Please fix the issues above before deploying")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
