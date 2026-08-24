# Goal: gpc / local-skill

## Working directory and identity

- Work ONLY in this worktree: `.worktrees/gpc-local-skill`. Do not touch the
  main checkout or sibling worktrees.
- Branch: `goal-batch/gpc/local-skill`
- Base: the integrated Wave 1 HEAD of this batch (your worktree already starts
  there -- the `compiler/` package, the cleaned `goal_lane.dot`, and the
  `generated/` namespace are all present and reviewed).
- Reference design: `docs/plans/2026-08-24-goal-plan-compiler-resolve-design.md`
  (sections "Decision", "Local backend", "Trust model per backend").
- **The compiler integration contract you build against:**
  `compiler/README.md` in this same worktree. Read it fully. It documents the
  exact `plan.json` fields, the `compile_plan`/`load_plan`/`build_plan`
  signatures + `PlanValidationError`, the `python -m compiler PLAN_JSON [-o OUT]`
  CLI, the generated `$param` requirements, and the new
  `budgets.lane_wall_timeout_seconds` / `waves[].concurrency` fields. Integrate
  against that document; you do not need to re-read the compiler implementation.

## What you own

`skills/goal-batch-attractor/` (new directory -- this repo has no `skills/`
tree yet, so you are creating it). Do not modify `compiler/`, `pipelines/`,
`generated/`, or root `README.md`.

## Complete when

Complete when **either** every item below reaches a terminal state, **or** it
is conclusively demonstrated the remainder cannot, naming the blocker for each.
Items ending FAIL or BLOCKED are residuals, not failures of the goal.

Terminal states: `PASS` / `FAIL-named` / `BLOCKED-named` / `PENDING-HUMAN`.

## Items

- **D1 -- `skills/goal-batch-attractor/SKILL.md` exists with correct frontmatter.**
  YAML frontmatter per the Amplifier Agent Skills spec: `name:
  goal-batch-attractor`, a `description`, `user-invocable: true`, and
  **`shortcut: goal-batch-attractor`** (this registers `/goal-batch-attractor`).
  It MUST NOT claim the shortcut `goal-batch` -- that name is deliberately not
  ours (see the design doc's Decision/Non-Goals). Verify the frontmatter parses
  as valid YAML.
- **D2 -- The skill body drives the LOCAL flow end to end.** Documented steps a
  reader (human or agent) follows: (1) decompose a pile of work into lanes with
  machine-checkable stop conditions -- reference/reuse the `goalify` skill's
  discipline rather than reinventing it; (2) determine dependency waves; (3)
  emit a `plan.json` conforming to `compiler/README.md`'s schema; (4) invoke the
  deterministic compiler (`python -m compiler <plan.json> -o <out.dot>`) to
  generate the parent pipeline; (5) run it LOCALLY via the attractor /
  `pipeline-runner` CLI against a local target repo checkout. Include the
  bootstrap-vs-light trust-mode choice from the design doc (default = keep
  bootstrap; `--light` = supervisor+worktrees only for small batches).
- **D3 -- Two explicit human checkpoints are specified**, matching the
  goal-batch discipline this skill is modeled on: a plan-review stop before
  compiling/launching, and it must never auto-submit. State them plainly in
  the body.
- **D4 -- The compiler contract is referenced, not duplicated.** The skill must
  point at `compiler/` as the single source of truth for plan.json shape and
  invocation -- do NOT restate the full schema inline in a way that will drift.
  A short pointer + the one canonical invocation line is correct; a copy of the
  whole schema is a defect (it will rot). State how you kept it DRY.
- **D5 -- Skill loads/valided.** Demonstrate the skill is discoverable and its
  frontmatter is well-formed. If a local `load_skill`-style validation is not
  available in this worktree, at minimum parse the frontmatter with a YAML
  parser and confirm required keys + the `shortcut` value, and record exactly
  how you validated it.

## Host capability limits

Documentation/authoring lane -- you are writing a SKILL.md and any small
companion files it needs, not running cloud infrastructure. Do not attempt a
real Resolve submission (that is the sibling `resolve-skill` lane's job, in a
different repo). Live services are read-only evidence.

## Process rules

- **Commit early, push always.** Push as you commit.
- **Never merge to `main`.** The orchestrator merges. Stay on your branch.
- **YAGNI.** Author the skill; do not also refactor the compiler or invent new
  compiler features. If you find the contract is missing something you need,
  that is a residual to record, not a change to make in `compiler/`.
- **Time bound: 2 hours (7200s).** Exceeding it is a terminal `BUDGET` state --
  write `DONE.json` truthfully, do not rush.
- **`DONE.json` is already gitignored at the repo root** -- confirm before
  writing, do not commit it.
- **Write `DONE.json` in the worktree root as your final act.** Fields:
  `lane` (`"local-skill"`), `session_id`, `verdict`
  (`COMPLETE`/`BLOCKED`/`PARTIAL`), `branch`, `head`, `pushed` (bool),
  `items` (D1-D5 as `{id, state, note}`), `residuals`, `pending_human`,
  `suite` (this lane has no pytest suite -- record how you validated D5, e.g.
  "frontmatter parsed, shortcut=goal-batch-attractor confirmed").

## KNOWN

- This repo has no existing `skills/` directory -- you are establishing it.
  Look at how other Amplifier skills are structured (frontmatter + markdown
  body; optional `scripts/` and `examples/`) before authoring. The kenergy
  `goaltractor` skill is a conceptual cousin (goal decomposition -> pipeline)
  but is NOT in this repo and is explicitly a SEPARATE, simpler tool -- do not
  depend on it or copy it wholesale; this skill is the `goal_plan_smoke`-family
  compiler front end.
- The two Amplifier mode/skill shortcut rules that matter here: `shortcut:`
  defaults to the skill name if omitted; set it explicitly to
  `goal-batch-attractor`. Do NOT set it to `goal-batch`.
