# attractor-pipelines

Public, real-world DOT pipelines for the attractor bundle, shared for
reference and reuse — not fixtures, not throwaway samples. Fetch one
directly via `git+https://` subdirectory URLs, or copy and adapt it for
your own pipeline.

## Convention

Each pipeline lives in its own `pipelines/[name]/` folder containing its
entry `.dot` file (`pipelines/[name]/[name].dot`), any `subgraphs/`, and
optional companion docs (e.g. `[name].md`).

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

Like `idea_to_shipped`, the build logic lives in its own subgraph rather
than being inlined into the top-level file -- this is what keeps the
rubric-driven exit condition legible in one place (see
`subgraphs/build_verify.dot`) and keeps the top-level graph itself short:
accept design, plan (including the rubric), delegate to build_verify,
delegate to deliver_pr, report.

```
pipelines/idea_to_pr/
  idea_to_pr.dot            # entry pipeline (arc only -- delegates via shape=folder)
  subgraphs/
    build_verify.dot         # implement -> self-evaluate against rubric -> fix (backstop-capped)
    deliver_pr.dot            # commit, push, open PR
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
