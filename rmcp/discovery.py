"""
Dynamic Tool Discovery for RMCP.

This module provides dynamic discovery and registration of R statistical analysis tools,
inspired by mcptools' flexible tool composition capabilities.

Key features:
- Automatic R script discovery and metadata extraction
- Dynamic tool registration at runtime
- Tool composition and dependency management
- Hot-reload capability for development
- Schema validation and compatibility checking

Design principles:
- Scripts can self-describe their MCP tool interface
- Backward compatibility with existing static tool registration
- Extensible architecture for plugin-style tool addition
- Graceful degradation when tools are unavailable
"""

import asyncio
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .core.context import Context
from .r_integration import execute_r_script_async
from .registries.tools import tool

logger = logging.getLogger(__name__)


class RToolMetadata:
    """Metadata for dynamically discovered R tools."""

    def __init__(
        self,
        script_path: Path,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        output_schema: dict[str, Any] | None = None,
        category: str | None = None,
        dependencies: list[str] | None = None,
        examples: list[dict[str, Any]] | None = None,
    ):
        self.script_path = script_path
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.category = category
        self.dependencies = dependencies or []
        self.examples = examples or []
        self.last_modified = script_path.stat().st_mtime if script_path.exists() else 0


class RToolDiscovery:
    """
    Discovers and manages R statistical analysis tools dynamically.

    This class scans directories for R scripts that follow the RMCP tool
    convention and can automatically register them as MCP tools.
    """

    def __init__(self, script_directories: list[Path] | None = None):
        """
        Initialize tool discovery.

        Args:
            script_directories: Directories to scan for R scripts
        """
        self.script_directories = script_directories or []
        self.discovered_tools: dict[str, RToolMetadata] = {}
        self.registered_tools: set[str] = set()
        self._file_mtimes: dict[Path, float] = {}

    def add_script_directory(self, directory: Path) -> None:
        """Add a directory to scan for R tools."""
        if directory.exists() and directory.is_dir():
            self.script_directories.append(directory)
            logger.info(f"Added R script directory: {directory}")
        else:
            logger.warning(f"Script directory does not exist: {directory}")

    async def discover_tools(
        self, force_refresh: bool = False
    ) -> dict[str, RToolMetadata]:
        """
        Discover R tools in configured directories.

        Args:
            force_refresh: Force rediscovery even if files haven't changed

        Returns:
            Dictionary of discovered tool metadata
        """
        discovered = {}

        for directory in self.script_directories:
            if not directory.exists():
                continue

            # Find all R scripts
            r_scripts = list(directory.rglob("*.R"))

            for script_path in r_scripts:
                try:
                    # Check if file has been modified
                    current_mtime = script_path.stat().st_mtime
                    if (
                        not force_refresh
                        and script_path in self._file_mtimes
                        and self._file_mtimes[script_path] == current_mtime
                    ):
                        # File hasn't changed, use cached metadata
                        tool_name = self._get_tool_name_from_path(script_path)
                        if tool_name in self.discovered_tools:
                            discovered[tool_name] = self.discovered_tools[tool_name]
                            continue

                    # Extract tool metadata from script
                    metadata = await self._extract_tool_metadata(script_path)
                    if metadata:
                        discovered[metadata.name] = metadata
                        self._file_mtimes[script_path] = current_mtime

                except Exception as e:
                    logger.warning(f"Failed to process R script {script_path}: {e}")

        self.discovered_tools.update(discovered)
        logger.info(f"Discovered {len(discovered)} R tools")
        return discovered

    async def _extract_tool_metadata(self, script_path: Path) -> RToolMetadata | None:
        """Extract MCP tool metadata from R script."""
        try:
            content = script_path.read_text(encoding="utf-8")

            # Look for RMCP tool metadata in comments
            metadata = self._parse_rmcp_metadata(content)
            if metadata:
                return RToolMetadata(
                    script_path=script_path,
                    name=metadata.get(
                        "name", self._get_tool_name_from_path(script_path)
                    ),
                    description=metadata.get(
                        "description", f"R tool from {script_path.name}"
                    ),
                    input_schema=metadata.get(
                        "input_schema", self._infer_input_schema(content)
                    ),
                    output_schema=metadata.get("output_schema"),
                    category=metadata.get(
                        "category", self._infer_category_from_path(script_path)
                    ),
                    dependencies=metadata.get("dependencies", []),
                    examples=metadata.get("examples", []),
                )

            # Fallback to convention-based discovery
            tool_name = self._get_tool_name_from_path(script_path)
            if self._is_valid_rmcp_tool(content):
                return RToolMetadata(
                    script_path=script_path,
                    name=tool_name,
                    description=f"Statistical analysis tool: {tool_name}",
                    input_schema=self._infer_input_schema(content),
                    category=self._infer_category_from_path(script_path),
                )

        except Exception as e:
            logger.warning(f"Error extracting metadata from {script_path}: {e}")

        return None

    def _parse_rmcp_metadata(self, content: str) -> dict[str, Any] | None:
        """Parse RMCP tool metadata from R script comments."""
        # Look for RMCP metadata block
        metadata_pattern = r"#\s*RMCP-TOOL-START\s*\n(.*?)\n#\s*RMCP-TOOL-END"
        match = re.search(metadata_pattern, content, re.DOTALL)

        if match:
            try:
                metadata_text = match.group(1)
                # Remove comment markers and parse as JSON
                cleaned_text = re.sub(r"^#\s*", "", metadata_text, flags=re.MULTILINE)
                return json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in RMCP metadata: {e}")

        return None

    def _infer_input_schema(self, content: str) -> dict[str, Any]:
        """Infer input schema from R script content."""
        # Basic schema inference based on common patterns
        schema: dict[str, Any] = {"type": "object", "properties": {}}

        # Look for common parameter patterns
        if "args$data" in content:
            schema["properties"]["data"] = {
                "type": "object",
                "description": "Input dataset",
            }

        if "args$formula" in content:
            schema["properties"]["formula"] = {
                "type": "string",
                "description": "Statistical formula",
            }

        if "args$method" in content:
            schema["properties"]["method"] = {
                "type": "string",
                "description": "Analysis method",
            }

        # Add basic data property if none found
        if not schema["properties"]:
            schema["properties"]["data"] = {
                "type": "object",
                "description": "Input data for analysis",
            }

        return schema

    def _infer_category_from_path(self, script_path: Path) -> str:
        """Infer tool category from script path."""
        path_parts = script_path.parts

        # Look for category in parent directory names
        categories = {
            "descriptive": "descriptive_statistics",
            "regression": "regression_analysis",
            "timeseries": "time_series",
            "machine_learning": "machine_learning",
            "statistical_tests": "statistical_tests",
            "fileops": "file_operations",
            "visualization": "data_visualization",
            "econometrics": "econometrics",
            "transforms": "data_transformation",
            "helpers": "helper_tools",
        }

        for part in path_parts:
            if part in categories:
                return categories[part]

        return "statistical_analysis"

    def _get_tool_name_from_path(self, script_path: Path) -> str:
        """Generate tool name from script path."""
        # Remove .R extension and convert to snake_case
        name = script_path.stem
        return re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()

    def _is_valid_rmcp_tool(self, content: str) -> bool:
        """Check if R script follows RMCP tool conventions."""
        # Check for required patterns
        required_patterns = [
            r"args\s*<-\s*fromJSON",  # JSON argument parsing
            r"library\(jsonlite\)",  # jsonlite usage
            r"result\s*<-",  # Result assignment
        ]

        return all(re.search(pattern, content) for pattern in required_patterns)

    async def create_dynamic_tool(self, metadata: RToolMetadata) -> Callable:
        """Create a dynamic MCP tool from R script metadata."""

        @tool(
            name=metadata.name,
            description=metadata.description,
            input_schema=metadata.input_schema,
        )
        async def dynamic_r_tool(
            context: Context, params: dict[str, Any]
        ) -> dict[str, Any]:
            """Dynamically generated R tool."""
            try:
                # Check dependencies
                if metadata.dependencies:
                    await self._check_dependencies(metadata.dependencies, context)

                # Execute R script with parameters
                script_content = metadata.script_path.read_text(encoding="utf-8")
                result = await context.execute_r_with_session(script_content, params)

                # Add metadata to result
                result.update(
                    {
                        "_tool_metadata": {
                            "name": metadata.name,
                            "category": metadata.category,
                            "script_path": str(metadata.script_path),
                            "dynamically_loaded": True,
                        }
                    }
                )

                return result

            except Exception as e:
                await context.error(f"Dynamic tool {metadata.name} failed: {e}")
                return {"error": str(e), "tool_name": metadata.name, "success": False}

        # Attach metadata to function
        dynamic_r_tool._rmcp_metadata = metadata  # type: ignore[attr-defined]
        return dynamic_r_tool

    async def _check_dependencies(
        self, dependencies: list[str], context: Context
    ) -> None:
        """Check if R package dependencies are available."""
        for package in dependencies:
            check_script = f"""
            if (!requireNamespace("{package}", quietly = TRUE)) {{
                stop("Required package '{package}' is not available")
            }}
            result <- list(package = "{package}", available = TRUE)
            """

            try:
                await execute_r_script_async(check_script, {}, context)
            except Exception:
                raise Exception(f"Missing R package dependency: {package}")

    async def register_discovered_tools(self, tools_registry) -> int:
        """Register discovered tools with the MCP tools registry."""
        registered_count = 0

        for tool_name, metadata in self.discovered_tools.items():
            if tool_name not in self.registered_tools:
                try:
                    # Create dynamic tool function
                    tool_func = await self.create_dynamic_tool(metadata)

                    # Register with tools registry
                    tools_registry.register_function(tool_func)

                    self.registered_tools.add(tool_name)
                    registered_count += 1

                    logger.info(f"Registered dynamic R tool: {tool_name}")

                except Exception as e:
                    logger.error(f"Failed to register dynamic tool {tool_name}: {e}")

        return registered_count


class RToolComposer:
    """
    Composes and manages R tool workflows.

    This class provides capabilities for combining multiple R tools
    into complex analytical workflows, similar to mcptools' composition features.
    """

    def __init__(self, discovery: RToolDiscovery):
        self.discovery = discovery
        self.workflows: dict[str, dict[str, Any]] = {}

    async def create_workflow(
        self, name: str, steps: list[dict[str, Any]], description: str | None = None
    ) -> None:
        """Create a multi-step analytical workflow."""
        workflow = {
            "name": name,
            "description": description or f"Analytical workflow: {name}",
            "steps": steps,
            "created_at": asyncio.get_event_loop().time(),
        }

        # Validate workflow steps
        for i, step in enumerate(steps):
            if "tool" not in step:
                raise ValueError(f"Step {i} missing 'tool' specification")

            tool_name = step["tool"]
            if tool_name not in self.discovery.discovered_tools:
                raise ValueError(f"Tool '{tool_name}' not found in discovered tools")

        self.workflows[name] = workflow
        logger.info(f"Created workflow: {name} with {len(steps)} steps")

    async def execute_workflow(
        self, workflow_name: str, initial_data: dict[str, Any], context: Context
    ) -> dict[str, Any]:
        """Execute a multi-step workflow."""
        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")

        workflow = self.workflows[workflow_name]
        steps = workflow["steps"]

        # Track data flow between steps
        workflow_data = initial_data.copy()
        step_results = []

        await context.info(f"Starting workflow: {workflow_name}")

        for i, step in enumerate(steps):
            tool_name = step["tool"]
            step_params = step.get("parameters", {})

            # Merge workflow data with step parameters
            execution_params = {**workflow_data, **step_params}

            await context.progress(
                f"Executing step {i + 1}: {tool_name}", i + 1, len(steps)
            )

            try:
                # Execute tool step
                metadata = self.discovery.discovered_tools[tool_name]
                tool_func = await self.discovery.create_dynamic_tool(metadata)

                step_result = await tool_func(context, execution_params)
                step_results.append(
                    {"step": i + 1, "tool": tool_name, "result": step_result}
                )

                # Update workflow data with step results
                if isinstance(step_result, dict):
                    workflow_data.update(step_result)

            except Exception as e:
                await context.error(f"Workflow step {i + 1} failed: {e}")
                return {
                    "workflow": workflow_name,
                    "failed_at_step": i + 1,
                    "error": str(e),
                    "completed_steps": step_results,
                    "success": False,
                }

        await context.info(f"Workflow {workflow_name} completed successfully")

        return {
            "workflow": workflow_name,
            "steps_completed": len(steps),
            "results": step_results,
            "final_data": workflow_data,
            "success": True,
        }


# Global discovery instance
_tool_discovery: RToolDiscovery | None = None


def get_tool_discovery() -> RToolDiscovery:
    """Get the global R tool discovery instance."""
    global _tool_discovery
    if _tool_discovery is None:
        _tool_discovery = RToolDiscovery()
    return _tool_discovery


async def initialize_tool_discovery(
    script_directories: list[Path] | None = None,
) -> None:
    """Initialize tool discovery with script directories."""
    discovery = get_tool_discovery()

    if script_directories:
        for directory in script_directories:
            discovery.add_script_directory(directory)

    # Discover tools
    await discovery.discover_tools()
    logger.info("R tool discovery initialized")


async def register_dynamic_tools(tools_registry) -> int:
    """Register all discovered tools with the MCP registry."""
    discovery = get_tool_discovery()
    return await discovery.register_discovered_tools(tools_registry)
