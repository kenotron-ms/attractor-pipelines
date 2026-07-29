# Sample: Exhaustive Parallel-Lane PR Review

`pipelines/pr-review-exhaustive/pr-review-exhaustive.dot` — an exhaustive, thread-isolated pull
request review pipeline. Ported into this samples repo from
[`microsoft/amplifier-app-actions`](https://github.com/microsoft/amplifier-app-actions)'s
`pipelines/pr-review-exhaustive/pr-review-exhaustive.dot`. The review logic is faithful to the
source; the runtime coupling was reworked so it runs on this repo's engine
(the loop-pipeline / attractor engine that
[`amplifier-resolver-dot-graph`](https://github.com/microsoft/amplifier-resolver-dot-graph)
drives) with no dependency on the source's composite action or custom bundle
profiles.

## What it does

A single-session reviewer satisfices: it finds a few issues, posts, and stops.
This pipeline instead runs **five independent reviewer lanes**, each on its own
`thread_id` (a fresh LLM context), so no lane can anchor on what another lane
already said. Data flows between nodes only through pipeline state
(`context_updates` → `$variable`), never through thread history, so the lanes
stay isolated even though the engine executes them sequentially.

```
start
  └─ checkout_and_read        (fetch PR metadata + unified diff + changed files)
       ├─ lane_correctness    (logic bugs, edge cases, exceptions, races)      [thread]
       ├─ lane_architecture   (layering, coupling, leaky abstractions)         [thread]
       ├─ lane_patterns       (API misuse, naming, dead code, magic values)    [thread]
       ├─ lane_tests          (coverage gaps, test quality)                    [thread]
       └─ lane_pedantic       (spelling, docstrings, nits — diff only)         [thread]
  └─ merge_findings           (dedupe by file:line, prioritize, elevate, verdict)
  └─ quality_eval             (goal_gate: adversarial completeness check)
       ├─ outcome=success  → comment_draft
       └─ outcome!=success → merge_findings   (retry synthesis; lanes preserved)
  └─ comment_draft            (post ONE inline PR review + labels via curl)
  └─ done
```

- **Merge** (`merge_findings`) collects all five lanes, deduplicates by
  `file:line`, orders `CRITICAL → HIGH → MEDIUM → LOW`, **elevates** a finding a
  tier when ≥2 lanes flag the same file, sets the verdict
  (`CHANGES_REQUESTED` if any `CRITICAL`/`HIGH`), and builds the inline-comment
  JSON with ` ```suggestion ` blocks.
- **Quality gate** (`quality_eval`, `goal_gate=true`, `retry_target="merge_findings"`)
  adversarially checks the *synthesis* — completeness, evidence, dedup,
  verdict consistency, organization. On FAIL it loops back to `merge_findings`
  only (the five lane sessions are preserved); on SUCCESS it continues.
- **Post** (`comment_draft`) submits one GitHub PR **review** with inline
  comments (`POST /repos/{o}/{r}/pulls/{n}/reviews`, event `APPROVE` /
  `REQUEST_CHANGES`), falls back to a single top-level PR comment on HTTP 422,
  and applies labels `reviewed` / `changes-requested`.

## Runtime assumptions (self-contained)

The graph runs on any resolver runtime that provides:

| Requirement | Why |
|---|---|
| An **anthropic** provider (model `claude-sonnet-4-6`, set in `model_stylesheet`) | Every reviewer/merge/gate node is an LLM `box` node. |
| A **bash** tool | Every GitHub interaction — metadata, diff, changed-files, clone, POST review, labels — is plain `curl` / `git` / `python3`. No custom `github_*` tools. |
| `ANTHROPIC_API_KEY` in env | Provider auth. |
| `GH_TOKEN` in env | Used directly by the `curl` / `git` commands inside node prompts. |
| `$goal` carrying a PR reference | A full PR URL, `OWNER/REPO#N`, or `#N`. `checkout_and_read` parses it. |

## Running it

**dot-graph resolver (remote source — no local checkout):**

```
git+https://github.com/kenotron-ms/dot-graph-samples@main#subdirectory=pipelines/pr-review-exhaustive/pr-review-exhaustive.dot
```

**GitHub Actions:** see
[`.github/workflows/pr-review-exhaustive.yml`](../../.github/workflows/pr-review-exhaustive.yml)
— a `pull_request` workflow (never `pull_request_target`) with
`permissions: { contents: read, pull-requests: write }` that runs the pipeline
via `microsoft/amplifier-app-actions@main` as the CI runner for the same
engine, pointing `attractor_source` at this file over git+https.

## Intentional omission: the broken "Path B" convergence loop

The source graph had an optional, issue-triggered "Path B" convergence loop in
`comment_draft` that emitted a
`/resolve new_instance(... path="./.amplifier-resolve/simple-fix.dot" ...)`
command. That `simple-fix.dot` file **does not exist anywhere in the source
repository** — Path B was a dangling reference. It has been removed wholesale
here, along with the `loop_exhausted` / `next_round` pipeline state that fed it,
so this sample is internally coherent and self-demonstrating. This pipeline
handles the direct `pull_request` trigger (Path A) only.

## Validating

Validate with the loop-pipeline engine's DOT validator (same one the other
samples use), e.g.:

```python
from amplifier_module_loop_pipeline.dot_parser import parse_dot
from amplifier_module_loop_pipeline.validation import validate

diags = validate(parse_dot(open("pipelines/pr-review-exhaustive/pr-review-exhaustive.dot").read()))
assert not [d for d in diags if d.severity == "ERROR"]
```
