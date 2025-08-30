"""
Statistical hypothesis testing tools for RMCP.

Comprehensive statistical testing capabilities.
"""

from typing import Dict, Any
from ..registries.tools import tool
from ..core.schemas import table_schema
from ..r_integration import execute_r_script


@tool(
    name="t_test",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variable": {"type": "string"},
            "group": {"type": "string"},
            "mu": {"type": "number", "default": 0},
            "alternative": {"type": "string", "enum": ["two.sided", "less", "greater"], "default": "two.sided"},
            "paired": {"type": "boolean", "default": False},
            "var_equal": {"type": "boolean", "default": True}
        },
        "required": ["data", "variable"]
    },
    description="Perform t-tests (one-sample, two-sample, paired)"
)
async def t_test(context, params):
    """Perform t-test analysis."""
    
    await context.info("Performing t-test")
    
    r_script = '''
    data <- as.data.frame(args$data)
    variable <- args$variable
    group <- args$group
    mu <- args$mu %||% 0
    alternative <- args$alternative %||% "two.sided"
    paired <- args$paired %||% FALSE
    var_equal <- args$var_equal %||% TRUE
    
    if (is.null(group)) {
        # One-sample t-test
        test_result <- t.test(data[[variable]], mu = mu, alternative = alternative)
        test_type <- "One-sample t-test"
        
        result <- list(
            test_type = test_type,
            statistic = as.numeric(test_result$statistic),
            df = test_result$parameter,
            p_value = test_result$p.value,
            confidence_interval = as.numeric(test_result$conf.int),
            mean = as.numeric(test_result$estimate),
            null_value = mu,
            alternative = alternative,
            n_obs = length(data[[variable]][!is.na(data[[variable]])])
        )
        
    } else {
        # Two-sample t-test
        group_values <- data[[group]]
        unique_groups <- unique(group_values[!is.na(group_values)])
        
        if (length(unique_groups) != 2) {
            stop("Group variable must have exactly 2 levels")
        }
        
        x <- data[[variable]][group_values == unique_groups[1]]
        y <- data[[variable]][group_values == unique_groups[2]]
        
        test_result <- t.test(x, y, alternative = alternative, paired = paired, var.equal = var_equal)
        test_type <- if (paired) "Paired t-test" else "Two-sample t-test"
        
        result <- list(
            test_type = test_type,
            statistic = as.numeric(test_result$statistic),
            df = test_result$parameter,
            p_value = test_result$p.value,
            confidence_interval = as.numeric(test_result$conf.int),
            mean_x = as.numeric(test_result$estimate[1]),
            mean_y = as.numeric(test_result$estimate[2]),
            mean_difference = as.numeric(test_result$estimate[1] - test_result$estimate[2]),
            groups = unique_groups,
            alternative = alternative,
            paired = paired,
            n_obs_x = length(x[!is.na(x)]),
            n_obs_y = length(y[!is.na(y)])
        )
    }
    '''
    
    try:
        result = execute_r_script(r_script, params)
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
            "type": {"type": "string", "enum": ["I", "II", "III"], "default": "I"}
        },
        "required": ["data", "formula"]
    },
    description="Analysis of Variance (ANOVA) with multiple types"
)
async def anova(context, params):
    """Perform ANOVA analysis."""
    
    await context.info("Performing ANOVA")
    
    r_script = '''
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
        if (!require(car)) install.packages("car", quietly = TRUE)
        library(car)
        anova_table <- Anova(model, type = as.numeric(substr(anova_type, 1, 1)))
    }
    
    # Extract ANOVA table
    result <- list(
        anova_table = list(
            terms = rownames(anova_table),
            df = anova_table[["Df"]],
            sum_sq = anova_table[["Sum Sq"]] %||% anova_table[["Sum of Sq"]],
            mean_sq = anova_table[["Mean Sq"]] %||% (anova_table[["Sum of Sq"]] / anova_table[["Df"]]),
            f_value = anova_table[["F value"]] %||% anova_table[["F"]],
            p_value = anova_table[["Pr(>F)"]] %||% anova_table[["Pr(>F)"]]
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
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("ANOVA completed successfully")
        return result
        
    except Exception as e:
        await context.error("ANOVA failed", error=str(e))
        raise


@tool(
    name="chi_square_test",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "x": {"type": "string"},
            "y": {"type": "string"},
            "test_type": {"type": "string", "enum": ["independence", "goodness_of_fit"], "default": "independence"},
            "expected": {"type": "array", "items": {"type": "number"}}
        },
        "required": ["data"]
    },
    description="Chi-square tests for independence and goodness of fit"
)
async def chi_square_test(context, params):
    """Perform chi-square tests."""
    
    await context.info("Performing chi-square test")
    
    r_script = '''
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
            test_result <- chisq.test(observed, p = expected)
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
    '''
    
    try:
        result = execute_r_script(r_script, params)
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
            "test": {"type": "string", "enum": ["shapiro", "jarque_bera", "anderson"], "default": "shapiro"}
        },
        "required": ["data", "variable"]
    },
    description="Test variables for normality (Shapiro-Wilk, Jarque-Bera, Anderson-Darling)"
)
async def normality_test(context, params):
    """Test for normality."""
    
    await context.info("Testing for normality")
    
    r_script = '''
    data <- as.data.frame(args$data)
    variable <- args$variable
    test_type <- args$test %||% "shapiro"
    
    values <- data[[variable]]
    values <- values[!is.na(values)]
    
    if (test_type == "shapiro") {
        test_result <- shapiro.test(values)
        result <- list(
            test_name = "Shapiro-Wilk normality test",
            statistic = as.numeric(test_result$statistic),
            p_value = test_result$p.value,
            is_normal = test_result$p.value > 0.05
        )
        
    } else if (test_type == "jarque_bera") {
        if (!require(tseries)) install.packages("tseries", quietly = TRUE)
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
        if (!require(nortest)) install.packages("nortest", quietly = TRUE)
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
    result$n_obs <- length(values)
    result$mean <- mean(values)
    result$sd <- sd(values)
    result$skewness <- (sum((values - mean(values))^3) / length(values)) / (sd(values)^3)
    result$kurtosis <- (sum((values - mean(values))^4) / length(values)) / (sd(values)^4) - 3
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Normality test completed successfully")
        return result
        
    except Exception as e:
        await context.error("Normality test failed", error=str(e))
        raise