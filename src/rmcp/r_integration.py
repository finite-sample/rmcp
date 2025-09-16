"""
R Integration Module for RMCP Statistical Analysis.

This module provides a clean interface for executing R scripts from Python,
handling data serialization, error management, and resource cleanup.

Key features:
- JSON-based data exchange between Python and R
- Automatic temporary file management
- Comprehensive error handling with detailed diagnostics
- Timeout protection for long-running R operations
- Cross-platform R execution support

Example:
    >>> script = '''
    ... result <- list(
    ...     mean_value = mean(args$data),
    ...     std_dev = sd(args$data)
    ... )
    ... '''
    >>> args = {"data": [1, 2, 3, 4, 5]}
    >>> result = execute_r_script(script, args)
    >>> print(result["mean_value"])  # 3.0
"""

import os
import json
import tempfile
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class RExecutionError(Exception):
    """
    Exception raised when R script execution fails.
    
    This exception provides detailed information about R execution failures,
    including stdout/stderr output and process return codes for debugging.
    
    Attributes:
        message: Human-readable error description
        stdout: Standard output from R process (if any)
        stderr: Standard error from R process (if any) 
        returncode: Process exit code (if available)
        
    Example:
        >>> try:
        ...     execute_r_script("invalid R code", {})
        ... except RExecutionError as e:
        ...     print(f"R failed: {e}")
        ...     print(f"Error details: {e.stderr}")
    """
    
    def __init__(self, message: str, stdout: str = "", stderr: str = "", returncode: int = None):
        """
        Initialize R execution error.
        
        Args:
            message: Primary error message
            stdout: R process standard output
            stderr: R process standard error
            returncode: R process exit code
        """
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr  
        self.returncode = returncode


def execute_r_script(script: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an R script with arguments and return JSON results.
    
    This function creates a complete R execution environment by:
    1. Writing arguments to a temporary JSON file
    2. Creating an R script that loads jsonlite and reads the arguments
    3. Appending the user's R code
    4. Writing results to a JSON output file
    5. Executing R and parsing the results
    6. Cleaning up all temporary files
    
    Args:
        script: R code to execute. Must set a 'result' variable with output.
            The script has access to an 'args' variable containing the arguments.
        args: Dictionary of arguments available to R script as 'args' variable.
            All values must be JSON-serializable.
        
    Returns:
        Dictionary containing the R script results (contents of 'result' variable).
        
    Raises:
        RExecutionError: If R script execution fails, with detailed error info
        FileNotFoundError: If R is not installed or not in PATH
        json.JSONDecodeError: If R script produces invalid JSON output
        
    Example:
        >>> # Calculate statistics on a dataset
        >>> r_code = '''
        ... result <- list(
        ...     mean = mean(args$values),
        ...     median = median(args$values),
        ...     sd = sd(args$values)
        ... )
        ... '''
        >>> args = {"values": [1, 2, 3, 4, 5]}
        >>> stats = execute_r_script(r_code, args)
        >>> print(stats["mean"])  # 3.0
        
        >>> # Linear regression example
        >>> r_code = '''
        ... df <- data.frame(args$data)
        ... model <- lm(y ~ x, data = df)
        ... result <- list(
        ...     coefficients = coef(model),
        ...     r_squared = summary(model)$r.squared
        ... )
        ... '''
        >>> data = {"data": {"x": [1,2,3,4], "y": [2,4,6,8]}}
        >>> reg_result = execute_r_script(r_code, data)
    """
    with tempfile.NamedTemporaryFile(suffix='.R', delete=False, mode='w') as script_file, \
         tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as args_file, \
         tempfile.NamedTemporaryFile(suffix='.json', delete=False) as result_file:
        
        script_path = script_file.name
        args_path = args_file.name
        result_path = result_file.name
        
        try:
            # Write arguments to JSON file
            json.dump(args, args_file, default=str)
            args_file.flush()
            
            # Create complete R script
            full_script = f'''
# Load required libraries
library(jsonlite)

# Load arguments
args <- fromJSON("{args_path}")

# User script
{script}

# Write result
write_json(result, "{result_path}", auto_unbox = TRUE)
'''
            
            script_file.write(full_script)
            script_file.flush()
            
            logger.debug(f"Executing R script with args: {args}")
            
            # Execute R script
            process = subprocess.run(
                ['R', '--slave', '--no-restore', '--file=' + script_path],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if process.returncode != 0:
                error_msg = f"R script failed with return code {process.returncode}"
                logger.error(f"{error_msg}\\nStderr: {process.stderr}")
                raise RExecutionError(
                    error_msg,
                    stdout=process.stdout,
                    stderr=process.stderr,
                    returncode=process.returncode
                )
            
            # Read results
            try:
                with open(result_path, 'r') as f:
                    result = json.load(f)
                logger.debug(f"R script executed successfully, result: {result}")
                return result
            except FileNotFoundError:
                raise RExecutionError("R script did not produce output file")
            except json.JSONDecodeError as e:
                raise RExecutionError(f"R script produced invalid JSON: {e}")
        
        finally:
            # Cleanup temporary files
            for temp_path in [script_path, args_path, result_path]:
                try:
                    os.unlink(temp_path)
                    logger.debug(f"Cleaned up temporary file: {temp_path}")
                except OSError:
                    pass