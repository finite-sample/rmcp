# Frequency Table Analysis Script for RMCP
# ========================================
#
# This script generates comprehensive frequency tables for categorical or discrete variables
# with support for percentages, sorting, and missing value analysis.

# Prepare data and parameters
data <- as.data.frame(args$data)
variables <- args$variables
include_percentages <- args$include_percentages %||% TRUE
sort_by <- args$sort_by %||% "frequency"

freq_tables <- list()

for (var in variables) {
    values <- data[[var]]
    freq_table <- table(values, useNA = "ifany")
    
    # Sort if requested
    if (sort_by == "frequency") {
        freq_table <- sort(freq_table, decreasing = TRUE)
    }
    
    freq_data <- list(
        values = names(freq_table),
        frequencies = as.numeric(freq_table),
        n_total = length(values[!is.na(values)])
    )
    
    if (include_percentages) {
        freq_data$percentages <- as.numeric(freq_table) / sum(freq_table) * 100
    }
    
    # Add missing value info
    n_missing <- sum(is.na(values))
    if (n_missing > 0) {
        freq_data$n_missing <- n_missing
        freq_data$missing_percentage <- n_missing / length(values) * 100
    }
    
    freq_tables[[var]] <- freq_data
}

result <- list(
    frequency_tables = freq_tables,
    variables = I(as.character(variables)),
    total_observations = nrow(data),

    # Special non-validated field for formatting (using assignment instead of backticks)
    "_formatting" = list(
        summary = tryCatch({
            # Create frequency summary table
            freq_summary <- do.call(rbind, lapply(names(freq_tables), function(var) {
                ft <- freq_tables[[var]]
                data.frame(
                    Variable = var,
                    Unique_Values = length(ft$values),
                    Total_Observations = ft$n_total,
                    Missing_Values = ifelse(is.null(ft$n_missing), 0, ft$n_missing)
                )
            }))
            as.character(knitr::kable(
                freq_summary, format = "markdown", digits = 4
            ))
        }, error = function(e) {
            "Frequency tables created successfully"
        }),
        interpretation = paste0("Frequency tables created for ", length(variables), " variables.")
    )
)