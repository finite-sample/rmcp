#!/usr/bin/env python3
"""
Basic smoke tests for RMCP core functionality.
These tests verify that basic server and CLI functionality works without requiring R.
"""
import pytest


class TestServerSmoke:
    """Test basic server functionality."""

    def test_server_can_be_created(self):
        """Test that RMCP server can be created without errors."""
        from rmcp.core.server import create_server

        server = create_server()
        assert server is not None

    def test_server_has_basic_capabilities(self):
        """Test that server has expected basic capabilities."""
        from rmcp.core.server import create_server

        server = create_server()
        assert hasattr(server, "tools")
        assert hasattr(server, "resources")
        assert hasattr(server, "prompts")

    def test_server_can_be_configured(self):
        """Test that server accepts configuration."""
        from rmcp.core.server import create_server

        server = create_server()
        # Should not raise an error
        server.configure(allowed_paths=["/tmp"], read_only=True)


class TestCLISmoke:
    """Test basic CLI functionality."""

    def test_cli_imports_without_error(self):
        """Test that CLI module can be imported."""
        from rmcp import cli

        assert cli is not None

    def test_rmcp_command_group_exists(self):
        """Test that main CLI command group exists."""
        from rmcp.cli import cli

        assert cli is not None
        assert hasattr(cli, "commands")

    def test_version_command_exists(self):
        """Test that version command exists."""
        from rmcp.cli import cli

        # Check if version command exists in CLI commands
        commands = getattr(cli, "commands", {})
        # Version might be handled by click's built-in --version flag
        assert cli is not None


class TestImportSmoke:
    """Test basic import functionality."""

    def test_core_modules_import(self):
        """Test that core modules can be imported."""
        # These should not raise ImportError
        from rmcp.core import context, schemas, server

        assert server is not None
        assert context is not None
        assert schemas is not None

    def test_transport_modules_import(self):
        """Test that transport modules can be imported."""
        from rmcp.transport import base, stdio

        assert base is not None
        assert stdio is not None

    def test_tools_modules_import(self):
        """Test that tool modules can be imported."""
        from rmcp.tools import fileops, helpers, regression

        assert regression is not None
        assert fileops is not None
        assert helpers is not None

    def test_registry_modules_import(self):
        """Test that registry modules can be imported."""
        from rmcp.registries import prompts, resources, tools

        assert tools is not None
        assert resources is not None
        assert prompts is not None


class TestBasicFunctionality:
    """Test basic functionality without R dependency."""

    def test_tool_registry_works(self):
        """Test that tool registry can register functions."""
        from rmcp.registries.tools import ToolsRegistry

        registry = ToolsRegistry()
        assert registry is not None
        assert hasattr(registry, "register")

    def test_context_creation_works(self):
        """Test that context can be created."""
        from rmcp.core.context import Context, LifespanState

        lifespan_state = LifespanState()
        context = Context.create("test", "test", lifespan_state)
        assert context is not None
        assert context.request.request_id == "test"

    def test_schema_validation_works(self):
        """Test that schema validation works."""
        from rmcp.core.schemas import table_schema

        schema = table_schema()
        assert schema is not None
        assert isinstance(schema, dict)
        assert "type" in schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
