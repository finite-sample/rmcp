import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from rmcp.tools import analyze_csv

def test_analyze_csv():
    # Assume you have a sample CSV file at tests/sample.csv.
    # Create a simple CSV file for testing if not already present.
    test_csv = "tests/sample.csv"
    with open(test_csv, "w") as f:
        f.write("col1,col2\n1,10\n2,20\n3,30\n")
    
    result = analyze_csv(file_path=test_csv)
    print("CSV Analysis result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_analyze_csv()
