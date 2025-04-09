from rmcp.tools import mcp
from rmcp.server.stdio import stdio_server
import click

@click.group()
def cli():
    """rmcp CLI for running and managing the R Econometrics MCP Server."""
    pass

@cli.command()
def start():
    click.echo("Starting the MCP server via standard input...")
    import sys, traceback
    try:
        stdio_server(mcp)
    except Exception as e:
        print("SERVER CRASHED!", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise


@cli.command()
def version():
    click.echo("rmcp version 0.1.0")

if __name__ == "__main__":
    cli()
