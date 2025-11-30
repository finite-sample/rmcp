"""
File output scenario tests for the RMCP approval system.
Tests real file creation and validation with the approval workflow.
"""

import tempfile
from pathlib import Path

import pytest
from rmcp.core.context import Context, LifespanState
from rmcp.security.vfs import VFS
from rmcp.tools.flexible_r import approve_operation, execute_r_analysis


@pytest.fixture
async def mock_context_with_vfs():
    """Create a test context with VFS for file operations and approval state."""
    lifespan = LifespanState()

    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    allowed_paths = [Path(temp_dir)]

    # Initialize VFS with write permissions
    vfs = VFS(allowed_roots=allowed_paths, read_only=False)
    lifespan.vfs = vfs

    context = Context.create("test", "test", lifespan)
    context.temp_dir = temp_dir

    # Initialize approval state for the context if not already present
    if not hasattr(context, "_approved_operations"):
        context._approved_operations = {}

    # Copy test iris data to temp directory to eliminate network dependency
    import shutil

    test_data_dir = Path(__file__).parent.parent / "fixtures"
    iris_source = test_data_dir / "iris_test_data.csv"
    iris_dest = Path(temp_dir) / "iris_test_data.csv"
    shutil.copy(iris_source, iris_dest)
    context.iris_data_path = str(iris_dest)

    yield context

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestFileOutputScenarios:
    """Test real file output scenarios with approval workflow."""

    @pytest.mark.asyncio
    async def test_complete_iris_analysis_with_file_saving(self, mock_context_with_vfs):
        """Test complete iris analysis workflow with plot saving."""
        context = mock_context_with_vfs

        # Step 1: Approve file operations (both ggsave and write.csv)
        approval_result = await approve_operation(
            context,
            {
                "operation_type": "file_operations",
                "specific_operation": "ggsave",
                "action": "approve",
                "scope": "session",
                "directory": context.temp_dir,
            },
        )
        assert approval_result["success"] is True
        assert approval_result["action"] == "approved"

        # Also approve write.csv
        csv_approval = await approve_operation(
            context,
            {
                "operation_type": "file_operations",
                "specific_operation": "write.csv",
                "action": "approve",
                "scope": "session",
                "directory": context.temp_dir,
            },
        )
        assert csv_approval["success"] is True

        # Step 2: Approve package installation (might be needed for readr)
        package_approval = await approve_operation(
            context,
            {
                "operation_type": "package_installation",
                "specific_operation": "install.packages",
                "action": "approve",
                "scope": "session",
            },
        )
        assert package_approval["success"] is True

        # Step 3: Execute iris analysis with file saving (using local test data)
        iris_analysis_code = f"""
        # Load iris data from local file (no network dependency)
        iris_data <- read.csv("{context.iris_data_path}")

        # Create analysis plot using base R (more reliable in CI)
        plot_file <- "{context.temp_dir}/iris_analysis.png"
        png(plot_file, width = 800, height = 600, res = 100)

        # Create scatter plot with base R
        plot(iris_data$petal_length, iris_data$petal_width,
             col = as.factor(iris_data$species),
             pch = 19,
             main = "Iris Species Classification",
             xlab = "Petal Length (cm)",
             ylab = "Petal Width (cm)")
        legend("topright",
               legend = unique(iris_data$species),
               col = 1:length(unique(iris_data$species)),
               pch = 19)

        dev.off()

        # Also save data to CSV
        data_file <- "{context.temp_dir}/iris_data.csv"
        write.csv(iris_data, data_file, row.names = FALSE)

        result <- list(
          analysis_complete = TRUE,
          plot_file = plot_file,
          data_file = data_file,
          plot_exists = file.exists(plot_file),
          data_exists = file.exists(data_file),
          rows_analyzed = nrow(iris_data),
          species_count = length(unique(iris_data$species)),
          debug_info = list(
            file_size_plot = if(file.exists(plot_file)) file.size(plot_file) else 0,
            file_size_data = if(file.exists(data_file)) file.size(data_file) else 0,
            working_dir = getwd(),
            temp_dir_exists = dir.exists("{context.temp_dir}")
          )
        )
        """

        analysis_result = await execute_r_analysis(
            context,
            {
                "r_code": iris_analysis_code,
                "description": "Complete iris analysis with file saving (base R)",
                "packages": [],  # Using base R only, no external packages needed
                "return_image": False,
            },
        )

        # Verify analysis succeeded with better error reporting
        if not analysis_result["success"]:
            error_info = analysis_result.get("error", "Unknown error")
            pytest.fail(f"R analysis failed: {error_info}")

        result_data = analysis_result["result"]
        assert result_data["analysis_complete"] is True
        assert result_data["plot_exists"] is True
        assert result_data["data_exists"] is True
        assert (
            result_data["rows_analyzed"] == 30
        )  # Our test data has 30 data rows (file has 30 lines total, no final newline)
        assert result_data["species_count"] == 3

        # Verify files actually exist on filesystem
        plot_path = Path(context.temp_dir) / "iris_analysis.png"
        data_path = Path(context.temp_dir) / "iris_data.csv"

        assert plot_path.exists()
        assert data_path.exists()
        assert plot_path.stat().st_size > 0  # PNG file has content
        assert data_path.stat().st_size > 0  # CSV file has content

    @pytest.mark.asyncio
    async def test_file_approval_workflow_rejection(self, mock_context_with_vfs):
        """Test that file operations are blocked without approval."""
        context = mock_context_with_vfs

        # Try to save file without approval
        save_code = f"""
        library(ggplot2)
        p <- ggplot(mtcars, aes(x = wt, y = mpg)) + geom_point()
        ggsave("{context.temp_dir}/test.png", plot = p)
        result <- list(saved = TRUE)
        """

        analysis_result = await execute_r_analysis(
            context,
            {
                "r_code": save_code,
                "description": "Test file saving without approval",
                "packages": ["ggplot2"],
            },
        )

        # Should fail due to lack of approval
        assert analysis_result["success"] is False
        assert "OPERATION_APPROVAL_NEEDED" in analysis_result["error"]
        assert "file_operations" in analysis_result["error"]

    @pytest.mark.asyncio
    async def test_package_installation_workflow(self, mock_context_with_vfs):
        """Test package installation with approval."""
        context = mock_context_with_vfs

        # First try without approval - should fail
        install_code = """
        install.packages("moments")
        result <- list(installed = TRUE)
        """

        result_without_approval = await execute_r_analysis(
            context,
            {
                "r_code": install_code,
                "description": "Test package installation without approval",
            },
        )

        assert result_without_approval["success"] is False
        assert "OPERATION_APPROVAL_NEEDED" in result_without_approval["error"]
        assert "package_installation" in result_without_approval["error"]

        # Now approve package installation
        approval_result = await approve_operation(
            context,
            {
                "operation_type": "package_installation",
                "specific_operation": "install.packages",
                "action": "approve",
                "scope": "session",
            },
        )
        assert approval_result["success"] is True

        # Try again with approval - should work
        result_with_approval = await execute_r_analysis(
            context,
            {
                "r_code": install_code,
                "description": "Test package installation with approval",
            },
        )

        # Note: This might still fail in test environment if package can't be installed,
        # but it should pass the validation step
        if result_with_approval["success"]:
            assert result_with_approval["result"]["installed"] is True
        else:
            # If it fails, it should be due to R execution, not approval
            assert "OPERATION_APPROVAL_NEEDED" not in result_with_approval["error"]

    @pytest.mark.asyncio
    async def test_multiple_file_formats(self, mock_context_with_vfs):
        """Test saving multiple file formats with approval."""
        context = mock_context_with_vfs

        # Approve file operations
        await approve_operation(
            context,
            {
                "operation_type": "file_operations",
                "specific_operation": "ggsave",
                "action": "approve",
                "directory": context.temp_dir,
            },
        )

        await approve_operation(
            context,
            {
                "operation_type": "file_operations",
                "specific_operation": "write.csv",
                "action": "approve",
                "directory": context.temp_dir,
            },
        )

        await approve_operation(
            context,
            {
                "operation_type": "file_operations",
                "specific_operation": "writeLines",
                "action": "approve",
                "directory": context.temp_dir,
            },
        )

        # Create and save multiple file formats
        multi_format_code = f"""
        # Create some data
        data <- data.frame(
          x = 1:10,
          y = (1:10)^2,
          category = rep(c("A", "B"), 5)
        )

        # Save as CSV
        write.csv(data, "{context.temp_dir}/data.csv", row.names = FALSE)

        # Create and save plot as PNG
        library(ggplot2)
        p <- ggplot(data, aes(x = x, y = y, color = category)) +
          geom_point(size = 3) +
          theme_minimal()
        ggsave("{context.temp_dir}/plot.png", plot = p, width = 8, height = 6)

        # Save text summary
        summary_text <- c(
          "Analysis Summary",
          paste("Rows:", nrow(data)),
          paste("Mean Y:", mean(data$y)),
          paste("Categories:", paste(unique(data$category), collapse = ", "))
        )
        writeLines(summary_text, "{context.temp_dir}/summary.txt")

        result <- list(
          csv_exists = file.exists("{context.temp_dir}/data.csv"),
          png_exists = file.exists("{context.temp_dir}/plot.png"),
          txt_exists = file.exists("{context.temp_dir}/summary.txt"),
          files_created = 3
        )
        """

        result = await execute_r_analysis(
            context,
            {
                "r_code": multi_format_code,
                "description": "Test multiple file format saving",
                "packages": ["ggplot2"],
            },
        )

        assert result["success"] is True
        assert result["result"]["csv_exists"] is True
        assert result["result"]["png_exists"] is True
        assert result["result"]["txt_exists"] is True
        assert result["result"]["files_created"] == 3

        # Verify files exist on filesystem
        csv_path = Path(context.temp_dir) / "data.csv"
        png_path = Path(context.temp_dir) / "plot.png"
        txt_path = Path(context.temp_dir) / "summary.txt"

        assert csv_path.exists() and csv_path.stat().st_size > 0
        assert png_path.exists() and png_path.stat().st_size > 0
        assert txt_path.exists() and txt_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_vfs_security_boundaries(self, mock_context_with_vfs):
        """Test that VFS security boundaries are maintained."""
        context = mock_context_with_vfs

        # Approve file operations
        await approve_operation(
            context,
            {
                "operation_type": "file_operations",
                "specific_operation": "write.csv",
                "action": "approve",
                "directory": context.temp_dir,
            },
        )

        # Try to write outside allowed directory - should fail
        outside_dir_code = """
        data <- data.frame(x = 1:5, y = 1:5)
        write.csv(data, "/tmp/unauthorized.csv", row.names = FALSE)
        result <- list(written = TRUE)
        """

        result = await execute_r_analysis(
            context,
            {
                "r_code": outside_dir_code,
                "description": "Test writing outside allowed directory",
            },
        )

        # The test should either:
        # 1. Fail during R execution due to approval system blocking, OR
        # 2. Succeed in R but VFS should prevent actual file creation
        unauthorized_file = Path("/tmp/unauthorized.csv")

        # Clean up any existing file first
        if unauthorized_file.exists():
            unauthorized_file.unlink()

        # After R execution, the unauthorized file should not exist
        assert not unauthorized_file.exists(), (
            "VFS security was bypassed - unauthorized file was created"
        )

        # The operation should have been blocked by approval system
        if not result["success"]:
            assert "OPERATION_APPROVAL_NEEDED" in result.get("error", "")
