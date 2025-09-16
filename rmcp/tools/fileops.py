"""
File operations tools for RMCP.

Data import, export, and file manipulation capabilities.
"""

from typing import Dict, Any
from ..registries.tools import tool
from ..core.schemas import table_schema
from ..r_integration import execute_r_script


@tool(
    name="read_csv",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "header": {"type": "boolean", "default": True},
            "sep": {"type": "string", "default": ","},
            "na_strings": {"type": "array", "items": {"type": "string"}, "default": ["", "NA", "NULL"]},
            "skip_rows": {"type": "integer", "minimum": 0, "default": 0},
            "max_rows": {"type": "integer", "minimum": 1}
        },
        "required": ["file_path"]
    },
    description="Read CSV files with flexible parsing options"
)
async def read_csv(context, params):
    """Read CSV file and return data."""
    
    await context.info("Reading CSV file", file_path=params.get("file_path"))
    
    r_script = '''
    file_path <- args$file_path
    header <- args$header %||% TRUE
    sep <- args$sep %||% ","
    na_strings <- args$na_strings %||% c("", "NA", "NULL")
    skip_rows <- args$skip_rows %||% 0
    max_rows <- args$max_rows
    
    # Check if file exists
    if (!file.exists(file_path)) {
        stop(paste("File not found:", file_path))
    }
    
    # Read CSV
    if (!is.null(max_rows)) {
        data <- read.csv(file_path, header = header, sep = sep, 
                        na.strings = na_strings, skip = skip_rows, nrows = max_rows)
    } else {
        data <- read.csv(file_path, header = header, sep = sep,
                        na.strings = na_strings, skip = skip_rows)
    }
    
    # Data summary
    numeric_vars <- names(data)[sapply(data, is.numeric)]
    character_vars <- names(data)[sapply(data, is.character)]
    factor_vars <- names(data)[sapply(data, is.factor)]
    
    result <- list(
        data = data,
        file_info = list(
            file_path = file_path,
            n_rows = nrow(data),
            n_cols = ncol(data),
            column_names = names(data),
            numeric_variables = numeric_vars,
            character_variables = character_vars,
            factor_variables = factor_vars
        ),
        parsing_info = list(
            header = header,
            separator = sep,
            na_strings = na_strings,
            rows_skipped = skip_rows
        )
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("CSV file read successfully",
                          rows=result["file_info"]["n_rows"],
                          cols=result["file_info"]["n_cols"])
        return result
        
    except Exception as e:
        await context.error("CSV reading failed", error=str(e))
        raise


@tool(
    name="write_csv", 
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "file_path": {"type": "string"},
            "include_rownames": {"type": "boolean", "default": False},
            "na_string": {"type": "string", "default": ""},
            "append": {"type": "boolean", "default": False}
        },
        "required": ["data", "file_path"]
    },
    description="Write data to CSV file with formatting options"
)
async def write_csv(context, params):
    """Write data to CSV file."""
    
    await context.info("Writing CSV file", file_path=params.get("file_path"))
    
    r_script = '''
    data <- as.data.frame(args$data)
    file_path <- args$file_path
    include_rownames <- args$include_rownames %||% FALSE
    na_string <- args$na_string %||% ""
    append_mode <- args$append %||% FALSE
    
    # Write CSV
    write.csv(data, file_path, row.names = include_rownames, na = na_string, append = append_mode)
    
    # Verify file was written
    if (!file.exists(file_path)) {
        stop(paste("Failed to write file:", file_path))
    }
    
    file_info <- file.info(file_path)
    
    result <- list(
        file_path = file_path,
        rows_written = nrow(data),
        cols_written = ncol(data), 
        file_size_bytes = file_info$size,
        success = TRUE,
        timestamp = as.character(Sys.time())
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("CSV file written successfully")
        return result
        
    except Exception as e:
        await context.error("CSV writing failed", error=str(e))
        raise


@tool(
    name="data_info",
    input_schema={
        "type": "object", 
        "properties": {
            "data": table_schema(),
            "include_sample": {"type": "boolean", "default": True},
            "sample_size": {"type": "integer", "minimum": 1, "maximum": 100, "default": 5}
        },
        "required": ["data"]
    },
    description="Get comprehensive information about a dataset"
)
async def data_info(context, params):
    """Get comprehensive dataset information."""
    
    await context.info("Analyzing dataset structure")
    
    r_script = '''
    data <- as.data.frame(args$data)
    include_sample <- args$include_sample %||% TRUE
    sample_size <- args$sample_size %||% 5
    
    # Basic info
    n_rows <- nrow(data)
    n_cols <- ncol(data)
    col_names <- names(data)
    
    # Variable types
    var_types <- sapply(data, class)
    numeric_vars <- names(data)[sapply(data, is.numeric)]
    character_vars <- names(data)[sapply(data, is.character)]
    factor_vars <- names(data)[sapply(data, is.factor)]
    logical_vars <- names(data)[sapply(data, is.logical)]
    date_vars <- names(data)[sapply(data, function(x) inherits(x, "Date"))]
    
    # Missing value analysis
    missing_counts <- sapply(data, function(x) sum(is.na(x)))
    missing_percentages <- missing_counts / n_rows * 100
    
    # Memory usage
    memory_usage <- object.size(data)
    
    result <- list(
        dimensions = list(rows = n_rows, columns = n_cols),
        variables = list(
            all = col_names,
            numeric = numeric_vars,
            character = character_vars, 
            factor = factor_vars,
            logical = logical_vars,
            date = date_vars
        ),
        variable_types = as.list(var_types),
        missing_values = list(
            counts = as.list(missing_counts),
            percentages = as.list(missing_percentages),
            total_missing = sum(missing_counts),
            complete_cases = sum(complete.cases(data))
        ),
        memory_usage_bytes = as.numeric(memory_usage)
    )
    
    # Add data sample if requested
    if (include_sample && n_rows > 0) {
        sample_rows <- min(sample_size, n_rows)
        result$sample_data <- head(data, sample_rows)
    }
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Dataset analysis completed successfully")
        return result
        
    except Exception as e:
        await context.error("Dataset analysis failed", error=str(e))
        raise


@tool(
    name="filter_data",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "conditions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "variable": {"type": "string"},
                        "operator": {"type": "string", "enum": ["==", "!=", ">", "<", ">=", "<=", "%in%", "!%in%"]},
                        "value": {}
                    },
                    "required": ["variable", "operator", "value"]
                }
            },
            "logic": {"type": "string", "enum": ["AND", "OR"], "default": "AND"}
        },
        "required": ["data", "conditions"]
    },
    description="Filter data based on multiple conditions"
)
async def filter_data(context, params):
    """Filter data based on conditions."""
    
    await context.info("Filtering data")
    
    r_script = '''
    if (!require(dplyr)) install.packages("dplyr", quietly = TRUE)
    library(dplyr)
    
    data <- as.data.frame(args$data)
    conditions <- args$conditions
    logic <- args$logic %||% "AND"
    
    # Build filter expressions
    filter_expressions <- c()
    
    for (condition in conditions) {
        var <- condition$variable
        op <- condition$operator
        val <- condition$value
        
        if (op == "%in%") {
            expr <- paste0(var, " %in% c(", paste(paste0("'", val, "'"), collapse = ","), ")")
        } else if (op == "!%in%") {
            expr <- paste0("!(", var, " %in% c(", paste(paste0("'", val, "'"), collapse = ","), "))")
        } else if (is.character(val)) {
            expr <- paste0(var, " ", op, " '", val, "'")
        } else {
            expr <- paste0(var, " ", op, " ", val)
        }
        
        filter_expressions <- c(filter_expressions, expr)
    }
    
    # Combine expressions
    if (logic == "AND") {
        full_expression <- paste(filter_expressions, collapse = " & ")
    } else {
        full_expression <- paste(filter_expressions, collapse = " | ")
    }
    
    # Apply filter
    filtered_data <- data %>% filter(eval(parse(text = full_expression)))
    
    result <- list(
        data = filtered_data,
        filter_expression = full_expression,
        original_rows = nrow(data),
        filtered_rows = nrow(filtered_data),
        rows_removed = nrow(data) - nrow(filtered_data),
        removal_percentage = (nrow(data) - nrow(filtered_data)) / nrow(data) * 100
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Data filtered successfully")
        return result
        
    except Exception as e:
        await context.error("Data filtering failed", error=str(e))
        raise