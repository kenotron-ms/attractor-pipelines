# Goal-Plan Compiler

A **deterministic** Python generator: a `plan.json`-shaped spec in, a
`goal_plan_smoke`-family parent `.dot` out. **No LLM anywhere in this code
path** — same spec in, byte-identical DOT out. (Rationale: the design doc,
`docs/plans/2026-08-24-goal-plan-compiler-resolve-design.md`. An LLM
re-authoring the parent graph per request risks reintroducing the exact class
of bug fixed in commit `fc27a29`.)

It generalizes the hand-authored exemplar
`pipelines/goal_plan_smoke/goal_plan_smoke.dot` — the `LaunchLaneX` /
`ParentVerifyX` / `IntegrateX` node triples, the wave-gating edges, and the
aggregation shell loops — into a generator correct for arbitrary **N lanes
across M waves**.

> **This document is the integration contract.** Wave-2 lanes (a local-facing
> skill in this repo and a cloud-facing skill in `amplifier-bundle-resolve`)
> integrate against *this file* without reading the implementation. If a field
> or signature below changes, it is a breaking change for those consumers.

---

## Invocation contract

### As a Python module

```python
from compiler import compile_plan, load_plan, build_plan, PlanValidationError

# From a file path:
dot_source: str = compile_plan(load_plan("plan.json"))

# From an already-parsed dict:
dot_source: str = compile_plan(build_plan(spec_dict))

# compile_plan also accepts a raw dict directly (validates internally):
dot_source: str = compile_plan(spec_dict)
```

Signatures (stable public API, re-exported from `compiler/__init__.py`):

| Callable | Signature | Behavior |
|---|---|---|
| `compile_plan` | `compile_plan(spec: dict \| Plan) -> str` | Returns the parent `.dot` source. Validates a raw dict via `build_plan` first. |
| `load_plan` | `load_plan(path: str \| Path) -> Plan` | Loads + validates a JSON spec file. |
| `build_plan` | `build_plan(spec: dict) -> Plan` | Validates + normalizes a raw dict. |
| `PlanValidationError` | `ValueError` subclass | Raised on any missing/invalid field; message always names the offending lane/field. |

### As a CLI

```bash
python -m compiler PLAN_JSON [-o OUTPUT_DOT]
```

- Writes to `-o`/`--output`, or stdout if omitted.
- Exit `0` on success; exit `2` with `error: invalid plan spec: <named reason>`
  on an invalid plan.

Run it from the repository root (so the package `compiler` is importable), or
ensure the repo root is on `PYTHONPATH`.

---

## `plan.json` fields the compiler reads

Only the fields below are consumed. Extra fields (e.g. `schema_version`,
`description`, `product_base_sha`, `waves[].concurrency`, `static_correspondence`)
are ignored — they may remain in the spec for humans/audit without affecting
output.

### Top level

| Field | Type | Required | Meaning |
|---|---|---|---|
| `plan_id` | string | **yes** | Digraph name and label stem. Must be a valid DOT id (e.g. `goal_plan_smoke`). |
| `lanes` | object | **yes** | Map of `lane_id -> lane spec` (see below). Non-empty. |
| `waves` | array | **yes** | `[{ "wave": <int>, ... }]`. Wave numbers must be strictly increasing and unique. Only `wave` is read. |
| `integration_order` | array[string] | **yes** | A permutation of all lane ids. Must be **non-decreasing by wave** (every earlier-wave lane precedes every later-wave lane). |
| `terminals` | array[string] | no (default `["COMPLETE","RESIDUALS_READY","INFRA_FAILURE","ABORTED"]`) | Emitted verbatim into the `plan_terminals` graph attribute. |
| `branch_namespace` | string | no (default: `plan_id` with `_`→`-`) | Prefix for per-lane git branches (`<namespace>/<lane_id>`). |
| `budgets` | object | no | Only `max_adaptive_attempts_per_lane` (int ≥ 1, default `3`) is read → each lane's `max_attempts`. |
| `correction` | object | no | Only `child_dot` (default `subgraphs/integration_correction.dot`) is read. |
| `delivery` | object | no | Only `child_dot` (default `subgraphs/deliver_pr.dot`) is read. |

### Per-lane spec (`lanes[<lane_id>]`)

| Field | Type | Required | Meaning |
|---|---|---|---|
| `wave` | int ≥ 1 | **yes** | Which wave the lane belongs to. Must appear in top-level `waves`. |
| `depends_on` | array[string] | **yes** (may be empty) | Lane ids this lane depends on. Each must be a known lane. Advisory/structural; wave gating is enforced by construction. |
| `verifier_argv` | array[string] | **yes**, non-empty | The lane's deterministic parent-side verifier argv. Embedded verbatim into the `ParentVerify` node as a Python list literal. |
| `marker_file` | string | **yes** | The lane's marker file name. Passed to the child lane pipeline. |
| `marker_content` | string | **yes** | Expected marker content. Passed to the child lane pipeline. |
| `seeded_failure` | bool | no (default `false`) | Passed through to the child lane pipeline (test-fixture flag). |
| `child_dot` | string | no (default `subgraphs/goal_lane.dot`) | Child lane pipeline; only the basename is used (joined to `$subgraphs_dir`). |
| `branch` | string | no (default `<branch_namespace>/<lane_id>`) | The lane's git branch. |

A missing required field, a lane whose `wave` is not declared in `waves`, an
`integration_order` that is not a wave-monotonic permutation of the lanes, or a
`depends_on` referencing an unknown lane each raises `PlanValidationError` with
a message naming the offending lane/field — never a malformed graph.

---

## What the generated pipeline needs at run time (`$param` context)

The compiler emits a `goal_plan_smoke`-family parent whose nodes reference these
engine-substituted params. The executing backend (local CLI or Resolve worker)
must supply them:

| Param | Meaning |
|---|---|
| `$target_repo` | Integration repo/worktree the run operates on. |
| `$state_root` | Run-scoped state directory (contracts, ledgers, results, evidence). |
| `$worktree_root` | Where per-lane worktrees are created. |
| `$delivery_state_root` | Delivery bookkeeping root (admission). |
| `$run_id` | Unique run id. |
| `$repo` | `owner/name` (used only when `$delivery_enabled=true`). |
| `$delivery_enabled` | `"true"` / `"false"`. |
| `$product_base_sha` | Base commit every **wave-1** lane worktree forks from. |
| `$runtime_py_dir` | Absolute path to the goal_plan runtime python dir (`goal_plan_runtime.py`, `goal_plan_supervisor.py`). |
| `$subgraphs_dir` | Absolute path to the reused `subgraphs/` dir. |
| `$git_bin` | Authenticated `git` argv prefix (single token). |
| `$runner_pythonpath` | `PYTHONPATH` (colon-joined) for the child runner process. |
| `$plan_json_path` | Path to this pipeline's `plan.json` — read by the correspondence check. |
| `$parent_dot_path` | Path to this generated parent `.dot` — read by the correspondence check. |

> `$plan_json_path` and `$parent_dot_path` are the compiler's generalization of
> the exemplar's hard-coded correspondence paths. Everything else matches the
> exemplar's param contract.

This lane (the compiler) does **not** modify or re-implement the reused runtime
(`goal_plan_runtime.py`, `goal_plan_supervisor.py`) or subgraphs
(`goal_lane.dot`, `integration_correction.dot`, `deliver_pr.dot`) — it only
generates the parent that drives them.

---

## Execution model of the generated graph

Faithful to the exemplar:

- **Wave 1** — every lane is launched **concurrently** from `$product_base_sha`
  via a `component` fan-out (`Wave1Launch`) into a `tripleoctagon` fan-in
  (`Wave1Collect`), then classified (`ClassifyWave1`).
- **Later waves** — each lane is launched **sequentially, just-in-time** from
  the current integration `HEAD` (which already contains every prior integrated
  lane). This is what structurally guarantees the wave gate: a wave-N+1 lane's
  `LaunchLane` node is reachable only via the previous lane's `Integrate`
  `ACCEPTED` edge, which itself sits behind every wave-N `ACCEPTED` edge. It
  mirrors the exemplar's `LaunchLaneC`. (Trade-off: intra-later-wave lanes are
  serialized rather than parallelized — correct, and simpler; wave-1
  parallelism is preserved.)
- All lanes are parent-verified (`ParentVerifyX`, using the lane's own
  `verifier_argv`) and integrated (`IntegrateX`, with a cumulative
  existence-aggregate over the lanes integrated so far) one at a time in
  `integration_order`.
- Then the shared tail: pre-coherence aggregate → cross-lane coherence review
  (the one LLM `box` node, `fidelity=full`) → bounded 1-round correction →
  affected-closure aggregate → freeze + lane sweep → final aggregate →
  optional delivery → cleanup → terminal carriers
  (`COMPLETE` / `RESIDUALS_READY` / `INFRA_FAILURE` / `ABORTED`).

The aggregation/coherence shell loops are **data-driven** from the spec's lane
ids (`for f in <lane ids>`), not literal `lane_a lane_b lane_c` strings.

Node naming: lane nodes are suffixed by **position in `integration_order`**
(`A`, `B`, `C`, … `Z`, `AA`, …), reproducing the exemplar's `LaunchLaneA` for
`lane_a` while staying collision-free for arbitrary lane ids.

---

## Validating generated output (D3)

The generated DOT is validated against the attractor engine's own
`parse_dot()` / `validate()` (design doctrine — must be zero ERROR-severity
diagnostics). The `attractor` CLI is often not on PATH and the engine module
(`amplifier_module_loop_pipeline`) is usually not pip-installed — it ships in
the `amplifier-bundle-attractor` cache. `compiler/validate.py` locates it, in
order:

1. a normal import (if installed / on `PYTHONPATH`);
2. `$AMPLIFIER_LOOP_PIPELINE_DIR` (dir *containing* the package);
3. a glob of `~/.amplifier/cache/*/modules/loop-pipeline`.

```python
from compiler.validate import validate_dot_source, EngineUnavailable

try:
    graph, diagnostics, error_count = validate_dot_source(dot_source)
    assert error_count == 0
except EngineUnavailable:
    ...  # engine not present in this environment; skip
```

---

## Tests

`compiler/tests/test_compiler.py` covers:

- **D2** — structural equivalence of the generated 3-lane/2-wave graph to the
  hand-authored `goal_plan_smoke.dot` (node ids, shapes, edges, wave-gating
  topology, graph attrs), plus an explicit reachability check.
- **D3** — generated output validates with zero ERROR diagnostics (3-lane and
  2-lane plans).
- **D4** — a 2-lane single-wave plan, the 3-lane/2-wave plan, and invalid plans
  (missing `lanes` / `integration_order` / a lane's `wave`; non-monotonic
  `integration_order`) producing clear, named errors.
- Escaping round-trip and determinism.

Run:

```bash
python -m pytest compiler/tests/ -q
```

Engine-dependent tests (`D2`, `D3`) skip gracefully when the attractor engine
cannot be located, so the pure-Python `D4` tests run in any environment.
