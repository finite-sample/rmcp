# Tests for time series analysis scripts
library(testthat)
library(jsonlite)

# Generate time series test data
ts_data <- data.frame(
  date = seq(as.Date("2023-01-01"), as.Date("2023-12-31"), by = "month"),
  values = c(100, 105, 110, 108, 115, 120, 125, 130, 128, 135, 140, 145)
)

test_that("arima_model fits time series", {
  input_data <- list(
    data = list(values = ts_data$values),
    order = c(1, 1, 1)
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/timeseries/arima_model.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("model_order" %in% names(output))
  expect_true("coefficients" %in% names(output))
  expect_true("fitted_values" %in% names(output))

  # Model order should match input
  expect_equal(output$model_order, c(1, 1, 1))

  # Should have fitted values for each observation
  expect_equal(length(output$fitted_values), length(ts_data$values))
})

test_that("decompose_timeseries separates components", {
  # Create longer time series for decomposition
  long_ts <- data.frame(
    values = c(
      # Year 1: seasonal pattern
      100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155,
      # Year 2: similar pattern with trend
      110, 115, 120, 125, 130, 135, 140, 145, 150, 155, 160, 165,
      # Year 3: continuing trend
      120, 125, 130, 135, 140, 145, 150, 155, 160, 165, 170, 175
    )
  )

  input_data <- list(
    data = list(values = long_ts$values),
    frequency = 12,
    type = "additive"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/timeseries/decompose_timeseries.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("trend" %in% names(output))
  expect_true("seasonal" %in% names(output))
  expect_true("remainder" %in% names(output))
  expect_true("type" %in% names(output))

  expect_equal(output$type, "additive")
})

test_that("stationarity_test detects non-stationarity", {
  # Create clearly non-stationary data (with trend)
  nonstationary_data <- data.frame(
    values = cumsum(rnorm(50, mean = 1, sd = 0.5)) # Random walk with drift
  )

  input_data <- list(
    data = list(values = nonstationary_data$values),
    test = "adf"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/timeseries/stationarity_test.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("test_statistic" %in% names(output))
  expect_true("p_value" %in% names(output))
  expect_true("is_stationary" %in% names(output))
  expect_true("test_type" %in% names(output))

  expect_equal(output$test_type, "adf")
  expect_true(is.logical(output$is_stationary))
})
