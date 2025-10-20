# Instrumental Variables (2SLS) Regression Script for RMCP
# =========================================================
#
# This script performs two-stage least squares (2SLS) instrumental variables
# regression with diagnostic tests for weak instruments and endogeneity.

# Load required libraries
library(AER)
library(lmtest)
library(knitr)
library(broom)

# Prepare data and parameters
formula_str <- args$formula
robust <- args$robust %||% TRUE

# Parse IV formula (y ~ x1 + x2 | z1 + z2)
formula <- as.formula(formula_str)

# Fit 2SLS model
iv_model <- ivreg(formula, data = data)

# Get robust standard errors if requested
if (robust) {
  robust_se <- coeftest(iv_model, vcov = sandwich)
  coef_table <- robust_se
} else {
  coef_table <- summary(iv_model)$coefficients
}
# Diagnostic tests
summary_iv <- summary(iv_model, diagnostics = TRUE)
# Extract coefficients with proper names
coef_vals <- coef_table[, "Estimate"]
names(coef_vals) <- rownames(coef_table)
std_err_vals <- coef_table[, "Std. Error"]
names(std_err_vals) <- rownames(coef_table)
t_vals <- coef_table[, "t value"]
names(t_vals) <- rownames(coef_table)
p_vals <- coef_table[, "Pr(>|t|)"]
names(p_vals) <- rownames(coef_table)
result <- list(
  coefficients = as.list(coef_vals),
  std_errors = as.list(std_err_vals),
  t_values = as.list(t_vals),
  p_values = as.list(p_vals),
  r_squared = summary_iv$r.squared,
  adj_r_squared = summary_iv$adj.r.squared,
  weak_instruments = {
    wi_stat <- if (is.na(summary_iv$diagnostics["Weak instruments", "statistic"])) NULL else summary_iv$diagnostics["Weak instruments", "statistic"]
    wi_p <- if (is.na(summary_iv$diagnostics["Weak instruments", "p-value"])) NULL else summary_iv$diagnostics["Weak instruments", "p-value"]
    if (is.null(wi_stat) && is.null(wi_p)) NULL else list(statistic = wi_stat, p_value = wi_p)
  },
  wu_hausman = {
    wh_stat <- if (is.na(summary_iv$diagnostics["Wu-Hausman", "statistic"])) NULL else summary_iv$diagnostics["Wu-Hausman", "statistic"]
    wh_p <- if (is.na(summary_iv$diagnostics["Wu-Hausman", "p-value"])) NULL else summary_iv$diagnostics["Wu-Hausman", "p-value"]
    if (is.null(wh_stat) && is.null(wh_p)) NULL else list(statistic = wh_stat, p_value = wh_p)
  },
  sargan = {
    s_stat <- if (is.na(summary_iv$diagnostics["Sargan", "statistic"])) NULL else summary_iv$diagnostics["Sargan", "statistic"]
    s_p <- if (is.na(summary_iv$diagnostics["Sargan", "p-value"])) NULL else summary_iv$diagnostics["Sargan", "p-value"]
    if (is.null(s_stat) && is.null(s_p)) NULL else list(statistic = s_stat, p_value = s_p)
  },
  robust_se = robust,
  formula = formula_str,
  n_obs = nobs(iv_model),
  # Special non-validated field for formatting
  "_formatting" = list(
    summary = tryCatch(
      {
        # Try to tidy the IV model
        tidy_model <- broom::tidy(iv_model)
        paste(as.character(knitr::kable(
          tidy_model,
          format = "markdown", digits = 4
        )), collapse = "\n")
      },
      error = function(e) {
        # Fallback: create summary table
        iv_summary <- data.frame(
          Model = "2SLS",
          R_Squared = round(summary_iv$r.squared, 4),
          Observations = nobs(iv_model),
          Robust_SE = robust
        )
        paste(as.character(knitr::kable(
          iv_summary,
          format = "markdown", digits = 4
        )), collapse = "\n")
      }
    ),
    interpretation = paste0(
      "Instrumental variables (2SLS) regression with ",
      nobs(iv_model), " observations."
    )
  )
)
