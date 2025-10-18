"""
Configuration Management for RMCP.

Provides a hierarchical configuration system supporting:
- Environment variables (RMCP_ prefix)
- Configuration files (JSON/YAML)
- Command-line overrides
- Validation and type safety
"""

from .loader import get_config, load_config
from .models import RMCPConfig

__all__ = ["get_config", "load_config", "RMCPConfig"]
