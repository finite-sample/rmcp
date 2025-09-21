"""
File operations tools for RMCP.

Data import, export, and file manipulation capabilities.
"""

from typing import Any

from ..core.schemas import table_schema
from ..r_integration import execute_r_script_async
from ..registries.tools import tool


@tool(
    name="read_csv",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "header": {"type": "boolean", "default": True},
            "sep": {"type": "string", "default": ","},
            "na_strings": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["", "NA", "NULL"],
            },
            "skip_rows": {"type": "integer", "minimum": 0, "default": 0},
            "max_rows": {"type": "integer", "minimum": 1},
        },
        "required": ["file_path"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "CSV data in column-wise format",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": ["string", "number", "boolean", "null"]},
                },
            },
            "file_info": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "is_url": {"type": "boolean"},
                    "n_rows": {"type": "integer", "minimum": 0},
                    "n_cols": {"type": "integer", "minimum": 0},
                    "column_names": {"type": "array", "items": {"type": "string"}},
                    "numeric_variables": {"type": "array", "items": {"type": "string"}},
                    "character_variables": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "factor_variables": {"type": "array", "items": {"type": "string"}},
                    "file_size_bytes": {"type": ["number", "null"]},
                    "modified_date": {"type": ["string", "null"]},
                },
                "description": "File metadata and structure information",
            },
            "parsing_info": {
                "type": "object",
                "properties": {
                    "header": {"type": "boolean"},
                    "separator": {"type": "string"},
                    "na_strings": {"type": "array", "items": {"type": "string"}},
                    "rows_skipped": {"type": "integer", "minimum": 0},
                },
                "description": "Parsing parameters used",
            },
            "summary": {
                "type": "object",
                "properties": {
                    "rows_read": {"type": "integer", "minimum": 0},
                    "columns_read": {"type": "integer", "minimum": 0},
                    "column_types": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    "missing_values": {
                        "type": "object",
                        "additionalProperties": {"type": "integer"},
                    },
                    "sample_data": {
                        "type": "object",
                        "description": "First few rows as sample",
                    },
                },
                "description": "Data summary and quality information",
            },
        },
        "required": ["data", "file_info", "parsing_info", "summary"],
        "additionalProperties": False,
    },
    description="Read CSV files with flexible parsing options",
)
async def read_csv(context, params) -> dict[str, Any]:
    """Read CSV file and return data."""

    await context.info("Reading CSV file", file_path=params.get("file_path"))

    r_script = """
    
    file_path <- args$file_path
    header <- args$header %||% TRUE
    sep <- args$sep %||% ","
    na_strings <- args$na_strings %||% c("", "NA", "NULL")
    skip_rows <- args$skip_rows %||% 0
    max_rows <- args$max_rows
    
    # Check if it's a URL or local file
    is_url <- grepl("^https?://", file_path)
    
    if (is_url) {
        # Read from URL
        if (!is.null(max_rows)) {
            data <- read.csv(url(file_path), header = header, sep = sep, 
                            na.strings = na_strings, skip = skip_rows, nrows = max_rows)
        } else {
            data <- read.csv(url(file_path), header = header, sep = sep,
                            na.strings = na_strings, skip = skip_rows)
        }
    } else {
        # Check if local file exists
        if (!file.exists(file_path)) {
            stop(paste("File not found:", file_path))
        }
        
        # Read local CSV
        if (!is.null(max_rows)) {
            data <- read.csv(file_path, header = header, sep = sep, 
                            na.strings = na_strings, skip = skip_rows, nrows = max_rows)
        } else {
            data <- read.csv(file_path, header = header, sep = sep,
                            na.strings = na_strings, skip = skip_rows)
        }
    }
    
    # Data summary
    numeric_vars <- names(data)[sapply(data, is.numeric)]
    character_vars <- names(data)[sapply(data, is.character)]
    factor_vars <- names(data)[sapply(data, is.factor)]
    
    # Get file info if it's a local file
    if (!is_url) {
        file_info_obj <- file.info(file_path)
        file_size <- file_info_obj$size
        modified_date <- as.character(file_info_obj$mtime)
    } else {
        file_size <- NA
        modified_date <- NA
    }
    
    result <- list(
        data = data,
        file_info = list(
            file_path = file_path,
            is_url = is_url,
            n_rows = nrow(data),
            n_cols = ncol(data),
            column_names = names(data),
            numeric_variables = numeric_vars,
            character_variables = character_vars,
            factor_variables = factor_vars,
            file_size_bytes = file_size,
            modified_date = modified_date
        ),
        parsing_info = list(
            header = header,
            separator = sep,
            na_strings = na_strings,
            rows_skipped = skip_rows
        ),
        summary = list(
            rows_read = nrow(data),
            columns_read = ncol(data),
            column_types = sapply(data, class),
            missing_values = sapply(data, function(x) sum(is.na(x))),
            sample_data = if(nrow(data) > 0) head(data, 3) else data.frame()
        )
    )
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info(
            "CSV file read successfully",
            rows=result["file_info"]["n_rows"],
            cols=result["file_info"]["n_cols"],
        )
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
            "append": {"type": "boolean", "default": False},
        },
        "required": ["data", "file_path"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path where the file was written",
            },
            "rows_written": {
                "type": "integer",
                "description": "Number of rows written to file",
                "minimum": 0,
            },
            "cols_written": {
                "type": "integer",
                "description": "Number of columns written to file",
                "minimum": 0,
            },
            "file_size_bytes": {
                "type": "number",
                "description": "Size of the written file in bytes",
                "minimum": 0,
            },
            "success": {
                "type": "boolean",
                "enum": [True],
                "description": "Whether the file was written successfully",
            },
            "timestamp": {
                "type": "string",
                "description": "Timestamp when the file was written",
            },
        },
        "required": [
            "file_path",
            "rows_written",
            "cols_written",
            "file_size_bytes",
            "success",
            "timestamp",
        ],
        "additionalProperties": False,
    },
    description="Write data to CSV file with formatting options",
)
async def write_csv(context, params) -> dict[str, Any]:
    """Write data to CSV file."""

    await context.info("Writing CSV file", file_path=params.get("file_path"))

    r_script = """
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
    """

    try:
        result = await execute_r_script_async(r_script, params)
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
            "sample_size": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 5,
            },
        },
        "required": ["data"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "dimensions": {
                "type": "object",
                "properties": {
                    "rows": {"type": "integer", "minimum": 0},
                    "columns": {"type": "integer", "minimum": 0},
                },
                "description": "Dataset dimensions",
            },
            "variables": {
                "type": "object",
                "properties": {
                    "all": {"type": "array", "items": {"type": "string"}},
                    "numeric": {"type": "array", "items": {"type": "string"}},
                    "character": {"type": "array", "items": {"type": "string"}},
                    "factor": {"type": "array", "items": {"type": "string"}},
                    "logical": {"type": "array", "items": {"type": "string"}},
                    "date": {"type": "array", "items": {"type": "string"}},
                },
                "description": "Variables grouped by data type",
            },
            "variable_types": {
                "type": "object",
                "description": "Data type for each variable",
                "additionalProperties": {"type": "string"},
            },
            "missing_values": {
                "type": "object",
                "properties": {
                    "counts": {
                        "type": "object",
                        "additionalProperties": {"type": "integer"},
                        "description": "Missing value count per variable",
                    },
                    "percentages": {
                        "type": "object",
                        "additionalProperties": {"type": "number"},
                        "description": "Missing value percentage per variable",
                    },
                    "total_missing": {"type": "integer", "minimum": 0},
                    "complete_cases": {"type": "integer", "minimum": 0},
                },
                "description": "Missing value analysis",
            },
            "memory_usage_bytes": {
                "type": "number",
                "description": "Memory usage of the dataset in bytes",
                "minimum": 0,
            },
            "sample_data": {
                "type": "object",
                "description": "Sample of the first few rows (if requested)",
            },
        },
        "required": [
            "dimensions",
            "variables",
            "variable_types",
            "missing_values",
            "memory_usage_bytes",
        ],
        "additionalProperties": False,
    },
    description="Get comprehensive information about a dataset",
)
async def data_info(context, params) -> dict[str, Any]:
    """Get comprehensive dataset information."""

    await context.info("Analyzing dataset structure")

    r_script = """
    data <- as.data.frame(args$data)
    include_sample <- args$include_sample %||% TRUE
    sample_size <- args$sample_size %||% 5
    
    # Basic info
    n_rows <- nrow(data)
    n_cols <- ncol(data)
    col_names <- names(data)
    
    # Variable types - ensure all are arrays
    var_types <- sapply(data, class)
    numeric_vars <- names(data)[sapply(data, is.numeric)]
    character_vars <- names(data)[sapply(data, is.character)]
    factor_vars <- names(data)[sapply(data, is.factor)]
    logical_vars <- names(data)[sapply(data, is.logical)]
    date_vars <- names(data)[sapply(data, function(x) inherits(x, "Date"))]
    
    # Ensure variables are always arrays even if empty or single
    numeric_vars <- if (length(numeric_vars) == 0) character(0) else as.character(numeric_vars)
    character_vars <- if (length(character_vars) == 0) character(0) else as.character(character_vars)
    factor_vars <- if (length(factor_vars) == 0) character(0) else as.character(factor_vars)
    logical_vars <- if (length(logical_vars) == 0) character(0) else as.character(logical_vars)
    date_vars <- if (length(date_vars) == 0) character(0) else as.character(date_vars)
    
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
        result$sample_data <- as.list(head(data, sample_rows))
    }
    
    cat(toJSON(result, auto_unbox = FALSE, na = "null"))
    """

    try:
        result = await execute_r_script_async(r_script, params)
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
                        "operator": {
                            "type": "string",
                            "enum": ["==", "!=", ">", "<", ">=", "<=", "%in%", "!%in%"],
                        },
                        "value": {},
                    },
                    "required": ["variable", "operator", "value"],
                },
            },
            "logic": {"type": "string", "enum": ["AND", "OR"], "default": "AND"},
        },
        "required": ["data", "conditions"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "Filtered dataset in column-wise format",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": ["string", "number", "boolean", "null"]},
                },
            },
            "filter_expression": {
                "type": "string",
                "description": "R expression used for filtering",
            },
            "original_rows": {
                "type": "integer",
                "description": "Number of rows in original dataset",
                "minimum": 0,
            },
            "filtered_rows": {
                "type": "integer",
                "description": "Number of rows after filtering",
                "minimum": 0,
            },
            "rows_removed": {
                "type": "integer",
                "description": "Number of rows removed by filtering",
                "minimum": 0,
            },
            "removal_percentage": {
                "type": "number",
                "description": "Percentage of rows removed",
                "minimum": 0,
                "maximum": 100,
            },
        },
        "required": [
            "data",
            "filter_expression",
            "original_rows",
            "filtered_rows",
            "rows_removed",
            "removal_percentage",
        ],
        "additionalProperties": False,
    },
    description="Filter data based on multiple conditions",
)
async def filter_data(context, params) -> dict[str, Any]:
    """Filter data based on conditions."""

    await context.info("Filtering data")

    r_script = """
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
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Data filtered successfully")
        return result

    except Exception as e:
        await context.error("Data filtering failed", error=str(e))
        raise


@tool(
    name="read_excel",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "sheet_name": {
                "type": "string",
                "description": "Sheet name or index (default: first sheet)",
            },
            "header": {"type": "boolean", "default": True},
            "skip_rows": {"type": "integer", "minimum": 0, "default": 0},
            "max_rows": {"type": "integer", "minimum": 1},
            "cell_range": {
                "type": "string",
                "description": "Excel range like 'A1:D100'",
            },
            "na_strings": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["", "NA", "NULL"],
            },
        },
        "required": ["file_path"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "Excel data in column-wise format",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": ["string", "number", "boolean", "null"]},
                },
            },
            "file_info": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "sheet_name": {"type": "string"},
                    "available_sheets": {"type": "array", "items": {"type": "string"}},
                    "rows": {"type": "integer", "minimum": 0},
                    "columns": {"type": "integer", "minimum": 0},
                    "column_names": {"type": "array", "items": {"type": "string"}},
                    "file_size_bytes": {"type": "number", "minimum": 0},
                    "modified_date": {"type": "string"},
                },
                "description": "Excel file metadata and structure information",
            },
            "summary": {
                "type": "object",
                "properties": {
                    "rows_read": {"type": "integer", "minimum": 0},
                    "columns_read": {"type": "integer", "minimum": 0},
                    "column_types": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    "missing_values": {
                        "type": "object",
                        "additionalProperties": {"type": "integer"},
                    },
                    "sample_data": {
                        "type": "object",
                        "description": "First few rows as sample",
                    },
                },
                "description": "Data summary and quality information",
            },
        },
        "required": ["data", "file_info", "summary"],
        "additionalProperties": False,
    },
    description="Read Excel files (.xlsx, .xls) with flexible sheet and range selection",
)
async def read_excel(context, params) -> dict[str, Any]:
    """Read Excel file and return data."""

    await context.info("Reading Excel file", file_path=params.get("file_path"))

    r_script = """
    library(readxl)
    
    file_path <- args$file_path
    sheet_name <- args$sheet_name
    header <- args$header %||% TRUE
    skip_rows <- args$skip_rows %||% 0
    max_rows <- args$max_rows
    cell_range <- args$cell_range
    na_strings <- args$na_strings %||% c("", "NA", "NULL")
    
    # Check if file exists
    if (!file.exists(file_path)) {
        stop(paste("File not found:", file_path))
    }
    
    # Check file extension
    file_ext <- tolower(tools::file_ext(file_path))
    if (!file_ext %in% c("xlsx", "xls")) {
        stop("File must be .xlsx or .xls format")
    }
    
    # Get sheet information
    sheet_names <- excel_sheets(file_path)
    
    # Determine which sheet to read
    if (is.null(sheet_name)) {
        sheet_to_read <- 1  # Default to first sheet
        actual_sheet_name <- sheet_names[1]
    } else {
        if (is.numeric(sheet_name)) {
            sheet_to_read <- as.integer(sheet_name)
            actual_sheet_name <- sheet_names[sheet_to_read]
        } else {
            if (sheet_name %in% sheet_names) {
                sheet_to_read <- sheet_name
                actual_sheet_name <- sheet_name
            } else {
                stop(paste("Sheet not found:", sheet_name, ". Available sheets:", paste(sheet_names, collapse=", ")))
            }
        }
    }
    
    # Read Excel file with parameters
    read_args <- list(
        path = file_path,
        sheet = sheet_to_read,
        col_names = header,
        skip = skip_rows,
        na = na_strings
    )
    
    # Add optional parameters
    if (!is.null(max_rows)) {
        read_args$n_max <- max_rows
    }
    
    if (!is.null(cell_range)) {
        read_args$range <- cell_range
    }
    
    # Read the data
    data <- do.call(read_excel, read_args)
    
    # Convert to data frame
    data <- as.data.frame(data)
    
    # Get file info
    file_info <- file.info(file_path)
    
    result <- list(
        data = data,
        file_info = list(
            file_path = file_path,
            sheet_name = actual_sheet_name,
            available_sheets = sheet_names,
            rows = nrow(data),
            columns = ncol(data),
            column_names = colnames(data),
            file_size_bytes = file_info$size,
            modified_date = as.character(file_info$mtime)
        ),
        summary = list(
            rows_read = nrow(data),
            columns_read = ncol(data),
            column_types = sapply(data, class),
            missing_values = sapply(data, function(x) sum(is.na(x))),
            sample_data = if(nrow(data) > 0) head(data, 3) else data.frame()
        )
    )
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info(
            "Excel file read successfully",
            rows=result["file_info"]["rows"],
            columns=result["file_info"]["columns"],
        )
        return result

    except Exception as e:
        await context.error("Excel file reading failed", error=str(e))
        raise


@tool(
    name="read_json",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "flatten": {
                "type": "boolean",
                "default": True,
                "description": "Flatten nested JSON to tabular format",
            },
            "max_depth": {
                "type": "integer",
                "minimum": 1,
                "default": 3,
                "description": "Maximum nesting depth to flatten",
            },
            "array_to_rows": {
                "type": "boolean",
                "default": True,
                "description": "Convert JSON arrays to separate rows",
            },
        },
        "required": ["file_path"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "JSON data converted to column-wise format",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": ["string", "number", "boolean", "null"]},
                },
            },
            "file_info": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "rows": {"type": "integer", "minimum": 0},
                    "columns": {"type": "integer", "minimum": 0},
                    "column_names": {"type": "array", "items": {"type": "string"}},
                    "file_size_bytes": {"type": ["number", "null"]},
                    "modified_date": {"type": ["string", "null"]},
                    "is_url": {"type": "boolean"},
                },
                "description": "JSON file metadata and structure information",
            },
            "summary": {
                "type": "object",
                "properties": {
                    "rows_read": {"type": "integer", "minimum": 0},
                    "columns_read": {"type": "integer", "minimum": 0},
                    "column_types": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    "missing_values": {
                        "type": "object",
                        "additionalProperties": {"type": "integer"},
                    },
                    "sample_data": {
                        "type": "object",
                        "description": "First few rows as sample",
                    },
                },
                "description": "Data summary and quality information",
            },
        },
        "required": ["data", "file_info", "summary"],
        "additionalProperties": False,
    },
    description="Read JSON files and convert to tabular format",
)
async def read_json(context, params) -> dict[str, Any]:
    """Read JSON file and return data."""

    await context.info("Reading JSON file", file_path=params.get("file_path"))

    r_script = """
    library(jsonlite)
    library(dplyr)
    
    file_path <- args$file_path
    flatten_data <- args$flatten %||% TRUE
    max_depth <- args$max_depth %||% 3
    array_to_rows <- args$array_to_rows %||% TRUE
    
    # Check if file exists
    if (!file.exists(file_path)) {
        stop(paste("File not found:", file_path))
    }
    
    # Check if it's a URL
    if (grepl("^https?://", file_path)) {
        # Read from URL
        json_data <- fromJSON(file_path, flatten = flatten_data)
    } else {
        # Read from local file
        json_data <- fromJSON(file_path, flatten = flatten_data)
    }
    
    # Convert to data frame if possible
    if (is.list(json_data) && !is.data.frame(json_data)) {
        # Try to convert list to data frame
        if (all(sapply(json_data, length) == length(json_data[[1]]))) {
            # All elements same length - can convert directly
            data <- as.data.frame(json_data, stringsAsFactors = FALSE)
        } else {
            # Unequal lengths - need to flatten differently
            data <- json_data %>% 
                   as.data.frame(stringsAsFactors = FALSE)
        }
    } else if (is.data.frame(json_data)) {
        data <- json_data
    } else {
        # Create single-column data frame
        data <- data.frame(value = json_data, stringsAsFactors = FALSE)
    }
    
    # Get file info
    if (!grepl("^https?://", file_path)) {
        file_info <- file.info(file_path)
        file_size <- file_info$size
        modified_date <- as.character(file_info$mtime)
    } else {
        file_size <- NA
        modified_date <- NA
    }
    
    result <- list(
        data = as.list(data),  # Convert to column-wise format for schema compatibility
        file_info = list(
            file_path = file_path,
            rows = nrow(data),
            columns = ncol(data),
            column_names = colnames(data),
            file_size_bytes = file_size,
            modified_date = modified_date,
            is_url = grepl("^https?://", file_path)
        ),
        summary = list(
            rows_read = nrow(data),
            columns_read = ncol(data),
            column_types = sapply(data, class),
            missing_values = sapply(data, function(x) sum(is.na(x))),
            sample_data = if(nrow(data) > 0) head(data, 3) else data.frame()
        )
    )
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info(
            "JSON file read successfully",
            rows=result["file_info"]["rows"],
            columns=result["file_info"]["columns"],
        )
        return result

    except Exception as e:
        await context.error("JSON file reading failed", error=str(e))
        raise
