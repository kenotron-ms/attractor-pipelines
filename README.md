# attractor-pipelines

Public, real-world DOT pipelines for
[`amplifier-resolver-dot-graph`](https://github.com/microsoft/amplifier-resolver-dot-graph)
(the attractor engine), shared for reference and reuse — not fixtures,
not throwaway samples. Fetch one directly via `git+https://` subdirectory
URLs, or copy and adapt it for your own pipeline.

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

Point the resolver at it via:

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

Point the resolver at it via:

```
git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/pr-review-exhaustive/pr-review-exhaustive.dot
```
