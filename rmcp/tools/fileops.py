"""
File operations tools for RMCP.
Data import, export, and file manipulation capabilities.
"""

from typing import Any

from ..core.schemas import table_schema
from ..r_assets.loader import get_r_script
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
                        "type": ["object", "array"],
                        "description": "First few rows as sample",
                    },
                },
                "description": "Data summary and quality information",
            },
        },
        "required": ["data", "file_info", "parsing_info", "summary"],
        "additionalProperties": False,
    },
    description="Reads CSV (Comma-Separated Values) files with flexible parsing options including custom separators, header handling, missing value specifications, and row/column selection. Automatically detects data types and handles various CSV formats. Use for importing datasets, loading experimental data, processing survey results, or reading any tabular data stored in CSV format. Essential first step in most data analysis workflows.",
)
async def read_csv(context, params) -> dict[str, Any]:
    """Read CSV file and return data."""
    await context.info("Reading CSV file", file_path=params.get("file_path"))

    # Load R script from separated file
    r_script = get_r_script("fileops", "read_csv")
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
    description="Writes data to CSV files with customizable formatting options including separators, missing value representations, decimal precision, and column selection. Preserves data types and handles special characters appropriately. Use for exporting analysis results, sharing datasets, creating backups, or preparing data for other applications. Standard format for data interchange and archival.",
)
async def write_csv(context, params) -> dict[str, Any]:
    """Write data to CSV file."""
    await context.info("Writing CSV file", file_path=params.get("file_path"))

    # Load R script from separated file
    r_script = get_r_script("fileops", "write_csv")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("CSV file written successfully")
        return result
    except Exception as e:
        await context.error("CSV writing failed", error=str(e))
        raise


@tool(
    name="write_excel",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "file_path": {"type": "string"},
            "sheet_name": {"type": "string", "default": "Sheet1"},
            "include_rownames": {"type": "boolean", "default": False},
        },
        "required": ["data", "file_path"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path where the Excel file was written",
            },
            "sheet_name": {
                "type": "string",
                "description": "Name of the worksheet where data was written",
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
            "sheet_name",
            "rows_written",
            "cols_written",
            "file_size_bytes",
            "success",
            "timestamp",
        ],
        "additionalProperties": False,
    },
    description="Writes data to Excel files (.xlsx) with advanced formatting including multiple worksheets, custom sheet names, cell formatting, and metadata. Preserves data types and provides professional presentation options. Use for business reports, stakeholder presentations, multi-table datasets, or when advanced formatting and multiple sheets are required for data delivery.",
)
async def write_excel(context, params) -> dict[str, Any]:
    """Write data to Excel file."""
    await context.info("Writing Excel file", file_path=params.get("file_path"))

    # Load R script from separated file
    r_script = get_r_script("fileops", "write_excel")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Excel file written successfully")
        return result
    except Exception as e:
        await context.error("Excel writing failed", error=str(e))
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
                "type": ["object", "array"],
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
    description="Provides comprehensive dataset information including dimensions, column names, data types, missing value counts, memory usage, and basic statistics summary. Essential for initial data exploration and quality assessment. Use to understand dataset structure, identify data quality issues, check for missing values, or generate data documentation and metadata reports.",
)
async def data_info(context, params) -> dict[str, Any]:
    """Get comprehensive dataset information."""
    await context.info("Analyzing dataset structure")

    # Load R script from separated file
    r_script = get_r_script("fileops", "data_info")
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
    description="Filters datasets using multiple logical conditions with support for numeric comparisons, string matching, date ranges, and complex boolean logic. Supports AND/OR operations and missing value handling. Use for data subsetting, creating analysis samples, removing outliers, selecting specific time periods, or preparing data for focused analysis on particular subgroups.",
)
async def filter_data(context, params) -> dict[str, Any]:
    """Filter data based on conditions."""
    await context.info("Filtering data")

    # Load R script from separated file
    r_script = get_r_script("fileops", "filter_data")
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
                        "type": ["object", "array"],
                        "description": "First few rows as sample",
                    },
                },
                "description": "Data summary and quality information",
            },
        },
        "required": ["data", "file_info", "summary"],
        "additionalProperties": False,
    },
    description="Reads Excel files (.xlsx, .xls) with flexible options for sheet selection, cell ranges, header detection, and data type specification. Handles multiple worksheets and complex Excel formatting. Use for importing business data, reading formatted reports, processing multi-sheet workbooks, or accessing data stored in Excel's native format with preserving original structure.",
)
async def read_excel(context, params) -> dict[str, Any]:
    """Read Excel file and return data."""
    await context.info("Reading Excel file", file_path=params.get("file_path"))

    # Load R script from separated file
    r_script = get_r_script("fileops", "read_excel")
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
                        "type": ["object", "array"],
                        "description": "First few rows as sample",
                    },
                },
                "description": "Data summary and quality information",
            },
        },
        "required": ["data", "file_info", "summary"],
        "additionalProperties": False,
    },
    description="Reads JSON files and intelligently converts nested structures to tabular format suitable for statistical analysis. Handles nested objects, arrays, and mixed data types with flexible flattening options. Use for importing API responses, web scraping results, NoSQL database exports, or any hierarchical data that needs conversion to rectangular format for analysis.",
)
async def read_json(context, params) -> dict[str, Any]:
    """Read JSON file and return data."""
    await context.info("Reading JSON file", file_path=params.get("file_path"))

    # Load R script from separated file
    r_script = get_r_script("fileops", "read_json")
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


@tool(
    name="write_json",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "file_path": {"type": "string"},
            "pretty": {"type": "boolean", "default": True},
            "auto_unbox": {"type": "boolean", "default": True},
        },
        "required": ["data", "file_path"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path where the JSON file was written",
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
            "variables_written": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Names of variables/columns written",
            },
            "file_size_bytes": {
                "type": "number",
                "description": "Size of the written file in bytes",
                "minimum": 0,
            },
            "pretty_formatted": {
                "type": "boolean",
                "description": "Whether the JSON was formatted with indentation",
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
            "variables_written",
            "file_size_bytes",
            "pretty_formatted",
            "success",
            "timestamp",
        ],
        "additionalProperties": False,
    },
    description="Writes data to JSON files using column-wise format optimized for statistical software with customizable formatting and compression options. Maintains data type information and handles missing values appropriately. Use for creating web API responses, exporting data for JavaScript applications, archiving datasets, or preparing data for JSON-based analytics platforms.",
)
async def write_json(context, params) -> dict[str, Any]:
    """Write data to JSON file."""
    await context.info("Writing JSON file", file_path=params.get("file_path"))

    # Load R script from separated file
    r_script = get_r_script("fileops", "write_json")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("JSON file written successfully")
        return result
    except Exception as e:
        await context.error("JSON writing failed", error=str(e))
        raise
