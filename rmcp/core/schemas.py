"""
JSON Schema validation helpers.
Provides utilities for:
- Schema validation with proper MCP error codes (-32602)
- Common schema patterns for statistical tools
- Type conversion helpers
"""

from typing import Any

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate


class SchemaError(Exception):
    """Schema validation error with MCP error code."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field
        self.code = -32602  # JSON-RPC invalid params error


def validate_schema(data: Any, schema: dict[str, Any], context: str = "") -> None:
    """
    Validate data against JSON schema.
    Raises SchemaError with MCP-compatible error code on failure.
    """
    try:
        validate(instance=data, schema=schema)
    except JsonSchemaValidationError as e:
        field_path = ".".join(str(p) for p in e.absolute_path)
        error_context = f" in {context}" if context else ""
        field_info = f" (field: {field_path})" if field_path else ""
        raise SchemaError(
            f"Schema validation failed{error_context}: {e.message}{field_info}",
            field=field_path,
        ) from e
    except Exception as e:
        raise SchemaError(f"Schema validation error: {str(e)}") from e


# Common schema patterns for statistical tools
def table_schema(required_columns: list[str] | None = None) -> dict[str, Any]:
    """Schema for tabular data (dict with column arrays)."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "additionalProperties": {
            "type": "array",
            "items": {"type": ["number", "string", "null"]},
        },
    }
    if required_columns:
        schema["required"] = required_columns
        properties = schema["properties"]
        for col in required_columns:
            properties[col] = {
                "type": "array",
                "items": {"type": ["number", "string", "null"]},
            }
    return schema


def formula_schema() -> dict[str, Any]:
    """Schema for R formula strings."""
    return {
        "type": "string",
        "pattern": r"^[^~]+~[^~]+$",
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
