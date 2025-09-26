#!/usr/bin/env python3
"""
Schema validation and functional tests for file operation tools.
Tests input schema validation and file operations without R execution where possible.
"""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from rmcp.core.context import Context, LifespanState
from rmcp.tools.fileops import (
    data_info,
    filter_data,
    read_csv,
    read_excel,
    read_json,
    write_csv,
    write_excel,
    write_json,
)


async def create_test_context():
    """Create a test context for tool execution."""
    lifespan = LifespanState()
    context = Context.create("test", "test", lifespan)
    return context


class TestFileOpsSchemaValidation:
    """Test file operations schema validation."""

    def test_read_csv_valid_input(self):
        """Test valid CSV read input."""
        valid_input = {
            "file_path": "/path/to/data.csv",
            "header": True,
            "separator": ",",
            "skip_rows": 0,
        }
        schema = read_csv._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_filter_data_valid_input(self):
        """Test valid data filtering input."""
        valid_input = {
            "data": {"age": [25, 30, 35, 40], "income": [50000, 60000, 70000, 80000]},
            "conditions": [
                {"variable": "age", "operator": ">", "value": 30},
                {"variable": "income", "operator": "<=", "value": 75000},
            ],
            "logic": "AND",
        }
        schema = filter_data._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_data_info_valid_input(self):
        """Test valid data info input."""
        valid_input = {
            "data": {
                "col1": [1, 2, 3],
                "col2": ["a", "b", "c"],
            }
        }
        schema = data_info._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_write_csv_valid_input(self):
        """Test valid CSV write input."""
        valid_input = {
            "data": {"col1": [1, 2, 3], "col2": [4, 5, 6]},
            "file_path": "/tmp/output.csv",
            "header": True,
        }
        schema = write_csv._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)


class TestEnhancedFileOps:
    """Test enhanced file operations (Excel, JSON)."""

    @pytest.mark.asyncio
    async def test_read_json_functionality(self):
        """Test reading JSON files."""
        context = await create_test_context()

        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"name": "test", "values": [1, 2, 3]}, f)
            temp_path = f.name

        try:
            # Test reading the JSON file
            result = await read_json(context, {"file_path": temp_path})
            # read_json returns the data directly, no success field
            assert "data" in result
            # Just verify structure due to R's jsonlite conversion
            assert "name" in result["data"]
            assert "values" in result["data"]
        finally:
            # Cleanup
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_write_json_functionality(self):
        """Test writing JSON files."""
        context = await create_test_context()

        # Create temporary file path
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            # Test writing JSON data
            test_data = {"test": "data", "numbers": [1, 2, 3]}
            result = await write_json(
                context,
                {"data": test_data, "file_path": temp_path}
            )

            # Verify write was successful
            assert result["success"] is True

            # Verify file contents
            with open(temp_path, "r") as f:
                written_data = json.load(f)
            # Note: R's jsonlite may format data differently
            # Just check that the key structure exists
            assert "test" in written_data
            assert "numbers" in written_data
        finally:
            # Cleanup
            os.unlink(temp_path)

    def test_read_excel_schema(self):
        """Test Excel reading schema validation."""
        valid_input = {
            "file_path": "/path/to/data.xlsx",
            "sheet": "Sheet1",
            "header": True,
        }
        schema = read_excel._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_write_excel_schema(self):
        """Test Excel writing schema validation."""
        valid_input = {
            "data": {"col1": [1, 2, 3], "col2": ["a", "b", "c"]},
            "file_path": "/path/to/output.xlsx",
            "sheet": "Results",
        }
        schema = write_excel._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])