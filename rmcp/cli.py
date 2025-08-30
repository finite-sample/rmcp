from rmcp.tools import mcp
from rmcp.server.stdio import stdio_server
from rmcp.server.legacy_server import legacy_server
import click
import sys
import select
import io

@click.group()
def cli():
    """rmcp CLI for running and managing the R Econometrics MCP Server."""
    pass

def detect_input_mode():
    """
    Detect if input is MCP protocol (starts with Content-Length) or legacy JSON
    """
    if not sys.stdin.isatty():
        # Read all available input
        input_data = sys.stdin.read()
        # Reset stdin for the server to use
        sys.stdin = io.StringIO(input_data)
        
        if input_data.startswith('Content-Length:'):
            # This looks like MCP protocol
            return "mcp"
        elif input_data.strip().startswith('{'):
            # This looks like JSON 
            return "legacy"
    return "legacy"  # Default to legacy mode

@cli.command()
def start():
    click.echo("Starting the MCP server via standard input...")
    import traceback
    try:
        mode = detect_input_mode()
        if mode == "mcp":
            stdio_server(mcp)
        else:
            legacy_server(mcp)
    except Exception as e:
        print("SERVER CRASHED!", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise


@cli.command()
def version():
    click.echo("rmcp version 0.1.1")

@cli.command()
@click.argument('dev_server_file', required=False, default='tests/dev_server.py')
def dev(dev_server_file):
    """Run development server with specified file"""
    click.echo(f"Running development server with {dev_server_file}...")
    import importlib.util
    import sys
    
    try:
        spec = importlib.util.spec_from_file_location("dev_server", dev_server_file)
        dev_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dev_module)
        
        if hasattr(dev_module, 'run_dev_server'):
            dev_module.run_dev_server()
        else:
            click.echo("Dev server file must contain a 'run_dev_server' function")
    except FileNotFoundError:
        click.echo(f"Dev server file not found: {dev_server_file}")
    except Exception as e:
        click.echo(f"Error running dev server: {e}")

if __name__ == "__main__":
    cli()
