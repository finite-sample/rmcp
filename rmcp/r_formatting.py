"""
R Formatting Utilities for RMCP
===============================

This module provides common R code snippets for formatting statistical results
as professional markdown tables and natural language summaries.
"""


def get_r_formatting_utilities() -> str:
    """
    Return R code that provides common formatting functions.
    
    This code will be prepended to R scripts that need formatting capabilities.
    It provides helper functions for creating markdown tables and interpreting
    statistical results in natural language.
    
    Returns:
        String containing R code with formatting utilities
    """
    return """
# ============================================================================
# R Formatting Utilities for RMCP
# ============================================================================

# Load required library
if (!require("knitr", quietly = TRUE)) {
    stop("Package 'knitr' is required for table formatting. Install with: install.packages('knitr')")
}

# Format coefficient table for regression results
format_coef_table <- function(model, title = "Regression Coefficients") {
    coef_summary <- summary(model)$coefficients
    
    # Create formatted table with proper column names
    coef_df <- data.frame(
        Variable = rownames(coef_summary),
        Coefficient = sprintf("%.3f", coef_summary[, "Estimate"]),
        `Std Error` = sprintf("%.3f", coef_summary[, "Std. Error"]),
        `t value` = sprintf("%.2f", coef_summary[, "t value"]),
        `p-value` = format_p_values(coef_summary[, "Pr(>|t|)"])
    )
    
    # Generate markdown table
    table_md <- knitr::kable(coef_df, format = "markdown", row.names = FALSE)
    
    return(paste0("### ", title, "\\n\\n", 
                 paste(table_md, collapse = "\\n"), "\\n"))
}

# Format p-values nicely (e.g., "<0.001" for very small values)
format_p_values <- function(p_vals) {
    formatted <- character(length(p_vals))
    for (i in seq_along(p_vals)) {
        if (is.na(p_vals[i])) {
            formatted[i] <- "NA"
        } else if (p_vals[i] < 0.001) {
            formatted[i] <- "<0.001"
        } else if (p_vals[i] < 0.01) {
            formatted[i] <- sprintf("%.3f", p_vals[i])
        } else {
            formatted[i] <- sprintf("%.3f", p_vals[i])
        }
    }
    return(formatted)
}

# Format correlation matrix as markdown table
format_correlation_matrix <- function(cor_matrix, title = "Correlation Matrix") {
    # Round to 3 decimal places
    cor_df <- round(cor_matrix, 3)
    
    # Add row names as first column
    cor_df <- data.frame(Variable = rownames(cor_df), cor_df)
    
    # Generate markdown table
    table_md <- knitr::kable(cor_df, format = "markdown", row.names = FALSE)
    
    return(paste0("### ", title, "\\n\\n", 
                 paste(table_md, collapse = "\\n"), "\\n"))
}

# Format summary statistics table
format_summary_stats <- function(stats_list, title = "Summary Statistics") {
    # Convert list to data frame
    stats_df <- data.frame(
        Variable = names(stats_list),
        Mean = sprintf("%.2f", sapply(stats_list, function(x) x$mean)),
        `Std Dev` = sprintf("%.2f", sapply(stats_list, function(x) x$sd)),
        Min = sprintf("%.2f", sapply(stats_list, function(x) x$min)),
        Q1 = sprintf("%.2f", sapply(stats_list, function(x) x$q1)),
        Median = sprintf("%.2f", sapply(stats_list, function(x) x$median)),
        Q3 = sprintf("%.2f", sapply(stats_list, function(x) x$q3)),
        Max = sprintf("%.2f", sapply(stats_list, function(x) x$max))
    )
    
    # Generate markdown table
    table_md <- knitr::kable(stats_df, format = "markdown", row.names = FALSE)
    
    return(paste0("### ", title, "\\n\\n", 
                 paste(table_md, collapse = "\\n"), "\\n"))
}

# Generate natural language interpretation for linear regression
interpret_linear_model <- function(model, formula_str, var_names = NULL) {
    coef_vals <- coef(model)
    summary_model <- summary(model)
    coef_summary <- summary_model$coefficients
    
    # Extract variable names
    if (is.null(var_names)) {
        all_vars <- all.vars(as.formula(formula_str))
        outcome_var <- all_vars[1]
        predictor_vars <- all_vars[-1]
    } else {
        outcome_var <- var_names$outcome
        predictor_vars <- var_names$predictors
    }
    
    # Start building interpretation
    interpretation <- "### Interpretation\\n\\n"
    
    # Model fit
    r2_pct <- round(summary_model$r.squared * 100, 1)
    interpretation <- paste0(interpretation, 
                           sprintf("The model explains **%.1f%%** of the variation in %s.\\n\\n", 
                                 r2_pct, outcome_var))
    
    # Individual coefficients
    interpretation <- paste0(interpretation, "**Key Findings:**\\n")
    
    for (var in predictor_vars) {
        if (var %in% names(coef_vals)) {
            coef_val <- coef_vals[var]
            p_val <- coef_summary[var, "Pr(>|t|)"]
            
            # Determine significance
            sig_text <- if (p_val < 0.001) "highly significant (p<0.001)" 
                       else if (p_val < 0.01) "significant (p<0.01)"
                       else if (p_val < 0.05) "significant (p<0.05)"
                       else "not significant"
            
            # Direction
            direction <- ifelse(coef_val > 0, "increases", "decreases")
            
            interpretation <- paste0(interpretation,
                                   sprintf("- A 1-unit increase in %s %s %s by %.3f (p=%.3f, %s)\\n",
                                         var, direction, outcome_var, abs(coef_val), p_val, sig_text))
        }
    }
    
    # Overall model significance
    f_stat <- summary_model$fstatistic[1]
    f_p <- pf(f_stat, summary_model$fstatistic[2], summary_model$fstatistic[3], lower.tail = FALSE)
    overall_sig <- if (f_p < 0.001) "highly significant (p<0.001)"
                  else if (f_p < 0.01) "significant (p<0.01)"
                  else if (f_p < 0.05) "significant (p<0.05)"
                  else "not significant"
    
    interpretation <- paste0(interpretation, 
                           sprintf("\\nThe overall model is %s (F=%.2f, p=%.3f).\\n", 
                                 overall_sig, f_stat, f_p))
    
    return(interpretation)
}

# Generate interpretation for correlation analysis
interpret_correlations <- function(cor_matrix, sig_tests = NULL) {
    interpretation <- "### Key Findings\\n\\n"
    
    n_vars <- nrow(cor_matrix)
    var_names <- rownames(cor_matrix)
    
    # Find strongest correlations (excluding diagonal)
    strongest_cors <- c()
    
    for (i in 1:(n_vars-1)) {
        for (j in (i+1):n_vars) {
            cor_val <- cor_matrix[i, j]
            var1 <- var_names[i]
            var2 <- var_names[j]
            
            # Get significance if available
            sig_key <- paste(var1, var2, sep = "_")
            if (!is.null(sig_tests) && sig_key %in% names(sig_tests)) {
                p_val <- sig_tests[[sig_key]]$p_value
                sig_text <- if (p_val < 0.001) ", p<0.001" 
                           else if (p_val < 0.01) ", p<0.01"
                           else if (p_val < 0.05) ", p<0.05"
                           else sprintf(", p=%.3f", p_val)
            } else {
                sig_text <- ""
            }
            
            strongest_cors <- c(strongest_cors, 
                              list(list(vars = c(var1, var2), cor = cor_val, 
                                       sig = sig_text, abs_cor = abs(cor_val))))
        }
    }
    
    # Sort by absolute correlation strength
    strongest_cors <- strongest_cors[order(sapply(strongest_cors, function(x) x$abs_cor), decreasing = TRUE)]
    
    # Report top 3 correlations
    for (i in 1:min(3, length(strongest_cors))) {
        cor_info <- strongest_cors[[i]]
        strength <- if (cor_info$abs_cor >= 0.8) "very strong"
                   else if (cor_info$abs_cor >= 0.6) "strong"
                   else if (cor_info$abs_cor >= 0.4) "moderate"
                   else if (cor_info$abs_cor >= 0.2) "weak"
                   else "very weak"
        
        direction <- ifelse(cor_info$cor > 0, "positive", "negative")
        
        interpretation <- paste0(interpretation,
                               sprintf("- **%s %s correlation** between %s and %s (r=%.3f%s)\\n",
                                     stringr::str_to_title(strength), direction,
                                     cor_info$vars[1], cor_info$vars[2], 
                                     cor_info$cor, cor_info$sig))
    }
    
    return(interpretation)
}

# Create model statistics summary
format_model_stats <- function(model, title = "Model Statistics") {
    summary_model <- summary(model)
    
    stats_text <- paste0("### ", title, "\\n\\n")
    stats_text <- paste0(stats_text, sprintf("- **R²** = %.3f (%.1f%% variance explained)\\n", 
                                            summary_model$r.squared, 
                                            summary_model$r.squared * 100))
    stats_text <- paste0(stats_text, sprintf("- **Adjusted R²** = %.3f\\n", 
                                            summary_model$adj.r.squared))
    stats_text <- paste0(stats_text, sprintf("- **F-statistic** = %.2f (df = %.0f, %.0f)\\n", 
                                            summary_model$fstatistic[1],
                                            summary_model$fstatistic[2], 
                                            summary_model$fstatistic[3]))
    
    # Calculate F p-value
    f_p <- pf(summary_model$fstatistic[1], 
              summary_model$fstatistic[2], 
              summary_model$fstatistic[3], 
              lower.tail = FALSE)
    
    stats_text <- paste0(stats_text, sprintf("- **F p-value** = %s\\n", 
                                            ifelse(f_p < 0.001, "<0.001", sprintf("%.3f", f_p))))
    stats_text <- paste0(stats_text, sprintf("- **Residual SE** = %.3f (df = %.0f)\\n", 
                                            summary_model$sigma, summary_model$df[2]))
    stats_text <- paste0(stats_text, sprintf("- **Sample size** = %d observations\\n", 
                                            nrow(model$model)))
    
    return(stats_text)
}
"""


def get_r_formatting_for_linear_model() -> str:
    """
    Get R code specifically for formatting linear model results.
    
    Returns:
        String with R code for linear model formatting
    """
    return get_r_formatting_utilities() + """

# Format complete linear regression results
format_linear_model_results <- function(model, formula_str, title = "Linear Regression Results") {
    # Build complete formatted output
    output <- paste0("## ", title, "\\n\\n")
    
    # Model statistics
    output <- paste0(output, format_model_stats(model))
    output <- paste0(output, "\\n")
    
    # Coefficients table
    output <- paste0(output, format_coef_table(model))
    output <- paste0(output, "\\n")
    
    # Interpretation
    output <- paste0(output, interpret_linear_model(model, formula_str))
    
    return(output)
}
"""


def get_r_formatting_for_correlation() -> str:
    """
    Get R code specifically for formatting correlation analysis results.
    
    Returns:
        String with R code for correlation formatting
    """
    return get_r_formatting_utilities() + """

# Format complete correlation analysis results
format_correlation_results <- function(cor_matrix, sig_tests = NULL, method = "pearson", 
                                      title = "Correlation Analysis") {
    # Build complete formatted output
    method_name <- switch(method,
                         "pearson" = "Pearson",
                         "spearman" = "Spearman", 
                         "kendall" = "Kendall",
                         stringr::str_to_title(method))
    
    full_title <- paste0(title, " (", method_name, ")")
    output <- paste0("## ", full_title, "\\n\\n")
    
    # Correlation matrix table
    output <- paste0(output, format_correlation_matrix(cor_matrix))
    output <- paste0(output, "\\n")
    
    # Interpretation
    output <- paste0(output, interpret_correlations(cor_matrix, sig_tests))
    
    return(output)
}
"""