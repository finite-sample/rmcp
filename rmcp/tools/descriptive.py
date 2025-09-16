"""
Descriptive statistics tools for RMCP.

Comprehensive data exploration and summary capabilities.
"""

from typing import Dict, Any
from ..registries.tools import tool
from ..core.schemas import table_schema
from ..r_integration import execute_r_script


@tool(
    name="summary_stats",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "group_by": {"type": "string"},
            "percentiles": {"type": "array", "items": {"type": "number"}, "default": [0.25, 0.5, 0.75]}
        },
        "required": ["data"]
    },
    description="Comprehensive descriptive statistics with optional grouping"
)
async def summary_stats(context, params):
    """Compute comprehensive descriptive statistics."""
    
    await context.info("Computing summary statistics")
    
    r_script = '''
    if (!require(dplyr)) install.packages("dplyr", quietly = TRUE)
    library(dplyr)
    
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
    }
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Summary statistics computed successfully")
        return result
        
    except Exception as e:
        await context.error("Summary statistics failed", error=str(e))
        raise


@tool(
    name="outlier_detection",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variable": {"type": "string"},
            "method": {"type": "string", "enum": ["iqr", "z_score", "modified_z"], "default": "iqr"},
            "threshold": {"type": "number", "minimum": 0, "default": 3.0}
        },
        "required": ["data", "variable"]
    },
    description="Detect outliers using IQR, Z-score, or Modified Z-score methods"
)
async def outlier_detection(context, params):
    """Detect outliers in data."""
    
    await context.info("Detecting outliers")
    
    r_script = '''
    data <- as.data.frame(args$data)
    variable <- args$variable
    method <- args$method %||% "iqr"
    threshold <- args$threshold %||% 3.0
    
    values <- data[[variable]]
    values_clean <- values[!is.na(values)]
    
    if (method == "iqr") {
        Q1 <- quantile(values_clean, 0.25)
        Q3 <- quantile(values_clean, 0.75)
        IQR <- Q3 - Q1
        lower_bound <- Q1 - 1.5 * IQR
        upper_bound <- Q3 + 1.5 * IQR
        outliers <- which(values < lower_bound | values > upper_bound)
        
        bounds <- list(lower = lower_bound, upper = upper_bound, iqr = IQR)
        
    } else if (method == "z_score") {
        mean_val <- mean(values_clean)
        sd_val <- sd(values_clean)
        z_scores <- abs((values - mean_val) / sd_val)
        outliers <- which(z_scores > threshold)
        
        bounds <- list(threshold = threshold, mean = mean_val, sd = sd_val)
        
    } else if (method == "modified_z") {
        median_val <- median(values_clean)
        mad_val <- mad(values_clean)
        modified_z <- abs(0.6745 * (values - median_val) / mad_val)
        outliers <- which(modified_z > threshold)
        
        bounds <- list(threshold = threshold, median = median_val, mad = mad_val)
    }
    
    result <- list(
        method = method,
        outlier_indices = outliers,
        outlier_values = values[outliers],
        n_outliers = length(outliers),
        n_obs = length(values[!is.na(values)]),
        outlier_percentage = length(outliers) / length(values_clean) * 100,
        bounds = bounds,
        variable = variable
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Outlier detection completed successfully")
        return result
        
    except Exception as e:
        await context.error("Outlier detection failed", error=str(e))
        raise


@tool(
    name="frequency_table",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "include_percentages": {"type": "boolean", "default": True},
            "sort_by": {"type": "string", "enum": ["frequency", "value"], "default": "frequency"}
        },
        "required": ["data", "variables"]
    },
    description="Generate frequency tables with counts and percentages"
)
async def frequency_table(context, params):
    """Generate frequency tables."""
    
    await context.info("Creating frequency tables")
    
    r_script = '''
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
        variables = variables,
        total_observations = nrow(data)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Frequency tables created successfully")
        return result
        
    except Exception as e:
        await context.error("Frequency table creation failed", error=str(e))
        raise