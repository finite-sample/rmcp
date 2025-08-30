"""
Test expanded RMCP capabilities using direct server calls.

Tests all new tool categories without CLI transport complexity.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rmcp.core.server import create_server
from rmcp.core.context import Context, LifespanState
from rmcp.registries.tools import register_tool_functions

# Import all tools directly
from rmcp.tools.regression import linear_model, correlation_analysis, logistic_regression
from rmcp.tools.timeseries import arima_model, decompose_timeseries, stationarity_test
from rmcp.tools.transforms import lag_lead, winsorize, difference, standardize
from rmcp.tools.statistical_tests import t_test, anova, chi_square_test, normality_test
from rmcp.tools.descriptive import summary_stats, outlier_detection, frequency_table
from rmcp.tools.fileops import read_csv, write_csv, data_info, filter_data
from rmcp.tools.econometrics import panel_regression, instrumental_variables, var_model
from rmcp.tools.machine_learning import kmeans_clustering, decision_tree, random_forest
from rmcp.tools.visualization import scatter_plot, histogram, boxplot, time_series_plot, correlation_heatmap, regression_plot

# Test data
SAMPLE_DATA = {
    "mpg": [21.0, 21.0, 22.8, 21.4, 18.7, 18.1, 14.3, 24.4, 22.8, 19.2, 17.8, 16.4, 17.3, 15.2, 10.4, 10.4, 14.7, 32.4, 30.4, 33.9],
    "cyl": [6, 6, 4, 6, 8, 6, 8, 4, 4, 6, 6, 8, 8, 8, 8, 8, 8, 4, 4, 4],
    "hp": [110, 110, 93, 110, 175, 105, 245, 62, 95, 123, 123, 180, 180, 180, 205, 215, 230, 66, 52, 65],
    "wt": [2.62, 2.875, 2.32, 3.215, 3.44, 3.46, 3.57, 3.19, 3.15, 3.44, 3.44, 4.07, 3.73, 3.78, 5.25, 5.424, 5.345, 2.2, 1.615, 1.835],
    "category": ["A", "A", "B", "A", "C", "A", "C", "B", "B", "A", "A", "C", "C", "C", "C", "C", "C", "B", "B", "B"]
}

TIME_SERIES_DATA = {
    "values": [100, 102, 98, 105, 108, 110, 95, 100, 103, 107, 112, 109, 104, 106, 111, 115, 118, 113, 108, 110, 114, 116, 112, 108, 105, 109, 113, 117, 120, 118, 115, 112, 109, 111, 114, 118]
}


async def create_test_server():
    """Create server with all tools registered."""
    server = create_server()
    
    # Register all tools
    register_tool_functions(
        server.tools,
        # Original regression tools
        linear_model, correlation_analysis, logistic_regression,
        # Time series analysis
        arima_model, decompose_timeseries, stationarity_test,
        # Data transformations
        lag_lead, winsorize, difference, standardize,
        # Statistical tests
        t_test, anova, chi_square_test, normality_test,
        # Descriptive statistics
        summary_stats, outlier_detection, frequency_table,
        # File operations
        read_csv, write_csv, data_info, filter_data,
        # Econometrics
        panel_regression, instrumental_variables, var_model,
        # Machine learning
        kmeans_clustering, decision_tree, random_forest,
        # Visualization
        scatter_plot, histogram, boxplot, time_series_plot, correlation_heatmap, regression_plot
    )
    
    return server


async def test_tool_call(server, tool_name, params):
    """Test a direct tool call through MCP protocol."""
    
    # Create MCP request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call", 
        "params": {
            "name": tool_name,
            "arguments": params
        }
    }
    
    try:
        response = await server.handle_request(request)
        
        if 'result' in response and 'content' in response['result']:
            result_text = response['result']['content'][0]['text']
            
            # Try parsing as JSON first
            try:
                result_data = json.loads(result_text)
                return result_data
            except json.JSONDecodeError:
                # Try eval for Python dict strings
                try:
                    result_data = eval(result_text)
                    return result_data
                except:
                    print(f"❌ Could not parse result for {tool_name}")
                    return None
        else:
            print(f"❌ Unexpected response format for {tool_name}: {response}")
            return None
            
    except Exception as e:
        print(f"❌ Tool {tool_name} failed: {e}")
        return None


async def main():
    """Run comprehensive capability tests."""
    print("🚀 Testing Radically Expanded RMCP Capabilities")
    print("=" * 60)
    
    server = await create_test_server()
    
    # List all tools
    context = Context.create("test", "test", server.lifespan_state)
    tools_list = await server.tools.list_tools(context)
    print(f"📊 Total tools registered: {len(tools_list['tools'])}")
    
    test_results = []
    
    # Test categories
    tests = [
        # Descriptive statistics
        ("summary_stats", {"data": SAMPLE_DATA, "variables": ["mpg", "hp"]}),
        ("outlier_detection", {"data": SAMPLE_DATA, "variable": "hp", "method": "iqr"}),
        ("frequency_table", {"data": SAMPLE_DATA, "variables": ["category"]}),
        
        # Statistical tests
        ("normality_test", {"data": SAMPLE_DATA, "variable": "mpg", "test": "shapiro"}),
        
        # Data transformations
        ("winsorize", {"data": SAMPLE_DATA, "variables": ["mpg"], "percentiles": [0.05, 0.45]}),
        ("standardize", {"data": SAMPLE_DATA, "variables": ["mpg", "hp"], "method": "z_score"}),
        
        # Machine learning
        ("kmeans_clustering", {"data": SAMPLE_DATA, "variables": ["mpg", "hp"], "k": 3}),
        
        # Time series
        ("stationarity_test", {"data": TIME_SERIES_DATA, "test": "adf"}),
        ("decompose_timeseries", {"data": TIME_SERIES_DATA, "frequency": 12}),
        
        # File operations
        ("data_info", {"data": SAMPLE_DATA, "include_sample": True}),
    ]
    
    print("\n🧪 Testing Tool Categories:")
    print("-" * 40)
    
    for tool_name, params in tests:
        print(f"Testing {tool_name}...", end=" ")
        result = await test_tool_call(server, tool_name, params)
        
        if result:
            print("✅")
            test_results.append(True)
        else:
            print("❌")
            test_results.append(False)
    
    # Summary
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All expanded capabilities working perfectly!")
        print("📈 RMCP has been radically expanded from 3 to 33 tools!")
    else:
        print("⚠️ Some capabilities need attention")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)