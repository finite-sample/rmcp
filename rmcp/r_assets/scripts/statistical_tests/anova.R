# ANOVA Analysis Script for RMCP
# ===============================
#
# This script performs Analysis of Variance (ANOVA) with support for Type I, II, and III
# sum of squares. It uses base R anova() for Type I and car::Anova() for Types II and III.

# Prepare data and parameters
formula <- as.formula(args$formula)
anova_type <- args$anova_type %||% "I"

# Load required libraries
library(knitr)
library(broom)

# Fit the model
model <- lm(formula, data = data)

# Perform ANOVA
if (anova_type == "I") {
  anova_result <- anova(model)
  anova_table <- anova_result
} else {
  library(car)
  # Convert ANOVA type string (e.g., "II", "III") to numeric for car::Anova
  # Type I = 1, Type II = 2, Type III = 3
  anova_numeric <- as.numeric(substr(anova_type, 1, 1))
  anova_table <- Anova(model, type = anova_numeric)
}

# Normalize ANOVA table column names
df <- as.data.frame(anova_table)
names(df) <- gsub("Pr\\(>F\\)", "p_value", names(df))
names(df) <- gsub("^F value$", "F", names(df))
names(df) <- gsub("^Sum of Sq$", "Sum Sq", names(df))
names(df) <- gsub("^Mean of Sq$", "Mean Sq", names(df))

# Remove residuals row which typically has NA for F-statistic and p-value
if ("Residuals" %in% rownames(df)) {
  df <- df[rownames(df) != "Residuals", , drop = FALSE]
}

# Extract values using normalized names, handling NAs properly
sum_sq <- if ("Sum Sq" %in% names(df)) df[["Sum Sq"]] else rep(0, nrow(df))
mean_sq <- if ("Mean Sq" %in% names(df)) df[["Mean Sq"]] else if ("Sum Sq" %in% names(df) && "Df" %in% names(df)) df[["Sum Sq"]] / df[["Df"]] else rep(0, nrow(df))
f_value <- if ("F" %in% names(df)) df[["F"]] else rep(0, nrow(df))
p_value <- if ("p_value" %in% names(df)) df[["p_value"]] else rep(0, nrow(df))

# Replace any remaining NAs with appropriate values for schema compliance
sum_sq[is.na(sum_sq)] <- 0
mean_sq[is.na(mean_sq)] <- 0
f_value[is.na(f_value)] <- 0
p_value[is.na(p_value)] <- 1 # Use 1 for non-significant when p-value is missing

# Ensure all vectors are properly formatted as lists (JSON arrays)
result <- list(
  anova_table = list(
    terms = as.list(rownames(df)),
    df = as.list(df[["Df"]]),
    sum_sq = as.list(sum_sq),
    mean_sq = as.list(mean_sq),
    f_value = as.list(f_value),
    p_value = as.list(p_value)
  ),
  model_summary = list(
    r_squared = summary(model)$r.squared,
    adj_r_squared = summary(model)$adj.r.squared,
    residual_se = summary(model)$sigma,
    df_residual = summary(model)$df[2],
    n_obs = nrow(model$model)
  ),
  formula = deparse(formula),
  anova_type = paste("Type", anova_type),
  # Special non-validated field for formatting
  "_formatting" = list(
    summary = tryCatch(
      {
        # Try to tidy the ANOVA table
        tidy_anova <- broom::tidy(anova_table)
        paste(as.character(knitr::kable(
          tidy_anova,
          format = "markdown", digits = 4
        )), collapse = "\n")
      },
      error = function(e) {
        # Fallback: format the data frame directly
        paste(as.character(knitr::kable(
          df,
          format = "markdown", digits = 4
        )), collapse = "\n")
      }
    ),
    interpretation = paste0(
      "ANOVA ",
      if (length(p_value[p_value > 0]) > 0) {
        get_significance(min(p_value[p_value > 0], na.rm = TRUE))
      } else {
        "analysis completed"
      }, "."
    )
  )
)
