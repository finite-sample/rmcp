# Panel Data Regression Script for RMCP
# =====================================
#
# This script performs panel data regression with fixed effects, random effects,
# between effects, or pooling models using the plm package.


# Load required libraries
library(jsonlite)

# Determine script directory for path resolution
script_dir <- if (exists("testthat_testing") && testthat_testing) {
    # Running under testthat - use relative path from test directory
    file.path("..", "..", "R")
} else {
    # Running normally - use relative path from script location
    file.path("..", "..", "R")
}

# Load RMCP utilities
utils_path <- file.path(script_dir, "utils.R")
if (file.exists(utils_path)) {
    source(utils_path)
} else {
    stop("Cannot find RMCP utilities at: ", utils_path)
}

# Parse command line arguments
args <- if (exists("test_args")) {
    # Use test arguments if provided (for testthat)
    test_args
} else {
    # Parse from command line
    cmd_args <- commandArgs(trailingOnly = TRUE)
    if (length(cmd_args) == 0) {
        stop("No JSON arguments provided")
    }
    
    # Parse JSON input
    tryCatch({
        fromJSON(cmd_args[1])
    }, error = function(e) {
        stop("Failed to parse JSON arguments: ", e$message)
    })
}


# Validate input
args <- validate_json_input(args, required = c("data"))

# Main script logic
library(plm)
library(lmtest)

# Prepare data and parameters
formula <- as.formula(args$formula)
id_var <- args$id_variable
time_var <- args$time_variable
model_type <- args$model %||% "within"
robust <- args$robust %||% TRUE

# Create panel data frame
pdata <- pdata.frame(data, index = c(id_var, time_var))

# Fit panel model
if (model_type == "pooling") {
    model <- plm(formula, data = pdata, model = "pooling")
} else if (model_type == "within") {
    model <- plm(formula, data = pdata, model = "within")  # Fixed effects
} else if (model_type == "between") {
    model <- plm(formula, data = pdata, model = "between")
} else if (model_type == "random") {
    model <- plm(formula, data = pdata, model = "random")
}

# Get robust standard errors if requested
if (robust) {
    robust_se <- coeftest(model, vcov = vcovHC(model, type = "HC1"))
    coef_table <- robust_se
} else {
    coef_table <- summary(model)$coefficients
}

# Extract coefficients with proper names
coef_vals <- coef_table[, "Estimate"]
names(coef_vals) <- rownames(coef_table)
std_err_vals <- coef_table[, "Std. Error"]
names(std_err_vals) <- rownames(coef_table)
t_vals <- coef_table[, "t value"]
names(t_vals) <- rownames(coef_table)
p_vals <- coef_table[, "Pr(>|t|)"]
names(p_vals) <- rownames(coef_table)

result <- list(
    coefficients = as.list(coef_vals),
    std_errors = as.list(std_err_vals),
    t_values = as.list(t_vals),
    p_values = as.list(p_vals),
    r_squared = summary(model)$r.squared[1],
    adj_r_squared = summary(model)$r.squared[2],
    model_type = model_type,
    robust_se = robust,
    n_obs = nobs(model),
    n_groups = pdim(model)$nT$n,
    time_periods = pdim(model)$nT$T,
    formula = deparse(formula),
    id_variable = id_var,
    time_variable = time_var,

    # Special non-validated field for formatting
    "_formatting" = list(
        summary = tryCatch({
            # Try to tidy the panel model
            tidy_model <- broom::tidy(model)
            as.character(knitr::kable(
                tidy_model, format = "markdown", digits = 4
            ))
        }, error = function(e) {
            # Fallback: create summary table
            panel_summary <- data.frame(
                Model = paste0("Panel (", model_type, ")"),
                Groups = pdim(model)$nT$n,
                Time_Periods = pdim(model)$nT$T,
                R_Squared = round(summary(model)$r.squared[1], 4)
            )
            as.character(knitr::kable(
                panel_summary, format = "markdown", digits = 4
            ))
        }),
        interpretation = paste0("Panel regression (", model_type, " effects) with ",
                              pdim(model)$nT$n, " groups and ", pdim(model)$nT$T, " time periods.")
    )
)
# Output results in standard JSON format
if (exists("result")) {
    cat(safe_json(format_json_output(result)))
} else {
    cat(safe_json(list(error = "No result generated", success = FALSE)))
}
