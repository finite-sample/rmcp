"""
Estimate Docker image size for optimized RMCP build.
"""

def estimate_optimized_image_size():
    """Estimate the size of the optimized Docker image."""
    
    # Base python:3.11-slim image: ~45MB
    base_size = 45
    
    # R base package: ~40MB
    r_base = 40
    
    # Essential system libs (curl, ssl): ~10MB  
    system_libs = 10
    
    # Core R package (jsonlite): ~5MB
    r_packages = 5
    
    # Python dependencies (click, jsonschema): ~8MB
    python_deps = 8
    
    # RMCP source code: ~1MB
    rmcp_source = 1
    
    total_size = base_size + r_base + system_libs + r_packages + python_deps + rmcp_source
    
    print("🐳 Optimized Docker Image Size Estimation")
    print("=" * 45)
    print(f"Base python:3.11-slim:     {base_size:3d} MB")
    print(f"R base installation:       {r_base:3d} MB") 
    print(f"System libraries:          {system_libs:3d} MB")
    print(f"Core R packages:           {r_packages:3d} MB")
    print(f"Python dependencies:       {python_deps:3d} MB")
    print(f"RMCP source code:          {rmcp_source:3d} MB")
    print("-" * 45)
    print(f"TOTAL ESTIMATED SIZE:      {total_size:3d} MB")
    
    if total_size <= 100:
        print("✅ Under 100MB target!")
    else:
        print("❌ Exceeds 100MB target")
        print("💡 Additional optimizations needed")
    
    print("\n📝 Notes:")
    print("- Additional R packages install on-demand (~5-10MB each)")
    print("- First-time tool usage will trigger package installation")
    print("- Core statistical tools (regression, correlation) work immediately")
    
    return total_size

if __name__ == "__main__":
    size = estimate_optimized_image_size()
    exit(0 if size <= 100 else 1)