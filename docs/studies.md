# Analyze a study with its collection context

The optional study tools use R SuperDF bundles. Existing RMCP tools continue to
accept ordinary tables with their current behavior. Study tools initially support
numeric survey means and complete-outcome randomized effects; unsupported requests
return issues and do not switch to an ordinary regression or t-test.

Install R SuperDF 0.3.0 or later with its collection-context API, plus `arrow` and
the needed `survey` or `estimatr` backend, on the execution host. The experimental
SuperDF revision is not assumed to be publicly released. From this repository,
with that checkout next door, a development setup is:

```sh
mkdir -p .local-r-library
R CMD INSTALL --library=.local-r-library ../superdf
R_LIBS="$PWD/.local-r-library" uv run rmcp start
```

The ordinary R dependencies must already be installed or installed through the
usual R package tooling. `zip` is also needed to create example bundles. The Python
reader is not required for this route; the server delegates to R. Neither package
installation nor metadata edits happen automatically.

Create a demonstration bundle from an R session using the same library:

```r
library(superdf)
source(system.file("examples", "simulated_study.R", package = "superdf"))
study <- collect_study(simulate_population())
write_superdf(study, "collected.superdf")
```

Start RMCP with the file inside an allowed filesystem root, then call:

```json
{"file_path": "/allowed/path/collected.superdf"}
```

Pass that to `open_study`. Use the returned `handle` in `inspect_study` or an analysis
request. For example, `run_study_analysis` accepts:

```json
{
  "handle": "<handle returned by open_study>",
  "analysis": {
    "kind": "mean",
    "outcome": "baseline",
    "weight": "sample_weight"
  }
}
```

For the experiment in this generated example:

```json
{
  "handle": "<handle returned by open_study>",
  "analysis": {
    "kind": "effect",
    "outcome": "followup",
    "assignment": "school_offer"
  }
}
```

The generated bundle records the randomized roster, its assignment scope, and
source evidence before outcome collection. A real bundle must carry its own
attributed declaration. Passing `roster_assertion` in an analysis request is not
supported: an agent cannot repair a response-only file by asserting completeness
at estimation time. SuperDF distinguishes received responses from randomized units
and requires a complete-roster declaration for this effect adapter. It still cannot
independently certify the truth of a producer's declaration. Missing or dropped
experimental outcomes remain unsupported.

`check_study_analysis` accepts the same request and calls SuperDF's public
`check_analysis()` without fitting an estimator. It returns typed requirement
records with `code`, `category`, `path`, `message`, `sources`, and `remedy`.
Categories distinguish missing information, contradictions, analyst choices,
unsupported methods, and dependencies. Both checking and running use R's shared
preparation logic; a successful check does not establish scientific assumptions.

Responses contain `ok` and `issues`. On success, analysis responses include the
estimate, standard error, 95% interval, degrees of freedom, selected declarations,
versions, input digest, and assumptions. No observation table or list of current
row identifiers is returned. Inspection exposes supplied metadata, which can itself
contain sensitive information; it is not a redaction service.

Handles identify immutable byte snapshots and are owned by the MCP session. A
changed source file requires opening a new revision. The server accepts at most
eight bundles of 16 MiB compressed each, with a separate 256 MiB uncompressed
limit enforced by R. It does not evict active studies. Restart the server to clear
the registry; handles do not survive restart. Temporary R input files are removed
after each call. Direct embedded callers share their supplied server lifespan.
Metadata responses are limited to 32 KiB of JSON and fail explicitly above that
limit. They are not moved into RMCP's shared oversized-result cache; paginated
inspection of larger studies is future work.

For required study validation in a development environment:

```sh
R_LIBS="$PWD/.local-r-library" RMCP_REQUIRE_STUDY_TESTS=1 \
  uv run pytest tests/unit/tools/test_studies.py tests/integration/tools/test_studies.py
R_LIBS="$PWD/.local-r-library" RMCP_REQUIRE_STUDY_TESTS=1 \
  Rscript rmcp/r_assets/run_tests.R
```

The initial route accepts already-created bundles. Collection imports, source
assertions, and supported transformations are performed through SuperDF before
opening a new immutable revision. Existing RMCP table tools remain available and
do not gain an implicit claim of study validation.

Before release, run the full Python, MCP protocol, and R regression suites in an
environment with the optional study dependencies, as well as lint, type,
documentation, and distribution checks. The protocol fixture compares inference
with direct R and exercises an ordinary `linear_model` call in the same session.
Deterministic tests establish transport and numerical behavior; evaluating whether
an agent asks for missing evidence and declines unsupported inference is a separate
rollout gate. Persistent shared study storage, metadata editing through MCP, and
additional estimators remain outside this route.
