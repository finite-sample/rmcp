# test_rmcp.py
import pytest

# Import the functions you want to test from rmcp.py.
# Adjust the import statement if your module is in a package or different directory.
from rmcp import linear_model, diagnostics, iv_regression, panel_model, panel_data_analysis_prompt

def test_linear_model():
    # Create a simple dataset where y = 2*x1 - 1
    data = {"x1": [1, 2, 3, 4, 5], "y": [1, 3, 5, 7, 9]}
    formula = "y ~ x1"
    
    # Run the linear model with robust = False for this test.
    result = linear_model(formula=formula, data=data, robust=False)
    
    # Check that the result includes expected keys and approximate values.
    assert "coefficients" in result, "Result must contain coefficients."
    coeffs = result["coefficients"]
    assert "(Intercept)" in coeffs and "x1" in coeffs, "Expected (Intercept) and x1 in coefficients."
    
    # Expect roughly an intercept near -1 and slope near 2 (allowing tolerance for floating point calculations).
    assert abs(coeffs["(Intercept)"] + 1) < 0.5, f"Unexpected intercept {coeffs['(Intercept)']}"
    assert abs(coeffs["x1"] - 2) < 0.5, f"Unexpected slope {coeffs['x1']}"

def test_diagnostics():
    data = {"x1": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]}
    formula = "y ~ x1"
    
    # Run a couple of diagnostic tests.
    result = diagnostics(formula=formula, data=data, tests=["bp", "reset"])
    
    # Make sure the expected diagnostic keys are present.
    assert "bp" in result, "Breusch-Pagan test result missing."
    assert "reset" in result, "RESET test result missing."

def test_iv_regression():
    # Provide a basic dummy dataset and formula for instrumental variables regression.
    data = {
        "x1": [1, 2, 3, 4, 5],
        "y": [1, 2, 3, 4, 5],
        "z1": [1, 2, 3, 4, 5]  # Instrument variable; in a real case, this needs to be exogenous.
    }
    formula = "y ~ x1 | z1"
    result = iv_regression(formula=formula, data=data)
    
    # Ensure the result contains coefficients.
    assert "coefficients" in result, "Coefficients missing in IV regression result."

def test_panel_model():
    # Create a dummy panel dataset.
    data = {
        "id": [1, 1, 2, 2],
        "time": [1, 2, 1, 2],
        "y": [1, 3, 2, 4],
        "x1": [1, 1, 2, 2]
    }
    formula = "y ~ x1"
    index = ["id", "time"]
    
    result = panel_model(formula=formula, data=data, index=index, effect="individual", model="within")
    assert "coefficients" in result, "Panel model result should include coefficients."

def test_panel_data_analysis_prompt():
    # Check that the prompt generating function returns valid messages.
    messages = panel_data_analysis_prompt("sample_dataset", "y", "x1,x2")
    assert isinstance(messages, list), "Prompt should be returned as a list of messages."
    for msg in messages:
        assert "role" in msg and "content" in msg, "Each prompt message should have both 'role' and 'content'."

if __name__ == "__main__":
    pytest.main()
