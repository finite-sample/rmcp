"""
Clean R integration for statistical analysis.

Extracted working R execution functionality without dependencies.
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