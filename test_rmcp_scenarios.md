# RMCP Test Scenarios - Real Data Analysis

## 🚀 Quick Start Commands

### 1. Start RMCP Server
```bash
rmcp start
```

### 2. Test with MCP Protocol
Send JSON-RPC requests to test functionality:

## 📊 Test Scenario 1: Sales Performance Analysis

**Objective**: Analyze relationship between marketing spend and sales

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "read_csv",
    "arguments": {
      "file_path": "test_sales_data.csv"
    }
  }
}
```

Then analyze with regression:
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "linear_model",
    "arguments": {
      "data": {
        "month": ["2023-01", "2023-02", "2023-03", "2023-04", "2023-05", "2023-06", "2023-07", "2023-08", "2023-09", "2023-10", "2023-11", "2023-12"],
        "sales": [50000, 52000, 48000, 55000, 58000, 60000, 62000, 59000, 61000, 64000, 67000, 70000],
        "marketing_spend": [5000, 5200, 4800, 5500, 5800, 6000, 6200, 5900, 6100, 6400, 6700, 7000],
        "customer_satisfaction": [4.2, 4.3, 4.1, 4.4, 4.5, 4.6, 4.7, 4.5, 4.6, 4.8, 4.9, 5.0]
      },
      "formula": "sales ~ marketing_spend + customer_satisfaction"
    }
  }
}
```

## 📈 Test Scenario 2: Customer Churn Prediction

**Objective**: Predict customer churn using logistic regression

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "read_json",
    "arguments": {
      "file_path": "test_customer_data.json"
    }
  }
}
```

Then build churn model:
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "logistic_regression",
    "arguments": {
      "data": {
        "customer_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        "age": [25, 34, 28, 45, 31, 38, 42, 29, 35, 41, 27, 33, 39, 26, 44, 32, 37, 30, 43, 36],
        "income": [45000, 67000, 52000, 85000, 58000, 72000, 78000, 49000, 63000, 81000, 47000, 59000, 74000, 46000, 83000, 55000, 69000, 51000, 79000, 65000],
        "purchase_frequency": [2, 5, 3, 8, 4, 6, 7, 3, 5, 9, 2, 4, 6, 2, 8, 4, 6, 3, 7, 5],
        "satisfaction": [3.5, 4.2, 3.8, 4.8, 4.0, 4.5, 4.6, 3.7, 4.3, 4.9, 3.4, 4.1, 4.4, 3.6, 4.7, 3.9, 4.4, 3.8, 4.5, 4.2],
        "churn": [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0]
      },
      "formula": "churn ~ age + income + purchase_frequency + satisfaction"
    }
  }
}
```

## 🎯 Test Scenario 3: Correlation Analysis

**Objective**: Find relationships between customer variables

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "correlation_analysis",
    "arguments": {
      "data": {
        "age": [25, 34, 28, 45, 31, 38, 42, 29, 35, 41, 27, 33, 39, 26, 44, 32, 37, 30, 43, 36],
        "income": [45000, 67000, 52000, 85000, 58000, 72000, 78000, 49000, 63000, 81000, 47000, 59000, 74000, 46000, 83000, 55000, 69000, 51000, 79000, 65000],
        "purchase_frequency": [2, 5, 3, 8, 4, 6, 7, 3, 5, 9, 2, 4, 6, 2, 8, 4, 6, 3, 7, 5],
        "satisfaction": [3.5, 4.2, 3.8, 4.8, 4.0, 4.5, 4.6, 3.7, 4.3, 4.9, 3.4, 4.1, 4.4, 3.6, 4.7, 3.9, 4.4, 3.8, 4.5, 4.2]
      },
      "variables": ["age", "income", "purchase_frequency", "satisfaction"]
    }
  }
}
```

## 📊 Test Scenario 4: Create Visualization

**Objective**: Generate scatter plot with correlation

```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "tools/call",
  "params": {
    "name": "scatter_plot",
    "arguments": {
      "data": {
        "income": [45000, 67000, 52000, 85000, 58000, 72000, 78000, 49000, 63000, 81000, 47000, 59000, 74000, 46000, 83000, 55000, 69000, 51000, 79000, 65000],
        "satisfaction": [3.5, 4.2, 3.8, 4.8, 4.0, 4.5, 4.6, 3.7, 4.3, 4.9, 3.4, 4.1, 4.4, 3.6, 4.7, 3.9, 4.4, 3.8, 4.5, 4.2]
      },
      "x": "income",
      "y": "satisfaction",
      "title": "Income vs Customer Satisfaction"
    }
  }
}
```

## 🤖 Test Scenario 5: Natural Language Features

**Objective**: Use helper tools for better UX

Get example data:
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "load_example",
    "arguments": {
      "dataset_type": "business"
    }
  }
}
```

Build formula from natural language:
```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "method": "tools/call",
  "params": {
    "name": "build_formula",
    "arguments": {
      "description": "predict customer satisfaction from age income and purchase frequency"
    }
  }
}
```

## 🧪 Test Using Command Line

You can test directly via command line:

```bash
# Test basic functionality
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | rmcp start

# Test a specific tool
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"load_example","arguments":{"dataset_type":"business"}}}' | rmcp start
```

## 📋 Expected Results

1. **Sales Analysis**: Should show strong positive correlation between marketing spend and sales
2. **Churn Prediction**: Logistic model should identify satisfaction as key predictor
3. **Correlations**: Should reveal relationships between customer variables
4. **Visualization**: Scatter plot should display as base64-encoded image
5. **Natural Language**: Should provide helpful suggestions and example data

## 🎯 Success Criteria

- All JSON responses should be valid
- No R script execution errors
- Formatted output with markdown tables
- Images display correctly (base64 encoded)
- Statistical results are meaningful