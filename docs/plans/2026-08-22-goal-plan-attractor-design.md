# Goal Plan Attractor Design

**Status:** Approved

**Date:** 2026-08-22

**Amended:** 2026-08-23

## Goal

Build an attractor-native pipeline that executes an approved, fixed dependency
plan of bounded goals in isolated git worktrees, integrates only independently
verified commits, proves the integrated result at final HEAD, and optionally
delivers one independently confirmed pull request.

The design preserves the useful behavioral contract of app-cli `/goal`,
`goalify`, and `goal-batch` without invoking those mechanisms literally at
runtime.

## Background and Source Analysis

### Attractor doctrine

The requested [Attractor VISION](https://github.com/microsoft/amplifier-bundle-attractor/blob/main/docs/VISION.md)
sets four constraints that control this design:

1. **The graph is the program.** The rendered graph must show the real
   dependency waves, convergence loops, gates, and terminal routes. A hidden
   queue or scheduler cannot own the actual control flow.
2. **Convergence is based on machine evidence, not step completion.** A lane
   worker's statement that it finished is a routing hint, never proof.
3. **Deterministic macro-control contains adaptive micro-control.** The graph
   owns dependencies, budgets, isolation, verification, integration, and
   recovery. Models adapt within the bounded lane goals and qualitative review
   duties assigned to them.
4. **Objectives enter; evidence-converged outcomes exit.** The pipeline must
   end in a verified success, an evidence-backed residual disposition, or a
   loud failure. It must never turn missing evidence into plausible success.

The same choices follow the local doctrine:

- `docs/primer.md` sections 2-4 require a corrective cycle, evidence-gated
  exit, resilience to a weak LLM node, and the design order
  **sink -> gate -> loop -> work**.
- `docs/RUBRIC.md` sections 2-4 reject worker self-report, require independent
  checks of side effects, distinguish a crashed parallel branch from a clean
  result, and treat budget exhaustion as a decision point rather than success.
- `docs/RUBRIC.md` section 5 and `AGENTS.md` require copying the nearest proven
  pipeline patterns, especially the shared PR-delivery subgraph, instead of
  inventing bespoke delivery steps.
- `docs/primer.md`'s engine foot-gun card requires file-backed evidence,
  routing on deterministic output such as `tool.last_line`, explicit
  failure routes, and graph-owned resume guards rather than assumed checkpoint
  resume.

### Behavioral contribution of the three app-cli mechanisms

The three source mechanisms contribute different behavior:

| Source | Behavioral contract retained | Runtime implementation not retained |
|---|---|---|
| `/goal` | An adaptive attempt continues until a concrete completion condition is satisfied; explicit caps and stall exits can stop without fabricating success. Feedback from the prior attempt informs the next one. | The slash command, transcript-only evaluator, nested Amplifier process, and orchestrator-owned continuation loop. |
| `goalify` | Each goal is checkable, names the proof that establishes completion, states constraints and scope-outs, and includes an honest blocker or exhaustion exit. | The inline skill invocation and any dependence on the current conversation at runtime. |
| `goal-batch` | Work is decomposed before launch, conflicts and dependencies are analyzed, the user approves the lane split, lanes work in isolated worktrees, results are merged sequentially, and the parent reruns verification. | Literal `/goal` child runs, app-cli launcher/status scripts, `DONE.json` coordination, and a runtime lane scheduler. Tmux was only a detachable process container, not a behavioral requirement. |

The important correction is that `/goal`'s transcript evaluator is not
independent machine evidence. In `goal_plan`, a deterministic verifier outside
the lane worker decides mechanical satisfaction, and the parent reruns that
verifier against the durable commit before integration.

### Verification experiment findings

Three bounded probe branches informed this amendment. They remain experimental
evidence and are not shipped production artifacts:

- The CWD probe proved that concurrent in-process folder/box lanes share the
  pipeline runner's global box-session CWD even when their deterministic tool
  nodes have distinct `context.target_dir` values. This rejects in-process
  folder lanes as the strict worktree-isolation boundary; it does not block
  process-per-lane execution.
- The convergence probe proved the limited external-failure -> correction ->
  parent-reverification mechanism. Production verification must strengthen it
  by making the correction genuinely dependent on changed feedback and by
  writing all run state outside immutable pipeline source directories.
- The macro-control probe caught branch-failure masking: a branch could write
  its expected artifact, exit nonzero, and still be accepted by an unsound
  collector. The parent must therefore persist and classify each child
  command's real exit status independently of artifact presence.

## Decision

Implement `goal_plan` as a **statically compiled goal-plan pipeline family**,
not as one generic dynamic root graph.

`goalify`/goal-batch-style decomposition remains the composition layer. It
produces a human-approved set of lane goals, owned paths, dependencies,
verifiers, qualitative criteria, and budgets. The already-existing
`goaltractor` composition behavior is the normal front end for arbitrary real
plans; a human author may materialize the same artifact contract directly.
Before runtime, either path writes a fixed, self-contained pipeline directory
whose DOT graph contains the approved dependency waves and lane subgraphs.
Changing lane count, dependencies, ownership, or verifier contracts requires
materializing and reviewing a changed static artifact.

Runtime does not compile another graph and does not discover or schedule work
from a queue. It executes the reviewed graph that is already present.

This repository supplies the reusable execution contract and a canonical fixed
smoke exemplar. It does not reimplement `goaltractor`, add another compiler, or
replace the composition mechanisms that create arbitrary plans.

Execution is intentionally hierarchical. The parent Attractor graph owns batch
admission, static dependency waves, process supervision, parent verification,
integration, aggregate/coherence gates, recovery, terminals, and delivery. One
separate headless child Attractor process owns each lane's bounded correction
cycle. This is parent/child Attractor composition, not nested app-cli `/goal`
orchestration.

## Goals

- Make every approved lane and dependency visible in DOT.
- Preserve adaptive, feedback-informed goal pursuit inside each bounded lane.
- Isolate concurrent lanes in separate git worktrees and separate headless
  child Attractor processes whose OS working directories are those worktrees.
- Supervise every child through a durable process ledger, logs, timeouts,
  process-group cancellation, and restart reconciliation.
- Separate the approved product baseline from the later execution-source commit
  that contains the complete compiled pipeline, and bind both identities through
  every runtime and evidence boundary.
- Keep the complete compiled pipeline directory byte-immutable throughout the
  run; source mutation is infrastructure failure, never corrective lane work.
- Accept lane completion only after an exact non-interactive verifier passes.
- Require a durable commit before a lane can be integrated.
- Have the parent independently rerun each lane verifier against the exact
  commit proposed for integration.
- Enforce declared path ownership before integration.
- Integrate passing lane commits sequentially.
- Run the aggregate verifier after every integration and again at final HEAD.
- Run a fresh cross-lane coherence review against the fully integrated result.
- Route late multi-owner findings through one bounded integration-branch
  correction loop.
- Rerun every lane verifier against exact final integration HEAD before
  completion.
- Optionally deliver one PR through the proven `deliver_pr.dot` pattern and
  independently verify that the remote PR points at the exact integrated HEAD.
- Recover by reconciling durable state with real git, worktree, verifier,
  merge, and remote PR state.
- End in one of four explicit terminal states:
  `COMPLETE`, `RESIDUALS_READY`, `INFRA_FAILURE`, or `ABORTED`.

## Non-Goals

- Invoking literal `/goal`.
- Launching `amplifier run` child processes or depending on app-cli process
  coordination.
- Depending on private app-cli internals.
- Requiring per-box `session_cwd` changes in loop-pipeline, pipeline-runner, or
  Resolve.
- Supporting non-Linux process supervision in schema version 1.
- Creating a new resolver.
- Creating a hidden runtime scheduler, generic work queue, or fixed-width pool
  that conceals the actual plan from the graph.
- Dynamically compiling child DOT during a run.
- Letting a lane certify its own success.
- Automatically delivering partial or residual work.
- Merging or deploying the PR after delivery.
- Replacing `goalify` or goal-batch-style composition.
- Reimplementing or wrapping the already-existing `goaltractor` compiler.

## Rejected Alternatives

### Literal `/goal` lanes

Rejected because the parent would wrap app-cli's transcript evaluator and
continuation loop rather than an evidence-gated lane graph. Convergence budgets,
evidence, and recovery would be split between two different orchestration
contracts. The selected child process runs `attractor run` on the reviewed
`goal_lane.dot`; it never runs `/goal` or `amplifier run`.

### In-process folder/box lanes

Rejected for strict lane isolation. The CWD probe showed that in-process box
sessions inherit the runner-global CWD even when folder lanes carry distinct
tool-node targets. Prompting a worker to stay inside a worktree is not
enforcement. A separate child pipeline runner launched with the lane worktree as
its OS CWD and `--cwd .` makes that boundary mechanical without an engine patch.

### Runtime child-DOT compilation

Rejected because the reviewed parent graph would not be the program that
actually runs. It would duplicate existing goaltractor-style composition and
move lane topology behind runtime generation.

### Manifest-driven fixed-width scheduler

Rejected because generic lane slots plus a queue make dependency and
parallelism policy invisible in the rendered graph. Scheduling would be hidden
script behavior rather than deterministic graph structure.

### A new resolver or platform-specific goal-batch wrapper

Rejected because this is pipeline policy, not a new execution substrate. A new
resolver would duplicate existing mechanisms and make the pipeline less
portable.

## Architecture

### Composition/runtime boundary

The composition layer produces one immutable member of the `goal_plan` pipeline
family. For a plan slug `PLAN_SLUG`, it materializes this self-contained
directory in the target repository:

```text
pipelines/PLAN_SLUG/
  PLAN_SLUG.dot
  plan.json
  PLAN_SLUG.md                 # optional; required by history_anchor mode
  subgraphs/
    goal_lane.dot
    deliver_pr.dot             # present only when delivery_mode is pr
  python/
    process_supervisor.py
```

`plan.json` is versioned design-time and audit data. It is not a runtime
scheduling manifest: runtime must not iterate its `lanes` or `waves` to decide
what runs next. The generated DOT owns dispatch and contains the actual program.

#### `plan.json` contract

`plan.json` has these required typed fields:

| Field | Type and invariant |
|---|---|
| `schema_version` | String with exact value `goal-plan.plan/v1`. |
| `plan_id` | Slug string equal to `PLAN_SLUG`; stable across runs of the same compiled plan. |
| `source_request` | Non-empty string containing the originating request or its durable reference. |
| `target_repo` | Object with `vcs: "git"`, `identity_mode: "remote"` or `"history_anchor"`, and the mode-specific fields defined below. |
| `product_base_sha` | Full immutable commit SHA of the approved product baseline used for requirement provenance and product-level delta reporting. It must be an ancestor of the admitted `execution_source_sha`. |
| `execution_source` | Object with exact `mode: "containing_commit"`, required runtime binding name `execution_source_sha`, and no embedded SHA value. Admission resolves the exact containing commit as described below, avoiding a self-referential Git hash while still binding the exact SHA through the plan contract. |
| `lanes` | Non-empty array of lane objects described below. |
| `waves` | Non-empty ordered array of objects with unique `id` and non-empty `lane_ids`; every lane appears in exactly one wave. |
| `integration_order` | Array containing every lane ID exactly once in deterministic integration order, with every dependency before its dependents. |
| `integration_seams` | Array of repository-relative path patterns explicitly writable by late integration correction. No pattern may equal, contain, or overlap `pipelines/PLAN_SLUG/**`. |
| `aggregate_verifier` | Aggregate-verifier contract defined below. |
| `global_budgets` | Object with positive integer `max_total_attempts`, positive integer `max_integration_corrections`, and positive integer `max_pipeline_seconds`. |
| `approval_mode` | Enum string `required` or `preapproved`. |
| `delivery_mode` | Enum string `none` or `pr`. |

#### Target-repository identity policy

Git does not provide a global repository ID. `target_repo` therefore uses one
of two machine-observable identity modes; a vague author-assigned
`repository_id` is not part of the schema.

**Remote-backed repositories** use:

| Field | Type and invariant |
|---|---|
| `identity_mode` | Exact string `remote`. |
| `expected_fetch_remote` | Required canonical string in normalized `host[:port]/path` form. |
| `remote_name` | Optional Git remote-name string, or `null`. |

Composition accepts HTTPS, `ssh://`, and scp-like SSH source forms and
normalizes the expected fetch URL as follows:

1. Parse the accepted form and discard the URL scheme.
2. Remove HTTPS credentials/userinfo and SSH user names.
3. Lowercase the host.
4. Remove the default port (`443` for HTTPS, `22` for SSH); retain any
   non-default port.
5. Strip leading and trailing slashes from the repository path.
6. Strip one exact trailing `.git` suffix.
7. Preserve the remaining repository-path case.
8. Emit exactly `host[:port]/path`.

At runtime, admission enumerates configured Git fetch URLs. When `remote_name`
is non-null it examines every fetch URL for that remote; otherwise it examines
every fetch URL for every configured remote. It applies the same normalization
and requires at least one exact match with `expected_fetch_remote`. Push URLs
do not establish identity.

**Local-only repositories** use:

| Field | Type and invariant |
|---|---|
| `identity_mode` | Exact string `history_anchor`. |
| `plan_commit_sha` | Full commit SHA anchoring the compiled plan. |
| `plan_path` | Repository-relative path of the identity-stable `PLAN_SLUG.md` plan artifact. |
| `plan_blob_sha256` | SHA-256 of the exact committed blob bytes at `plan_path`. |
| `product_base_sha` | Full approved product-baseline commit SHA; must equal top-level `product_base_sha`. |

`PLAN_SLUG.md` is required in `history_anchor` mode and must not contain the
anchor fields themselves. This avoids a content-addressing cycle: composition
first commits that identity-stable plan artifact, records its commit and blob
hash in `plan.json`, materializes the final DOT, and commits the complete
compiled pipeline directory. Runtime requires every immutable file in
`pipelines/PLAN_SLUG/` to be tracked at exact `execution_source_sha`; admission
and every later immutable-source gate compare complete path/mode/byte state to
that commit.

Admission then proves:

1. the target Git object database contains `plan_commit_sha` as a commit;
2. `plan_commit_sha:plan_path` resolves to a blob;
3. the blob's exact bytes hash to `plan_blob_sha256`;
4. those bytes match the invoked plan artifact at `plan_path` in
   `execution_source_sha`;
5. the target object database contains `product_base_sha`;
6. `product_base_sha` is an ancestor of `plan_commit_sha`;
7. `plan_commit_sha` is an ancestor of the admitted `execution_source_sha`;
8. `product_base_sha` is an ancestor of `execution_source_sha`; and
9. the complete compiled pipeline directory at `execution_source_sha` is
   tracked and matches the admission byte manifest.

The committed plan/blob/base relationship is the identity proof for a
local-only repository. The design does not claim that Git supplies a globally
unique repository identifier.

Each `lanes` entry contains:

| Field | Type and invariant |
|---|---|
| `id` | Unique lane-ID slug. |
| `origins` | Non-empty array of requirement identifiers or text. |
| `goal` | Non-empty, checkable end-state string. |
| `scope_outs` | String array. |
| `owned_paths` | Non-empty array of repository-relative path patterns. No pattern may equal, contain, or overlap `pipelines/PLAN_SLUG/**`. |
| `dependencies` | Array of lane IDs; references must exist and form an acyclic graph. |
| `verifier` | Object with exactly one of non-empty `command`, or checked-in `script_path` plus `script_sha256`; exact symbolic `cwd_policies: ["lane_worktree", "candidate_verification_worktree", "integration_worktree"]`; positive integer `timeout_seconds`; evidence schema version `goal-plan.lane-verifier/v1`; exit/token mapping; and `definition_sha256`. |
| `review_criteria` | Array of qualitative criterion objects, or an empty array when no lane review is required. |
| `child_pipeline` | Object with repository-relative `dot_path`, exact `dot_sha256`, exact executable identity and argv/parameter contract defined below, symbolic `cwd_policy: "lane_worktree"`, expected evidence schema `goal-plan.lane-result/v1`, and a hash binding those immutable values. |
| `budgets` | Object with positive integer `max_attempts` and positive integer `max_child_seconds`. |
| `process_supervision` | Object with exact `schema_version: "goal-plan.process-supervision/v1"`, `platform: "linux"`, `mode: "supervised_process_group"`, repository-relative `supervisor_path`, exact `supervisor_sha256`, positive integer `poll_interval_seconds`, positive integer `term_grace_seconds`, canonical procfs identity requirements, durable log/ledger policies, and supervisor-definition hash. |

The composition layer owns decomposition, collision analysis, all typed values
above, and plan approval or explicit preapproval. It writes `plan.json`
canonically and computes `plan_sha256` over the exact UTF-8 bytes of that file.

The child launch command is an exact argv-array template, never a freeform shell
string. The parent mints:

```text
process_run_id = PLAN_ID/RUN_ID/LANE_ID/LAUNCH_ATTEMPT
```

where every component is the already-validated slug or positive decimal launch
attempt. This is the durable process-run identifier. Individual child box
session IDs are optional observability and never identity or completion
evidence.

After resolving typed placeholders, argv has exactly this order:

```text
attractor
run
<repo-relative-child-dot>
--cwd
.
--logs-root
<absolute state_root/lanes/<lane-id>/runs/<launch-attempt>/attractor-run>
--param lane_id=<lane-id>
--param process_run_id=<plan-id>/<run-id>/<lane-id>/<launch-attempt>
--param lane_state_root=<absolute state_root/lanes/<lane-id>>
--param lane_result_path=<absolute lane-attempt-root/lane-result.json>
--param lane_feedback_path=<absolute lane-state-root/feedback/current.md>
--param lane_attempt_root=<absolute state_root/lanes/<lane-id>/runs/<launch-attempt>>
--param lane_contract_snapshot_path=<absolute lane-state-root/contract.json>
--param candidate_branch=<validated lane branch name>
--param product_base_sha=<full product base SHA>
--param execution_source_sha=<full execution source SHA>
--param lane_verifier_definition_sha256=<full verifier contract hash>
--param ownership_contract_sha256=<full ownership contract hash>
```

The child DOT operand is repository-relative, contains no `..`, and resolves
under `pipelines/PLAN_SLUG/` in the lane worktree. `--cwd` is the literal token
`.`. `candidate_branch`, IDs, and SHA/hash params are typed strings with the
validation stated above. `--logs-root` and every path-valued `--param` are
absolute, `realpath`-canonicalized, and must resolve beneath that lane's
run-scoped `state_root/lanes/<lane-id>/`; none may resolve beneath immutable
source. No additional child parameter is permitted unless a new compiled-plan
revision adds it to this ordered schema and changes the launch-contract hash.

The launch environment is also closed and hashed. The plan declares the exact
allowed environment-key set. The ledger records non-secret values directly and
sensitive values only as `sha256(value)`; a canonical environment hash covers
the complete key set and value/value-hash representation. The immutable
launch-contract hash covers executable identity policy, ordered argv template,
typed parameter schema, environment policy, child DOT hash, symbolic
`lane_worktree` CWD policy, and expected lane-result schema.

At launch, the parent records the resolved executable realpath, exact argv,
environment hash, lane-worktree realpath, `process_run_id`, and a
`launch_command_sha256` over their canonical serialization. Plan/DOT
correspondence validates the immutable template and parameter ordering;
runtime admission and the process ledger bind the resolved values. Extra argv,
environment keys, parameter reordering, or path escape is `INFRA_FAILURE`.

These exact arguments direct child events, checkpoints, session metadata,
feedback, and result artifacts outside source. Preflight rejects a child runtime
that cannot honor `--logs-root` and the absolute output paths; execution may not
fall back to writing generated state beside `goal_lane.dot`.

#### Generated DOT correspondence

`PLAN_SLUG.dot` embeds `plan_sha256` as a graph attribute and directly encodes:

- one explicit deterministic launch/monitor branch per lane, bound to that
  lane's checked-in child DOT path and hash;
- explicit component/tripleoctagon nodes for each wave;
- every dependency edge;
- the full integration-order chain;
- every lane, integration-correction, run-wide, and duration budget;
- the literal `product_base_sha` and the `execution_source_sha`
  containing-commit binding contract;
- every child DOT path/hash, launch-command contract, symbolic worktree-CWD
  policy, exact ordered parameter schema, expected child-evidence schema, and
  Linux process-supervision policy;
- the aggregate-verifier definition hash;
- approval and delivery modes; and
- all terminal and correction routes.

Embedding the exact `execution_source_sha` inside the commit it identifies would
create an impossible content-addressing cycle. The immutable plan and DOT
therefore encode graph attributes
`product_base_sha="<literal-full-sha>"`,
`execution_source_binding="containing_commit"`, and
`execution_source_input="execution_source_sha"`. Admission proves the supplied
exact SHA is the containing commit of those exact bytes, then freezes the exact
value in run context and durable state. Thus plan/DOT bind the derivation and
every runtime/evidence artifact binds the resolved SHA without self-reference.

Admission runs before approval and before any mutation. It deterministically:

1. locates the adjacent `plan.json`;
2. recomputes its SHA-256 and requires equality with embedded
   `plan_sha256`;
3. schema-validates `plan.json`;
4. proves the selected target-repository identity mode; and
5. resolves `execution_source_sha` to the exact commit containing the invoked
   byte-clean parent DOT and adjacent `plan.json`, and proves that commit also
   contains the complete compiled pipeline directory;
6. parses the static DOT to require exact correspondence for lane IDs, waves,
   dependency edges, integration order, budget values, aggregate-verifier hash,
   both source-SHA contracts, child launch/monitor nodes, exact child argv/param
   ordering, child DOT/command/supervision hashes, approval mode, and delivery
   mode; and
7. records the complete compiled-directory byte manifest and its canonical hash
   under `state_root/admission/`.

A missing file, hash mismatch, schema failure, or graph/plan mismatch aborts
admission loudly. Admission reads `plan.json` only to audit the already-static
program; it never dispatches work from the JSON.

#### Runtime invocation interface

Each compiled family member accepts only these runtime inputs:

| Input | Type and rule |
|---|---|
| `target_repo` | Required absolute path to the Git working repository. Admission must prove its `remote` or `history_anchor` identity policy from `plan.json.target_repo`. |
| `execution_source_sha` | Required full Git commit SHA. It must be the containing commit of the exact invoked parent DOT and adjacent `plan.json`, contain every immutable compiled source file, descend from `product_base_sha`, and satisfy the complete byte-manifest gate. |
| `run_id` | Required slug unique within the plan's run directory. |
| `state_root` | Absolute path. If omitted, preflight resolves the absolute default `TARGET_REPO/.amplifier/runs/goal-plan/PLAN_ID/RUN_ID`; it must be ignored by Git before runtime writes it. |
| `approval_mode` | Required enum `required` or `preapproved`; must equal the compiled plan value. |
| `delivery_mode` | Required enum `none` or `pr`; must equal the compiled plan value. |
| `github_repo` | `owner/repo` string required only when `delivery_mode` is `pr`; forbidden otherwise. |

Preflight rejects non-Linux hosts, missing or unreadable required procfs
identity files, relative `target_repo` or `state_root` values, mode mismatches,
failed remote/history-anchor identity proofs, reused `run_id` with incompatible
state, an invalid `product_base_sha`, or an `execution_source_sha` that does not
contain the exact compiled program being invoked.

Composition owns the immutable files under `pipelines/PLAN_SLUG/`. Runtime
reads but never rewrites them. All runtime-created filesystem state and
evidence, including its lane and integration worktree directories, live beneath
`state_root`; product changes leave those worktrees only as explicit Git commits
and integrations.

Preflight defines the dedicated external worktree root as
`state_root/worktrees/`. The integration worktree and every initially prepared
lane branch are created at exact `execution_source_sha`. Before a later
dependency wave launches, its lane branch is advanced only to the current
parent-verified integration HEAD, which must descend from
`execution_source_sha`; therefore every lane always contains the compiled child
DOT and supervisor. Lane-owned candidate diffs and integration mutations are
measured from `execution_source_sha`, while final product reporting separately
identifies the known compiled-plan delta
`product_base_sha..execution_source_sha` and the lane-produced delta
`execution_source_sha..final_integrated_head`.

The runtime graph is responsible for:

- deterministic preflight;
- isolated worktree preparation;
- explicit dependency-wave execution;
- supervised launch and monitoring of one headless child Attractor process per
  lane;
- parent-side evidence checks;
- sequential integration and rollback of failed candidates;
- aggregate and coherence gates;
- terminal classification;
- recovery; and
- optional PR delivery.

### Immutable compiled-source contract

Admission walks `pipelines/PLAN_SLUG/` at exact `execution_source_sha` and writes
`state_root/admission/compiled-source-manifest.json` with schema
`goal-plan.compiled-source-manifest/v1`. The canonical manifest records
`product_base_sha`, `execution_source_sha`, compiled-directory path, and a
lexicographically sorted entry for every regular file containing:

- repository-relative path;
- Git mode;
- byte length; and
- SHA-256 of the exact blob bytes.

Symlinks, submodules, untracked entries, non-regular files, duplicate normalized
paths, and case-colliding paths are rejected. The manifest includes
`plan.json`, parent DOT, child lane DOT, supervisor code, verifier definitions,
delivery subgraph when present, and every other compiled-directory byte. Its
`manifest_sha256` covers the canonical JSON excluding only that hash field.
The manifest itself lives under `state_root`, so it does not create a
self-hashing source cycle.

The deterministic `CompiledSourceGate` compares both the complete path set and
every entry's mode, length, and bytes against the admission manifest. It emits
only `COMPILED_SOURCE:PASS` or `COMPILED_SOURCE:INFRA`. The gate runs:

1. at admission in the execution-source checkout;
2. against each lane worktree immediately after every child exit;
3. against the candidate commit before parent candidate verification;
4. against the integration worktree after every merge and every
   `IntegrationCorrection`;
5. against all existing run worktrees during restart reconciliation; and
6. against the integration worktree immediately before finalization or
   delivery.

Any missing, added, mode-changed, or byte-changed compiled-source entry is
`INFRA_FAILURE`. It never enters a lane, integration-correction, or verifier
retry loop. Composition additionally rejects any lane `owned_paths` or
`integration_seams` pattern that could match `pipelines/PLAN_SLUG/**`.

### Top-level topology

```text
Start
  -> Reconcile durable state
  -> Bind typed runtime inputs
  -> Admission: validate plan/graph/repo + bind product_base_sha/execution_source_sha
  -> Record compiled-source byte manifest; establish ignored state_root/worktree root
  -> Plan approval (or verify explicit preapproval)
  -> Prepare integration + Wave 1 worktrees from execution_source_sha
  -> component fan-out
       -> LaunchChild(A) -> MonitorChild(A) -> classify terminal A
       -> LaunchChild(B) -> MonitorChild(B) -> classify terminal B
  -> tripleoctagon fan-in
  -> Collect child process records + artifacts
       -> missing exit/artifact = CRASHED or INFRA, never PASS
  -> CompiledSourceGate on every exited lane worktree
  -> For each candidate: CompiledSourceGate on candidate commit
       -> create clean detached candidate_verification_worktree at exact candidate SHA
       -> parent reruns lane verifier there
       -> require clean after verifier; remove/reconcile detached worktree
  -> Enforce ownership
  -> Integrate passing commits one at a time
       -> aggregate verifier after each merge
       -> CompiledSourceGate after each merge
       -> on failure: undo candidate merge, return evidence to owning lane
  -> Prepare next explicit dependency wave
  -> ...
  -> Aggregate verifier at final HEAD
  -> Fresh cross-lane coherence review at final HEAD
       -> ITERATE: one IntegrationCorrection on integration branch
            -> CompiledSourceGate after correction
            -> affected-closure lane verifiers at current integration HEAD
            -> aggregate verifier
            -> fresh coherence review
       -> residual classification when no bounded correction remains
       -> PASS: final sweep of every lane verifier at exact final HEAD
            -> red: IntegrationCorrection within integration budget
            -> all green: completion-eligible
  -> CompiledSourceGate before finalization/delivery
  -> Classify convergence result
       -> all gates green
            -> delivery disabled -> COMPLETE
            -> delivery enabled -> deliver_pr.dot
                 -> exact-head PR verification -> COMPLETE
                 -> unverifiable delivery -> INFRA_FAILURE
       -> residuals -> residual disposition gate
            -> preserve evidence-backed residuals -> RESIDUALS_READY
            -> operator stops -> ABORTED
       -> untrustworthy substrate -> INFRA_FAILURE
       -> rejected/cancelled plan -> ABORTED
```

Each dependency wave is drawn explicitly. `shape=component` and
`shape=tripleoctagon` provide concurrent fan-out/fan-in only within that visible
wave. Each branch contains its statically named launch and monitor/poll gates.
Launch nodes start the approved child process and atomically record the process
ledger; they perform no lane cognition. Monitor gates poll only their compiled
lane ID until the child is terminal, timed out, cancelled, or inconsistent.
The graph contains no generic "get next lane" operation, dynamic scheduler, or
work queue.

## Lane Contract

Every lane has the following approved, immutable contract:

| Field | Requirement |
|---|---|
| Lane ID | Stable identifier used in graph nodes, worktree names, state, logs, and evidence. |
| Originating requirement | Traceable statement connecting the lane to the approved objective. |
| Goal | Checkable end state, not a list of procedural steps. |
| Scope-outs | Explicit work the lane must not perform. |
| Owned paths | Allowed write set. Concurrent lanes must not have conflicting ownership. |
| Dependencies | Lane IDs that must be `PASS` and integrated before this lane starts. |
| Verifier | Exact, non-interactive command with a defined symbolic CWD policy and timeout. The child uses `lane_worktree`; pre-integration parent verification uses a clean detached `candidate_verification_worktree`; post-merge closure and final-sweep verification use `integration_worktree`. Exit zero means the mechanical condition passed; any other result is evidence to classify. |
| Qualitative criteria | Optional criteria that require an independent judgment gate after the mechanical verifier passes. |
| Attempt budget | Maximum verification-bearing attempts available to the lane. |

A lane may read outside its owned paths as needed to understand the repository,
but it may not modify outside them. Generated files and repository-wide files
must be assigned deliberately during composition; undeclared writes are an
ownership failure.

The lane result must bind evidence to:

- the lane ID;
- the approved plan revision, `product_base_sha`, and
  `execution_source_sha`;
- its current dependency/integration base commit;
- the exact lane head commit;
- the approved child DOT and launch-command hashes;
- the durable process-ledger entry, `process_run_id`, and observed exit
  status;
- the verifier command and exit status;
- verifier output;
- ownership-check output;
- qualitative-review output, when applicable; and
- the attempt and budget counters.

The lane's prose summary is informational. The bound artifacts above determine
its disposition.

### Lane verifier cwd and hash contract

Lane-verifier definitions are immutable across runs and worktree locations.
Their `definition_sha256` covers a canonical serialization of:

- the exact command string, or the checked-in script's content SHA-256;
- the exact ordered symbolic CWD policies `lane_worktree`,
  `candidate_verification_worktree`, and `integration_worktree`;
- the configured timeout;
- lane-verifier evidence schema version `goal-plan.lane-verifier/v1`; and
- the exact exit/verdict/token mapping.

No resolved absolute path is part of the immutable hash. A child attempt selects
`lane_worktree`; pre-integration parent verification selects
`candidate_verification_worktree`; affected-closure and final-sweep
verification select `integration_worktree`.

At runtime:

- `lane_worktree` resolves from `state_root`, run ID, and lane ID and is rooted
  at the lane's current integration base, which descends from
  `execution_source_sha`;
- `candidate_verification_worktree` resolves to a unique disposable path under
  `state_root/worktrees/candidate-verification/LANE_ID/CANDIDATE_SHA/ATTEMPT`
  and is detached at that exact candidate SHA; and
- `integration_worktree` resolves beneath `state_root/worktrees/integration`
  and begins at exact `execution_source_sha`.

The wrapper canonicalizes every selected path with `realpath`, requires equality
with the corresponding durable worktree record, confirms the target
repository's Git common object database, and records `product_base_sha`,
`execution_source_sha`, selected `cwd_policy`, and resolved `cwd` separately
from `definition_sha256`.

#### Candidate verification worktree lifecycle

After a child produces a candidate commit, the parent first resolves that SHA
directly from Git and runs `CompiledSourceGate` against its tree. It then:

1. requires the candidate to descend from the lane's current integration base,
   which must itself descend from `execution_source_sha`;
2. creates a clean disposable detached worktree at the exact candidate SHA under
   the dedicated external worktree root;
3. proves `HEAD == candidate_sha`, the common Git directory matches, and
   `git status --porcelain=v1 --untracked-files=all` is empty before verification;
4. runs the immutable lane verifier only in that worktree using
   `candidate_verification_worktree`;
5. records the canonical path, candidate SHA, `product_base_sha`,
   `execution_source_sha`, verifier-definition hash, command/exit/log, and
   clean-before result;
6. requires the same full status command to remain empty after verification;
7. removes the detached worktree without `--force`, prunes/reconciles its Git
   registration, and proves both filesystem path and worktree-list entry are
   absent; and
8. atomically records clean-after, removal command/result, registration
   reconciliation, and final disposition in the parent-verification evidence.

These fields extend `goal-plan.lane-verifier/v1` whenever
`cwd_policy == "candidate_verification_worktree"`. A dirty verifier worktree,
wrong HEAD, path escape, create failure, remove failure, stale registration, or
inability to reconcile is `INFRA_FAILURE`, regardless of verifier exit. It never
becomes lane feedback. A verifier failure is product evidence only after clean
teardown succeeds.

### Child launch and process-supervision contract

The parent launches each lane through the checked-in deterministic
`process_supervisor.py`; the launch node does not call the lane worker directly.
The launch operation is equivalent to:

```python
subprocess.Popen(
    supervisor_command,
    cwd=lane_worktree,
    start_new_session=True,
    stdout=supervisor_log,
    stderr=subprocess.STDOUT,
)
```

The supervisor then launches the approved child Attractor CLI command from the
same worktree, passing `run <goal_lane.dot>` and `--cwd .`. The child gets its
own process group. The supervisor stays outside that child group so it can
capture the real exit status even after cancellation. Because the child
pipeline runner starts with the lane worktree as both OS CWD and Attractor root
CWD, every child box session inherits the correct lane root without changes to
loop-pipeline, pipeline-runner, or Resolve.

Process-supervision schema version 1 is Linux-only. Preflight requires procfs
and rejects any host where `/proc/sys/kernel/random/boot_id`,
`/proc/<pid>/stat`, `/proc/<pid>/cmdline`, or `/proc/<pid>/exe` cannot supply
the identity contract below.

Before the launch node returns, the supervisor atomically creates
`state_root/lanes/<lane-id>/runs/<launch-attempt>/process.json` with schema
`goal-plan.child-process/v1`. The versioned ledger records:

| Field | Contract |
|---|---|
| `schema_version` | Exact value `goal-plan.child-process/v1`. |
| `lane_id`, `process_run_id`, `launch_attempt` | Exact compiled lane ID, canonical `PLAN_ID/RUN_ID/LANE_ID/LAUNCH_ATTEMPT`, and positive attempt integer. |
| `product_base_sha`, `execution_source_sha` | Exact admitted source SHAs. |
| `state` | One of `STARTING`, `RUNNING`, `TERM_SENT`, `KILL_SENT`, `EXITED`, `TIMED_OUT`, `CANCELLED`, or `INTERRUPTED`. |
| `supervisor_identity`, `child_identity` | Identity objects containing the canonical Linux token, cmdline SHA-256, expected PGID, executable realpath, and launch command hash. Child identity may be null only during `STARTING`. |
| `argv`, `environment_sha256`, `launch_command_sha256` | Exact argv, canonical environment hash, and hash of the approved executable/argv/env/CWD/process-run envelope. |
| `cwd_policy`, `cwd` | Exact token `lane_worktree` and its verified absolute realpath. |
| `dot_path`, `dot_sha256` | Resolved checked-in child DOT path and verified content hash. |
| `started_at`, `ended_at` | UTC timestamps; `ended_at` is null until terminal. |
| `child_box_session_ids` | Optional array used only for observability; it may be empty and never participates in identity or completion. |
| `stdout_stderr_log` | Absolute durable log path under the lane state directory. |
| `exit_code`, `timed_out`, `termination_reason` | Real observed child exit and timeout/cancellation facts; null only before terminal. |

Ledger writes use atomic replace and retain a JSONL transition history so a
partially written status cannot be mistaken for terminal evidence.

#### Canonical Linux process identity

For both supervisor and child, the canonical identity token is:

```text
linux:<boot_id>:<pid>:<starttime_ticks>
```

`boot_id` is the exact trimmed value read from
`/proc/sys/kernel/random/boot_id`. `pid` is the decimal PID.
`starttime_ticks` is field 22 of `/proc/<pid>/stat` as defined by procfs. The
identity object also records and verifies:

- SHA-256 of the exact NUL-delimited bytes from `/proc/<pid>/cmdline`;
- expected PGID;
- `realpath` of `/proc/<pid>/exe`; and
- the canonical `launch_command_sha256`.

For the supervisor identity this final hash is the approved supervisor
invocation hash; for the child identity it is the exact child
executable/argv/env/CWD/process-run hash defined above.

Before adoption, every monitor poll, `TERM`, or `KILL`, the responsible
supervisor or parent rereads and exactly matches boot ID, PID start ticks,
cmdline hash, PGID, executable realpath, and launch command hash. `kill -0` may
be used only after this identity check and proves liveness only. Unreadable
required procfs identity data or any mismatch writes stale-PID evidence and is
`INFRA_FAILURE`; that PID or process group is never signalled or adopted.

The supervisor enforces `max_child_seconds`. On timeout or graph-requested
cancellation it revalidates the complete child identity, sends `TERM` to the
verified child process group, waits exactly `term_grace_seconds`, revalidates
identity again, then sends `KILL` to that group only if the same process remains.
It records the real child exit, timeout/cancellation reason, and final ledger
state before exiting. The monitor routes on this persisted exit status even
when expected child artifacts exist; artifact presence can never mask a nonzero
process exit.

The child process may outlive a crashed parent graph. On restart,
reconciliation adopts monitoring only when the durable supervisor and child
identities both match live processes. If the supervisor is gone but a matching
child group remains, the run cannot recover a trustworthy eventual exit status;
it safely terminates that verified group and classifies the attempt
`INTERRUPTED`. If `/proc/<pid>` is absent because the process exited, absence is
never success: reconciliation uses the durable supervisor exit record, child
result/evidence, compiled-source evidence, and Git state to classify the
attempt. A reboot/boot-ID mismatch, unreadable procfs state, contradictory
identity, or ledger disagreement is `INFRA_FAILURE`.

Manual observation uses the durable combined log, transition history, child
Attractor events, `process_run_id`, and optional child box-session IDs.

### Aggregate verifier contract

The approved plan also contains one immutable aggregate-verifier contract. It
declares:

- either the exact non-interactive command string or the repository-relative
  path and content SHA-256 of a checked-in executable script;
- the symbolic cwd policy token `integration_worktree`;
- a configured timeout in seconds;
- a SHA-256 verifier-definition hash;
- the stdout/stderr log location; and
- the JSON evidence-record location.

The immutable verifier-definition hash covers a canonical serialization of:

- the exact command string, or the checked-in script's content SHA-256;
- exact symbolic cwd policy token `integration_worktree`;
- the configured timeout;
- evidence schema version `goal-plan.aggregate-verifier/v1`; and
- the exact exit/verdict/last-line-token mapping below.

The canonical hash input never contains a resolved absolute worktree path, so
the same approved verifier contract has the same hash across runs. Before every
aggregate run, the wrapper recomputes the immutable definition hash and
compares it with the approved value. A mismatch is infrastructure failure; the
changed verifier is not run as though it were the approved definition of done.

At runtime, the wrapper resolves `integration_worktree` from `target_repo`,
`state_root`, and `run_id`, canonicalizes it with `realpath`, requires equality
with the integration-worktree realpath in the durable run record, and confirms
that it uses the target repository's Git common object database. That resolved
absolute path is runtime evidence, not immutable contract input.

Every invocation runs from that verified absolute integration-worktree path.
Combined stdout and stderr are written to an `attempt-N.log` file under the
run's integration evidence directory. An adjacent `attempt-N.json` evidence
record is written atomically with these required fields:

| Field | Contract |
|---|---|
| `schema_version` | Exact value `goal-plan.aggregate-verifier/v1`. |
| `attempt` | Positive integer for this aggregate-verifier invocation. |
| `product_base_sha`, `execution_source_sha` | Exact admitted source SHAs. |
| `head_sha` | Full SHA returned by `git rev-parse HEAD` immediately before the run. |
| `verifier_hash` | Recomputed SHA-256 verifier-definition hash. |
| `cwd_policy` | Exact value `integration_worktree`. |
| `cwd` | Absolute, `realpath`-canonicalized integration-worktree path verified for this run. |
| `exit_code` | Child exit code; a timeout records wrapper exit code `124`. |
| `timed_out` | Boolean that is `true` only when the configured timeout fired. |
| `verdict` | Exact value `PASS`, `FAIL`, or `INFRA`. |

The deterministic wrapper captures the child result, writes the log and JSON
record, and emits exactly one of these tokens as its last non-empty stdout line:

| Observed result | JSON verdict | Last-line token |
|---|---|---|
| Exit `0` before timeout | `PASS` | `AGGREGATE_VERIFY:PASS` |
| Exit `1` before timeout | `FAIL` | `AGGREGATE_VERIFY:FAIL` |
| Exit `2` or greater, timeout, definition-hash mismatch, or inability to execute the verifier | `INFRA` | `AGGREGATE_VERIFY:INFRA` |

Graph edges route on `tool.last_line`. Only `AGGREGATE_VERIFY:PASS` may advance
to another dependency wave, final coherence review, delivery eligibility, or
completion. `FAIL` enters the responsible correction loop; `INFRA` leaves
product-correction loops and routes toward `INFRA_FAILURE`.

## Lane Convergence Subgraph

Each headless child process runs the versioned, hash-checked `goal_lane.dot`
already present in its lane worktree. The subgraph adapts the proven task-runner
shape:

```text
Orient
  -> Adaptive attempt
  -> Deterministic verifier
       -> red -> classify failure
                    -> novel/actionable -> curate feedback -> attempt
                    -> repeated signature -> root-cause diagnosis
                         -> actionable change of course -> attempt
                         -> blocker -> BLOCKED
                    -> budget exhausted -> budget-exhausted
       -> green -> optional fresh qualitative critique
                    -> iterate -> curate feedback -> attempt
                    -> pass -> ownership check -> commit check -> PASS candidate
```

The cheap deterministic verifier always precedes the expensive qualitative
gate. Feedback records the highest-leverage next correction and replaces stale
guidance rather than growing an unbounded transcript. Repeated identical
failure signatures route to diagnosis rather than another blind attempt.

The child lane graph does not mark the batch lane `PASS`, certify integration,
or certify batch completion. It produces a candidate commit and versioned
`goal-plan.lane-result/v1` evidence under
`state_root/lanes/<lane-id>/runs/<launch-attempt>/`. Parent verification in a
clean detached candidate worktree assigns the final `PASS` disposition.

## Deterministic and LLM Boundaries

| Responsibility | Owner | Reason |
|---|---|---|
| Plan-schema validation, dependency-cycle checks, ownership-collision checks, source-SHA/compiled-manifest admission | Deterministic nodes | These are exact predicates. |
| Lane, candidate-verification, and integration worktree creation, cleanliness, cleanup, branch/source inspection | Deterministic nodes | Git state is observable and must be reproducible. |
| Child process launch, identity ledger, logs, timeout, TERM/grace/KILL, exit capture, and restart reconciliation | Deterministic supervisor and parent nodes | Process control is exact infrastructure state; artifacts cannot substitute for the real exit status. |
| Advancing a lane goal and adapting implementation | LLM lane worker inside the child Attractor process | The implementation path may change as the domain surprises the worker. |
| Running lane and aggregate verifier commands | Deterministic nodes | Exit status and captured output are the primary machine evidence. |
| Failure-signature comparison and budget accounting | Deterministic nodes | Loop control must not depend on model judgment. |
| Root-cause diagnosis after repeated failure | Fresh or gate-class LLM context | Classification may require semantic judgment, but its proposed correction is tested by the deterministic verifier. |
| Optional qualitative lane critique | Independent LLM gate plus deterministic artifact classifier | Some acceptance criteria cannot be reduced to a command; the reviewer must be outside the worker context, and its versioned artifact must be schema-valid and tied to the exact commit. |
| Ownership diff, commit existence, ancestry, clean-state checks | Deterministic nodes | A worker cannot attest its own git side effects. |
| Merge/cherry-pick, rollback of a failed candidate, merge journal | Deterministic nodes | Integration is state mutation with exact success criteria. |
| Cross-lane coherence review | Fresh independent LLM gate plus the same deterministic artifact classifier | Semantic conflicts can survive lane-local mechanical checks. The shared review interface ties the verdict to final HEAD and routes correction to named lane IDs. |
| PR existence and exact-head verification | Deterministic remote query | `OpenPR` cannot certify its own external side effect. |

No LLM node is used merely to translate formats, increment counters, select the
next lane, compare SHAs, or parse known structured state.

## Evidence Model

### Evidence hierarchy

Evidence is accepted in this order:

1. Git object, worktree, source-SHA, and compiled-source-manifest state observed
   by deterministic commands.
2. Canonical process identity, real process exit, and process-run evidence.
3. Verifier command, exit status, timeout status, and captured output.
4. Deterministic ownership and dependency checks.
5. Independent qualitative review tied to an exact commit, only for criteria
   that genuinely require judgment.
6. Remote API state for delivery.

Worker self-report is never in this hierarchy.

### Required lane artifacts

Each lane writes durable, lane-scoped artifacts under a run-scoped state
directory rooted at `state_root/lanes/<lane-id>/`. Execution never writes
checkpoint, session, log, feedback, candidate, or result state under
`pipelines/PLAN_SLUG/`; source DOT, source scripts, and committed historical
fixtures remain byte-clean. The implementation may choose additional
serialization, but the state must include:

- contract snapshot and hash;
- process ledger and transition history;
- durable combined stdout/stderr and child event log;
- `product_base_sha`, `execution_source_sha`, current integration base, and
  candidate head SHAs;
- attempt/convergence record;
- latest verifier log and status;
- curated feedback and diagnosis;
- ownership diff/check result;
- optional qualitative verdict;
- candidate commit reference; and
- final disposition with a named reason.

The child's terminal `lane-result.json` is an atomic summary with this minimum
schema:

| Field | Contract |
|---|---|
| `schema_version` | Exact value `goal-plan.lane-result/v1`. |
| `lane_id`, `plan_hash` | Exact compiled lane ID and approved plan hash. |
| `process_run_id`, `launch_attempt` | Canonical process-run ID and matching positive launch-attempt integer. |
| `product_base_sha`, `execution_source_sha` | Exact admitted source SHAs. |
| `child_dot_sha256`, `launch_command_sha256` | Exact approved child DOT and launch-contract hashes. |
| `process_ledger_path`, `child_box_session_ids` | Path to the matching durable process record and optional observability-only box-session ID array. |
| `integration_base_sha`, `candidate_head_sha` | Full expected integration base and candidate commit SHA, or null candidate when no commit exists. Both must descend from `execution_source_sha`. |
| `attempts_used`, `max_attempts` | Non-negative used count and approved positive limit. |
| `candidate_disposition` | One of `CANDIDATE`, named `FAIL`, named `BLOCKED`, `PENDING_HUMAN`, or `BUDGET_EXHAUSTED`; never parent `PASS`. |
| `verifier_evidence_paths`, `review_evidence_paths`, `ownership_evidence_path` | Run-scoped evidence references; arrays may be empty only when the candidate disposition explains why the gate was unreachable. |
| `feedback_sha256` | Hash of the final curated feedback that informed the last correction, or null when no correction occurred. |

The parent requires the child process ledger and `lane-result.json` to agree on
lane ID, both source SHAs, plan/command/DOT hashes, `process_run_id`, launch
attempt, and terminal timing. This agreement still supplies only a candidate
routing hint. Parent verification is the evidence gate that can assign `PASS`.

The fan-in collector treats a missing required result artifact as `CRASHED`.
It must not substitute an empty result, `PASS`, or "(none found)." This directly
applies `docs/RUBRIC.md`'s parallel-branch coverage rule.

### Fresh-review artifact contract

Optional lane qualitative review and final cross-lane coherence review use one
machine-readable interface. In both cases a reviewer with fresh context writes
a JSON artifact; it does not certify the artifact itself. The artifact has this
required schema:

| Field | Contract |
|---|---|
| `schema_version` | Exact value `goal-plan.fresh-review/v1`. |
| `review_kind` | Exact value `lane` or `cross_lane`. |
| `product_base_sha`, `execution_source_sha` | Exact admitted source SHAs. |
| `reviewed_head` | Full commit SHA reviewed from actual repository state. |
| `verdict` | Exact value `PASS`, `ITERATE`, or `BLOCKED`; no other verdict is valid. |
| `findings` | JSON array of objects with required `id`, `summary`, `evidence` string array, and `disposition_detail` string fields. |
| `responsible_lane_ids` | Non-empty JSON array containing only lane IDs from the approved plan. |

For `review_kind: "lane"`, `responsible_lane_ids` must be the singleton array
containing the current lane ID. For `review_kind: "cross_lane"`, it contains one
or more approved lane IDs: all integrated lanes covered by a `PASS` review, or
the specific correction owners for `ITERATE` and `BLOCKED`.

A deterministic classifier schema-validates the artifact, resolves current
HEAD directly from Git, requires both source SHAs to equal the durable run
binding, and requires `reviewed_head == current HEAD`. It then routes:

- `PASS` onward only when the relevant mechanical verifier is already green:
  the lane verifier for lane review, or `AGGREGATE_VERIFY:PASS` for cross-lane
  review;
- `ITERATE` to curated feedback and the correction surface for every
  `responsible_lane_ids` entry; and
- `BLOCKED` to `BLOCKED(review:lane:LANE_ID)` for lane review or
  `BLOCKED(review:cross_lane:SORTED_LANE_IDS)` for cross-lane review, recording
  the responsible lane IDs, findings, and artifact path.

A missing, malformed, schema-invalid, or stale artifact is a deterministic
review failure and can never be normalized to `PASS`. It remains subject to the
existing bounded retry, crash, infrastructure, and residual-classification
rules.

### Lane dispositions

| Disposition | Meaning |
|---|---|
| `PASS` | Parent reran the verifier against the exact durable commit, ownership passed, and any qualitative gate passed. |
| named `FAIL` | The lane reached a deterministic failing condition with an explicit reason code and evidence path. |
| named `BLOCKED` | The lane cannot proceed because a named dependency, access requirement, contradiction, or external prerequisite is unavailable. |
| `PENDING_HUMAN` | Evidence exposes a consequential ambiguity that the approved plan does not resolve. It is reported as a residual; it does not trigger an immediate routine gate. |
| `CRASHED` | The lane timed out, terminated unexpectedly, or failed to produce its required artifact. |
| `BUDGET_EXHAUSTED` | The lane consumed its bounded attempts without satisfying the gates. Its postmortem and last evidence are preserved. |

`FAIL`, `BLOCKED`, `CRASHED`, and `BUDGET_EXHAUSTED` are not interchangeable.
Their distinct causes determine dependent-lane handling and the residual report.

## Isolation, Dependencies, and Parallelism

### Worktree isolation

Every lane runs in a dedicated git worktree, branch, and headless child
Attractor process. The integration worktree and prepared lane branches begin at
exact `execution_source_sha`. When dependencies have already integrated, the
eligible lane is advanced to that current integration HEAD only after proving it
descends from `execution_source_sha`. The deterministic parent resolves the lane
worktree's absolute realpath and launches the approved process supervisor with
that path as OS `cwd`. The child Attractor command receives `--cwd .`, so its
pipeline runner and box sessions inherit the lane worktree mechanically.

This process boundary is the isolation mechanism. The design does not depend on
per-box `session_cwd` propagation. The verified runner-global box-CWD behavior
remains relevant only as the reason in-process folder/box lanes were rejected.
Lane state, process state, logs, and evidence are namespaced by run and lane ID
outside immutable source paths.

Before a wave starts, deterministic preflight confirms:

- repository identity, literal `product_base_sha`, exact
  `execution_source_sha`, and their ancestry;
- the admission compiled-source manifest still matches every existing
  execution worktree;
- worktree paths are available or reconcilable;
- lane branches do not point at unexpected commits;
- the child DOT, launch command, and supervisor hashes match the approved plan;
- the process ledger and lane evidence directories resolve beneath the approved
  ignored `state_root`;
- the aggregate verifier is runnable;
- lane verifiers are present and non-interactive; and
- declared ownership for concurrently running lanes does not overlap and no
  owned path or integration seam can match `pipelines/PLAN_SLUG/**`.

### Dependency semantics

A lane is eligible only after every declared dependency is:

1. parent-verified as `PASS`;
2. integrated; and
3. followed by a passing aggregate verifier.

If a dependency ends in any other disposition, its dependent lane does not
run. The dependent receives a named `BLOCKED(dependency:<lane-id>)`
disposition, preserving causality.

### Parallelism semantics

Only lanes in the same explicit wave run concurrently. They must be independent
under the approved dependency graph and ownership analysis. Shared-file or
ordering-sensitive lanes are placed in different waves.

Parallelism is therefore a consequence of proven independence, not a throughput
pool. The wave's component branches are static: one launch plus one monitor loop
per compiled lane ID. Fan-in waits for every child process to become terminal
and then mechanically classifies real exit status, missing artifacts, stale
identity, and clean terminal results before any integration begins.

## Parent Verification and Integration

For each candidate lane in stable plan order, the parent:

1. reads the child process exit and child evidence as candidate routing hints,
   never as final proof;
2. requires a zero child exit plus schema-valid, run-scoped lane evidence; a
   nonzero or missing exit remains non-pass even when candidate artifacts exist;
3. resolves the exact candidate commit from Git rather than from prose;
4. confirms the candidate and its integration base descend from
   `execution_source_sha`;
5. runs `CompiledSourceGate` against the candidate tree;
6. creates the clean disposable detached
   `candidate_verification_worktree` at that exact commit;
7. reruns the immutable lane verifier only there, proves clean before and after,
   removes/reconciles the worktree, and records all lifecycle evidence;
8. records the cumulative candidate tree delta from `execution_source_sha`,
   subtracts the already-journaled cumulative delta through the exact current
   integration base to isolate this lane's mutation, and checks that isolated
   mutation against `owned_paths`, with compiled source categorically excluded;
9. checks required qualitative evidence, when declared;
10. records the parent verdict;
11. integrates only a `PASS` candidate into the integration branch;
12. runs the aggregate verifier immediately after the integration; and
13. runs `CompiledSourceGate` against the resulting integration HEAD.

If candidate integration or the aggregate verifier fails:

- the integration branch returns to the recorded pre-candidate HEAD;
- the failed candidate is not recorded as integrated;
- merge/verifier evidence is attached to the responsible lane;
- the lane re-enters its bounded correction loop from the current integrated
  base; and
- parent verification repeats before another integration attempt.

A compiled-source failure, candidate-verification worktree lifecycle failure, or
other infrastructure verdict bypasses this correction loop and routes directly
to `INFRA_FAILURE`.

This is the integration-level corrective cycle. It prevents a lane-local green
result from poisoning the shared branch.

After every wave, the parent records the integrated HEAD and aggregate result
before the next dependency wave is prepared.

### Late multi-owner integration correction

Late correction begins only after work has been integrated. A cross-lane
`ITERATE` never fans work back into several old lane branches, because those
branches no longer share the current integrated base and cannot jointly prove a
coherent result.

Instead, every cross-lane `ITERATE` routes to one bounded
`IntegrationCorrection` worker operating directly on the integration branch.
Its input contains the complete fresh-review artifact, all findings, and the
full `responsible_lane_ids` array.

For each correction round, deterministic setup computes:

1. the **responsible set** from `responsible_lane_ids`;
2. the **affected closure** as that responsible set plus every transitive
   dependent in the static lane DAG; and
3. the allowed write set as the union of every responsible lane's
   `owned_paths` plus `plan.json.integration_seams`.

Only the responsible set contributes owned paths; transitive dependents are
included for proof invalidation and re-verification, not to widen correction
ownership. A deterministic diff check rejects any write outside the computed
allowed set. The compiled pipeline directory is always subtracted from this set,
and composition has already proved no input pattern overlaps it.

Before the worker acts, the graph appends invalidation records for every
affected lane's prior verifier and review evidence. The old artifacts remain
available for audit, but they are marked superseded and cannot satisfy any
later gate.

After `IntegrationCorrection` writes and commits a correction, the graph:

1. runs `CompiledSourceGate` against the current integration HEAD and routes any
   mismatch directly to `INFRA_FAILURE`;
2. reruns every affected-closure lane verifier against the current integration
   HEAD, in static integration order restricted to that closure;
3. rejects any verifier evidence whose `head_sha` is not that current HEAD;
4. reruns the aggregate verifier;
5. reruns fresh cross-lane coherence review; and
6. repeats only through the one `IntegrationCorrection` loop when product evidence is
   red.

An affected-closure lane-verifier failure adds that lane ID to the next
responsible set and routes back to `IntegrationCorrection`. Each worker entry
consumes one `global_budgets.max_integration_corrections` unit and also counts
toward `max_total_attempts`. Exhaustion writes named
`BUDGET_EXHAUSTED(integration_correction:SORTED_LANE_IDS)` residuals with the
last findings, closure, ownership check, verifier logs, and integration HEAD.

### Final lane-verifier sweep

After coherence returns `PASS`, and before delivery eligibility or
`COMPLETE`, `CompiledSourceGate` passes and the graph runs every lane verifier
once more against the exact current integration HEAD in full static integration
order. Each final-sweep record is bound to that one SHA,
`product_base_sha`, and `execution_source_sha`.

If any final-sweep lane verifier is red, its lane ID becomes the responsible
set for `IntegrationCorrection`; the graph computes its transitive-dependent
closure and re-enters the same bounded correction loop. After correction it
must again pass closure verification, aggregate verification, coherence review,
and the complete final sweep. No pre-merge, lane-branch, or pre-correction
verifier evidence can satisfy completion.

## Final Aggregate and Coherence Gates

After all runnable waves finish:

1. The deterministic aggregate verifier runs at final integrated HEAD.
2. A fresh independent reviewer reads the approved plan, lane evidence, final
   lane-produced diff `execution_source_sha..final_integrated_head`, the
   separately labeled compiled-plan delta
   `product_base_sha..execution_source_sha`, and actual repository state at
   that HEAD.
3. The reviewer checks cross-lane coherence: compatible interfaces, preserved
   assumptions, no duplicated or contradictory implementations, and complete
   satisfaction of qualitative criteria.
4. The reviewer writes the versioned fresh-review artifact.
5. The shared deterministic classifier schema-validates it, requires
   `reviewed_head` to equal final integrated HEAD, and routes only the exact
   `PASS`, `ITERATE`, or `BLOCKED` verdicts.

Actionable coherence findings route only to `IntegrationCorrection`, carrying
all responsible lane IDs. They must survive affected-closure lane verification,
aggregate verification, a fresh coherence review, and the final all-lane
verifier sweep. If responsibility is ambiguous or correction budget is
exhausted, the finding becomes an evidence-backed residual rather than an
invented pass.

Final coherence review is unreachable until the aggregate wrapper emitted
`AGGREGATE_VERIFY:PASS` for the same HEAD. A coherence `PASS` therefore cannot
mask a red or stale mechanical result.

## Budgets and Exhaustion

### Per-lane budget

Each lane contract declares its attempt budget. Every entry into the
verification-bearing attempt cycle consumes budget, including retries caused by
mechanical failure, qualitative refusal, or reintegration failure.

The lane budget cannot be reset by re-entering from parent integration or
coherence review.

Each child launch also has one wall-clock limit, `max_child_seconds`, enforced by
the deterministic process supervisor across the entire child Attractor run.
That wall is a safety bound, not evidence of completion. When it fires, the
supervisor performs TERM -> grace -> KILL against the verified child process
group, persists the timeout and real exit status, and the parent classifies the
lane `CRASHED` or `BUDGET_EXHAUSTED` according to whether trustworthy
lane-attempt evidence exists.

### Run-wide budget

The plan also declares one run-wide ceiling across all lane attempts and
corrective re-entries. This counter is minted once and never replenished by:

- moving to another wave;
- reopening a lane after aggregate failure;
- coherence-review correction;
- restart/recovery; or
- retrying delivery.

The run-wide ceiling prevents nested per-lane, aggregate, and coherence loops
from multiplying into an unbounded run, following the
`resolve_expert_builder` precedent.

`global_budgets.max_integration_corrections` separately bounds entries into the
single late `IntegrationCorrection` worker. It is a sub-budget of
`max_total_attempts`, not a renewable pool. Red affected-closure or final-sweep
lane verifiers consume this same correction budget.

Engine wall-clock and step limits remain safety fuses, not completion
conditions. The graph's own budget walls must fire first and produce usable
evidence.

### Exhaustion behavior

Exhaustion writes a postmortem that names:

- the counter and limit reached;
- attempts made;
- last verifier/coherence evidence;
- whether progress was descending, oscillating, or wandering;
- affected lane and dependent lanes; and
- the remaining unsatisfied criteria.

The exhausted lane becomes `BUDGET_EXHAUSTED`. The run continues only far
enough to classify unaffected durable work and assemble `RESIDUALS_READY`;
exhaustion never routes directly to `COMPLETE`.

Integration-correction exhaustion preserves the integration branch and records
named residuals for the responsible set and affected closure. It never restores
or resumes old lane branches.

## Human Gates

### Plan approval

The only pre-mutation gate presents:

- the full lane/dependency graph;
- `product_base_sha`, admitted `execution_source_sha`, their ancestry, and the
  known compiled-plan delta between them;
- the compiled-source manifest hash;
- ownership and collision analysis;
- lane and aggregate verifiers;
- child DOT/launch hashes, lane wall limits, and process-supervision policy;
- budgets;
- planned integration order; and
- delivery intent.

No worktree or repository mutation occurs before approval. An invocation may
carry explicit preapproval, but the graph must still render and persist the
same plan and preflight evidence before mutation.

Rejecting or cancelling this gate produces `ABORTED`.

### Residual disposition

The second possible gate appears only after bounded convergence cannot reach
`COMPLETE`. It presents the residual report together with:

- verified passing commits and whether they were integrated;
- every non-pass lane disposition;
- blocked dependents;
- aggregate/coherence status at the retained HEAD; and
- exact evidence and postmortems.

The operator decides the disposition of that evidence-backed partial result.
The gate cannot relabel residual work as `COMPLETE`. No partial work is
automatically delivered.

There are no routine gates between waves.

## Durable State and Crash Recovery

Recovery is a graph pattern, not an assumption about engine checkpoints. Every
run begins with deterministic reconciliation.

### Durable state

The run persists:

- approved plan snapshot/hash and preapproval/approval evidence;
- compiled-pipeline path, embedded `plan_sha256`, typed runtime inputs,
  selected target-repository identity mode and its remote-match or
  history-anchor proof, exact `product_base_sha`, exact
  `execution_source_sha`, their ancestry proof, and the separated compiled-plan
  and lane-produced delta ranges;
- admission compiled-source manifest path/hash and every subsequent
  `CompiledSourceGate` record;
- run-wide and per-lane counters;
- worktree/branch/base/head mapping, including recorded `realpath` values for
  every lane worktree, disposable candidate-verification worktree, and the
  integration worktree;
- per-lane process ledger and transition history, including supervisor/child
  canonical Linux identity tokens, cmdline hashes, PGIDs, executable realpaths,
  environment/command/DOT hashes, `process_run_id`, optional box-session IDs,
  log path, start/end times, timeout/cancellation state, and real exit status;
- lane contracts, evidence, and dispositions;
- parent-verification records, including detached candidate SHA/path,
  verifier hash, clean-before/after results, and removal/reconciliation proof;
- integration journal whose every entry binds `product_base_sha`,
  `execution_source_sha`, candidate SHA, and pre-merge/post-merge HEADs;
- integration-correction journal with each round's responsible set, affected
  closure, allowed write set, both source SHAs, compiled-source-gate evidence,
  evidence invalidations, commit, and budget count;
- aggregate-verifier records after each merge;
- final aggregate and versioned fresh-review records;
- final-sweep lane-verifier records bound to final integration HEAD;
- terminal classification;
- versioned `result.json`; and
- the versioned delivery-attempt ledger, branch, expected head, PR URL, observed
  remote head, and verification result.

State writes must be atomic. Human-readable reports are derived from structured
state; they are not the source of truth.

### Reconciliation rules

On restart, the graph compares state with reality:

1. Rerun admission against the immutable adjacent `plan.json` and embedded
   `plan_sha256`, including graph/plan correspondence.
2. Re-prove the selected `remote` or `history_anchor` target-repository
   identity policy, then confirm `plan_id`, typed runtime inputs, `state_root`,
   `product_base_sha`, `execution_source_sha`, their ancestry, and the
   compiled-source manifest hash match the durable run record.
3. Run `CompiledSourceGate` against the execution source and every existing
   lane, candidate-verification, and integration worktree. Any mismatch is
   immediate `INFRA_FAILURE`.
4. Enumerate actual worktrees and branches beneath `state_root`; canonicalize
   each with `realpath` and require equality with its recorded path and Git
   common object database.
5. Reconcile any disposable candidate-verification worktree left by a crash.
   Require its recorded candidate SHA/path, exact detached HEAD, and clean full
   status; dirty, wrong, or unremovable state is `INFRA_FAILURE`. Remove and
   prune a valid leftover, record reconciliation evidence, and restart parent
   candidate verification from worktree creation rather than trusting a partial
   verifier result.
6. Reconcile every nonterminal child process ledger. Before polling, adoption,
   or signalling, reread and match for both supervisor and child the canonical
   Linux boot-ID/PID/starttime token, exact cmdline hash, PGID, executable
   realpath, and launch command hash.
7. Adopt monitoring when the recorded supervisor and child are both alive and
   match. If a matching child remains without its supervisor, terminate only
   that verified process group and classify the attempt `INTERRUPTED`; no new
   process may reuse the stale PID record. Missing/unreadable procfs identity or
   mismatch is stale-PID `INFRA_FAILURE` and is never signalled.
8. If `/proc/<pid>` is absent, reconcile from the durable supervisor exit
   record, child result/evidence, compiled-source evidence, and Git state;
   process absence alone never means success.
9. Resolve recorded commits directly from Git and require every work commit and
   current integration HEAD to descend from `execution_source_sha`.
10. Reclassify a purported completed lane whose artifact or commit is missing
   as `CRASHED` or `INFRA_FAILURE`, depending on whether lane work or the
   substrate is untrustworthy.
11. Require the persisted child exit status even when candidate artifacts exist;
   a missing or nonzero exit cannot be normalized to `PASS`.
12. Rerun pre-integration parent verification only through a newly created
   clean `candidate_verification_worktree` when its lifecycle evidence is
   absent, stale, incomplete, or not bound to the candidate commit.
13. Reconcile the integration journal against the actual integration HEAD and
   Git ancestry before attempting another merge.
14. Recompute every recorded integration-correction affected closure from the
   static DAG and require it to match the durable journal. Preserve prior
   artifacts but enforce all recorded invalidations.
15. If an integration-correction commit exists but its proof sequence is
   incomplete, first run `CompiledSourceGate`, then resume at affected-closure
   verification against current integration HEAD rather than rerunning the
   worker.
16. Rerun the aggregate verifier if the actual HEAD lacks a bound passing
   record.
17. Reject a fresh-review artifact whose source SHAs differ or whose
   `reviewed_head` does not equal actual HEAD.
18. Require a complete all-lane final sweep and a current compiled-source pass
    at actual integration HEAD before
    restoring completion eligibility.
19. Reconcile the delivery ledger, then query remote PR state at the ledger's
   exact expected head if delivery may already have occurred; never open a
   duplicate merely because local state is incomplete.

Reconciliation is idempotent. It skips work only when durable evidence and real
state agree. Ambiguous or contradictory infrastructure state fails loudly as
`INFRA_FAILURE`.

## Terminal and Failure Behavior

| Terminal | Required condition | Delivery behavior |
|---|---|---|
| `COMPLETE` | Both source SHAs remain bound; the compiled-source manifest passes immediately before finalization; all work is integrated; no proof invalidation or integration-correction exhaustion residual remains unsatisfied; every lane verifier passes in the final sweep at exact final integration HEAD; the aggregate verifier and fresh coherence review pass at that same HEAD; and, when delivery is enabled, the PR is independently confirmed at exact HEAD. | May auto-deliver one PR. |
| `RESIDUALS_READY` | All lanes are terminal or dependency-blocked, but at least one is not `PASS`, or final aggregate/coherence criteria remain unsatisfied. Passing work and every residual have evidence. | Never auto-delivers; requires residual disposition. |
| `INFRA_FAILURE` | Source-SHA/compiled-byte identity, Git/worktree state, candidate-verification worktree lifecycle, Linux procfs process identity/supervision, verifier execution substrate, credentials, remote API, or recovery state cannot be trusted enough to classify product work honestly. | No delivery. |
| `ABORTED` | The plan was rejected/cancelled before mutation, or the operator explicitly stopped the run at an allowed gate. | No delivery. |

### Finalizer machine contract

Every terminal route passes through one deterministic finalizer. It atomically
writes the run root's versioned `result.json` with, at minimum:

- `schema_version` with exact value `goal-plan.result/v1`;
- `status` with exact value `COMPLETE`, `RESIDUALS_READY`, `INFRA_FAILURE`, or
  `ABORTED`;
- `plan_hash`;
- `product_base_sha` and `execution_source_sha`;
- `compiled_source_manifest_path` and `compiled_source_manifest_sha256`;
- `integrated_head_sha`, or `null` when no integration HEAD exists;
- `compiled_plan_delta` describing `product_base_sha..execution_source_sha`;
- `lane_produced_delta` describing
  `execution_source_sha..integrated_head_sha`, or null when no integration HEAD
  exists;
- `lane_dispositions`;
- `child_process_evidence_paths`;
- `integration_correction_records`;
- `aggregate_evidence_path`;
- `fresh_review_evidence_paths`;
- `final_sweep_evidence_paths`;
- `residual_evidence_paths`;
- `delivery_ledger_path`; and
- `delivery_pr_url` and `delivery_verified_head_sha` when delivery was
  requested, otherwise `null`.

The finalizer sets `goal_plan.status` to the same exact `status` value and emits
exactly one of these strings as its last non-empty stdout line, with no prose
after it:

| `goal_plan.status` | Last-line token |
|---|---|
| `COMPLETE` | `GOAL_PLAN:COMPLETE` |
| `RESIDUALS_READY` | `GOAL_PLAN:RESIDUALS_READY` |
| `INFRA_FAILURE` | `GOAL_PLAN:INFRA_FAILURE` |
| `ABORTED` | `GOAL_PLAN:ABORTED` |

The finalizer completes its write successfully so the graph can route on
`tool.last_line`; the explicit terminal carrier then preserves the intended
pipeline outcome. `COMPLETE` is the only successful and deliverable outcome.
The other three remain distinct non-success, evidence-bearing outcomes rather
than aliases for a generic failure.

Before writing any terminal result, including `INFRA_FAILURE`, the finalizer
attempts one last `CompiledSourceGate` and records its evidence. Only a passing
gate can emit `COMPLETE` or begin delivery; a red or unexecutable gate forces or
preserves `INFRA_FAILURE`.

Terminal nodes must route explicitly to the graph exit with the intended machine
status. They must not dead-end and become `no_matching_edge` authoring errors.
Failure routes must account for real node outcomes; no "successful failure"
sentinel may rely on an unreachable `outcome=fail` edge.

## PR Delivery

The `COMPLETE` path is the only automatic-delivery path. A run becomes eligible
for that path only after all lane, aggregate, and coherence gates pass. When
delivery is enabled, the final `COMPLETE` terminal is emitted only after
delivery is independently verified.

The implementation copies the proven portable `deliver_pr.dot` into the
pipeline-local `subgraphs/` directory, as required by `AGENTS.md` and
`docs/RUBRIC.md` section 5. It must retain independent push and PR existence
checks.

`goal_plan` adds one final deterministic assertion: the remote PR head SHA must
equal the exact final integrated HEAD that passed the all-lane final sweep,
aggregate verification, and coherence review. A real PR at the wrong head is
not successful delivery.

Delivery must not mutate that verified HEAD. If the delivery subgraph changes
local HEAD, the exact-head assertion fails; the run cannot claim `COMPLETE`
without re-establishing the aggregate and coherence evidence for the new HEAD.

Delivery has a hard limit of two attempts total for the run, including across
crash recovery. Before any network mutation, each attempt appends a durable
`started` entry to the run root's `delivery/attempts.jsonl`. Every ledger entry
uses schema version `goal-plan.delivery-attempt/v1` and records:

- `schema_version` with exact value `goal-plan.delivery-attempt/v1`;
- `attempt` as integer `1` or `2`;
- `product_base_sha` and `execution_source_sha`;
- `compiled_source_manifest_sha256`;
- `branch` as the delivery branch;
- `expected_head_sha` as the exact expected head SHA;
- `phase` as `started` or `completed`;
- `existing_pr_query` as the remote query result;
- `action` as the action taken;
- `pr_url`, if any;
- `observed_remote_head_sha` from independent verification;
- `verified` as a boolean; and
- `failure_reason`, if any.

Before each attempt, delivery queries the remote for an existing PR whose head
is the recorded branch at the exact expected head SHA. If one exists, the
attempt does not create another PR; it proceeds directly to independent
verification. If none exists, the proven delivery subgraph may push/open the
PR. In both cases, the attempt succeeds only after a separate remote query
confirms that the PR exists and that its head SHA exactly equals the ledger's
expected head SHA. The delivery actor's own report is never sufficient.

Immediately before any delivery query or mutation, `CompiledSourceGate` must
pass at the exact expected integration HEAD and both source SHAs must match the
ledger. Delivery evidence and the PR report preserve the known compiled-plan
delta separately from the lane-produced delta.

An incomplete ledger entry discovered during recovery counts as an attempt and
is reconciled against remote state before another attempt can start. No third
attempt is possible. If neither attempt obtains independent exact-head
verification, the integrated branch, verifier/review evidence, and ledger are
preserved, and the finalizer emits `GOAL_PLAN:INFRA_FAILURE`; the pipeline does
not claim `COMPLETE`. Delivery attempts cannot consume or reset lane-convergence
budget.

## Reusable Precedent

Implementation should copy these proven shapes rather than inventing new ones:

| Precedent | Reuse |
|---|---|
| Attractor bundle `examples/patterns/task-runner.dot` | `goal_lane.dot`'s attempt -> deterministic verify -> triage/diagnose -> critique -> curated feedback convergence skeleton, plus explicit budget/postmortem behavior. |
| `pipelines/pr_review/pr_review.dot` | `shape=component` fan-out, `shape=tripleoctagon` fan-in, file-backed cross-branch results, and explicit missing-artifact/crashed-lane detection. |
| `pipelines/resolve_expert_builder/resolve_expert_builder.dot` | One run-wide corrective-work ceiling that cannot be replenished by entering another fix loop, and evidence-rich exhaustion reporting. |
| Existing `subgraphs/deliver_pr.dot` | Commit/push/PR delivery with downstream checks of real remote state. Copy it unchanged first, then add exact-head verification in the parent pipeline rather than rebuilding delivery. |
| Existing `goaltractor` composition behavior | Design-time materialization of arbitrary approved plans as static DOT. Reuse it as the composition front end; do not copy its intelligence into runtime. |
| The bounded CWD, convergence, and macro-control probes | Evidence for the process boundary, external correction cycle, and real-exit ledger requirement. They inform production tests but are not copied or shipped as production pipelines. |

## Anticipated File Changes

This repository implements one canonical, statically compiled member of the
family, the reusable local subgraphs, and the deterministic process-supervisor
support that `goaltractor` copies into arbitrary real plan directories. It does
not add a generic root graph, compiler, or runtime scheduler. The expected
footprint is:

```text
pipelines/goal_plan_smoke/goal_plan_smoke.dot
pipelines/goal_plan_smoke/plan.json
pipelines/goal_plan_smoke/goal_plan_smoke.md
pipelines/goal_plan_smoke/subgraphs/goal_lane.dot
pipelines/goal_plan_smoke/subgraphs/deliver_pr.dot
pipelines/goal_plan_smoke/python/goal_plan_runtime.py
pipelines/goal_plan_smoke/python/process_supervisor.py
pipelines/goal_plan_smoke/python/tests/test_goal_plan_runtime.py
pipelines/goal_plan_smoke/python/tests/test_process_supervisor.py
README.md
```

`goal_plan_runtime.py` is the single deterministic home for source-SHA
admission, compiled-source manifests/gates, ownership-pattern rejection,
candidate-verification worktree lifecycle, and delta reporting. DOT nodes call
that module rather than duplicating shell logic. `process_supervisor.py` remains
the single home for Linux process identity and child lifecycle.

The smoke exemplar proves orchestration rather than product behavior. In a
temporary repository, two Wave 1 fixture lanes each produce a file in disjoint
owned paths; one Wave 2 integration fixture lane depends on both and produces a
third fixture file. Each fixture lane runs as a separately supervised child
Attractor process. Its graph is fixed and self-contained. The existing
`goaltractor` remains the composition front end that materializes arbitrary
real plans to the same directory and contract; it is not reimplemented here.

This design-document revision does not implement those files.

## Verification Strategy

Verification follows the repository's live-run gradient because this is
orchestration behavior, not a library-only change.

### Static checks

1. Parse and render every DOT file with Graphviz.
2. Run `attractor lint` on the entry graph and both subgraphs.
3. Audit the implementation against every item in `docs/RUBRIC.md`.
4. Confirm all deterministic routes use observed state and explicit failure
   edges; no LLM judgment gate uses `shape=diamond`.
5. Confirm every terminal is reachable and routes explicitly to the exit.
6. Confirm the README and companion guide describe the actual graph.
7. Validate the aggregate-verifier evidence schema, exit/token normalization,
   verifier-hash guard, shared fresh-review schema, finalizer token map, and
   two-attempt delivery ledger against the contracts above.
8. Validate `plan.json` schema and exact-byte hash, embedded `plan_sha256`,
   graph/plan correspondence, both target-repository identity modes, and typed
   runtime-input rejection cases.
9. Prove the graph contains no manifest-driven scheduler: lane, wave,
   dependency, integration-order, and budget dispatch all remain explicit DOT
   nodes, edges, and constants.
10. Prove lane verifier-definition hashes include all three symbolic CWD
    policies and no absolute paths; aggregate hashes retain only
    `integration_worktree`; every invocation records and validates its resolved
    `realpath` separately.
11. Validate `product_base_sha`, the non-self-referential containing-commit
    binding for exact `execution_source_sha`, their graph attributes and
    ancestry, and separate compiled-plan/lane-produced reporting ranges.
12. Validate every lane's child DOT hash, exact ordered argv/typed-parameter
    schema, closed environment policy, `process_run_id` template,
    process-supervisor hash, expected evidence schema, child wall budget, and
    static launch/monitor node correspondence.
13. Validate ownership and integration-seam schemas reject every pattern that
    can match `pipelines/PLAN_SLUG/**`; validate complete manifest path-set,
    mode, length, and byte comparisons at every `CompiledSourceGate`.
14. Unit-test Linux process identity, atomic ledger transitions, exact
    argv/env/CWD hashing, real exit capture, timeout escalation, cancellation,
    stale-PID rejection, and restart reconciliation in
    `process_supervisor.py`.

### Primary live smoke scenario

Run the canonical `goal_plan_smoke` pipeline against a temporary,
GitHub-backed Git repository with a known aggregate verifier and three fixed
fixture lanes:

- `lane_a` and `lane_b` each produce one fixture file in disjoint owned paths
  and run concurrently in Wave 1 as separate child Attractor processes launched
  from distinct worktrees.
- `lane_b` is seeded so its first verifier run fails with a stable, actionable
  error; it must consume one attempt, preserve the log, use curated feedback,
  and pass on a later attempt.
- `lane_c` is the integration fixture lane. It produces a third fixture file,
  depends on both Wave 1 lanes, and cannot start until both commits are
  parent-verified, integrated sequentially, and followed by green aggregate
  checks.
- A controlled first coherence review returns `ITERATE` with `lane_a` and
  `lane_b` as responsible. The static DAG makes the affected closure
  `lane_a`, `lane_b`, and transitive dependent `lane_c`.
- Delivery is enabled, producing one real PR.

The live smoke passes only if direct observation proves:

1. The adjacent `plan.json` hash equals embedded `plan_sha256`; admission proves
   graph/plan correspondence, an exact normalized fetch-remote identity match,
   literal `product_base_sha`, exact containing `execution_source_sha`, their
   ancestry, and the complete compiled-source manifest before mutation.
2. Typed runtime inputs are bound, `state_root/worktrees` is the dedicated
   external worktree root, state is ignored, and no mutation occurs before
   approval/preapproval validation.
3. The integration worktree and prepared Wave 1 branches begin at exact
   `execution_source_sha`; a later-wave lane begins at a parent-verified
   integration HEAD descended from it. Product reporting separately names the
   compiled-plan and lane-produced delta ranges.
4. Wave 1 launches two concurrent child Attractor processes in distinct
   worktrees. Process and child evidence show that each OS CWD and Attractor
   root CWD is its assigned worktree and that its box-session relative writes
   remain there.
5. Every process ledger binds both source SHAs, canonical `process_run_id`,
   exact ordered argv/params, environment hash, CWD/command/DOT hashes,
   canonical Linux process identities, optional box-session IDs, durable log,
   and real exit status.
6. `lane_b`'s first failure is visible and causes a corrective cycle rather
   than a silent pass or blind restart.
7. The correction is genuinely dependent on the changed verifier feedback: a
   control run with unchanged/withheld feedback remains red, while the changed
   feedback produces a different candidate hash and later green evidence.
8. Parent verification creates a clean detached
   `candidate_verification_worktree` at the exact candidate SHA, runs the
   verifier only there, proves clean before and after, removes/reconciles it,
   and records canonical path, SHA, verifier hash, and lifecycle evidence.
9. Ownership checks pass, reject an out-of-scope write, and categorically
   reject any compiled-pipeline write or integration seam.
10. Integration occurs in stable order, with an aggregate-verifier record and
   passing `CompiledSourceGate` after
   each merge that names the exact HEAD and verifier hash and whose last-line
   token agrees with its JSON verdict. The immutable hash contains
   `integration_worktree`, while the evidence separately records the verified
   absolute cwd.
11. `lane_c` starts only after both dependencies are integrated and green.
12. Cross-lane `ITERATE` invokes one `IntegrationCorrection` on the integration
   branch, never the old lane branches; its write set is limited to the
   responsible lanes' ownership union plus declared integration seams.
13. Correction invalidates prior proof for the affected closure, passes
    `CompiledSourceGate`, then reruns
    all three closure lane verifiers at current integration HEAD before
    aggregate and coherence gates pass.
14. The final sweep reruns every lane verifier at one exact final integration
    HEAD; final aggregate and fresh-review records name that SHA and both source
    SHAs.
15. The pre-finalization and pre-delivery compiled-source gates match the
    admission manifest.
16. The delivery ledger records no more than two attempts, both source SHAs,
    and the manifest hash, and the remote PR
    exists with a head SHA equal to its exact expected head.
17. `result.json` reports both delta ranges; `result.json`,
    `goal_plan.status`, and the last-line token agree on `COMPLETE` only after
    all sixteen preceding observations hold.

### Fault and recovery probes

The implementation is not ready until live probes also demonstrate:

- deleting one lane's required result before fan-in yields `CRASHED`, not a
  clean result;
- a child that writes its expected artifact and then exits nonzero remains
  non-pass because the process ledger preserves the real exit status;
- killing the parent graph while two children run leaves independently
  supervised child process groups observable; restart safely adopts matching
  canonical Linux supervisor/child identities or classifies/terminates them
  under the recovery contract;
- a child wall timeout performs TERM -> configured grace -> KILL against the
  whole verified child process group, revalidating identity before each signal,
  and records the timeout and exit;
- stale-PID probes independently change PID start ticks, cmdline bytes, PGID,
  executable realpath, and launch command hash; each mismatch is
  `INFRA_FAILURE` and the PID is never signalled;
- a changed boot ID simulates reboot, a reused PID has the wrong canonical
  `linux:<boot_id>:<pid>:<starttime_ticks>` token, and permission/mount fault
  injection makes each required procfs identity file unreadable; every case
  fails loudly without adoption, polling, TERM, or KILL;
- when `/proc/<pid>` is absent after a real exit, recovery uses the durable
  supervisor exit record, child result/evidence, and Git state and never
  interprets absence alone as success;
- a candidate-verification worktree with wrong HEAD, dirty-before state,
  dirty-after state, failed non-force removal, stale worktree registration, or
  crash-left incomplete lifecycle evidence yields `INFRA_FAILURE`; a clean
  crash-left worktree is removed/reconciled and verification restarts in a new
  detached worktree;
- two consecutive runs leave source DOT, scripts, and committed fixtures
  byte-clean, with every generated log, event, checkpoint, feedback, and result
  beneath `state_root/lanes/<lane-id>/`;
- deleting, adding, mode-changing, or byte-changing any compiled-source entry
  is detected after child exit, before candidate verification, after merge,
  after integration correction, during restart, and before
  finalization/delivery; every case reaches `INFRA_FAILURE` without lane
  correction;
- an impossible verifier exhausts its lane budget, produces a postmortem,
  blocks dependents by name, reaches `RESIDUALS_READY`, and opens no automatic
  PR;
- an out-of-ownership write is rejected even when the lane verifier passes;
- an aggregate failure after a candidate merge restores the pre-merge HEAD and
  routes evidence back to the responsible lane;
- a `plan.json` byte change, DOT/plan lane mismatch, relative runtime path,
  wrong `product_base_sha`, non-containing or non-descendant
  `execution_source_sha`, argv/param order mismatch, output-path escape,
  incompatible reused `run_id`, non-Linux platform, or mode mismatch fails
  admission before mutation;
- HTTPS, `ssh://`, and scp-like forms for the same fetch remote normalize to
  the same `host[:port]/path`, while a host, non-default-port, path-case, or
  repository-path mismatch fails remote identity admission;
- `history_anchor` admission fails when the plan commit, product-base object, or
  execution-source object is
  missing, the committed blob hash differs, the working plan artifact differs,
  the product base is not an ancestor of the plan commit, or the plan commit is
  not an ancestor of the containing execution source;
- changing the aggregate verifier definition after approval yields
  `AGGREGATE_VERIFY:INFRA` before the changed verifier runs;
- the same aggregate/lane verifier contract retains one
  `definition_sha256` across different run directories; the lane hash includes
  all three symbolic CWD policies while the aggregate hash includes only
  `integration_worktree`; a missing,
  replaced, or incorrectly resolved recorded worktree `realpath` yields
  infrastructure failure before verification;
- a missing, malformed, or stale fresh-review artifact is rejected and never
  advances as `PASS`;
- a multi-owner coherence `ITERATE` creates one integration-branch correction,
  rejects a write outside the ownership union plus integration seams, computes
  the full transitive-dependent closure, rejects every compiled-source write,
  runs `CompiledSourceGate`, and invalidates its old evidence;
- a red affected-closure or final-sweep lane verifier routes back to
  `IntegrationCorrection`, while correction-budget exhaustion records named
  residuals and never resumes old lane branches;
- restarting after an integration-correction commit resumes closure proof at
  current integration HEAD rather than duplicating the correction;
- restarting after a lane commit but before integration reconciles the commit
  without duplicate work or duplicate merge;
- restarting after remote PR creation discovers the existing PR and verifies
  its head instead of opening another;
- two unverifiable delivery attempts preserve the integrated branch and end
  with `GOAL_PLAN:INFRA_FAILURE`, with no third attempt; and
- an unavailable or untrustworthy verifier/git/remote substrate reaches
  `INFRA_FAILURE` rather than consuming model-correction budget.

The smoke evidence consists of the exact commands, exit statuses, git SHAs,
verifier logs, state artifacts, rendered graph, and remote PR/API output. Lane
or reviewer prose alone cannot satisfy any check.

## Open Questions

None.