#!/bin/bash
# Test all RMCP tools

echo "=== RMCP Tool Testing Suite ==="
echo

echo "1. Testing linear_model..."
cat <<EOF | rmcp start
{"tool": "linear_model", "args": {"formula": "y ~ x1", "data": {"x1": [1,2,3,4,5], "y": [1,3,5,7,9]}, "robust": false}}
EOF
echo

echo "2. Testing correlation..."
cat <<EOF | rmcp start
{"tool": "correlation", "args": {"data": {"x": [1,2,3,4,5], "y": [2,4,6,8,10]}, "var1": "x", "var2": "y", "method": "pearson"}}
EOF
echo

echo "3. Testing group_by..."
cat <<EOF | rmcp start
{"tool": "group_by", "args": {"data": {"group": ["A","A","B","B"], "value": [1,2,3,4]}, "group_col": "group", "summarise_col": "value", "stat": "mean"}}
EOF
echo

echo "4. Testing available tools..."
python -c "from rmcp.tools import mcp; print('Available tools:', list(mcp.tools.keys()))"

echo "=== All tests completed ==="