#!/usr/bin/env python3
"""
Test script to run the local development version of RMCP.

This bypasses the installed package and uses the updated code in src/
"""
import sys
import os

# Add the src directory to Python path so we use local development code
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now import and run the CLI
from rmcp.cli import cli

if __name__ == '__main__':
    cli()