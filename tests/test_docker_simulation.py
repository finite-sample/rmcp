"""
Simulate Docker build validation locally.

Tests everything that would happen in the Docker container to ensure the build succeeds.
"""

import subprocess
import sys
from pathlib import Path

def test_r_availability():
    """Test that R is available."""
    try:
        result = subprocess.run(['R', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ R is available")
            return True
        else:
            print("❌ R not available")
            return False
    except:
        print("❌ R not found")
        return False

def test_required_r_packages():
    """Test that required R packages would install."""
    packages = [
        'plm', 'lmtest', 'sandwich', 'AER', 'jsonlite', 
        'forecast', 'dplyr', 'tseries', 'nortest', 'car', 
        'rpart', 'randomForest', 'vars', 'ggplot2', 
        'reshape2', 'gridExtra', 'cluster'
    ]
    
    print(f"Testing {len(packages)} R packages...")
    
    # Test package installation simulation
    for pkg in packages:
        r_script = f'''
        if (!require("{pkg}", quietly = TRUE)) {{
            cat("MISSING: {pkg}\\n")
        }} else {{
            cat("OK: {pkg}\\n")
        }}
        '''
        
        try:
            result = subprocess.run(['R', '-e', r_script], 
                                  capture_output=True, text=True, timeout=15)
            if "MISSING" in result.stdout:
                print(f"⚠️  {pkg} would need installation")
            elif "OK" in result.stdout:
                print(f"✅ {pkg} available")
        except:
            print(f"❓ {pkg} - could not test")

def test_python_dependencies():
    """Test Python dependencies."""
    deps = ['click', 'jsonschema']
    
    print(f"Testing {len(deps)} Python dependencies...")
    
    for dep in deps:
        try:
            __import__(dep)
            print(f"✅ {dep} available")
        except ImportError:
            print(f"❌ {dep} missing")

def test_package_structure():
    """Test package structure matches Dockerfile expectations."""
    required_files = [
        'src/rmcp',
        'pyproject.toml', 
        'requirements.txt'
    ]
    
    print("Testing package structure...")
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")

def test_rmcp_functionality():
    """Test RMCP actually works."""
    try:
        result = subprocess.run([
            'python', '-m', 'src.rmcp.cli', '--version'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and "0.3.0" in result.stdout:
            print("✅ RMCP CLI works and shows v0.3.0")
            return True
        else:
            print(f"❌ RMCP CLI issue: {result}")
            return False
    except Exception as e:
        print(f"❌ RMCP CLI failed: {e}")
        return False

def estimate_docker_image_size():
    """Estimate final Docker image size."""
    
    # Base Ubuntu 22.04: ~70MB
    # R packages: ~200MB
    # Python deps: ~50MB  
    # RMCP source: ~1MB
    
    estimated_size = 70 + 200 + 50 + 1
    print(f"📏 Estimated Docker image size: ~{estimated_size}MB")
    
    if estimated_size > 100:
        print("⚠️  Image will exceed 100MB (mostly due to R packages)")
        print("💡 Consider using rocker/r-base for smaller size")
    else:
        print("✅ Image should be under 100MB")
    
    return estimated_size

def main():
    """Run Docker simulation tests."""
    print("🐳 Docker Build Simulation for RMCP v0.3.0")
    print("=" * 50)
    
    tests = [
        ("R Environment", test_r_availability),
        ("Python Dependencies", test_python_dependencies), 
        ("Package Structure", test_package_structure),
        ("RMCP Functionality", test_rmcp_functionality),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        print("-" * 30)
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    print(f"\n📋 R Package Dependencies:")
    print("-" * 30)
    test_required_r_packages()
    
    print(f"\n📋 Image Size Estimation:")
    print("-" * 30)
    estimated_size = estimate_docker_image_size()
    
    print(f"\n🎯 Docker Simulation Results:")
    print("=" * 50)
    print(f"✅ Core Tests: {passed}/{total} passed")
    print(f"📏 Estimated Size: ~{estimated_size}MB")
    
    if passed == total:
        print("🎉 Docker build should succeed!")
    else:
        print("⚠️  Docker build may have issues")

if __name__ == "__main__":
    main()