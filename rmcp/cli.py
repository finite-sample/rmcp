# rmcp/cli.py
import click
import os

# Import your server's main function from rmcp, adjust the import if necessary.
from rmcp.server.stdio import stdio_server
from rmcp.server.fastmcp import FastMCP

# Initialize your MCP server (update the parameters as needed)
mcp = FastMCP(
    name="R Econometrics",
    version="0.1.0",
    description="A Model Context Protocol server for R-based econometric analysis"
)

@click.group()
def cli():
    """rmcp CLI for running and managing the R Econometrics MCP Server."""
    pass

@cli.command()
@click.argument("server_file", type=click.Path(exists=True))
def dev(server_file):
    """
    Run the MCP server in development mode from the given server file.
    
    SERVER_FILE: The Python file containing your MCP server definition.
    """
    click.echo(f"Running MCP server in development mode from {server_file}...")
    with open(server_file) as f:
        code = f.read()
        exec(code, globals())

@cli.command()
def start():
    """
    Start the MCP server using the default configuration.
    """
    click.echo("Starting the MCP server via standard input...")
    stdio_server(mcp)

@cli.command()
def version():
    """Show the version of the rmcp package."""
    click.echo("rmcp version 0.1.0")

if __name__ == "__main__":
    cli()
