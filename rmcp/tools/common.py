# rmcp/tools/common.py

import os
import json
import tempfile
import subprocess
from typing import Dict, Any

def execute_r_script(script: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an R script with the given arguments and return the results.
    Captures stdout and stderr from the Rscript call.
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
        # Construct the R command.
        r_command = f"""
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
        """
        subprocess.run(
            ['Rscript', '-e', r_command],
            check=True,
            capture_output=True,
            text=True
        )
        with open(result_path, 'r') as f:
            result = json.load(f)
        return result
    except subprocess.CalledProcessError as e:
        print("Rscript STDOUT:")
        print(e.stdout)
        print("Rscript STDERR:")
        print(e.stderr)
        raise
    finally:
        for file_path in [script_path, args_path, result_path]:
            try:
                os.unlink(file_path)
            except Exception:
                pass

