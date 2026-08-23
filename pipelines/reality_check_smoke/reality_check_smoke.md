# reality_check_smoke -- smoke test for the Amplifier Resolve reality-check broker

This pipeline exists for exactly one purpose: to prove, end to end, that the
Amplifier Resolve platform's reality-check capability actually works --
broker admission, Incus runner spin-up, DTU provisioning, deployment,
validation, verdict callback, and retrieval -- by performing one trivial,
cheap, real action and having reality-check independently confirm it took
effect. It is a smoke test, not a production pipeline: no planning, no
rubric, no fix loop.

**Read this before submitting a job for this pipeline.** Unlike
`resolve_hello_world.md` (which documents two *optional-if-you-skip-a-step*
submission requirements), this pipeline has a requirement that is
**invasive and must be a conscious choice**: it commits and pushes directly
to the target repo's default branch, with no PR and no review.

## Why a direct push to the default branch is required (not a shortcut)

Reality-check's `software_path` -- confirmed from the one proven, non-wip
reference implementation in this ecosystem
(`amplifier-resolver-dot-graph/.../pipelines/reality_check.dot`'s
`BuildArtifact` node) -- is always constructed as a bare
`https://github.com/<owner>/<repo>` URL, with **no branch or ref qualifier
anywhere in that code path**. A plain `git clone` of a bare repo URL checks
out the repository's default branch. There is no confirmed mechanism (in
`amplifier_resolver_sdk`, in `amplifier-resolve`'s broker routes, or in the
one reference pipeline) for pointing reality-check's clone at a specific
branch or ref.

That means: for reality-check's own fresh clone (performed inside its own
Incus-provisioned DTU, entirely separate from this pipeline's worker
container) to ever see the trivial claim file this pipeline writes, the
file must land on the repo's actual default branch. Pushing it to a new
feature branch, or opening a PR and leaving it unmerged, would make the
claim genuinely invisible to reality-check's own verdict -- the pipeline
would then just be checking that reality-check inspected some *other*,
unrelated, pre-existing repo state, defeating the entire point of the
exercise (proving that a real, freshly-performed action is independently
confirmed).

Given that hard constraint, this pipeline's `WriteClaimAndPush` node pushes
straight to `https://github.com/<repo>` using `GH_TOKEN` directly (bypassing
whatever the local `origin` remote is configured as -- it may be a Gitea
sidecar mirror per `resolve_hello_world.dot`'s own documented platform
behavior, which reality-check's clone would never reach), onto whatever
branch is currently checked out. **Only submit this job against a
disposable/scratch repo you do not mind being modified directly.**

## Submission requirements

| Requirement | Why |
|---|---|
| `repo` param = a repo slug (`owner/name`) you can push **directly to its default branch** | See above -- reality-check's software_path has no branch qualifier. |
| `GH_TOKEN` present in the worker container env, with push rights to that repo | `WriteClaimAndPush` pushes with `https://x-access-token:${GH_TOKEN}@github.com/...` directly; if the repo has branch-protection rules that block direct pushes to the default branch (required PRs, required reviews, required status checks), the push will fail and the pipeline reports `smoke.result=failed` / `rc.failure_mode=local_push_failed` without ever calling reality-check. |
| `AMPLIFIER_RESOLVE_ENABLE_REALITY_CHECK=true` set on the resolve backend | Reality-check is feature-gated. If unset, the broker returns HTTP 501; `reality_check_invoke.py` catches this and writes a real (non-crashing) failure verdict with `failure_mode=config` -- the pipeline still completes, `smoke.result=failed`, `rc.status=not_attempted` is NOT what you'll see here (you'll see a real broker-side `failed` status with `failure_mode=config`), so check `rc.failure_mode` in the final report to tell this apart from a local push failure. |
| Must be submitted to the **dot-graph** resolver specifically | `RealityCheck`'s tool_command invokes `/opt/uv-tools/amplifier/bin/python -m amplifier_resolver_dot_graph.handlers.reality_check_invoke` -- this module, and the SDK-enabled Python interpreter at that path, are provided by the dot-graph resolver's own worker environment, not by this pipeline repo. This pipeline is not portable to other engines/resolvers, deliberately (same category of non-portability as `resolve_hello_world.dot` and `resolve_expert_builder.dot`). |

### Recommended first run

Point `repo` at a small, public, disposable scratch repo you fully control,
with **no branch protection** on its default branch, so the only two
variables you're testing are (a) the broker/runner/DTU round trip itself and
(b) this pipeline's own logic -- not GH_TOKEN scope or branch-protection
interactions.

### In natural language

> "Submit a dot-graph job using pipeline
> `git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/reality_check_smoke/reality_check_smoke.dot`,
> against `repo=<owner>/<scratch-repo>` (a repo you can push directly to the
> default branch of, no PR). Requires the resolve backend to have
> `AMPLIFIER_RESOLVE_ENABLE_REALITY_CHECK=true` set."

### Via the CLI / `remote.py`

```bash
remote.py call dot-graph \
  "git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/reality_check_smoke/reality_check_smoke.dot" \
  --params '{"repo": "<owner>/<scratch-repo>"}'
```

Then watch it:

```bash
remote.py watch <instance_id>
```

## What "done" looks like

The pipeline's final `Report` node states the outcome in prose, but the
authoritative, machine-checkable evidence is the `smoke.result` context
field (`"passed"` | `"failed"`), backed by `rc.verdict`, `rc.status`,
`rc.failure_mode`, and `rc.session_id`. A human-readable copy is also
written to `.reality-check-smoke/verdict.md` inside the worker's workspace.

`smoke.result="passed"` means: the file was written, pushed to the real
target repo, and a **live** reality-check broker session -- running in its
own Incus-provisioned DTU, entirely independent of this pipeline's worker
container -- cloned that repo fresh and confirmed the file exists with
exactly the expected content. That is the full round trip this smoke test
exists to prove.

## Open questions / things this pipeline could NOT verify from source alone

Per this repo's own working agreements (see `AGENTS.md` / `docs/primer.md`
§7: "evidence over claims... never fabricate"), the following were **not**
independently confirmed by reading source, and are flagged here rather than
silently assumed:

1. **Runner network reachability.** Whether the Incus reality-check runner
   sub-container (which performs its own independent `git clone` of
   `software_path` inside its own DTU) has outbound network egress to reach
   `github.com` at all, and what credential path it uses if the target repo
   is private. The broker route code read for this pipeline
   (`amplifier-resolve/src/amplifier_resolve/routes/reality_checks.py`)
   treats `software_path` as an opaque string forwarded to the runner; the
   runner's own git-clone implementation and its network/DNS/egress policy
   were not traced. **Recommendation: start with a public scratch repo** to
   remove any private-repo-auth variable from the first live test.
2. **Whether the locally-checked-out branch name really always equals the
   real repo's default branch name.** `WriteClaimAndPush` assumes this (it
   pushes `HEAD:<currently-checked-out-branch-name>`), which should hold for
   a repo freshly cloned by the platform's standard `workspace_spec()` clone
   step, but was not independently verified against every possible
   `delivery_mode`/workspace configuration this resolver supports.
3. **DOT-attribute-string escaping for very long, multi-quote shell/python
   payloads.** This pipeline avoids the ambiguity by using the same defensive
   pattern already proven in `resolve_hello_world.dot` (python heredocs with
   single-quoted string literals only, `chr(10)` for embedded content
   newlines, zero literal double quotes inside the heredoc body) rather than
   the shell `case`/`printf`-with-embedded-`\n` pattern used by
   `reality_check.dot`'s own `BuildArtifact` node (which appeared, on close
   reading, to use a different/heavier escaping convention than the rest of
   this repo's pipelines -- not reconciled here). This pipeline was **not**
   executed against a live attractor engine as part of authoring it;
   recommend a dry run (or this repo's own lint/test tooling, if any covers
   DOT parsing) before a live DTU submission.

None of the above are guesses baked into the pipeline's logic -- they are
either sidestepped by design choice (item 3) or stated as an explicit
pre-flight recommendation (items 1-2) rather than asserted as fact.

## Pipeline shape

```
pipelines/reality_check_smoke/
  reality_check_smoke.dot   # entry pipeline: Start -> WriteClaimAndPush
                             #   -> (ok) PrepareRealityCheckInputs -> RealityCheck
                             #        -> RenderVerdict -> Report -> Exit
                             #   -> (push_failed / crash) MarkPushFailed -> Report -> Exit
```
