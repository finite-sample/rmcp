# T-Test Analysis Script for RMCP
# ===============================
#
# This script performs t-test analysis including one-sample, two-sample, and paired t-tests.
# It handles different types of t-tests based on the provided parameters and returns
# comprehensive test statistics and confidence intervals.

# Main script logic
variable <- args$variable
group <- args$group
mu <- args$mu %||% 0
alternative <- args$alternative %||% "two.sided"
paired <- args$paired %||% FALSE
var_equal <- args$var_equal %||% FALSE

if (is.null(group)) {
  # One-sample t-test
  test_result <- t.test(data[[variable]], mu = mu, alternative = alternative)
  test_type <- "One-sample t-test"

  # Clean data
  values <- data[[variable]][!is.na(data[[variable]])]

  result <- list(
    test_type = test_type,
    statistic = as.numeric(test_result$statistic),
    df = test_result$parameter,
    p_value = test_result$p.value,
    confidence_interval = list(
      lower = as.numeric(test_result$conf.int[1]),
      upper = as.numeric(test_result$conf.int[2]),
      level = if (!is.null(attr(test_result$conf.int, "conf.level"))) attr(test_result$conf.int, "conf.level") else 0.95
    ),
    mean = as.numeric(test_result$estimate),
    null_value = mu,
    alternative = alternative,
    n_obs = length(values),

    # Special non-validated field for formatting
    "_formatting" = list(
      summary = format_result_table(test_result, "T-Test Results"),
      interpretation = interpret_result(test_result, "T-test")
    )
  )
} else {
  # Two-sample t-test
  group_values <- data[[group]]

  # Sort groups consistently and handle NA values
  unique_groups <- sort(unique(stats::na.omit(group_values)))
  if (length(unique_groups) != 2) {
    stop("Group variable must have exactly 2 levels")
  }

  # Extract and clean data for each group
  x <- data[[variable]][group_values == unique_groups[1]]
  y <- data[[variable]][group_values == unique_groups[2]]
  x <- x[!is.na(x)]
  y <- y[!is.na(y)]

  test_result <- t.test(x, y, alternative = alternative, paired = paired, var.equal = var_equal)
  test_type <- if (paired) "Paired t-test" else if (var_equal) "Two-sample t-test (equal variances)" else "Welch's t-test"

  result <- list(
    test_type = test_type,
    statistic = as.numeric(test_result$statistic),
    df = test_result$parameter,
    p_value = test_result$p.value,
    confidence_interval = list(
      lower = as.numeric(test_result$conf.int[1]),
      upper = as.numeric(test_result$conf.int[2]),
      level = if (!is.null(attr(test_result$conf.int, "conf.level"))) attr(test_result$conf.int, "conf.level") else 0.95
    ),
    mean_x = as.numeric(test_result$estimate[1]),
    mean_y = as.numeric(test_result$estimate[2]),
    mean_difference = as.numeric(test_result$estimate[1] - test_result$estimate[2]),
    groups = unique_groups,
    alternative = alternative,
    paired = paired,
    var_equal = var_equal,
    n_obs_x = length(x),
    n_obs_y = length(y),

    # Special non-validated field for formatting
    "_formatting" = list(
      summary = format_result_table(test_result, "T-Test Results"),
      interpretation = interpret_result(test_result, "T-test")
    )
  )
}
