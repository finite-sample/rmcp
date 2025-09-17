"""
End-to-end tests simulating realistic Claude Desktop user scenarios
with the new features added in v0.3.5.

These tests simulate actual conversations users would have with Claude Desktop
using RMCP's enhanced capabilities.
"""

import asyncio
import json
import tempfile
import os
import sys
from pathlib import Path

# Add rmcp to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions

# Import comprehensive tool set
from rmcp.tools.regression import linear_model, correlation_analysis, logistic_regression
from rmcp.tools.fileops import read_csv, read_json, read_excel, data_info
from rmcp.tools.formula_builder import build_formula, validate_formula
from rmcp.tools.helpers import suggest_fix, validate_data, load_example


async def create_claude_desktop_server():
    """Create server exactly as Claude Desktop would see it."""
    server = create_server()
    server.configure(allowed_paths=["/tmp"], read_only=False)
    
    # Register all tools that would be available in Claude Desktop
    register_tool_functions(
        server.tools,
        # Core analysis tools
        linear_model, correlation_analysis, logistic_regression,
        # Enhanced file operations
        read_csv, read_json, read_excel, data_info,
        # New natural language features
        build_formula, validate_formula,
        # Helper and recovery tools
        suggest_fix, validate_data, load_example
    )
    
    return server


async def simulate_claude_request(server, request_id, tool_name, arguments, user_intent):
    """Simulate how Claude Desktop would make a request."""
    print(f"\n💬 User: {user_intent}")
    print(f"🤖 Claude calls: {tool_name}")
    
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    try:
        response = await server.handle_request(request)
        
        if 'result' in response and 'content' in response['result']:
            content = response['result']['content'][0]['text']
            result_data = json.loads(content)
            print(f"✅ Success: {tool_name} completed")
            return result_data
        else:
            error = response.get('error', {})
            print(f"❌ Failed: {error.get('message', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"💥 Exception: {e}")
        return None


async def scenario_1_natural_formula_to_analysis():
    """Scenario: User wants to analyze relationship using natural language."""
    print("\n" + "="*70)
    print("📊 SCENARIO 1: Natural Language to Statistical Analysis")
    print("="*70)
    print("User Goal: Analyze customer satisfaction and purchase behavior")
    
    server = await create_claude_desktop_server()
    
    # Step 1: User describes what they want in natural language
    formula_result = await simulate_claude_request(
        server, 1, "build_formula",
        {
            "description": "predict customer satisfaction from purchase frequency and age",
            "analysis_type": "regression"
        },
        "I want to see if customer satisfaction depends on how often they buy and their age"
    )
    
    if not formula_result:
        return False
    
    formula = formula_result["formula"]
    print(f"   📝 Formula created: {formula}")
    
    # Step 2: Load example data to work with
    data_result = await simulate_claude_request(
        server, 2, "load_example",
        {
            "dataset_name": "survey",
            "size": "small"
        },
        "Can you load some example customer survey data?"
    )
    
    if not data_result:
        return False
    
    dataset = data_result["data"]
    print(f"   📊 Dataset loaded: {data_result['metadata']['rows']} customers")
    
    # Step 3: Validate the formula works with the data
    validation_result = await simulate_claude_request(
        server, 3, "validate_formula",
        {
            "formula": "satisfaction ~ purchase_frequency + age",
            "data": dataset
        },
        "Before running the full analysis, can you check if my formula will work?"
    )
    
    if not validation_result:
        return False
    
    print(f"   ✅ Formula validation: {'Valid' if validation_result['is_valid'] else 'Invalid'}")
    
    # Step 4: Run the actual analysis
    analysis_result = await simulate_claude_request(
        server, 4, "linear_model",
        {
            "data": dataset,
            "formula": "satisfaction ~ purchase_frequency + age"
        },
        "Great! Now run the regression analysis to see the relationships"
    )
    
    if not analysis_result:
        return False
    
    r_squared = analysis_result.get("r_squared", 0)
    print(f"   📈 Analysis completed: R² = {r_squared:.3f}")
    
    print("\n🎉 Scenario 1 completed successfully!")
    print("   User went from natural language to statistical results seamlessly")
    return True


async def scenario_2_file_analysis_with_help():
    """Scenario: User has a file and needs help with analysis."""
    print("\n" + "="*70)
    print("📁 SCENARIO 2: File Analysis with Intelligent Help")
    print("="*70)
    print("User Goal: Analyze JSON data file with error recovery help")
    
    server = await create_claude_desktop_server()
    
    # Create a realistic JSON file
    quarterly_data = {
        "company_metrics": [
            {"quarter": "Q1_2023", "revenue": 1250000, "marketing_spend": 85000, "customer_satisfaction": 8.2},
            {"quarter": "Q2_2023", "revenue": 1380000, "marketing_spend": 92000, "customer_satisfaction": 8.4},
            {"quarter": "Q3_2023", "revenue": 1190000, "marketing_spend": 78000, "customer_satisfaction": 7.9},
            {"quarter": "Q4_2023", "revenue": 1520000, "marketing_spend": 105000, "customer_satisfaction": 8.7}
        ]
    }
    
    json_file = "/tmp/quarterly_metrics.json"
    with open(json_file, 'w') as f:
        json.dump(quarterly_data, f, indent=2)
    
    try:
        # Step 1: Load JSON file
        file_result = await simulate_claude_request(
            server, 1, "read_json",
            {
                "file_path": json_file,
                "flatten": True
            },
            "I have quarterly metrics in a JSON file. Can you load and analyze it?"
        )
        
        if not file_result:
            return False
        
        dataset = file_result["data"]
        print(f"   📊 JSON loaded: {file_result['file_info']['rows']} quarters")
        
        # Step 2: Validate data quality
        validation_result = await simulate_claude_request(
            server, 2, "validate_data",
            {
                "data": dataset,
                "analysis_type": "correlation",
                "strict": True
            },
            "Can you check if this data is good for correlation analysis?"
        )
        
        if not validation_result:
            return False
        
        print(f"   🔍 Data quality: {'✓ Good' if validation_result['is_valid'] else '⚠ Issues'}")
        if validation_result.get('warnings'):
            print(f"   ⚠️  Warnings: {len(validation_result['warnings'])}")
        
        # Step 3: Run correlation analysis
        correlation_result = await simulate_claude_request(
            server, 3, "correlation_analysis",
            {
                "data": dataset,
                "method": "pearson"
            },
            "Now analyze the correlations between revenue, marketing spend, and satisfaction"
        )
        
        if not correlation_result:
            return False
        
        correlations = correlation_result.get("correlation_matrix", {})
        print(f"   📈 Correlations computed: {len(correlations)} relationships analyzed")
        
        print("\n🎉 Scenario 2 completed successfully!")
        print("   User successfully analyzed their JSON file with data validation")
        return True
        
    finally:
        try:
            os.unlink(json_file)
        except:
            pass


async def scenario_3_error_recovery_workflow():
    """Scenario: User encounters error and gets intelligent help."""
    print("\n" + "="*70)
    print("🔧 SCENARIO 3: Error Recovery and Learning")
    print("="*70)
    print("User Goal: Get help when things go wrong")
    
    server = await create_claude_desktop_server()
    
    # Step 1: User encounters a package error
    error_result = await simulate_claude_request(
        server, 1, "suggest_fix",
        {
            "error_message": "there is no package called 'forecast'",
            "tool_name": "arima_model"
        },
        "I'm getting an error about a missing 'forecast' package. Can you help?"
    )
    
    if not error_result:
        return False
    
    print(f"   🔍 Error diagnosed: {error_result['error_type']}")
    print(f"   💡 Fix suggested: {error_result['suggestions'][0][:60]}...")
    
    # Step 2: User wants to learn with example data
    example_result = await simulate_claude_request(
        server, 2, "load_example",
        {
            "dataset_name": "timeseries",
            "size": "small"
        },
        "Can you load some example time series data so I can practice?"
    )
    
    if not example_result:
        return False
    
    print(f"   📊 Example data: {example_result['metadata']['description']}")
    print(f"   💡 Suggested analyses: {len(example_result['suggested_analyses'])} options")
    
    # Step 3: User wants to understand formula building
    formula_result = await simulate_claude_request(
        server, 3, "build_formula",
        {
            "description": "analyze value over time",
            "analysis_type": "regression"
        },
        "How would I build a formula to analyze trends over time?"
    )
    
    if not formula_result:
        return False
    
    print(f"   📝 Formula suggestion: {formula_result['formula']}")
    print(f"   📚 Interpretation: {formula_result['interpretation'][:60]}...")
    
    print("\n🎉 Scenario 3 completed successfully!")
    print("   User received intelligent help and learned how to proceed")
    return True


async def main():
    """Run all Claude Desktop E2E scenarios."""
    print("🎭 RMCP Claude Desktop End-to-End Scenarios")
    print("🤖 Testing realistic user interactions with new features")
    print("=" * 80)
    
    scenarios = [
        ("Natural Language to Analysis", scenario_1_natural_formula_to_analysis),
        ("File Analysis with Help", scenario_2_file_analysis_with_help),
        ("Error Recovery and Learning", scenario_3_error_recovery_workflow)
    ]
    
    passed = 0
    for i, (name, scenario_func) in enumerate(scenarios, 1):
        print(f"\n🎯 RUNNING SCENARIO {i}/3: {name}")
        
        try:
            success = await scenario_func()
            if success:
                passed += 1
                print(f"✅ SCENARIO {i} PASSED")
            else:
                print(f"❌ SCENARIO {i} FAILED")
        except Exception as e:
            print(f"💥 SCENARIO {i} ERROR: {e}")
    
    # Results
    print("\n" + "=" * 80)
    print("🎉 CLAUDE DESKTOP E2E TEST RESULTS")
    print("=" * 80)
    print(f"✅ Scenarios Passed: {passed}/{len(scenarios)}")
    print(f"📊 Success Rate: {passed/len(scenarios)*100:.1f}%")
    
    if passed == len(scenarios):
        print("\n🎊 ALL SCENARIOS PASSED!")
        print("🤖 Claude Desktop integration ready!")
        print("\n💡 New capabilities demonstrated:")
        print("   • Natural language formula building")
        print("   • Enhanced file format support (JSON, Excel)")
        print("   • Pre-analysis data validation") 
        print("   • Intelligent error recovery")
        print("   • Example datasets for learning")
        print("   • Seamless workflow integration")
    elif passed >= len(scenarios) * 0.8:
        print("\n✨ Most scenarios passed - excellent!")
    else:
        print("\n⚠️ Several scenarios failed - needs attention")
    
    return passed == len(scenarios)


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        exit(1)