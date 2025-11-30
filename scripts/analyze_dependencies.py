#!/usr/bin/env python3
"""
Dependency Analysis Script for RMCP

Systematically analyzes R and Python files to determine required packages.
This ensures we include exactly what RMCP needs, nothing more.
"""

import ast
import re
from pathlib import Path


def extract_python_imports(file_path: Path) -> set[str]:
    """Extract third-party package imports from Python file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get top-level package name
                    pkg = alias.name.split(".")[0]
                    imports.add(pkg)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Get top-level package name
                    pkg = node.module.split(".")[0]
                    imports.add(pkg)

        # Filter out standard library and relative imports
        stdlib_modules = {
            "asyncio",
            "base64",
            "copy",
            "inspect",
            "json",
            "logging",
            "mimetypes",
            "os",
            "platform",
            "queue",
            "re",
            "shutil",
            "subprocess",
            "sys",
            "tempfile",
            "time",
            "uuid",
            "abc",
            "collections",
            "contextlib",
            "contextvars",
            "dataclasses",
            "enum",
            "pathlib",
            "typing",
            "unittest",
            "urllib",
        }

        third_party = imports - stdlib_modules
        # Remove relative imports and rmcp internal imports
        third_party = {
            pkg for pkg in third_party if not pkg.startswith(".") and pkg != "rmcp"
        }

        return third_party

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return set()


def extract_r_libraries(file_path: Path) -> set[str]:
    """Extract R package dependencies from R script."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        libraries = set()

        # Pattern for library() calls
        library_pattern = r'library\s*\(\s*["\']?([^"\'\s,)]+)["\']?\s*\)'
        for match in re.finditer(library_pattern, content):
            libraries.add(match.group(1))

        # Pattern for require() calls
        require_pattern = r'require\s*\(\s*["\']?([^"\'\s,)]+)["\']?'
        for match in re.finditer(require_pattern, content):
            libraries.add(match.group(1))

        # Pattern for requireNamespace() calls
        namespace_pattern = r'requireNamespace\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(namespace_pattern, content):
            libraries.add(match.group(1))

        return libraries

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return set()


def analyze_rmcp_dependencies():
    """Analyze RMCP codebase to determine required dependencies."""

    print("🔍 RMCP Dependency Analysis")
    print("=" * 50)

    # Find project root
    project_root = Path(__file__).parent.parent

    # Analyze Python files in rmcp/
    print("\n📦 Python Dependencies (rmcp/ source code):")
    python_deps = set()
    for py_file in project_root.rglob("rmcp/**/*.py"):
        if "__pycache__" not in str(py_file):
            file_deps = extract_python_imports(py_file)
            if file_deps:
                print(f"  {py_file.relative_to(project_root)}: {file_deps}")
                python_deps.update(file_deps)

    print(f"\n✅ Core Python dependencies needed: {sorted(python_deps)}")

    # Analyze test files
    print("\n🧪 Test-Only Python Dependencies:")
    test_deps = set()
    for py_file in project_root.rglob("tests/**/*.py"):
        if "__pycache__" not in str(py_file):
            file_deps = extract_python_imports(py_file)
            test_deps.update(file_deps)

    test_only_deps = test_deps - python_deps
    print(f"✅ Test-only dependencies: {sorted(test_only_deps)}")

    # Analyze R scripts
    print("\n📊 R Package Dependencies:")
    r_deps = set()
    for r_file in project_root.rglob("rmcp/r_assets/**/*.R"):
        file_deps = extract_r_libraries(r_file)
        if file_deps:
            print(f"  {r_file.relative_to(project_root)}: {file_deps}")
            r_deps.update(file_deps)

    print(f"\n✅ Critical R packages needed: {sorted(r_deps)}")

    # Generate recommendations
    print("\n" + "=" * 50)
    print("📋 DEPENDENCY RECOMMENDATIONS")
    print("=" * 50)

    print("\n🐍 pyproject.toml Production Dependencies:")
    print("# Core dependencies:")
    print(f"dependencies = {sorted(python_deps)}")

    if test_only_deps:
        print("\n# Dev dependencies (test scaffolding):")
        test_list = sorted(test_only_deps)
        # Add version constraints for known packages
        versioned_test_deps = []
        for dep in test_list:
            if dep == "pytest":
                versioned_test_deps.append('"pytest>=8.2.0"')
            elif dep == "pandas":
                versioned_test_deps.append('"pandas>=1.5.0"')
            elif dep == "openpyxl":
                versioned_test_deps.append('"openpyxl>=3.0.0"')
            else:
                versioned_test_deps.append(f'"{dep}"')
        print(f"dev = {versioned_test_deps}")

    print("\n📦 Docker Base Image R Packages Required:")
    print("# Critical R packages for RMCP functionality:")
    r_list = sorted(r_deps)
    for i, pkg in enumerate(r_list):
        end_char = "," if i < len(r_list) - 1 else ""
        print(f'  "{pkg}"{end_char}')

    print(
        f"\n✅ Analysis complete! Found {len(python_deps)} Python + {len(r_deps)} R dependencies."
    )

    return {
        "python_core": python_deps,
        "python_test": test_only_deps,
        "r_packages": r_deps,
    }


if __name__ == "__main__":
    analyze_rmcp_dependencies()
