study_error <- function(code, message, category = "invalid") {
  list(ok = FALSE, issues = list(list(
    code = code, category = category, path = "", message = message,
    sources = list(), remedy = "Inspect the study and resolve the reported requirement."
  )))
}

study_main <- function(args) {
  required <- c("superdf", "arrow")
  absent <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
  if (length(absent)) {
    return(study_error(
      "missing_dependency",
      paste("Install these R packages on the execution host:", paste(absent, collapse = ", ")),
      "dependency"
    ))
  }
  if (utils::packageVersion("superdf") < "0.3.0") {
    return(study_error("unsupported_superdf", "This route requires R superdf >= 0.3.0 with structured analysis requirements.", "dependency"))
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
        roster = ctx$roster,
        declarations_verified = FALSE,
        superdf_version = as.character(utils::packageVersion("superdf"))
      ),
      context = ctx
    ))
  }
  tryCatch(
    {
      request <- do.call(superdf::analysis_request, args$request)
      if (args$action == "check") {
        checked <- superdf::check_analysis(study, request)
        return(list(
          ok = checked$ok,
          issues = checked$issues,
          validation_method = "requirements_check",
          receipt = list(
            request = checked$request, input_digest = checked$input_digest,
            roster = ctx$roster, evidence = ctx$evidence, declarations_verified = FALSE
          )
        ))
      }
      fit <- superdf::run_analysis(study, request)
      if (request$kind == "mean") {
        interval <- stats::confint(fit$fit, df = fit$analysis$design_df)
        estimate <- list(
          value = unname(stats::coef(fit$fit)[[1]]),
          standard_error = unname(survey::SE(fit$fit)[[1]]),
          lower = unname(interval[1, 1]), upper = unname(interval[1, 2]),
          confidence_level = 0.95, degrees_of_freedom = fit$analysis$design_df
        )
      } else {
        estimate <- list(
          value = unname(fit$fit$coefficients[[1]]),
          standard_error = unname(fit$fit$std.error[[1]]),
          lower = unname(fit$fit$conf.low[[1]]), upper = unname(fit$fit$conf.high[[1]]),
          confidence_level = 0.95, degrees_of_freedom = unname(fit$fit$df[[1]])
        )
      }
      if (any(!is.finite(unlist(estimate)))) {
        return(study_error("nonfinite_inference", "The backend returned undefined or nonfinite inference.", "unsupported"))
      }
      analysis <- fit$analysis
      analysis$current_keys <- NULL
      list(
        ok = TRUE, issues = list(), estimate = estimate,
        receipt = list(request = request, analysis = analysis, declarations_verified = FALSE)
      )
    },
    superdf_analysis_error = function(e) {
      list(ok = FALSE, issues = e$issues)
    },
    error = function(e) {
      study_error("analysis_failed", conditionMessage(e))
    }
  )
}

result <- study_main(args)
