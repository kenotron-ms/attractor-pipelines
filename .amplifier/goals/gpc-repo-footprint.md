# Goal: gpc / repo-footprint

## Working directory and identity

- Work ONLY in this worktree: `.worktrees/gpc-repo-footprint`. Do not touch
  the main checkout or sibling worktrees.
- Branch: `goal-batch/gpc/repo-footprint`
- Base SHA: `85e9d18` (docs: add goal-plan-compiler-resolve design)
- Reference design: `docs/plans/2026-08-24-goal-plan-compiler-resolve-design.md`,
  section "Repository placement decision rule" and the "Always committing
  generated artifacts into `attractor-pipelines`" entry under "Rejected
  Alternatives" (read both -- they define exactly what this namespace is
  and is not for).

## What you own

`generated/` (new top-level directory, does not exist yet at base SHA) and
root `README.md` ONLY. Do not touch `compiler/`, `pipelines/`, or `skills/`
-- other lanes own those in this same batch and are running concurrently in
sibling worktrees. If you find you need to touch something outside your
files to make this work, that is a residual: record exactly what edit is
needed and why, do not make it, and record it in `DONE.json`'s `residuals`
field.

## Complete when

Complete when **either** every item below reaches a terminal state, **or**
it is conclusively demonstrated the remainder cannot, naming the blocker for
each. Items ending FAIL or BLOCKED are residuals, not failures of the goal.

Terminal states: `PASS` / `FAIL-named` / `BLOCKED-named` / `PENDING-HUMAN`.

## Items

- **D1 -- `generated/README.md` exists and states the contract precisely.**
  Per the design doc: this namespace is the documented **fallback** landing
  zone used only when a target repo (for a compiled, task-specific
  goal-plan pipeline) is not GitHub-hosted. It holds task-specific
  `plan.json` + compiled parent `.dot` artifacts, always on a disposable
  `resolve/goal-plan-<run-id>` branch, **never on `main`**, and is explicitly
  *not* part of this repo's curated, reviewed `pipelines/` content. State
  this distinction in the file plainly enough that a future contributor does
  not mistake something under `generated/` for a reviewed reference pipeline.
- **D2 -- A concrete retention/prune policy, not just prose.** This repo has
  no CI cron today (verify: check `.github/workflows/` yourself rather than
  trusting this note) -- so the policy must be a documented, copy-pasteable
  manual command (or a small script under `generated/`) that identifies and
  deletes `resolve/goal-plan-*` branches in this repo older than a stated
  age (30 days is a reasonable default unless you find a reason otherwise --
  state your reasoning either way). It's fine for this to be manual for now;
  it is not fine for it to be undocumented.
- **D3 -- Root `README.md` gets a new section for this namespace.** Match
  the existing convention already used for every other pipeline entry in
  this file (see the `## Pipeline: <name>` sections for `hello_world`,
  `goal_plan_smoke`, etc.) -- a short section explaining what `generated/`
  is, linking to `generated/README.md`, and explicitly noting it is
  machine-generated / not curated content, unlike the rest of this repo.
- **D4 -- `.gitignore` reviewed.** Check whether `generated/` needs any
  local-scratch subpath ignored (e.g. a working directory used only during
  compilation, never committed). If nothing is needed, state `N/A` with your
  reasoning rather than silently skipping this item.

## Host capability limits

Pure documentation/scaffolding work -- no code, no LLM generation required
beyond writing prose and one policy command/script. No live services
involved.

## Process rules

- **Commit early, push always.** Push as you commit.
- **Never merge to `main`.** The orchestrator merges. Stay on your branch.
- **Time bound: 1 hour (3600s).** Exceeding it is a terminal `BUDGET`
  state -- write `DONE.json` truthfully, do not rush.
- **`DONE.json` is already gitignored at the repo root** -- confirm before
  writing, do not commit it.
- **Write `DONE.json` in the worktree root as your final act.** Fields:
  `lane` (`"repo-footprint"`), `session_id`, `verdict` (`COMPLETE` /
  `BLOCKED` / `PARTIAL`), `branch`, `head`, `pushed` (bool), `items` (D1-D4
  as `{id, state, note}`), `residuals`, `pending_human`, `suite` (this lane
  has no test suite of its own -- write `"N/A -- documentation-only lane"`).

## KNOWN

- This repo's README follows a consistent per-pipeline section pattern --
  read at least two existing sections (e.g. "Pipeline: hello world" and
  "Pipeline: goal_plan_smoke...") before writing yours, to match voice and
  structure rather than inventing a new format.
- This repo's own stated identity (top of `README.md`): "Public, real-world
  DOT pipelines... shared for reference and reuse -- not fixtures, not
  throwaway samples." Your job is to carve out an *explicit, documented
  exception* to that identity for `generated/`, not to quietly blur the line
  -- readers should never wonder whether something under `generated/` was
  meant to be a reviewed example.
