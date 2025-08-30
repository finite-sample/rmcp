"""
Command-line interface for RMCP MCP Server.

Provides entry points for running the server with different transports
and configurations, following the principle of "multiple deployment targets."
"""

import asyncio
import click
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .core.server import create_server
from .transport.stdio import StdioTransport
from .registries.tools import register_tool_functions  
from .registries.resources import ResourcesRegistry
from .registries.prompts import register_prompt_functions, statistical_workflow_prompt, model_diagnostic_prompt

# Configure logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.2.0")
def cli():
    """RMCP MCP Server - Production-ready statistical analysis via Model Context Protocol."""
    pass


@cli.command()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level"
)
def start(log_level: str):
    """Start RMCP MCP server (default stdio transport)."""
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, log_level))
    
    logger.info("Starting RMCP MCP Server")
    
    try:
        # Create and configure server
        server = create_server()
        config = {"allowed_paths": [str(Path.cwd())], "read_only": True}
        server.configure(**config)
        
        # Register built-in statistical tools
        _register_builtin_tools(server)
        
        # Register built-in prompts
        register_prompt_functions(
            server.prompts,
            statistical_workflow_prompt,
            model_diagnostic_prompt
        )
        
        # Set up stdio transport
        transport = StdioTransport()
        transport.set_message_handler(server.handle_request)
        
        # Run the server
        asyncio.run(transport.run())
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--allowed-paths", 
    multiple=True, 
    help="Allowed file system paths (can be specified multiple times)"
)
@click.option(
    "--cache-root",
    type=click.Path(),
    help="Root directory for content caching"
)
@click.option(
    "--read-only/--read-write",
    default=True,
    help="File system access mode (default: read-only)"
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level"
)
@click.option(
    "--config-file",
    type=click.Path(exists=True),
    help="Configuration file path"
)
def serve(
    allowed_paths: List[str],
    cache_root: Optional[str],
    read_only: bool,
    log_level: str,
    config_file: Optional[str],
):
    """Run MCP server with advanced configuration options."""
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, log_level))
    
    logger.info("Starting RMCP MCP Server")
    
    try:
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
            model_diagnostic_prompt
        )
        
        # Set up stdio transport
        transport = StdioTransport()
        transport.set_message_handler(server.handle_request)
        
        # Run the server
        asyncio.run(transport.run())
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


@cli.command()
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
def serve_http(host: str, port: int):
    """Run MCP server over HTTP transport (requires fastapi extras)."""
    try:
        from .transport.http import HTTPTransport
    except ImportError:
        click.echo("HTTP transport requires 'fastapi' extras. Install with: pip install rmcp-mcp[http]")
        sys.exit(1)
    
    logger.info(f"HTTP transport not yet implemented")
    # TODO: Implement HTTP transport
    click.echo("HTTP transport coming soon!")


@cli.command()
@click.option(
    "--allowed-paths",
    multiple=True,
    help="Allowed file system paths"
)
@click.option("--output", type=click.Path(), help="Output file for capabilities")
def list_capabilities(allowed_paths: List[str], output: Optional[str]):
    """List server capabilities (tools, resources, prompts)."""
    
    # Create server to inspect capabilities
    server = create_server()
    if allowed_paths:
        server.configure(allowed_paths=list(allowed_paths))
    
    _register_builtin_tools(server)
    register_prompt_functions(server.prompts, statistical_workflow_prompt, model_diagnostic_prompt)
    
    async def _list():
        from .core.context import Context, LifespanState
        
        context = Context.create("list", "list", server.lifespan_state)
        
        # Get capabilities
        tools = await server.tools.list_tools(context)
        resources = await server.resources.list_resources(context) 
        prompts = await server.prompts.list_prompts(context)
        
        capabilities = {
            "server": {
                "name": server.name,
                "version": server.version,
                "description": server.description
            },
            "tools": tools,
            "resources": resources,
            "prompts": prompts
        }
        
        import json
        json_output = json.dumps(capabilities, indent=2)
        
        if output:
            with open(output, 'w') as f:
                f.write(json_output)
            click.echo(f"Capabilities written to {output}")
        else:
            click.echo(json_output)
    
    asyncio.run(_list())


@cli.command()
def validate_config():
    """Validate server configuration."""
    click.echo("Configuration validation not yet implemented")
    # TODO: Add config validation


def _load_config(config_file: str) -> dict:
    """Load configuration from file."""
    import json
    
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file {config_file}: {e}")
        return {}


def _register_builtin_tools(server):
    """Register built-in statistical tools."""
    from .tools.regression import linear_model, correlation_analysis, logistic_regression
    
    # Register our working statistical tools
    register_tool_functions(
        server.tools,
        linear_model,
        correlation_analysis, 
        logistic_regression
    )
    
    logger.info("Registered statistical analysis tools")


if __name__ == "__main__":
    cli()