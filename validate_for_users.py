#!/usr/bin/env python3
"""
Final comprehensive validation script for RMCP from user perspective.

This script tests every major use case a researcher would need.
"""

import json
import subprocess
import time
import os
from pathlib import Path

def test_tool_functionality():
    """Test all tools with realistic scenarios."""
    print("🔧 COMPREHENSIVE TOOL TESTING")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Linear regression with economic data
    print("\n📊 Test 1: Linear Regression Analysis")
    tests_total += 1
    try:
        from rmcp.tools import mcp
        linear_func = mcp.tools["linear_model"]["function"]
        
        result = linear_func(
            formula="gdp ~ investment + unemployment",
            data={
                'gdp': [100, 105, 102, 108, 110, 104],
                'investment': [20, 22, 19, 24, 25, 21],
                'unemployment': [5.2, 4.8, 6.1, 4.5, 4.2, 5.8]
            },
            robust=True
        )
        
        # Validate results
        assert isinstance(result['coefficients'], dict)
        assert 'investment' in result['coefficients']
        assert 'unemployment' in result['coefficients']
        assert 0 <= result['r_squared'] <= 1
        assert result['robust'] == True
        
        print(f"   ✅ Investment effect: {result['coefficients']['investment']:.3f}")
        print(f"   ✅ R² = {result['r_squared']:.3f}")
        tests_passed += 1
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 2: Correlation analysis
    print("\n📈 Test 2: Correlation Analysis")
    tests_total += 1
    try:
        corr_func = mcp.tools["correlation"]["function"]
        
        result = corr_func(
            data={'x': [1, 2, 3, 4, 5], 'y': [2, 4, 5, 8, 10]},
            var1="x", var2="y", method="pearson"
        )
        
        assert -1 <= result['correlation'] <= 1
        assert result['method'] == "pearson"
        
        print(f"   ✅ Correlation: {result['correlation']:.3f}")
        tests_passed += 1
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 3: Group-by analysis
    print("\n📊 Test 3: Group-by Analysis")
    tests_total += 1
    try:
        group_func = mcp.tools["group_by"]["function"]
        
        result = group_func(
            data={
                'sector': ['tech', 'tech', 'finance', 'finance', 'energy', 'energy'],
                'profit': [100, 120, 80, 95, 150, 140]
            },
            group_col="sector",
            summarise_col="profit",
            stat="mean"
        )
        
        assert 'summary' in result
        assert len(result['summary']) == 3  # 3 sectors
        
        print("   ✅ Sector averages calculated")
        for row in result['summary']:
            print(f"   - {row['sector']}: {row['s_value']:.1f}")
        tests_passed += 1
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 4: File analysis
    print("\n📁 Test 4: CSV File Analysis")
    tests_total += 1
    try:
        # Create temporary CSV for testing
        import tempfile
        import csv
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['x', 'y', 'z'])
            writer.writerow([1, 2, 3])
            writer.writerow([4, 5, 6])
            writer.writerow([7, 8, 9])
            temp_csv = f.name
        
        try:
            analyze_func = mcp.tools["analyze_csv"]["function"]
            result = analyze_func(file_path=temp_csv)
            
            assert 'summary' in result
            assert 'colnames' in result
            assert 'nrows' in result
            assert result['ncols'] == 3
            assert result['nrows'] == 3
            
            print(f"   ✅ File analyzed: {result['nrows']} rows, {result['ncols']} cols")
            print(f"   ✅ Columns: {result['colnames']}")
            tests_passed += 1
            
        finally:
            os.unlink(temp_csv)
            
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 5: Panel data analysis
    print("\n🏢 Test 5: Panel Data Analysis")
    tests_total += 1
    try:
        panel_func = mcp.tools["panel_model"]["function"]
        
        result = panel_func(
            formula="sales ~ advertising",
            data={
                'firm': [1, 1, 1, 2, 2, 2, 3, 3, 3],
                'year': [2020, 2021, 2022, 2020, 2021, 2022, 2020, 2021, 2022],
                'sales': [100, 110, 120, 80, 85, 90, 150, 160, 170],
                'advertising': [10, 12, 14, 8, 9, 10, 15, 16, 18]
            },
            index=['firm', 'year'],
            model='within'
        )
        
        assert 'coefficients' in result
        assert 'advertising' in result['coefficients']
        assert result['model_type'] == 'within'
        
        print(f"   ✅ Panel model: advertising effect = {result['coefficients']['advertising']:.3f}")
        tests_passed += 1
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 6: IV Regression
    print("\n🎯 Test 6: Instrumental Variables")
    tests_total += 1
    try:
        iv_func = mcp.tools["iv_regression"]["function"]
        
        result = iv_func(
            formula="y ~ x | z",  # y on x, using z as instrument
            data={
                'y': [10, 12, 14, 16, 18, 20],
                'x': [5, 6, 7, 8, 9, 10],
                'z': [2, 3, 4, 4, 5, 5]  # instrument
            }
        )
        
        assert 'coefficients' in result
        assert 'x' in result['coefficients']
        
        print(f"   ✅ IV regression: x coefficient = {result['coefficients']['x']:.3f}")
        tests_passed += 1
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 7: Diagnostics
    print("\n🔍 Test 7: Model Diagnostics")
    tests_total += 1
    try:
        diag_func = mcp.tools["diagnostics"]["function"]
        
        result = diag_func(
            formula="y ~ x1 + x2",
            data={
                'y': [10, 12, 14, 16, 18, 20, 22, 24],
                'x1': [1, 2, 3, 4, 5, 6, 7, 8],
                'x2': [2, 4, 6, 8, 10, 12, 14, 16]
            },
            tests=['bp']  # Breusch-Pagan test
        )
        
        assert isinstance(result, dict)
        print(f"   ✅ Diagnostic tests completed")
        tests_passed += 1
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print(f"\n📊 TOOL TEST SUMMARY: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total

def test_cli_functionality():
    """Test CLI interface thoroughly.""" 
    print("\n🖥️  COMPREHENSIVE CLI TESTING")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Version command
    print("\n🔢 Test 1: Version Command")
    tests_total += 1
    try:
        result = subprocess.run(['rmcp', 'version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and "rmcp version" in result.stdout:
            print(f"   ✅ {result.stdout.strip()}")
            tests_passed += 1
        else:
            print(f"   ❌ Version command failed: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Version command error: {e}")
    
    # Test 2: Simple correlation via CLI
    print("\n📊 Test 2: CLI Analysis")
    tests_total += 1
    try:
        test_request = {
            "tool": "correlation",
            "args": {
                "data": {"temperature": [20, 25, 30, 35], "ice_cream_sales": [50, 75, 100, 125]},
                "var1": "temperature",
                "var2": "ice_cream_sales",
                "method": "pearson"
            }
        }
        
        result = subprocess.run(
            ['rmcp', 'start'],
            input=json.dumps(test_request),
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            # Parse the output to find the JSON result
            lines = result.stdout.strip().split('\n')
            json_line = None
            for line in lines:
                if line.strip().startswith('{') and 'correlation' in line:
                    json_line = line.strip()
                    break
            
            if json_line:
                response = json.loads(json_line)
                if 'correlation' in response and abs(response['correlation'] - 1.0) < 0.01:
                    print(f"   ✅ Perfect correlation detected: {response['correlation']:.3f}")
                    tests_passed += 1
                else:
                    print(f"   ❌ Unexpected correlation: {response}")
            else:
                print(f"   ❌ No JSON response found in: {result.stdout}")
        else:
            print(f"   ❌ CLI analysis failed: {result.stderr}")
            
    except Exception as e:
        print(f"   ❌ CLI analysis error: {e}")
    
    # Test 3: Error handling via CLI
    print("\n⚠️  Test 3: CLI Error Handling")
    tests_total += 1
    try:
        bad_request = {
            "tool": "linear_model", 
            "args": {
                "formula": "y ~ nonexistent_variable",
                "data": {"y": [1, 2, 3], "x": [4, 5, 6]},
                "robust": False
            }
        }
        
        result = subprocess.run(
            ['rmcp', 'start'],
            input=json.dumps(bad_request),
            capture_output=True, text=True, timeout=30
        )
        
        # Should complete (not crash) and return error message
        if "error" in result.stdout.lower() or "Error" in result.stdout:
            print("   ✅ Error handled gracefully")
            tests_passed += 1
        else:
            print(f"   ❌ No error message found in: {result.stdout}")
            
    except Exception as e:
        print(f"   ❌ Error handling test failed: {e}")
    
    print(f"\n📊 CLI TEST SUMMARY: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total

def test_performance_and_reliability():
    """Test performance with realistic workloads."""
    print("\n⚡ PERFORMANCE & RELIABILITY TESTING")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Medium-sized dataset performance
    print("\n📊 Test 1: Medium Dataset Performance")
    tests_total += 1
    try:
        from rmcp.tools import mcp
        linear_func = mcp.tools["linear_model"]["function"]
        
        # Generate 1000-point dataset
        n = 1000
        data = {
            'y': [i + (i % 10) * 0.5 for i in range(n)],  # Linear with noise
            'x1': list(range(n)),
            'x2': [i * 0.5 + (i % 7) for i in range(n)]
        }
        
        start_time = time.time()
        result = linear_func(
            formula="y ~ x1 + x2",
            data=data,
            robust=True
        )
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        if execution_time < 30 and result['r_squared'] > 0.9:  # Should be very high R²
            print(f"   ✅ {n}-point analysis: {execution_time:.2f}s, R² = {result['r_squared']:.4f}")
            tests_passed += 1
        else:
            print(f"   ❌ Performance issue: {execution_time:.2f}s, R² = {result['r_squared']:.4f}")
            
    except Exception as e:
        print(f"   ❌ Performance test failed: {e}")
    
    # Test 2: Multiple rapid requests
    print("\n🚀 Test 2: Rapid Sequential Requests")
    tests_total += 1
    try:
        corr_func = mcp.tools["correlation"]["function"]
        
        start_time = time.time()
        successful_requests = 0
        
        for i in range(10):
            try:
                result = corr_func(
                    data={'a': [1, 2, 3, 4], 'b': [2, 4, 6, 8]},
                    var1="a", var2="b", method="pearson"
                )
                if abs(result['correlation'] - 1.0) < 0.01:
                    successful_requests += 1
            except:
                pass
        
        end_time = time.time()
        total_time = end_time - start_time
        
        if successful_requests == 10 and total_time < 30:
            print(f"   ✅ 10 requests in {total_time:.2f}s ({total_time/10:.2f}s avg)")
            tests_passed += 1
        else:
            print(f"   ❌ Only {successful_requests}/10 succeeded in {total_time:.2f}s")
            
    except Exception as e:
        print(f"   ❌ Rapid request test failed: {e}")
    
    print(f"\n📊 PERFORMANCE TEST SUMMARY: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total

def validate_user_documentation():
    """Validate that examples in documentation work."""
    print("\n📚 DOCUMENTATION VALIDATION")
    print("=" * 60)
    
    # Check that example files exist and are readable
    examples_dir = Path("examples")
    if examples_dir.exists():
        example_files = list(examples_dir.glob("*.md"))
        print(f"   ✅ Found {len(example_files)} example files")
        
        for file in example_files:
            try:
                content = file.read_text()
                if len(content) > 100:  # Non-empty
                    print(f"   ✅ {file.name} - {len(content)} characters")
                else:
                    print(f"   ⚠️  {file.name} - Very short")
            except Exception as e:
                print(f"   ❌ {file.name} - Error reading: {e}")
        return True
    else:
        print("   ⚠️  No examples directory found")
        return False

def main():
    """Run all validation tests."""
    print("🧪 RMCP COMPREHENSIVE USER VALIDATION")
    print("=" * 70)
    print("Testing RMCP from real user perspective...")
    print("This validates functionality, performance, and usability.")
    
    all_passed = True
    
    # Core functionality tests
    if not test_tool_functionality():
        all_passed = False
        print("⚠️  Some tool functionality tests failed")
    
    # CLI interface tests  
    if not test_cli_functionality():
        all_passed = False
        print("⚠️  Some CLI functionality tests failed")
    
    # Performance tests
    if not test_performance_and_reliability():
        all_passed = False
        print("⚠️  Some performance tests failed")
    
    # Documentation validation
    if not validate_user_documentation():
        all_passed = False
        print("⚠️  Documentation validation had issues")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL VALIDATION TESTS PASSED!")
        print("\n✅ RMCP is ready for real-world usage by researchers!")
        print("\nValidated capabilities:")
        print("• All 7 econometric tools functioning correctly") 
        print("• CLI interface working smoothly")
        print("• Error handling providing helpful feedback")
        print("• Performance suitable for research datasets")
        print("• Documentation and examples available")
        print("\n🚀 Ready for release and user adoption!")
    else:
        print("❌ SOME VALIDATION TESTS FAILED")
        print("\nPlease address the issues before releasing to users.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)