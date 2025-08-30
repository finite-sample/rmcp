"""
Common utilities for RMCP tools.

This module provides shared functionality for executing R scripts
and handling data exchange between Python and R.
"""

import os
import json
import tempfile
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RExecutionError(Exception):
    """Exception raised when R script execution fails."""
    
    def __init__(self, message: str, stdout: str = "", stderr: str = "", returncode: int = None):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr  
        self.returncode = returncode

def execute_r_script(script: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an R script with the given arguments and return the results.
    
    Args:
        script: R script code to execute
        args: Dictionary of arguments to pass to the R script
        
    Returns:
        Dictionary containing the results from R script execution
        
    Raises:
        RExecutionError: If R script execution fails
        FileNotFoundError: If R is not installed or not in PATH
        json.JSONDecodeError: If R script returns invalid JSON
        
    Note:
        The function creates temporary files for script, arguments, and results.
        All temporary files are cleaned up after execution.
    """
    with tempfile.NamedTemporaryFile(suffix='.R', delete=False, mode='w') as script_file, \
         tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as args_file, \
         tempfile.NamedTemporaryFile(suffix='.json', delete=False) as result_file:
        
        script_path = script_file.name
        args_path = args_file.name
        result_path = result_file.name
        
        # Write the script and arguments to temporary files.
        script_file.write(script)
        json.dump(args, args_file)
    
    try:
        # Construct the R command with proper error handling
        r_command = f"""
        tryCatch({{
            library(jsonlite)
            library(plm)
            library(lmtest)
            library(sandwich)
            library(AER)
            library(dplyr)
            
            '%||%' <- function(x, y) if (is.null(x)) y else x
            
            args <- fromJSON('{args_path}')
            {script}
            writeLines(toJSON(result, auto_unbox = TRUE), '{result_path}')
        }}, error = function(e) {{
            error_result <- list(error = paste("R Error:", e$message))
            writeLines(toJSON(error_result, auto_unbox = TRUE), '{result_path}')
            quit(status = 1)
        }})
        """
        
        logger.debug(f"Executing R script with args: {args}")
        
        # Execute R script
        process = subprocess.run(
            ['Rscript', '-e', r_command],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        # Read results
        try:
            with open(result_path, 'r') as f:
                result = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to read R script results: {e}")
            raise RExecutionError(
                f"Failed to parse R script output: {str(e)}",
                stdout=process.stdout,
                stderr=process.stderr,
                returncode=process.returncode
            )
        
        # Check for R-level errors
        if isinstance(result, dict) and 'error' in result:
            logger.error(f"R script error: {result['error']}")
            raise RExecutionError(
                result['error'],
                stdout=process.stdout,
                stderr=process.stderr,
                returncode=process.returncode
            )
        
        # Check subprocess return code
        if process.returncode != 0:
            logger.error(f"R script failed with return code {process.returncode}")
            logger.error(f"STDOUT: {process.stdout}")
            logger.error(f"STDERR: {process.stderr}")
            raise RExecutionError(
                f"R script execution failed with return code {process.returncode}",
                stdout=process.stdout,
                stderr=process.stderr,
                returncode=process.returncode
            )
        
        logger.debug(f"R script executed successfully, result: {result}")
        return result
        
    except subprocess.TimeoutExpired as e:
        logger.error("R script execution timed out")
        raise RExecutionError(
            "R script execution timed out after 30 seconds",
            stdout=getattr(e, 'stdout', ''),
            stderr=getattr(e, 'stderr', '')
        )
    except FileNotFoundError as e:
        logger.error("R not found - ensure R is installed and in PATH")
        raise RExecutionError(
            "R not found. Please ensure R is installed and available in PATH.",
            stderr=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during R script execution: {e}")
        raise RExecutionError(f"Unexpected error: {str(e)}")
        
    finally:
        # Clean up temporary files
        for file_path in [script_path, args_path, result_path]:
            try:
                os.unlink(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {file_path}: {e}")

