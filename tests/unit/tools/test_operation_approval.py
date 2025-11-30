"""
Unit tests for the universal operation approval system.
Tests the approve_operation tool and validation logic.
"""

import pytest
from rmcp.core.context import Context, LifespanState
from rmcp.tools.flexible_r import (
    OPERATION_CATEGORIES,
    approve_operation,
    is_operation_approved,
    validate_r_code,
)


@pytest.fixture
async def mock_context():
    """Create a mock context for testing."""
    lifespan = LifespanState()
    context = Context.create("test", "test", lifespan)
    return context


class TestOperationApproval:
    """Test the approve_operation tool functionality."""

    @pytest.mark.asyncio
    async def test_approve_file_operation(self, mock_context):
        """Test approving file operations."""
        params = {
            "operation_type": "file_operations",
            "specific_operation": "ggsave",
            "action": "approve",
            "scope": "session",
            "directory": "./plots",
        }

        result = await approve_operation(mock_context, params)

        assert result["success"] is True
        assert result["action"] == "approved"
        assert result["operation_type"] == "file_operations"
        assert result["specific_operation"] == "ggsave"
        assert "approved_operations" in result
        assert "security_info" in result

    @pytest.mark.asyncio
    async def test_approve_package_installation(self, mock_context):
        """Test approving package installation."""
        params = {
            "operation_type": "package_installation",
            "specific_operation": "install.packages",
            "action": "approve",
            "scope": "session",
        }

        result = await approve_operation(mock_context, params)

        assert result["success"] is True
        assert result["action"] == "approved"
        assert result["operation_type"] == "package_installation"
        assert result["specific_operation"] == "install.packages"

    @pytest.mark.asyncio
    async def test_deny_operation(self, mock_context):
        """Test denying operations."""
        params = {
            "operation_type": "system_operations",
            "specific_operation": "system",
            "action": "deny",
        }

        result = await approve_operation(mock_context, params)

        assert result["success"] is True
        assert result["action"] == "denied"
        assert result["scope"] == "none"

    @pytest.mark.asyncio
    async def test_session_approval_tracking(self, mock_context):
        """Test that approvals are tracked in session context."""
        # Approve file operations
        await approve_operation(
            mock_context,
            {
                "operation_type": "file_operations",
                "specific_operation": "ggsave",
                "action": "approve",
            },
        )

        # Check that approval is tracked
        assert hasattr(mock_context, "_approved_operations")
        assert "file_operations" in mock_context._approved_operations
        assert "ggsave" in mock_context._approved_operations["file_operations"]

    def test_is_operation_approved_logic(self, mock_context):
        """Test the operation approval checking logic."""
        # Initially not approved
        assert not is_operation_approved(mock_context, "file_operations", "ggsave")

        # Add approval manually
        mock_context._approved_operations = {
            "file_operations": {"ggsave": {"approved_at": 123456}}
        }

        # Now should be approved
        assert is_operation_approved(mock_context, "file_operations", "ggsave")
        assert not is_operation_approved(mock_context, "file_operations", "write.csv")


class TestValidationWithApproval:
    """Test R code validation with the approval system."""

    def test_validation_requires_approval_for_ggsave(self):
        """Test that ggsave requires approval."""
        r_code = 'ggsave("plot.png", plot = p)'
        is_safe, error = validate_r_code(r_code)

        assert not is_safe
        assert "OPERATION_APPROVAL_NEEDED:file_operations:ggsave" in error

    def test_validation_requires_approval_for_install_packages(self):
        """Test that install.packages requires approval."""
        r_code = 'install.packages("moments")'
        is_safe, error = validate_r_code(r_code)

        assert not is_safe
        assert (
            "OPERATION_APPROVAL_NEEDED:package_installation:install.packages" in error
        )

    def test_validation_allows_approved_operations(self, mock_context):
        """Test that approved operations pass validation."""
        # Add approval
        mock_context._approved_operations = {
            "file_operations": {"ggsave": {"approved_at": 123456}}
        }

        r_code = 'ggsave("plot.png", plot = p)'
        is_safe, error = validate_r_code(r_code, context=mock_context)

        assert is_safe
        assert error is None

    def test_validation_still_blocks_dangerous_patterns(self, mock_context):
        """Test that truly dangerous patterns are still blocked."""
        r_code = 'system("rm -rf /")'
        is_safe, error = validate_r_code(r_code, context=mock_context)

        assert not is_safe
        assert "OPERATION_APPROVAL_NEEDED:system_operations:system" in error

    def test_validation_blocks_non_approvable_dangerous_patterns(self):
        """Test that some dangerous patterns cannot be approved."""
        r_code = 'setwd("/etc")'
        is_safe, error = validate_r_code(r_code)

        assert not is_safe
        assert "Dangerous pattern detected" in error


class TestOperationCategories:
    """Test the operation category configuration."""

    def test_operation_categories_structure(self):
        """Test that operation categories are properly structured."""
        assert "file_operations" in OPERATION_CATEGORIES
        assert "package_installation" in OPERATION_CATEGORIES
        assert "system_operations" in OPERATION_CATEGORIES

        for _category, config in OPERATION_CATEGORIES.items():
            assert "patterns" in config
            assert "description" in config
            assert "examples" in config
            assert "security_level" in config
            assert isinstance(config["patterns"], list)
            assert len(config["patterns"]) > 0

    def test_file_operations_patterns(self):
        """Test that file operation patterns are correct."""
        patterns = OPERATION_CATEGORIES["file_operations"]["patterns"]
        assert any("ggsave" in pattern for pattern in patterns)
        assert any("write\\.csv" in pattern for pattern in patterns)
        assert any("writeLines" in pattern for pattern in patterns)

    def test_package_installation_patterns(self):
        """Test that package installation patterns are correct."""
        patterns = OPERATION_CATEGORIES["package_installation"]["patterns"]
        assert any("install\\.packages" in pattern for pattern in patterns)

    def test_system_operations_patterns(self):
        """Test that system operation patterns are correct."""
        patterns = OPERATION_CATEGORIES["system_operations"]["patterns"]
        assert any("system" in pattern for pattern in patterns)
        assert any("shell" in pattern for pattern in patterns)
        assert any("Sys\\.setenv" in pattern for pattern in patterns)
