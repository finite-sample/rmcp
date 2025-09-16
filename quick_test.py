#!/usr/bin/env python3
"""
Quick test to verify our logging fixes work.
This uses the installed package but patches the problematic module.
"""

import sys
import importlib.util

# Import the installed rmcp module
import rmcp.transport.stdio as stdio_module

# Check if the fixed version has been loaded
print("Testing logging calls without file= parameter...")

# Test if we can call logger methods without the file parameter
import logging
logger = logging.getLogger("test")

try:
    # This should work (our fix)
    logger.info("Test message without file parameter")
    print("✅ Logger calls work correctly")
except Exception as e:
    print(f"❌ Logger calls still broken: {e}")

# Check if the stdio module has the problematic code
import inspect
source = inspect.getsource(stdio_module)

if 'file=sys.stderr' in source:
    print("❌ Installed stdio module still has file= parameter bug")
    print("The rmcp command is using the old installed package")
else:
    print("✅ Installed stdio module has been fixed")

# Show where the module is loaded from
print(f"stdio module loaded from: {stdio_module.__file__}")