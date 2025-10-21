# RMCP Claude Web Connector Specification

**Connector Name**: RMCP Statistical Analysis  
**Identifier**: `rmcp-statistics`  
**Version**: 0.5.1  
**Protocol**: Model Context Protocol (MCP)  
**Server URL**: https://rmcp-server-394229601724.us-central1.run.app/mcp

## Overview

RMCP provides professional statistical analysis capabilities to Claude web through 44 statistical tools powered by R. This connector enables users to perform comprehensive data analysis, regression modeling, time series forecasting, and machine learning directly within Claude conversations.

## Claude API Configuration

### Required Headers
```
anthropic-beta: mcp-client-2025-04-04
```

### MCP Server Configuration
```json
{
  "type": "url",
  "url": "https://rmcp-server-394229601724.us-central1.run.app/mcp",
  "name": "rmcp-statistics",
  "tool_configuration": {
    "enabled": true,
    "allowed_tools": [
      "linear_model",
      "correlation_analysis",
      "arima_model",
      "build_formula",
      "chi_square_test",
      "anova"
    ]
  }
}
```

## Authentication

**Current Implementation**: No authentication required (public access)  
**Security**: Request origin validation and rate limiting applied  
**Future**: OAuth 2.0 support planned for enterprise deployments

## Available Tools

### Core Statistical Analysis (6 primary tools)

#### 1. linear_model
**Purpose**: Linear and logistic regression with comprehensive diagnostics  
**Input Example**:
```json
{
  "formula": "sales ~ marketing_spend + customer_satisfaction",
  "data": {
    "sales": [15000, 18000, 12000, 22000, 16000],
    "marketing_spend": [2000, 2500, 1500, 3000, 2200],
    "customer_satisfaction": [8.5, 8.8, 7.2, 9.1, 8.0]
  },
  "family": "gaussian"
}
```

**Output**: Model statistics (R², F-statistic), coefficients with p-values, confidence intervals, residual diagnostics

#### 2. correlation_analysis
**Purpose**: Correlation matrices with significance testing  
**Input Example**:
```json
{
  "data": {
    "revenue": [25000, 30000, 22000, 35000],
    "advertising": [3000, 4000, 2500, 5000],
    "satisfaction": [8.2, 8.8, 7.5, 9.1]
  },
  "method": "pearson"
}
```

**Output**: Correlation matrix, p-values, confidence intervals

#### 3. arima_model
**Purpose**: Time series modeling and forecasting  
**Input Example**:
```json
{
  "data": [100, 105, 110, 108, 115, 120, 125, 130],
  "variable_name": "monthly_sales",
  "forecast_periods": 3
}
```

**Output**: ARIMA model summary, forecasts with confidence intervals

#### 4. build_formula
**Purpose**: Convert natural language to R statistical formulas  
**Input Example**:
```json
{
  "description": "predict customer satisfaction from service quality and response time"
}
```

**Output**: R formula syntax with alternatives and validation

#### 5. chi_square_test
**Purpose**: Chi-square tests for independence and goodness-of-fit  
**Input Example**:
```json
{
  "data": {
    "satisfied": [45, 30, 25],
    "neutral": [20, 25, 15],
    "dissatisfied": [10, 15, 20]
  },
  "test_type": "independence"
}
```

**Output**: Chi-square statistic, p-value, degrees of freedom

#### 6. anova
**Purpose**: Analysis of variance for group comparisons  
**Input Example**:
```json
{
  "data": {
    "treatment_a": [85, 87, 89, 91, 88],
    "treatment_b": [78, 82, 80, 84, 81],
    "control": [75, 77, 76, 74, 78]
  },
  "test_type": "one_way"
}
```

**Output**: ANOVA table, F-statistic, p-values, post-hoc comparisons

## Claude Integration Examples

### Business Analytics Prompt
```
"I have sales data and want to understand the relationship with marketing spend. 
Sales: [15000, 18000, 12000, 22000, 16000]
Marketing: [2000, 2500, 1500, 3000, 2200]
Customer ratings: [8.5, 8.8, 7.2, 9.1, 8.0]

Can you analyze this data and tell me the ROI?"
```

**Expected Claude Workflow**:
1. Use `linear_model` tool for regression analysis
2. Use `correlation_analysis` for relationship strength
3. Interpret results in business context
4. Provide actionable insights

### Time Series Forecasting Prompt
```
"Here's my monthly sales data: [100, 105, 110, 108, 115, 120, 125, 130]
Can you forecast the next 3 months?"
```

**Expected Claude Workflow**:
1. Use `arima_model` tool with forecast_periods: 3
2. Interpret forecasted values and confidence intervals
3. Provide business recommendations

## Response Format

### Structured Output
All tools return dual-format responses:

1. **Human-readable markdown** (for Claude to interpret)
2. **Structured JSON data** (for programmatic access)

Example response structure:
```json
{
  "content": [
    {
      "type": "text",
      "text": "## Linear Regression Results\n\n**Model Statistics:**\n- R² = 0.995...",
      "annotations": {"mimeType": "text/markdown"}
    }
  ],
  "structuredContent": {
    "type": "json",
    "json": {
      "r_squared": 0.995,
      "coefficients": {...},
      "p_values": {...}
    }
  }
}
```

## Performance Characteristics

- **Session Initialization**: ~200ms
- **Simple Analysis** (correlation): ~1.5s
- **Complex Analysis** (regression): ~3s
- **Time Series Models**: ~5s
- **Concurrent Sessions**: 100 supported
- **Max Data Points**: 10,000 observations

## Error Handling

### Common Error Responses
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Session not initialized. Send initialize request first.",
    "data": {"type": "HTTPException"}
  }
}
```

### Error Recovery
- Automatic session retry for expired sessions
- Input validation with helpful error messages
- Graceful degradation for large datasets

## Use Cases

### 1. Business Intelligence
- Sales performance analysis
- Marketing ROI measurement
- Customer satisfaction modeling
- Revenue forecasting

### 2. Academic Research
- Hypothesis testing
- Experimental design analysis
- Publication-ready statistical reporting
- Data exploration and visualization

### 3. Data Science Workflows
- Feature correlation analysis
- Predictive modeling
- Time series analysis
- Statistical validation

## Competitive Advantages

1. **Professional R Backend**: Unlike basic analytics, provides publication-quality statistical analysis
2. **Comprehensive Tool Set**: 44 tools across 11 statistical categories
3. **Natural Language Integration**: `build_formula` tool converts plain English to statistical formulas
4. **Dual Output Format**: Both human-readable and machine-readable results
5. **Real-time Analysis**: Fast response times for interactive analysis
6. **Industry Standard**: Uses established R packages and methodologies

## Technical Requirements Met

✅ **HTTPS Endpoint**: Google Cloud Run deployment with SSL  
✅ **MCP Protocol Compliance**: Full JSON-RPC 2.0 implementation  
✅ **Session Management**: Proper header-based session tracking  
✅ **Tool Discovery**: `tools/list` endpoint with comprehensive metadata  
✅ **Error Handling**: Standard JSON-RPC error responses  
✅ **Performance**: Sub-5s response times for complex analysis  
✅ **Scalability**: Cloud-native deployment with auto-scaling  

## Connector Validation

### Tested Scenarios
- ✅ Session initialization and management
- ✅ Linear regression with business data
- ✅ Correlation analysis with multiple variables
- ✅ Error handling and recovery
- ✅ Concurrent user sessions
- ✅ Large dataset processing (1000+ observations)

### Integration Testing
```bash
# Test MCP protocol compliance
curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \
  -H "Content-Type: application/json" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize",...}'

# Verify tools/list endpoint
curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \
  -H "MCP-Session-Id: <session>" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

## Documentation Resources

- **Interactive API Docs**: https://rmcp-server-394229601724.us-central1.run.app/docs
- **Landing Page**: https://rmcp-server-394229601724.us-central1.run.app/
- **GitHub Repository**: https://github.com/finite-sample/rmcp
- **Complete Tool Reference**: https://finite-sample.github.io/rmcp/

## Deployment Information

- **Infrastructure**: Google Cloud Run (serverless)
- **Availability**: 99.9% uptime SLA
- **Scaling**: Automatic based on demand
- **Monitoring**: Health checks and metrics available
- **Backup**: Stateless design, no data persistence required

## Future Enhancements

1. **OAuth 2.0 Authentication**: Enterprise-grade security
2. **Additional R Packages**: Extend statistical capabilities
3. **Visualization Tools**: Enhanced plotting and charting
4. **Data Import**: Direct CSV/Excel file processing
5. **Custom Models**: User-defined statistical models

---

**Ready for Integration**: This connector is production-ready and can be immediately integrated with Claude web using the MCP configuration above.