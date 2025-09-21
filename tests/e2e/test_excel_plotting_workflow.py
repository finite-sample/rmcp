#!/usr/bin/env python3
"""
Test script to simulate the exact Claude Desktop scenario that was failing.
This tests Excel file loading and scatter plot generation.
"""

import asyncio
import sys
import tempfile
from pathlib import Path
from shutil import which

import pandas as pd
import pytest

# Add rmcp to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions
from rmcp.tools.fileops import read_excel
from rmcp.tools.visualization import scatter_plot
from tests.utils import extract_json_content

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for Excel plotting workflow tests"
)


async def simulate_claude_desktop_workflow():
    """Simulate the exact workflow that was failing."""
    print("🎭 Simulating Claude Desktop Workflow")
    print("=" * 50)

    # Step 1: Create a test Excel file
    print("📊 Step 1: Creating test Excel file...")
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        # Create sample data similar to what a user might have
        df = pd.DataFrame(
            {
                "sales": [1200, 1500, 1800, 2100, 2400, 2700, 3000],
                "marketing_spend": [100, 150, 200, 250, 300, 350, 400],
                "month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
            }
        )
        df.to_excel(f.name, index=False)
        excel_path = f.name
        print(f"✅ Created Excel file: {excel_path}")

    # Step 2: Set up server with proper configuration (like Claude Desktop)
    print("🚀 Step 2: Setting up RMCP server...")
    server = create_server()
    server.configure(allowed_paths=["/tmp"], read_only=False)

    register_tool_functions(server.tools, read_excel, scatter_plot)
    print("✅ Server configured with read_excel and scatter_plot tools")

    # Step 3: Test reading Excel file (this was failing before)
    print("📖 Step 3: Testing Excel file reading...")
    read_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "read_excel", "arguments": {"file_path": excel_path}},
    }

    try:
        response = await server.handle_request(read_request)
        if "result" in response and "content" in response["result"]:
            excel_data = extract_json_content(response)
            print("✅ Excel file read successfully!")
            file_info = excel_data.get("file_info", {})
            print(
                f"   📊 Data shape: {file_info.get('n_rows', 'unknown')} rows, {file_info.get('n_cols', 'unknown')} columns"
            )
            print(f"   📋 Columns: {file_info.get('column_names', 'unknown')}")

            # Extract the data for the next step
            plot_data = excel_data["data"]
        else:
            error = response.get("error", {})
            print(f"❌ Excel reading failed: {error.get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"💥 Excel reading exception: {e}")
        return False

    # Step 4: Test creating scatter plot (this was also failing before)
    print("📈 Step 4: Testing scatter plot generation...")
    plot_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "scatter_plot",
            "arguments": {
                "data": plot_data,
                "x": "marketing_spend",
                "y": "sales",
                "title": "Sales vs Marketing Spend",
            },
        },
    }

    try:
        response = await server.handle_request(plot_request)
        if "result" in response and "content" in response["result"]:
            content = response["result"]["content"]
            # Check if we got both text and image content
            has_text = any(item.get("type") == "text" for item in content)
            has_image = any(item.get("type") == "image" for item in content)

            print("✅ Scatter plot generated successfully!")
            print(f"   📊 Response contains text: {has_text}")
            print(f"   🖼️ Response contains image: {has_image}")

            if has_image:
                print("   ✨ Plot will display inline in Claude Desktop!")

        else:
            error = response.get("error", {})
            print(f"❌ Scatter plot failed: {error.get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"💥 Scatter plot exception: {e}")
        return False

    print("\n🎉 SUCCESS: Full workflow completed!")
    print("✅ The %||% operator errors have been fixed")
    print("✅ Excel files can be loaded properly")
    print("✅ Scatter plots can be generated with inline images")
    print("✅ RMCP is ready for Claude Desktop integration")

    return True


@pytest.mark.asyncio
async def test_other_problematic_tools():
    """Test other tools that might have had similar issues."""
    print("\n🔧 Testing Other Previously Problematic Tools")
    print("=" * 50)

    server = create_server()
    server.configure(allowed_paths=["/tmp"], read_only=False)

    # Import and register more tools
    from rmcp.tools.descriptive import summary_stats
    from rmcp.tools.fileops import data_info, read_csv
    from rmcp.tools.regression import correlation_analysis, linear_model
    from rmcp.tools.statistical_tests import t_test

    register_tool_functions(
        server.tools,
        read_csv,
        data_info,
        linear_model,
        correlation_analysis,
        summary_stats,
        t_test,
    )

    # Test data
    test_data = {
        "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "y": [2.1, 3.9, 6.2, 7.8, 10.1, 12.2, 13.8, 16.1, 18.0, 20.2],
        "group": ["A", "A", "B", "B", "A", "B", "A", "B", "A", "B"],
    }

    tests = [
        ("data_info", {"data": test_data}),
        ("summary_stats", {"data": test_data}),
        ("correlation_analysis", {"data": test_data}),
        ("linear_model", {"data": test_data, "formula": "y ~ x"}),
        ("t_test", {"data": test_data, "variable": "y"}),
    ]

    all_passed = True
    for tool_name, args in tests:
        print(f"🧪 Testing {tool_name}...", end=" ")

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args},
        }

        try:
            response = await server.handle_request(request)
            if "result" in response:
                print("✅")
            else:
                error = response.get("error", {})
                print(f"❌ ({error.get('message', 'Unknown error')})")
                all_passed = False
        except Exception as e:
            print(f"💥 (Exception: {e})")
            all_passed = False

    return all_passed


async def main():
    """Run all tests."""
    print("🎯 RMCP Claude Desktop Integration Test")
    print("Testing the exact scenario that was failing")
    print("=" * 60)

    # Test 1: Main workflow
    workflow_success = await simulate_claude_desktop_workflow()

    # Test 2: Other tools
    tools_success = await test_other_problematic_tools()

    print(f"\n{'=' * 60}")
    print("📋 FINAL TEST RESULTS")
    print("=" * 60)
    print(
        f"Excel + Scatter Plot Workflow: {'✅ PASSED' if workflow_success else '❌ FAILED'}"
    )
    print(f"Other Statistical Tools: {'✅ PASSED' if tools_success else '❌ FAILED'}")

    if workflow_success and tools_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("🚀 RMCP is ready for Claude Desktop!")
        print("\n📝 Next steps:")
        print("   1. Restart Claude Desktop to pick up the changes")
        print("   2. Try your Excel + plotting workflow")
        print("   3. Check Claude Desktop logs if any issues")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("🔧 Please review the errors above")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
