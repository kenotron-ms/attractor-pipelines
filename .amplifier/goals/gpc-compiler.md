# Goal: gpc / compiler

## Working directory and identity

- Work ONLY in this worktree: `.worktrees/gpc-compiler` (repo root once the
  worktree is created). Do not touch the main checkout or sibling worktrees.
- Branch: `goal-batch/gpc/compiler`
- Base SHA: `85e9d18` (docs: add goal-plan-compiler-resolve design)
- Reference design: `docs/plans/2026-08-24-goal-plan-compiler-resolve-design.md`
  (read this first -- it is the authoritative spec for this lane; sections
  "The compiler", "Reused building blocks", "plan.json: from audit artifact
  to real compiler input").

## What you own

`compiler/` (new directory, does not exist yet at base SHA) -- and nothing
else. Do not modify `pipelines/goal_plan_smoke/*`, `skills/`, `generated/`,
or root `README.md` -- other lanes own those in this same batch and are
running concurrently in sibling worktrees. If you find you genuinely need to
touch a file outside `compiler/` to make this work, that is a residual: write
down exactly what edit is needed and why, do NOT make it, and record it in
`DONE.json`'s `residuals` field.

## Complete when

Complete when **either** every item below reaches a terminal state, **or**
it is conclusively demonstrated the remainder cannot, naming the blocker for
each. Items ending FAIL or BLOCKED are residuals, not failures of the goal.

Terminal states: `PASS` / `FAIL-named` / `BLOCKED-named` / `PENDING-HUMAN`.

## Items

- **D1 -- The compiler exists and generalizes the parent graph.** A
  deterministic Python package under `compiler/` that takes a `plan.json`-
  shaped spec (see the design doc's schema description: `lanes{}` keyed by
  lane id with `wave`, `depends_on`, `verifier_argv`; `waves[]`;
  `integration_order`; `budgets`; `correction`; `delivery`) and emits a
  `goal_plan_smoke`-family parent `.dot` -- generalizing the hand-written
  `LaunchLaneX`/`ParentVerifyX`/`IntegrateX` node triples, the wave-gating
  edges (a lane in wave N+1 reachable only via wave N's `ACCEPTED` edges),
  and the aggregation/coherence shell loops (`for f in <lane ids>...`,
  data-driven from the spec) -- correct for arbitrary N lanes across M waves.
  No LLM call anywhere in this code path -- read
  `pipelines/goal_plan_smoke/goal_plan_smoke.dot` as the reference exemplar
  to generalize, not to copy verbatim.
- **D2 -- Prove it by regenerating the known-good exemplar.** Feed the
  compiler a `plan.json`-shaped spec equivalent to
  `pipelines/goal_plan_smoke/plan.json` (3 lanes, 2 waves, the same
  dependency shape) and diff the *parsed graph structure* (nodes, edges,
  shapes, wave-gating topology) of your generated output against the
  existing hand-authored `goal_plan_smoke.dot` -- not byte-for-byte text,
  structural equivalence. If exact structural parity isn't achievable, name
  precisely what differs and why, as a named item, not a silent gap.
- **D3 -- Output validates.** Generated `.dot` output validates against this
  repo's own doctrine: parse it with the engine's `parse_dot()`/`validate()`
  (the `attractor` CLI is not on PATH in this environment -- check with
  `command -v attractor` first; if absent, use the Python library call
  directly and document which you used). Zero ERROR-severity diagnostics.
- **D4 -- Unit tests.** Under `compiler/tests/` (or `tests/test_compiler.py`
  if this repo's test runner expects that layout -- check
  `pipelines/goal_plan_smoke/python/tests/` for the existing convention and
  match it), cover at minimum: a 2-lane single-wave plan, the 3-lane/2-wave
  plan from D2, and an invalid `plan.json` (missing a required field)
  producing a clear, named error rather than a malformed graph.
- **D5 -- Integration contract documented.** A short `compiler/README.md`
  documenting exactly the `plan.json` fields the compiler reads and the
  CLI/module invocation contract (function signature or CLI args) --
  Wave 2 lanes in this same batch (a local-facing skill in this repo, and a
  cloud-facing skill in a *different* repo, `amplifier-bundle-resolve`) will
  integrate against this document without reading your implementation. Get
  the contract right; it is load-bearing for two other lanes that haven't
  started yet.

## Host capability limits

No live LLM generation belongs in this lane's own code path -- the compiler
is deterministic Python, by design (see the design doc's rationale: an LLM
re-authoring the parent graph per request risks reintroducing the exact
class of bug fixed in commit `fc27a29`). Live shared services (if any) are
read-only evidence to you; use fixtures for tests.

## Process rules

- **Commit early, push always.** Push as you commit -- do not batch pushes.
- **Never merge to `main`.** The orchestrator merges. Stay on your branch.
- **The disjunctive exit governs completion**, not a feeling of doneness: you
  are complete when every D-item above is PASS, or when you can name exactly
  which remain and why they cannot resolve in this lane.
- **Time bound: 3 hours (10800s).** Exceeding it is a terminal `BUDGET`
  state -- write `DONE.json` with `verdict: "PARTIAL"` and the true state of
  each item, do not rush the last item or skip the final commit to beat the
  clock.
- **`DONE.json` is already gitignored at the repo root** (`/DONE.json` in
  `.gitignore`) -- confirm before writing, do not commit it.
- **Write `DONE.json` in the worktree root as your final act.** Fields:
  `lane` (`"compiler"`), `session_id` (this session's own id), `verdict`
  (exactly one of `COMPLETE` / `BLOCKED` / `PARTIAL`), `branch`, `head`,
  `pushed` (bool), `items` (array of `{id, state, note}` for D1-D5),
  `residuals` (array of strings), `pending_human` (array), `suite` (the
  exact test-run summary line, e.g. "12 passed" -- run it yourself, do not
  guess).

## KNOWN

- Baseline (measured at base SHA, before this lane started):
  `python3 -m pytest --collect-only -q` from the repo root reports **104
  tests collected, 1 pre-existing collection error** in
  `tests/test_resolve_expert_builder_resume_gate.py` (`ModuleNotFoundError:
  amplifier_module_loop_pipeline`) -- this is pre-existing and unrelated to
  this lane. Do not attempt to fix it. Your own new tests are additive to
  this baseline.
- `pipelines/goal_plan_smoke/python/tests/` is the existing convention for
  this repo's Python test layout and passes cleanly today -- look at it for
  style/structure before choosing your own.
- The `attractor` CLI is not installed in this environment
  (`command -v attractor` returns nothing) -- plan D3's validation
  accordingly; do not block on installing it.
