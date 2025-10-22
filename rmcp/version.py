"""
Version management for RMCP package.

This module provides version information using importlib.metadata for consistent
version handling across the package.
"""

try:
    from importlib.metadata import PackageNotFoundError, version

    def get_version() -> str:
        """
        Get the version of the RMCP package.

        Returns:
            str: The version string of the installed package, or a fallback
                 version if the package is not installed (development mode).
        """
        try:
            return version("rmcp")
        except PackageNotFoundError:
            # Package is not installed - fallback for development
            return "0.0.0+unknown"

except ImportError:
    # Should not happen with Python >=3.10, but keeping as safety
    def get_version() -> str:
        """Fallback version function for older Python versions."""
        return "0.0.0+unknown"


__all__ = ["get_version"]
