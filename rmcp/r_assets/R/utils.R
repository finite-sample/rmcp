#' @title RMCP R Utility Functions
#' @description
#' Shared utility functions for RMCP statistical analysis scripts.
#' Provides common functionality for progress reporting, input validation,
#' and output formatting across all R scripts.
#'
#' @details
#' This package provides a comprehensive set of utility functions designed
#' to standardize the interface between Python MCP server and R statistical
#' computing scripts. All functions handle JSON input/output consistently
#' and provide robust error handling for production use.
#'
#' @author RMCP Team
#' @docType package
#' @name rmcp.stats

#' Report progress for long-running operations
#'
#' @description
#' Sends progress information that can be captured by the Python MCP server
#' to provide user feedback during statistical computations. Progress messages
#' are output to stderr to avoid interfering with JSON results.
#'
#' @param message Character string describing current operation
#' @param current Integer current step number (optional)
#' @param total Integer total number of steps (optional)
#' @param percentage Numeric percentage complete (optional, 0-100)
#'
#' @details
#' When both \code{current} and \code{total} are provided, the percentage
#' is automatically calculated. If only \code{percentage} is provided,
#' it's used directly. The function outputs a structured JSON message
#' prefixed with "RMCP_PROGRESS:" for easy parsing by the MCP server.
#'
#' @return No return value, called for side effects (progress output)
#'
#' @examples
#' \dontrun{
#' # Basic progress message
#' rmcp_progress("Loading data")
#'
#' # Progress with step counting
#' rmcp_progress("Processing", current = 50, total = 100)
#'
#' # Progress with direct percentage
#' rmcp_progress("Computing statistics", percentage = 75)
#' }
#'
#' @seealso \code{\link{format_json_output}} for output formatting
#' @export
rmcp_progress <- function(message, current = NULL, total = NULL, percentage = NULL) {
  progress_data <- list(
    type = "progress",
    message = message,
    timestamp = format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  )

  if (!is.null(current) && !is.null(total)) {
    progress_data$current <- current
    progress_data$total <- total
    progress_data$percentage <- round((current / total) * 100, 1)
  } else if (!is.null(percentage)) {
    progress_data$percentage <- percentage
  }

  # Output to stderr so it doesn't interfere with JSON results
  cat("RMCP_PROGRESS:", jsonlite::toJSON(progress_data, auto_unbox = TRUE), "\n", file = stderr())
}

#' Validate JSON input parameters
#'
#' @description
#' Performs comprehensive validation checks on input parameters received from
#' the Python MCP server. Ensures required parameters exist, have appropriate
#' types and values, and automatically converts data structures when possible.
#'
#' @param params Named list of input parameters from JSON
#' @param required Character vector of required parameter names
#' @param optional Character vector of optional parameter names (currently unused)
#'
#' @details
#' This function validates several common parameter types:
#' \itemize{
#'   \item \strong{data}: Ensures it's a list or data.frame, converts if needed
#'   \item \strong{formula}: Validates formula syntax and parseability
#'   \item \strong{Required parameters}: Checks all required params are present
#' }
#'
#' The function also performs automatic type conversions where safe and
#' appropriate, such as converting JSON lists to R data.frames.
#'
#' @return Named list of validated and potentially converted parameters
#'
#' @throws Error with descriptive message if validation fails
#'
#' @examples
#' \dontrun{
#' # Basic validation
#' args <- list(data = mtcars, formula = "mpg ~ wt")
#' params <- validate_json_input(args, required = c("data", "formula"))
#'
#' # Data conversion example
#' json_data <- list(data = list(x = c(1, 2, 3), y = c(4, 5, 6)))
#' params <- validate_json_input(json_data, required = "data")
#' # params$data is now a data.frame
#' }
#'
#' @seealso \code{\link{format_json_output}} for output formatting
#' @export
validate_json_input <- function(params, required = character(0), optional = character(0)) {
  # Check for required parameters
  missing_required <- setdiff(required, names(params))
  if (length(missing_required) > 0) {
    stop("Missing required parameters: ", paste(missing_required, collapse = ", "))
  }

  # Validate data parameter if present
  if ("data" %in% names(params)) {
    if (!is.list(params$data) && !is.data.frame(params$data)) {
      stop("Parameter 'data' must be a list or data frame")
    }

    # Convert to data frame if it's a list
    if (is.list(params$data) && !is.data.frame(params$data)) {
      tryCatch(
        {
          params$data <- as.data.frame(params$data, stringsAsFactors = FALSE)
        },
        error = function(e) {
          stop("Cannot convert 'data' to data frame: ", e$message)
        }
      )
    }

    # Check for empty data
    if (nrow(params$data) == 0) {
      stop("Data cannot be empty")
    }
  }

  # Validate formula parameter if present
  if ("formula" %in% names(params)) {
    if (!is.character(params$formula) || length(params$formula) != 1) {
      stop("Parameter 'formula' must be a single character string")
    }

    # Try to parse formula
    tryCatch(
      {
        as.formula(params$formula)
      },
      error = function(e) {
        stop("Invalid formula syntax: ", e$message)
      }
    )
  }

  return(params)
}

#' Format JSON output with consistent structure
#'
#' @description
#' Ensures all R script outputs follow consistent JSON structure with
#' proper type handling, special value conversion, and optional formatting
#' metadata for enhanced user experience.
#'
#' @param result Named list containing analysis results
#' @param summary Character string summary for human consumption (optional)
#' @param interpretation Character string interpretation of results (optional)
#'
#' @details
#' This function performs several important transformations:
#' \itemize{
#'   \item \strong{Special values}: Converts Inf to "Inf", -Inf to "-Inf", NA/NaN to null
#'   \item \strong{Precision}: Rounds numeric values to 10 decimal places
#'   \item \strong{Scientific notation}: Uses exponential format for very large/small numbers
#'   \item \strong{Metadata}: Adds optional _formatting section with summary/interpretation
#' }
#'
#' @return Named list with standardized output format suitable for JSON serialization
#'
#' @examples
#' \dontrun{
#' # Basic usage
#' result <- list(coefficient = 0.5, p_value = 0.02, r_squared = 0.85)
#' output <- format_json_output(result)
#'
#' # With formatting metadata
#' output <- format_json_output(
#'   result = list(coefficient = 0.5, p_value = 0.02),
#'   summary = "Linear regression completed successfully",
#'   interpretation = "Significant positive relationship found (p < 0.05)"
#' )
#'
#' # Handles special values
#' problematic <- list(inf_val = Inf, na_val = NA, huge = 1e15)
#' clean_output <- format_json_output(problematic)
#' }
#'
#' @seealso \code{\link{safe_json}} for JSON serialization, \code{\link{validate_json_input}} for input validation
#' @export
format_json_output <- function(result, summary = NULL, interpretation = NULL) {
  # Ensure numeric values are properly formatted
  result <- rapply(result, function(x) {
    if (is.numeric(x)) {
      # Handle vectors element-wise
      if (length(x) > 1) {
        return(sapply(x, function(val) {
          if (is.infinite(val)) {
            return(if (val > 0) "Inf" else "-Inf")
          }
          if (is.nan(val)) {
            return(NULL)
          }
          if (is.na(val)) {
            return(NULL)
          }
          # Round to reasonable precision
          if (abs(val) > 1e10 || (abs(val) < 1e-10 && val != 0)) {
            return(formatC(val, format = "e", digits = 6))
          } else {
            return(round(val, 10))
          }
        }))
      } else {
        # Handle scalar values
        if (is.infinite(x)) {
          return(if (x > 0) "Inf" else "-Inf")
        }
        if (is.nan(x)) {
          return(NULL)
        }
        if (is.na(x)) {
          return(NULL)
        }
        # Round to reasonable precision
        if (abs(x) > 1e10 || (abs(x) < 1e-10 && x != 0)) {
          return(formatC(x, format = "e", digits = 6))
        } else {
          return(round(x, 10))
        }
      }
    }
    return(x)
  }, how = "replace")

  # Add formatting metadata if provided
  if (!is.null(summary) || !is.null(interpretation)) {
    result$"_formatting" <- list()
    if (!is.null(summary)) {
      result$"_formatting"$summary <- summary
    }
    if (!is.null(interpretation)) {
      result$"_formatting"$interpretation <- interpretation
    }
  }

  return(result)
}

#' Null-coalescing operator
#'
#' @description
#' Returns the right-hand side if the left-hand side is NULL,
#' similar to the %||% operator in other languages like JavaScript or R's
#' upcoming native null-coalescing operator.
#'
#' @param a First value to check for NULL
#' @param b Value to return if \code{a} is NULL
#'
#' @details
#' This operator is particularly useful for providing default values
#' for optional parameters or handling potentially NULL values in
#' data processing pipelines. It only checks for NULL, not other
#' "falsy" values like 0, FALSE, or empty strings.
#'
#' @return \code{a} if not NULL, otherwise \code{b}
#'
#' @examples
#' \dontrun{
#' # Provide default values for optional parameters
#' method <- args$method %||% "default"
#' alpha <- args$alpha %||% 0.05
#'
#' # Chain multiple null-coalescing operations
#' value <- config$primary %||% config$secondary %||% "fallback"
#'
#' # Note: only NULL triggers the alternative
#' 0 %||% "default" # Returns 0
#' FALSE %||% "default" # Returns FALSE
#' NULL %||% "default" # Returns "default"
#' }
#'
#' @export
`%||%` <- function(a, b) if (is.null(a)) b else a

#' Check if R packages are available
#'
#' @description
#' Checks whether required R packages are installed and can be loaded.
#' Provides helpful error messages for missing packages with installation
#' instructions.
#'
#' @param packages Character vector of package names to check
#' @param stop_on_missing Logical, whether to stop execution if packages are missing (default: FALSE)
#'
#' @details
#' This function uses \code{requireNamespace()} to check package availability
#' without actually loading them, making it faster and avoiding potential
#' conflicts. When \code{stop_on_missing = TRUE}, it provides a helpful
#' error message with the exact \code{install.packages()} command needed.
#'
#' @return Named logical vector indicating which packages are available
#'
#' @examples
#' \dontrun{
#' # Check multiple packages (returns logical vector)
#' available <- check_packages(c("dplyr", "ggplot2", "forecast"))
#' print(available)
#'
#' # Stop execution if critical packages are missing
#' check_packages(c("forecast", "tseries"), stop_on_missing = TRUE)
#'
#' # Use in conditional logic
#' if (check_packages("randomForest")) {
#'   # Use randomForest functionality
#' } else {
#'   # Fallback to base R methods
#' }
#' }
#'
#' @seealso \code{\link[base]{requireNamespace}}, \code{\link[utils]{install.packages}}
#' @export
check_packages <- function(packages, stop_on_missing = FALSE) {
  available <- sapply(packages, function(pkg) {
    requireNamespace(pkg, quietly = TRUE)
  })

  if (stop_on_missing && any(!available)) {
    missing <- packages[!available]
    stop(
      "Missing required R packages: ", paste(missing, collapse = ", "),
      "\nInstall with: install.packages(c(",
      paste(paste0('"', missing, '"'), collapse = ", "), "))"
    )
  }

  return(available)
}

#' Safe JSON serialization
#'
#' @description
#' Converts R objects to JSON with proper handling of special values,
#' data types that don't translate well to JSON, and consistent formatting
#' suitable for MCP protocol communication.
#'
#' @param obj R object to serialize (list, data.frame, vector, etc.)
#' @param pretty Logical, whether to format JSON with indentation (default: FALSE)
#'
#' @details
#' This function handles several problematic R-to-JSON conversions:
#' \itemize{
#'   \item \strong{Factors}: Automatically converted to character strings
#'   \item \strong{Special values}: NA/NaN/NULL properly handled as JSON null
#'   \item \strong{Precision}: Numeric values formatted with 10 decimal places
#'   \item \strong{Auto-unboxing}: Single-element vectors become scalars in JSON
#' }
#'
#' The resulting JSON is guaranteed to be valid and parseable by most
#' JSON libraries, including Python's standard json module.
#'
#' @return Character string containing valid JSON
#'
#' @examples
#' \dontrun{
#' # Basic serialization
#' data <- list(mean = 1.5, values = c(1, 2, 3), method = "linear")
#' json_str <- safe_json(data)
#'
#' # Handle factors properly
#' df <- data.frame(
#'   x = 1:3,
#'   category = factor(c("A", "B", "A"))
#' )
#' json_str <- safe_json(df) # category becomes character array
#'
#' # Pretty printing for debugging
#' json_pretty <- safe_json(data, pretty = TRUE)
#' cat(json_pretty)
#' }
#'
#' @seealso \code{\link[jsonlite]{toJSON}}, \code{\link{format_json_output}}
#' @export
safe_json <- function(obj, pretty = FALSE) {
  # Convert factors to characters
  obj <- rapply(obj, function(x) {
    if (is.factor(x)) {
      return(as.character(x))
    }
    return(x)
  }, how = "replace")

  jsonlite::toJSON(obj,
    auto_unbox = TRUE, pretty = pretty,
    null = "null", na = "null", digits = 10
  )
}
