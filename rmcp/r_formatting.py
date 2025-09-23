"""
R Formatting Utilities for RMCP
===============================

This module provides R formatting utilities using broom and knitr packages
to create professional markdown tables and summaries from R statistical results.
"""


def get_r_formatting_utilities() -> str:
    """
    Return minimal R formatting utilities using broom and knitr.

    These packages are required dependencies - if missing, tools will fail
    with clear error messages about installation.

    Returns:
        String containing R code with formatting utilities
    """
    return """
# Load required formatting libraries
library(broom)
library(knitr)

# Format any R result using broom::tidy and knitr::kable
format_result_table <- function(obj, title = NULL, digits = 4) {
    # Use broom to create tidy data frame
    tidy_result <- tidy(obj)

    # Create markdown table and convert to character string for JSON serialization
    formatted_table <- as.character(kable(
        tidy_result, format = "markdown", digits = digits
    ))

    # Add title if provided
    if (!is.null(title)) {
        output <- paste0("## ", title, "\\n\\n",
                        paste(formatted_table, collapse = "\\n"))
    } else {
        output <- paste(formatted_table, collapse = "\\n")
    }

    return(output)
}

# Get significance text from p-value
get_significance <- function(p_value) {
    if (is.na(p_value)) {
        return("unable to determine significance")
    } else if (p_value < 0.001) {
        return("highly significant (p < 0.001)")
    } else if (p_value < 0.01) {
        return("significant (p < 0.01)")
    } else if (p_value < 0.05) {
        return("significant (p < 0.05)")
    } else {
        return(paste0("not significant (p = ", round(p_value, 4), ")"))
    }
}

# Simple interpretation for any test with p-value
interpret_result <- function(obj, test_name = "Test") {
    tidy_result <- tidy(obj)

    # Extract p-value (broom usually puts it in p.value column)
    p_val <- if("p.value" %in% names(tidy_result)) {
        tidy_result$p.value[1]
    } else {
        NA
    }

    paste0(test_name, " result is ", get_significance(p_val), ".")
}
"""


def get_r_formatting_for_linear_model() -> str:
    """
    Get R code for formatting linear model results.

    Returns:
        String with R code for linear model formatting using broom
    """
    return (
        get_r_formatting_utilities()
        + """

# Format linear model with model statistics
format_lm_results <- function(model, formula_str) {
    # Get tidy coefficients table
    coef_table <- tidy(model, conf.int = TRUE)
    formatted_coefs <- as.character(kable(coef_table, format = "markdown", digits = 4))

    # Get model statistics
    model_stats <- glance(model)
    stats_summary <- paste0(
        "**Model Statistics:**\\n",
        "- R² = ", round(model_stats$r.squared, 4), "\\n",
        "- Adjusted R² = ", round(model_stats$adj.r.squared, 4), "\\n",
        "- F-statistic = ", round(model_stats$statistic, 2),
        " (p ", ifelse(model_stats$p.value < 0.001, "< 0.001",
                      paste0("= ", round(model_stats$p.value, 4))), ")\\n"
    )

    # Combine output
    output <- paste0(
        "## Linear Regression Results\\n\\n",
        stats_summary, "\\n\\n",
        "### Coefficients\\n\\n",
        paste(formatted_coefs, collapse = "\\n")
    )

    return(output)
}

# Interpret linear model
interpret_lm <- function(model) {
    model_stats <- glance(model)
    r2_pct <- round(model_stats$r.squared * 100, 1)

    paste0(
        "The model explains ", r2_pct, "% of the variance. ",
        "Overall model is ", get_significance(model_stats$p.value), "."
    )
}
"""
    )


def get_r_formatting_for_correlation() -> str:
    """
    Get R code for formatting correlation analysis results.

    Returns:
        String with R code for correlation formatting
    """
    return (
        get_r_formatting_utilities()
        + """

# Format correlation matrix using kable
format_correlation_matrix <- function(cor_matrix, digits = 3) {
    # Convert to data frame for kable
    cor_df <- as.data.frame(cor_matrix)

    # Add row names as first column
    cor_df <- cbind(Variable = rownames(cor_df), cor_df)

    # Format as markdown table and convert to character string
    formatted <- as.character(kable(
        cor_df, format = "markdown", digits = digits, row.names = FALSE
    ))

    output <- paste0(
        "## Correlation Matrix\\n\\n",
        paste(formatted, collapse = "\\n")
    )

    return(output)
}
"""
    )
