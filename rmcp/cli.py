"""
Command-line interface for RMCP MCP Server.
Provides entry points for running the server with different transports
and configurations, following the principle of "multiple deployment targets."
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import click

from . import __version__
from .config import get_config, load_config
from .core.server import create_server
from .logging_config import configure_structured_logging, get_logger
from .registries.prompts import (
    model_diagnostic_prompt,
    panel_regression_prompt,
    register_prompt_functions,
    regression_diagnostics_prompt,
    statistical_workflow_prompt,
    time_series_forecast_prompt,
)
from .registries.tools import register_tool_functions
from .transport.stdio import StdioTransport

# Modern Python 3.10+ syntax for type hints
# Structured logging will be configured in CLI commands based on config
logger = get_logger(__name__)


async def _run_server_with_transport(server, transport) -> None:
    """Run a transport while honoring server lifecycle hooks."""
    started = False
    try:
        await server.startup()
        started = True
        await transport.run()
    finally:
        if started:
            await server.shutdown()


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option(
    "--log-format",
    type=click.Choice(["structured", "pretty"]),
    default="structured",
    help="Log output format (structured=JSON, pretty=colored console)",
)
@click.pass_context
def cli(ctx, config: Path, debug: bool, log_format: str):
    """RMCP MCP Server - Comprehensive statistical analysis with 44 tools across 11 categories."""
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Load configuration with overrides
    overrides = {}
    if debug:
        overrides["debug"] = True
        overrides["logging"] = {"level": "DEBUG"}

    # Store config in context for subcommands
    ctx.obj["config"] = load_config(config_file=config, overrides=overrides)
    ctx.obj["log_format"] = log_format


@cli.command()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Logging level (overrides config)",
)
@click.pass_context
def start(ctx, log_level: str):
    """Start RMCP MCP server (default stdio transport)."""
    # Get configuration
    config = ctx.obj.get("config") or get_config()
    log_format = ctx.obj.get("log_format", "structured")

    # Configure structured logging
    effective_log_level = log_level or config.logging.level
    configure_structured_logging(
        level=effective_log_level,
        development_mode=(log_format == "pretty" or config.debug),
        enable_console=True,
    )

    logger.info(f"Starting RMCP MCP Server v{__version__}")
    if config.debug:
        logger.debug("Debug mode enabled")
        logger.debug(
            f"Configuration loaded from: {config.config_file or 'defaults/environment'}"
        )
    if sys.platform == "win32":
        logger.info(
            "Windows platform detected - using Windows-compatible stdio transport"
        )
    try:
        # Check R version compatibility (but don't fail if R check fails)
        from .r_integration import check_r_version

        try:
            is_compatible, version_string = check_r_version()
            logger.info(f"R version check: {version_string}")
            if not is_compatible:
                logger.warning(
                    "RMCP requires R 4.4.0 or higher for full compatibility. "
                    "Some features may not work correctly with older R versions. "
                    "Please upgrade R to 4.4.0+ for best experience."
                )
        except Exception as e:
            logger.warning(f"R version check failed: {e}")
            logger.warning(
                "R may not be properly installed. Server will start but R-dependent tools may fail. "
                "Please ensure R 4.4.0+ is installed and available in PATH."
            )

        # Create and configure server
        logger.info("Creating MCP server...")
        server = create_server()

        # Configure server with paths from config
        allowed_paths = [str(Path.cwd())] + config.security.vfs_allowed_paths
        server.configure(
            allowed_paths=allowed_paths, read_only=config.security.vfs_read_only
        )

        # Set up stdio transport BEFORE registering tools to avoid notification timing issues
        logger.info("Setting up stdio transport...")
        transport = StdioTransport(
            max_workers=config.performance.threadpool_max_workers
        )
        transport.set_message_handler(server.create_message_handler(transport))

        logger.info("Registering built-in tools...")
        # Register built-in statistical tools
        _register_builtin_tools(server)

        logger.info("Registering built-in prompts...")
        # Register built-in prompts
        register_prompt_functions(
            server.prompts,
            statistical_workflow_prompt,
            model_diagnostic_prompt,
            regression_diagnostics_prompt,
            time_series_forecast_prompt,
            panel_regression_prompt,
        )

        logger.info("Starting MCP server with stdio transport...")
        # Run the server with lifecycle management
        try:
            asyncio.run(_run_server_with_transport(server, transport))
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--allowed-paths",
    multiple=True,
    help="Allowed file system paths (can be specified multiple times)",
)
@click.option(
    "--cache-root", type=click.Path(), help="Root directory for content caching"
)
@click.option(
    "--read-only/--read-write",
    default=True,
    help="File system access mode (default: read-only)",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level",
)
@click.option(
    "--config-file", type=click.Path(exists=True), help="Configuration file path"
)
def serve(
    allowed_paths: list[str],
    cache_root: str | None,
    read_only: bool,
    log_level: str,
    config_file: str | None,
):
    """Run MCP server with advanced configuration options."""
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, log_level))
    logger.info(f"Starting RMCP MCP Server v{__version__}")
    try:
        # Check R version compatibility
        from .r_integration import check_r_version

        try:
            is_compatible, version_string = check_r_version()
            logger.info(f"R version check: {version_string}")
            if not is_compatible:
                logger.error(
                    "RMCP requires R 4.4.0 or higher for full compatibility. "
                    "Some features may not work correctly with older R versions. "
                    "Please upgrade R to 4.4.0+ for best experience."
                )
        except Exception as e:
            logger.error(f"R version check failed: {e}")
            logger.error(
                "R may not be properly installed. Please ensure R 4.4.0+ is installed and available in PATH."
            )

        # Load configuration
        config = _load_config(config_file) if config_file else {}
        # Override with CLI options
        if allowed_paths:
            config["allowed_paths"] = list(allowed_paths)
        if cache_root:
            config["cache_root"] = cache_root
        config["read_only"] = read_only
        # Set defaults if not specified
        if "allowed_paths" not in config:
            config["allowed_paths"] = [str(Path.cwd())]
        # Create and configure server
        server = create_server()
        server.configure(**config)
        # Register built-in statistical tools
        _register_builtin_tools(server)
        # Register built-in prompts
        register_prompt_functions(
            server.prompts,
            statistical_workflow_prompt,
            model_diagnostic_prompt,
            regression_diagnostics_prompt,
            time_series_forecast_prompt,
            panel_regression_prompt,
        )
        # Set up stdio transport
        transport = StdioTransport()
        transport.set_message_handler(server.create_message_handler(transport))
        # Run the server with lifecycle management
        asyncio.run(_run_server_with_transport(server, transport))
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


@cli.command()
@click.option("--host", help="Host to bind to (overrides config)")
@click.option("--port", type=int, help="Port to bind to (overrides config)")
@click.option("--ssl-keyfile", help="SSL private key file (enables HTTPS)")
@click.option("--ssl-certfile", help="SSL certificate file (enables HTTPS)")
@click.option("--ssl-keyfile-password", help="Password for encrypted SSL key")
@click.option(
    "--allowed-paths", multiple=True, help="Additional allowed file system paths"
)
@click.option("--cache-root", help="Cache root directory")
@click.pass_context
def serve_http(
    ctx,
    host: str,
    port: int,
    ssl_keyfile: str,
    ssl_certfile: str,
    ssl_keyfile_password: str,
    allowed_paths: tuple[str, ...],
    cache_root: str | None,
):
    """Run MCP server over HTTP transport (requires fastapi extras)."""
    try:
        from .transport.http import HTTPTransport
    except ImportError:
        click.echo(
            "HTTP transport requires 'fastapi' extras. "
            "Install with: pip install rmcp[http]"
        )
        sys.exit(1)

    # Get configuration
    config = ctx.obj.get("config") or get_config()
    log_format = ctx.obj.get("log_format", "structured")

    # Configure structured logging for HTTP transport
    configure_structured_logging(
        level=config.logging.level,
        development_mode=(log_format == "pretty" or config.debug),
        enable_console=True,
    )

    # Use CLI options or fall back to config
    effective_host = host or config.http.host
    effective_port = port or config.http.port
    effective_ssl_keyfile = ssl_keyfile or config.http.ssl_keyfile
    effective_ssl_certfile = ssl_certfile or config.http.ssl_certfile
    effective_ssl_keyfile_password = (
        ssl_keyfile_password or config.http.ssl_keyfile_password
    )

    # Determine if HTTPS is enabled
    is_https = bool(effective_ssl_keyfile and effective_ssl_certfile)
    protocol = "https" if is_https else "http"

    logger.info(
        f"Starting {protocol.upper()} transport on {effective_host}:{effective_port}"
    )

    # Create and configure server
    server = create_server()

    # Configure allowed paths (combine config and CLI options)
    all_allowed_paths = (
        [str(Path.cwd())] + config.security.vfs_allowed_paths + list(allowed_paths)
    )
    server.configure(
        allowed_paths=all_allowed_paths,
        read_only=config.security.vfs_read_only,
        cache_root=str(Path(cache_root)) if cache_root else None,
    )

    _register_builtin_tools(server)

    # Create HTTP transport with configuration
    transport = HTTPTransport(
        host=effective_host,
        port=effective_port,
        ssl_keyfile=effective_ssl_keyfile,
        ssl_certfile=effective_ssl_certfile,
        ssl_keyfile_password=effective_ssl_keyfile_password,
    )
    transport.set_message_handler(server.create_message_handler(transport))

    # Show appropriate protocol and security info
    if is_https:
        click.echo(
            f"🔒 RMCP HTTPS server starting on https://{effective_host}:{effective_port}"
        )
        click.echo("🛡️  SSL/TLS encryption enabled")
    else:
        click.echo(
            f"🚀 RMCP HTTP server starting on http://{effective_host}:{effective_port}"
        )

    click.echo(f"📊 Available tools: {len(server.tools._tools)}")
    click.echo("🔗 Endpoints:")
    click.echo(
        f"   • POST {protocol}://{effective_host}:{effective_port}/mcp (JSON-RPC requests)"
    )
    click.echo(
        f"   • GET  {protocol}://{effective_host}:{effective_port}/mcp/sse (Server-Sent Events)"
    )
    click.echo(
        f"   • GET  {protocol}://{effective_host}:{effective_port}/health (Health check)"
    )
    try:
        asyncio.run(_run_server_with_transport(server, transport))
    except KeyboardInterrupt:
        click.echo("\n👋 Shutting down HTTP server")
    except Exception as e:
        logger.error(f"HTTP server error: {e}")
        sys.exit(1)


@cli.command()
@click.option("--allowed-paths", multiple=True, help="Allowed file system paths")
@click.option("--output", type=click.Path(), help="Output file for capabilities")
def list_capabilities(allowed_paths: list[str], output: str | None):
    """List server capabilities (tools, resources, prompts)."""
    # Create server to inspect capabilities
    server = create_server()
    if allowed_paths:
        server.configure(allowed_paths=list(allowed_paths))
    _register_builtin_tools(server)
    register_prompt_functions(
        server.prompts,
        statistical_workflow_prompt,
        model_diagnostic_prompt,
        regression_diagnostics_prompt,
        time_series_forecast_prompt,
        panel_regression_prompt,
    )

    async def _list():
        from .core.context import Context

        context = Context.create("capabilities", "list", server.lifespan_state)
        tools = await server.tools.list_tools(context)
        resources = await server.resources.list_resources(context)
        prompts = await server.prompts.list_prompts(context)
        initialize = await server._handle_initialize(
            {"clientInfo": {"name": "rmcp-cli"}}
        )
        capabilities = {
            "server": {
                "name": server.name,
                "version": server.version,
                "description": server.description,
                "allowedPaths": [
                    str(path) for path in server.lifespan_state.allowed_paths
                ],
                "resourceMounts": {
                    name: str(path)
                    for name, path in server.lifespan_state.resource_mounts.items()
                },
            },
            "initialize": initialize,
            "tools": tools["tools"],
            "resources": resources["resources"],
            "prompts": prompts["prompts"],
        }
        json_output = json.dumps(capabilities, indent=2)
        if output:
            with open(output, "w") as f:
                f.write(json_output)
            click.echo(f"Capabilities written to {output}")
        else:
            click.echo(json_output)
        return capabilities

    capabilities = asyncio.run(_list())
    problems = _validate_allowed_paths(capabilities["server"]["allowedPaths"])
    if problems:
        click.echo("\n⚠️  Configuration issues detected:")
        for problem in problems:
            click.echo(f" - {problem}")


@cli.command()
@click.option("--allowed-paths", multiple=True, help="Allowed file system paths")
@click.option("--cache-root", type=click.Path(), help="Cache root directory")
@click.option("--read-only/--read-write", default=True, help="File system access mode")
def validate_config(
    allowed_paths: tuple[str, ...], cache_root: str | None, read_only: bool
):
    """Validate server configuration and highlight potential issues."""
    if not allowed_paths:
        allowed_paths = (str(Path.cwd()),)
    problems = _validate_allowed_paths(list(allowed_paths))
    if cache_root:
        cache_path = Path(cache_root).expanduser()
        if cache_path.exists() and not cache_path.is_dir():
            problems.append(f"Cache root {cache_path} is not a directory")
        elif not cache_path.exists():
            parent = cache_path.parent
            if not parent.exists():
                problems.append(
                    f"Parent directory for cache root {cache_path} does not exist"
                )
    click.echo("🔍 Configuration review")
    click.echo("=" * 40)
    click.echo(f"Allowed paths: {', '.join(str(Path(p)) for p in allowed_paths)}")
    click.echo(f"Cache root: {cache_root or 'not configured'}")
    click.echo(f"Access mode: {'read-only' if read_only else 'read-write'}")
    if problems:
        click.echo("\n⚠️  Issues detected:")
        for problem in problems:
            click.echo(f" - {problem}")
        sys.exit(1)
    click.echo("\n✅ Configuration looks good!")


@cli.command()
@click.option(
    "--config-file",
    type=click.Path(dir_okay=False, writable=True),
    help="Optional path to write the generated configuration",
)
def setup(config_file: str | None):
    """Interactively configure allowed paths and caching for the server."""
    click.echo("🛠️  RMCP interactive setup")
    click.echo("=" * 40)
    allowed_paths: list[str] = []
    while True:
        default_path = str(Path.cwd()) if not allowed_paths else ""
        path = click.prompt(
            "Enter a directory to expose to the MCP client",
            default=default_path,
            show_default=bool(default_path),
        ).strip()
        if path:
            allowed_paths.append(path)
        if not click.confirm("Add another directory?", default=False):
            break
    read_only = click.confirm("Should file access be read-only?", default=True)
    cache_root = click.prompt(
        "Cache directory (leave blank to skip)", default="", show_default=False
    ).strip()
    config = {
        "allowed_paths": allowed_paths or [str(Path.cwd())],
        "read_only": read_only,
    }
    if cache_root:
        config["cache_root"] = cache_root
    click.echo("\nGenerated configuration:")
    click.echo(json.dumps(config, indent=2))
    if config_file:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        click.echo(f"Configuration written to {config_file}")
    else:
        click.echo("Use these values with `rmcp start` or `rmcp serve-http`.")


@cli.command("check-r-packages")
def check_r_packages():
    """Check R package installation status."""
    import subprocess

    # Define all required packages with their categories
    packages = {
        "Core Statistical": ["jsonlite", "plm", "lmtest", "sandwich", "AER", "dplyr"],
        "Time Series": ["forecast", "vars", "urca", "tseries"],
        "Statistical Testing": ["nortest", "car"],
        "Machine Learning": ["rpart", "randomForest"],
        "Data Visualization": [
            "ggplot2",
            "gridExtra",
            "tidyr",
            "rlang",
            "base64enc",
            "reshape2",
        ],
        "File Operations": ["readxl"],
        "Reporting & Formatting": ["knitr"],
    }
    click.echo("🔍 Checking R Package Installation Status")
    click.echo("=" * 50)
    # Check if R is available
    try:
        result = subprocess.run(
            ["R", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            click.echo("❌ R not found. Please install R first.")
            return
        version_line = result.stdout.split("\n")[0]
        click.echo(f"✅ R is available: {version_line}")
    except Exception as e:
        click.echo(f"❌ R check failed: {e}")
        return
    click.echo()
    # Check each package category
    all_packages = []
    missing_packages = []
    for category, pkg_list in packages.items():
        click.echo(f"📦 {category} Packages:")
        for pkg in pkg_list:
            all_packages.append(pkg)
            try:
                # Check if package is installed
                r_cmd = f'if (require("{pkg}", quietly=TRUE)) cat("INSTALLED") else cat("MISSING")'
                result = subprocess.run(
                    ["R", "--slave", "-e", r_cmd],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if "INSTALLED" in result.stdout:
                    click.echo(f"   ✅ {pkg}")
                else:
                    click.echo(f"   ❌ {pkg}")
                    missing_packages.append(pkg)
            except Exception:
                click.echo(f"   ❓ {pkg} (check failed)")
                missing_packages.append(pkg)
        click.echo()
    # Summary
    installed_count = len(all_packages) - len(missing_packages)
    click.echo(f"📊 Summary: {installed_count}/{len(all_packages)} packages installed")
    if missing_packages:
        click.echo()
        click.echo("❌ Missing Packages:")
        for pkg in missing_packages:
            click.echo(f"   - {pkg}")
        click.echo()
        click.echo("💡 To install missing packages, run in R:")
        missing_str = '", "'.join(missing_packages)
        click.echo(f'   install.packages(c("{missing_str}"))')
        click.echo()
        click.echo("🚀 Or install all RMCP packages at once:")
        all_str = '", "'.join(all_packages)
        click.echo(
            f'   install.packages(c("{all_str}"), repos="https://cran.rstudio.com/")'
        )
    else:
        click.echo()
        click.echo("🎉 All required R packages are installed!")
        click.echo("✅ RMCP is ready to use!")


def _load_config(config_file: str) -> dict:
    """Load configuration from file."""
    import json

    try:
        with open(config_file) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file {config_file}: {e}")
        return {}


def _validate_allowed_paths(paths: list[str]) -> list[str]:
    """Return a list of human-readable warnings for invalid paths."""
    problems: list[str] = []
    seen: set[str] = set()
    for raw_path in paths:
        normalized = str(Path(raw_path).expanduser())
        if normalized in seen:
            problems.append(f"Duplicate allowed path specified: {normalized}")
            continue
        seen.add(normalized)
        path_obj = Path(normalized)
        if not path_obj.exists():
            problems.append(f"Allowed path does not exist: {normalized}")
        elif not path_obj.is_dir():
            problems.append(f"Allowed path is not a directory: {normalized}")
        elif not os.access(path_obj, os.R_OK):
            problems.append(f"Allowed path is not readable: {normalized}")
    return problems


def _register_builtin_tools(server):
    """Register built-in statistical tools and advanced MCP features."""
    from .bidirectional import (
        create_r_callback_session,
        handle_r_callback,
        list_callback_sessions,
        setup_r_bidirectional,
    )
    from .tools.descriptive import frequency_table, outlier_detection, summary_stats
    from .tools.econometrics import instrumental_variables, panel_regression, var_model
    from .tools.fileops import (
        data_info,
        filter_data,
        read_csv,
        read_excel,
        read_json,
        write_csv,
        write_excel,
        write_json,
    )
    from .tools.flexible_r import execute_r_analysis, list_allowed_r_packages
    from .tools.formula_builder import build_formula, validate_formula
    from .tools.helpers import load_example, suggest_fix, validate_data

    # Import advanced MCP integration tools
    from .tools.introspection import (
        get_r_session_info,
        inspect_r_object,
        list_r_objects,
        list_r_packages,
    )
    from .tools.machine_learning import decision_tree, kmeans_clustering, random_forest
    from .tools.regression import (
        correlation_analysis,
        linear_model,
        logistic_regression,
    )
    from .tools.statistical_tests import anova, chi_square_test, normality_test, t_test
    from .tools.timeseries import arima_model, decompose_timeseries, stationarity_test
    from .tools.transforms import difference, lag_lead, standardize, winsorize
    from .tools.visualization import (
        boxplot,
        correlation_heatmap,
        histogram,
        regression_plot,
        scatter_plot,
        time_series_plot,
    )

    # Register all statistical tools
    register_tool_functions(
        server.tools,
        # Original regression tools
        linear_model,
        correlation_analysis,
        logistic_regression,
        # Time series analysis
        arima_model,
        decompose_timeseries,
        stationarity_test,
        # Data transformations
        lag_lead,
        winsorize,
        difference,
        standardize,
        # Statistical tests
        t_test,
        anova,
        chi_square_test,
        normality_test,
        # Descriptive statistics
        summary_stats,
        outlier_detection,
        frequency_table,
        # File operations
        read_csv,
        write_csv,
        data_info,
        filter_data,
        read_excel,
        write_excel,
        read_json,
        write_json,
        # Econometrics
        panel_regression,
        instrumental_variables,
        var_model,
        # Machine learning
        kmeans_clustering,
        decision_tree,
        random_forest,
        # Visualization
        scatter_plot,
        histogram,
        boxplot,
        time_series_plot,
        correlation_heatmap,
        regression_plot,
        # Natural language tools
        build_formula,
        validate_formula,
        # Helper tools
        suggest_fix,
        validate_data,
        load_example,
        # Flexible R execution
        execute_r_analysis,
        list_allowed_r_packages,
        # Advanced MCP Integration - R Session Management
        list_r_objects,
        inspect_r_object,
        list_r_packages,
        get_r_session_info,
        # Advanced MCP Integration - Bidirectional Communication
        create_r_callback_session,
        handle_r_callback,
        setup_r_bidirectional,
        list_callback_sessions,
    )
    logger.info(
        "Registered comprehensive statistical analysis tools (52 total: 44 core + 8 advanced MCP)"
    )


if __name__ == "__main__":
    cli()
