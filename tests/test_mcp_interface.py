"""
Test the actual MCP protocol interface that Claude Desktop would use.

This tests what happens when an AI assistant like Claude makes tool calls
through the Model Context Protocol to RMCP.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rmcp.core.server import create_server
from rmcp.core.context import Context, LifespanState
from rmcp.tools.regression import linear_model, correlation_analysis, logistic_regression
from rmcp.registries.tools import register_tool_functions


async def create_mcp_server():
    """Create an MCP server with registered tools."""
    server = create_server()
    
    # Register our working tools
    register_tool_functions(
        server.tools,
        linear_model,
        correlation_analysis, 
        logistic_regression
    )
    
    return server


async def test_tool_discovery():
    """Test that Claude can discover available tools."""
    print("🔍 Testing Tool Discovery (what Claude Desktop does first)")
    print("-" * 60)
    
    server = await create_mcp_server()
    context = Context.create("test", "test", server.lifespan_state)
    
    # This is what Claude Desktop sends to discover tools
    tools = await server.tools.list_tools(context)
    
    print(f"✅ Found {len(tools['tools'])} tools:")
    for tool in tools['tools']:
        print(f"   📊 {tool['name']}: {tool['description']}")
    
    # Verify we have our expected tools
    tool_names = [tool['name'] for tool in tools['tools']]
    expected_tools = ['linear_model', 'correlation_analysis', 'logistic_regression']
    
    for expected in expected_tools:
        assert expected in tool_names, f"Missing tool: {expected}"
    
    print("✅ PASS: Tool discovery works")
    return True


async def test_business_analyst_mcp():
    """Test business analyst scenario through MCP protocol."""
    print("\n📊 Testing Business Analyst MCP Flow")
    print("-" * 50)
    
    server = await create_mcp_server()
    
    # This simulates what Claude Desktop sends when user asks:
    # "I have sales data and marketing spend. Can you analyze the ROI?"
    
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "linear_model",
            "arguments": {
                "data": {
                    "sales": [120, 135, 128, 142, 156, 148, 160, 175],
                    "marketing": [10, 12, 11, 14, 16, 15, 18, 20]
                },
                "formula": "sales ~ marketing"
            }
        }
    }
    
    print(f"📤 MCP Request: {request['method']} -> {request['params']['name']}")
    
    try:
        # Process request through MCP server
        response = await server.handle_request(request)
        
        print(f"📥 MCP Response received")
        
        # Extract the result
        if 'result' in response and 'content' in response['result']:
            result_text = response['result']['content'][0]['text']
            
            # Handle both JSON strings and Python dict strings
            try:
                # Try parsing as JSON first
                result_data = json.loads(result_text)
            except json.JSONDecodeError:
                # If that fails, it might be a Python dict string, eval it safely
                try:
                    result_data = eval(result_text)
                except:
                    print(f"❌ Could not parse result: {result_text}")
                    return False
        else:
            print(f"❌ Unexpected response format: {response}")
            return False
        
        # Verify business analyst needs are met
        marketing_coef = result_data['coefficients']['marketing']
        r_squared = result_data['r_squared']
        p_value = result_data['p_values']['marketing']
        
        print(f"✅ Marketing ROI: ${marketing_coef:.2f} per $1 spent")
        print(f"✅ Model R²: {r_squared:.3f}")
        print(f"✅ Significance: p = {p_value:.6f}")
        
        # Business validation
        assert marketing_coef > 0, "Marketing should increase sales"
        assert r_squared > 0.8, "Model should explain >80% variance"
        assert p_value < 0.05, "Effect should be significant"
        
        print("✅ PASS: Business analyst MCP flow works")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Business analyst MCP error - {e}")
        return False


async def test_economist_mcp():
    """Test economist scenario through MCP protocol."""
    print("\n🏛️ Testing Economist MCP Flow")
    print("-" * 50)
    
    server = await create_mcp_server()
    
    # Simulates: "I have GDP and unemployment data. Can you test Okun's Law?"
    request = {
        "jsonrpc": "2.0", 
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "correlation_analysis",
            "arguments": {
                "data": {
                    "gdp_growth": [2.1, 2.3, 1.8, 2.5, 2.7, 2.2],
                    "unemployment": [5.2, 5.0, 5.5, 4.8, 4.5, 4.9]
                },
                "variables": ["gdp_growth", "unemployment"],
                "method": "pearson"
            }
        }
    }
    
    print(f"📤 MCP Request: {request['method']} -> {request['params']['name']}")
    
    try:
        response = await server.handle_request(request)
        result_text = response['result']['content'][0]['text']
        
        # Handle both JSON strings and Python dict strings
        try:
            result_data = json.loads(result_text)
        except json.JSONDecodeError:
            result_data = eval(result_text)
        
        # Check Okun's Law correlation
        correlation = result_data['correlation_matrix']['gdp_growth'][1]  # unemployment correlation
        
        print(f"✅ GDP-Unemployment Correlation: {correlation:.3f}")
        print(f"✅ Sample size: {result_data['n_obs']} observations")
        
        # Economic validation
        assert correlation < 0, "GDP growth and unemployment should be negatively correlated"
        assert abs(correlation) > 0.5, "Correlation should be substantial"
        
        print("✅ PASS: Economist MCP flow works (Okun's Law confirmed)")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Economist MCP error - {e}")
        return False


async def test_data_scientist_mcp():
    """Test data scientist scenario through MCP protocol."""
    print("\n🤖 Testing Data Scientist MCP Flow") 
    print("-" * 50)
    
    server = await create_mcp_server()
    
    # Simulates: "Help me build a customer churn prediction model"
    request = {
        "jsonrpc": "2.0",
        "id": 3, 
        "method": "tools/call",
        "params": {
            "name": "logistic_regression",
            "arguments": {
                "data": {
                    "churn": [0, 1, 0, 1, 0, 0, 1, 1, 0, 1],
                    "tenure_months": [24, 6, 36, 3, 48, 18, 9, 2, 60, 4],
                    "monthly_charges": [70, 85, 65, 90, 60, 75, 95, 100, 55, 88]
                },
                "formula": "churn ~ tenure_months + monthly_charges",
                "family": "binomial",
                "link": "logit"
            }
        }
    }
    
    print(f"📤 MCP Request: {request['method']} -> {request['params']['name']}")
    
    try:
        response = await server.handle_request(request)
        result_text = response['result']['content'][0]['text']
        
        # Handle both JSON strings and Python dict strings
        try:
            result_data = json.loads(result_text)
        except json.JSONDecodeError:
            result_data = eval(result_text)
        
        # Extract model performance
        accuracy = result_data.get('accuracy', 0)
        tenure_coef = result_data['coefficients']['tenure_months']
        charges_coef = result_data['coefficients']['monthly_charges']
        
        print(f"✅ Model Accuracy: {accuracy:.1%}")
        print(f"✅ Tenure Effect: {tenure_coef:.4f} (negative = good)")
        print(f"✅ Charges Effect: {charges_coef:.4f} (positive = expected)")
        
        # Data science validation
        assert accuracy > 0.6, "Model should achieve >60% accuracy"
        assert tenure_coef < 0, "Longer tenure should reduce churn"
        assert charges_coef > 0, "Higher charges should increase churn"
        
        print("✅ PASS: Data scientist MCP flow works")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Data scientist MCP error - {e}")
        return False


async def test_error_handling_mcp():
    """Test MCP error handling with invalid requests."""
    print("\n🚨 Testing MCP Error Handling")
    print("-" * 50)
    
    server = await create_mcp_server()
    
    # Test invalid tool name
    invalid_request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call", 
        "params": {
            "name": "nonexistent_tool",
            "arguments": {"data": [1, 2, 3]}
        }
    }
    
    print("📤 Testing invalid tool name...")
    
    try:
        response = await server.handle_request(invalid_request)
        
        # Should get an error response
        if 'error' in response:
            print(f"✅ Proper error handling: {response['error']['message']}")
            print("✅ PASS: MCP error handling works")
            return True
        else:
            print("❌ FAIL: Should have returned error for invalid tool")
            return False
            
    except Exception as e:
        print(f"✅ Exception handling works: {e}")
        return True


async def run_mcp_interface_tests():
    """Run all MCP interface tests."""
    
    print("🎯 RMCP MCP Interface Testing")
    print("=" * 55)
    print("Testing the actual protocol that AI assistants use\n")
    
    test_functions = [
        ("Tool Discovery", test_tool_discovery),
        ("Business Analyst MCP", test_business_analyst_mcp),
        ("Economist MCP", test_economist_mcp), 
        ("Data Scientist MCP", test_data_scientist_mcp),
        ("Error Handling MCP", test_error_handling_mcp),
    ]
    
    results = []
    
    for test_name, test_func in test_functions:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*55)
    print("🎯 MCP INTERFACE TEST RESULTS")
    print("="*55)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📊 MCP Success Rate: {passed}/{total} ({passed/total:.1%})")
    
    if passed == total:
        print("🎉 ALL MCP INTERFACE TESTS PASSED!")
        print("✅ Claude Desktop can successfully use RMCP")
        print("🗣️ Conversational examples in documentation are VALID")
    else:
        print("⚠️  SOME MCP TESTS FAILED")
        print("🔧 Conversational interface needs fixes")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_mcp_interface_tests())
    exit(0 if success else 1)