# Data Filtering Script for RMCP
# ==============================
#
# This script filters datasets based on multiple conditions with logical operators.
# Supports various comparison operators and flexible condition combinations.

# Prepare data and parameters
conditions <- args$conditions
logic <- args$logic %||% "AND"

# fromJSON() simplifies an array of condition objects to a data.frame;
# normalize to a list of row-lists so iteration sees one condition at a time.
if (is.data.frame(conditions)) {
  conditions <- lapply(
    seq_len(nrow(conditions)),
    function(i) as.list(conditions[i, , drop = FALSE])
  )
}

evaluate_condition <- function(cond) {
  values <- data[[cond$variable]]
  target <- cond$value
  switch(cond$operator,
    "==" = values == target,
    "!=" = values != target,
    ">" = values > target,
    "<" = values < target,
    ">=" = values >= target,
    "<=" = values <= target,
    "%in%" = values %in% target,
    "!%in%" = !(values %in% target),
    stop(paste("Unsupported filter operator:", cond$operator))
  )
}

matches <- lapply(conditions, evaluate_condition)
keep <- if (logic == "AND") Reduce(`&`, matches) else Reduce(`|`, matches)
keep[is.na(keep)] <- FALSE
filtered_data <- data[keep, , drop = FALSE]

format_value <- function(value) paste(as.character(value), collapse = ",")
filter_expressions <- vapply(
  conditions,
  function(cond) paste(cond$variable, cond$operator, format_value(cond$value)),
  character(1)
)
full_expression <- paste(
  filter_expressions,
  collapse = if (logic == "AND") " AND " else " OR "
)
result <- list(
  data = lapply(filtered_data, I), # Column-wise; I() keeps length-1 vectors as JSON arrays
  filter_expression = full_expression,
  original_rows = nrow(data),
  filtered_rows = nrow(filtered_data),
  rows_removed = nrow(data) - nrow(filtered_data),
  removal_percentage = (nrow(data) - nrow(filtered_data)) / nrow(data) * 100
)
