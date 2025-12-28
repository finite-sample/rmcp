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
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .config import get_config
from .logging_config import get_logger, log_r_execution

logger = get_logger(__name__)
# Global semaphore for R process concurrency (max 4 concurrent R processes)
R_SEMAPHORE = asyncio.Semaphore(4)

# Cached R binary path for performance
_R_BINARY_PATH = None


def get_r_binary_path() -> str:
    """
    Discover and cache the R binary path.

    Returns:
        str: Path to R binary

    Raises:
        FileNotFoundError: If R binary cannot be found
    """
    global _R_BINARY_PATH

    if _R_BINARY_PATH is not None:
        return _R_BINARY_PATH

    import shutil

    # Try to find R binary using multiple approaches
    candidates = [
        # Standard approach - use which to find R in PATH
        shutil.which("R"),
        # Common installation paths
        "/usr/bin/R",
        "/usr/local/bin/R",
        "/opt/R/bin/R",
        # Windows paths (if running on Windows)
        shutil.which("R.exe") if os.name == "nt" else None,
        # Try Rscript as alternative
        shutil.which("Rscript"),
    ]

    # Filter out None values
    candidates = [path for path in candidates if path is not None]

    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            _R_BINARY_PATH = candidate
            logger.info(f"Found R binary at: {_R_BINARY_PATH}")
            return _R_BINARY_PATH

    # If we get here, R was not found
    raise FileNotFoundError(
        "R binary not found. Please ensure R is installed and available in PATH. "
        f"Searched paths: {candidates}"
    )


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
        self,
        message: str,
        stdout: str = "",
        stderr: str = "",
        returncode: int | None = None,
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


def check_r_version() -> tuple[bool, str]:
    """
    Check if R version is 4.4.0 or higher.

    Returns:
        Tuple of (is_compatible, version_string)
        - is_compatible: True if R version >= 4.4.0
        - version_string: Full R version string for logging

    Raises:
        RExecutionError: If R is not available or version check fails
    """
    try:
        result = subprocess.run(
            ["R", "--version"],
            capture_output=True,
            text=True,
            timeout=get_config().r.version_check_timeout,
        )

        if result.returncode != 0:
            raise RExecutionError(
                "R version check failed - R is not working properly",
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
            )

        # Parse version from first line: "R version 4.4.0 (2024-04-24) -- ..."
        version_line = result.stdout.split("\n")[0]

        # Extract version number using regex
        version_match = re.search(r"R version (\d+)\.(\d+)\.(\d+)", version_line)

        if not version_match:
            raise RExecutionError(
                f"Could not parse R version from output: {version_line}",
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=0,
            )

        major, minor, patch = map(int, version_match.groups())

        # Check if version >= 4.4.0
        is_compatible = (major > 4) or (major == 4 and minor >= 4)

        if not is_compatible:
            logger.warning(
                f"R version {major}.{minor}.{patch} detected. "
                f"RMCP requires R 4.4.0+ for full compatibility."
            )

        return is_compatible, version_line.strip()

    except subprocess.TimeoutExpired:
        raise RExecutionError("R version check timed out", "", "", None)
    except FileNotFoundError:
        raise RExecutionError("R is not installed or not in PATH", "", "", None)


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
            r_binary = get_r_binary_path()
            process = subprocess.run(
                [r_binary, "--slave", "--no-restore", "--file=" + script_path],
                capture_output=True,
                text=True,
                timeout=get_config().r.timeout,
            )
            if process.returncode != 0:
                # Enhanced error handling for missing packages
                try:
                    r_path = get_r_binary_path()
                except FileNotFoundError:
                    r_path = "R (not found in PATH)"
                env_info = {
                    "PATH": os.environ.get("PATH", ""),
                    "R_HOME": os.environ.get("R_HOME", ""),
                    "R_LIBS": os.environ.get("R_LIBS", ""),
                    "working_dir": str(Path.cwd()),
                }

                error_msg = f"""R script failed with return code {process.returncode}
COMMAND: {r_path} --slave --no-restore --file={script_path}
STDOUT:
{process.stdout or "(empty)"}
STDERR:
{process.stderr or "(empty)"}
ENVIRONMENT:
{env_info}"""
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
                with open(result_path) as f:
                    result = json.load(f)
                logger.debug(f"R script executed successfully, result: {result}")
                return result
            except FileNotFoundError:
                exc = RExecutionError("R script did not produce output file")
                exc.add_note(f"Expected output file: {result_path}")
                exc.add_note(
                    "This usually indicates R script execution failed before producing results"
                )
                raise exc
            except json.JSONDecodeError as e:
                exc = RExecutionError(f"R script produced invalid JSON: {e}")
                exc.add_note(f"Output file: {result_path}")
                exc.add_note(
                    "Check R script for JSON formatting errors or unexpected output"
                )
                raise exc
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
        start_time = time.time()
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
                r_binary = get_r_binary_path()
                proc = await asyncio.create_subprocess_exec(
                    r_binary,
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
                        assert proc.stdout is not None
                        while True:
                            chunk = await proc.stdout.read(1024)
                            if not chunk:
                                break
                            stdout_chunks.append(chunk)

                    async def monitor_stderr():
                        """Monitor stderr for progress messages and errors."""
                        assert proc.stderr is not None
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

                    # Run stdout and stderr monitoring concurrently using TaskGroup (Python 3.11+)
                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(read_stdout())
                        tg.create_task(monitor_stderr())
                        tg.create_task(
                            asyncio.wait_for(
                                proc.wait(), timeout=get_config().r.timeout
                            )
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
                    except TimeoutError:
                        logger.warning("R process didn't terminate gracefully, killing")
                        proc.kill()
                        await proc.wait()
                    raise
                except TimeoutError:
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
                    try:
                        r_path = get_r_binary_path()
                    except FileNotFoundError:
                        r_path = "R (not found in PATH)"
                    env_info = {
                        "PATH": os.environ.get("PATH", ""),
                        "R_HOME": os.environ.get("R_HOME", ""),
                        "R_LIBS": os.environ.get("R_LIBS", ""),
                        "working_dir": str(Path.cwd()),
                    }

                    error_msg = f"""R script failed with return code {proc.returncode}
COMMAND: {r_path} --slave --no-restore --file={script_path}
STDOUT:
{stdout or "(empty)"}
STDERR:
{stderr or "(empty)"}
ENVIRONMENT:
{env_info}"""
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
                            returncode=proc.returncode or 0,
                        )

                    # Enhanced error detection for statistical issues
                    combined_output = (stdout + stderr).lower()

                    if any(
                        phrase in combined_output
                        for phrase in [
                            "insufficient data",
                            "insufficient degrees",
                            "need at least",
                            "requires at least",
                            "sample size",
                        ]
                    ):
                        # Extract context from R stderr if available
                        context_info = ""
                        if stderr and "parameters but only" in stderr:
                            # Try to extract parameter and observation counts
                            import re

                            match = re.search(
                                r"(\d+) parameters but only (\d+) observations", stderr
                            )
                            if match:
                                params, obs = match.groups()
                                context_info = f"\n📋 Analysis details: {params} parameters, {obs} observations"

                        helpful_msg = f"""❌ Insufficient Data for Statistical Analysis

🔍 The analysis requires more data points than provided.{context_info}

📊 Common requirements:
   • Linear regression: At least 2 observations
   • Multiple regression: At least k+1 observations (k = number of predictors)
   • Reliable estimates: Generally 10-20 observations per parameter

💡 Try:
   • Adding more data points to your sample
   • Using a simpler model with fewer variables
   • Checking for missing values that reduce sample size

Original error:
{error_msg}"""
                        raise RExecutionError(
                            helpful_msg,
                            stdout=stdout,
                            stderr=stderr,
                            returncode=proc.returncode or 0,
                        )

                    if any(
                        phrase in combined_output
                        for phrase in [
                            "degrees of freedom",
                            "non-numeric argument",
                            "nans produced",
                        ]
                    ):
                        helpful_msg = f"""❌ Statistical Computation Error

🔍 The analysis encountered a mathematical issue, often due to:
   • Insufficient degrees of freedom (too few observations vs parameters)
   • Perfect multicollinearity (predictors are perfectly correlated)
   • Numerical instability with very small sample sizes

💡 Try:
   • Increasing your sample size
   • Removing redundant or highly correlated variables
   • Checking for constant variables or perfect relationships

Original error:
{error_msg}"""
                        raise RExecutionError(
                            helpful_msg,
                            stdout=stdout,
                            stderr=stderr,
                            returncode=proc.returncode or 0,
                        )

                    # Fall back to general error
                    raise RExecutionError(
                        error_msg,
                        stdout=stdout,
                        stderr=stderr,
                        returncode=proc.returncode or 0,
                    )
                # Read and parse results
                try:
                    with open(result_path) as f:
                        result_json = f.read()
                        result = json.loads(result_json)
                        result_info = (
                            list(result.keys())
                            if isinstance(result, dict)
                            else type(result)
                        )
                        # Log structured R execution completion
                        execution_time_ms = int((time.time() - start_time) * 1000)
                        log_r_execution(
                            logger,
                            r_command=script[:100] + "..."
                            if len(script) > 100
                            else script,
                            execution_time_ms=execution_time_ms,
                            success=True,
                        )

                        logger.debug(
                            f"R script completed successfully, result keys: {result_info}"
                        )
                        return result
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    # Log structured R execution failure
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    log_r_execution(
                        logger,
                        r_command=script[:100] + "..." if len(script) > 100 else script,
                        execution_time_ms=execution_time_ms,
                        success=False,
                        error_message=str(e),
                    )

                    error_msg = (
                        f"Failed to read or parse R script results: {e}\\n\\n"
                        f"R stdout: {stdout}\\n\\nR stderr: {stderr}"
                    )
                    raise RExecutionError(
                        error_msg,
                        stdout=stdout,
                        stderr=stderr,
                        returncode=proc.returncode or 0,
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


def diagnose_r_installation() -> dict[str, Any]:
    """
    Diagnose R installation and return comprehensive status information.

    Returns:
        dict containing diagnostic information including:
        - r_available: Whether R binary is found
        - r_path: Path to R binary
        - r_version: R version string (if available)
        - jsonlite_available: Whether jsonlite package is installed
        - environment: Relevant environment variables
        - error: Any error encountered during diagnosis
    """
    import os
    import subprocess

    diagnosis: dict[str, Any] = {
        "r_available": False,
        "r_path": None,
        "r_version": None,
        "jsonlite_available": False,
        "environment": {
            "PATH": os.environ.get("PATH", ""),
            "R_HOME": os.environ.get("R_HOME", ""),
            "R_LIBS": os.environ.get("R_LIBS", ""),
            "working_dir": str(Path.cwd()),
        },
        "error": None,
    }

    try:
        # Check if R is available
        try:
            r_path = get_r_binary_path()
        except FileNotFoundError:
            r_path = None

        if r_path:
            diagnosis["r_available"] = True
            diagnosis["r_path"] = r_path

            # Get R version
            try:
                result = subprocess.run(
                    [r_path, "--version"], capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    # Extract first line which contains version info
                    version_line = (
                        result.stdout.split("\n")[0] if result.stdout else "Unknown"
                    )
                    diagnosis["r_version"] = version_line
                else:
                    diagnosis["error"] = (
                        f"R --version failed with return code {result.returncode}: {result.stderr}"
                    )
            except subprocess.TimeoutExpired:
                diagnosis["error"] = "R --version timed out after 30 seconds"
            except Exception as e:
                diagnosis["error"] = f"Failed to get R version: {str(e)}"

            # Test basic R functionality and jsonlite availability
            try:
                test_script = """
                cat("R OK\\n")
                library(jsonlite)
                cat(toJSON(list(jsonlite_ok=TRUE)), "\\n")
                """

                result = subprocess.run(
                    [r_path, "--slave", "--no-restore", "-e", test_script],
                    capture_output=True,
                    text=True,
                    timeout=get_config().r.version_check_timeout,
                )

                if result.returncode == 0:
                    if "jsonlite_ok" in result.stdout:
                        diagnosis["jsonlite_available"] = True
                    else:
                        diagnosis["error"] = (
                            f"jsonlite test failed - unexpected output: {result.stdout}"
                        )
                else:
                    diagnosis["error"] = (
                        f"R basic test failed (code {result.returncode}): {result.stderr}"
                    )
            except subprocess.TimeoutExpired:
                diagnosis["error"] = "R basic test timed out after 30 seconds"
            except Exception as e:
                diagnosis["error"] = f"R basic test failed: {str(e)}"
        else:
            diagnosis["error"] = "R binary not found in PATH"

    except Exception as e:
        diagnosis["error"] = f"Diagnostic failed: {str(e)}"

    return diagnosis


async def diagnose_r_installation_async() -> dict[str, Any]:
    """
    Asynchronous version of R installation diagnosis.

    Returns:
        dict containing the same diagnostic information as diagnose_r_installation
    """
    import asyncio
    import os

    diagnosis: dict[str, Any] = {
        "r_available": False,
        "r_path": None,
        "r_version": None,
        "jsonlite_available": False,
        "environment": {
            "PATH": os.environ.get("PATH", ""),
            "R_HOME": os.environ.get("R_HOME", ""),
            "R_LIBS": os.environ.get("R_LIBS", ""),
            "working_dir": str(Path.cwd()),
        },
        "error": None,
    }

    try:
        # Check if R is available
        try:
            r_path = get_r_binary_path()
        except FileNotFoundError:
            r_path = None

        if r_path:
            diagnosis["r_available"] = True
            diagnosis["r_path"] = r_path

            # Get R version
            try:
                proc = await asyncio.create_subprocess_exec(
                    r_path,
                    "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=get_config().r.version_check_timeout
                )

                if proc.returncode == 0:
                    # Extract first line which contains version info
                    version_line = (
                        stdout.decode().split("\n")[0] if stdout else "Unknown"
                    )
                    diagnosis["r_version"] = version_line
                else:
                    diagnosis["error"] = (
                        f"R --version failed with return code {proc.returncode}: {stderr.decode()}"
                    )
            except TimeoutError:
                diagnosis["error"] = "R --version timed out after 30 seconds"
            except Exception as e:
                diagnosis["error"] = f"Failed to get R version: {str(e)}"

            # Test basic R functionality and jsonlite availability
            try:
                test_script = """
                cat("R OK\\n")
                library(jsonlite)
                cat(toJSON(list(jsonlite_ok=TRUE)), "\\n")
                """

                proc = await asyncio.create_subprocess_exec(
                    r_path,
                    "--slave",
                    "--no-restore",
                    "-e",
                    test_script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=get_config().r.version_check_timeout
                )

                if proc.returncode == 0:
                    stdout_str = stdout.decode()
                    if "jsonlite_ok" in stdout_str:
                        diagnosis["jsonlite_available"] = True
                    else:
                        diagnosis["error"] = (
                            f"jsonlite test failed - unexpected output: {stdout_str}"
                        )
                else:
                    diagnosis["error"] = (
                        f"R basic test failed (code {proc.returncode}): {stderr.decode()}"
                    )
            except TimeoutError:
                diagnosis["error"] = "R basic test timed out after 30 seconds"
            except Exception as e:
                diagnosis["error"] = f"R basic test failed: {str(e)}"
        else:
            diagnosis["error"] = "R binary not found in PATH"

    except Exception as e:
        diagnosis["error"] = f"Diagnostic failed: {str(e)}"

    return diagnosis
