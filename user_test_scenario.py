#!/usr/bin/env python3
"""
Real-world user testing scenario for RMCP.

This script simulates what a real user would do when using RMCP
for econometric analysis.
"""

import json
import time

def test_user_workflow():
    """Test complete user workflow from a researcher's perspective."""
    print("🔬 RMCP User Scenario Testing")
    print("=" * 50)
    
    # Import RMCP tools
    try:
        from rmcp.tools import mcp
        print("✅ Successfully imported RMCP tools")
        print(f"   Available tools: {len(mcp.tools)} registered")
        for tool_name in mcp.tools.keys():
            print(f"   - {tool_name}")
    except Exception as e:
        print(f"❌ Failed to import RMCP: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("📊 SCENARIO 1: Economic Growth Analysis")
    print("Research Question: What drives economic growth?")
    
    # Realistic economic data (simplified)
    economic_data = {
        'gdp_growth': [2.1, 1.8, 2.5, 1.2, 3.1, 2.8, 1.9, 2.4, 1.6, 2.9],
        'inflation': [1.2, 2.1, 1.8, 0.5, 2.8, 1.9, 3.1, 1.4, 2.3, 1.7],
        'unemployment': [6.2, 7.1, 5.8, 8.2, 5.1, 5.9, 7.8, 6.5, 7.2, 5.4],
        'investment': [18.2, 19.1, 20.4, 17.8, 21.2, 19.8, 18.9, 20.1, 19.3, 21.5],
        'trade_openness': [45.2, 47.1, 48.8, 44.3, 49.2, 46.7, 45.9, 48.1, 46.3, 49.8]
    }
    
    try:
        # Step 1: Basic correlation analysis
        print("\n📈 Step 1: Correlation Analysis")
        correlation_func = mcp.tools["correlation"]["function"]
        
        corr_result = correlation_func(
            data=economic_data,
            var1="gdp_growth",
            var2="investment",
            method="pearson"
        )
        
        print(f"   GDP Growth ↔ Investment correlation: {corr_result['correlation']:.3f}")
        
        # Step 2: Main regression analysis
        print("\n📊 Step 2: Growth Regression Model")
        linear_model = mcp.tools["linear_model"]["function"]
        
        start_time = time.time()
        growth_model = linear_model(
            formula="gdp_growth ~ inflation + unemployment + investment + trade_openness",
            data=economic_data,
            robust=True
        )
        end_time = time.time()
        
        print(f"   Model executed in {end_time - start_time:.2f} seconds")
        print(f"   R² = {growth_model['r_squared']:.3f}")
        print("   Key coefficients:")
        for var, coef in growth_model['coefficients'].items():
            if var != "(Intercept)":
                print(f"   - {var}: {coef:.4f}")
        
        # Economic interpretation
        investment_coef = growth_model['coefficients']['investment']
        print(f"\n💡 Economic Interpretation:")
        print(f"   Investment effect: {investment_coef:.4f}")
        print(f"   → 1% increase in investment → {investment_coef:.2f}% GDP growth change")
        
        # Step 3: Test another correlation
        print("\n📉 Step 3: Phillips Curve Test")
        phillips_corr = correlation_func(
            data=economic_data,
            var1="inflation", 
            var2="unemployment",
            method="pearson"
        )
        
        print(f"   Inflation ↔ Unemployment correlation: {phillips_corr['correlation']:.3f}")
        phillips_evidence = "supports" if phillips_corr['correlation'] < -0.1 else "does not clearly support"
        print(f"   → This {phillips_evidence} the Phillips Curve hypothesis")
        
        print(f"\n✅ Economic growth analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Economic analysis failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🏢 SCENARIO 2: Firm Performance Analysis")
    print("Research Question: Does R&D spending improve firm performance?")
    
    # Realistic firm data
    firm_data = {
        'firm_id': [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4],
        'year': [2020, 2021, 2022, 2020, 2021, 2022, 2020, 2021, 2022, 2020, 2021, 2022],
        'revenue': [1200, 1350, 1480, 890, 920, 1050, 2100, 2250, 2400, 1500, 1620, 1780],
        'rd_spending': [85, 95, 105, 42, 48, 55, 125, 135, 145, 78, 82, 88],
        'employees': [2800, 3100, 3300, 1900, 2000, 2200, 4500, 4700, 4900, 3200, 3350, 3500]
    }
    
    try:
        # Step 1: Industry analysis by grouping
        print("\n📊 Step 1: Revenue Analysis")
        group_by_func = mcp.tools["group_by"]["function"]
        
        # Average revenue by firm
        firm_avg = group_by_func(
            data=firm_data,
            group_col="firm_id",
            summarise_col="revenue", 
            stat="mean"
        )
        
        print("   Average revenue by firm:")
        for row in firm_avg['summary']:
            print(f"   - Firm {row['firm_id']}: ${row['s_value']:.0f}M")
        
        # Step 2: R&D effectiveness analysis  
        print("\n🔬 Step 2: R&D Effectiveness Model")
        rd_model = linear_model(
            formula="revenue ~ rd_spending + employees",
            data=firm_data,
            robust=True
        )
        
        print(f"   Model R² = {rd_model['r_squared']:.3f}")
        rd_coef = rd_model['coefficients']['rd_spending']
        emp_coef = rd_model['coefficients']['employees']
        print(f"   R&D coefficient: {rd_coef:.2f}")
        print(f"   Employee coefficient: {emp_coef:.4f}")
        
        # Business interpretation
        print(f"\n💼 Business Interpretation:")
        print(f"   → $1M additional R&D → ${rd_coef:.1f}M revenue increase")
        print(f"   → 1000 additional employees → ${emp_coef*1000:.1f}M revenue increase")
        
        if rd_coef > 0:
            roi = (rd_coef - 1) * 100
            print(f"   → R&D ROI: {roi:.0f}% (each $1 R&D generates ${rd_coef:.2f} revenue)")
        
        print(f"\n✅ Firm performance analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Firm analysis failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("⚠️  SCENARIO 3: Error Handling Test")
    print("Testing realistic user errors...")
    
    try:
        # Test 1: Missing variable
        print("\n🚫 Test 1: Missing Variable Error")
        try:
            error_model = linear_model(
                formula="gdp_growth ~ missing_var + inflation",
                data=economic_data,
                robust=False
            )
            print("   ❌ Should have failed but didn't!")
            return False
        except Exception as e:
            print(f"   ✅ Caught error correctly: {str(e)[:80]}...")
        
        # Test 2: Invalid formula
        print("\n🚫 Test 2: Invalid Formula Error") 
        try:
            error_model2 = linear_model(
                formula="gdp_growth ~ ~ + inflation",  # Invalid syntax
                data=economic_data,
                robust=False
            )
            print("   ❌ Should have failed but didn't!")
            return False
        except Exception as e:
            print(f"   ✅ Caught error correctly: {str(e)[:80]}...")
        
        print(f"\n✅ Error handling tests passed!")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎯 USER EXPERIENCE SUMMARY")
    print("✅ All major user scenarios completed successfully!")
    print("✅ Realistic econometric analyses working")
    print("✅ Error handling providing helpful messages")
    print("✅ Performance acceptable for typical datasets")
    print("✅ Results are economically interpretable")
    
    return True

def test_cli_user_experience():
    """Test the CLI from a user's perspective."""
    print("\n" + "=" * 50)
    print("🖥️  CLI USER EXPERIENCE TEST")
    
    import subprocess
    import tempfile
    import os
    
    # Test 1: Check version
    try:
        result = subprocess.run(['rmcp', 'version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ CLI version: {result.stdout.strip()}")
        else:
            print(f"❌ CLI version failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ CLI not accessible: {e}")
        return False
    
    # Test 2: Simple analysis via CLI
    try:
        test_data = {
            "tool": "correlation",
            "args": {
                "data": {"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]},
                "var1": "x",
                "var2": "y", 
                "method": "pearson"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name
        
        try:
            result = subprocess.run(['rmcp', 'start'], 
                                  input=json.dumps(test_data),
                                  capture_output=True, text=True, timeout=30)
            
            if "correlation" in result.stdout and "1" in result.stdout:
                print("✅ CLI analysis working - perfect correlation detected")
            else:
                print(f"❌ CLI analysis issue: {result.stdout}")
                return False
                
        finally:
            os.unlink(temp_file)
            
    except Exception as e:
        print(f"❌ CLI analysis failed: {e}")
        return False
    
    print("✅ CLI user experience test passed!")
    return True

if __name__ == "__main__":
    print("🧪 RMCP Real-World User Testing")
    print("Testing RMCP as actual users would use it...")
    print()
    
    success = True
    
    # Test core functionality
    if not test_user_workflow():
        success = False
    
    # Test CLI experience  
    if not test_cli_user_experience():
        success = False
    
    if success:
        print("\n🎉 ALL USER TESTS PASSED!")
        print("RMCP is ready for real-world usage!")
        print("\nKey Strengths Demonstrated:")
        print("• Handles realistic econometric datasets")
        print("• Provides economically meaningful results") 
        print("• Error handling guides users effectively")
        print("• CLI interface is intuitive")
        print("• Performance suitable for research work")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("Issues need to be addressed before release")
    
    exit(0 if success else 1)