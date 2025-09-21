"""
Visualization tools for RMCP.

Statistical plotting and data visualization capabilities.
"""

from typing import Any

from ..core.schemas import formula_schema, table_schema
from ..r_integration import execute_r_script_with_image_async
from ..registries.tools import tool


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
            "file_path": {
                "type": "string",
                "description": "Optional: Save plot to this file",
            },
            "return_image": {
                "type": "boolean",
                "default": True,
                "description": "Return image data for inline display",
            },
            "width": {"type": "integer", "minimum": 100, "default": 800},
            "height": {"type": "integer", "minimum": 100, "default": 600},
        },
        "required": ["data", "x", "y"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["scatter_plot"],
                "description": "Type of plot generated",
            },
            "variables": {
                "type": "object",
                "properties": {
                    "x": {"type": "string"},
                    "y": {"type": "string"},
                    "group": {"type": ["string", "null"]},
                },
                "required": ["x", "y"],
                "description": "Variables plotted",
            },
            "statistics": {
                "type": "object",
                "properties": {
                    "correlation": {"type": "number"},
                    "n_points": {"type": "integer"},
                    "trend_line": {
                        "type": "object",
                        "properties": {
                            "slope": {"type": "number"},
                            "intercept": {"type": "number"},
                            "r_squared": {"type": "number"},
                        },
                    },
                },
                "description": "Statistical summary of the plot",
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "description": "Plot dimensions in pixels",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded PNG image data",
            },
            "image_mime_type": {
                "type": "string",
                "enum": ["image/png"],
                "description": "MIME type of the image",
            },
        },
        "required": ["plot_type", "variables"],
        "additionalProperties": False,
    },
    description="Create scatter plot with optional grouping and trend lines",
)
async def scatter_plot(context, params) -> dict[str, Any]:
    """Create scatter plot."""

    await context.info("Creating scatter plot")

    r_script = """
    # Set CRAN mirror
    options(repos = c(CRAN = "https://cloud.r-project.org/"))
    
    library(ggplot2)
    
    data <- as.data.frame(args$data)
    x_var <- args$x
    y_var <- args$y
    group_var <- args$group
    title <- args$title %||% paste("Scatter plot:", y_var, "vs", x_var)
    file_path <- args$file_path
    return_image <- args$return_image %||% TRUE
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
    
    # Save to file if path provided
    if (!is.null(file_path)) {
        ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
        plot_saved <- file.exists(file_path)
    } else {
        plot_saved <- FALSE
    }
    
    # Basic correlation
    correlation <- cor(data[[x_var]], data[[y_var]], use = "complete.obs")
    
    # Prepare result
    result <- list(
        x_variable = x_var,
        y_variable = y_var,
        group_variable = group_var,
        correlation = correlation,
        title = title,
        n_points = sum(!is.na(data[[x_var]]) & !is.na(data[[y_var]])),
        plot_saved = plot_saved
    )
    
    # Add file path if provided
    if (!is.null(file_path)) {
        result$file_path <- file_path
    }
    
    # Generate base64 image if requested
    if (return_image) {
        image_data <- safe_encode_plot(p, width, height)
        if (!is.null(image_data)) {
            result$image_data <- image_data
        }
    }
    """

    try:
        # Use the new image-enabled function
        return_image = params.get("return_image", True)
        width = params.get("width", 800)
        height = params.get("height", 600)

        result = await execute_r_script_with_image_async(
            r_script,
            params,
            include_image=return_image,
            image_width=width,
            image_height=height,
        )

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
            "file_path": {
                "type": "string",
                "description": "Optional: Save plot to this file",
            },
            "return_image": {
                "type": "boolean",
                "default": True,
                "description": "Return image data for inline display",
            },
            "width": {"type": "integer", "minimum": 100, "default": 800},
            "height": {"type": "integer", "minimum": 100, "default": 600},
        },
        "required": ["data", "variable"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["histogram"],
                "description": "Type of plot generated",
            },
            "variable": {
                "type": "string",
                "description": "Variable analyzed in histogram",
            },
            "group_variable": {
                "type": ["string", "null"],
                "description": "Grouping variable if specified",
            },
            "bins": {
                "type": "integer",
                "description": "Number of bins used in histogram",
            },
            "statistics": {
                "type": "object",
                "properties": {
                    "mean": {"type": "number"},
                    "median": {"type": "number"},
                    "sd": {"type": "number"},
                    "skewness": {"type": "number"},
                    "kurtosis": {"type": "number"},
                },
                "description": "Descriptive statistics for the variable",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of valid observations",
                "minimum": 0,
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "description": "Plot dimensions in pixels",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded PNG image data",
            },
            "image_mime_type": {
                "type": "string",
                "enum": ["image/png"],
                "description": "MIME type of the image",
            },
        },
        "required": ["plot_type", "variable", "bins", "statistics", "n_obs"],
        "additionalProperties": False,
    },
    description="Create histogram with optional grouping and density overlay",
)
async def histogram(context, params) -> dict[str, Any]:
    """Create histogram."""

    await context.info("Creating histogram")

    r_script = """
    # Set CRAN mirror
    options(repos = c(CRAN = "https://cloud.r-project.org/"))
    
    library(ggplot2)
    
    data <- as.data.frame(args$data)
    variable <- args$variable
    group_var <- args$group
    bins <- args$bins %||% 30
    title <- args$title %||% paste("Histogram of", variable)
    file_path <- args$file_path
    return_image <- args$return_image %||% TRUE
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
    
    # Save to file if path provided
    if (!is.null(file_path)) {
        ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
        plot_saved <- file.exists(file_path)
    } else {
        plot_saved <- FALSE
    }
    
    # Basic statistics
    values <- data[[variable]][!is.na(data[[variable]])]
    stats <- list(
        mean = mean(values),
        median = median(values),
        sd = sd(values),
        skewness = (sum((values - mean(values))^3) / length(values)) / (sd(values)^3),
        kurtosis = (sum((values - mean(values))^4) / length(values)) / (sd(values)^4) - 3
    )
    
    # Prepare result
    result <- list(
        variable = variable,
        group_variable = group_var,
        bins = bins,
        statistics = stats,
        title = title,
        n_obs = length(values),
        plot_saved = plot_saved
    )
    
    # Add file path if provided
    if (!is.null(file_path)) {
        result$file_path <- file_path
    }
    
    # Generate base64 image if requested
    if (return_image) {
        image_data <- safe_encode_plot(p, width, height)
        if (!is.null(image_data)) {
            result$image_data <- image_data
        }
    }
    """

    try:
        # Use the new image-enabled function
        return_image = params.get("return_image", True)
        width = params.get("width", 800)
        height = params.get("height", 600)

        result = await execute_r_script_with_image_async(
            r_script,
            params,
            include_image=return_image,
            image_width=width,
            image_height=height,
        )

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
            "file_path": {
                "type": "string",
                "description": "Optional: Save plot to this file",
            },
            "return_image": {
                "type": "boolean",
                "default": True,
                "description": "Return image data for inline display",
            },
            "width": {"type": "integer", "minimum": 100, "default": 800},
            "height": {"type": "integer", "minimum": 100, "default": 600},
        },
        "required": ["data", "variable"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["boxplot"],
                "description": "Type of plot generated",
            },
            "variable": {
                "type": "string",
                "description": "Variable analyzed in boxplot",
            },
            "group_variable": {
                "type": ["string", "null"],
                "description": "Grouping variable if specified",
            },
            "summary_statistics": {
                "type": "object",
                "description": "Quartile statistics by group or overall",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "median": {"type": "number"},
                        "q1": {"type": "number"},
                        "q3": {"type": "number"},
                        "iqr": {"type": "number"},
                        "n": {"type": "integer"},
                        "outliers": {"type": "integer"},
                    },
                },
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "description": "Plot dimensions in pixels",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded PNG image data",
            },
            "image_mime_type": {
                "type": "string",
                "enum": ["image/png"],
                "description": "MIME type of the image",
            },
        },
        "required": ["plot_type", "variable", "summary_statistics"],
        "additionalProperties": False,
    },
    description="Create box plot with optional grouping",
)
async def boxplot(context, params) -> dict[str, Any]:
    """Create box plot."""

    await context.info("Creating box plot")

    r_script = """
    # Set CRAN mirror
    options(repos = c(CRAN = "https://cloud.r-project.org/"))
    
    library(ggplot2)
    
    data <- as.data.frame(args$data)
    variable <- args$variable
    group_var <- args$group
    title <- args$title %||% paste("Box plot of", variable)
    file_path <- args$file_path
    return_image <- args$return_image %||% TRUE
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
    
    # Save to file if path provided
    if (!is.null(file_path)) {
        ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
        plot_saved <- file.exists(file_path)
    } else {
        plot_saved <- FALSE
    }
    
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
    
    # Prepare result
    result <- list(
        variable = variable,
        group_variable = group_var,
        summary_statistics = summary_stats,
        title = title,
        plot_saved = plot_saved
    )
    
    # Add file path if provided
    if (!is.null(file_path)) {
        result$file_path <- file_path
    }
    
    # Generate base64 image if requested
    if (return_image) {
        image_data <- safe_encode_plot(p, width, height)
        if (!is.null(image_data)) {
            result$image_data <- image_data
        }
    }
    """

    try:
        # Use the new image-enabled function
        return_image = params.get("return_image", True)
        width = params.get("width", 800)
        height = params.get("height", 600)

        result = await execute_r_script_with_image_async(
            r_script,
            params,
            include_image=return_image,
            image_width=width,
            image_height=height,
        )

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
                    "dates": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["values"],
            },
            "title": {"type": "string"},
            "file_path": {
                "type": "string",
                "description": "Optional: Save plot to this file",
            },
            "return_image": {
                "type": "boolean",
                "default": True,
                "description": "Return image data for inline display",
            },
            "show_trend": {"type": "boolean", "default": True},
            "width": {"type": "integer", "minimum": 100, "default": 1000},
            "height": {"type": "integer", "minimum": 100, "default": 600},
        },
        "required": ["data"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["time_series_plot"],
                "description": "Type of plot generated",
            },
            "statistics": {
                "type": "object",
                "properties": {
                    "mean": {"type": "number"},
                    "sd": {"type": "number"},
                    "min": {"type": "number"},
                    "max": {"type": "number"},
                    "range": {"type": "number"},
                    "n_obs": {"type": "integer"},
                },
                "description": "Time series descriptive statistics",
            },
            "has_dates": {
                "type": "boolean",
                "description": "Whether date information was provided",
            },
            "show_trend": {
                "type": "boolean",
                "description": "Whether trend line was included",
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "description": "Plot dimensions in pixels",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded PNG image data",
            },
            "image_mime_type": {
                "type": "string",
                "enum": ["image/png"],
                "description": "MIME type of the image",
            },
        },
        "required": ["plot_type", "statistics", "has_dates", "show_trend"],
        "additionalProperties": False,
    },
    description="Create time series plot with optional trend line",
)
async def time_series_plot(context, params) -> dict[str, Any]:
    """Create time series plot."""

    await context.info("Creating time series plot")

    r_script = """
    # Set CRAN mirror
    options(repos = c(CRAN = "https://cloud.r-project.org/"))
    
    library(ggplot2)
    
    values <- args$data$values
    dates <- args$data$dates
    title <- args$title %||% "Time Series Plot"
    file_path <- args$file_path
    return_image <- args$return_image %||% TRUE
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
    
    # Save to file if path provided
    if (!is.null(file_path)) {
        ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
        plot_saved <- file.exists(file_path)
    } else {
        plot_saved <- FALSE
    }
    
    # Basic time series statistics
    ts_stats <- list(
        mean = mean(values, na.rm = TRUE),
        sd = sd(values, na.rm = TRUE),
        min = min(values, na.rm = TRUE),
        max = max(values, na.rm = TRUE),
        n_obs = length(values[!is.na(values)]),
        range = max(values, na.rm = TRUE) - min(values, na.rm = TRUE)
    )
    
    # Prepare result
    result <- list(
        title = title,
        statistics = ts_stats,
        has_dates = !is.null(dates),
        show_trend = show_trend,
        plot_saved = plot_saved
    )
    
    # Add file path if provided
    if (!is.null(file_path)) {
        result$file_path <- file_path
    }
    
    # Generate base64 image if requested
    if (return_image) {
        image_data <- safe_encode_plot(p, width, height)
        if (!is.null(image_data)) {
            result$image_data <- image_data
        }
    }
    """

    try:
        # Use the new image-enabled function
        return_image = params.get("return_image", True)
        width = params.get("width", 1000)
        height = params.get("height", 600)

        result = await execute_r_script_with_image_async(
            r_script,
            params,
            include_image=return_image,
            image_width=width,
            image_height=height,
        )

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
            "method": {
                "type": "string",
                "enum": ["pearson", "spearman", "kendall"],
                "default": "pearson",
            },
            "title": {"type": "string"},
            "file_path": {
                "type": "string",
                "description": "Optional: Save plot to this file",
            },
            "return_image": {
                "type": "boolean",
                "default": True,
                "description": "Return image data for inline display",
            },
            "width": {"type": "integer", "minimum": 100, "default": 800},
            "height": {"type": "integer", "minimum": 100, "default": 800},
        },
        "required": ["data"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["correlation_heatmap"],
                "description": "Type of plot generated",
            },
            "correlation_matrix": {
                "type": "object",
                "description": "Correlation coefficients between variables",
                "additionalProperties": {"type": "array", "items": {"type": "number"}},
            },
            "variables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables included in correlation matrix",
            },
            "method": {
                "type": "string",
                "enum": ["pearson", "spearman", "kendall"],
                "description": "Correlation method used",
            },
            "n_variables": {
                "type": "integer",
                "description": "Number of variables in correlation matrix",
                "minimum": 2,
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "description": "Plot dimensions in pixels",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded PNG image data",
            },
            "image_mime_type": {
                "type": "string",
                "enum": ["image/png"],
                "description": "MIME type of the image",
            },
        },
        "required": [
            "plot_type",
            "correlation_matrix",
            "variables",
            "method",
            "n_variables",
        ],
        "additionalProperties": False,
    },
    description="Create correlation heatmap matrix",
)
async def correlation_heatmap(context, params) -> dict[str, Any]:
    """Create correlation heatmap."""

    await context.info("Creating correlation heatmap")

    r_script = """
    # Set CRAN mirror
    options(repos = c(CRAN = "https://cloud.r-project.org/"))
    
    library(ggplot2)
    library(reshape2)
    
    data <- as.data.frame(args$data)
    variables <- args$variables
    method <- args$method %||% "pearson"
    title <- args$title %||% paste("Correlation Heatmap (", method, ")")
    file_path <- args$file_path
    return_image <- args$return_image %||% TRUE
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
    
    # Save to file if path provided
    if (!is.null(file_path)) {
        ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
        plot_saved <- file.exists(file_path)
    } else {
        plot_saved <- FALSE
    }
    
    # Prepare result
    result <- list(
        correlation_matrix = as.matrix(cor_matrix),
        variables = variables,
        method = method,
        title = title,
        n_variables = length(variables),
        plot_saved = plot_saved
    )
    
    # Add file path if provided
    if (!is.null(file_path)) {
        result$file_path <- file_path
    }
    
    # Generate base64 image if requested
    if (return_image) {
        image_data <- safe_encode_plot(p, width, height)
        if (!is.null(image_data)) {
            result$image_data <- image_data
        }
    }
    """

    try:
        # Use the new image-enabled function
        return_image = params.get("return_image", True)
        width = params.get("width", 800)
        height = params.get("height", 800)

        result = await execute_r_script_with_image_async(
            r_script,
            params,
            include_image=return_image,
            image_width=width,
            image_height=height,
        )

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
            "file_path": {
                "type": "string",
                "description": "Optional: Save plot to this file",
            },
            "return_image": {
                "type": "boolean",
                "default": True,
                "description": "Return image data for inline display",
            },
            "residual_plots": {"type": "boolean", "default": True},
            "width": {"type": "integer", "minimum": 100, "default": 1200},
            "height": {"type": "integer", "minimum": 100, "default": 800},
        },
        "required": ["data", "formula"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["regression_plot"],
                "description": "Type of plot generated",
            },
            "r_squared": {
                "type": "number",
                "description": "R-squared value of the regression model",
                "minimum": 0,
                "maximum": 1,
            },
            "adj_r_squared": {
                "type": "number",
                "description": "Adjusted R-squared value",
                "maximum": 1,
            },
            "residual_se": {
                "type": "number",
                "description": "Residual standard error",
                "minimum": 0,
            },
            "formula": {"type": "string", "description": "Regression formula used"},
            "residual_plots": {
                "type": "boolean",
                "description": "Whether diagnostic plots were generated",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations in the model",
                "minimum": 1,
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "description": "Plot dimensions in pixels",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded PNG image data",
            },
            "image_mime_type": {
                "type": "string",
                "enum": ["image/png"],
                "description": "MIME type of the image",
            },
        },
        "required": [
            "plot_type",
            "r_squared",
            "adj_r_squared",
            "residual_se",
            "formula",
            "residual_plots",
            "n_obs",
        ],
        "additionalProperties": False,
    },
    description="Create regression diagnostic plots (fitted vs residuals, Q-Q plot, etc.)",
)
async def regression_plot(context, params) -> dict[str, Any]:
    """Create regression diagnostic plots."""

    await context.info("Creating regression plots")

    r_script = """
    # Set CRAN mirror
    options(repos = c(CRAN = "https://cloud.r-project.org/"))
    
    library(ggplot2)
    library(gridExtra)
    
    data <- as.data.frame(args$data)
    formula <- as.formula(args$formula)
    title <- args$title %||% "Regression Diagnostics"
    file_path <- args$file_path
    return_image <- args$return_image %||% TRUE
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
        
        # Save to file if path provided
        if (!is.null(file_path)) {
            ggsave(file_path, plot = combined_plot, width = width/100, height = height/100, dpi = 100)
            plot_saved <- file.exists(file_path)
        } else {
            plot_saved <- FALSE
        }
        
        # For image encoding, use the combined plot
        main_plot <- combined_plot
        
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
        
        # Save to file if path provided
        if (!is.null(file_path)) {
            ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
            plot_saved <- file.exists(file_path)
        } else {
            plot_saved <- FALSE
        }
        
        # For image encoding, use the simple plot
        main_plot <- p
    }
    
    # Model summary
    model_summary <- summary(model)
    
    # Prepare result
    result <- list(
        title = title,
        r_squared = model_summary$r.squared,
        adj_r_squared = model_summary$adj.r.squared,
        residual_se = model_summary$sigma,
        formula = deparse(formula),
        residual_plots = residual_plots,
        n_obs = nobs(model),
        plot_saved = plot_saved
    )
    
    # Add file path if provided
    if (!is.null(file_path)) {
        result$file_path <- file_path
    }
    
    # Generate base64 image if requested
    if (return_image) {
        image_data <- safe_encode_plot(main_plot, width, height)
        if (!is.null(image_data)) {
            result$image_data <- image_data
        }
    }
    """

    try:
        # Use the new image-enabled function
        return_image = params.get("return_image", True)
        width = params.get("width", 1200)
        height = params.get("height", 800)

        result = await execute_r_script_with_image_async(
            r_script,
            params,
            include_image=return_image,
            image_width=width,
            image_height=height,
        )

        await context.info("Regression plots created successfully")
        return result

    except Exception as e:
        await context.error("Regression plot creation failed", error=str(e))
        raise
