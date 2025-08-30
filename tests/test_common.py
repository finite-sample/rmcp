"""
Tests for rmcp.tools.common module.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from rmcp.tools.common import execute_r_script, RExecutionError


class TestExecuteRScript:
    """Test the execute_r_script function."""
    
    def test_successful_execution(self):
        """Test successful R script execution."""
        # Simple script that just returns the input args
        script = "result <- args"
        args = {"test_value": 42, "test_string": "hello"}
        
        result = execute_r_script(script, args)
        
        assert isinstance(result, dict)
        assert result["test_value"] == 42
        assert result["test_string"] == "hello"
    
    def test_r_calculation(self):
        """Test R script with actual calculations."""
        script = """
        x <- args$x
        y <- args$y
        correlation <- cor(x, y)
        result <- list(correlation = correlation, length = length(x))
        """
        args = {"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]}
        
        result = execute_r_script(script, args)
        
        assert "correlation" in result
        assert "length" in result
        assert result["correlation"] == 1.0  # Perfect correlation
        assert result["length"] == 5
    
    @patch('subprocess.run')
    def test_r_not_found(self, mock_run):
        """Test error when R is not installed."""
        mock_run.side_effect = FileNotFoundError("Rscript not found")
        
        with pytest.raises(RExecutionError) as exc_info:
            execute_r_script("result <- list()", {})
        
        assert "R not found" in str(exc_info.value)
    
    @patch('subprocess.run')
    def test_r_script_error(self, mock_run):
        """Test error handling when R script fails."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = "R output"
        mock_process.stderr = "R error"
        mock_run.return_value = mock_process
        
        # Mock the result file to contain error
        with patch('builtins.open', side_effect=[
            MagicMock(),  # script file
            MagicMock(),  # args file  
            MagicMock(),  # result file (read)
        ]):
            with patch('json.load', return_value={"error": "R Error: undefined variable"}):
                with pytest.raises(RExecutionError) as exc_info:
                    execute_r_script("undefined_variable", {})
                
                assert "R Error:" in str(exc_info.value)
    
    @patch('subprocess.run')
    def test_timeout_error(self, mock_run):
        """Test timeout handling."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("Rscript", 30)
        
        with pytest.raises(RExecutionError) as exc_info:
            execute_r_script("Sys.sleep(60)", {})
        
        assert "timed out" in str(exc_info.value)
    
    @patch('json.load')
    @patch('builtins.open')
    @patch('subprocess.run')
    def test_invalid_json_result(self, mock_run, mock_open, mock_json_load):
        """Test handling of invalid JSON from R script."""
        # Mock successful subprocess run
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process
        
        # Mock file operations
        mock_open.return_value.__enter__ = MagicMock()
        mock_open.return_value.__exit__ = MagicMock()
        
        # Mock JSON parsing to fail
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        
        with pytest.raises(RExecutionError):
            execute_r_script("result <- list(value = 1)", {})


class TestRExecutionError:
    """Test the RExecutionError exception class."""
    
    def test_error_creation(self):
        """Test creating RExecutionError with all parameters."""
        error = RExecutionError(
            "Test error",
            stdout="stdout content",
            stderr="stderr content", 
            returncode=1
        )
        
        assert str(error) == "Test error"
        assert error.stdout == "stdout content"
        assert error.stderr == "stderr content"
        assert error.returncode == 1
    
    def test_error_minimal(self):
        """Test creating RExecutionError with minimal parameters."""
        error = RExecutionError("Minimal error")
        
        assert str(error) == "Minimal error"
        assert error.stdout == ""
        assert error.stderr == ""
        assert error.returncode is None