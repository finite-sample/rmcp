# Time Series Decomposition Script for RMCP
# ==========================================
#
# This script decomposes time series into trend, seasonal, and remainder
# components using additive or multiplicative decomposition methods.

# Prepare data and parameters
values <- args$data$values
frequency <- args$frequency %||% 12
decomp_type <- args$type %||% "additive"

# Create time series
ts_data <- ts(values, frequency = frequency)

# Decompose
if (decomp_type == "multiplicative") {
    decomp <- decompose(ts_data, type = "multiplicative")
} else {
    decomp <- decompose(ts_data, type = "additive")
}

# Handle NA values properly for JSON - use I() to preserve arrays
result <- list(
    original = I(as.numeric(decomp$x)),
    trend = I(as.numeric(decomp$trend)),
    seasonal = I(as.numeric(decomp$seasonal)),
    remainder = I(as.numeric(decomp$random)),
    type = decomp_type,
    frequency = frequency,
    n_obs = length(values),

    # Special non-validated field for formatting
    "_formatting" = list(
        summary = tryCatch({
            # Create decomposition summary table
            decomp_summary <- data.frame(
                Component = c("Original", "Trend", "Seasonal", "Remainder"),
                Missing_Values = c(
                    sum(is.na(decomp$x)),
                    sum(is.na(decomp$trend)),
                    sum(is.na(decomp$seasonal)),
                    sum(is.na(decomp$random))
                ),
                Type = c(decomp_type, decomp_type, decomp_type, decomp_type)
            )
            as.character(knitr::kable(
                decomp_summary, format = "markdown", digits = 4
            ))
        }, error = function(e) {
            "Time series decomposition completed successfully"
        }),
        interpretation = paste0("Time series decomposed using ", decomp_type, " method with frequency ", frequency, ".")
    )
)