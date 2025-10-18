# Logistic Regression Analysis Script for RMCP
# ============================================
#
# This script performs logistic regression and other generalized linear models
# using R's glm() function. It supports multiple families and link functions,
# with special diagnostics for binomial models.

# Prepare data and parameters
formula <- as.formula(args$formula)
family <- args$family %||% "binomial"
link <- args$link %||% "logit"

# Load required libraries
# Prepare family specification
if (family == "binomial") {
  family_spec <- binomial(link = link)
} else {
  family_spec <- get(family)()
}

# Fit GLM
model <- glm(formula, data = data, family = family_spec)
summary_model <- summary(model)

# Additional diagnostics for logistic regression
if (family == "binomial") {
  # Odds ratios
  odds_ratios <- exp(coef(model))

  # McFadden's R-squared
  ll_null <- logLik(glm(update(formula, . ~ 1), data = data, family = family_spec))
  ll_model <- logLik(model)
  mcfadden_r2 <- 1 - (ll_model / ll_null)
  # Predicted probabilities
  predicted_probs <- fitted(model)
  predicted_classes <- ifelse(predicted_probs > 0.5, 1, 0)
  # Confusion matrix (if binary outcome)
  actual <- model.response(model.frame(model))
  if (all(actual %in% c(0, 1))) {
    confusion <- table(actual, predicted_classes)
    accuracy <- sum(diag(confusion)) / sum(confusion)
  } else {
    confusion <- NULL
    accuracy <- NULL
  }
}
result <- list(
  coefficients = as.list(coef(model)),
  std_errors = as.list(summary_model$coefficients[, "Std. Error"]),
  z_values = as.list(summary_model$coefficients[, "z value"]),
  p_values = as.list(summary_model$coefficients[, "Pr(>|z|)"]),
  deviance = model$deviance,
  null_deviance = model$null.deviance,
  aic = AIC(model),
  bic = BIC(model),
  fitted_values = as.numeric(fitted(model)),
  residuals = as.numeric(residuals(model, type = "deviance")),
  n_obs = nobs(model),
  family = family,
  link = link
)
# Add logistic-specific results
if (family == "binomial") {
  result$odds_ratios <- as.list(odds_ratios)
  result$mcfadden_r_squared <- as.numeric(mcfadden_r2)
  result$predicted_probabilities <- predicted_probs
  if (!is.null(accuracy)) {
    result$accuracy <- accuracy
    result$confusion_matrix <- as.list(as.data.frame.matrix(confusion))
  }
}
