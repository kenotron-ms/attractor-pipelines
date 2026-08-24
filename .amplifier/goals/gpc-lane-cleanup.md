# Goal: gpc / lane-cleanup

## Working directory and identity

- Work ONLY in this worktree: `.worktrees/gpc-lane-cleanup`. Do not touch the
  main checkout or sibling worktrees.
- Branch: `goal-batch/gpc/lane-cleanup`
- Base SHA: `85e9d18` (docs: add goal-plan-compiler-resolve design)
- Reference design: `docs/plans/2026-08-24-goal-plan-compiler-resolve-design.md`,
  section "Reused building blocks" (the `goal_lane.dot` bullet) and the
  genericity-audit table under "Background and Source Analysis" item 6.

## What you own

`pipelines/goal_plan_smoke/subgraphs/goal_lane.dot` ONLY. Do not touch
`pipelines/goal_plan_smoke/goal_plan_smoke.dot` (the parent that references
this subgraph via `dot_file=`), any other file under `pipelines/`, `compiler/`,
`skills/`, `generated/`, or root `README.md` -- other lanes own those in this
same batch and are running concurrently in sibling worktrees. If you find you
need to touch something outside your file to make this work, that is a
residual: record exactly what edit is needed and why, do not make it, and
record it in `DONE.json`'s `residuals` field.

## Complete when

Complete when **either** every item below reaches a terminal state, **or**
it is conclusively demonstrated the remainder cannot, naming the blocker for
each. Items ending FAIL or BLOCKED are residuals, not failures of the goal.

Terminal states: `PASS` / `FAIL-named` / `BLOCKED-named` / `PENDING-HUMAN`.

## Items

- **D1 -- Remove the smoke-test-only fixture.** This subgraph's `Attempt`
  node prompt hardcodes a seeded-failure test fixture conditioned on
  `$seeded_failure=true`, whose only current caller is `lane_b` in
  `goal_plan_smoke.dot`. Remove this fixture branch from the prompt text (or
  make it a cleanly optional, clearly-labeled test-only parameter with a
  documented default) so the subgraph is reusable for arbitrary lanes outside
  the original 3-lane smoke test, without carrying dead test-fixture weight
  into every future invocation.
- **D2 -- Prove `goal_plan_smoke`'s existing behavior is unchanged.** The
  parent `goal_plan_smoke.dot` still invokes this subgraph for `lane_a`,
  `lane_b`, `lane_c` with the exact same `$param` contract (`$lane_id`,
  `$marker_file`, `$marker_content`, `$seeded_failure`, `$runtime_py_dir`,
  `$output_root`, `$evidence_path`, `$max_attempts`). Your change must not
  alter the observable contract (inputs/outputs) of this subgraph for those
  existing callers. State exactly how you verified this (a structural diff of
  the subgraph before/after against the same params, or an equivalent proof)
  -- do not just assert it.
- **D3 -- Validates.** The modified subgraph still parses/validates cleanly
  (same tooling note as other lanes in this batch: `attractor lint` if
  available, else the engine's `parse_dot()`/`validate()` library call
  directly -- `command -v attractor` first to check). Zero ERROR-severity
  diagnostics.
- **D4 -- Existing Python test suite unaffected.** Run
  `python3 -m pytest pipelines/goal_plan_smoke/python/tests/ -q` and confirm
  it still passes at its existing count (this lane does not touch Python, so
  this should be a no-op regression check, not new work -- if it somehow
  regresses, that is a `FAIL-named` item naming exactly what broke).

## Host capability limits

No live LLM generation required for this lane -- this is a text edit to an
existing `.dot` file plus a validation/proof pass. The `attractor` CLI may
not be on PATH; check and fall back to the library call as needed. Live
shared services are read-only evidence; use fixtures.

## Process rules

- **Commit early, push always.** Push as you commit.
- **Never merge to `main`.** The orchestrator merges. Stay on your branch.
- **Time bound: 1.5 hours (5400s).** Exceeding it is a terminal `BUDGET`
  state -- write `DONE.json` truthfully, do not rush.
- **`DONE.json` is already gitignored at the repo root** -- confirm before
  writing, do not commit it.
- **Write `DONE.json` in the worktree root as your final act.** Fields:
  `lane` (`"lane-cleanup"`), `session_id`, `verdict` (`COMPLETE` /
  `BLOCKED` / `PARTIAL`), `branch`, `head`, `pushed` (bool), `items` (D1-D4
  as `{id, state, note}`), `residuals`, `pending_human`, `suite` (exact
  pytest summary line from D4).

## KNOWN

- Baseline: `pipelines/goal_plan_smoke/python/tests/` passes cleanly today
  (part of the repo's overall 104-test baseline). This lane's D4 is a
  regression check against that baseline, not new coverage.
- This subgraph is referenced by `goal_plan_smoke.dot` via a relative
  `dot_file=` path -- do not rename the file or move it; only edit its
  contents.
- The `seeded_failure` fixture exists specifically to let `lane_b` simulate a
  failed first attempt in the original smoke test -- removing it changes
  smoke-test *test coverage* for that scenario, which is expected and fine;
  it must not change `lane_a`/`lane_c`'s behavior (which never set
  `seeded_failure=true`) at all.
