---
name: goal-batch-attractor
description: >
  Turn a pile of work into a deterministically-compiled goal_plan_smoke-family
  attractor pipeline and run it LOCALLY against a target repo checkout. Decompose
  the work into lanes with machine-checkable stop conditions, group the lanes into
  dependency waves, emit a plan.json, compile it with the deterministic `compiler/`
  (no LLM in that step), then run the generated parent .dot via the attractor /
  pipeline-runner CLI. Use when the user wants to batch multi-lane work through the
  goal_plan_smoke compiler locally: "goal-batch-attractor", "compile this plan and
  run it", "batch these lanes as an attractor pipeline". Two human checkpoints:
  review the plan before compiling/launching, and never auto-submit. This is the
  goal_plan_smoke-family compiler front end -- it is NOT the `goal-batch` tmux/goal
  orchestrator (that owns /goal-batch), and NOT the kenergy `goaltractor` skill.
user-invocable: true
shortcut: goal-batch-attractor
argument-hint: "<the pile of work to batch> [--light]"
version: 0.1.0
license: MIT
---

# Goal-Batch-Attractor (local)

Compile a pile of work into a `goal_plan_smoke`-family attractor pipeline and run
it **locally**. You decompose the work into lanes, the deterministic `compiler/`
turns that spec into a parent `.dot`, and the attractor / `pipeline-runner` CLI
runs it against a local checkout of the target repo.

You are the ORCHESTRATOR of the *authoring* half: decompose, compose the spec,
compile, launch, report. The generated pipeline owns the rest — worktree isolation,
supervision, parent-side verification, integration, correction, and terminal
selection. Do not re-implement any of that here.

**Identity — what this is and is NOT.** This is a from-scratch, unproven
up-and-comer for the `goal_plan_smoke`-family compiler specifically.

- It deliberately claims **`/goal-batch-attractor`**, never `/goal-batch`. That
  name belongs to a different, existing tool (the tmux + `/goal`-session batch
  orchestrator) and is reserved until this skill is actually proven out.
- It is **not** the kenergy `goaltractor` skill — a separate, simpler, local-only
  goal-runner. Do not depend on or copy it.

**Input** — `$ARGUMENTS`: the pile of work to batch (or a pointer to where it is
enumerated), optionally followed by `--light` (trust mode, see below). If there is
genuinely no work to plan against, say so in one line and ask for it — one
question, not an interview.

$ARGUMENTS

---

## Two human checkpoints (non-negotiable)

This skill stops for a human exactly twice. Everything between is mechanical.

1. **Plan review, before anything is compiled or launched.** Show the lane split,
   waves, ownership, and per-lane stop conditions. Nothing is compiled and nothing
   runs until the user has seen the plan and said go. (Pre-authorization in the
   invocation itself is valid — post the plan for the record and proceed.)
2. **Never auto-submit.** This is the LOCAL front end. It runs against a local
   target-repo checkout only. It never pushes the compiled pipeline to a remote for
   cloud execution and never submits to the Amplifier Resolve platform — that is the
   sibling cloud submission skill's job, deliberately out of scope here.

---

## The local flow

### 1 — Decompose into lanes (reuse `goalify`, do not reinvent)

Load the **`goalify`** skill and apply its discipline per lane. Its rules are the
single source of truth for what a good stop condition looks like — outcome-first,
machine-checkable, with a disjunctive exit and per-item negative terminals. Do not
restate or re-derive those rules here.

Each lane must have:

- **A deterministic, machine-checkable verifier** — the argv that decides PASS/FAIL
  from real evidence, not a self-report. This becomes the lane's `verifier_argv`,
  and its marker becomes `marker_file` / `marker_content`.
- **Disjoint file ownership.** Two lanes that would touch the same file either fold
  into one lane, or one owns it and the other records the needed edit as a residual.
- **A provable outcome that does not need a sibling to finish first** — unless that
  dependency is captured as a real wave edge (step 2).

### 2 — Determine dependency waves

Group lanes into waves by dependency:

- **Wave 1** lanes are independent and launch **concurrently** from a shared base
  commit.
- Each **later wave** launches **sequentially** from the current integration HEAD,
  which already contains every prior-integrated lane. A lane in wave N+1 is
  structurally reachable only after every wave-N lane is integrated — that is what
  enforces the dependency, so `depends_on` must be consistent with wave order and
  `integration_order`.

Pin the base SHA every wave-1 lane forks from, and produce an `integration_order`
that is a wave-monotonic permutation of all lanes.

### 3 — Emit `plan.json`

Write a `plan.json` conforming to the compiler's input schema. **`compiler/README.md`
is the authoritative, single source of truth for every field, type, default, charset
rule, and the `child_dot` resolution rules — read it and build against it.** Do not
copy the full schema into this skill or into your plan's prose; a copy will rot.

A minimal illustrative shape (not the full schema — see `compiler/README.md`):

```json
{
  "plan_id": "my_plan",
  "lanes": {
    "auth": {
      "wave": 1, "depends_on": [],
      "verifier_argv": ["/bin/sh", "-c", "test -f artifacts/auth.done"],
      "marker_file": "artifacts/auth.done", "marker_content": "auth:ok"
    },
    "api": {
      "wave": 1, "depends_on": [],
      "verifier_argv": ["/bin/sh", "-c", "test -f artifacts/api.done"],
      "marker_file": "artifacts/api.done", "marker_content": "api:ok"
    }
  },
  "waves": [{"wave": 1, "concurrency": 2}],
  "integration_order": ["auth", "api"],
  "terminals": ["COMPLETE", "RESIDUALS_READY", "INFRA_FAILURE", "ABORTED"]
}
```

Real work usually wants `budgets.lane_wall_timeout_seconds` well above the smoke
default (real lanes need minutes, not seconds) and `budgets.max_adaptive_attempts_per_lane`
per the lane's difficulty. Both are optional and documented in `compiler/README.md`.

> The hand-authored `pipelines/goal_plan_smoke/plan.json` is **audit-era fixture
> data, not a compiler input** — it carries `waves[].concurrency` as a description
> string and will be rejected by the compiler (`concurrency must be an integer`).
> Use `compiler/README.md`'s field list as the schema, not that file.

### --- CHECKPOINT 1: plan review (human) ---

Present the plan — lanes, waves, ownership, base SHA, per-lane stop conditions, and
what the batch will and will NOT deliver. Wait for `go`. Do not compile or launch
before this.

### 4 — Compile (deterministic; no LLM)

One canonical invocation (the compiler's own contract — see `compiler/README.md`
"Invocation contract"):

```bash
python3 -m compiler <plan.json> -o <out.dot>
```

Run it from the repo root so the `compiler` package is importable. Exit `0` writes
the parent `.dot`; exit `2` prints `error: invalid plan spec: <named reason>` and
writes nothing — the message names the offending lane/field, so fix the spec and
recompile. Same spec in, byte-identical DOT out.

Validate the generated DOT before running it — it must lint with **zero
ERROR-severity diagnostics**. The compiler ships `compiler.validate.validate_dot_source`
(locates the attractor engine from the `amplifier-bundle-attractor` cache and raises
`EngineUnavailable` if it is not present); `attractor lint` on the output is the
equivalent CLI check when the CLI is on PATH.

### 5 — Run locally

Run the generated parent `.dot` via the attractor / `pipeline-runner` CLI
(`python -m amplifier_module_pipeline_runner.cli run <out.dot> ...`) against a local
checkout of the target repo.

The generated pipeline needs a set of engine-substituted `$param` values at launch
(`$target_repo`, `$state_root`, `$worktree_root`, `$product_base_sha`,
`$runtime_py_dir`, `$subgraphs_dir`, `$git_bin`, `$runner_pythonpath`,
`$plan_json_path`, `$parent_dot_path`, and the delivery params). **The full list,
with meanings, is in `compiler/README.md` "What the generated pipeline needs at run
time" and is echoed in the header comment of every generated `.dot`** — supply them
from there rather than memorizing a copy. `$runtime_py_dir` and `$subgraphs_dir`
point at this repo's reused `pipelines/goal_plan_smoke/python/` and `subgraphs/`
(unchanged by the compiler).

**Trust mode — default vs `--light`:**

| | Default (bootstrap) | `--light` |
|---|---|---|
| Bootstrap / launch-descriptor / sealed-runtime layer | **Yes** | No |
| Supervisor (bounded wall timeout, normalized exit codes) | Yes | Yes |
| Worktree + budget-ledger registry | Yes | Yes |
| Use for | Shared / CI / untrusted hosts | Small ad-hoc batches on a trusted local host |

- **Default** keeps the bootstrap/descriptor/sealing trust layer (`goal_plan_bootstrap.py`).
  It is already generic and free to reuse; local hosts can be shared or CI too. Its
  external launch-descriptor + disjoint-roots prerequisites are documented in
  `pipelines/goal_plan_smoke/goal_plan_smoke.md` — follow that, do not restate it.
- **`--light`** (passed in `$ARGUMENTS`) drops only the bootstrap layer and runs
  supervisor + worktrees directly. It is a flag on this skill, not a separate
  architecture. Use it only when that ceremony is unwarranted.

### --- CHECKPOINT 2: never auto-submit ---

A local run against a local checkout is the end of this skill's road. Do not push
the compiled pipeline anywhere for cloud execution and do not submit to Resolve.
Report terminals (`COMPLETE` / `RESIDUALS_READY` / `INFRA_FAILURE` / `ABORTED`) and
any residuals verdict-first.

---

## Single source of truth (how this stays DRY)

The compiler is the one home for plan shape and invocation. This skill deliberately
holds only:

- **one pointer** — `compiler/README.md` — for the full `plan.json` schema, the
  `$param` runtime contract, and the `child_dot`/charset rules;
- **one canonical invocation line** — `python3 -m compiler <plan.json> -o <out.dot>`;
- **one small illustrative example**, clearly marked as illustrative, not a schema.

For the decomposition discipline it points at the **`goalify`** skill; for the
default-mode bootstrap prerequisites it points at
`pipelines/goal_plan_smoke/goal_plan_smoke.md`. Nothing here restates a schema, a
param table, or a lint rule that lives elsewhere — so when the compiler contract
changes, this skill does not silently drift.
