"""
Data transformation tools for RMCP.

Essential data manipulation and cleaning capabilities.
"""

from typing import Dict, Any
from ..registries.tools import tool
from ..core.schemas import table_schema
from ..r_integration import execute_r_script


@tool(
    name="lag_lead",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "lags": {"type": "array", "items": {"type": "integer"}},
            "leads": {"type": "array", "items": {"type": "integer"}}
        },
        "required": ["data", "variables"]
    },
    description="Create lagged and lead variables for time series analysis"
)
async def lag_lead(context, params):
    """Create lagged and lead variables."""
    
    await context.info("Creating lag/lead variables")
    
    r_script = '''
    data <- as.data.frame(args$data)
    variables <- args$variables
    lags <- args$lags %||% c(1)
    leads <- args$leads %||% c()
    
    result_data <- data
    
    # Create lagged variables
    for (var in variables) {
        for (lag_val in lags) {
            new_var <- paste0(var, "_lag", lag_val)
            result_data[[new_var]] <- c(rep(NA, lag_val), head(data[[var]], -lag_val))
        }
    }
    
    # Create lead variables  
    for (var in variables) {
        for (lead_val in leads) {
            new_var <- paste0(var, "_lead", lead_val)
            result_data[[new_var]] <- c(tail(data[[var]], -lead_val), rep(NA, lead_val))
        }
    }
    
    result <- list(
        data = result_data,
        variables_created = names(result_data)[!names(result_data) %in% names(data)],
        n_obs = nrow(result_data),
        operation = "lag_lead"
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Lag/lead variables created successfully")
        return result
        
    except Exception as e:
        await context.error("Lag/lead creation failed", error=str(e))
        raise


@tool(
    name="winsorize",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "percentiles": {
                "type": "array",
                "items": {"type": "number", "minimum": 0, "maximum": 0.5},
                "minItems": 2,
                "maxItems": 2,
                "default": [0.01, 0.99]
            }
        },
        "required": ["data", "variables"]
    },
    description="Winsorize variables to handle outliers"
)
async def winsorize(context, params):
    """Winsorize variables to handle outliers."""
    
    await context.info("Winsorizing variables")
    
    r_script = '''
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
        data = result_data,
        outliers_summary = outliers_summary,
        percentiles = percentiles,
        variables_winsorized = variables,
        n_obs = nrow(result_data)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Variables winsorized successfully")
        return result
        
    except Exception as e:
        await context.error("Winsorization failed", error=str(e))
        raise


@tool(
    name="difference",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "order": {"type": "integer", "minimum": 1, "maximum": 3, "default": 1},
            "log_transform": {"type": "boolean", "default": False}
        },
        "required": ["data", "variables"]
    },
    description="Compute differences of variables (for stationarity)"
)
async def difference(context, params):
    """Compute differences of variables."""
    
    await context.info("Computing variable differences")
    
    r_script = '''
    data <- as.data.frame(args$data)
    variables <- args$variables
    diff_order <- args$order %||% 1
    log_transform <- args$log_transform %||% FALSE
    
    result_data <- data
    
    for (var in variables) {
        original_values <- data[[var]]
        
        # Log transform first if requested
        if (log_transform) {
            if (any(original_values <= 0, na.rm = TRUE)) {
                stop(paste("Cannot log-transform", var, "- contains non-positive values"))
            }
            transformed <- log(original_values)
            log_var <- paste0("log_", var)
            result_data[[log_var]] <- transformed
            working_values <- transformed
            base_name <- log_var
        } else {
            working_values <- original_values
            base_name <- var
        }
        
        # Compute differences
        diff_values <- working_values
        for (i in 1:diff_order) {
            diff_values <- diff(diff_values)
            diff_name <- paste0(base_name, "_diff", if (diff_order > 1) i else "")
            
            # Pad with NA to maintain same length
            padded_diff <- c(rep(NA, i), diff_values)
            result_data[[diff_name]] <- padded_diff
        }
    }
    
    result <- list(
        data = result_data,
        variables_differenced = variables,
        difference_order = diff_order,
        log_transformed = log_transform,
        n_obs = nrow(result_data)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Variable differences computed successfully")
        return result
        
    except Exception as e:
        await context.error("Differencing failed", error=str(e))
        raise


@tool(
    name="standardize",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "method": {"type": "string", "enum": ["z_score", "min_max", "robust"], "default": "z_score"}
        },
        "required": ["data", "variables"]
    },
    description="Standardize variables using z-score, min-max, or robust scaling"
)
async def standardize(context, params):
    """Standardize variables."""
    
    await context.info("Standardizing variables")
    
    r_script = '''
    data <- as.data.frame(args$data)
    variables <- args$variables
    method <- args$method %||% "z_score"
    
    result_data <- data
    scaling_info <- list()
    
    for (var in variables) {
        original_values <- data[[var]]
        
        if (method == "z_score") {
            mean_val <- mean(original_values, na.rm = TRUE)
            sd_val <- sd(original_values, na.rm = TRUE)
            scaled <- (original_values - mean_val) / sd_val
            scaling_info[[var]] <- list(mean = mean_val, sd = sd_val)
            
        } else if (method == "min_max") {
            min_val <- min(original_values, na.rm = TRUE)
            max_val <- max(original_values, na.rm = TRUE)
            scaled <- (original_values - min_val) / (max_val - min_val)
            scaling_info[[var]] <- list(min = min_val, max = max_val)
            
        } else if (method == "robust") {
            median_val <- median(original_values, na.rm = TRUE)
            mad_val <- mad(original_values, na.rm = TRUE)
            scaled <- (original_values - median_val) / mad_val
            scaling_info[[var]] <- list(median = median_val, mad = mad_val)
        }
        
        new_var <- paste0(var, "_", method)
        result_data[[new_var]] <- scaled
    }
    
    result <- list(
        data = result_data,
        scaling_method = method,
        scaling_info = scaling_info,
        variables_scaled = variables,
        n_obs = nrow(result_data)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Variables standardized successfully")
        return result
        
    except Exception as e:
        await context.error("Standardization failed", error=str(e))
        raise