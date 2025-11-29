# End-to-end test: Economist workflow
# Panel data regression with robust standard errors

library(plm)
library(lmtest)
library(sandwich)

# Convert to panel data frame
pdata <- pdata.frame(data, index = c("id", "time"))

# Fit fixed effects model
model <- plm(y ~ x, data = pdata, model = "within")

# Robust standard errors
robust_se <- sqrt(diag(vcovHC(model, type = "HC1")))

# Results
result <- list(
    coefficients = coef(model),
    standard_errors = robust_se,
    t_statistics = coef(model) / robust_se,
    model_type = "fixed_effects",
    n_obs = nobs(model),
    n_groups = pdim(model)$nT$n
)
