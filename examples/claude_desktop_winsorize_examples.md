# Winsorize Tool Examples for Claude Desktop

Now that the winsorize tool schema has been fixed, here are concrete examples you can test in Claude Desktop to verify the functionality:

## Example 1: Basic Winsorization (Sales Data with Outliers)

```
I have sales data with some extreme outliers. Can you winsorize the sales figures at the 5th and 95th percentiles?

Data:
- sales: [120, 135, 128, 142, 500, 148, 160, 175, 168, 180, 165, 172, 185, 178, 192, 1000]
- region: ["North", "South", "East", "West", "North", "South", "East", "West", "North", "South", "East", "West", "North", "South", "East", "West"]

Please use the winsorize tool to handle the outliers (500 and 1000) in the sales data.
```

## Example 2: Conservative Winsorization (Financial Returns)

```
I have monthly stock returns that include some extreme market movements. Please winsorize the returns at the 10th and 90th percentiles to reduce the impact of market crashes and bubbles.

Data:
- returns: [0.02, -0.15, 0.05, 0.08, -0.03, 0.12, -0.45, 0.25, 0.01, -0.08, 0.15, 0.35]
- month: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

Use winsorize with percentiles [0.1, 0.9] to handle the extreme returns.
```

## Example 3: Multiple Variable Winsorization (Research Data)

```
I have experimental data with multiple measurements that may contain outliers. Please winsorize both response_time and accuracy variables at the 5th and 95th percentiles.

Data:
- response_time: [234, 456, 289, 1200, 345, 298, 267, 389, 2000, 298, 334, 287]
- accuracy: [0.95, 0.87, 0.92, 0.45, 0.89, 0.94, 0.91, 0.88, 0.23, 0.93, 0.90, 0.92]
- condition: ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B", "A", "B"]

Use the winsorize tool on both response_time and accuracy variables.
```

## Example 4: Aggressive Winsorization (Quality Control)

```
I have manufacturing quality measurements where I need to be very conservative about outliers. Please winsorize the defect_rate at the 20th and 80th percentiles.

Data:
- defect_rate: [0.02, 0.15, 0.03, 0.08, 0.01, 0.12, 0.45, 0.05, 0.01, 0.08, 0.35, 0.03]
- batch: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

Use winsorize with percentiles [0.2, 0.8] for aggressive outlier treatment.
```

## Expected Results

When you run these examples, you should see:

1. **Outlier Summary**: Number of values capped at lower and upper thresholds
2. **Threshold Values**: The actual percentile values used for capping
3. **Transformed Data**: The dataset with extreme values replaced by threshold values
4. **Formatting**: A markdown table showing the winsorization summary

The fixed schema now properly allows percentiles up to 1.0 (100th percentile), so standard winsorization ranges like [0.05, 0.95] will work correctly.

## Testing the Fix

To verify the schema fix worked, try this example that previously failed:

```
Please winsorize this data at the 5th and 95th percentiles:
- values: [1, 2, 3, 4, 5, 100, 7, 8, 9, 10]

Use percentiles [0.05, 0.95]
```

This should now work without the "0.95 is greater than the maximum of 0.5" error.
