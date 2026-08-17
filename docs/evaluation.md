# Evaluating MCP Servers and Skills

Shipping an MCP server requires more than checking that its process starts. A useful
release gate verifies the contract, the protocol, the meaning of results, and the
agent's ability to choose the right capability.

## The four evaluation layers

| Layer | What it isolates | Required checks |
|---|---|---|
| Package | Implementation correctness | Unit, integration, lint, type, and dependency-lock checks |
| Contract | Whether tools are safe to call | Unique names, strict JSON Schemas, cross-field validation, bounded outputs, and expected-failure cases |
| Protocol | Whether a real client can use the server | Initialize, discovery, sequential calls, state, approvals, errors, and shutdown through an official MCP client |
| Model | Whether an agent chooses and uses capabilities correctly | Intent-to-tool selection, argument construction, recovery, and collisions between similar tools or skills |

A passing lower layer does not imply that the next layer passes. Run failures at the
lowest layer that can explain them: schema failures before subprocess tests, protocol
failures before agent tests, and deterministic semantic identities before subjective
quality scoring.

## RMCP's executable E2E contracts

`tests/evals/test_mcp_server_evals.py` starts RMCP over stdio and drives it with the
official MCP client. Its cases cover exact statistical identities, malformed and
ragged data, typoed arguments, inert code-like data, formula injection, filesystem
confinement, approval state, write/read workflows, and actionable error recovery.

Run the deterministic suite with:

```bash
uv run pytest tests/evals/test_mcp_server_evals.py
```

Run the same contracts against a packaged production image with:

```bash
RMCP_EVAL_DOCKER_IMAGE=rmcp:production uv run pytest tests/evals/test_mcp_server_evals.py
```

Each case records a stable ID, evaluation layer, user intent, tool call, and an exact
oracle or expected error. Add a regression case whenever production, a review, or a
model-in-the-loop exercise discovers a defect. A test must fail if its assertion is
not reached; skipped or returned checks are not successes.

## Data as code

Treat tool definitions, eval cases, allowlists, and `SKILL.md` files like source code:

1. Keep them versioned and review changes as diffs.
2. Validate syntax and cross-field invariants before execution.
3. Reject unknown fields and duplicate identifiers instead of silently choosing one.
4. Keep data separate from executable expressions. Never construct code by string
   interpolation when a typed operation can express the same request.
5. Test representative valid, boundary, malformed, adversarial, and recovery inputs.
6. Record provenance and use deterministic fixtures for release gates.

For table-shaped inputs, validate non-empty, rectangular columns before invoking R.
For formulas, allow only the operators and function calls the tool actually supports.
For paths, authorize the resolved path before handing it to a subprocess. Return a
sanitized client error while retaining full diagnostics in local logs.

## Detecting overlap

Exact duplicate names and descriptions are build-time failures. Semantic overlap is
a model-level property and needs a labeled intent set. Include direct intents,
paraphrases, deliberately ambiguous prompts, negative controls, and prompts that
should use no tool. Measure the selected tool, arguments, answer correctness,
unnecessary calls, and recovery after a rejected call. Report a confusion matrix by
tool or skill; repeated confusion usually means descriptions or boundaries need to
change.

The same method applies to skills. Lint the front matter and referenced files first,
run the skill in an isolated fixture next, then test selection against neighboring
skills. MCP protocol tests cannot establish that an LLM will choose the right tool,
and a structurally valid `SKILL.md` cannot establish that an agent will follow it.

## A practical "good to go" gate

An MCP server or skill is ready when:

- deterministic checks pass from a clean locked environment;
- advertised inputs and outputs match observed behavior;
- invalid input fails before side effects;
- expected failures are actionable and do not disclose secrets or host details;
- filesystem, network, package, and process boundaries are exercised end to end;
- stateful approval and recovery workflows work through a real client;
- model-level selection meets a declared threshold on held-out intents; and
- the artifact is tested in the same packaging and runtime form that will ship.

Keep the deterministic harness in the project. Extract a shared package only after
multiple servers expose the same stable primitives; premature abstraction tends to
hide server-specific invariants, which are where the consequential defects live.
