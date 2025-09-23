# Summary Statistics Analysis Script for RMCP
# ===========================================
#
# This script computes comprehensive descriptive statistics for numeric variables
# with support for grouped analysis and customizable percentiles.

library(dplyr)

# Prepare data and parameters
data <- as.data.frame(args$data)
variables <- args$variables
group_by <- args$group_by
percentiles <- args$percentiles %||% c(0.25, 0.5, 0.75)

# Select variables to analyze
if (is.null(variables)) {
    numeric_vars <- names(data)[sapply(data, is.numeric)]
    if (length(numeric_vars) == 0) {
        stop("No numeric variables found in data")
    }
    variables <- numeric_vars
}

# Function to compute detailed stats
compute_stats <- function(x) {
    x_clean <- x[!is.na(x)]
    if (length(x_clean) == 0) {
        return(list(
            n = 0, n_missing = length(x), mean = NA, sd = NA, min = NA, max = NA,
            q25 = NA, median = NA, q75 = NA, skewness = NA, kurtosis = NA
        ))
    }
    stats <- list(
        n = length(x_clean),
        n_missing = sum(is.na(x)),
        mean = mean(x_clean),
        sd = sd(x_clean),
        min = min(x_clean),
        max = max(x_clean),
        range = max(x_clean) - min(x_clean),
        skewness = (sum((x_clean - mean(x_clean))^3) / length(x_clean)) / (sd(x_clean)^3),
        kurtosis = (sum((x_clean - mean(x_clean))^4) / length(x_clean)) / (sd(x_clean)^4) - 3
    )
    # Add percentiles
    for (i in seq_along(percentiles)) {
        pct_name <- paste0("p", percentiles[i] * 100)
        stats[[pct_name]] <- quantile(x_clean, percentiles[i])
    }
    return(stats)
}

if (is.null(group_by)) {
    # Overall statistics
    stats_list <- list()
    for (var in variables) {
        stats_list[[var]] <- compute_stats(data[[var]])
    }
    result <- list(
        statistics = stats_list,
        variables = variables,
        n_obs = nrow(data),
        grouped = FALSE
    )

    # Add formatting using assignment approach like normality test
    result$"_formatting" <- list(
        summary = tryCatch({
            # Create a simple data frame for broom::tidy
            stats_df <- do.call(rbind, lapply(names(stats_list), function(var) {
                s <- stats_list[[var]]
                data.frame(variable = var, n = s$n, mean = s$mean, sd = s$sd, min = s$min, max = s$max)
            }))
            as.character(knitr::kable(
                stats_df, format = "markdown", digits = 4
            ))
        }, error = function(e) {
            "Summary statistics computed successfully"
        }),
        interpretation = paste0("Summary statistics for ", length(variables), " variables computed.")
    )
} else {
    # Grouped statistics
    grouped_stats <- list()
    groups <- unique(data[[group_by]][!is.na(data[[group_by]])])
    for (group_val in groups) {
        group_data <- data[data[[group_by]] == group_val, ]
        group_stats <- list()
        for (var in variables) {
            group_stats[[var]] <- compute_stats(group_data[[var]])
        }
        grouped_stats[[as.character(group_val)]] <- group_stats
    }
    result <- list(
        statistics = grouped_stats,
        variables = variables,
        group_by = group_by,
        groups = as.character(groups),
        n_obs = nrow(data),
        grouped = TRUE
    )

    # Add formatting using assignment approach like normality test
    result$"_formatting" <- list(
        summary = tryCatch({
            # Create summary table for grouped stats
            group_summary <- paste0("Grouped statistics by ", group_by, " (", length(groups), " groups)")
            as.character(knitr::kable(
                data.frame(Summary = group_summary), 
                format = "markdown"
            ))
        }, error = function(e) {
            "Grouped summary statistics computed successfully"
        }),
        interpretation = paste0("Summary statistics for ", length(variables), " variables across ", length(groups), " groups.")
    )
}