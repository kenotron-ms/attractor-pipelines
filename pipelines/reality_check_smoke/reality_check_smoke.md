# reality_check_smoke -- claim-free smoke test for the reality-check broker

This pipeline exercises the real Amplifier Resolve reality-check broker round
trip -- broker admission, Incus runner spin-up, DTU provisioning,
deployment/clone, validation, verdict callback --
**without writing, committing, or pushing anything to the target repo.**

Reality-check only ever needs read access to the target repo, so there is no
local write/push step that can fail, and no scratch-repo requirement.

## The question this file answers

> Does exercising the reality-check broker API actually require the pipeline
> to write/push new content to the target repo first? Or can it validate the
> repo's EXISTING state as-is?

**Answer: no push is required. Reality-check only ever needs read access.**
It clones the target repo fresh, exactly the same whether that repo was just
modified moments ago or hasn't changed in a year.

## Evidence (read from source, not assumed)

### 1. The runner's clone is read-only

`amplifier-resolve/docker/reality-check-runner/src/amplifier_reality_check_runner/inputs.py`,
function `resolve_software_path()` (lines ~122-219 as read):

```python
clone_cmd = ["git", "clone", "--depth", "1"]
if clone_ref:
    clone_cmd += ["--branch", clone_ref]
clone_cmd += [auth_url, str(clone_dest)]

result = subprocess.run(clone_cmd, check=False, capture_output=True, text=True, timeout=300)
```

This is the **only** place `software_path` is ever touched by the runner.
It is a plain `git clone --depth 1` (optionally `--branch <ref>` when the
resolver encoded one via `git+<url>@<ref>` -- see `_split_software_ref()` in
the same file, used by the understudy resolver to pin a working branch).
`auth_url` only ever injects `https://x-access-token:<GH_TOKEN>@github.com/...`
for **read** auth on private repos (comment at line ~169: "Token injection
for private GitHub HTTPS repos"). There is no code path anywhere in this
function, or anywhere else in the runner package, that pushes, commits, or
writes back to the source repo. **Write access to the target repo is never
required or used.**

### 2. Nothing requires a fresh commit

- `amplifier_resolver_sdk/_reality_check.py` (`_rc_start`): POSTs
  `software_path` as an opaque string to
  `POST /api/instances/{id}/broker/reality-check`. No commit-existence
  check, no diffing against a prior state.
- `amplifier-resolve/src/amplifier_resolve/routes/reality_checks.py`
  (`RealityCheckJob`, `_build_runner_config`): forwards `software_path`
  verbatim into the runner's `config.json` (runner field 7). No git
  operations happen in this file at all -- `git clone` (grepped for) does
  not appear anywhere in `reality_checks.py`; all git interaction is
  downstream, inside the runner (see #1).
- `amplifier-resolver-dot-graph/.../handlers/reality_check_invoke.py`
  (`_run_reality_check`): reads `.resolve/reality_check/artifact.json`'s
  `software_path` and `config.json`'s `params.spec`/`acceptance_criteria`,
  then calls the SDK. No local git state is read or required beyond those
  two JSON files.

Since `software_path` is carried as an opaque string end to end and the
runner does a **fresh, read-only clone every time**, acceptance criteria
that are true of the repo's *current* default-branch state validate exactly
as well as criteria written against a claim a pipeline just pushed itself.
There is no dependency on freshness, recency, or the check being "for this
specific run."

### 3. Confirmed against a real target repo

Directly cloned `kenotron-ms/test-resolve-repo` (a repo already used in an
earlier live reality-check attempt) to verify the default acceptance
criteria below are true *right now*, without this pipeline having touched
it:

```
$ git clone --depth 1 https://github.com/kenotron-ms/test-resolve-repo.git
$ cat README.md
# workspace
```

`README.md` exists at the repo root and is non-empty (13 bytes). This
confirms the default spec below (non-empty `README.md` at the repo root)
is satisfiable today, with zero writes from this pipeline.

(Side note, not this file's main point: that clone also showed
`reality_check_smoke_claim.txt` already present and committed on `main`
-- meaning the original `WriteClaimAndPush` push from the earlier live run
actually **succeeded** on the git side, even though the pipeline reported
`push_failed`. That is a separate bug in `WriteClaimAndPush`'s own
stdout/stderr capture, not evidence about reality-check's requirements, and
is out of scope for this file.)

## Pipeline shape

```
Start -> PrepareRealityCheckInputs -> RealityCheck -> RenderVerdict -> Report -> Exit
```

No `WriteClaimAndPush`, no `MarkPushFailed` -- there is no local write step
that can fail, so there is nothing to route around before the broker call.

## Submission requirements

| Requirement | Why |
|---|---|
| `repo` param = a repo slug (`owner/name`) or full URL you can **read** | Reality-check only ever clones; push/write access is never used. Public repos need no token at all. |
| `AMPLIFIER_RESOLVE_ENABLE_REALITY_CHECK=true` set on the resolve backend | Reality-check is feature-gated, same as every other reality-check pipeline. If unset, the broker returns HTTP 501; `reality_check_invoke.py` writes a real (non-crashing) failure verdict with `failure_mode=config`. |
| Must be submitted to the **dot-graph** resolver specifically | `RealityCheck`'s tool_command invokes a module only present in the dot-graph resolver's worker environment. |
| (optional) `spec` param | Overrides the default acceptance criteria with your own already-true claim about your own target repo. |

No `GH_TOKEN` push scope is required. No branch-protection interaction. No
disposable/scratch-repo requirement -- this is safe to point at a real,
non-scratch repo, including this very `attractor-pipelines` repo itself.

### Via the CLI / `remote.py`

```bash
remote.py call dot-graph \
  "git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/reality_check_smoke/reality_check_smoke.dot" \
  --params '{"repo": "kenotron-ms/test-resolve-repo"}'
```

Then watch it:

```bash
remote.py watch <instance_id>
```

## What "done" looks like

Same evidence shape as `reality_check_smoke.dot`: the authoritative,
machine-checkable field is `smoke.result` (`"passed"` | `"failed"`), backed
by `rc.verdict`, `rc.status`, `rc.failure_mode`, `rc.session_id`. A
human-readable copy is written to `.reality-check-smoke/verdict.md` inside
the worker's workspace.

`smoke.result="passed"` means: a **live** reality-check broker session --
running in its own Incus-provisioned DTU, entirely independent of this
pipeline's worker container -- cloned the target repo fresh (read-only) and
confirmed the default acceptance criteria (non-empty `README.md` at the repo
root) against whatever is *already* there. Nothing was written by this
pipeline to make that true.

## Open questions / not independently verified

One open item, carried over from earlier investigation, that applies
identically to a read-only clone:

1. **Runner network reachability.** Whether the Incus reality-check runner
   sub-container (which performs its own independent `git clone` of
   `software_path` inside its own DTU) has outbound network egress to reach
   `github.com`. Not traced beyond the code path in inputs.py's
   `resolve_software_path()`. **Recommendation: start with a public scratch
   repo** (or any public repo) to remove any private-repo-auth variable from
   the first live test -- this recommendation is weaker than it would be for
   a write-based pipeline, because "scratch" no longer matters for
   push-safety reasons, only for keeping the first test's blast radius small
   while confirming the broker round trip end to end.

2. This pipeline was **not** executed against a live attractor engine as
   part of authoring it.
