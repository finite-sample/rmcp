"""
Statistical hypothesis testing tools for RMCP.

Comprehensive statistical testing capabilities.
"""

from typing import Any

from ..core.schemas import table_schema
from ..r_integration import execute_r_script_async
from ..registries.tools import tool


@tool(
    name="t_test",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variable": {"type": "string"},
            "group": {
                "type": "string",
                "description": "Required for two-sample t-test. Column name for group variable. Omit for one-sample t-test."
            },
            "mu": {"type": "number", "default": 0},
            "alternative": {
                "type": "string",
                "enum": ["two.sided", "less", "greater"],
                "default": "two.sided",
            },
            "paired": {"type": "boolean", "default": False},
            "var_equal": {"type": "boolean", "default": False},
        },
        "required": ["data", "variable"],
    },
    description="Perform t-tests (one-sample, two-sample, paired)",
)
async def t_test(context, params) -> dict[str, Any]:
    """Perform t-test analysis."""

    await context.info("Performing t-test")

    r_script = """
    
    data <- as.data.frame(args$data)
    variable <- args$variable
    group <- args$group
    mu <- args$mu %||% 0
    alternative <- args$alternative %||% "two.sided"
    paired <- args$paired %||% FALSE
    var_equal <- args$var_equal %||% FALSE
    
    if (is.null(group)) {
        # One-sample t-test
        test_result <- t.test(data[[variable]], mu = mu, alternative = alternative)
        test_type <- "One-sample t-test"
        
        # Clean data
        values <- data[[variable]][!is.na(data[[variable]])]
        
        result <- list(
            test_type = test_type,
            statistic = as.numeric(test_result$statistic),
            df = test_result$parameter,
            p_value = test_result$p.value,
            confidence_interval = list(
                lower = as.numeric(test_result$conf.int[1]),
                upper = as.numeric(test_result$conf.int[2]),
                level = attr(test_result$conf.int, "conf.level") %||% 0.95
            ),
            mean = as.numeric(test_result$estimate),
            null_value = mu,
            alternative = alternative,
            n_obs = length(values)
        )
        
    } else {
        # Two-sample t-test
        group_values <- data[[group]]
        # Sort groups consistently and handle NA values
        unique_groups <- sort(unique(stats::na.omit(group_values)))
        
        if (length(unique_groups) != 2) {
            stop("Group variable must have exactly 2 levels")
        }
        
        # Extract and clean data for each group
        x <- data[[variable]][group_values == unique_groups[1]]
        y <- data[[variable]][group_values == unique_groups[2]]
        x <- x[!is.na(x)]
        y <- y[!is.na(y)]
        
        test_result <- t.test(x, y, alternative = alternative, paired = paired, var.equal = var_equal)
        test_type <- if (paired) "Paired t-test" else if (var_equal) "Two-sample t-test (equal variances)" else "Welch's t-test"
        
        result <- list(
            test_type = test_type,
            statistic = as.numeric(test_result$statistic),
            df = test_result$parameter,
            p_value = test_result$p.value,
            confidence_interval = list(
                lower = as.numeric(test_result$conf.int[1]),
                upper = as.numeric(test_result$conf.int[2]),
                level = attr(test_result$conf.int, "conf.level") %||% 0.95
            ),
            mean_x = as.numeric(test_result$estimate[1]),
            mean_y = as.numeric(test_result$estimate[2]),
            mean_difference = as.numeric(test_result$estimate[1] - test_result$estimate[2]),
            groups = unique_groups,
            alternative = alternative,
            paired = paired,
            var_equal = var_equal,
            n_obs_x = length(x),
            n_obs_y = length(y)
        )
    }
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("T-test completed successfully")
        return result

    except Exception as e:
        await context.error("T-test failed", error=str(e))
        raise


@tool(
    name="anova",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "formula": {"type": "string"},
            "type": {"type": "string", "enum": ["I", "II", "III"], "default": "I"},
        },
        "required": ["data", "formula"],
    },
    description="Analysis of Variance (ANOVA) with multiple types",
)
async def anova(context, params) -> dict[str, Any]:
    """Perform ANOVA analysis."""

    await context.info("Performing ANOVA")

    r_script = """
    
    data <- as.data.frame(args$data)
    formula <- as.formula(args$formula)
    anova_type <- args$type %||% "I"
    
    # Fit the model
    model <- lm(formula, data = data)
    
    # Perform ANOVA
    if (anova_type == "I") {
        anova_result <- anova(model)
        anova_table <- anova_result
    } else {
        library(car)
        # Convert ANOVA type string (e.g., "II", "III") to numeric for car::Anova
        # Type I = 1, Type II = 2, Type III = 3
        anova_numeric <- as.numeric(substr(anova_type, 1, 1))
        anova_table <- Anova(model, type = anova_numeric)
    }
    
    # Normalize ANOVA table column names
    df <- as.data.frame(anova_table)
    names(df) <- gsub("Pr\\(>F\\)", "p_value", names(df))
    names(df) <- gsub("^F value$", "F", names(df))
    names(df) <- gsub("^Sum of Sq$", "Sum Sq", names(df))
    names(df) <- gsub("^Mean of Sq$", "Mean Sq", names(df))
    
    # Extract values using normalized names
    sum_sq <- if ("Sum Sq" %in% names(df)) df[["Sum Sq"]] else rep(NA, nrow(df))
    mean_sq <- if ("Mean Sq" %in% names(df)) df[["Mean Sq"]] else if ("Sum Sq" %in% names(df) && "Df" %in% names(df)) df[["Sum Sq"]] / df[["Df"]] else rep(NA, nrow(df))
    f_value <- if ("F" %in% names(df)) df[["F"]] else rep(NA, nrow(df))
    p_value <- if ("p_value" %in% names(df)) df[["p_value"]] else rep(NA, nrow(df))

    result <- list(
        anova_table = list(
            terms = rownames(df),
            df = df[["Df"]],
            sum_sq = sum_sq,
            mean_sq = mean_sq,
            f_value = f_value,
            p_value = p_value
        ),
        model_summary = list(
            r_squared = summary(model)$r.squared,
            adj_r_squared = summary(model)$adj.r.squared,
            residual_se = summary(model)$sigma,
            df_residual = summary(model)$df[2],
            n_obs = nrow(model$model)
        ),
        formula = deparse(formula),
        anova_type = paste("Type", anova_type)
    )
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("ANOVA completed successfully")
        return result

    except Exception as e:
        await context.error("ANOVA failed", error=str(e))
        raise


@tool(
    name="chi_square_test",
    input_schema={
        "type": "object",
        "oneOf": [
            {
                "properties": {
                    "data": table_schema(),
                    "test_type": {"const": "independence"},
                    "x": {"type": "string"},
                    "y": {"type": "string"},
                },
                "required": ["data", "test_type", "x", "y"],
                "additionalProperties": False,
            },
            {
                "properties": {
                    "data": table_schema(),
                    "test_type": {"const": "goodness_of_fit"},
                    "x": {"type": "string"},
                    "expected": {
                        "type": "array", 
                        "items": {"type": "number", "minimum": 0},
                        "minItems": 1
                    },
                },
                "required": ["data", "test_type", "x"],
                "additionalProperties": False,
            },
        ],
    },
    description="Chi-square tests for independence and goodness of fit",
)
async def chi_square_test(context, params) -> dict[str, Any]:
    """Perform chi-square tests."""

    await context.info("Performing chi-square test")

    r_script = """
    
    data <- as.data.frame(args$data)
    x_var <- args$x
    y_var <- args$y
    test_type <- args$test_type %||% "independence"
    expected <- args$expected
    
    if (test_type == "independence") {
        if (is.null(x_var) || is.null(y_var)) {
            stop("Both x and y variables required for independence test")
        }
        
        # Create contingency table
        cont_table <- table(data[[x_var]], data[[y_var]])
        test_result <- chisq.test(cont_table)
        
        result <- list(
            test_type = "Chi-square test of independence",
            contingency_table = as.matrix(cont_table),
            statistic = as.numeric(test_result$statistic),
            df = test_result$parameter,
            p_value = test_result$p.value,
            expected_frequencies = as.matrix(test_result$expected),
            residuals = as.matrix(test_result$residuals),
            x_variable = x_var,
            y_variable = y_var,
            cramers_v = sqrt(test_result$statistic / (sum(cont_table) * (min(dim(cont_table)) - 1)))
        )
        
    } else {
        # Goodness of fit test
        if (is.null(x_var)) {
            stop("x variable required for goodness of fit test")
        }
        
        observed <- table(data[[x_var]])
        
        if (!is.null(expected)) {
            # Validate expected probabilities
            if (length(expected) != length(observed)) {
                stop(paste("Expected probabilities length (", length(expected), 
                          ") must match number of categories (", length(observed), ")"))
            }
            if (any(expected < 0)) {
                stop("Expected probabilities must be non-negative")
            }
            if (sum(expected) == 0) {
                stop("Expected probabilities cannot all be zero")
            }
            
            # Normalize to probabilities (sum to 1)
            p <- expected / sum(expected)
            names(p) <- names(observed)
            
            test_result <- chisq.test(observed, p = p)
            
            # Warn about low expected counts
            expected_counts <- test_result$expected
            low_expected <- sum(expected_counts < 5)
            if (low_expected > 0) {
                warning(paste(low_expected, "cell(s) have expected counts < 5. Results may be unreliable."))
            }
        } else {
            test_result <- chisq.test(observed)
        }
        
        result <- list(
            test_type = "Chi-square goodness of fit test",
            observed_frequencies = as.numeric(observed),
            expected_frequencies = as.numeric(test_result$expected),
            statistic = as.numeric(test_result$statistic),
            df = test_result$parameter,
            p_value = test_result$p.value,
            residuals = as.numeric(test_result$residuals),
            categories = names(observed)
        )
    }
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Chi-square test completed successfully")
        return result

    except Exception as e:
        await context.error("Chi-square test failed", error=str(e))
        raise


@tool(
    name="normality_test",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variable": {"type": "string"},
            "test": {
                "type": "string",
                "enum": ["shapiro", "jarque_bera", "anderson"],
                "default": "shapiro",
            },
        },
        "required": ["data", "variable"],
    },
    description="Test variables for normality (Shapiro-Wilk, Jarque-Bera, Anderson-Darling)",
)
async def normality_test(context, params) -> dict[str, Any]:
    """Test for normality."""

    await context.info("Testing for normality")

    r_script = """
    
    data <- as.data.frame(args$data)
    variable <- args$variable
    test_type <- args$test %||% "shapiro"
    
    values <- data[[variable]]
    values <- values[!is.na(values)]
    n <- length(values)
    
    if (test_type == "shapiro") {
        # Check Shapiro-Wilk sample size limits
        if (n > 5000) {
            warning("Sample size (", n, ") is large for Shapiro-Wilk test. Consider using Anderson-Darling test for better reliability.")
        }
        if (n < 3) {
            stop("Shapiro-Wilk test requires at least 3 observations")
        }
        
        test_result <- shapiro.test(values)
        result <- list(
            test_name = "Shapiro-Wilk normality test",
            statistic = as.numeric(test_result$statistic),
            p_value = test_result$p.value,
            is_normal = test_result$p.value > 0.05
        )
        
    } else if (test_type == "jarque_bera") {
        if (!requireNamespace("tseries", quietly = TRUE)) {
            stop("Package 'tseries' is required for Jarque-Bera test but not installed")
        }
        library(tseries)
        test_result <- jarque.bera.test(values)
        result <- list(
            test_name = "Jarque-Bera normality test",
            statistic = as.numeric(test_result$statistic),
            df = test_result$parameter,
            p_value = test_result$p.value,
            is_normal = test_result$p.value > 0.05
        )
        
    } else if (test_type == "anderson") {
        if (!requireNamespace("nortest", quietly = TRUE)) {
            stop("Package 'nortest' is required for Anderson-Darling test but not installed")
        }
        library(nortest)
        test_result <- ad.test(values)
        result <- list(
            test_name = "Anderson-Darling normality test",
            statistic = as.numeric(test_result$statistic),
            p_value = test_result$p.value,
            is_normal = test_result$p.value > 0.05
        )
    }
    
    result$variable <- variable
    result$n_obs <- n
    result$mean <- mean(values)
    result$sd <- sd(values)
    result$skewness <- (sum((values - mean(values))^3) / n) / (sd(values)^3)
    result$excess_kurtosis <- (sum((values - mean(values))^4) / n) / (sd(values)^4) - 3
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Normality test completed successfully")
        return result

    except Exception as e:
        await context.error("Normality test failed", error=str(e))
        raise
