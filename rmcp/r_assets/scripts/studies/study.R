study_error <- function(code, message) {
  list(ok = FALSE, issues = list(list(code = code, message = message)))
}

study_main <- function(args) {
  required <- c("superdf", "arrow")
  if (args$action != "inspect") {
    required <- c(required, if (args$request$kind == "mean") "survey" else "estimatr")
  }
  absent <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
  if (length(absent)) {
    return(study_error(
      "missing_dependency",
      paste("Install these R packages on the execution host:", paste(absent, collapse = ", "))
    ))
  }
  if (utils::packageVersion("superdf") < "0.2.0") {
    return(study_error("unsupported_superdf", "This route requires R superdf >= 0.2.0 with collection-context bundles."))
  }
  study <- tryCatch(superdf::read_superdf(args$path), error = identity)
  if (inherits(study, "error")) {
    return(study_error("invalid_bundle", conditionMessage(study)))
  }
  ctx <- superdf::context(study)
  if (args$action == "inspect") {
    return(list(
      ok = TRUE,
      issues = list(),
      study = list(
        dataset = ctx$dataset,
        schema_version = ctx$schema_version,
        current_rows = nrow(study),
        roster_rows = nrow(superdf::collection_data(study)),
        roster_completeness = "not_independently_verified",
        superdf_version = as.character(utils::packageVersion("superdf"))
      ),
      context = ctx
    ))
  }
  request <- args$request
  if (request$kind == "effect" &&
    (!isTRUE(request$roster_assertion$complete) ||
      is.null(request$roster_assertion$source) ||
      !nzchar(trimws(request$roster_assertion$source)))) {
    return(study_error("roster_assertion_required", "Supply a sourced caller assertion that the roster includes every randomized unit; response rows alone cannot establish this."))
  }
  result <- tryCatch(
    {
      if (request$kind == "mean") {
        fit <- superdf::estimate_mean(
          study, request$outcome, request$weight,
          domain = isTRUE(request$domain), missing = request$missing %||% "fail"
        )
        interval <- stats::confint(fit$fit, df = fit$analysis$design_df)
        estimate <- list(
          value = unname(stats::coef(fit$fit)[[1]]),
          standard_error = unname(survey::SE(fit$fit)[[1]]),
          lower = unname(interval[1, 1]), upper = unname(interval[1, 2]),
          confidence_level = 0.95, degrees_of_freedom = fit$analysis$design_df
        )
      } else if (request$kind == "effect") {
        fit <- superdf::estimate_effect(study, request$outcome, request$assignment)
        estimate <- list(
          value = unname(fit$fit$coefficients[[1]]),
          standard_error = unname(fit$fit$std.error[[1]]),
          lower = unname(fit$fit$conf.low[[1]]), upper = unname(fit$fit$conf.high[[1]]),
          confidence_level = 0.95, degrees_of_freedom = unname(fit$fit$df[[1]])
        )
      } else {
        stop("Unsupported study analysis kind.")
      }
      if (any(!is.finite(unlist(estimate)))) {
        stop("The backend returned undefined or nonfinite inference; the request is not estimable by this route.")
      }
      analysis <- fit$analysis
      analysis$current_keys <- NULL
      selected_design <- NULL
      selected_weight <- NULL
      if (request$kind == "mean") {
        selected_weight <- Filter(function(w) identical(w$id, request$weight), ctx$weights)[[1]]
        if (!is.null(selected_weight$sampling)) {
          selected_design <- Filter(function(s) identical(s$id, selected_weight$sampling), ctx$sampling)[[1]]
        }
        analysis$target <- if (is.null(selected_design$population)) {
          "Population not documented; interpretation relies on supplied weights and declarations"
        } else {
          selected_design$population
        }
      } else {
        selected_design <- Filter(function(a) identical(a$id, request$assignment), ctx$assignments)[[1]]
      }
      receipt <- list(
        request = request,
        analysis = analysis,
        selected_design = selected_design,
        selected_weight = selected_weight,
        assumptions = list(
          declarations = "Source and design declarations are supplied assertions, not independently verified facts.",
          roster_completeness = "not_independently_verified",
          roster_assertion = request$roster_assertion,
          missingness = "Omission, when requested, does not establish a nonresponse assumption."
        )
      )
      answer <- list(ok = TRUE, issues = list(), receipt = receipt)
      if (args$action == "check") {
        answer$validation_method <- "adapter_execution_estimates_withheld"
      } else {
        answer$estimate <- estimate
      }
      answer
    },
    error = function(e) study_error("analysis_rejected", conditionMessage(e))
  )
  result
}

result <- study_main(args)
