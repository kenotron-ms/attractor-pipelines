# dot-graph-samples

Fixture repository for testing the recursive `git+https://` remote
DOT-source feature in
[`amplifier-resolver-dot-graph`](https://github.com/microsoft/amplifier-resolver-dot-graph).

This repo is not a real pipeline — it exists to be **fetched over the
network** by the dot-graph resolver's remote-source machinery, exercising:

- In-origin `shape=folder` subgraph resolution (relative `dot_file=` paths)
- Multi-level recursive fetching (a subgraph that itself references a
  further subgraph)
- Cross-repo (cross-origin) subgraph resolution via a full
  `git+https://github.com/<owner>/<repo>@<ref>#subdirectory=<path>` URL
- That real file writes during a run land in the actual workspace
  (`context.target_dir`), not an ephemeral fetch temp directory

## Reference graph

```
main.dot
  ├── WriteProof              (tool node; writes proof.txt to workspace)
  ├── subgraphs/child.dot     (in-origin, relative dot_file=)
  │     └── subgraphs/grandchild.dot   (in-origin, relative dot_file=; leaf)
  └── git+https://github.com/kenotron-ms/dot-graph-samples-lib@main#subdirectory=lib.dot
        (cross-repo subgraph; see sibling repo)
```

## Usage

Point `amplifier-resolver-dot-graph` at this repo's entry pipeline via:

```
git+https://github.com/kenotron-ms/dot-graph-samples@main#subdirectory=pipelines/main.dot
```

The resolver should recursively fetch and materialize `main.dot`,
`subgraphs/child.dot`, `subgraphs/grandchild.dot` (all from this repo),
and `lib.dot` (from the sibling `dot-graph-samples-lib` repo, a different
origin), then execute the assembled pipeline end-to-end.

## Sibling repo

[`kenotron-ms/dot-graph-samples-lib`](https://github.com/kenotron-ms/dot-graph-samples-lib)
— the cross-repo subgraph library referenced by `main.dot`.

## Sample: idea-to-shipped SDLC pipeline

`pipelines/idea_to_shipped/idea_to_shipped.dot` — a full "idea to shipped"
lifecycle sample pipeline, mined from real successful Amplifier Resolve
session arcs (brainstorm/think -> plan -> build with a verdict-gated
fix loop -> PR -> human merge gate -> human deploy gate -> report).

Unlike the fixture pipeline above (`pipelines/main.dot`), this one is meant
to be read and adapted, not just fetched by resolver tests. It demonstrates:

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
git+https://github.com/kenotron-ms/dot-graph-samples@main#subdirectory=pipelines/idea_to_shipped/idea_to_shipped.dot
```

## Sample: exhaustive PR review pipeline

`pipelines/pr-review-exhaustive.dot` — a thread-isolated, five-lane pull
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
[`pipelines/pr-review-exhaustive.md`](pipelines/pr-review-exhaustive.md) for the
full walkthrough, runtime assumptions, and the intentionally-omitted broken
"Path B" convergence branch. A ready-to-use `pull_request` workflow (never
`pull_request_target`) lives at
[`.github/workflows/pr-review-exhaustive.yml`](.github/workflows/pr-review-exhaustive.yml).

Point the resolver at it via:

```
git+https://github.com/kenotron-ms/dot-graph-samples@main#subdirectory=pipelines/pr-review-exhaustive.dot
```
