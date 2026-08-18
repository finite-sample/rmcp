#!/usr/bin/env python3
"""
Schema validation and functional tests for file operation tools.
Tests input schema validation and file operations without R execution where possible.
"""

import json
import os
import tempfile
from datetime import datetime
from shutil import which

import pytest
from jsonschema import validate

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for fileops tests"
)

from rmcp.core.context import Context, LifespanState
from rmcp.security.vfs import VFS
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
        """Test reading JSON files with actual R execution."""
        context = await create_test_context()

        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"name": "test", "values": [1, 2, 3]}, f)
            temp_path = f.name

        try:
            # Test reading the JSON file with actual R execution
            result = await read_json(context, {"file_path": temp_path})
            # Verify structure matches actual R output
            assert "data" in result
            assert "file_info" in result
            assert "summary" in result
            # R's jsonlite expands JSON objects to column-wise format
            assert "name" in result["data"]
            assert "values" in result["data"]
        finally:
            # Cleanup
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_staged_csv_read_preserves_source_metadata(self, tmp_path):
        source = tmp_path / "source.csv"
        source.write_text("x\n1\n", encoding="utf-8")
        source_mtime = 946_684_800
        os.utime(source, (source_mtime, source_mtime))
        context = Context.create(
            "test",
            "read_csv",
            LifespanState(vfs=VFS([tmp_path], read_only=True)),
        )

        result = await read_csv(context, {"file_path": str(source)})

        assert result["file_info"]["file_path"] == str(source)
        assert result["file_info"]["file_size_bytes"] == source.stat().st_size
        assert result["file_info"]["modified_date"] == datetime.fromtimestamp(
            source_mtime
        ).strftime("%Y-%m-%d %H:%M:%S")

    @pytest.mark.asyncio
    async def test_read_excel_through_extension_bearing_symlink(self, tmp_path):
        import openpyxl

        target = tmp_path / "workbook-data"
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.append(["x"])
        worksheet.append([1])
        workbook.save(target)
        alias = tmp_path / "data.xlsx"
        alias.symlink_to(target.name)
        context = Context.create(
            "test",
            "read_excel",
            LifespanState(vfs=VFS([tmp_path], read_only=True)),
        )

        result = await read_excel(context, {"file_path": str(alias)})

        assert result["data"]["x"] == [1]
        assert result["file_info"]["file_path"] == str(alias)

    @pytest.mark.asyncio
    async def test_write_json_functionality(self):
        """Test writing JSON files with actual R execution."""
        context = await create_test_context()

        # Create temporary file path
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            # Test writing JSON data with actual R execution
            test_data = {"test": "data", "numbers": [1, 2, 3]}
            result = await write_json(
                context, {"data": test_data, "file_path": temp_path}
            )

            # Verify write was successful
            assert result["success"] is True
            assert "file_path" in result
            assert "timestamp" in result
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
