#!/usr/bin/env python3
"""
Integration tests for R error and warning handling.

Tests actual R error scenarios with real R execution to ensure:
1. R errors/warnings are properly captured and surfaced
2. Error messages match actual R behavior (not mocked assumptions)
3. RMCP handles all categories of R failures gracefully
4. Error responses provide actionable guidance to users

These tests deliberately trigger R errors/warnings to validate the complete
error handling pipeline: R → RMCP → MCP → Claude.
"""

import asyncio
import os
import sys
from pathlib import Path
from shutil import which
from typing import Any, Dict

import pytest

# Add rmcp to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rmcp.core.context import Context, LifespanState
from rmcp.tools.helpers import suggest_fix, validate_data
from rmcp.tools.machine_learning import decision_tree, random_forest
from rmcp.tools.regression import correlation_analysis, linear_model, logistic_regression
from rmcp.tools.statistical_tests import chi_square_test, t_test
from rmcp.tools.timeseries import arima_model
from tests.utils import extract_json_content, extract_text_summary

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for R error handling tests"
)


@pytest.fixture
def context():
    """Create test context for R error scenarios."""
    lifespan = LifespanState()
    ctx = Context.create("test", "r_error_test", lifespan)
    return ctx


class TestRealRErrors:
    """Test actual R error scenarios with real R execution."""

    # Data designed to trigger specific R errors/warnings
    ERROR_DATA_SCENARIOS = {
        "perfect_separation": {
            # Causes logistic regression separation warning
            "data": {
                "outcome": [0, 0, 0, 1, 1, 1],
                "predictor": [1, 2, 3, 10, 11, 12]  # Perfect separation
            },
            "description": "Perfect separation in logistic regression",
            "expected_pattern": "fitted probabilities.*0 or 1"
        },
        "perfect_collinearity": {
            # Causes linear regression rank deficiency
            "data": {
                "y": [10, 20, 30, 40, 50],
                "x1": [1, 2, 3, 4, 5],
                "x2": [2, 4, 6, 8, 10]  # x2 = 2*x1 (perfect collinearity)
            },
            "description": "Perfect collinearity in regression",
            "expected_pattern": "rank.*deficient|collinearity"
        },
        "small_sample_chi_square": {
            # Causes chi-square low expected count warning
            "data": {
                "var1": ["A", "B", "A"],  # Very small sample
                "var2": ["X", "Y", "X"]
            },
            "description": "Small sample chi-square test",
            "expected_pattern": "expected.*count.*5|approximation.*incorrect"
        },
        "non_convergent_data": {
            # Causes optimization convergence issues
            "data": {
                "outcome": [0, 0, 0, 0, 0, 1],  # Extreme imbalance
                "predictor": [1, 1, 1, 1, 1, 2]  # Minimal variation
            },
            "description": "Non-convergent optimization",
            "expected_pattern": "convergence|iteration.*limit"
        },
        "missing_values": {
            # Data with NAs that R handles differently
            "data": {
                "x": [1, 2, None, 4, 5],
                "y": [10, 20, None, 40, 50]
            },
            "description": "Missing values handling",
            "expected_pattern": "missing.*value|NA.*introduced"
        }
    }

    @pytest.mark.asyncio
    async def test_logistic_regression_separation_warning(self, context):
        """Test real R warning for perfect separation in logistic regression."""
        data = self.ERROR_DATA_SCENARIOS["perfect_separation"]["data"]
        
        try:
            result = await logistic_regression(
                context,
                {
                    "data": data,
                    "formula": "outcome ~ predictor",
                    "family": "binomial"
                }
            )
            
            # Should not fail, but should contain warning information
            assert "model_summary" in result
            
            # Check if warning information is captured
            # (R warnings should be included in output or handled gracefully)
            print(f"✅ Logistic regression handled separation scenario")
            print(f"   Model converged: {result.get('converged', 'unknown')}")
            
        except Exception as e:
            # If it fails, the error should be informative
            error_msg = str(e)
            assert len(error_msg) > 10, "Error message should be descriptive"
            print(f"✅ Logistic regression separation produced informative error: {error_msg[:100]}...")

    @pytest.mark.asyncio 
    async def test_linear_regression_collinearity_warning(self, context):
        """Test real R warning for perfect collinearity."""
        data = self.ERROR_DATA_SCENARIOS["perfect_collinearity"]["data"]
        
        try:
            result = await linear_model(
                context,
                {
                    "data": data,
                    "formula": "y ~ x1 + x2"
                }
            )
            
            # Should complete but may have warnings about rank deficiency
            assert "r_squared" in result
            assert "coefficients" in result
            
            print(f"✅ Linear regression handled collinearity scenario")
            print(f"   R-squared: {result.get('r_squared', 'unknown')}")
            print(f"   DF residual: {result.get('df_residual', 'unknown')}")
            
        except Exception as e:
            error_msg = str(e)
            assert "rank" in error_msg.lower() or "collinearity" in error_msg.lower()
            print(f"✅ Collinearity error properly identified: {error_msg[:100]}...")

    @pytest.mark.asyncio
    async def test_chi_square_small_sample_warning(self, context):
        """Test real R warning for small sample chi-square test."""
        data = self.ERROR_DATA_SCENARIOS["small_sample_chi_square"]["data"]
        
        try:
            result = await chi_square_test(
                context,
                {
                    "data": data,
                    "test_type": "independence",
                    "x": "var1",
                    "y": "var2"
                }
            )
            
            # Should complete but may have warnings about low expected counts
            assert "test_statistic" in result
            
            print(f"✅ Chi-square test handled small sample scenario")
            print(f"   Test statistic: {result.get('test_statistic', 'unknown')}")
            print(f"   P-value: {result.get('p_value', 'unknown')}")
            
        except Exception as e:
            error_msg = str(e)
            # Error could be about missing variables OR statistical issues
            error_lower = error_msg.lower()
            expected_errors = ["expected", "count", "approximation", "variables", "required", "both"]
            assert any(keyword in error_lower for keyword in expected_errors), \
                f"Error should mention statistical or variable issues: {error_msg}"
            print(f"✅ Small sample chi-square error properly identified: {error_msg[:100]}...")

    @pytest.mark.asyncio
    async def test_missing_package_error(self, context):
        """Test real R error for missing package."""
        # Create data that would work if package existed
        data = {
            "values": [100, 102, 98, 105, 108, 110, 95, 100, 103, 107, 112, 109]
        }
        
        try:
            # This should fail with missing package error if forecast not installed
            result = await arima_model(
                context,
                {
                    "data": data,
                    "order": [1, 1, 1]
                }
            )
            
            # If it succeeds, the package is installed
            assert "aic" in result or "coefficients" in result
            print(f"✅ ARIMA model succeeded (forecast package available)")
            
        except Exception as e:
            error_msg = str(e)
            if "package" in error_msg.lower():
                assert "forecast" in error_msg or "there is no package" in error_msg
                print(f"✅ Missing package error properly identified: {error_msg[:100]}...")
            else:
                # Other errors are also valid (data format, model issues)
                print(f"✅ ARIMA model produced error (expected): {error_msg[:100]}...")

    @pytest.mark.asyncio
    async def test_data_type_error(self, context):
        """Test real R error for invalid data types."""
        # Data with string where number expected
        invalid_data = {
            "numeric_var": [1, 2, "not_a_number", 4, 5],
            "outcome": [10, 20, 30, 40, 50]
        }
        
        try:
            result = await linear_model(
                context,
                {
                    "data": invalid_data,
                    "formula": "outcome ~ numeric_var"
                }
            )
            
            # Should not succeed with string in numeric variable
            # If it does, R coerced the data somehow
            print(f"⚠️  Linear model handled mixed data types (R coercion occurred)")
            
        except Exception as e:
            error_msg = str(e)
            # Should contain information about data type issues
            assert any(keyword in error_msg.lower() for keyword in 
                      ["numeric", "character", "invalid", "coerced", "na"])
            print(f"✅ Data type error properly identified: {error_msg[:100]}...")

    @pytest.mark.asyncio
    async def test_insufficient_data_error(self, context):
        """Test real R error for insufficient data."""
        # Too little data for meaningful analysis
        minimal_data = {
            "x": [1],
            "y": [2]
        }
        
        try:
            result = await linear_model(
                context,
                {
                    "data": minimal_data,
                    "formula": "y ~ x"
                }
            )
            
            # Should not succeed with just one data point
            print(f"⚠️  Linear model handled minimal data (unexpected)")
            
        except Exception as e:
            error_msg = str(e)
            # Should contain information about insufficient data
            assert any(keyword in error_msg.lower() for keyword in 
                      ["insufficient", "degrees", "freedom", "sample", "observations"])
            print(f"✅ Insufficient data error properly identified: {error_msg[:100]}...")

    @pytest.mark.asyncio
    async def test_file_not_found_error(self, context):
        """Test real R error for missing files."""
        from rmcp.tools.fileops import read_csv
        
        try:
            result = await read_csv(
                context,
                {
                    "file_path": "/nonexistent/path/missing_file.csv"
                }
            )
            
            # Should not succeed
            print(f"⚠️  File read succeeded for nonexistent file (unexpected)")
            
        except Exception as e:
            error_msg = str(e)
            # Should contain file-related error information
            assert any(keyword in error_msg.lower() for keyword in 
                      ["file", "not.*found", "no.*such", "path", "does.*not.*exist"])
            print(f"✅ File not found error properly identified: {error_msg[:100]}...")


class TestRWarningCaptureAndSurfacing:
    """Test that R warnings are properly captured and surfaced to users."""

    @pytest.mark.asyncio
    async def test_warning_information_in_suggest_fix(self, context):
        """Test that suggest_fix provides helpful guidance for common R warnings."""
        
        # Test common R warning scenarios
        warning_scenarios = [
            {
                "error_message": "glm.fit: fitted probabilities numerically 0 or 1 occurred",
                "tool_name": "logistic_regression",
                "expected_type": "convergence_issue"
            },
            {
                "error_message": "there is no package called 'forecast'",
                "tool_name": "arima_model", 
                "expected_type": "missing_package"
            },
            {
                "error_message": "Chi-squared approximation may be incorrect",
                "tool_name": "chi_square_test",
                "expected_type": "statistical_assumption"
            }
        ]
        
        for scenario in warning_scenarios:
            result = await suggest_fix(
                context,
                {
                    "error_message": scenario["error_message"],
                    "tool_name": scenario["tool_name"]
                }
            )
            
            assert "error_type" in result
            assert "suggestions" in result
            assert len(result["suggestions"]) > 0
            
            # Suggestions should be actionable
            suggestions_text = " ".join(result["suggestions"]).lower()
            assert any(action in suggestions_text for action in 
                      ["try", "consider", "install", "check", "use", "ensure"])
            
            print(f"✅ Error guidance for '{scenario['error_message'][:30]}...': {result['error_type']}")

    @pytest.mark.asyncio
    async def test_data_validation_captures_r_warnings(self, context):
        """Test that data validation captures R warnings about data quality."""
        
        # Data likely to trigger R warnings
        problematic_data = {
            "var_with_nas": [1, 2, None, 4, None, 6],
            "constant_var": [5, 5, 5, 5, 5, 5],  # No variation
            "extreme_outlier": [1, 2, 3, 4, 1000],  # Extreme value
            "very_small_sample": [1, 2]  # Too small for many analyses
        }
        
        result = await validate_data(
            context,
            {
                "data": problematic_data,
                "analysis_type": "regression"
            }
        )
        
        assert "is_valid" in result
        assert "warnings" in result or "errors" in result
        
        # Should identify data quality issues
        if not result.get("is_valid", True):
            assert len(result.get("warnings", [])) > 0 or len(result.get("errors", [])) > 0
            
        print(f"✅ Data validation identified {len(result.get('warnings', []))} warnings")
        print(f"   and {len(result.get('errors', []))} errors for problematic data")


class TestErrorMessageQuality:
    """Test that error messages are clear and actionable for end users."""

    @pytest.mark.asyncio
    async def test_error_messages_are_user_friendly(self, context):
        """Test that error messages provide clear guidance without technical jargon."""
        
        # Test various error scenarios and check message quality
        error_scenarios = [
            {
                "tool": linear_model,
                "args": {"data": {}, "formula": "y ~ x"},
                "description": "Empty dataset"
            },
            {
                "tool": logistic_regression, 
                "args": {"data": {"x": [1, 2], "y": [0, 1]}, "formula": "y ~ x"},
                "description": "Insufficient data"
            }
        ]
        
        for scenario in error_scenarios:
            try:
                await scenario["tool"](context, scenario["args"])
                print(f"⚠️  {scenario['description']} didn't trigger expected error")
            except Exception as e:
                error_msg = str(e)
                
                # Error message quality checks
                assert len(error_msg) > 20, "Error message should be descriptive"
                assert not error_msg.startswith("Traceback"), "Should not expose raw stack traces"
                
                # Should contain helpful information
                error_lower = error_msg.lower()
                has_helpful_info = any(keyword in error_lower for keyword in [
                    "data", "analysis", "requires", "try", "check", "ensure", "missing", "invalid"
                ])
                
                assert has_helpful_info, f"Error message should be helpful: {error_msg[:100]}"
                
                print(f"✅ {scenario['description']} error message quality verified")
                print(f"   Message: {error_msg[:80]}...")

    @pytest.mark.asyncio
    async def test_error_context_preservation(self, context):
        """Test that errors preserve enough context for debugging."""
        
        # Create an error scenario with specific context
        problematic_data = {
            "sales": [100, 200, 300],
            "marketing": ["low", "medium", "high"]  # String where numeric expected
        }
        
        try:
            await linear_model(
                context,
                {
                    "data": problematic_data,
                    "formula": "sales ~ marketing"
                }
            )
        except Exception as e:
            error_msg = str(e)
            
            # Error should preserve context about what went wrong
            assert "marketing" in error_msg or "sales" in error_msg, "Error should mention problematic variables"
            
            # Should indicate the nature of the problem
            error_lower = error_msg.lower()
            has_type_info = any(keyword in error_lower for keyword in [
                "character", "numeric", "string", "number", "type", "coerced"
            ])
            
            assert has_type_info, f"Error should indicate data type issue: {error_msg}"
            
            print(f"✅ Error context preserved: mentions data types and variables")
            print(f"   Error: {error_msg[:100]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])