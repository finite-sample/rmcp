# Integration test: Complete regression workflow
# Fit model, check assumptions, generate diagnostics

# Fit linear model
model <- lm(y ~ x, data = data)

# Extract key results
result <- list(
    coefficients = coef(model),
    fitted_values = fitted(model),
    residuals = residuals(model),
    r_squared = summary(model)$r.squared,
    adj_r_squared = summary(model)$adj.r.squared,
    p_values = summary(model)$coefficients[, "Pr(>|t|)"],
    model_summary = summary(model)
)
