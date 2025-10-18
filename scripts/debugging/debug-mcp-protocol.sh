#!/bin/bash
set -e

echo "🐳 Testing MCP Protocol Communication Locally..."

# Build the same Docker environment as CI
docker build -t rmcp-test . > /dev/null 2>&1

echo "🔍 Running MCP protocol debugging..."
docker run --rm -v $(pwd):/workspace rmcp-test bash -c '
export PATH="/opt/venv/bin:$PATH"
cd /workspace
pip install -e . > /dev/null 2>&1

echo "=== Testing R Integration First ==="
python -c "
try:
    from rmcp.r_integration import check_r_version
    is_compatible, version_string = check_r_version()
    print(f\"✅ R version check: {version_string} (compatible: {is_compatible})\")
except Exception as e:
    print(f\"❌ R version check failed: {e}\")
"

echo ""
echo "=== Testing RMCP CLI Basic Commands ==="
echo "rmcp --version:"
rmcp --version

echo ""
echo "rmcp list-capabilities (should work):"
timeout 5 rmcp list-capabilities || echo "❌ list-capabilities timed out or failed"

echo ""
echo "=== Testing RMCP Start Command (Direct) ==="
echo "Starting rmcp start with DEBUG logging..."
timeout 3 rmcp start --log-level DEBUG 2>&1 | head -10 || echo "❌ rmcp start timed out or crashed"

echo ""
echo "=== Testing MCP Protocol Communication (Exact CI Test) ==="
python -c "
import subprocess
import json
import sys

# Test MCP initialize message (exact same as CI)
init_msg = {
    \"jsonrpc\": \"2.0\",
    \"id\": 1,
    \"method\": \"initialize\",
    \"params\": {
        \"protocolVersion\": \"2025-06-18\",
        \"capabilities\": {\"tools\": {}},
        \"clientInfo\": {\"name\": \"Test Client\", \"version\": \"1.0.0\"}
    }
}

print(f\"Sending MCP message: {json.dumps(init_msg)}\")

process = subprocess.Popen([\"rmcp\", \"start\"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE, text=True)

try:
    stdout, stderr = process.communicate(
        input=json.dumps(init_msg) + \"\n\", timeout=10)
    
    print(f\"Return code: {process.returncode}\")
    print(f\"STDOUT ({len(stdout)} chars): {repr(stdout[:500])}\")
    print(f\"STDERR ({len(stderr)} chars): {repr(stderr[:500])}\")
    
    # Look for JSON response
    found_json = False
    for line in stdout.strip().split(\"\n\"):
        if line.startswith(\'{\') and \"jsonrpc\" in line:
            try:
                response = json.loads(line)
                assert response[\"jsonrpc\"] == \"2.0\"
                assert \"result\" in response
                print(f\"✅ Found valid MCP response: {response}\")
                found_json = True
                break
            except (json.JSONDecodeError, AssertionError) as e:
                print(f\"❌ Invalid JSON response: {e}\")
    
    if not found_json:
        print(\"❌ No valid JSON MCP response found\")
        print(\"Full stdout lines:\")
        for i, line in enumerate(stdout.strip().split(\"\n\")):
            print(f\"  {i}: {repr(line)}\")
        
except subprocess.TimeoutExpired:
    process.kill()
    print(\"❌ MCP server timeout - process killed\")
except Exception as e:
    print(f\"❌ Unexpected error: {e}\")
finally:
    if process.poll() is None:
        process.terminate()
"

echo ""
echo "=== Testing Server Creation Programmatically ==="
python -c "
import sys
from rmcp.core.server import create_server
from rmcp.cli import _register_builtin_tools

try:
    server = create_server()
    _register_builtin_tools(server)
    print(f\"✅ Server creation: {len(server.tools._tools)} tools registered\")
except Exception as e:
    print(f\"❌ Server creation failed: {e}\")
    import traceback
    traceback.print_exc()
"

echo ""
echo "🔍 MCP protocol debugging complete"
'