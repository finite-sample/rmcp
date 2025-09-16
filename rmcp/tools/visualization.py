"""
Visualization tools for RMCP.

Statistical plotting and data visualization capabilities.
"""

from typing import Dict, Any
from ..registries.tools import tool
from ..core.schemas import table_schema, formula_schema
from ..r_integration import execute_r_script


@tool(
    name="scatter_plot",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "x": {"type": "string"},
            "y": {"type": "string"},
            "group": {"type": "string"},
            "title": {"type": "string"},
            "file_path": {"type": "string"},
            "width": {"type": "integer", "minimum": 100, "default": 800},
            "height": {"type": "integer", "minimum": 100, "default": 600}
        },
        "required": ["data", "x", "y", "file_path"]
    },
    description="Create scatter plot with optional grouping and trend lines"
)
async def scatter_plot(context, params):
    """Create scatter plot."""
    
    await context.info("Creating scatter plot")
    
    r_script = '''
    if (!require(ggplot2)) install.packages("ggplot2", quietly = TRUE)
    library(ggplot2)
    
    data <- as.data.frame(args$data)
    x_var <- args$x
    y_var <- args$y
    group_var <- args$group
    title <- args$title %||% paste("Scatter plot:", y_var, "vs", x_var)
    file_path <- args$file_path
    width <- args$width %||% 800
    height <- args$height %||% 600
    
    # Create base plot
    p <- ggplot(data, aes_string(x = x_var, y = y_var))
    
    if (!is.null(group_var)) {
        p <- p + geom_point(aes_string(color = group_var), alpha = 0.7) +
             geom_smooth(aes_string(color = group_var), method = "lm", se = TRUE)
    } else {
        p <- p + geom_point(alpha = 0.7) +
             geom_smooth(method = "lm", se = TRUE, color = "blue")
    }
    
    p <- p + labs(title = title, x = x_var, y = y_var) +
         theme_minimal() +
         theme(plot.title = element_text(hjust = 0.5))
    
    # Save plot
    ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
    
    # Basic correlation
    correlation <- cor(data[[x_var]], data[[y_var]], use = "complete.obs")
    
    result <- list(
        file_path = file_path,
        x_variable = x_var,
        y_variable = y_var,
        group_variable = group_var,
        correlation = correlation,
        title = title,
        n_points = sum(!is.na(data[[x_var]]) & !is.na(data[[y_var]])),
        plot_saved = file.exists(file_path)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Scatter plot created successfully")
        return result
        
    except Exception as e:
        await context.error("Scatter plot creation failed", error=str(e))
        raise


@tool(
    name="histogram",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variable": {"type": "string"},
            "group": {"type": "string"},
            "bins": {"type": "integer", "minimum": 5, "maximum": 100, "default": 30},
            "title": {"type": "string"},
            "file_path": {"type": "string"},
            "width": {"type": "integer", "minimum": 100, "default": 800},
            "height": {"type": "integer", "minimum": 100, "default": 600}
        },
        "required": ["data", "variable", "file_path"]
    },
    description="Create histogram with optional grouping and density overlay"
)
async def histogram(context, params):
    """Create histogram."""
    
    await context.info("Creating histogram")
    
    r_script = '''
    if (!require(ggplot2)) install.packages("ggplot2", quietly = TRUE)
    library(ggplot2)
    
    data <- as.data.frame(args$data)
    variable <- args$variable
    group_var <- args$group
    bins <- args$bins %||% 30
    title <- args$title %||% paste("Histogram of", variable)
    file_path <- args$file_path
    width <- args$width %||% 800
    height <- args$height %||% 600
    
    # Create base plot
    p <- ggplot(data, aes_string(x = variable))
    
    if (!is.null(group_var)) {
        p <- p + geom_histogram(aes_string(fill = group_var), bins = bins, alpha = 0.7, position = "identity") +
             geom_density(aes_string(color = group_var), alpha = 0.8)
    } else {
        p <- p + geom_histogram(bins = bins, alpha = 0.7, fill = "steelblue") +
             geom_density(alpha = 0.8, color = "red")
    }
    
    p <- p + labs(title = title, x = variable, y = "Frequency") +
         theme_minimal() +
         theme(plot.title = element_text(hjust = 0.5))
    
    # Save plot
    ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
    
    # Basic statistics
    values <- data[[variable]][!is.na(data[[variable]])]
    stats <- list(
        mean = mean(values),
        median = median(values),
        sd = sd(values),
        skewness = (sum((values - mean(values))^3) / length(values)) / (sd(values)^3),
        kurtosis = (sum((values - mean(values))^4) / length(values)) / (sd(values)^4) - 3
    )
    
    result <- list(
        file_path = file_path,
        variable = variable,
        group_variable = group_var,
        bins = bins,
        statistics = stats,
        title = title,
        n_obs = length(values),
        plot_saved = file.exists(file_path)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Histogram created successfully")
        return result
        
    except Exception as e:
        await context.error("Histogram creation failed", error=str(e))
        raise


@tool(
    name="boxplot",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variable": {"type": "string"},
            "group": {"type": "string"},
            "title": {"type": "string"},
            "file_path": {"type": "string"},
            "width": {"type": "integer", "minimum": 100, "default": 800},
            "height": {"type": "integer", "minimum": 100, "default": 600}
        },
        "required": ["data", "variable", "file_path"]
    },
    description="Create box plot with optional grouping"
)
async def boxplot(context, params):
    """Create box plot."""
    
    await context.info("Creating box plot")
    
    r_script = '''
    if (!require(ggplot2)) install.packages("ggplot2", quietly = TRUE)
    library(ggplot2)
    
    data <- as.data.frame(args$data)
    variable <- args$variable
    group_var <- args$group
    title <- args$title %||% paste("Box plot of", variable)
    file_path <- args$file_path
    width <- args$width %||% 800
    height <- args$height %||% 600
    
    # Create plot
    if (!is.null(group_var)) {
        p <- ggplot(data, aes_string(x = group_var, y = variable, fill = group_var)) +
             geom_boxplot(alpha = 0.7) +
             geom_jitter(width = 0.2, alpha = 0.5) +
             labs(title = title, x = group_var, y = variable)
    } else {
        p <- ggplot(data, aes_string(y = variable)) +
             geom_boxplot(fill = "steelblue", alpha = 0.7) +
             geom_jitter(width = 0.1, alpha = 0.5) +
             labs(title = title, x = "", y = variable)
    }
    
    p <- p + theme_minimal() +
         theme(plot.title = element_text(hjust = 0.5))
    
    # Save plot
    ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
    
    # Summary statistics
    if (!is.null(group_var)) {
        stats <- by(data[[variable]], data[[group_var]], function(x) {
            x_clean <- x[!is.na(x)]
            list(
                median = median(x_clean),
                q1 = quantile(x_clean, 0.25),
                q3 = quantile(x_clean, 0.75),
                iqr = IQR(x_clean),
                n = length(x_clean),
                outliers = length(boxplot.stats(x_clean)$out)
            )
        })
        summary_stats <- lapply(stats, identity)
    } else {
        x_clean <- data[[variable]][!is.na(data[[variable]])]
        summary_stats <- list(
            overall = list(
                median = median(x_clean),
                q1 = quantile(x_clean, 0.25),
                q3 = quantile(x_clean, 0.75),
                iqr = IQR(x_clean),
                n = length(x_clean),
                outliers = length(boxplot.stats(x_clean)$out)
            )
        )
    }
    
    result <- list(
        file_path = file_path,
        variable = variable,
        group_variable = group_var,
        summary_statistics = summary_stats,
        title = title,
        plot_saved = file.exists(file_path)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Box plot created successfully")
        return result
        
    except Exception as e:
        await context.error("Box plot creation failed", error=str(e))
        raise


@tool(
    name="time_series_plot",
    input_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "properties": {
                    "values": {"type": "array", "items": {"type": "number"}},
                    "dates": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["values"]
            },
            "title": {"type": "string"},
            "file_path": {"type": "string"},
            "show_trend": {"type": "boolean", "default": True},
            "width": {"type": "integer", "minimum": 100, "default": 1000},
            "height": {"type": "integer", "minimum": 100, "default": 600}
        },
        "required": ["data", "file_path"]
    },
    description="Create time series plot with optional trend line"
)
async def time_series_plot(context, params):
    """Create time series plot."""
    
    await context.info("Creating time series plot")
    
    r_script = '''
    if (!require(ggplot2)) install.packages("ggplot2", quietly = TRUE)
    library(ggplot2)
    
    values <- args$data$values
    dates <- args$data$dates
    title <- args$title %||% "Time Series Plot"
    file_path <- args$file_path
    show_trend <- args$show_trend %||% TRUE
    width <- args$width %||% 1000
    height <- args$height %||% 600
    
    # Create time index if dates not provided
    if (is.null(dates)) {
        time_index <- 1:length(values)
        x_label <- "Time Index"
    } else {
        time_index <- as.Date(dates)
        x_label <- "Date"
    }
    
    # Create data frame
    ts_data <- data.frame(
        time = time_index,
        value = values
    )
    
    # Create plot
    p <- ggplot(ts_data, aes(x = time, y = value)) +
         geom_line(color = "steelblue", size = 1) +
         geom_point(alpha = 0.6, size = 1.5)
    
    if (show_trend) {
        p <- p + geom_smooth(method = "loess", se = TRUE, color = "red", alpha = 0.3)
    }
    
    p <- p + labs(title = title, x = x_label, y = "Value") +
         theme_minimal() +
         theme(plot.title = element_text(hjust = 0.5))
    
    # Save plot
    ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
    
    # Basic time series statistics
    ts_stats <- list(
        mean = mean(values, na.rm = TRUE),
        sd = sd(values, na.rm = TRUE),
        min = min(values, na.rm = TRUE),
        max = max(values, na.rm = TRUE),
        n_obs = length(values[!is.na(values)]),
        range = max(values, na.rm = TRUE) - min(values, na.rm = TRUE)
    )
    
    result <- list(
        file_path = file_path,
        title = title,
        statistics = ts_stats,
        has_dates = !is.null(dates),
        show_trend = show_trend,
        plot_saved = file.exists(file_path)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Time series plot created successfully")
        return result
        
    except Exception as e:
        await context.error("Time series plot creation failed", error=str(e))
        raise


@tool(
    name="correlation_heatmap",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "method": {"type": "string", "enum": ["pearson", "spearman", "kendall"], "default": "pearson"},
            "title": {"type": "string"},
            "file_path": {"type": "string"},
            "width": {"type": "integer", "minimum": 100, "default": 800},
            "height": {"type": "integer", "minimum": 100, "default": 800}
        },
        "required": ["data", "file_path"]
    },
    description="Create correlation heatmap matrix"
)
async def correlation_heatmap(context, params):
    """Create correlation heatmap."""
    
    await context.info("Creating correlation heatmap")
    
    r_script = '''
    if (!require(ggplot2)) install.packages("ggplot2", quietly = TRUE)
    if (!require(reshape2)) install.packages("reshape2", quietly = TRUE)
    library(ggplot2)
    library(reshape2)
    
    data <- as.data.frame(args$data)
    variables <- args$variables
    method <- args$method %||% "pearson"
    title <- args$title %||% paste("Correlation Heatmap (", method, ")")
    file_path <- args$file_path
    width <- args$width %||% 800
    height <- args$height %||% 800
    
    # Select variables
    if (is.null(variables)) {
        numeric_vars <- names(data)[sapply(data, is.numeric)]
        if (length(numeric_vars) == 0) {
            stop("No numeric variables found")
        }
        variables <- numeric_vars
    }
    
    # Calculate correlation matrix
    cor_data <- data[, variables, drop = FALSE]
    cor_matrix <- cor(cor_data, use = "complete.obs", method = method)
    
    # Melt for ggplot
    cor_melted <- melt(cor_matrix)
    colnames(cor_melted) <- c("Var1", "Var2", "value")
    
    # Create heatmap
    p <- ggplot(cor_melted, aes(Var1, Var2, fill = value)) +
         geom_tile(color = "white") +
         scale_fill_gradient2(low = "blue", high = "red", mid = "white", 
                             midpoint = 0, limit = c(-1, 1), space = "Lab",
                             name = "Correlation") +
         theme_minimal() +
         theme(axis.text.x = element_text(angle = 45, vjust = 1, size = 12, hjust = 1),
               plot.title = element_text(hjust = 0.5)) +
         coord_fixed() +
         labs(title = title, x = "", y = "") +
         geom_text(aes(label = round(value, 2)), color = "black", size = 3)
    
    # Save plot
    ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
    
    result <- list(
        file_path = file_path,
        correlation_matrix = as.matrix(cor_matrix),
        variables = variables,
        method = method,
        title = title,
        n_variables = length(variables),
        plot_saved = file.exists(file_path)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Correlation heatmap created successfully")
        return result
        
    except Exception as e:
        await context.error("Correlation heatmap creation failed", error=str(e))
        raise


@tool(
    name="regression_plot",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "formula": formula_schema(),
            "title": {"type": "string"},
            "file_path": {"type": "string"},
            "residual_plots": {"type": "boolean", "default": True},
            "width": {"type": "integer", "minimum": 100, "default": 1200},
            "height": {"type": "integer", "minimum": 100, "default": 800}
        },
        "required": ["data", "formula", "file_path"]
    },
    description="Create regression diagnostic plots (fitted vs residuals, Q-Q plot, etc.)"
)
async def regression_plot(context, params):
    """Create regression diagnostic plots."""
    
    await context.info("Creating regression plots")
    
    r_script = '''
    if (!require(ggplot2)) install.packages("ggplot2", quietly = TRUE)
    if (!require(gridExtra)) install.packages("gridExtra", quietly = TRUE)
    library(ggplot2)
    library(gridExtra)
    
    data <- as.data.frame(args$data)
    formula <- as.formula(args$formula)
    title <- args$title %||% "Regression Diagnostics"
    file_path <- args$file_path
    residual_plots <- args$residual_plots %||% TRUE
    width <- args$width %||% 1200
    height <- args$height %||% 800
    
    # Fit model
    model <- lm(formula, data = data)
    
    # Extract model data
    fitted_values <- fitted(model)
    residuals <- residuals(model)
    standardized_residuals <- rstandard(model)
    
    if (residual_plots) {
        # Create diagnostic plots
        p1 <- ggplot(data.frame(fitted = fitted_values, residuals = residuals), 
                     aes(x = fitted, y = residuals)) +
              geom_point(alpha = 0.6) +
              geom_hline(yintercept = 0, color = "red", linetype = "dashed") +
              geom_smooth(se = FALSE, color = "blue") +
              labs(title = "Residuals vs Fitted", x = "Fitted Values", y = "Residuals") +
              theme_minimal()
        
        p2 <- ggplot(data.frame(residuals = standardized_residuals), aes(sample = residuals)) +
              stat_qq() + stat_qq_line(color = "red") +
              labs(title = "Q-Q Plot", x = "Theoretical Quantiles", y = "Sample Quantiles") +
              theme_minimal()
        
        p3 <- ggplot(data.frame(fitted = fitted_values, sqrt_abs_residuals = sqrt(abs(standardized_residuals))), 
                     aes(x = fitted, y = sqrt_abs_residuals)) +
              geom_point(alpha = 0.6) +
              geom_smooth(se = FALSE, color = "red") +
              labs(title = "Scale-Location", x = "Fitted Values", y = "√|Standardized Residuals|") +
              theme_minimal()
        
        p4 <- ggplot(data.frame(leverage = hatvalues(model), std_residuals = standardized_residuals), 
                     aes(x = leverage, y = std_residuals)) +
              geom_point(alpha = 0.6) +
              geom_hline(yintercept = 0, color = "red", linetype = "dashed") +
              geom_smooth(se = FALSE, color = "blue") +
              labs(title = "Residuals vs Leverage", x = "Leverage", y = "Standardized Residuals") +
              theme_minimal()
        
        # Combine plots
        combined_plot <- grid.arrange(p1, p2, p3, p4, ncol = 2, 
                                     top = textGrob(title, gp = gpar(fontsize = 16, font = 2)))
        
        # Save combined plot
        ggsave(file_path, plot = combined_plot, width = width/100, height = height/100, dpi = 100)
        
    } else {
        # Simple fitted vs actual plot
        response_var <- all.vars(formula)[1]
        actual_values <- data[[response_var]]
        
        p <- ggplot(data.frame(actual = actual_values, fitted = fitted_values), 
                   aes(x = actual, y = fitted)) +
             geom_point(alpha = 0.6) +
             geom_abline(intercept = 0, slope = 1, color = "red", linetype = "dashed") +
             labs(title = title, x = "Actual Values", y = "Fitted Values") +
             theme_minimal() +
             theme(plot.title = element_text(hjust = 0.5))
        
        ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
    }
    
    # Model summary
    model_summary <- summary(model)
    
    result <- list(
        file_path = file_path,
        title = title,
        r_squared = model_summary$r.squared,
        adj_r_squared = model_summary$adj.r.squared,
        residual_se = model_summary$sigma,
        formula = deparse(formula),
        residual_plots = residual_plots,
        n_obs = nobs(model),
        plot_saved = file.exists(file_path)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Regression plots created successfully")
        return result
        
    except Exception as e:
        await context.error("Regression plot creation failed", error=str(e))
        raise