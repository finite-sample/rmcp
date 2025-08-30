#!/bin/bash
# run_tests.sh

# Test linear_model via stdio
echo "Testing linear_model..."
cat <<EOF | rmcp start > response.json
{
  "tool": "linear_model",
  "args": {
    "formula": "y ~ x1",
    "data": {"x1": [1, 2, 3, 4, 5], "y": [1, 3, 5, 7, 9]},
    "robust": false
  }
}
EOF

echo "Response:"
cat response.json
