"""
JSON Schema validation helpers.
Provides utilities for:
- Schema validation with proper MCP error codes (-32602)
- Common schema patterns for statistical tools
- Type conversion helpers
"""

import re
from typing import Any

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate


class SchemaError(Exception):
    """Schema validation error with MCP error code."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field
        self.code = -32602  # JSON-RPC invalid params error


_FORMULA_CHARACTERS = re.compile(r"^[A-Za-z0-9_.\s~+\-*/:^(),]+$")
_FORMULA_CALL = re.compile(r"([A-Za-z.][A-Za-z0-9_.]*)\s*\(")
_ALLOWED_FORMULA_CALLS = {
    "I",
    "abs",
    "as.factor",
    "exp",
    "factor",
    "log",
    "log10",
    "log1p",
    "poly",
    "scale",
    "sqrt",
}


def _validate_formula(value: str, context: str) -> None:
    """Reject formula syntax that can evaluate arbitrary R code."""
    if "::" in value or not _FORMULA_CHARACTERS.fullmatch(value):
        raise SchemaError(
            f"Unsafe or unsupported R formula syntax in {context}", field=context
        )
    calls = set(_FORMULA_CALL.findall(value))
    unsupported = sorted(calls - _ALLOWED_FORMULA_CALLS)
    if unsupported:
        raise SchemaError(
            f"Unsupported formula function(s) in {context}: {', '.join(unsupported)}",
            field=context,
        )


def _validate_rmcp_extensions(data: Any, schema: dict[str, Any], path: str) -> None:
    """Apply RMCP's cross-field constraints after JSON Schema validation."""
    if schema.get("x-rmcp-table") and isinstance(data, dict):
        if not data:
            raise SchemaError(
                f"Tabular data in {path} must contain at least one column"
            )
        lengths = {name: len(values) for name, values in data.items()}
        if len(set(lengths.values())) != 1:
            rendered = ", ".join(f"{name}={length}" for name, length in lengths.items())
            raise SchemaError(
                f"Tabular columns in {path} must have equal lengths ({rendered})"
            )
        if next(iter(lengths.values())) == 0:
            raise SchemaError(f"Tabular data in {path} must contain at least one row")

    if schema.get("x-rmcp-formula") and isinstance(data, str):
        _validate_formula(data, path)

    if isinstance(data, dict):
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties")
        for key, value in data.items():
            child_schema = properties.get(key)
            if child_schema is None and isinstance(additional, dict):
                child_schema = additional
            if isinstance(child_schema, dict):
                _validate_rmcp_extensions(value, child_schema, f"{path}.{key}")
    elif isinstance(data, list) and isinstance(schema.get("items"), dict):
        for index, value in enumerate(data):
            _validate_rmcp_extensions(value, schema["items"], f"{path}[{index}]")


def validate_schema(data: Any, schema: dict[str, Any], context: str = "") -> None:
    """
    Validate data against JSON schema.
    Raises SchemaError with MCP-compatible error code on failure.
    """
    try:
        validate(instance=data, schema=schema)
        _validate_rmcp_extensions(data, schema, context or "value")
    except JsonSchemaValidationError as e:
        field_path = ".".join(str(p) for p in e.absolute_path)
        error_context = f" in {context}" if context else ""
        field_info = f" (field: {field_path})" if field_path else ""
        raise SchemaError(
            f"Schema validation failed{error_context}: {e.message}{field_info}",
            field=field_path,
        ) from e
    except SchemaError:
        raise
    except Exception as e:
        raise SchemaError(f"Schema validation error: {str(e)}") from e


# Common schema patterns for statistical tools
def table_schema(required_columns: list[str] | None = None) -> dict[str, Any]:
    """Schema for tabular data (dict with column arrays)."""
    schema: dict[str, Any] = {
        "type": "object",
        "x-rmcp-table": True,
        "properties": {},
        "additionalProperties": {
            "type": "array",
            "items": {"type": ["number", "string", "boolean", "null"]},
        },
    }
    if required_columns:
        schema["required"] = required_columns
        properties = schema["properties"]
        for col in required_columns:
            properties[col] = {
                "type": "array",
                "items": {"type": ["number", "string", "boolean", "null"]},
            }
    return schema


def formula_schema() -> dict[str, Any]:
    """Schema for R formula strings."""
    return {
        "type": "string",
        "pattern": r"^[^~]+~[^~]+$",
        "x-rmcp-formula": True,
        "description": "R formula (e.g., 'y ~ x1 + x2')",
    }


def numeric_array_schema(min_length: int = 1) -> dict[str, Any]:
    """Schema for numeric arrays."""
    return {"type": "array", "items": {"type": "number"}, "minItems": min_length}


def positive_number_schema() -> dict[str, Any]:
    """Schema for positive numbers."""
    return {"type": "number", "minimum": 0, "exclusiveMinimum": True}


def confidence_level_schema() -> dict[str, Any]:
    """Schema for confidence levels (0-1)."""
    return {
        "type": "number",
        "minimum": 0,
        "maximum": 1,
        "exclusiveMinimum": True,
        "exclusiveMaximum": True,
    }


def choice_schema(choices: list[str]) -> dict[str, Any]:
    """Schema for enumerated choices."""
    return {"type": "string", "enum": choices}


def image_content_schema() -> dict[str, Any]:
    """Schema for image content in MCP responses."""
    return {
        "type": "object",
        "properties": {
            "type": {"type": "string", "const": "image"},
            "data": {"type": "string", "description": "Base64 encoded image"},
            "mimeType": {
                "type": "string",
                "enum": ["image/png", "image/jpeg", "image/svg+xml"],
            },
            "alt": {"type": "string", "description": "Alternative text description"},
        },
        "required": ["type", "data", "mimeType"],
    }


def text_content_schema() -> dict[str, Any]:
    """Schema for text content in MCP responses."""
    return {
        "type": "object",
        "properties": {
            "type": {"type": "string", "const": "text"},
            "text": {"type": "string", "description": "Text content"},
        },
        "required": ["type", "text"],
    }


def mcp_content_schema() -> dict[str, Any]:
    """Schema for MCP content arrays (text and/or images)."""
    return {
        "type": "array",
        "items": {"anyOf": [text_content_schema(), image_content_schema()]},
        "minItems": 1,
    }


# Tool result schemas
def statistical_result_schema() -> dict[str, Any]:
    """Base schema for statistical analysis results."""
    return {
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "data": {"type": "object"},
            "metadata": {
                "type": "object",
                "properties": {
                    "method": {"type": "string"},
                    "n_obs": {"type": "integer", "minimum": 0},
                    "timestamp": {"type": "string", "format": "date-time"},
                },
            },
        },
        "required": ["success"],
    }


def error_result_schema() -> dict[str, Any]:
    """Schema for error results."""
    return {
        "type": "object",
        "properties": {
            "success": {"const": False},
            "error": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "message": {"type": "string"},
                    "details": {"type": "object"},
                },
                "required": ["type", "message"],
            },
        },
        "required": ["success", "error"],
    }
