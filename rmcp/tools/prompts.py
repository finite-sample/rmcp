# rmcp/tools/prompts.py
from typing import List, Dict, Any

def panel_data_analysis_prompt(dataset_name: str, dependent_var: str, independent_vars: str) -> List[Dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": {
                "type": "text",
                "text": "You are an econometrics assistant helping a researcher with panel data analysis."
            }
        },
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"I'm analyzing panel data in the dataset '{dataset_name}'. I want to examine the relationship between my dependent variable {dependent_var} and independent variables {independent_vars}. Please help me:\n1. Run both fixed effects and random effects models\n2. Determine which model is more appropriate using the Hausman test\n3. Interpret the coefficients\n4. Check for heteroskedasticity and autocorrelation\n5. Suggest any necessary corrections to the model"
            }
        }
    ]

def time_series_analysis_prompt(dataset_name: str, time_var: str, dependent_var: str) -> List[Dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": {
                "type": "text",
                "text": "You are an econometrics assistant helping a researcher with time series analysis."
            }
        },
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"I'm analyzing time series data in the dataset '{dataset_name}' with time variable {time_var} and I'm interested in {dependent_var}. Please help me:\n1. Check for stationarity using unit root tests\n2. Transform the data if necessary (differencing, logging)\n3. Identify the appropriate ARIMA model\n4. Estimate the model and interpret results\n5. Perform diagnostic checks\n6. Create forecasts if appropriate"
            }
        }
    ]
