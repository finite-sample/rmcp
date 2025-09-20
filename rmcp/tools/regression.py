"""
Regression Analysis Tools for RMCP MCP Server.

This module provides comprehensive regression modeling capabilities including:
- Linear regression with diagnostics
- Logistic regression for binary outcomes
- Correlation analysis with significance testing
- Comprehensive model validation and statistics

All tools support missing value handling, weighted observations, and return
detailed statistical outputs suitable for research and business analysis.

Example Usage:
    >>> # Linear regression on sales data
    >>> data = {"sales": [100, 120, 140], "advertising": [10, 15, 20]}
    >>> result = await linear_model(context, {
    ...     "data": data,
    ...     "formula": "sales ~ advertising"
    ... })
    >>> print(f"R-squared: {result['r_squared']}")
"""

from typing import Any

from ..core.schemas import formula_schema, table_schema
from ..r_integration import execute_r_script_async
from ..registries.tools import tool


@tool(
    name="linear_model",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(required_columns=None),
            "formula": formula_schema(),
            "weights": {"type": "array", "items": {"type": "number"}},
            "na_action": {
                "type": "string",
                "enum": ["na.omit", "na.exclude", "na.fail"],
            },
        },
        "required": ["data", "formula"],
    },
    description="Fit linear regression model with comprehensive diagnostics",
)
async def linear_model(context, params) -> dict[str, Any]:
    """
    Fit ordinary least squares (OLS) linear regression model.

    This tool performs comprehensive linear regression analysis using R's lm() function.
    It supports weighted regression, missing value handling, and returns detailed
    model diagnostics including coefficients, significance tests, and goodness-of-fit.

    Args:
        context: Request execution context for logging and progress
        params: Dictionary containing:
            - data: Dataset as dict of column_name -> [values]
            - formula: R formula string (e.g., "y ~ x1 + x2")
            - weights: Optional array of observation weights
            - na_action: How to handle missing values ("na.omit", "na.exclude", "na.fail")

    Returns:
        Dictionary containing:
            - coefficients: Model coefficients by variable name
            - std_errors: Standard errors of coefficients
            - t_values: t-statistics for coefficient tests
            - p_values: p-values for coefficient significance
            - r_squared: Coefficient of determination
            - adj_r_squared: Adjusted R-squared
            - fstatistic: Overall F-statistic value
            - f_pvalue: p-value for overall model significance
            - residual_se: Residual standard error
            - fitted_values: Predicted values for each observation
            - residuals: Model residuals
            - n_obs: Number of observations used

    Example:
        >>> # Simple linear regression
        >>> data = {
        ...     "price": [100, 120, 140, 160, 180],
        ...     "size": [1000, 1200, 1400, 1600, 1800]
        ... }
        >>> result = await linear_model(context, {
        ...     "data": data,
        ...     "formula": "price ~ size"
        ... })
        >>> print(f"Price increases ${result['coefficients']['size']:.2f} per sq ft")
        >>> print(f"Model explains {result['r_squared']:.1%} of variance")

        >>> # Multiple regression with weights
        >>> data = {
        ...     "sales": [100, 150, 200, 250],
        ...     "advertising": [10, 20, 30, 40],
        ...     "price": [50, 45, 40, 35]
        ... }
        >>> result = await linear_model(context, {
        ...     "data": data,
        ...     "formula": "sales ~ advertising + price",
        ...     "weights": [1, 1, 2, 2]  # Weight later observations more
        ... })
    """

    await context.info("Fitting linear regression model")

    r_script = """
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
    
    result <- list(
        coefficients = as.list(coef(model)),
        std_errors = as.list(summary_model$coefficients[, "Std. Error"]),
        t_values = as.list(summary_model$coefficients[, "t value"]),  
        p_values = as.list(summary_model$coefficients[, "Pr(>|t|)"]),
        r_squared = summary_model$r.squared,
        adj_r_squared = summary_model$adj.r.squared,
        fstatistic = summary_model$fstatistic[1],
        f_pvalue = pf(summary_model$fstatistic[1], 
                     summary_model$fstatistic[2], 
                     summary_model$fstatistic[3], lower.tail = FALSE),
        residual_se = summary_model$sigma,
        df_residual = summary_model$df[2],
        fitted_values = as.numeric(fitted(model)),
        residuals = as.numeric(residuals(model)),
        n_obs = nrow(model$model),
        method = "lm"
    )
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info(
            "Linear model fitted successfully",
            r_squared=result.get("r_squared"),
            n_obs=result.get("n_obs"),
        )
        return result

    except Exception as e:
        await context.error("Linear model fitting failed", error=str(e))
        raise


@tool(
    name="correlation_analysis",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables to include in correlation analysis",
            },
            "method": {
                "type": "string",
                "enum": ["pearson", "spearman", "kendall"],
                "description": "Correlation method",
            },
            "use": {
                "type": "string",
                "enum": [
                    "everything",
                    "all.obs",
                    "complete.obs",
                    "na.or.complete",
                    "pairwise.complete.obs",
                ],
                "description": "Missing value handling",
            },
        },
        "required": ["data"],
    },
    description="Comprehensive correlation analysis with significance tests",
)
async def correlation_analysis(context, params) -> dict[str, Any]:
    """
    Compute correlation matrix with significance testing.

    This tool calculates pairwise correlations between numeric variables using
    Pearson, Spearman, or Kendall methods. It includes significance tests for
    each correlation and handles missing values appropriately.

    Args:
        context: Request execution context for logging and progress
        params: Dictionary containing:
            - data: Dataset as dict of column_name -> [values]
            - variables: Optional list of variable names to include
            - method: Correlation method ("pearson", "spearman", "kendall")
            - use: Missing value handling strategy

    Returns:
        Dictionary containing:
            - correlation_matrix: Pairwise correlations as nested dict
            - significance_tests: p-values for each correlation
            - sample_sizes: Number of complete observations for each pair
            - variables_used: List of variables included in analysis
            - method_used: Correlation method applied

    Example:
        >>> # Basic correlation analysis
        >>> data = {
        ...     "sales": [100, 150, 200, 250, 300],
        ...     "advertising": [10, 20, 25, 35, 40],
        ...     "price": [50, 48, 45, 42, 40]
        ... }
        >>> result = await correlation_analysis(context, {
        ...     "data": data,
        ...     "method": "pearson"
        ... })
        >>> sales_ad_corr = result["correlation_matrix"]["sales"]["advertising"]
        >>> print(f"Sales-Advertising correlation: {sales_ad_corr:.3f}")

        >>> # Spearman correlation for non-linear relationships
        >>> result = await correlation_analysis(context, {
        ...     "data": data,
        ...     "method": "spearman",
        ...     "variables": ["sales", "advertising"]
        ... })
    """

    await context.info("Computing correlation matrix")

    r_script = """
    data <- as.data.frame(args$data)
    variables <- args$variables
    method <- args$method %||% "pearson"
    use <- args$use %||% "complete.obs"
    
    # Select variables if specified
    if (!is.null(variables)) {
        # Validate variables exist
        missing_vars <- setdiff(variables, names(data))
        if (length(missing_vars) > 0) {
            stop(paste("Variables not found:", paste(missing_vars, collapse = ", ")))
        }
        data <- data[, variables, drop = FALSE]
    }
    
    # Select only numeric variables
    numeric_vars <- sapply(data, is.numeric)
    if (sum(numeric_vars) < 2) {
        stop("Need at least 2 numeric variables for correlation analysis")
    }
    numeric_data <- data[, numeric_vars, drop = FALSE]
    
    # Compute correlation matrix
    cor_matrix <- cor(numeric_data, method = method, use = use)
    
    # Compute significance tests
    n <- nrow(numeric_data)
    cor_test_results <- list()
    
    for (i in 1:(ncol(numeric_data)-1)) {
        for (j in (i+1):ncol(numeric_data)) {
            var1 <- names(numeric_data)[i]
            var2 <- names(numeric_data)[j]
            
            # Filter complete cases for cor.test (cor.test doesn't accept 'use' parameter)
            x <- numeric_data[,i]
            y <- numeric_data[,j]
            complete_cases <- !is.na(x) & !is.na(y)
            test_result <- cor.test(x[complete_cases], y[complete_cases], method = method)
            
            cor_test_results[[paste(var1, var2, sep = "_")]] <- list(
                correlation = test_result$estimate,
                p_value = test_result$p.value,
                conf_int_lower = if (!is.null(test_result$conf.int)) test_result$conf.int[1] else NA,
                conf_int_upper = if (!is.null(test_result$conf.int)) test_result$conf.int[2] else NA
            )
        }
    }
    
    result <- list(
        correlation_matrix = as.list(as.data.frame(cor_matrix)),
        significance_tests = cor_test_results,
        method = method,
        n_obs = n,
        variables = names(numeric_data)
    )
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info(
            "Correlation analysis completed",
            n_variables=len(result.get("variables", [])),
            method=result.get("method"),
        )
        return result

    except Exception as e:
        await context.error("Correlation analysis failed", error=str(e))
        raise


@tool(
    name="logistic_regression",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "formula": formula_schema(),
            "family": {
                "type": "string",
                "enum": ["binomial", "poisson", "gamma", "inverse.gaussian"],
                "description": "Error distribution family",
            },
            "link": {
                "type": "string",
                "enum": ["logit", "probit", "cloglog", "cauchit"],
                "description": "Link function for binomial family",
            },
        },
        "required": ["data", "formula"],
    },
    description="Fit generalized linear model (logistic regression)",
)
async def logistic_regression(context, params) -> dict[str, Any]:
    """Fit logistic regression model."""

    await context.info("Fitting logistic regression model")

    r_script = """
    data <- as.data.frame(args$data)
    formula <- as.formula(args$formula)
    family <- args$family %||% "binomial"
    link <- args$link %||% "logit"
    
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
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info(
            "Logistic regression fitted successfully",
            aic=result.get("aic"),
            n_obs=result.get("n_obs"),
        )
        return result

    except Exception as e:
        await context.error("Logistic regression fitting failed", error=str(e))
        raise
