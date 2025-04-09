import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from rmcp.tools import linear_model, diagnostics, iv_regression, panel_model, panel_data_analysis_prompt, correlation, group_by

# Test Group-By Functionality
def test_group_by():
    # Create a simple dataset with groups.
    # For example, group "A" and "B" with associated numeric values.
    data = {
        "group": ["A", "A", "B", "B", "A", "B"],
        "value": [10, 20, 30, 40, 15, 35]
    }
    # We want to group by the 'group' column and compute the mean of the 'value' column.
    result = group_by(data=data, group_col="group", summarise_col="value", stat="mean")
    print("Group-by result:")
    print(json.dumps(result, indent=2))

# Test Correlation Functionality
def test_correlation():
    # Create a simple dataset for correlation.
    data = {
        "x": [1, 2, 3, 4, 5],
        "y": [2, 4, 5, 8, 10]  # should show a high positive correlation with x
    }
    # Compute Pearson correlation.
    result = correlation(data=data, var1="x", var2="y", method="pearson")
    print("Correlation result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    print("=== Testing Group-By Tool ===")
    test_group_by()
    print("\n=== Testing Correlation Tool ===")
    test_correlation()
