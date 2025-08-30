"""
Test the dramatically expanded RMCP capabilities.

Tests all the new tool categories to verify the radical expansion works.
"""

import pytest
import json
import subprocess
from pathlib import Path

# Test data for all scenarios
SAMPLE_DATA = {
    "mpg": [21.0, 21.0, 22.8, 21.4, 18.7, 18.1, 14.3, 24.4, 22.8, 19.2, 17.8, 16.4, 17.3, 15.2, 10.4, 10.4, 14.7, 32.4, 30.4, 33.9],
    "cyl": [6, 6, 4, 6, 8, 6, 8, 4, 4, 6, 6, 8, 8, 8, 8, 8, 8, 4, 4, 4],
    "disp": [160.0, 160.0, 108.0, 258.0, 360.0, 225.0, 360.0, 146.7, 140.8, 167.6, 167.6, 275.8, 275.8, 275.8, 472.0, 460.0, 440.0, 78.7, 75.7, 71.1],
    "hp": [110, 110, 93, 110, 175, 105, 245, 62, 95, 123, 123, 180, 180, 180, 205, 215, 230, 66, 52, 65],
    "wt": [2.62, 2.875, 2.32, 3.215, 3.44, 3.46, 3.57, 3.19, 3.15, 3.44, 3.44, 4.07, 3.73, 3.78, 5.25, 5.424, 5.345, 2.2, 1.615, 1.835],
    "gear": [4, 4, 4, 3, 3, 3, 3, 4, 4, 4, 4, 3, 3, 3, 3, 3, 3, 4, 4, 4],
    "category": ["A", "A", "B", "A", "C", "A", "C", "B", "B", "A", "A", "C", "C", "C", "C", "C", "C", "B", "B", "B"]
}

TIME_SERIES_DATA = {
    "values": [100, 102, 98, 105, 108, 110, 95, 100, 103, 107, 112, 109, 104, 106, 111, 115, 118, 113, 108, 110],
    "dates": ["2022-01-01", "2022-02-01", "2022-03-01", "2022-04-01", "2022-05-01", "2022-06-01", "2022-07-01", "2022-08-01", "2022-09-01", "2022-10-01", "2022-11-01", "2022-12-01", "2023-01-01", "2023-02-01", "2023-03-01", "2023-04-01", "2023-05-01", "2023-06-01", "2023-07-01", "2023-08-01"]
}

PANEL_DATA = {
    "id": [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4],
    "time": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3],
    "y": [10, 12, 14, 8, 9, 11, 15, 17, 19, 7, 8, 10],
    "x": [2, 3, 4, 1, 2, 3, 4, 5, 6, 1, 1, 2]
}


def run_mcp_test(tool_name, params):
    """Run MCP tool test using stdio transport."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": params
        }
    }
    
    # Start the server process
    process = subprocess.Popen(
        ["python", "-m", "src.rmcp.cli", "start"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=Path.cwd()
    )
    
    try:
        # Send request
        request_json = json.dumps(request) + "\n"
        stdout, stderr = process.communicate(input=request_json, timeout=30)
        
        # Parse response
        lines = stdout.strip().split('\n')
        for line in lines:
            if line.strip() and not line.startswith('['):
                try:
                    response = json.loads(line)
                    if "result" in response:
                        return response["result"]
                    elif "error" in response:
                        raise Exception(f"MCP Error: {response['error']}")
                except json.JSONDecodeError:
                    continue
        
        raise Exception(f"No valid response. stdout: {stdout}, stderr: {stderr}")
    
    finally:
        if process.poll() is None:
            process.terminate()


def test_time_series_capabilities():
    """Test time series analysis tools."""
    
    # Test stationarity
    result = run_mcp_test("stationarity_test", {
        "data": TIME_SERIES_DATA,
        "test": "adf"
    })
    assert "test_name" in result
    
    # Test decomposition  
    result = run_mcp_test("decompose_timeseries", {
        "data": TIME_SERIES_DATA,
        "frequency": 12,
        "type": "additive"
    })
    assert "components" in result


def test_data_transformation_capabilities():
    """Test data transformation tools."""
    
    # Test winsorization
    result = run_mcp_test("winsorize", {
        "data": SAMPLE_DATA,
        "variables": ["mpg"],
        "percentiles": [0.05, 0.95]
    })
    assert "winsorized_data" in result
    
    # Test standardization
    result = run_mcp_test("standardize", {
        "data": SAMPLE_DATA,
        "variables": ["mpg", "hp"],
        "method": "z_score"
    })
    assert "standardized_data" in result


def test_statistical_test_capabilities():
    """Test statistical hypothesis testing tools."""
    
    # Test t-test
    result = run_mcp_test("t_test", {
        "data": SAMPLE_DATA,
        "variable": "mpg",
        "group": "category"
    })
    assert "test_type" in result
    assert "p_value" in result
    
    # Test ANOVA
    result = run_mcp_test("anova", {
        "data": SAMPLE_DATA,
        "formula": "mpg ~ cyl + hp"
    })
    assert "anova_table" in result


def test_descriptive_capabilities():
    """Test descriptive statistics tools."""
    
    # Test summary statistics
    result = run_mcp_test("summary_stats", {
        "data": SAMPLE_DATA,
        "variables": ["mpg", "hp"],
        "group_by": "category"
    })
    assert "statistics" in result
    assert result["grouped"] == True
    
    # Test outlier detection
    result = run_mcp_test("outlier_detection", {
        "data": SAMPLE_DATA,
        "variable": "hp",
        "method": "iqr"
    })
    assert "outlier_indices" in result


def test_file_operations_capabilities():
    """Test file operations tools."""
    
    # Test data info
    result = run_mcp_test("data_info", {
        "data": SAMPLE_DATA,
        "include_sample": True
    })
    assert "dimensions" in result
    assert "variables" in result
    assert result["dimensions"]["rows"] == 20


def test_econometrics_capabilities():
    """Test econometric analysis tools."""
    
    # Test panel regression
    result = run_mcp_test("panel_regression", {
        "data": PANEL_DATA,
        "formula": "y ~ x",
        "id_variable": "id",
        "time_variable": "time",
        "model": "within"
    })
    assert "coefficients" in result
    assert "model_type" in result


def test_machine_learning_capabilities():
    """Test machine learning tools."""
    
    # Test k-means clustering
    result = run_mcp_test("kmeans_clustering", {
        "data": SAMPLE_DATA,
        "variables": ["mpg", "hp"],
        "k": 3
    })
    assert "cluster_assignments" in result
    assert "cluster_centers" in result
    
    # Test decision tree
    result = run_mcp_test("decision_tree", {
        "data": SAMPLE_DATA,
        "formula": "category ~ mpg + hp",
        "type": "classification"
    })
    assert "performance" in result
    assert "variable_importance" in result


def test_comprehensive_workflow():
    """Test a comprehensive analysis workflow using multiple tool categories."""
    
    # Step 1: Get data info
    data_info = run_mcp_test("data_info", {"data": SAMPLE_DATA})
    assert data_info["dimensions"]["rows"] == 20
    
    # Step 2: Summary stats
    summary = run_mcp_test("summary_stats", {
        "data": SAMPLE_DATA,
        "variables": ["mpg", "hp"]
    })
    assert "statistics" in summary
    
    # Step 3: Correlation analysis
    correlation = run_mcp_test("correlation_analysis", {
        "data": SAMPLE_DATA,
        "variables": ["mpg", "hp", "wt"]
    })
    assert "correlation_matrix" in correlation
    
    # Step 4: Linear regression
    regression = run_mcp_test("linear_model", {
        "data": SAMPLE_DATA,
        "formula": "mpg ~ hp + wt"
    })
    assert "coefficients" in regression
    assert "r_squared" in regression
    
    # Step 5: Statistical test
    normality = run_mcp_test("normality_test", {
        "data": SAMPLE_DATA,
        "variable": "mpg",
        "test": "shapiro"
    })
    assert "test_name" in normality
    assert "p_value" in normality


if __name__ == "__main__":
    # Run all tests
    test_functions = [
        test_time_series_capabilities,
        test_data_transformation_capabilities, 
        test_statistical_test_capabilities,
        test_descriptive_capabilities,
        test_file_operations_capabilities,
        test_econometrics_capabilities,
        test_machine_learning_capabilities,
        test_comprehensive_workflow
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            print(f"Running {test_func.__name__}...")
            test_func()
            print(f"✅ {test_func.__name__} PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} FAILED: {e}")
            failed += 1
    
    print(f"\n🎯 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🚀 All expanded capabilities working perfectly!")
    else:
        print("⚠️ Some tests failed - review implementation")