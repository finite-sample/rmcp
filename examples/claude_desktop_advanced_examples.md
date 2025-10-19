# Advanced Claude Desktop Examples with RMCP

This guide provides concrete examples you can type directly into Claude Desktop to showcase RMCP's advanced statistical capabilities enabled by the comprehensive 429-package ecosystem.

## Prerequisites

Make sure RMCP is configured in your Claude Desktop:

```json
{
  "mcpServers": {
    "rmcp": {
      "command": "rmcp",
      "args": ["start"]
    }
  }
}
```

## 🧠 Machine Learning Examples

### K-means Customer Segmentation

```
I have customer data with variables: annual_spending, visit_frequency, avg_order_value, customer_age. Can you perform k-means clustering to segment customers into 3 groups and tell me what each segment represents?

Use this sample data:
annual_spending,visit_frequency,avg_order_value,customer_age
2400,24,100,28
4800,48,200,45
1200,12,50,22
3600,36,150,38
6000,60,300,52
1800,18,75,25
5400,54,250,48
2100,21,85,32
3900,39,175,41
4500,45,225,44
```

**Expected Output**: Cluster assignments, centroids for each segment (e.g., "Budget Shoppers", "Premium Customers", "Occasional Buyers"), and business insights for targeting each segment.

### Random Forest for House Price Prediction

```
I want to predict house prices using a random forest model. I have these variables: bedrooms, bathrooms, sqft, age, garage_spaces, lot_size. Build a model and tell me which features are most important for pricing.

Sample data:
bedrooms,bathrooms,sqft,age,garage_spaces,lot_size,price
3,2,1800,15,2,0.25,320000
4,3,2400,8,2,0.35,450000
2,1,1200,25,1,0.15,250000
5,4,3200,5,3,0.5,650000
3,2.5,2000,12,2,0.3,380000
4,2,2200,20,2,0.4,420000
6,5,4000,3,3,0.75,850000
```

**Expected Output**: Variable importance rankings, out-of-bag error rate, prediction accuracy, and practical insights about what drives home values.

### Decision Tree for Loan Approval

```
Create an interpretable decision tree model to predict loan approval (approved/denied) based on: credit_score, income, debt_ratio, employment_years, loan_amount. I want to understand the decision rules.

Data:
credit_score,income,debt_ratio,employment_years,loan_amount,approved
720,65000,0.3,5,200000,approved
580,35000,0.8,2,150000,denied
750,85000,0.2,8,300000,approved
620,45000,0.6,3,180000,denied
680,55000,0.4,6,220000,approved
540,25000,0.9,1,100000,denied
780,95000,0.1,10,350000,approved
```

**Expected Output**: Decision tree rules in plain English (e.g., "If credit_score > 650 AND debt_ratio < 0.5, then approve"), accuracy metrics, and variable importance.

## 📈 Advanced Econometrics Examples

### Panel Data Regression

```
I have panel data for 5 states over 4 years studying the effect of minimum wage on employment. Run a fixed effects panel regression to estimate the causal impact.

Variables: state_id, year, min_wage, employment_rate, gdp_growth, population

Data:
state_id,year,min_wage,employment_rate,gdp_growth,population
1,2020,7.25,92.5,2.1,5000000
1,2021,8.00,91.8,1.8,5050000
1,2022,8.50,91.2,2.4,5100000
1,2023,9.00,90.9,3.1,5150000
2,2020,8.50,93.2,2.8,3000000
2,2021,9.25,92.7,2.2,3030000
2,2022,10.00,92.1,2.9,3060000
2,2023,10.75,91.6,3.4,3090000
```

**Expected Output**: Fixed effects coefficients, statistical significance, interpretation of minimum wage impact on employment, R-squared values.

### Vector Autoregression (VAR) Model

```
Build a VAR model to analyze the dynamic relationships between GDP growth, inflation, and unemployment using quarterly data. I want to understand how shocks in one variable affect the others.

Data:
quarter,gdp_growth,inflation,unemployment
2020Q1,2.1,1.8,3.5
2020Q2,-9.5,0.1,14.7
2020Q3,33.4,1.2,8.4
2020Q4,4.3,1.4,6.7
2021Q1,6.3,2.6,6.0
2021Q2,6.7,5.4,5.9
2021Q3,2.3,5.3,4.8
2021Q4,6.9,6.8,3.9
2022Q1,-1.6,8.5,3.6
2022Q2,-0.6,9.1,3.6
```

**Expected Output**: VAR coefficients for each equation, impulse response functions, variance decomposition, and economic interpretation of dynamic relationships.

### Instrumental Variables Regression

```
Estimate the causal effect of education on wages using distance to college as an instrument. I suspect education is endogenous due to ability bias.

Formula: "wage ~ education + experience + age | distance_to_college + experience + age"

Data:
wage,education,experience,age,distance_to_college
45000,12,5,27,25
65000,16,8,32,5
35000,10,3,23,45
85000,18,12,38,2
50000,14,6,30,15
75000,16,10,34,8
40000,11,4,25,35
95000,20,15,43,3
```

**Expected Output**: 2SLS estimates, first-stage statistics, weak instruments test, Wu-Hausman endogeneity test, and interpretation of causal education premium.

## ⏰ Time Series Forecasting Examples

### ARIMA Forecasting

```
I have monthly sales data and need to forecast the next 6 months. Build an ARIMA model and provide confidence intervals for the predictions.

Data (monthly sales in thousands):
month,sales
2023-01,145
2023-02,158
2023-03,162
2023-04,148
2023-05,171
2023-06,185
2023-07,178
2023-08,192
2023-09,186
2023-10,201
2023-11,198
2023-12,215
2024-01,156
2024-02,169
2024-03,174
```

**Expected Output**: ARIMA model selection (p,d,q), forecast values with 95% confidence intervals, model diagnostics, and business interpretation.

### Time Series Decomposition

```
Decompose my quarterly revenue data into trend, seasonal, and irregular components. I want to understand the underlying patterns.

Data:
quarter,revenue
2020Q1,2400000
2020Q2,1800000
2020Q3,2100000
2020Q4,3200000
2021Q1,2600000
2021Q2,2000000
2021Q3,2300000
2021Q4,3500000
2022Q1,2800000
2022Q2,2200000
2022Q3,2500000
2022Q4,3800000
```

**Expected Output**: Trend analysis, seasonal patterns, irregular fluctuations, and strategic insights for business planning.

## 📊 Advanced Statistical Testing

### ANOVA with Multiple Comparisons

```
I conducted an experiment testing 4 different marketing strategies on sales performance. Run ANOVA to test for differences and identify which strategies are significantly different.

Data:
strategy,sales
A,1200
A,1180
A,1220
A,1195
A,1210
B,1350
B,1380
B,1340
B,1365
B,1375
C,1180
C,1165
C,1175
C,1170
C,1185
D,1420
D,1445
D,1430
D,1438
D,1452
```

**Expected Output**: ANOVA F-statistic and p-value, post-hoc pairwise comparisons, effect sizes, and practical recommendations for marketing strategy.

### Chi-Square Test of Independence

```
Test whether customer satisfaction is independent of product category using this survey data.

Data:
category,satisfaction
Electronics,Satisfied
Electronics,Very Satisfied
Electronics,Neutral
Clothing,Satisfied
Clothing,Dissatisfied
Clothing,Very Satisfied
Home,Very Satisfied
Home,Satisfied
Home,Satisfied
Electronics,Very Satisfied
Clothing,Neutral
Home,Very Satisfied
```

**Expected Output**: Chi-square statistic, p-value, degrees of freedom, Cramér's V effect size, and interpretation of association between variables.

## 🔧 Data Transformation Examples

### Standardization and Outlier Treatment

```
Standardize my financial variables and apply winsorization to handle extreme outliers before modeling.

Variables to process: revenue, profit_margin, debt_ratio, roa

Data:
revenue,profit_margin,debt_ratio,roa
1000000,0.15,0.3,0.08
15000000,0.22,0.4,0.12
500000,0.08,0.8,0.02
8000000,0.18,0.2,0.15
2000000,0.12,0.6,0.05
50000000,0.35,0.1,0.25
800000,0.05,0.9,0.01
```

**Expected Output**: Standardized variables (mean=0, sd=1), outlier detection report, winsorized values, and recommendations for modeling.

## 🎯 Business Intelligence Scenarios

### Customer Lifetime Value Analysis

```
Calculate CLV using these metrics and segment customers by value tiers. Use clustering to identify distinct customer profiles.

Variables: annual_spend, tenure_months, purchase_frequency, avg_order_value, support_tickets

Data:
customer_id,annual_spend,tenure_months,purchase_frequency,avg_order_value,support_tickets
C001,2400,18,24,100,2
C002,6000,36,60,100,1
C003,1200,6,12,100,5
C004,4800,24,24,200,3
C005,9600,48,48,200,0
C006,800,12,8,100,8
C007,7200,30,36,200,2
```

**Expected Output**: CLV calculations, customer segments (e.g., "High Value", "Growing", "At Risk"), retention strategies, and revenue optimization recommendations.

### Market Basket Analysis

```
Analyze purchase patterns to identify product associations and cross-selling opportunities.

Transaction data:
transaction_id,products
T001,"bread,milk,eggs"
T002,"bread,butter,jam"
T003,"milk,eggs,cheese"
T004,"bread,milk,butter"
T005,"eggs,cheese,yogurt"
T006,"bread,jam,honey"
T007,"milk,cheese,yogurt"
```

**Expected Output**: Association rules (e.g., "If customers buy bread, they're 65% likely to buy milk"), confidence and lift metrics, cross-selling recommendations.

## 💡 Getting Started Tips

1. **Copy-paste any example above** directly into Claude Desktop
2. **Modify the data** to match your real datasets
3. **Ask follow-up questions** like "What if I add more variables?" or "How would this change with more data?"
4. **Request visualizations** by saying "Can you also create plots to show these results?"
5. **Ask for interpretations** with "What do these results mean for my business?"

## 🔍 Advanced Features to Explore

- **Model Validation**: "Split this into training/test sets and validate the model"
- **Feature Engineering**: "Create interaction terms and polynomial features"
- **Ensemble Methods**: "Compare random forest with gradient boosting"
- **Bayesian Analysis**: "Run this as a Bayesian regression with priors"
- **Survival Analysis**: "Analyze time-to-event data for customer churn"
- **Panel Data**: "Control for unobserved heterogeneity with fixed effects"

## 🎯 Pro Tips

- Start with simple examples and build complexity
- Always ask for business interpretation, not just statistical output
- Request confidence intervals and effect sizes for practical significance
- Ask follow-up questions to deepen understanding
- Combine multiple analyses for comprehensive insights

These examples showcase RMCP's comprehensive 429-package ecosystem, demonstrating capabilities far beyond basic statistics through the systematic CRAN task view organization and evidence-based package selection.