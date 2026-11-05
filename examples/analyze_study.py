"""Inspect, check, and analyze a local bundle through the official MCP client."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def analyze(bundle: Path, request: dict[str, Any]) -> dict[str, Any]:
    """Run the ordinary stdio server with the bundle directory as its root."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "rmcp.cli", "start"],
        cwd=str(bundle.parent),
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
                response = await session.call_tool(name, arguments)
                payload = response.model_dump(mode="json", by_alias=True)
                if payload.get("isError"):
                    raise RuntimeError(f"{name} failed: {payload['content']}")
                return payload["structuredContent"]

            inspection = await call("inspect_study", {"file_path": str(bundle)})
            report = {"ok": False, "inspection": inspection}
            if not inspection["ok"]:
                return report
            arguments = {"study_ref": inspection["study_ref"], "analysis": request}
            checked = await call("check_study_analysis", arguments)
            report["check"] = checked
            if not checked["ok"]:
                return report
            result = await call("run_study_analysis", arguments)
            report["run"] = result
            report["ok"] = result["ok"]
            return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("request", type=Path, help="JSON analysis request")
    parser.add_argument("--output", type=Path, help="Write the JSON report here")
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        parser.error("the analysis request must be a JSON object")
    report = asyncio.run(
        asyncio.wait_for(
            analyze(args.bundle.resolve(strict=True), request), args.timeout
        )
    )
    serialized = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(serialized)
    else:
        print(serialized, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
