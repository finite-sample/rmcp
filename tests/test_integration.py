"""
Integration tests for RMCP tools.

These tests verify that the tools work correctly with real R execution.
"""

import pytest
import json
from rmcp.tools import mcp
from rmcp.tools.common import RExecutionError


class TestToolIntegration:
    """Integration tests for RMCP tools."""
    
    def test_linear_model_integration(self):
        """Test linear_model tool with real data."""
        # Get the linear_model function from registered tools
        linear_model_func = mcp.tools["linear_model"]["function"]
        
        # Perfect linear relationship: y = 2*x + 1
        data = {
            "x": [1, 2, 3, 4, 5],
            "y": [3, 5, 7, 9, 11]
        }
        formula = "y ~ x"
        
        result = linear_model_func(formula=formula, data=data, robust=False)
        
        # Verify structure
        assert isinstance(result, dict)
        assert "coefficients" in result
        assert "std_errors" in result
        assert "r_squared" in result
        
        # Verify coefficients (approximate due to floating point)
        coeffs = result["coefficients"]
        assert "(Intercept)" in coeffs
        assert "x" in coeffs
        assert abs(coeffs["(Intercept)"] - 1.0) < 0.01  # Intercept ≈ 1
        assert abs(coeffs["x"] - 2.0) < 0.01  # Slope ≈ 2
        
        # Perfect fit should have R² = 1
        assert abs(result["r_squared"] - 1.0) < 0.01
    
    def test_correlation_integration(self):
        """Test correlation tool with real data."""
        correlation_func = mcp.tools["correlation"]["function"]
        
        # Perfect positive correlation
        data = {
            "x": [1, 2, 3, 4, 5],
            "y": [2, 4, 6, 8, 10]
        }
        
        result = correlation_func(data=data, var1="x", var2="y", method="pearson")
        
        assert isinstance(result, dict)
        assert "correlation" in result
        assert "method" in result
        assert abs(result["correlation"] - 1.0) < 0.01  # Perfect correlation
        assert result["method"] == "pearson"
    
    def test_group_by_integration(self):
        """Test group_by tool with real data."""
        group_by_func = mcp.tools["group_by"]["function"]
        
        data = {
            "group": ["A", "A", "B", "B", "C", "C"],
            "value": [10, 20, 30, 40, 50, 60]
        }
        
        result = group_by_func(
            data=data,
            group_col="group",
            summarise_col="value",
            stat="mean"
        )
        
        assert isinstance(result, dict)
        assert "summary" in result
        
        # Verify grouped results
        summary = result["summary"]
        assert len(summary) == 3  # Three groups
        
        # Check that we have the expected groups (order may vary)
        groups = {row["group"]: row["s_value"] for row in summary}
        assert abs(groups["A"] - 15.0) < 0.01  # Mean of [10, 20]
        assert abs(groups["B"] - 35.0) < 0.01  # Mean of [30, 40]
        assert abs(groups["C"] - 55.0) < 0.01  # Mean of [50, 60]
    
    def test_panel_model_integration(self):
        """Test panel_model tool with real data."""
        panel_model_func = mcp.tools["panel_model"]["function"]
        
        # Simple panel data - 2 individuals over 3 time periods
        data = {
            "individual": [1, 1, 1, 2, 2, 2],
            "time": [1, 2, 3, 1, 2, 3],
            "y": [10, 12, 14, 20, 22, 24],
            "x": [5, 6, 7, 10, 11, 12]
        }
        
        result = panel_model_func(
            formula="y ~ x",
            data=data,
            index=["individual", "time"],
            effect="individual",
            model="within"
        )
        
        assert isinstance(result, dict)
        assert "coefficients" in result
        assert "model_type" in result
        assert "effect_type" in result
        assert result["model_type"] == "within"
        assert result["effect_type"] == "individual"
    
    def test_iv_regression_integration(self):
        """Test iv_regression tool with real data."""
        iv_regression_func = mcp.tools["iv_regression"]["function"]
        
        # Simple instrumental variables setup
        # y = x + error, z is instrument for x
        data = {
            "y": [10, 12, 14, 16, 18],
            "x": [5, 6, 7, 8, 9], 
            "z": [2.5, 3.0, 3.5, 4.0, 4.5]  # z = x/2
        }
        
        result = iv_regression_func(
            formula="y ~ x | z",  # y on x, using z as instrument
            data=data
        )
        
        assert isinstance(result, dict)
        assert "coefficients" in result
        assert "std_errors" in result
        assert "r_squared" in result
    
    def test_diagnostics_integration(self):
        """Test diagnostics tool with real data."""
        diagnostics_func = mcp.tools["diagnostics"]["function"]
        
        data = {
            "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "y": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
        }
        
        result = diagnostics_func(
            formula="y ~ x",
            data=data,
            tests=["bp", "dw"]  # Breusch-Pagan and Durbin-Watson
        )
        
        assert isinstance(result, dict)
        # The exact structure depends on the R diagnostic functions
        # but we expect some test results
    
    def test_error_handling_integration(self):
        """Test error handling with invalid inputs."""
        linear_model_func = mcp.tools["linear_model"]["function"]
        
        # Invalid formula should raise an error
        with pytest.raises(RExecutionError):
            linear_model_func(
                formula="invalid formula syntax @#$",
                data={"x": [1, 2, 3]},
                robust=False
            )
        
        # Missing variables should raise an error
        with pytest.raises(RExecutionError):
            linear_model_func(
                formula="y ~ missing_variable",
                data={"x": [1, 2, 3]},
                robust=False
            )


class TestMCPServer:
    """Test MCP server functionality."""
    
    def test_tools_registered(self):
        """Test that all expected tools are registered."""
        expected_tools = [
            "linear_model",
            "panel_model", 
            "iv_regression",
            "diagnostics",
            "correlation",
            "group_by",
            "analyze_csv"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in mcp.tools, f"Tool {tool_name} not registered"
            assert "function" in mcp.tools[tool_name]
            assert "description" in mcp.tools[tool_name]
            assert "schema" in mcp.tools[tool_name]
    
    def test_tool_schemas(self):
        """Test that tool schemas are properly defined."""
        for tool_name, tool_info in mcp.tools.items():
            schema = tool_info["schema"]
            
            # Basic schema structure
            assert "type" in schema
            assert schema["type"] == "object"
            
            if "properties" in schema:
                assert isinstance(schema["properties"], dict)
                
            # Check required fields if present
            if "required" in schema:
                assert isinstance(schema["required"], list)
                for required_field in schema["required"]:
                    assert required_field in schema["properties"]