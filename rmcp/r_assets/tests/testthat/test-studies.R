study_dependencies <- function() {
  for (package in c("superdf", "arrow", "zip", "survey", "estimatr")) {
    if (!requireNamespace(package, quietly = TRUE)) {
      if (Sys.getenv("RMCP_REQUIRE_STUDY_TESTS") == "1") {
        stop("Required study dependency is missing: ", package)
      }
      testthat::skip(paste("Optional study dependency:", package))
    }
  }
  if (utils::packageVersion("superdf") < "0.3.0") {
    if (Sys.getenv("RMCP_REQUIRE_STUDY_TESTS") == "1") stop("superdf >= 0.3.0 required")
    testthat::skip("Optional study route needs superdf >= 0.3.0")
  }
}

study_bridge <- function(path, action = "inspect", request = list()) {
  env <- new.env(parent = globalenv())
  env$args <- list(path = path, action = action, request = request)
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
  testthat::expect_equal(info$study$roster, context(study)$roster)
  testthat::expect_false(info$study$declarations_verified)
  requests <- list(
    list(kind = "mean", outcome = "baseline", weight = "sample_weight"),
    list(kind = "effect", outcome = "followup", assignment = "school_offer")
  )
  expected <- analyze_study(study)$table
  for (i in 1:2) {
    request <- requests[[i]]
    actual <- study_bridge(path, "run", request)
    testthat::expect_true(actual$ok)
    testthat::expect_equal(actual$estimate$value, expected$estimate[[i]])
    testthat::expect_equal(actual$estimate$standard_error, expected$se[[i]])
    testthat::expect_equal(actual$estimate$lower, expected$lower[[i]])
    testthat::expect_equal(actual$estimate$upper, expected$upper[[i]])
    testthat::expect_null(actual$receipt$analysis$current_keys)
    testthat::expect_equal(actual$receipt$request, do.call(analysis_request, request))
    testthat::expect_equal(actual$receipt$analysis$roster, context(study)$roster)
    checked <- study_bridge(path, "check", request)
    testthat::expect_true(checked$ok)
    testthat::expect_null(checked$estimate)
    testthat::expect_equal(checked$validation_method, "requirements_check")
  }
})

testthat::test_that("bridge preflight does not call the estimator", {
  study_dependencies()
  library(superdf)
  source(system.file("examples", "workflows.R", package = "superdf"), local = TRUE)
  path <- tempfile(fileext = ".superdf")
  on.exit(unlink(path), add = TRUE)
  write_superdf(reference_workflows()$survey, path)
  testthat::local_mocked_bindings(
    run_analysis = function(...) stop("Estimator was invoked during check"),
    .package = "superdf"
  )
  request <- list(kind = "mean", outcome = "income", weight = "main")
  checked <- study_bridge(path, "check", request)
  testthat::expect_true(checked$ok)
  testthat::expect_null(checked$estimate)
})

testthat::test_that("typed requirements pass unchanged through check and execution", {
  study_dependencies()
  library(superdf)
  source(system.file("examples", "workflows.R", package = "superdf"), local = TRUE)
  restricted <- reference_workflows()$experiment[-1, ]
  path <- tempfile(fileext = ".superdf")
  on.exit(unlink(path), add = TRUE)
  write_superdf(restricted, path)
  request <- list(kind = "effect", outcome = "outcome", assignment = "offer_assignment")
  expected <- check_analysis(restricted, do.call(analysis_request, request))
  for (action in c("check", "run")) {
    rejected <- study_bridge(path, action, request)
    testthat::expect_false(rejected$ok)
    testthat::expect_equal(rejected$issues, expected$issues)
    testthat::expect_null(rejected$estimate)
  }
  unknown <- superdf(as.data.frame(restricted), "id", "pupil", "unknown_roster",
    assignments = context(restricted)$assignments
  )
  unlink(path)
  write_superdf(unknown, path)
  for (action in c("check", "run")) {
    rejected <- study_bridge(path, action, request)
    testthat::expect_false(rejected$ok)
    testthat::expect_true("randomized_roster_required" %in% vapply(rejected$issues, function(issue) issue$code, character(1)))
    testthat::expect_null(rejected$estimate)
  }
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
  testthat::expect_equal(env$result$issues[[1]]$category, "dependency")
  testthat::expect_match(env$result$issues[[1]]$message, "superdf, arrow")
})
