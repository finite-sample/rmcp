"""Every tool's published schemas match the committed snapshot.

Tool schemas are what MCP clients see, so a refactor of how they are built must
not change them. After an intended schema change, regenerate the snapshot with::

    uv run python tests/unit/tools/test_tool_schema_snapshot.py
"""

import importlib
import json
import pkgutil
from pathlib import Path
from typing import Any

import rmcp.tools

SNAPSHOT = Path(__file__).parents[2] / "fixtures" / "tool_schemas.json"


def current_schemas() -> dict[str, Any]:
    schemas: dict[str, Any] = {}
    for module_info in pkgutil.iter_modules(rmcp.tools.__path__):
        module = importlib.import_module(f"rmcp.tools.{module_info.name}")
        for obj in vars(module).values():
            name = getattr(obj, "_mcp_tool_name", None)
            if name is None or getattr(obj, "__module__", None) != module.__name__:
                continue
            schemas[name] = {
                "input": obj._mcp_tool_input_schema,
                "output": obj._mcp_tool_output_schema,
            }
    return dict(sorted(schemas.items()))


def test_tool_schemas_match_snapshot():
    expected = json.loads(SNAPSHOT.read_text())
    actual = json.loads(json.dumps(current_schemas()))
    assert actual.keys() == expected.keys()
    for name in expected:
        assert actual[name] == expected[name], name


if __name__ == "__main__":
    SNAPSHOT.write_text(json.dumps(current_schemas(), indent=2, sort_keys=True) + "\n")
