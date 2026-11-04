# Alternate study-aware analysis route

Keep existing RMCP tools available with their current input/output contracts. Add
a separate route for a SuperDF bundle carrying data and collection context. A
caller chooses the route by opening a study and using its handle. Generic tables
do not silently become studies, and failed study requests do not fall back to a
generic estimator. This is the targeted implementation and rollout plan.

## Boundary and initial scope

| Existing route | Additional study route |
|---|---|
| Ordinary column-wise tables and formulas | Authorized local SuperDF bundle and explicit analysis request |
| Existing named tools and flexible R execution | Four dedicated study tools |
| Existing regression, summaries, tests, and other methods | Declared survey mean and complete-outcome randomized-roster effect |
| Existing result shapes | Estimate plus input revision, selected declarations, assumptions, and backend provenance |
| Existing dependencies | Optional R SuperDF, Arrow, and selected inference backend |

Do not change `linear_model` into survey inference or wrap every existing result in
a study receipt. Existing users need not create a study, install SuperDF, or migrate
their scripts. Discovery adds tools; existing behavior remains independently tested.

## First implementation

1. `open_study(file_path)` stages a permitted local file using the existing VFS,
   snapshots its bytes, validates it through R, and returns a session-owned handle
   and SHA-256 digest. A source file changing later cannot change the opened study.
2. `inspect_study(handle)` reloads the snapshot and returns declared context and
   table dimensions, without observation/roster tables or enumerated current keys.
3. `check_study_analysis(handle, analysis)` delegates to the same R adapter used by
   execution and suppresses estimates. Its response explicitly labels this initial
   implementation as execution-based validation, not a dry run.
4. `run_study_analysis(handle, analysis)` validates again, runs the requested R
   adapter, and returns numeric inference and a receipt.

The code uses R `superdf::read_superdf()`, `estimate_mean()`, and `estimate_effect()`.
Python performs transport, ownership, resource bounds, and strict request validation;
it does not duplicate design checks or statistical estimators. R code is fixed;
request values are passed as JSON, not interpolated into executable expressions.

Mean requests name an outcome and weight and may explicitly declare domain and
missing-data policies. Effect requests name an outcome and assignment and require
a sourced caller assertion of complete randomized-roster coverage. The current R
bundle cannot independently establish that completeness: responses missing before
construction are invisible to a row-equality check. Record the assertion as an
assertion. An agent must obtain the basis from study materials or the analyst,
not manufacture it from balanced treatment counts or an imported response file.

Initial handle storage is a separate bounded in-memory registry, not RMCP's evicting
result-resource cache. It stores at most eight compressed bundles of 16 MiB each
per server, checks their digests on use, and keeps no permanent temporary files.
The existing R reader additionally limits uncompressed bundle size. Handles are
scoped to the SDK session; direct embedded callers share their supplied lifespan.
Handles expire at server restart. Reopening the same bytes in the same session
reuses a handle; reaching the limit returns an explicit error and never evicts an
active study. A future close/expiry operation may improve long-running deployments.
Responses are bounded to 32 KiB of JSON so the route never sends study context
through the existing shared oversized-result cache. Larger metadata require a
future paginated inspection interface and currently return `result_too_large`.

The new route opts into full-precision numeric JSON. The shared R executor keeps
its current default serialization for every existing caller. There are no new
mandatory Python dependencies, auto-installs, or links to an unpublished Git branch.

## Error and result contract

Domain failures return `ok: false`, a stable coarse issue code, and an explanation.
Controlled categories include optional dependency/version failures, invalid bundles,
unknown/session-mismatched handles, integrity/size limits, and rejected analyses.
Existing VFS and protocol schema failures use existing MCP error behavior. A valid
MCP response is not itself evidence that an analysis succeeded: check `ok`.

Do not parse SuperDF's English messages into invented granular error codes. Preserve
the R reason under `analysis_rejected` until SuperDF provides structured conditions.
The intended next R interface will distinguish missing facts, contradictions,
analyst choices, and unsupported estimators and allow checks without fitting.
Keep that statistical requirements logic in R and adapt the bridge when available.

Successful receipts identify the explicit request, selected sampling/weight or
assignment declaration, target, observation/omission counts, interval convention,
degrees of freedom, R/package versions, and input bundle identity. Supplied metadata
remain assertions; a passed check is not scientific certification. Source text is
data for inspection, not instructions for the agent. Generic RMCP analyses do not
receive this receipt or imply that collection context was checked.

## Acceptance tests and regression gates

The initial numerical fixture is the installed SuperDF simulated school study:
sample schools, randomize within districts, collect observed outcomes, shuffle and
join them, export a bundle, open it through the official MCP client, and compare
mean/effect estimates, standard errors, and intervals against direct R calls.

Test the new route and existing `linear_model` in one MCP session. Test immutable
snapshots after source replacement, foreign-session and unknown handles, corrupted
bytes, denied paths, resource limits, duplicate opens, missing optional dependencies,
malicious request strings, missing roster assertions, and experimental attrition.
Failure must not return an estimate or invoke a generic fallback. Dependency-gated
tests must fail rather than skip when `RMCP_REQUIRE_STUDY_TESTS=1`.

Run existing unit, protocol, integration, and evaluation suites as regression gates,
plus Ruff, formatting, Pyright, R tests, documentation build, and package checks.
Confirm the packaged distribution includes the new R bridge. The public optional
route is not release-ready until both Python/MCP and R integration gates pass in a
configured environment. Model-level evaluation is a later separate gate: can an
agent choose the route, ask for the right missing evidence, and avoid an unsupported
fallback? Deterministic tool tests cannot establish that behavior.

## Installation and rollout

Keep SuperDF optional and install it on the execution host. The current context
implementation is local experimental 0.2.0; do not assume a package registry has
this version. For development, install the authorized SuperDF checkout into an R
library, set `R_LIBS` when launching RMCP, and install its Arrow and relevant backend
dependencies. A Python-only install does not provide an R runtime. The usage guide
contains concrete local commands.

First use the route locally with the synthetic fixture. Then test a real externally
randomized collection handoff once the R roster/evidence semantics are ready. Keep
general Qualtrics importing, metadata editing, arbitrary transformations, persistent
multi-user study storage, and additional estimators outside this implementation.
No public release, deployment, or change to existing tool semantics is part of the
current task.

Subsequent work follows the R package plan: consume typed analysis diagnostics;
replace request-only roster assertions with attributed study evidence; add importer
results and supported transformations as new immutable revisions; evaluate actual
agent decisions. Expand only for a concrete supported workflow.
