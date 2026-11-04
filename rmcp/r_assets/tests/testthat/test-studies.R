study_dependencies <- function() {
  for (package in c("superdf", "arrow", "zip", "survey", "estimatr")) {
    if (!requireNamespace(package, quietly = TRUE)) {
      if (Sys.getenv("RMCP_REQUIRE_STUDY_TESTS") == "1") {
        stop("Required study dependency is missing: ", package)
      }
      testthat::skip(paste("Optional study dependency:", package))
    }
  }
  if (utils::packageVersion("superdf") < "0.2.0") {
    if (Sys.getenv("RMCP_REQUIRE_STUDY_TESTS") == "1") stop("superdf >= 0.2.0 required")
    testthat::skip("Optional study route needs superdf >= 0.2.0")
  }
}

study_bridge <- function(path, action = "inspect", request = list()) {
  env <- new.env(parent = globalenv())
  env$args <- list(path = path, action = action, request = request)
  env$`%||%` <- function(a, b) if (!is.null(a)) a else b
  source(testthat::test_path("..", "..", "scripts", "studies", "study.R"), local = env)
  env$result
}

testthat::test_that("study bridge matches direct inference and withholds row identities", {
  study_dependencies()
  library(superdf)
  source(system.file("examples", "simulated_study.R", package = "superdf"), local = TRUE)
  study <- collect_study(simulate_population())
  path <- tempfile(fileext = ".superdf")
  on.exit(unlink(path), add = TRUE)
  write_superdf(study, path)
  info <- study_bridge(path)
  testthat::expect_true(info$ok)
  testthat::expect_equal(info$study$current_rows, 96L)
  testthat::expect_equal(info$study$roster_completeness, "not_independently_verified")
  mean_request <- list(kind = "mean", outcome = "baseline", weight = "sample_weight")
  effect_request <- list(
    kind = "effect", outcome = "followup", assignment = "school_offer",
    roster_assertion = list(complete = TRUE, source = "Simulation assignment roster")
  )
  expected <- analyze_study(study)$table
  for (i in 1:2) {
    request <- list(mean_request, effect_request)[[i]]
    actual <- study_bridge(path, "run", request)
    testthat::expect_true(actual$ok)
    testthat::expect_equal(actual$estimate$value, expected$estimate[[i]])
    testthat::expect_equal(actual$estimate$standard_error, expected$se[[i]])
    testthat::expect_equal(actual$estimate$lower, expected$lower[[i]])
    testthat::expect_equal(actual$estimate$upper, expected$upper[[i]])
    testthat::expect_null(actual$receipt$analysis$current_keys)
    testthat::expect_equal(actual$receipt$request, request)
    checked <- study_bridge(path, "check", request)
    testthat::expect_true(checked$ok)
    testthat::expect_null(checked$estimate)
    testthat::expect_equal(checked$validation_method, "adapter_execution_estimates_withheld")
  }
})

testthat::test_that("study failures cannot silently fall back to another estimator", {
  study_dependencies()
  library(superdf)
  source(system.file("examples", "workflows.R", package = "superdf"), local = TRUE)
  x <- reference_workflows()$experiment
  path <- tempfile(fileext = ".superdf")
  on.exit(unlink(path), add = TRUE)
  write_superdf(x[-1, ], path)
  request <- list(kind = "effect", outcome = "outcome", assignment = "offer_assignment")
  missing <- study_bridge(path, "run", request)
  testthat::expect_false(missing$ok)
  testthat::expect_equal(missing$issues[[1]]$code, "roster_assertion_required")
  request$roster_assertion <- list(complete = TRUE, source = "Supplied roster")
  rejected <- study_bridge(path, "run", request)
  testthat::expect_false(rejected$ok)
  testthat::expect_equal(rejected$issues[[1]]$code, "analysis_rejected")
  testthat::expect_match(rejected$issues[[1]]$message, "Attrition or restriction")
  testthat::expect_null(rejected$estimate)
  writeLines("not a bundle", path)
  invalid <- suppressWarnings(study_bridge(path))
  testthat::expect_false(invalid$ok)
  testthat::expect_equal(invalid$issues[[1]]$code, "invalid_bundle")
})

testthat::test_that("optional dependency failure is actionable", {
  study_dependencies()
  env <- new.env(parent = globalenv())
  env$args <- list(path = "unused", action = "inspect", request = list())
  env$requireNamespace <- function(package, quietly) FALSE
  source(testthat::test_path("..", "..", "scripts", "studies", "study.R"), local = env)
  testthat::expect_false(env$result$ok)
  testthat::expect_equal(env$result$issues[[1]]$code, "missing_dependency")
  testthat::expect_match(env$result$issues[[1]]$message, "superdf, arrow")
})
