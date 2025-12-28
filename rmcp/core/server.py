"""
MCP Server shell with lifecycle hooks.
This module provides the main server class that:
- Initializes the MCP app using official SDK
- Manages lifespan hooks (startup/shutdown)
- Composes transports at the edge
- Centralizes registry management
Following the principle: "A single shell centralizes initialization and teardown."
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from pathlib import Path
from typing import Any

try:
    from mcp.types import (  # type: ignore
        LATEST_PROTOCOL_VERSION,
        Implementation,
        InitializeResult,
        LoggingCapability,
        PromptsCapability,
        ResourcesCapability,
        ServerCapabilities,
        ToolsCapability,
    )

    _MCP_TYPES_AVAILABLE = True
    _PROTOCOL_VERSION = LATEST_PROTOCOL_VERSION
    # Use fallback log levels since LoggingLevel.__args__ may not be available
    _SUPPORTED_LOG_LEVELS = ["debug", "info", "warning", "error"]
except Exception:  # pragma: no cover - optional dependency
    _MCP_TYPES_AVAILABLE = False
    _PROTOCOL_VERSION = "2025-11-25"
    _SUPPORTED_LOG_LEVELS = [
        "debug",
        "info",
        "notice",
        "warning",
        "error",
        "critical",
        "alert",
        "emergency",
    ]
# Supported MCP protocol versions (latest first)
_SUPPORTED_PROTOCOL_VERSIONS = tuple(dict.fromkeys((_PROTOCOL_VERSION, "2025-06-18")))

# Import version from __init__ at runtime to avoid circular imports
from ..registries.prompts import PromptsRegistry
from ..registries.resources import ResourcesRegistry
from ..registries.tools import ToolsRegistry
from ..security.vfs import VFS
from ..transport.base import Transport
from .context import Context, LifespanState, RequestState

# Official MCP SDK imports (to be added when SDK is available)
# from mcp import Server, initialize_server
# from mcp.types import Request, Response, Notification
logger = logging.getLogger(__name__)
_transport_context: ContextVar[dict[str, Any] | None] = ContextVar(
    "rmcp_transport_context", default=None
)


class MCPServer:
    """
    Main MCP server shell that manages lifecycle and registries.
    This class serves as the central orchestrator for the RMCP MCP server, providing:
    - Lifespan management (startup/shutdown hooks)
    - Registry composition (tools/resources/prompts)
    - Security policy enforcement via VFS
    - Transport-agnostic request handling
    - Request tracking and cancellation support
    The server follows the Model Context Protocol (MCP) specification for
    communication with AI assistants like Claude Desktop.
    Example:
        >>> server = MCPServer(name="My Server", version="1.0.0")
        >>> server.configure(allowed_paths=["/data"], read_only=True)
        >>> # Register tools, prompts, resources...
        >>> await server.startup()
    """

    def __init__(
        self,
        name: str = "RMCP MCP Server",
        version: str | None = None,
        description: str = """RMCP provides 44 comprehensive statistical analysis tools through R:

**Regression & Econometrics (8 tools):**
- Linear/logistic regression with diagnostics and residual analysis
- Panel data regression (fixed/random effects) with robust standard errors
- Instrumental variables (2SLS) regression for causal inference
- Vector autoregression (VAR) models for multivariate time series
- Correlation analysis with significance testing and confidence intervals

**Time Series Analysis (6 tools):**
- ARIMA modeling with automatic order selection and forecasting
- Time series decomposition (trend, seasonal, remainder components)
- Stationarity testing (ADF, KPSS, Phillips-Perron tests)
- Lag/lead variable creation and differencing transformations

**Statistical Testing (5 tools):**
- T-tests (one-sample, two-sample, paired) with effect sizes
- ANOVA (one-way, two-way) with post-hoc comparisons
- Chi-square tests for independence and goodness-of-fit
- Normality tests (Shapiro-Wilk, Kolmogorov-Smirnov, Anderson-Darling)

**Data Analysis & Transformation (9 tools):**
- Comprehensive descriptive statistics with distribution analysis
- Outlier detection using multiple methods (IQR, Z-score, Mahalanobis)
- Data standardization (z-score, min-max, robust scaling)
- Winsorization for outlier treatment and data cleaning
- Professional frequency tables with percentages and cumulative statistics

**Machine Learning (4 tools):**
- K-means clustering with optimal cluster selection and visualization
- Decision trees for classification and regression with pruning
- Random forest models with variable importance and out-of-bag error

**Professional Visualizations (6 tools):**
- Scatter plots with trend lines, confidence bands, and grouping
- Time series plots for single/multiple variables with forecasting
- Histograms with density overlays and distribution fitting
- Correlation heatmaps with hierarchical clustering
- Box plots for distribution comparison and outlier identification
- Comprehensive residual diagnostic plots (4-panel analysis)

**File Operations (3 tools):**
- CSV/Excel/JSON import with automatic type detection
- Data filtering, export, and comprehensive dataset information
- Missing value analysis and data quality reporting

**Advanced Features:**
- Formula builder: Convert natural language to R statistical formulas
- Error recovery: Intelligent error diagnosis with suggested fixes
- Flexible R execution: Custom R code with 80+ whitelisted packages
- Example datasets: Built-in datasets for testing and learning

All tools provide professionally formatted output with markdown tables, statistical interpretations, and inline visualizations (base64 images). Results include both raw data and formatted summaries using broom/knitr for publication-ready output.""",
    ):
        """
        Initialize the MCP server instance.
        Args:
            name: Human-readable name for the server
            version: Semantic version string
            description: Brief description of server capabilities
        """
        # Get version dynamically to avoid circular imports
        if version is None:
            from .. import __version__

            version = __version__
        self.name = name
        self.version = version
        self.description = description
        # Lifespan state
        self.lifespan_state = LifespanState()
        # Transport + notification state
        self._transports: set[Transport] = set()
        self._pending_notifications: list[dict[str, Any]] = []
        self._resource_subscribers: set[Transport] = set()
        # Registries
        self.tools = ToolsRegistry(
            on_list_changed=self._make_list_changed_callback("tools")
        )
        self.resources = ResourcesRegistry(
            on_list_changed=self._make_list_changed_callback("resources")
        )
        self.prompts = PromptsRegistry(
            on_list_changed=self._make_list_changed_callback("prompts")
        )
        # Security
        self.vfs: VFS | None = None
        # Callbacks
        self._startup_callbacks: list[Callable[[], Awaitable[None]]] = []
        self._shutdown_callbacks: list[Callable[[], Awaitable[None]]] = []
        # Request tracking for cancellation
        self._active_requests: dict[str, RequestState] = {}
        # Register built-in static resources for quick discovery
        self._register_builtin_resources()

    def configure(
        self,
        allowed_paths: list[str] | None = None,
        cache_root: str | None = None,
        read_only: bool = True,
        **settings: Any,
    ) -> "MCPServer":
        """
        Configure server security and operational settings.

        Args:
            allowed_paths: List of filesystem paths the server can access.
                If None, defaults to current working directory.
            cache_root: Directory for caching intermediate results.
                Created if it doesn't exist.
            read_only: Whether filesystem access is read-only.
                Recommended for production deployments.
            **settings: Additional configuration options passed to lifespan state.

        Returns:
            Self for method chaining.

        Example:
            >>> server.configure(
            ...     allowed_paths=["/data", "/models"],
            ...     cache_root="/tmp/rmcp_cache",
            ...     read_only=True
            ... )
        """
        if allowed_paths:
            resolved_paths = []
            for raw_path in allowed_paths:
                path = Path(raw_path).expanduser()
                try:
                    resolved_paths.append(path.resolve())
                except OSError:
                    logger.warning(f"Unable to resolve allowed path: {raw_path}")
                    resolved_paths.append(path)
            self.lifespan_state.allowed_paths = resolved_paths
        elif not self.lifespan_state.allowed_paths:
            # Default to current working directory if nothing configured
            self.lifespan_state.allowed_paths = [Path.cwd()]
        if cache_root:
            cache_path = Path(cache_root)
            cache_path.mkdir(parents=True, exist_ok=True)
            self.lifespan_state.cache_root = cache_path
        self.lifespan_state.read_only = read_only
        self.lifespan_state.settings.update(settings)
        # Build resource mounts for allowed paths so clients can browse them
        self.lifespan_state.resource_mounts = self._build_resource_mounts(
            self.lifespan_state.allowed_paths
        )
        # Initialize VFS
        self.vfs = VFS(
            allowed_roots=self.lifespan_state.allowed_paths, read_only=read_only
        )
        # Wire VFS into lifespan state so tools can access it via context.lifespan.vfs
        self.lifespan_state.vfs = self.vfs
        return self

    def _build_resource_mounts(self, paths: list[Path]) -> dict[str, Path]:
        """Create deterministic mount names for each allowed path."""
        mounts: dict[str, Path] = {}
        for index, path in enumerate(paths, start=1):
            name = path.name or f"root-{index}"
            candidate = name
            suffix = 1
            while candidate in mounts:
                suffix += 1
                candidate = f"{name}-{suffix}"
            mounts[candidate] = path
        return mounts

    def on_startup(
        self, func: Callable[[], Awaitable[None]]
    ) -> Callable[[], Awaitable[None]]:
        """
        Register a callback to run during server startup.
        Args:
            func: Async function to call during startup. Should not take arguments.
        Returns:
            The same function (for use as decorator).
        Example:
            >>> @server.on_startup
            ... async def initialize_r_packages():
            ...     # Check R installation, load packages, etc.
            ...     pass
        """
        self._startup_callbacks.append(func)
        return func

    def on_shutdown(
        self, func: Callable[[], Awaitable[None]]
    ) -> Callable[[], Awaitable[None]]:
        """
        Register a callback to run during server shutdown.
        Args:
            func: Async function to call during shutdown. Should not take arguments.
        Returns:
            The same function (for use as decorator).
        Example:
            >>> @server.on_shutdown
            ... async def cleanup_temp_files():
            ...     # Clean up R temporary files, connections, etc.
            ...     pass
        """
        self._shutdown_callbacks.append(func)
        return func

    async def startup(self) -> None:
        """
        Start the server and run all startup callbacks.
        This method should be called once before handling any requests.
        It executes all registered startup callbacks in registration order.
        Raises:
            Exception: If any startup callback fails, the exception propagates.
        """
        import platform
        import sys

        # Emit prominent version and system information
        logger.info("=" * 60)
        logger.info(f"🚀 {self.name} v{self.version}")
        logger.info("=" * 60)
        logger.info(
            f"Python {sys.version.split()[0]} on {platform.system()} {platform.release()}"
        )

        # Log configuration summary
        if self.lifespan_state.allowed_paths:
            paths_str = ", ".join(str(p) for p in self.lifespan_state.allowed_paths[:3])
            if len(self.lifespan_state.allowed_paths) > 3:
                paths_str += f" (and {len(self.lifespan_state.allowed_paths) - 3} more)"
            logger.info(f"Allowed paths: {paths_str}")

        logger.info(
            f"Access mode: {'read-only' if self.lifespan_state.read_only else 'read-write'}"
        )

        if self.lifespan_state.cache_root:
            logger.info(f"Cache root: {self.lifespan_state.cache_root}")

        # Execute startup callbacks
        logger.info("Executing startup callbacks...")
        for callback in self._startup_callbacks:
            await callback()

        # Log registry summary
        tools_count = len(getattr(self.tools, "_tools", {}))
        resources_count = len(getattr(self.resources, "_static_resources", {})) + len(
            getattr(self.resources, "_templates", {})
        )
        prompts_count = len(getattr(self.prompts, "_prompts", {}))

        logger.info(
            f"Registered: {tools_count} tools, {resources_count} resources, {prompts_count} prompts"
        )
        logger.info("✅ Server startup complete - ready to handle requests")
        logger.info("=" * 60)

    async def shutdown(self) -> None:
        """
        Shutdown the server gracefully.
        This method:
        1. Cancels all active requests
        2. Runs all shutdown callbacks (continuing on errors)
        3. Logs completion
        Shutdown callbacks are called in registration order and errors
        are logged but don't prevent other callbacks from running.
        """
        logger.info("Shutting down server")
        # Cancel active requests
        for request in self._active_requests.values():
            request.cancel()
        # Run shutdown callbacks
        for callback in self._shutdown_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error(f"Error in shutdown callback: {e}")
        logger.info("Server shutdown complete")

    def create_context(
        self,
        request_id: str,
        method: str,
        progress_token: str | None = None,
        tool_invocation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Context:
        """
        Create execution context for a request.
        Args:
            request_id: Unique identifier for the request
            method: MCP method being called (e.g., "tools/call")
            progress_token: Optional token for progress reporting
        Returns:
            Context object with progress/logging callbacks configured
        """
        transport_info = _transport_context.get()
        transport: Transport | None = None
        if transport_info and isinstance(transport_info, dict):
            transport = transport_info.get("transport")
        progress_sender = None
        log_sender = None
        if transport:
            progress_sender = getattr(transport, "send_progress_notification", None)
            log_sender = getattr(transport, "send_log_notification", None)

        async def progress_callback(message: str, current: int, total: int) -> None:
            if not progress_token:
                return
            if progress_sender:
                try:
                    await progress_sender(progress_token, current, total, message)
                    return
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning(
                        "Failed to send progress notification for %s: %s",
                        request_id,
                        exc,
                    )
            logger.info("Progress %s: %s (%s/%s)", request_id, message, current, total)

        async def log_callback(level: str, message: str, data: dict[str, Any]) -> None:
            payload = {"requestId": request_id, **data}
            if tool_invocation_id:
                payload.setdefault("toolInvocationId", tool_invocation_id)
            log_level = getattr(logging, level.upper(), logging.INFO)
            if log_sender:
                try:
                    await log_sender(level, message, payload)
                    return
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning(
                        "Failed to send log notification for %s: %s",
                        request_id,
                        exc,
                    )
            # Use proper logging methods with formatted messages to avoid parameter conflicts
            log_message = f"{request_id}: {message}"
            if payload:
                log_message += f" {payload}"
            if log_level >= logging.ERROR:
                logger.error(log_message)
            elif log_level >= logging.WARNING:
                logger.warning(log_message)
            else:
                logger.info(log_message)

        context = Context.create(
            request_id=request_id,
            method=method,
            lifespan_state=self.lifespan_state,
            progress_token=progress_token,
            tool_invocation_id=tool_invocation_id,
            metadata=metadata,
            progress_callback=progress_callback,
            log_callback=log_callback,
        )
        # Add server reference for resource access to large data store
        context._server = self
        # Track request for cancellation
        self._active_requests[request_id] = context.request
        return context

    def finish_request(self, request_id: str) -> None:
        """
        Clean up request tracking after completion.
        Args:
            request_id: The request ID to remove from active tracking
        """
        self._active_requests.pop(request_id, None)

    async def cancel_request(self, request_id: str) -> None:
        """
        Cancel an active request by ID.
        Args:
            request_id: The request ID to cancel
        Note:
            If the request is not found, this method does nothing.
            Cancellation is cooperative - the request handler must
            check for cancellation periodically.
        """
        if request_id in self._active_requests:
            self._active_requests[request_id].cancel()
            logger.info(f"Cancelled request {request_id}")

    async def _handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle MCP initialize request.
        Returns server capabilities and metadata according to MCP protocol.
        Args:
            params: Initialize parameters from client
        Returns:
            Initialize response with server capabilities
        """
        requested_version = params.get("protocolVersion")
        if requested_version and requested_version not in _SUPPORTED_PROTOCOL_VERSIONS:
            raise ValueError(
                "Unsupported protocol version requested: "
                f"{requested_version}. Supported versions: "
                f"{', '.join(_SUPPORTED_PROTOCOL_VERSIONS)}"
            )
        protocol_version = requested_version or _PROTOCOL_VERSION

        client_info = params.get("clientInfo", {})
        logger.info(
            f"Initializing MCP connection with client: "
            f"{client_info.get('name', 'unknown')}"
        )
        if _MCP_TYPES_AVAILABLE:
            # Build capabilities - completion capability is not available in current MCP version
            capabilities = ServerCapabilities(
                tools=ToolsCapability(listChanged=False),
                resources=ResourcesCapability(subscribe=True, listChanged=True),
                prompts=PromptsCapability(listChanged=False),
                logging=LoggingCapability(),
            )
            initialize_result = InitializeResult(
                protocolVersion=protocol_version,
                capabilities=capabilities,
                serverInfo=Implementation(name=self.name, version=self.version),
                instructions=self.description or None,
            )
            return initialize_result.model_dump(mode="json", exclude_none=True)
        # Fallback for when MCP types not available
        capabilities_dict = {
            "tools": {"listChanged": False},
            "resources": {"subscribe": True, "listChanged": True},
            "prompts": {"listChanged": False},
            "logging": {},
            "completion": {},
        }
        result = {
            "protocolVersion": protocol_version,
            "capabilities": capabilities_dict,
            "serverInfo": {"name": self.name, "version": self.version},
        }
        if self.description:
            result["instructions"] = self.description
        return result

    async def _handle_set_log_level(self, level: str) -> dict[str, Any]:
        """
        Handle logging/setLevel request.
        Args:
            level: Log level to set (debug, info, notice, warning, error, critical, alert, emergency)
        Returns:
            Empty result dict on success
        """
        # Validate log level
        if level not in _SUPPORTED_LOG_LEVELS:
            raise ValueError(
                f"Unsupported log level: {level}. "
                f"Supported levels: {_SUPPORTED_LOG_LEVELS}"
            )
        # Map MCP levels to Python logging levels
        level_mapping = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "notice": logging.INFO,  # Python doesn't have NOTICE
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
            "alert": logging.CRITICAL,  # Python doesn't have ALERT, use CRITICAL
            "emergency": logging.CRITICAL,  # Python doesn't have EMERGENCY, use CRITICAL
        }
        # Set log level for RMCP loggers
        python_level = level_mapping[level]
        logging.getLogger("rmcp").setLevel(python_level)
        # Store current level in server state
        self.lifespan_state.current_log_level = level
        logger.info(f"Log level set to: {level}")
        return {}

    async def _handle_resources_subscribe(self, context: Context) -> dict[str, Any]:
        """Subscribe the current transport to resource change notifications."""
        transport = self._current_transport()
        if not transport:
            raise ValueError("resources/subscribe requires an active transport")
        self._resource_subscribers.add(transport)
        await context.info(
            "Transport subscribed to resource updates",
            transport=getattr(transport, "name", "transport"),
        )
        return {"subscription": "resources"}

    async def _handle_resources_unsubscribe(self, context: Context) -> dict[str, Any]:
        """Unsubscribe the current transport from resource notifications."""
        transport = self._current_transport()
        if not transport:
            return {}
        self._resource_subscribers.discard(transport)
        await context.info(
            "Transport unsubscribed from resource updates",
            transport=getattr(transport, "name", "transport"),
        )
        return {}

    async def _handle_completion(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle completion/complete request for auto-completion suggestions.
        Provides intelligent auto-completion for:
        - Tool names
        - Tool parameter names
        - R formula syntax
        - Variable names from datasets
        - Analysis type options
        Args:
            params: Completion parameters including ref (completion target)
        Returns:
            Dict with completion suggestions
        """
        ref = params.get("ref", {})
        completion_type = ref.get("type")
        name = ref.get("name", "")
        # Use match/case for completion type routing (Python 3.10+)
        match completion_type:
            case "tools":
                # Complete tool names
                all_tools = await self.tools.list_tools(
                    self.create_context("completion", "completion/complete"), limit=None
                )
                tool_names = [tool["name"] for tool in all_tools.get("tools", [])]
                # Filter based on partial input
                if name:
                    matching_tools = [
                        tool for tool in tool_names if tool.startswith(name)
                    ]
                else:
                    matching_tools = tool_names
                completions = [
                    {
                        "type": "text",
                        "value": tool_name,
                        "label": tool_name,
                        "detail": "Statistical analysis tool",
                    }
                    for tool_name in matching_tools[:10]  # Limit to 10 suggestions
                ]
            case "tool_parameters":
                # Complete parameter names for specific tools
                tool_name = ref.get("toolName")
                if tool_name and tool_name in self.tools._tools:
                    tool_def = self.tools._tools[tool_name]
                    schema = tool_def.input_schema
                    properties = schema.get("properties", {})
                    if name:
                        matching_params = [
                            p for p in properties.keys() if p.startswith(name)
                        ]
                    else:
                        matching_params = list(properties.keys())
                    completions = [
                        {
                            "type": "parameter",
                            "value": param,
                            "label": param,
                            "detail": properties[param].get("description", "Parameter"),
                        }
                        for param in matching_params[:10]
                    ]
                else:
                    completions = []
            case "formula":
                # Complete R formula syntax
                formula_suggestions = [
                    {
                        "type": "formula",
                        "value": "y ~ x",
                        "label": "y ~ x",
                        "detail": "Simple regression formula",
                    },
                    {
                        "type": "formula",
                        "value": "y ~ x1 + x2",
                        "label": "y ~ x1 + x2",
                        "detail": "Multiple regression formula",
                    },
                    {
                        "type": "formula",
                        "value": "y ~ x1 * x2",
                        "label": "y ~ x1 * x2",
                        "detail": "Interaction formula",
                    },
                    {
                        "type": "formula",
                        "value": "y ~ .",
                        "label": "y ~ .",
                        "detail": "Use all variables",
                    },
                    {
                        "type": "formula",
                        "value": "y ~ x + I(x^2)",
                        "label": "y ~ x + I(x^2)",
                        "detail": "Polynomial formula",
                    },
                ]
                if name:
                    # Filter based on partial input
                    completions = [s for s in formula_suggestions if name in s["value"]]
                else:
                    completions = formula_suggestions
            case "analysis_type":
                # Complete analysis type options
                analysis_types = [
                    {"value": "regression", "detail": "Linear and logistic regression"},
                    {"value": "correlation", "detail": "Correlation analysis"},
                    {"value": "timeseries", "detail": "Time series modeling"},
                    {
                        "value": "classification",
                        "detail": "Classification and clustering",
                    },
                    {"value": "anova", "detail": "Analysis of variance"},
                    {"value": "econometrics", "detail": "Panel data and IV regression"},
                    {"value": "general", "detail": "General statistical analysis"},
                ]
                if name:
                    matching_types = [
                        t for t in analysis_types if t["value"].startswith(name)
                    ]
                else:
                    matching_types = analysis_types
                completions = [
                    {
                        "type": "option",
                        "value": at["value"],
                        "label": at["value"],
                        "detail": at["detail"],
                    }
                    for at in matching_types
                ]
            case "dataset":
                # Complete example dataset names
                datasets = [
                    {
                        "value": "sales",
                        "detail": "Sales and marketing data with seasonal patterns",
                    },
                    {
                        "value": "economics",
                        "detail": "Economic indicators for regression analysis",
                    },
                    {
                        "value": "customers",
                        "detail": "Customer data for churn prediction",
                    },
                    {
                        "value": "timeseries",
                        "detail": "Time series data with trend and seasonality",
                    },
                    {"value": "survey", "detail": "Survey data with Likert scales"},
                ]
                if name:
                    matching_datasets = [
                        d for d in datasets if d["value"].startswith(name)
                    ]
                else:
                    matching_datasets = datasets
                completions = [
                    {
                        "type": "dataset",
                        "value": d["value"],
                        "label": d["value"],
                        "detail": d["detail"],
                    }
                    for d in matching_datasets
                ]
            case _:
                # Default: provide general RMCP help
                completions = [
                    {
                        "type": "help",
                        "value": "load_example",
                        "label": "load_example",
                        "detail": "Load example datasets for analysis",
                    },
                    {
                        "type": "help",
                        "value": "data_info",
                        "label": "data_info",
                        "detail": "Get information about your dataset",
                    },
                    {
                        "type": "help",
                        "value": "validate_data",
                        "label": "validate_data",
                        "detail": "Validate data quality before analysis",
                    },
                    {
                        "type": "help",
                        "value": "build_formula",
                        "label": "build_formula",
                        "detail": "Convert natural language to R formulas",
                    },
                ]
        return {
            "completion": {
                "values": completions,
                "total": len(completions),
                "hasMore": False,
            }
        }

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """
        Handle incoming MCP request and route to appropriate handler.
        This is the main entry point for all MCP requests. It:
        1. Extracts method, ID, and parameters from the request
        2. Routes to appropriate registry (tools, resources, prompts)
        3. Returns properly formatted JSON-RPC response
        4. Handles errors with appropriate error codes
        Args:
            request: JSON-RPC request dict with method, id, and params
        Returns:
            JSON-RPC response dict or None for notifications
        Supported methods:
            - initialize: Initialize MCP connection and return capabilities
            - tools/list: List available tools
            - tools/call: Execute a tool with parameters
            - resources/list: List available resources
            - resources/read: Read a resource by URI
            - prompts/list: List available prompts
            - prompts/get: Get a prompt with arguments
            - completion/complete: Provide auto-completion suggestions
            - logging/setLevel: Set the server logging level
        """
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})
        if not isinstance(params, dict):
            params = {}

        # Handle notifications (no response expected)
        if request_id is None:
            if method is None:
                # For notifications, we can't return an error, so just log and return
                logger.error("Invalid JSON-RPC notification: missing method")
                return None
            await self._handle_notification(method, params)
            return None

        try:
            # Validate method for requests (can return error response)
            if method is None:
                raise ValueError("Invalid JSON-RPC request: missing method")
            progress_token = params.get("progressToken")
            tool_invocation_id = params.get("toolInvocationId")
            metadata = {}
            if tool_invocation_id:
                metadata["toolInvocationId"] = tool_invocation_id
            context = self.create_context(
                request_id,
                method,
                progress_token=progress_token,
                tool_invocation_id=tool_invocation_id,
                metadata=metadata,
            )
            # Route to appropriate handler using match/case (Python 3.10+)
            match method:
                case "initialize":
                    result = await self._handle_initialize(params)
                case "tools/list":
                    result = await self.tools.list_tools(
                        context,
                        cursor=params.get("cursor"),
                        limit=params.get("limit"),
                    )
                case "tools/call":
                    tool_name = params.get("name")
                    if not isinstance(tool_name, str):
                        raise ValueError("tools/call requires 'name' parameter")
                    arguments = params.get("arguments", {})
                    result = await self.tools.call_tool(context, tool_name, arguments)
                case "resources/list":
                    result = await self.resources.list_resources(
                        context,
                        cursor=params.get("cursor"),
                        limit=params.get("limit"),
                    )
                case "resources/read":
                    uri = params.get("uri")
                    if not isinstance(uri, str):
                        raise ValueError("resources/read requires 'uri' parameter")
                    result = await self.resources.read_resource(context, uri)
                case "resources/subscribe":
                    result = await self._handle_resources_subscribe(context)
                case "resources/unsubscribe":
                    result = await self._handle_resources_unsubscribe(context)
                case "prompts/list":
                    result = await self.prompts.list_prompts(
                        context,
                        cursor=params.get("cursor"),
                        limit=params.get("limit"),
                    )
                case "prompts/get":
                    name = params.get("name")
                    if not isinstance(name, str):
                        raise ValueError("prompts/get requires 'name' parameter")
                    arguments = params.get("arguments", {})
                    result = await self.prompts.get_prompt(context, name, arguments)
                case "logging/setLevel":
                    level = params.get("level")
                    if not isinstance(level, str):
                        raise ValueError("logging/setLevel requires 'level' parameter")
                    result = await self._handle_set_log_level(level)
                case "completion/complete":
                    result = await self._handle_completion(params)
                case _:
                    raise ValueError(f"Unknown method: {method}")
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as e:
            logger.error(f"Error handling request {request_id}: {e}")

            # Map specific errors to appropriate JSON-RPC error codes
            error_message = str(e)
            if "missing method" in error_message.lower():
                error_code = -32600  # Invalid Request
            elif "unknown method" in error_message.lower():
                error_code = -32601  # Method not found
            elif (
                "requires" in error_message.lower()
                and "parameter" in error_message.lower()
            ):
                error_code = -32602  # Invalid params
            else:
                error_code = -32603  # Internal error

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": error_code, "message": error_message},
            }
        finally:
            if request_id:
                self.finish_request(request_id)

    def create_message_handler(
        self, transport: Transport
    ) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]:
        """Bind a transport to the server handler so context can emit feedback."""

        async def handler(message: dict[str, Any]) -> dict[str, Any] | None:
            self._transports.add(transport)
            token = _transport_context.set({"transport": transport})
            try:
                await self._flush_pending_notifications()
                return await self.handle_request(message)
            finally:
                _transport_context.reset(token)

        return handler

    def _make_list_changed_callback(
        self, kind: str
    ) -> Callable[[list[str] | None], None]:
        """Create a callback that enqueues list changed notifications."""

        def callback(item_ids: list[str] | None = None) -> None:
            self._queue_list_changed_notification(kind, item_ids)

        return callback

    def _queue_list_changed_notification(
        self, kind: str, item_ids: list[str] | None = None
    ) -> None:
        """Queue a list_changed notification for connected clients."""
        params: dict[str, Any] = {"kind": kind}
        if item_ids:
            params["itemIds"] = item_ids
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/list_changed",
            "params": params,
        }
        self._queue_notification(notification)

    def _queue_notification(self, notification: dict[str, Any]) -> None:
        """Queue notification for broadcast when transports are available."""
        if not self._transports:
            self._pending_notifications.append(notification)
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._pending_notifications.append(notification)
            return
        loop.create_task(self._broadcast_notification(notification))

    async def _broadcast_notification(self, notification: dict[str, Any]) -> None:
        """Broadcast a notification to all registered transports."""
        transports = list(self._transports)
        kind = notification.get("params", {}).get("kind")
        if kind == "resources":
            if self._resource_subscribers:
                transports = [
                    transport
                    for transport in transports
                    if transport in self._resource_subscribers
                ]
            else:
                return
        for transport in transports:
            try:
                await transport.send_message(dict(notification))
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "Failed to send notification via %s: %s",
                    getattr(transport, "name", "transport"),
                    exc,
                )

    async def _flush_pending_notifications(self) -> None:
        """Send any notifications queued before transports were ready."""
        if not self._pending_notifications or not self._transports:
            return
        pending = self._pending_notifications[:]
        self._pending_notifications.clear()
        for notification in pending:
            await self._broadcast_notification(notification)

    def _register_builtin_resources(self) -> None:
        """Expose project documentation as static resources."""
        project_root = Path(__file__).resolve().parents[2]
        readme_path = project_root / "README.md"
        if readme_path.exists():
            self.resources.register_static_resource(
                uri="rmcp://docs/readme",
                name="RMCP README",
                description="Project overview and setup guidance",
                mime_type="text/markdown",
                content_loader=lambda path=readme_path: path.read_text(
                    encoding="utf-8"
                ),
            )
        examples_dir = project_root / "examples"
        if examples_dir.exists():
            for example_path in examples_dir.glob("*.md"):
                uri = f"rmcp://examples/{example_path.stem}"
                self.resources.register_static_resource(
                    uri=uri,
                    name=f"Example: {example_path.stem.replace('_', ' ').title()}",
                    description=f"Example workflow from {example_path.name}",
                    mime_type="text/markdown",
                    content_loader=(
                        lambda path=example_path: path.read_text(encoding="utf-8")
                    ),
                )
        # Discovery resources
        self.resources.register_static_resource(
            uri="rmcp://catalog",
            name="Tool Catalog",
            description="Index of tools with usage examples",
            mime_type="text/markdown",
        )
        self.resources.register_static_resource(
            uri="rmcp://env",
            name="Environment Report",
            description="R version, packages, and platform details",
            mime_type="application/json",
        )
        self.resources.register_resource_template(
            uri_template="rmcp://dataset/{name}",
            name="Example Dataset",
            description="Expose built-in sample datasets via rmcp://dataset/<name>",
        )

    def _current_transport(self) -> Transport | None:
        """Return the transport currently handling a request, if any."""
        info = _transport_context.get()
        if info and isinstance(info, dict):
            transport = info.get("transport")
            if isinstance(transport, Transport):
                return transport
        return None

    async def _handle_notification(self, method: str, params: dict[str, Any]) -> None:
        """
        Handle MCP notification messages (no response expected).
        Args:
            method: Notification method name
            params: Notification parameters
        Supported notifications:
            - notifications/cancelled: Request cancellation
            - notifications/initialized: Client initialization complete
        """
        logger.info(f"Received notification: {method}")
        match method:
            case "notifications/cancelled":
                # Handle cancellation notification
                request_id = params.get("requestId")
                if request_id:
                    await self.cancel_request(request_id)
            case "notifications/initialized":
                # MCP initialization complete
                logger.info("MCP client initialization complete")
            case _:
                logger.warning(f"Unknown notification method: {method}")


def create_server(
    name: str = "RMCP MCP Server",
    version: str | None = None,
    description: str = """RMCP provides 44 comprehensive statistical analysis tools through R:

**Regression & Econometrics (8 tools):**
- Linear/logistic regression with diagnostics and residual analysis
- Panel data regression (fixed/random effects) with robust standard errors
- Instrumental variables (2SLS) regression for causal inference
- Vector autoregression (VAR) models for multivariate time series
- Correlation analysis with significance testing and confidence intervals

**Time Series Analysis (6 tools):**
- ARIMA modeling with automatic order selection and forecasting
- Time series decomposition (trend, seasonal, remainder components)
- Stationarity testing (ADF, KPSS, Phillips-Perron tests)
- Lag/lead variable creation and differencing transformations

**Statistical Testing (5 tools):**
- T-tests (one-sample, two-sample, paired) with effect sizes
- ANOVA (one-way, two-way) with post-hoc comparisons
- Chi-square tests for independence and goodness-of-fit
- Normality tests (Shapiro-Wilk, Kolmogorov-Smirnov, Anderson-Darling)

**Data Analysis & Transformation (9 tools):**
- Comprehensive descriptive statistics with distribution analysis
- Outlier detection using multiple methods (IQR, Z-score, Mahalanobis)
- Data standardization (z-score, min-max, robust scaling)
- Winsorization for outlier treatment and data cleaning
- Professional frequency tables with percentages and cumulative statistics

**Machine Learning (4 tools):**
- K-means clustering with optimal cluster selection and visualization
- Decision trees for classification and regression with pruning
- Random forest models with variable importance and out-of-bag error

**Professional Visualizations (6 tools):**
- Scatter plots with trend lines, confidence bands, and grouping
- Time series plots for single/multiple variables with forecasting
- Histograms with density overlays and distribution fitting
- Correlation heatmaps with hierarchical clustering
- Box plots for distribution comparison and outlier identification
- Comprehensive residual diagnostic plots (4-panel analysis)

**File Operations (3 tools):**
- CSV/Excel/JSON import with automatic type detection
- Data filtering, export, and comprehensive dataset information
- Missing value analysis and data quality reporting

**Advanced Features:**
- Formula builder: Convert natural language to R statistical formulas
- Error recovery: Intelligent error diagnosis with suggested fixes
- Flexible R execution: Custom R code with 80+ whitelisted packages
- Example datasets: Built-in datasets for testing and learning

All tools provide professionally formatted output with markdown tables, statistical interpretations, and inline visualizations (base64 images). Results include both raw data and formatted summaries using broom/knitr for publication-ready output.""",
) -> MCPServer:
    """
    Factory function to create a new MCP server instance.
    Args:
        name: Human-readable server name
        version: Semantic version string
        description: Brief description of server capabilities
    Returns:
        Configured MCPServer instance ready for configuration and startup
    Example:
        >>> server = create_server(
        ...     name="My Analytics Server",
        ...     version="1.0.0",
        ...     description="Custom R analytics tools"
        ... )
        >>> server.configure(allowed_paths=["/data"])
    """
    return MCPServer(name=name, version=version, description=description)
