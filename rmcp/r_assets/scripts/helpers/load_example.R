# Example Dataset Loading Script for RMCP
# ========================================
#
# This script generates example datasets for testing and learning
# statistical analysis methods with realistic data patterns.

# Load required libraries
library(dplyr)

# Prepare parameters with safe fallbacks
dataset_name <- args$dataset %||% "sales"
size_param <- args$size %||% "small"
add_noise <- args$add_noise %||% FALSE

# Set size parameters
size_map <- list(
  small = 20,
  medium = 100,
  large = 500
)
n <- size_map[[size_param]]

set.seed(42) # For reproducible examples

if (dataset_name == "sales") {
  # Sales and marketing data
  months <- 1:n
  marketing_spend <- round(rnorm(n, 1000, 200), 0)
  sales <- round(50 + 4.5 * marketing_spend + rnorm(n, 0, 500), 0)
  # Add some seasonal effect
  seasonal <- 200 * sin(2 * pi * months / 12)
  sales <- sales + seasonal
  data <- data.frame(
    month = months,
    marketing_spend = pmax(marketing_spend, 0),
    sales = pmax(sales, 0),
    quarter = paste0("Q", ceiling(months %% 12 / 3))
  )
  description <- "Sales and marketing spend data with seasonal patterns"
} else if (dataset_name == "economics") {
  # Economic indicators
  years <- seq(2000, 2000 + n / 4, length.out = n)
  gdp_growth <- round(rnorm(n, 2.5, 1.2), 2)
  unemployment <- round(8 - 0.8 * gdp_growth + rnorm(n, 0, 0.5), 1)
  investment <- round(18 + 0.3 * gdp_growth + rnorm(n, 0, 2), 1)
  data <- data.frame(
    year = years,
    gdp_growth = gdp_growth,
    unemployment = pmax(unemployment, 1),
    investment = pmax(investment, 10),
    country = sample(c("USA", "GBR", "DEU", "FRA"), n, replace = TRUE)
  )
  description <- "Economic indicators demonstrating Okun's Law and investment relationships"
} else if (dataset_name == "customers") {
  # Customer data for churn analysis
  customer_id <- 1:n
  tenure_months <- sample(1:72, n, replace = TRUE)
  monthly_charges <- round(runif(n, 20, 120), 2)
  total_charges <- round(tenure_months * monthly_charges + rnorm(n, 0, 100), 2)
  # Churn probability based on tenure and charges
  churn_prob <- plogis(-2 + -0.05 * tenure_months + 0.02 * monthly_charges)
  churned <- rbinom(n, 1, churn_prob)
  age <- sample(18:80, n, replace = TRUE)
  data <- data.frame(
    customer_id = customer_id,
    age = age,
    tenure_months = tenure_months,
    monthly_charges = monthly_charges,
    total_charges = pmax(total_charges, 0),
    churned = churned,
    contract_type = sample(c("Month-to-month", "One year", "Two year"), n, replace = TRUE, prob = c(0.5, 0.3, 0.2))
  )
  description <- "Customer data for churn prediction analysis"
} else if (dataset_name == "timeseries") {
  # Time series data with trend and seasonality
  time_points <- 1:n
  trend <- 0.5 * time_points
  seasonal <- 10 * sin(2 * pi * time_points / 12) + 5 * cos(2 * pi * time_points / 4)
  noise <- rnorm(n, 0, 3)
  value <- 100 + trend + seasonal + noise
  data <- data.frame(
    time = time_points,
    value = round(value, 2),
    month = rep(1:12, length.out = n),
    year = rep(2020:(2020 + ceiling(n / 12)), each = 12)[1:n]
  )
  description <- "Time series data with trend and seasonal components"
} else if (dataset_name == "survey") {
  # Survey data with Likert scales
  respondent_id <- 1:n
  age <- sample(18:75, n, replace = TRUE)
  satisfaction <- sample(1:10, n, replace = TRUE, prob = c(0.05, 0.05, 0.1, 0.1, 0.15, 0.15, 0.15, 0.15, 0.05, 0.05))
  # Purchase frequency correlated with satisfaction
  purchase_freq <- pmax(1, round(satisfaction * 0.8 + rnorm(n, 0, 1.5)), 0)
  education <- sample(c("High School", "Bachelor", "Master", "PhD"), n, replace = TRUE, prob = c(0.3, 0.4, 0.25, 0.05))
  income_bracket <- sample(c("< $30k", "$30-50k", "$50-75k", "$75-100k", "> $100k"), n, replace = TRUE, prob = c(0.2, 0.25, 0.25, 0.2, 0.1))
  data <- data.frame(
    respondent_id = respondent_id,
    age = age,
    satisfaction = satisfaction,
    purchase_frequency = purchase_freq,
    education = education,
    income_bracket = income_bracket
  )
  description <- "Survey data with satisfaction and demographic variables"
} else {
  stop("Unknown dataset name")
}
# Add noise if requested
if (add_noise) {
  # Add missing values randomly (5-10% missing)
  missing_rate <- runif(1, 0.05, 0.10)
  for (col in names(data)) {
    if (is.numeric(data[[col]])) {
      missing_indices <- sample(1:nrow(data), round(nrow(data) * missing_rate))
      data[missing_indices, col] <- NA
    }
  }
  # Add some outliers to numeric columns
  numeric_cols <- names(data)[sapply(data, is.numeric)]
  for (col in numeric_cols) {
    if (!all(is.na(data[[col]]))) {
      # Add 2-3 outliers
      outlier_indices <- sample(which(!is.na(data[[col]])), min(3, sum(!is.na(data[[col]]))))
      mean_val <- mean(data[[col]], na.rm = TRUE)
      sd_val <- sd(data[[col]], na.rm = TRUE)
      data[outlier_indices, col] <- data[outlier_indices, col] + sample(c(-1, 1), length(outlier_indices), replace = TRUE) * 3 * sd_val
    }
  }
}
# Calculate basic statistics
numeric_vars <- names(data)[sapply(data, is.numeric)]
stats <- list()
for (var in numeric_vars) {
  if (sum(!is.na(data[[var]])) > 0) {
    stats[[var]] <- list(
      mean = round(mean(data[[var]], na.rm = TRUE), 2),
      sd = round(sd(data[[var]], na.rm = TRUE), 2),
      min = min(data[[var]], na.rm = TRUE),
      max = max(data[[var]], na.rm = TRUE),
      missing = sum(is.na(data[[var]]))
    )
  }
}
result <- list(
  data = as.list(data), # Convert to column-wise format for schema compatibility
  metadata = list(
    name = dataset_name,
    description = description,
    size = size_param,
    rows = nrow(data),
    columns = ncol(data),
    has_noise = add_noise
  ),
  statistics = stats,
  suggested_analyses = list(),
  variable_info = list(
    numeric_variables = numeric_vars,
    categorical_variables = as.list(names(data)[sapply(data, function(x) is.factor(x) || is.character(x))]),
    variable_types = as.list(setNames(sapply(data, class), names(data)))
  )
)
# Add suggested analyses based on dataset
if (dataset_name == "sales") {
  result$suggested_analyses <- c(
    "Linear regression: sales ~ marketing_spend",
    "Correlation analysis between all numeric variables",
    "Time series analysis of sales data"
  )
} else if (dataset_name == "economics") {
  result$suggested_analyses <- c(
    "Test Okun's Law: unemployment ~ gdp_growth",
    "Investment effects: gdp_growth ~ investment",
    "Panel regression with country effects"
  )
} else if (dataset_name == "customers") {
  result$suggested_analyses <- c(
    "Logistic regression: churned ~ tenure_months + monthly_charges",
    "Survival analysis for customer retention",
    "Customer segmentation with clustering"
  )
} else if (dataset_name == "timeseries") {
  result$suggested_analyses <- c(
    "ARIMA modeling and forecasting",
    "Time series decomposition",
    "Seasonal trend analysis"
  )
} else if (dataset_name == "survey") {
  result$suggested_analyses <- c(
    "Correlation: satisfaction ~ purchase_frequency",
    "ANOVA: satisfaction by education level",
    "Multiple regression with demographic controls"
  )
}
