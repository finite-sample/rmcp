# Analyze a study with its collection context

The optional study tools use R studyframe bundles. Existing RMCP tools continue to
accept ordinary tables with their current behavior. Study tools initially support
numeric survey means, complete-outcome randomized effects, and explicitly
model-based regressions. Unsupported requests return issues and do not switch
estimators automatically.

Install R studyframe 0.3.0 from its GitHub release on the execution host. The R
package is named `studyframe`; its source repository is `gojiplus/superdf`. It is
not yet available from CRAN. Install its dependencies first, including `arrow`
for bundles and `survey` and `estimatr` for the supported estimators:

```sh
mkdir -p .local-r-library
export R_LIBS="$PWD/.local-r-library"
Rscript -e 'install.packages(c("digest", "jsonlite", "jsonvalidate", "arrow", "survey", "estimatr", "zip"), repos = "https://cloud.r-project.org", lib = Sys.getenv("R_LIBS"))'
Rscript -e 'install.packages("https://github.com/gojiplus/superdf/releases/download/v0.3.0/studyframe_0.3.0.tar.gz", repos = NULL, type = "source", lib = Sys.getenv("R_LIBS"))'
uv run rmcp start
```

`zip` is needed to create example bundles. The Python reader is not required for
this route; the server delegates to R. Package installation and metadata edits
are explicit operations; the study tools do neither automatically. Existing RMCP
tools remain usable without these optional R dependencies.

Create a demonstration bundle from an R session using the same library:

```r
library(studyframe)
source(system.file("examples", "simulated_study.R", package = "studyframe"))
study <- collect_study(simulate_population())
write_studyframe(study, "collected.studyframe")
```

Start RMCP with the file inside an allowed filesystem root, then call:

```json
{"file_path": "/allowed/path/collected.studyframe"}
```

Pass that to `inspect_study`. Use its returned `study_ref` in an analysis
request. For example, `run_study_analysis` accepts:

```json
{
  "study_ref": {
    "file_path": "/allowed/path/collected.studyframe",
    "sha256": "<sha256 returned by inspect_study>"
  },
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
  "study_ref": {
    "file_path": "/allowed/path/collected.studyframe",
    "sha256": "<sha256 returned by inspect_study>"
  },
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
at estimation time. studyframe distinguishes received responses from randomized units
and requires a complete-roster declaration for this effect adapter. It still cannot
independently certify the truth of a producer's declaration. Missing or dropped
experimental outcomes remain unsupported.

`check_study_analysis` accepts the same request and calls studyframe's public
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

A study reference identifies a file's exact bytes with its original authorized
path and SHA-256. Every call checks the current filesystem access policy,
reads a bounded snapshot, and passes those same bytes to R. Checking or running
analysis refuses a changed file before invoking R. Inspect a changed file to get
a new reference. The hash identifies content; it grants no permission.

References do not depend on a transport connection or server registry. They can
be reused after reconnecting or restarting, provided the file still exists,
remains authorized, and has the same bytes. Relative paths remain relative to
the server's current working directory; use an absolute path for stable local
references. RMCP's existing allowed roots and deployment access policy apply;
these tools do not introduce per-user isolation or a persistent artifact store.

Bundles are limited to 16 MiB compressed per call, with a separate 256 MiB
uncompressed limit enforced by R. Temporary snapshot files are removed after
each call. No study bytes are retained in a server registry.
Metadata responses are limited to 256 KiB of JSON and fail explicitly above that
limit. Real questionnaires with hundreds of variables can exceed 32 KiB before
adding collection evidence. The larger finite limit accommodates these codebooks;
study responses remain inline and never enter RMCP's shared oversized-result cache.
Paginated inspection of larger studies is future work.

## Run the handoff from a local client

The executable example uses the official MCP client to inspect a bundle, check
the supplied request, and run it only when the check succeeds:

```sh
uv run python examples/analyze_study.py /path/to/collected.studyframe request.json \
  --output receipt.json
```

The server starts with the bundle's directory as its filesystem root. It inherits
the client's R library configuration. The report contains inspection metadata,
the requirements check, and the analysis receipt, with no observation rows.
It refuses to overwrite an existing output file and exits nonzero when the
request is refused. See the [official SDK client documentation](https://py.sdk.modelcontextprotocol.io/client/).

## Explicit model-based regression

Regression requires a studyframe build exporting `regression_request()`; the
0.3.0 release supports only means and effects. The server reports an actionable
dependency issue if that API is unavailable. A regression request uses variable
identifiers rather than executable formulas:

```json
{
  "kind": "regression",
  "outcome": "recall_extremity",
  "predictors": ["recall_rank"],
  "cluster": "respondent_id",
  "se_type": "stata",
  "missing": "omit",
  "target": "Association among observed recall records",
  "assumptions": ["Respondent clusters are independent; the linear conditional mean is an adequate working model."]
}
```

The result returns one entry per model term in `estimate.coefficients`, each with
`term`, `value`, `standard_error`, `lower`, `upper`, `p_value`, and
`degrees_of_freedom`. The receipt records the target, assumptions, exclusions,
and variance choice. An explicit regression request does not establish randomized
assignment or probability sampling, and is never selected as a fallback when
a mean or effect request fails.

To require the regression protocol test instead of skipping when its optional
R API is absent, set `RMCP_REQUIRE_STUDY_REGRESSION=1` when running
`tests/integration/tools/test_studies.py` with the newer R library.

For required study validation in a development environment:

```sh
R_LIBS="$PWD/.local-r-library" RMCP_REQUIRE_STUDY_TESTS=1 \
  uv run pytest tests/unit/tools/test_studies.py tests/integration/tools/test_studies.py
R_LIBS="$PWD/.local-r-library" RMCP_REQUIRE_STUDY_TESTS=1 \
  Rscript rmcp/r_assets/run_tests.R
```

The initial route accepts already-created bundles. Collection imports, source
assertions, and supported transformations are performed through studyframe before
inspecting a new revision. Existing RMCP table tools remain available and
do not gain an implicit claim of study validation.

Before release, run the full Python, MCP protocol, and R regression suites in an
environment with the optional study dependencies, as well as lint, type,
documentation, and distribution checks. The protocol fixture compares inference
with direct R and exercises an ordinary `linear_model` call in the same session.
Deterministic tests establish transport and numerical behavior; evaluating whether
an agent asks for missing evidence and declines unsupported inference is a separate
rollout gate. Persistent shared study storage, metadata editing through MCP, and
additional estimators remain outside this route.
