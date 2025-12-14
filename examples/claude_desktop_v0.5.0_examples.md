# Claude Desktop Testing Examples for RMCP v0.5.0

This document provides comprehensive examples to test the Universal Operation Approval System and enhanced functionality in RMCP v0.5.0.

## Setup Requirements

1. **Claude Desktop Configuration**: Add RMCP to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "rmcp": {
      "command": "poetry",
      "args": ["run", "rmcp", "start"],
      "cwd": "/path/to/rmcp"
    }
  }
}
```

2. **Data Setup**: Create test data files for examples:
```csv
# Save as /tmp/sales_data.csv
date,product,sales,region
2024-01-01,Widget A,1200,North
2024-01-02,Widget B,850,South
2024-01-03,Widget A,1100,North
2024-01-04,Widget C,950,East
2024-01-05,Widget B,1300,West
2024-01-06,Widget A,1050,South
2024-01-07,Widget C,1400,North
2024-01-08,Widget B,900,East
2024-01-09,Widget A,1250,West
2024-01-10,Widget C,800,South
```

## Example 1: File Operation Approval Testing

Test the file operations approval system with visualization saving:

**Prompt:**
```
Load the sales data from /tmp/sales_data.csv and create a sales trend visualization. Save the plot as 'sales_trend.png' in /tmp/ directory. This should test the new file operation approval system.
```

**Expected Behavior:**
1. RMCP loads the data successfully
2. Creates visualization with ggplot2
3. **Approval Required**: System prompts for permission to save file via `ggsave()`
4. Upon approval, saves plot to `/tmp/sales_trend.png`
5. Returns base64 encoded image for preview

**Follow-up Test:**
```
Now create another plot showing sales by region and save it as 'sales_by_region.png'. This should use the previously approved file operations permission.
```

Expected: No additional approval needed (session persistence).

## Example 2: Package Installation Approval Testing

Test the package installation approval system:

**Prompt:**
```
I want to use the 'forecast' package for time series analysis. Install it if it's not available, then create a simple forecast of the sales data.
```

**Expected Behavior:**
1. RMCP detects `install.packages("forecast")` in R code
2. **Approval Required**: System prompts for permission to install packages
3. Upon approval, installs the forecast package
4. Proceeds with time series analysis

**Follow-up Test:**
```
Now install the 'plotly' package to create an interactive plot.
```

Expected: Uses previously approved package installation permission.

## Example 3: Decision Tree Analysis with File Output

Test the fixed decision tree functionality:

**Prompt:**
```
Using the sales data, build a decision tree to predict sales based on product and region. Save the results and create a visualization that I can save to file.
```

**Expected Behavior:**
1. Uses the fixed `decision_tree.R` script
2. Returns proper tree structure and variable importance
3. **Approval Required**: For any file saving operations
4. Demonstrates the fixed schema compliance issues

## Example 4: Statistical Analysis Pipeline

Test multiple tools with data transformations:

**Prompt:**
```
Perform a comprehensive analysis of the sales data:
1. Load and describe the data
2. Create lagged variables for time series analysis
3. Standardize the sales values using z-score method
4. Detect outliers and winsorize at 5%-95% percentiles
5. Save all intermediate datasets and final visualization
```

**Expected Behavior:**
1. Executes multiple statistical tools in sequence
2. **Multiple Approvals**: May require approval for file operations at various stages
3. Tests the enhanced tools with fixed knitr::kable formatting
4. Demonstrates session-based approval persistence

## Example 5: System Operations Testing (High Security)

Test high-security operations (use with caution):

**Prompt:**
```
Check the R environment and show me what packages are installed. Also show the current working directory using system commands.
```

**Expected Behavior:**
1. **High Security Approval**: System prompts for system-level operations
2. Clear warning about security implications
3. Upon approval, executes system commands safely
4. Returns environment information

## Example 6: Error Handling and Recovery

Test approval denial and error recovery:

**Prompt:**
```
Create a simple plot and try to save it. When prompted for approval, please deny the file operation.
```

**Expected Behavior:**
1. Creates plot successfully
2. **Approval Denied**: User denies file operation permission
3. Graceful failure with clear error message
4. Plot still available as base64 for viewing
5. No file created on filesystem

## Example 7: Comprehensive Workflow Test

Test a realistic data science workflow:

**Prompt:**
```
I have sales data and want to perform a complete analysis:
1. Load data from /tmp/sales_data.csv
2. Perform exploratory data analysis with summary statistics
3. Create multiple visualizations (scatter plots, box plots, time series)
4. Build predictive models (linear regression, decision tree)
5. Save all outputs (plots, model results, transformed data) to /tmp/analysis_output/
6. Create a summary report of findings

This workflow should test the approval system comprehensively across different operation types.
```

**Expected Behavior:**
1. Sequential execution of multiple analysis steps
2. **Strategic Approvals**: Approval requests at key points (first file save, first package install)
3. Session persistence reduces repetitive approvals
4. Complete analysis pipeline with all outputs saved
5. Demonstrates the 53 available tools working together

## Example 8: Concurrent Operations Testing

Test approval system under concurrent requests:

**Prompt:**
```
Create three different visualizations in parallel:
1. Sales trend over time
2. Sales distribution by product
3. Regional performance comparison
Save each to separate files with descriptive names.
```

**Expected Behavior:**
1. Handles multiple concurrent operations
2. Approval system works correctly with concurrent requests
3. All files saved successfully after approval
4. No conflicts or race conditions

## Testing Checklist

After running these examples, verify:

- [ ] **Approval Prompts**: Clear, informative prompts for each operation type
- [ ] **Session Persistence**: Approved operations don't require re-approval in same session
- [ ] **Security Boundaries**: High-security operations have appropriate warnings
- [ ] **Graceful Failures**: Denied operations fail safely with clear messages
- [ ] **File Integration**: VFS permissions work correctly with approval system
- [ ] **Performance**: No significant slowdown from approval checking
- [ ] **Schema Compliance**: All R tools return properly formatted JSON
- [ ] **Error Recovery**: System recovers gracefully from approval denials

## Expected Output Locations

After running these examples with approvals, you should find:

```
/tmp/
├── sales_data.csv                    (input data)
├── sales_trend.png                   (Example 1)
├── sales_by_region.png              (Example 1 follow-up)
├── analysis_output/                  (Example 7)
│   ├── exploratory_plots/
│   ├── model_results/
│   └── transformed_data/
└── [various other output files]
```

## Troubleshooting

**Common Issues:**

1. **Permission Denied**: Ensure `/tmp/` has write permissions
2. **Approval Not Triggered**: Check that operation patterns match R code
3. **File Not Found**: Verify data file exists and path is correct
4. **Package Errors**: Some packages may require system dependencies

**Debug Commands:**
```bash
# Check RMCP status
uv run rmcp --debug start

# Verify file permissions
ls -la /tmp/

# Check R environment in Docker
docker run -v $(pwd):/workspace rmcp-dev R --version
```

These examples comprehensively test the Universal Operation Approval System and demonstrate the enhanced security and usability features in RMCP v0.5.0.
