# Linear Regression Analysis Script for RMCP
# ===========================================
# 
# This script performs comprehensive linear regression analysis using R's lm() function.
# It supports weighted regression, missing value handling, and returns detailed
# model diagnostics including coefficients, significance tests, and goodness-of-fit.

# Prepare data and parameters
data <- as.data.frame(args$data)
formula <- as.formula(args$formula)

# Handle optional parameters
weights <- args$weights
na_action <- args$na_action %||% "na.omit"

# Fit model
if (!is.null(weights)) {
    model <- lm(formula, data = data, weights = weights, na.action = get(na_action))
} else {
    model <- lm(formula, data = data, na.action = get(na_action))
}

# Get comprehensive results
summary_model <- summary(model)

# Generate formatted summary using our formatting functions
formatted_summary <- format_lm_results(model, args$formula)

# Generate natural language interpretation
interpretation <- interpret_lm(model)

result <- list(
    # Schema-compliant fields only (strict validation)
    coefficients = as.list(coef(model)),
    std_errors = as.list(summary_model$coefficients[, "Std. Error"]),
    t_values = as.list(summary_model$coefficients[, "t value"]),
    p_values = as.list(summary_model$coefficients[, "Pr(>|t|)"]),
    r_squared = summary_model$r.squared,
    adj_r_squared = summary_model$adj.r.squared,
    f_statistic = summary_model$fstatistic[1],
    f_p_value = pf(summary_model$fstatistic[1],
                  summary_model$fstatistic[2],
                  summary_model$fstatistic[3], lower.tail = FALSE),
    residual_se = summary_model$sigma,
    df_residual = summary_model$df[2],
    fitted_values = as.numeric(fitted(model)),
    residuals = as.numeric(residuals(model)),
    n_obs = nrow(model$model),
    method = "lm",

    # Special non-validated field for formatting (will be extracted before validation)
    "_formatting" = list(
        summary = formatted_summary,
        interpretation = interpretation
    )
)