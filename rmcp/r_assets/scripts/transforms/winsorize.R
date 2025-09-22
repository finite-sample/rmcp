# Winsorization Script for RMCP
# ==============================
#
# This script winsorizes variables to handle outliers by capping extreme values
# at specified percentile thresholds, preserving data structure while reducing outlier impact.

# Prepare data and parameters
data <- as.data.frame(args$data)
variables <- args$variables
percentiles <- args$percentiles %||% c(0.01, 0.99)

result_data <- data
outliers_summary <- list()

for (var in variables) {
    original_values <- data[[var]]
    
    # Calculate percentile thresholds
    lower_threshold <- quantile(original_values, percentiles[1], na.rm = TRUE)
    upper_threshold <- quantile(original_values, percentiles[2], na.rm = TRUE)
    
    # Winsorize
    winsorized <- pmax(pmin(original_values, upper_threshold), lower_threshold)
    result_data[[var]] <- winsorized
    
    # Track changes
    n_lower <- sum(original_values < lower_threshold, na.rm = TRUE)
    n_upper <- sum(original_values > upper_threshold, na.rm = TRUE)
    
    outliers_summary[[var]] <- list(
        lower_threshold = lower_threshold,
        upper_threshold = upper_threshold,
        n_capped_lower = n_lower,
        n_capped_upper = n_upper,
        total_capped = n_lower + n_upper
    )
}

result <- list(
    data = as.list(result_data),
    outliers_summary = outliers_summary,
    percentiles = percentiles,
    variables_winsorized = I(variables),
    n_obs = nrow(result_data),

    # Special non-validated field for formatting
    "_formatting" = list(
        summary = tryCatch({
            # Create winsorization summary table
            total_capped <- sum(sapply(outliers_summary, function(x) x$total_capped))
            winsor_summary <- data.frame(
                Operation = "Winsorization",
                Variables = length(variables),
                Percentiles = paste0(percentiles[1]*100, "%-", percentiles[2]*100, "%"),
                Total_Outliers_Capped = total_capped,
                Observations = nrow(result_data)
            )
            as.character(knitr::kable(
                winsor_summary, format = "markdown", digits = 4
            ))
        }, error = function(e) {
            "Variables winsorized successfully"
        }),
        interpretation = paste0("Winsorized ", length(variables), " variables at ",
                              percentiles[1]*100, "%-", percentiles[2]*100, "% thresholds.")
    )
)