"""
Econometric analysis tools for RMCP.

Advanced econometric modeling for panel data, instrumental variables, etc.
"""

from typing import Dict, Any
from ..registries.tools import tool
from ..core.schemas import table_schema, formula_schema
from ..r_integration import execute_r_script


@tool(
    name="panel_regression",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "formula": formula_schema(),
            "id_variable": {"type": "string"},
            "time_variable": {"type": "string"},
            "model": {"type": "string", "enum": ["pooling", "within", "between", "random"], "default": "within"},
            "robust": {"type": "boolean", "default": True}
        },
        "required": ["data", "formula", "id_variable", "time_variable"]
    },
    description="Panel data regression with fixed/random effects"
)
async def panel_regression(context, params):
    """Perform panel data regression."""
    
    await context.info("Fitting panel data regression")
    
    r_script = '''
    if (!require(plm)) install.packages("plm", quietly = TRUE)
    library(plm)
    
    data <- as.data.frame(args$data)
    formula <- as.formula(args$formula)
    id_var <- args$id_variable
    time_var <- args$time_variable
    model_type <- args$model %||% "within"
    robust <- args$robust %||% TRUE
    
    # Create panel data frame
    pdata <- pdata.frame(data, index = c(id_var, time_var))
    
    # Fit panel model
    if (model_type == "pooling") {
        model <- plm(formula, data = pdata, model = "pooling")
    } else if (model_type == "within") {
        model <- plm(formula, data = pdata, model = "within")  # Fixed effects
    } else if (model_type == "between") {
        model <- plm(formula, data = pdata, model = "between")
    } else if (model_type == "random") {
        model <- plm(formula, data = pdata, model = "random")
    }
    
    # Get robust standard errors if requested
    if (robust) {
        if (!require(lmtest)) install.packages("lmtest", quietly = TRUE)
        library(lmtest)
        robust_se <- coeftest(model, vcov = vcovHC(model, type = "HC1"))
        coef_table <- robust_se
    } else {
        coef_table <- summary(model)$coefficients
    }
    
    result <- list(
        coefficients = as.list(coef_table[, "Estimate"]),
        std_errors = as.list(coef_table[, "Std. Error"]), 
        t_values = as.list(coef_table[, "t value"]),
        p_values = as.list(coef_table[, "Pr(>|t|)"]),
        r_squared = summary(model)$r.squared[1],
        adj_r_squared = summary(model)$r.squared[2],
        model_type = model_type,
        robust_se = robust,
        n_obs = nobs(model),
        n_groups = pdim(model)$nT$n,
        time_periods = pdim(model)$nT$T,
        formula = deparse(formula),
        id_variable = id_var,
        time_variable = time_var
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Panel regression completed successfully")
        return result
        
    except Exception as e:
        await context.error("Panel regression failed", error=str(e))
        raise


@tool(
    name="instrumental_variables",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "formula": {"type": "string", "description": "Format: 'y ~ x1 + x2 | z1 + z2' where | separates instruments"},
            "robust": {"type": "boolean", "default": True}
        },
        "required": ["data", "formula"]
    },
    description="Two-stage least squares (2SLS) instrumental variables regression"
)
async def instrumental_variables(context, params):
    """Perform instrumental variables regression."""
    
    await context.info("Fitting instrumental variables model")
    
    r_script = '''
    if (!require(AER)) install.packages("AER", quietly = TRUE)
    library(AER)
    
    data <- as.data.frame(args$data)
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
    
    result <- list(
        coefficients = as.list(coef_table[, "Estimate"]),
        std_errors = as.list(coef_table[, "Std. Error"]),
        t_values = as.list(coef_table[, "t value"]),
        p_values = as.list(coef_table[, "Pr(>|t|)"]),
        r_squared = summary_iv$r.squared,
        adj_r_squared = summary_iv$adj.r.squared,
        weak_instruments = list(
            statistic = summary_iv$diagnostics["Weak instruments", "statistic"],
            p_value = summary_iv$diagnostics["Weak instruments", "p-value"]
        ),
        wu_hausman = list(
            statistic = summary_iv$diagnostics["Wu-Hausman", "statistic"],
            p_value = summary_iv$diagnostics["Wu-Hausman", "p-value"]
        ),
        sargan = list(
            statistic = summary_iv$diagnostics["Sargan", "statistic"], 
            p_value = summary_iv$diagnostics["Sargan", "p-value"]
        ),
        robust_se = robust,
        formula = formula_str,
        n_obs = nobs(iv_model)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Instrumental variables model fitted successfully")
        return result
        
    except Exception as e:
        await context.error("Instrumental variables fitting failed", error=str(e))
        raise


@tool(
    name="var_model",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "lags": {"type": "integer", "minimum": 1, "maximum": 10, "default": 2},
            "type": {"type": "string", "enum": ["const", "trend", "both", "none"], "default": "const"}
        },
        "required": ["data", "variables"]
    },
    description="Vector Autoregression (VAR) model for multivariate time series"
)
async def var_model(context, params):
    """Fit Vector Autoregression model."""
    
    await context.info("Fitting VAR model")
    
    r_script = '''
    if (!require(vars)) install.packages("vars", quietly = TRUE)
    library(vars)
    
    data <- as.data.frame(args$data)
    variables <- args$variables
    lag_order <- args$lags %||% 2
    var_type <- args$type %||% "const"
    
    # Select variables for VAR
    var_data <- data[, variables, drop = FALSE]
    
    # Remove missing values
    var_data <- na.omit(var_data)
    
    # Fit VAR model
    var_model <- VAR(var_data, p = lag_order, type = var_type)
    
    # Extract coefficients for each equation
    equations <- list()
    for (var in variables) {
        eq_summary <- summary(var_model)$varresult[[var]]
        equations[[var]] <- list(
            coefficients = as.list(coef(eq_summary)),
            std_errors = as.list(eq_summary$coefficients[, "Std. Error"]),
            t_values = as.list(eq_summary$coefficients[, "t value"]),
            p_values = as.list(eq_summary$coefficients[, "Pr(>|t|)"]),
            r_squared = eq_summary$r.squared,
            adj_r_squared = eq_summary$adj.r.squared
        )
    }
    
    # Model diagnostics
    var_summary <- summary(var_model)
    
    result <- list(
        equations = equations,
        variables = variables,
        lag_order = lag_order,
        var_type = var_type,
        n_obs = nobs(var_model),
        n_variables = length(variables),
        loglik = logLik(var_model)[1],
        aic = AIC(var_model),
        bic = BIC(var_model),
        residual_covariance = as.matrix(var_summary$covres)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("VAR model fitted successfully")
        return result
        
    except Exception as e:
        await context.error("VAR model fitting failed", error=str(e))
        raise