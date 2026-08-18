#!/usr/bin/env python3
"""Run RMCP's complete local test suite through its canonical pytest harness."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    """Run every collected test and return pytest's exit status."""
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "-v",
        "--tb=short",
    ]
    return subprocess.run(command, cwd=PROJECT_ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
