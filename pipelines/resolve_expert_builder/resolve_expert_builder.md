# resolve_expert_builder -- autonomous spec-to-PR builder via Amplifier Resolve

This pipeline is a sibling of `resolve_hello_world.dot` in spirit -- it is
**deliberately not portable** across engines. It leans on Amplifier Resolve
platform mechanism as heavily as `expert_builder.dot` (the pipeline it was
ported from, in `microsoft/amplifier-resolver-dot-graph`) always did. Nothing
about the pipeline's *logic* changed in this port -- only the file layout
needed to fit this repo's `pipelines/[name]/` convention. See "What was
ported, and what changed" below.

## What this pipeline does

Given a high-level spec (`spec`) and an existing target repo (`repo_url`),
`resolve_expert_builder.dot` runs an unattended, seven-stage build:

1. **Admission** -- an autonomous gate (composes `subgraphs/admission.dot`)
   that decides, without asking a human anything, whether the request can
   proceed. Writes the acceptance criteria the request already implies to
   `.ai/admission.yaml`, each tagged with its source (stated / entailed /
   repo / convention), or halts with a stated reason (`escalate` / `reject`).
2. **Decompose + explore** -- identifies the two hardest/riskiest parts of
   the build and spikes each in parallel (composes
   `subgraphs/expert_builder_explorer.dot` twice via a `shape=component`
   fan-out), packaging pros/cons and a recommendation for each.
3. **Plan** -- fans the packaged pieces back in to a detailed, ordered
   implementation plan under `.ai/plan/`, with explicit
   reuse/adapt/discard decisions against the spiked code.
4. **Implement** -- walks the plan's task files one at a time, in order,
   with stall and max-iteration safety exits and a run-wide implement
   budget that survives every downstream fix loop.
5. **Validate** -- exercises the freshly built project exactly as a new
   user would (install, run, edge cases), attributes faults, and loops a
   bounded number of fix rounds back into step 4 on failure.
6. **Reality-check** -- an INDEPENDENT verification against the original
   spec: publishes the build to the per-instance Gitea sidecar, then runs
   the platform's reality-check capability (composes
   `subgraphs/reality_check.dot`) against it, with its own bounded fix
   loop back into step 4 on failure.
7. **Deliver** -- writes a user-facing README + delivery summary, pushes
   the final state to Gitea, and -- when a promotable target repo was
   submitted -- opens a real GitHub PR via `subgraphs/deliver_promote.dot`
   (the same subgraph `resolve_hello_world.dot` uses for PR delivery).

Every non-passing exit (admission halt, exhausted fix budget) writes a
plain-language explanation to `/project/.resolve/data/delivery.md` --
this pipeline never silently stops.

## This is NOT portable -- Resolve-platform-specific by design

Unlike most pipelines in this repo, `resolve_expert_builder.dot` cannot be
pointed at a bare `attractor run` or a non-Resolve engine and expected to
work end to end. It is built to run **only** inside an Amplifier Resolve
worker container, for the same reasons `resolve_hello_world.dot` is:

- **Reads `/project/.resolve/config.json` directly**, repeatedly, for
  `params` (the submitted `repo_url` / `delivery_mode` / `spec`),
  `platform_url`, `instance_id`, and `sub_container_token` -- this path
  and shape only exists inside a Resolve worker container
  (`RepoGate`, `PrepareRC`, `DeliverFinalize`, `PromoteCheck`,
  `PromoteReport` all read it directly).
- **Requires a live Gitea sidecar remote (`origin`)**. `DeliverGitea` and
  `DeliverFinalize` commit and `git push origin HEAD:main` against the
  per-instance Gitea sidecar the platform provisions and clones into
  before `Start` ever fires -- there is no sidecar outside a Resolve
  instance.
- **Calls the platform's reality-check REST endpoints directly**, via
  `python/reality_check_invoke.py` (`amplifier_resolver_sdk.Resolver
  .start_reality_check` / `.wait_for_reality_check`). This requires
  `AMPLIFIER_RESOLVE_ENABLE_REALITY_CHECK=true` on the resolve backend and
  a worker-reachable `AMPLIFIER_RESOLVE_PLATFORM_URL` -- infrastructure
  that only exists on the Amplifier Resolve platform.
- **Calls the platform's internal promote/pr endpoint** (via
  `subgraphs/deliver_promote.dot`'s `CallPromotePR`, same mechanism
  `resolve_hello_world.dot` uses) -- `POST
  {platform_url}/internal/instances/{id}/repos/{repo}/promote/pr`,
  authenticated with the `sub_container_token` from `config.json`. This
  endpoint does not exist outside the platform.
- **Every `tool_command` invokes `/opt/uv-tools/amplifier/bin/python3`**
  explicitly, the SDK-enabled interpreter baked into the Resolve worker
  image (plain `python3` on a generic engine's PATH lacks `aiohttp` and
  `amplifier-resolver-sdk`).

If you need a spec-to-PR pipeline that runs outside a Resolve worker
container, this is not that pipeline -- adapt the shape but replace every
platform call above with a portable equivalent (see `hello_world.dot` /
`resolve_hello_world.dot`'s own portable-vs-platform split for the
pattern).

## Required instantiation params

Ported directly from `expert_builder.resolver.yaml` (kept in this folder
for reference -- see "What was ported" below):

| Param | Type | Required | Notes |
|---|---|---|---|
| `spec` | long text | yes | High-level specification -- what to build, not how. Passed via `tool_env`, never `$`-substituted into a shell command, so arbitrary user prose cannot break out into the shell. |
| `repo_url` | text | yes | Target repo as `owner/repo`. **Must already exist** -- an empty existing repo is a valid greenfield start, but a repo that fails to clone is not; `RepoGate` escalates in that case. This is the ONE repo input: it drives the workspace clone (`workspace_repo_from: repo_url`), admission's lint target, AND the promote PR target. |
| `delivery_mode` | choice | yes | Always `"promote"` -- the build is delivered as a GitHub PR (the review gate). The platform's promote endpoint 409s without it, exactly like `resolve_hello_world.dot`'s submission contract. |

### In natural language

> "Submit a dot-graph job using pipeline
> `git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/resolve_expert_builder/resolve_expert_builder.dot`,
> with `spec=<your high-level spec>`, `repo_url=<owner/repo, must already
> exist>`, and `delivery_mode=promote`."

Same submission discipline as `resolve_hello_world.md` applies: get
`delivery_mode` wrong and the pipeline runs the entire seven-stage build,
passes its own reality check, and only fails late at the promote step with
a 409 -- a job-submission bug that looks like a pipeline bug.

## Honest note on the `python/` files

`python/admission_lint.py`, `python/reality_check_invoke.py`, and
`python/reality_check.py` are included **verbatim, for reference only** --
they are **not directly runnable in this repo** and no attempt was made to
rewrite their imports to make them look portable, because that would
misrepresent what they actually need to run:

- They still import from their source package path,
  `amplifier_resolver_dot_graph.*` (e.g. `admission_lint.py` is invoked in
  `subgraphs/admission.dot` as
  `python -m amplifier_resolver_dot_graph.admission.lint`, and
  `reality_check_invoke.py` as
  `python -m amplifier_resolver_dot_graph.handlers.reality_check_invoke`).
  That package does not exist in this repo.
- `reality_check_invoke.py` additionally depends on
  `amplifier-resolver-sdk` and `aiohttp`, neither of which is part of this
  repo or its context. Both are installed only inside a Resolve worker
  container's SDK-enabled interpreter
  (`/opt/uv-tools/amplifier/bin/python`), via the resolver manifest's
  `setup_commands`.
- `admission_lint.py` additionally depends on `PyYAML` (stdlib +
  `yaml` only, per its own module docstring).

They are here as documentation of exactly what the source platform
executes -- same spirit as this repo already including other
platform-specific mechanism it can't fully run standalone (e.g.
`resolve_hello_world.dot`'s reliance on `/opt/uv-tools/amplifier/bin/python`
and the platform's `promote/pr` endpoint). Copy them into a real
`amplifier_resolver_dot_graph`-shaped package (or your own resolver's
package) if you want to actually run them.

## What was ported, and what changed

Ported from `microsoft/amplifier-resolver-dot-graph`'s
`src/amplifier_resolver_dot_graph/pipelines/`:

- `expert_builder.dot` -> `resolve_expert_builder.dot`
- `expert_builder_explorer.dot` -> `subgraphs/expert_builder_explorer.dot`
- `admission.dot` -> `subgraphs/admission.dot`
- `reality_check.dot` -> `subgraphs/reality_check.dot`
- `subgraphs/deliver_promote.dot` -> `subgraphs/deliver_promote.dot`
  (unchanged path -- already matched this repo's convention)
- `expert_builder.resolver.yaml` -> `resolve_expert_builder.resolver.yaml`
  (kept for reference; this repo does not run resolver manifests directly)
- `admission/lint.py` + `admission/__init__.py` -> `python/admission_lint.py`
  (the package docstring from `__init__.py` is preserved as a header
  comment in the ported file)
- `handlers/reality_check_invoke.py` -> `python/reality_check_invoke.py`
- `handlers/reality_check.py` -> `python/reality_check.py`

**The only changes made are the four `dot_file=` path references** inside
`resolve_expert_builder.dot`, updated to point at the new `subgraphs/`
layout (`admission.dot`, `expert_builder_explorer.dot` x2, and
`reality_check.dot`). Every node, edge, condition, prompt, comment, and
tool_command is byte-for-byte identical to the source -- this is a
structural port, not a rewrite. The comment blocks throughout the `.dot`
files ARE the design documentation for this pipeline; there is no separate
design doc, so they were preserved in full rather than summarized.

## Pipeline shape

```
pipelines/resolve_expert_builder/
  resolve_expert_builder.dot              # entry pipeline (7 stages, ~1130 lines)
  resolve_expert_builder.md               # this file
  resolve_expert_builder.resolver.yaml    # ported resolver manifest, for reference
  subgraphs/
    admission.dot                         # autonomous admission gate
    expert_builder_explorer.dot           # per-hard-part spike + package (parallel fan-out)
    reality_check.dot                     # independent reality-check against the original spec
    deliver_promote.dot                   # commit, push, open PR via the platform promote/pr endpoint
  python/
    admission_lint.py                     # invoked by admission.dot's Lint node (reference only)
    reality_check_invoke.py               # invoked by reality_check.dot's RealityCheck node (reference only)
    reality_check.py                      # copy-paste SDK node handlers (reference only, not invoked by any node)
```

Point the attractor bundle at it via:

```
git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/resolve_expert_builder/resolve_expert_builder.dot
```
