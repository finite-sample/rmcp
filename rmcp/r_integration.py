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

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from typing import Any

logger = logging.getLogger(__name__)
# Global semaphore for R process concurrency (max 4 concurrent R processes)
R_SEMAPHORE = asyncio.Semaphore(4)


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

    def __init__(
        self, message: str, stdout: str = "", stderr: str = "", returncode: int = None
    ):
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


def execute_r_script(script: str, args: dict[str, Any]) -> dict[str, Any]:
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
    with (
        tempfile.NamedTemporaryFile(suffix=".R", delete=False, mode="w") as script_file,
        tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as args_file,
        tempfile.NamedTemporaryFile(suffix=".json", delete=False) as result_file,
    ):
        script_path = script_file.name
        args_path = args_file.name
        result_path = result_file.name
        try:
            # Write arguments to JSON file
            json.dump(args, args_file, default=str)
            args_file.flush()
            # Normalize path for Windows compatibility
            args_path_safe = args_path.replace("\\", "/")
            result_path_safe = result_path.replace("\\", "/")
            # Create complete R script
            full_script = f"""
# Load required libraries
library(jsonlite)
# Define null-coalescing operator (from rlang, defined locally to avoid dependency)
`%||%` <- function(a, b) if (!is.null(a)) a else b
# Load arguments
args <- fromJSON("{args_path_safe}")
# User script
{script}
# Write result
write_json(result, "{result_path_safe}", auto_unbox = TRUE)
"""
            script_file.write(full_script)
            script_file.flush()
            logger.debug(f"Executing R script with args: {args}")
            # Execute R script
            process = subprocess.run(
                ["R", "--slave", "--no-restore", "--file=" + script_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if process.returncode != 0:
                # Enhanced error handling for missing packages
                error_msg = f"R script failed with return code {process.returncode}"
                stderr = process.stderr or ""
                # Check for common R package errors
                if "there is no package called" in stderr:
                    # Extract package name from error
                    import re

                    match = re.search(r"there is no package called '([^']+)'", stderr)
                    if match:
                        missing_pkg = match.group(1)
                        # Map package to feature category
                        pkg_features = {
                            "plm": "Panel Data Analysis",
                            "lmtest": "Statistical Testing",
                            "sandwich": "Robust Standard Errors",
                            "AER": "Applied Econometrics",
                            "jsonlite": "Data Exchange",
                            "forecast": "Time Series Forecasting",
                            "vars": "Vector Autoregression",
                            "urca": "Unit Root Testing",
                            "tseries": "Time Series Analysis",
                            "nortest": "Normality Testing",
                            "car": "Regression Diagnostics",
                            "rpart": "Decision Trees",
                            "randomForest": "Random Forest",
                            "ggplot2": "Data Visualization",
                            "gridExtra": "Plot Layouts",
                            "tidyr": "Data Tidying",
                            "rlang": "Programming Tools",
                            "dplyr": "Data Manipulation",
                            "knitr": "Table Formatting & Reporting",
                        }
                        feature = pkg_features.get(missing_pkg, "Statistical Analysis")
                        error_msg = f"""❌ Missing R Package: '{missing_pkg}'
🔍 This package is required for: {feature}
📦 Install with:
   install.packages("{missing_pkg}")
🚀 Or install all RMCP packages:
   install.packages(c(
     "jsonlite", "plm", "lmtest", "sandwich", "AER", "dplyr", "forecast",
     "vars", "urca", "tseries", "nortest", "car", "rpart", "randomForest",
     "ggplot2", "gridExtra", "tidyr", "rlang", "knitr"
   ))
💡 Check package status: rmcp check-r-packages"""
                elif "could not find function" in stderr:
                    error_msg = f"""❌ R Function Error
The R script failed because a required function is missing. This usually means:
1. A required package is not loaded
2. A package is installed but not the right version
💡 Try: rmcp check-r-packages
Original error: {stderr.strip()}"""
                logger.error(f"{error_msg}\\nOriginal stderr: {stderr}")
                raise RExecutionError(
                    error_msg,
                    stdout=process.stdout,
                    stderr=stderr,
                    returncode=process.returncode,
                )
            # Read results
            try:
                with open(result_path, "r") as f:
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


async def execute_r_script_async(
    script: str, args: dict[str, Any], context=None
) -> dict[str, Any]:
    """
    Execute R script asynchronously with proper cancellation support and concurrency control.
    This function provides:
    - True async execution using asyncio.create_subprocess_exec
    - Proper subprocess cancellation (SIGTERM -> SIGKILL)
    - Global concurrency limiting via semaphore
    - Progress reporting from R scripts via context
    - Same interface and error handling as execute_r_script
    Args:
        script: R script code to execute
        args: Arguments to pass to the R script as JSON
        context: Optional context for progress reporting and logging
    Returns:
        dict[str, Any]: Result data from R script execution
    Raises:
        RExecutionError: If R script execution fails
        asyncio.CancelledError: If the operation is cancelled
    """
    async with R_SEMAPHORE:  # Limit concurrent R processes
        # Create temporary files for script, arguments, and results
        with (
            tempfile.NamedTemporaryFile(
                suffix=".R", delete=False, mode="w"
            ) as script_file,
            tempfile.NamedTemporaryFile(
                suffix=".json", delete=False, mode="w"
            ) as args_file,
            tempfile.NamedTemporaryFile(suffix=".json", delete=False) as result_file,
        ):
            script_path = script_file.name
            args_path = args_file.name
            result_path = result_file.name
            try:
                # Write arguments to JSON file
                json.dump(args, args_file, default=str)
                args_file.flush()
                # Normalize path for Windows compatibility
                args_path_safe = args_path.replace("\\", "/")
                result_path_safe = result_path.replace("\\", "/")
                # Create complete R script with progress reporting
                full_script = f"""
# Load required libraries
library(jsonlite)
# Define null-coalescing operator (from rlang, defined locally to avoid dependency)
`%||%` <- function(a, b) if (!is.null(a)) a else b
# Progress reporting function for RMCP
rmcp_progress <- function(message, current = NULL, total = NULL) {{
    progress_data <- list(
        type = "progress",
        message = message,
        timestamp = Sys.time()
    )
    if (!is.null(current) && !is.null(total)) {{
        progress_data$current <- current
        progress_data$total <- total
        progress_data$percentage <- round((current / total) * 100, 1)
    }}
    cat("RMCP_PROGRESS:", toJSON(progress_data, auto_unbox = TRUE), "\\n", file = stderr())
    flush(stderr())
}}
# Load arguments
args <- fromJSON("{args_path_safe}")
# User script
{script}
# Write result
if (exists("result")) {{
    writeLines(toJSON(result, auto_unbox = TRUE, na = "null", pretty = TRUE), "{result_path_safe}")
}} else {{
    stop("R script must define a 'result' variable")
}}
"""
                # Write R script to file
                script_file.write(full_script)
                script_file.flush()
                logger.debug(f"Executing R script asynchronously with args: {args}")
                # Execute R script asynchronously
                proc = await asyncio.create_subprocess_exec(
                    "R",
                    "--slave",
                    "--no-restore",
                    f"--file={script_path}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    # Monitor stderr for progress messages and collect output
                    stderr_lines = []
                    stdout_chunks = []

                    async def read_stdout():
                        """Read stdout to completion."""
                        while True:
                            chunk = await proc.stdout.read(1024)
                            if not chunk:
                                break
                            stdout_chunks.append(chunk)

                    async def monitor_stderr():
                        """Monitor stderr for progress messages and errors."""
                        while True:
                            line = await proc.stderr.readline()
                            if not line:
                                break
                            line_str = line.decode("utf-8").strip()
                            stderr_lines.append(line_str)
                            # Parse progress messages if context is available
                            if context and line_str.startswith("RMCP_PROGRESS:"):
                                try:
                                    import json

                                    progress_json = line_str[
                                        14:
                                    ]  # Remove "RMCP_PROGRESS:" prefix
                                    progress_data = json.loads(progress_json)
                                    if progress_data.get("type") == "progress":
                                        message = progress_data.get(
                                            "message", "Processing..."
                                        )
                                        current = progress_data.get("current")
                                        total = progress_data.get("total")
                                        if current is not None and total is not None:
                                            await context.progress(
                                                message, current, total
                                            )
                                        else:
                                            # Send as info log if no numeric progress
                                            await context.info(f"R: {message}")
                                except (json.JSONDecodeError, AttributeError) as e:
                                    logger.debug(
                                        f"Failed to parse progress message: {e}"
                                    )

                    # Run stdout and stderr monitoring concurrently
                    await asyncio.wait_for(
                        asyncio.gather(read_stdout(), monitor_stderr(), proc.wait()),
                        timeout=120,  # 2 minute timeout
                    )
                    # Combine output
                    stdout = (
                        b"".join(stdout_chunks).decode("utf-8") if stdout_chunks else ""
                    )
                    stderr = "\n".join(stderr_lines) if stderr_lines else ""
                except asyncio.CancelledError:
                    logger.info("R script execution cancelled, terminating process")
                    # Graceful termination: SIGTERM first, then SIGKILL
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=0.5)
                    except asyncio.TimeoutError:
                        logger.warning("R process didn't terminate gracefully, killing")
                        proc.kill()
                        await proc.wait()
                    raise
                except asyncio.TimeoutError:
                    logger.error("R script execution timed out")
                    proc.kill()
                    await proc.wait()
                    raise RExecutionError(
                        "R script execution timed out after 120 seconds",
                        stdout="",
                        stderr="Execution timed out",
                        returncode=-1,
                    )
                if proc.returncode != 0:
                    # Enhanced error handling for missing packages
                    error_msg = f"R script failed with return code {proc.returncode}"
                    stderr = stderr or ""
                    # Check for common R package errors
                    if "there is no package called" in stderr:
                        # Extract package name from error
                        import re

                        match = re.search(
                            r"there is no package called '([^']+)'", stderr
                        )
                        if match:
                            missing_pkg = match.group(1)
                            # Map package to feature category
                            pkg_features = {
                                "plm": "Panel Data Analysis",
                                "lmtest": "Statistical Testing",
                                "sandwich": "Robust Standard Errors",
                                "AER": "Applied Econometrics",
                                "jsonlite": "Data Exchange",
                                "forecast": "Time Series Forecasting",
                                "vars": "Vector Autoregression",
                                "urca": "Unit Root Testing",
                                "tseries": "Time Series Analysis",
                                "nortest": "Normality Testing",
                                "car": "Regression Diagnostics",
                                "rpart": "Decision Trees",
                                "randomForest": "Random Forest",
                                "ggplot2": "Data Visualization",
                                "gridExtra": "Plot Layouts",
                                "tidyr": "Data Tidying",
                                "rlang": "Programming Tools",
                                "dplyr": "Data Manipulation",
                            }
                            feature = pkg_features.get(
                                missing_pkg, "Statistical Analysis"
                            )
                            error_msg = f"""❌ Missing R Package: '{missing_pkg}'
🔍 This package is required for: {feature}
📦 Install with:
   R -e "install.packages('{missing_pkg}')"
💡 Check package status: rmcp check-r-packages"""
                    raise RExecutionError(
                        error_msg,
                        stdout=stdout,
                        stderr=stderr,
                        returncode=proc.returncode,
                    )
                # Read and parse results
                try:
                    with open(result_path, "r") as f:
                        result_json = f.read()
                        result = json.loads(result_json)
                        result_info = (
                            list(result.keys())
                            if isinstance(result, dict)
                            else type(result)
                        )
                        logger.debug(
                            f"R script completed successfully, result keys: {result_info}"
                        )
                        return result
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    error_msg = (
                        f"Failed to read or parse R script results: {e}\\n\\n"
                        f"R stdout: {stdout}\\n\\nR stderr: {stderr}"
                    )
                    raise RExecutionError(
                        error_msg,
                        stdout=stdout,
                        stderr=stderr,
                        returncode=proc.returncode,
                    )
            finally:
                # Cleanup temporary files
                for temp_path in [script_path, args_path, result_path]:
                    try:
                        os.unlink(temp_path)
                        logger.debug(f"Cleaned up temporary file: {temp_path}")
                    except OSError:
                        pass


def get_r_image_encoder_script() -> str:
    """
    Get R script code for encoding plots as base64 images.
    This function returns R code that can be included in visualization scripts
    to generate base64-encoded PNG images for display in Claude.
    Returns:
        str: R script code with base64 encoding functions
    """
    return """
    # Set CRAN mirror for package installation
    options(repos = c(CRAN = "https://cloud.r-project.org/"))
    # Base64 image encoding utilities for RMCP
    # Function to encode current plot as base64 PNG
    encode_current_plot_base64 <- function(width = 800, height = 600, dpi = 100) {
        # Create temporary file
        temp_file <- tempfile(fileext = ".png")
        # Save current plot
        dev.copy(png, temp_file, width = width, height = height, res = dpi)
        dev.off()
        # Read and encode
        if (file.exists(temp_file)) {
            image_raw <- readBin(temp_file, "raw", file.info(temp_file)$size)
            image_base64 <- base64enc::base64encode(image_raw)
            unlink(temp_file)
            return(image_base64)
        } else {
            return(NULL)
        }
    }
    # Function to encode ggplot object as base64 PNG
    encode_ggplot_base64 <- function(plot_obj, width = 800, height = 600, dpi = 100) {
        library(base64enc)
        # Create temporary file
        temp_file <- tempfile(fileext = ".png")
        # Save ggplot
        ggsave(temp_file, plot = plot_obj, width = width/100, height = height/100,
               dpi = dpi, device = "png", bg = "white")
        # Read and encode
        if (file.exists(temp_file) && file.info(temp_file)$size > 0) {
            image_raw <- readBin(temp_file, "raw", file.info(temp_file)$size)
            image_base64 <- base64enc::base64encode(image_raw)
            unlink(temp_file)
            return(image_base64)
        } else {
            return(NULL)
        }
    }
    # Function to safely encode plot with fallback
    safe_encode_plot <- function(plot_obj = NULL, width = 800, height = 600, dpi = 100) {
        tryCatch({
            if (is.null(plot_obj)) {
                # Use current plot
                encode_current_plot_base64(width, height, dpi)
            } else {
                # Use ggplot object
                encode_ggplot_base64(plot_obj, width, height, dpi)
            }
        }, error = function(e) {
            warning(paste("Failed to encode plot as base64:", e$message))
            return(NULL)
        })
    }
    """


def execute_r_script_with_image(
    script: str,
    args: dict[str, Any],
    include_image: bool = True,
    image_width: int = 800,
    image_height: int = 600,
) -> dict[str, Any]:
    """
    Execute R script and optionally include base64-encoded image data.
    This function extends execute_r_script to support automatic image encoding
    for visualization tools. If include_image is True, it will attempt to capture
    any plot generated by the R script and return it as base64-encoded PNG data.
    Args:
        script: R script code to execute
        args: Arguments to pass to R script
        include_image: Whether to attempt image capture and encoding
        image_width: Width of captured image in pixels
        image_height: Height of captured image in pixels
    Returns:
        Dict containing R script results, optionally with image_data and image_mime_type
    """
    if include_image:
        # Prepend image encoding utilities to the script
        enhanced_script = get_r_image_encoder_script() + "\n\n" + script
        # Modify args to include image settings
        enhanced_args = args.copy()
        enhanced_args.update(
            {
                "image_width": image_width,
                "image_height": image_height,
                "include_image": True,
            }
        )
        # Execute the enhanced script
        result = execute_r_script(enhanced_script, enhanced_args)
        # Check if the script included image data
        if isinstance(result, dict) and result.get("image_data"):
            result["image_mime_type"] = "image/png"
        return result
    else:
        # Standard execution without image support
        return execute_r_script(script, args)


async def execute_r_script_with_image_async(
    script: str,
    args: dict[str, Any],
    include_image: bool = True,
    image_width: int = 800,
    image_height: int = 600,
) -> dict[str, Any]:
    """
    Execute R script asynchronously and optionally include base64-encoded image data.
    This function extends execute_r_script_async to support automatic image encoding
    for visualization tools. If include_image is True, it will attempt to capture
    any plot generated by the R script and return it as base64-encoded PNG data.
    Args:
        script: R script code to execute
        args: Arguments to pass to R script
        include_image: Whether to attempt image capture and encoding
        image_width: Width of captured image in pixels
        image_height: Height of captured image in pixels
    Returns:
        Dict containing R script results, optionally with image_data and image_mime_type
    """
    if include_image:
        # Prepend image encoding utilities to the script
        enhanced_script = get_r_image_encoder_script() + "\n\n" + script
        # Modify args to include image settings
        enhanced_args = args.copy()
        enhanced_args.update(
            {
                "image_width": image_width,
                "image_height": image_height,
                "include_image": True,
            }
        )
        # Execute the enhanced script asynchronously
        result = await execute_r_script_async(enhanced_script, enhanced_args)
        # Check if the script included image data
        if isinstance(result, dict) and result.get("image_data"):
            result["image_mime_type"] = "image/png"
        return result
    else:
        # Standard execution without image support
        return await execute_r_script_async(script, args)
