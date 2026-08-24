# attractor-pipelines

Public, real-world DOT pipelines for the attractor bundle, shared for
reference and reuse — not fixtures, not throwaway samples. Fetch one
directly via `git+https://` subdirectory URLs, or copy and adapt it for
your own pipeline.

## Convention

Each pipeline lives in its own `pipelines/[name]/` folder containing its
entry `.dot` file (`pipelines/[name]/[name].dot`), any `subgraphs/`, and
optional companion docs (e.g. `[name].md`).

## Pipeline: hello world

`pipelines/hello_world/hello_world.dot` — the minimal end-to-end demo in
this repo: given `$repo`, write a `hello_world.txt` file and open a PR with
it. No planning, no rubric, no verification tiers, no fix loop — just
write → commit → push → open PR. Useful as a smoke test for a
resolver/runtime setup (prove the engine can reach a repo, write a file,
and open a PR end to end) and as the simplest possible reference for the
`shape=folder` delegation pattern (`subgraphs/deliver_pr.dot`) used
throughout this repo's other pipelines.

```
pipelines/hello_world/
  hello_world.dot           # entry pipeline
  subgraphs/
    deliver_pr.dot            # commit, push, open PR
```

Point the attractor bundle at it via:

```
git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/hello_world/hello_world.dot
```

## Pipeline: resolve hello world

`pipelines/resolve_hello_world/resolve_hello_world.dot` — a sibling of
`hello_world.dot` with the same minimal shape (write → commit/push → open
PR), but deliberately **not** portable across engines: it leans on
Amplifier Resolve platform mechanism as much as possible instead of staying
engine-agnostic.

- **Clone** and **migrate to Gitea** are not pipeline steps — both are
  handled automatically by the platform (`workspace_spec()` + Gitea sidecar
  mirroring) before the pipeline's `Start` node ever fires.
- **PR delivery** goes through the platform's provider-agnostic
  `/usr/local/bin/create-pr` script (injected into every worker container)
  instead of raw `gh`/`curl` — it resolves GitHub-vs-Gitea destination and
  auth (GitHub App token first, PAT fallback) from container env, so the
  pipeline never touches credentials directly.

Use `hello_world.dot` instead if this pipeline needs to run outside an
Amplifier Resolve worker container (`create-pr` will not exist there).

```
pipelines/resolve_hello_world/
  resolve_hello_world.dot         # entry pipeline
  resolve_hello_world.md          # required reading: how to SUBMIT this job correctly
  subgraphs/
    deliver_pr_resolve.dot          # commit, push, open PR via create-pr
```

Point the attractor bundle at it via:

```
git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/resolve_hello_world/resolve_hello_world.dot
```

**Before submitting a job for this pipeline, read
[`pipelines/resolve_hello_world/resolve_hello_world.md`](pipelines/resolve_hello_world/resolve_hello_world.md)**
-- real PR delivery requires two instantiation params
(`delivery_mode=promote` + an optional matching `branch_name`) that this
pipeline cannot request on its own after the instance is already running.
This is the reference example in this repo for correct remote PR delivery
via the Amplifier Resolve platform.

## Pipeline: resolve expert builder

`pipelines/resolve_expert_builder/resolve_expert_builder.dot` -- an
autonomous, seven-stage spec-to-PR builder, ported from
[`microsoft/amplifier-resolver-dot-graph`](https://github.com/microsoft/amplifier-resolver-dot-graph)'s
`expert_builder.dot`. Given a high-level spec and an existing target repo,
it runs unattended end to end: an autonomous admission gate (no human in
the loop) -> decompose the hard parts and spike each in parallel ->
fan-in to an ordered implementation plan -> implement task-by-task ->
validate by using the build like a new user would -> an INDEPENDENT
reality-check against the original spec -> deliver as a GitHub PR. Like
`resolve_hello_world.dot`, this pipeline is deliberately **not portable**
-- it leans on Amplifier Resolve platform mechanism (a live Gitea sidecar,
the platform's reality-check and promote/pr endpoints, and the worker Python
environment) as heavily as the source pipeline always did. The original port
changed only the four `dot_file=` sub-pipeline paths for this repository's
layout. It now also carries the finalized upstream graph-level `ResumeGate`
from commit `c36ab0f`: on every engine start, the gate inspects durable `.ai/`
artifacts and resumes at admission, decomposition, synthesis, or plan
verification. All existing work nodes, prompts, validation loops,
reality-check behavior, and delivery behavior remain unchanged.

```
pipelines/resolve_expert_builder/
  resolve_expert_builder.dot              # entry pipeline (7 stages)
  resolve_expert_builder.md                # required reading: platform dependencies + submission params
  resolve_expert_builder.resolver.yaml    # ported resolver manifest, for reference
  subgraphs/
    admission.dot                         # autonomous admission gate
    expert_builder_explorer.dot           # per-hard-part spike + package (parallel fan-out)
    reality_check.dot                     # independent reality-check against the original spec
    deliver_promote.dot                   # commit, push, open PR via the platform promote/pr endpoint
  python/
    admission_lint.py                     # invoked by admission.dot's Lint node (reference only)
    reality_check_invoke.py               # invoked by reality_check.dot's RealityCheck node (reference only)
    reality_check.py                      # copy-paste SDK node handlers (reference only)
```

Point the attractor bundle at it via:

```
git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/resolve_expert_builder/resolve_expert_builder.dot
```

**Before submitting a job for this pipeline, read
[`pipelines/resolve_expert_builder/resolve_expert_builder.md`](pipelines/resolve_expert_builder/resolve_expert_builder.md)**
-- it requires `spec`, `repo_url` (must already exist), and
`delivery_mode=promote`, and explains why the `python/` files are included
for reference only and are not directly runnable in this repo.

## Pipeline: idea-to-shipped SDLC pipeline

`pipelines/idea_to_shipped/idea_to_shipped.dot` — a full "idea to shipped"
lifecycle pipeline, mined from real successful Amplifier Resolve
session arcs (brainstorm/think -> plan -> build with a verdict-gated
fix loop -> PR -> human merge gate -> human deploy gate -> report).

This one is meant to be read and adapted. It demonstrates:

- `shape=folder` phase delegation (`subgraphs/build_loop.dot`,
  `subgraphs/deliver_pr.dot`, `subgraphs/merge_gate.dot`,
  `subgraphs/deploy_gate.dot`)
- A verdict-file-driven fix loop with a capped retry counter
  (`CheckFixRounds`, `loop_restart=true`)
- Both hexagon human-gate styles: freeform (merge approval) and
  multiple-choice (deploy decision)
- `outcome=fail` fallback edges so a crashing tool node never dead-ends
  the pipeline

```
pipelines/idea_to_shipped/
  idea_to_shipped.dot         # entry pipeline
  subgraphs/
    build_loop.dot            # implement -> verify -> quality -> fix loop
    deliver_pr.dot            # commit, push, open PR
    merge_gate.dot            # human approval -> rebase/test -> merge
    deploy_gate.dot           # human decision -> deploy prod/staging/hold
```

Point the attractor bundle at it via:

```
git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/idea_to_shipped/idea_to_shipped.dot
```

## Pipeline: exhaustive PR review pipeline

`pipelines/pr-review-exhaustive/pr-review-exhaustive.dot` — a thread-isolated, five-lane pull
request review pipeline, ported from
[`microsoft/amplifier-app-actions`](https://github.com/microsoft/amplifier-app-actions)
and reworked to run self-contained on this repo's engine. Five reviewer lanes
(correctness, architecture, patterns, tests, pedantic) each run on their own
`thread_id` (fresh LLM context), then a merge node deduplicates/prioritizes, an
adversarial quality gate (`goal_gate` with a `retry_target` loop) checks the
synthesis, and a final node posts one inline GitHub PR review plus labels — all
via plain `curl`/`git` (only an anthropic provider, a bash tool, and `GH_TOKEN`
are required).

Like `idea_to_shipped`, this one is meant to be read and adapted. See
[`pipelines/pr-review-exhaustive/pr-review-exhaustive.md`](pipelines/pr-review-exhaustive/pr-review-exhaustive.md) for the
full walkthrough, runtime assumptions, and the intentionally-omitted broken
"Path B" convergence branch. A ready-to-use `pull_request` workflow (never
`pull_request_target`) lives at
[`.github/workflows/pr-review-exhaustive.yml`](.github/workflows/pr-review-exhaustive.yml).

Point the attractor bundle at it via:

```
git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/pr-review-exhaustive/pr-review-exhaustive.dot
```

## Pipeline: idea-to-shipped (lite)

`pipelines/idea_to_pr/idea_to_pr.dot` — a lower-ceremony
derivative of `idea_to_shipped`, for the common case: idea -> plan -> build
according to plan, without the full pipeline's plan-approval gate or
three-agent build loop. Differences from `idea_to_shipped`:

- No `PlanConfidenceCheck` / `PlanApproval` human gate — Plan always flows
  straight into Implement.
- One combined Implement step plus an independent SelfEvaluate (judge)
  step, instead of separate implementer / verifier / quality-reviewer
  agents.
- **Completion is gated by a weighted, user-facing rubric, not a round
  count and not a bare pass/fail self-report.** Plan follows the
  [rubric-design methodology](https://github.com/microsoft/amplifier-bundle-evaluation/blob/main/context/methodology/rubric-design.md):
  name the 2-3 things that separate genuinely good work from
  competent-looking-but-shallow work first, phrase every criterion as an
  *observable question judged from a user's vantage point* (not "does the
  file exist" — "does submitting an empty required field show an inline
  error naming which field is missing?"), mark the heavy-hitting criteria
  `CRITICAL:`, and weight points by discriminating power rather than
  splitting them evenly. The rubric (`.resolve/plan/rubric.json`) also
  carries its own evidence-gathering `steps` and a `pass_threshold`
  (default 0.85). Since the rubric lives in its own file, Plan is required
  to reference it back into the human-readable plan doc — an "Acceptance"
  subsection per task naming its criteria, points, and description — so a
  human skimming the plan alone understands what "done" means. SelfEvaluate
  gathers/re-gathers that evidence itself and scores every criterion
  (partial credit per the criterion's own stated rule, not an invented
  scale) before the loop can exit — it does not trust Implement's own
  claim. A round counter still exists as a **safety backstop** (default 2)
  against a truly non-convergent loop, but it isn't the completion
  mechanism — if it trips, the pipeline reports `build.verdict=escalated`
  and lists which criteria are still short of full points rather than
  silently declaring success.
- Stops after opening the PR — no `MergeGate` / `DeployGate` subgraphs. The
  normal GitHub PR review is the human gate, and the `ship_ready` pipeline
  (below), triggered by the PR itself, handles preview/prod deploy.
- A **narrower, three-tier Verification Driven Development hierarchy**
  (vs. `idea_to_shipped`'s five-tier ladder), picked in this preference
  order per task: (1) unit tests for library code, (2) a lightweight
  jsdom + node test environment for integration tests, (3) real
  browser-based verification (playwright-cli / browser-tester) reserved for
  the genuinely hardest-to-verify things — focus management, accessibility,
  visual layout truth — not the default path.

Unlike `idea_to_shipped`, this pipeline is a **single flat file, no
subgraphs** -- the build/verify loop and the commit/push/PR delivery
sequence are inlined directly at the root level rather than delegated via
`shape=folder`. That makes the pipeline's one real cycle (Implement ->
SelfEvaluate -> Fix -> SelfEvaluate, bounded by the fix-round backstop)
visible directly in the graph, instead of hidden a level down in a
subgraph -- see `docs/RUBRIC.md`'s doctrine on why a pipeline's cycles are
what make it an attractor rather than a flowchart.

```
pipelines/idea_to_pr/
  idea_to_pr.dot            # entry pipeline -- everything inlined, single file
```

Point the attractor bundle at it via:

```
git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/idea_to_pr/idea_to_pr.dot
```

## Pipeline: fast parallel PR review

`pipelines/pr_review/pr_review.dot` — a redux of
`pr-review-exhaustive` built for turnaround measured in minutes rather than
exhaustive thoroughness. The exhaustive pipeline's 5 reviewer lanes run on
separate `thread_id`s (session isolation) but still **sequentially** through
the graph — lane N+1 doesn't start until lane N finishes. This pipeline
fixes that with genuine wall-clock parallelism:

- `shape=component` fans the 5 lanes out as concurrent asyncio branches
  (`max_parallel=5`, `join_policy="wait_all"`), joined via
  `shape=tripleoctagon`.
- Since parallel branches get a cloned/isolated context, each lane writes
  its findings directly to a fixed file path (`.resolve/review/*.json`)
  rather than depending on `context.parallel.results` plumbing; a single
  tool node (`collect_lane_results`) reads them back into the same flat
  variables the merge step expects.
- Drops the adversarial `quality_eval` retry loop that
  `pr-review-exhaustive` has around its merge step — worth the extra
  sequential round for exhaustiveness, not worth it for a fast pass. Merge
  goes straight to posting the review.

```
pipelines/pr_review/
  pr_review.dot         # entry pipeline (self-contained, no subgraphs)
```

Point the attractor bundle at it via:

```
git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/pr_review/pr_review.dot
```

## Pipeline: ship_ready (CI/CD bootstrap + Vercel/Supabase deploy)

`pipelines/ship_ready/ship_ready.dot` — ensures a repo has a working
CI/CD pipeline, then drives its actual deploys. One graph, two modes,
selected by a router node (`DetectMode`) reading `$github_event_name`:

- **Bootstrap mode** (no GitHub event context — run manually against a
  repo, or from `idea_to_pr`): idempotently writes
  `.github/workflows/deploy.yml` if missing or stale (detected via a stable
  marker comment, not just file existence), configuring it to deploy a
  Vercel **preview** on every `pull_request` and Vercel **prod** + a
  Supabase migration on every push to the default branch. Commits the
  workflow if written; no-ops if already current.
- **Runtime mode** (invoked *by* that generated workflow —
  `$github_event_name` is `pull_request` or `push`): performs the actual
  deploy for the event that fired, each followed by a curl-poll-with-backoff
  liveness check (inside the `tool_command`'s own shell loop, not repeated
  graph-level LLM retries) before declaring success — never claims a
  deploy is live without proving it.

Together with the other two pipelines in this repo: `idea_to_pr`
opens a PR, `pr_review` posts a fast automated review on it, and this
pipeline's `pull_request` job (via the PR's own GitHub Actions run) gives it
a live Vercel preview — merging to main then triggers a real Vercel prod
deploy + Supabase migration.

```
pipelines/ship_ready/
  ship_ready.dot             # entry pipeline (self-contained, no subgraphs)
```

Point the attractor bundle at it via:

```
git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/ship_ready/ship_ready.dot
```

## Pipeline: goal_plan_smoke (multi-lane parallel goal/plan attractor family)

`pipelines/goal_plan_smoke/goal_plan_smoke.dot` — the canonical member of the
Goal Plan Attractor family: a static, reviewed parent program that runs an
explicit three-lane dependency plan (`lane_a` and `lane_b` concurrently in
Wave 1, `lane_c` in Wave 2 once both are integrated) as visible DOT control
flow, not a hidden runtime scheduler. Each lane runs in its own Git worktree
and its own headless child Attractor process, reaped by a small
Python-standard-library supervisor that owns raw `waitpid` truth — an
artifact existing on disk is never treated as success without that
supervisor's exit/signal evidence. Parent candidate verification runs in a
clean, disposable, detached worktree at the exact candidate commit;
passing commits integrate sequentially with an aggregate check after every
merge; a bounded (one-round) cross-lane coherence correction and a
final-HEAD lane sweep run before an optional exact-head-verified PR
delivery, cleanup, and one of four explicit terminal states
(`COMPLETE` / `RESIDUALS_READY` / `INFRA_FAILURE` / `ABORTED`).

See `pipelines/goal_plan_smoke/goal_plan_smoke.md` for the stable
identity-anchor guide (prerequisites, trusted-verification route, terminal
states) and `docs/primer.md` + `docs/RUBRIC.md` for the attractor doctrine
this family is authored against.

```
pipelines/goal_plan_smoke/
  goal_plan_smoke.dot            # static parent: waves, integration, coherence, delivery, terminals
  goal_plan_smoke.md              # identity-stable history-anchor guide
  plan.json                       # immutable design-time/audit data (lanes, waves, budgets, terminals)
  python/
    goal_plan_bootstrap.py          # trusted external bootstrap (descriptor auth, sealed runtime materialization)
    goal_plan_runtime.py            # admission, worktrees, budgets, verifier envelopes, integration, cleanup (library, no CLI)
    goal_plan_supervisor.py         # per-child reaper: run/poll/terminate/reconcile, authoritative exit/signal truth
    tests/                          # pytest coverage for all three modules
  subgraphs/
    goal_lane.dot                    # bounded per-lane attempt/verify/diagnose convergence loop
    integration_correction.dot        # bounded (1-round) shared-branch coherence correction
    deliver_pr.dot                    # exact-final-HEAD PR delivery, adapted from this repo's proven deliver_pr pattern
```

This pipeline is not meant to be fetched and run standalone the way the
other pipelines in this repo are — it requires an externally installed
trusted bootstrap, launch descriptor, and process-supervision prerequisites
described in `goal_plan_smoke.md`. It is included here as the reference
example for a multi-lane, worktree-isolated, supervisor-verified parallel
goal/plan attractor.

## Namespace: generated/ (machine-generated, NOT curated)

`generated/` is the one deliberate exception to this repo's identity. Every
pipeline above is hand-authored, reviewed content "shared for reference and
reuse." `generated/` is the opposite: a **machine-generated, ephemeral
fallback landing zone** for the goal-plan compiler, used *only* when a
compiled goal-plan pipeline's target repo is **not** GitHub-hosted (the
normal, GitHub-hosted case commits the artifact into the target repo itself,
never here). Task-specific `plan.json` + compiled parent `.dot` artifacts land
here on disposable `resolve/goal-plan-<run-id>` branches — **never on `main`**,
never reviewed, never meant to be copied as an example.

Do not mistake anything that appears under `generated/` for a reviewed
reference pipeline. The only files that live there on `main` are its own
`README.md` and the `prune-branches.sh` retention tool; the actual generated
artifacts exist only on those disposable branches and are pruned on a
documented schedule (default: older than 30 days).

See [`generated/README.md`](generated/README.md) for the full contract, the
GitHub-vs-non-GitHub placement rule, and the prune policy. Background:
[`docs/plans/2026-08-24-goal-plan-compiler-resolve-design.md`](docs/plans/2026-08-24-goal-plan-compiler-resolve-design.md)
("Repository placement decision rule").

```
generated/
  README.md              # the contract: fallback-only, never main, not curated
  prune-branches.sh       # manual retention tool (dry-run by default)
```
