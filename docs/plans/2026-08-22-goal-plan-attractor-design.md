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
cycle; the same supervised-child boundary owns integration-correction and
delivery runs. This is parent/child Attractor composition, not nested app-cli
`/goal` orchestration.

## Goals

- Make every approved lane and dependency visible in DOT.
- Preserve adaptive, feedback-informed goal pursuit inside each bounded lane.
- Isolate concurrent lanes in separate git worktrees and separate headless
  child Attractor processes whose OS working directories are those worktrees.
- Supervise every child through one accountable long-lived per-child reaper,
  durable intent/ledger/ack/result records, logs, timeouts, process-group
  cancellation, and restart reconciliation.
- Enforce verification-bearing adaptive attempts, separately bounded process
  launches, and the run-wide deadline through one locked external budget
  ledger.
- Reserve each supervised integration-correction child launch as one immutable
  correction round before launch; its internal verifier-bearing adaptive
  attempts remain independently charged through `ReserveGlobalAttempt`.
- Require every lane and integration-correction child to execute a deterministic
  `ReserveGlobalAttempt` node before each adaptive attempt; process
  starts/restarts never stand in for attempt accounting.
- Launch every lane, integration-correction, and delivery child from one
  immutable `attractor_runner_argv_prefix` with the exact compiled `provider`.
- Launch the parent Attractor CLI only after the launching process has changed
  its OS CWD to the canonical `target_repo`; require the parent process CWD,
  literal `--cwd .` resolution, invoked parent DOT realpath, DOT bytes/hash,
  compiled provider, and runner prefix to remain bound to that repository and
  `execution_source_sha`.
- Execute every supervisor start and control operation from one separately
  immutable external `trusted_supervisor_argv_prefix`; no supervisor operation
  uses PATH, a shell command string, or a target-repository interpreter/script.
- During the first green admission, before any repository mutation, prove the
  checked-out `goal_plan_runtime.py` and `goal_plan_supervisor.py` bytes against
  both `execution_source_sha` and the compiled-source manifest, then materialize
  byte-exact, non-writable copies from those Git blobs beneath external
  `state_root` and bind their exact Git/interpreter/executable identities.
- After that admission, execute every safety-critical gate, budget/process/
  worktree control, cleanup, finalizer, and recovery operation only through the
  external `trusted_runtime_argv_prefix` or
  `trusted_supervisor_argv_prefix`; target-repository runtime files remain
  source evidence and are never a safety-critical executable.
- Separate the approved product baseline from the later execution-source commit
  that contains the complete compiled pipeline, and bind both identities through
  every runtime and evidence boundary.
- Keep the complete compiled pipeline directory byte-immutable throughout the
  run; source mutation is infrastructure failure, never corrective lane work.
- Accept lane completion only after an exact non-interactive verifier passes.
- Require a durable commit before a lane can be integrated.
- Have the parent independently rerun each lane verifier against the exact
  commit proposed for integration through the shared read-only verifier
  envelope.
- Enforce declared path ownership before integration.
- Integrate passing lane commits sequentially.
- Run the aggregate verifier through the same envelope after every integration,
  before every coherence review, and after the final all-lane sweep.
- Run a fresh cross-lane coherence review against the fully integrated result.
- Route late multi-owner findings through one bounded integration-branch
  correction loop.
- After coherence passes, rerun every lane verifier at one exact final
  integration HEAD, then require `final-aggregate-after-sweep` at that same
  HEAD before completion.
- Optionally deliver one PR by adapting the proven `deliver_pr.dot` topology
  into a supervised child running in a clean disposable final-HEAD worktree
  whose generated state is rooted only at external `delivery_state_root`, then
  independently verify that the remote PR points at the exact integrated HEAD.
- Recover by reconciling durable state with real git, worktree, verifier,
  merge, and remote PR state, but only after validating or deterministically
  rehydrating the exact external trusted-runtime binding from Git blobs at
  `execution_source_sha`.
- Record every post-approval lane, integration, candidate-verification, and
  delivery worktree in `run-owned-worktrees.json`; reject foreign paths and
  when current `FULL` authority permits Git cleanup, clean up only exact
  recorded run-owned worktrees.
- Recompute pre-terminal mutation authority from the current parent-runner,
  trusted-runtime, target/source-identity, and compiled-source gates. Grant
  `FULL` only when all are green; grant `EXTERNAL_ONLY` only when the external
  trusted runtime remains green but a repository/source gate is red; otherwise
  grant `NONE`, perform no Git mutation or general signalling, and stop as
  infrastructure-blocked.
- Route every intended terminal state through `PreTerminalCleanup`, let that
  phase choose the final status from real process/worktree state, and only then
  publish durable terminal result/status/token/carrier evidence.
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
- Programmatic host interviewer integration. That is future separate work, not a
  schema-v1 interface; v1 interactive approval exists only on an attached
  standalone console.

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
    goal_plan_runtime.py
    goal_plan_supervisor.py
```

`plan.json` is versioned design-time and audit data. It is not a runtime
scheduling manifest: runtime must not iterate its `lanes` or `waves` to decide
what runs next. The generated DOT owns dispatch and contains the actual program.

#### `plan.json` contract

`plan.json` has these required typed fields:

| Field | Type and invariant |
|---|---|
| `schema_version` | String with exact value `goal-plan.plan/v3`. |
| `plan_id` | Slug string equal to `PLAN_SLUG`; stable across runs of the same compiled plan. |
| `source_request` | Non-empty string containing the originating request or its durable reference. |
| `target_repo` | Object with `vcs: "git"`, `identity_mode: "remote"` or `"history_anchor"`, and the mode-specific fields defined below. |
| `product_base_sha` | Full immutable commit SHA of the approved product baseline used for requirement provenance and product-level delta reporting. It must be an ancestor of the admitted `execution_source_sha`. |
| `execution_source` | Object with exact `mode: "containing_commit"`, required runtime binding name `execution_source_sha`, and no embedded SHA value. Admission resolves the exact containing commit as described below, avoiding a self-referential Git hash while still binding the exact SHA through the plan contract. |
| `lanes` | Non-empty array of lane objects described below. |
| `waves` | Non-empty ordered array of objects with unique `id` and non-empty `lane_ids`; every lane appears in exactly one wave. |
| `integration_order` | Array containing every lane ID exactly once in deterministic integration order, with every dependency before its dependents. |
| `integration_seams` | Array of repository-relative path patterns explicitly writable by late integration correction. No pattern may equal, contain, or overlap `pipelines/PLAN_SLUG/**`. |
| `verifier_execution_envelope` | Shared immutable `VerifierExecutionEnvelope` contract defined below, including checked-in implementation path/hash, canonical HEAD/status commands, output-root policy, evidence schema, token mapping, and `definition_sha256`. |
| `aggregate_verifier` | Aggregate-verifier contract defined below. |
| `attractor_runner_argv_prefix` | Required immutable non-empty `list[str]`. The only permitted exact forms are `["/absolute/path/to/attractor"]` or `["/absolute/path/to/python", "-m", "amplifier_module_pipeline_runner.cli"]`. PATH lookup, `/usr/bin/env`, relative executables, wrapper shell strings, and extra prefix tokens are forbidden. |
| `attractor_runner_identity` | Object binding the prefix's canonical JSON SHA-256, executable realpath/hash, exact module name, module-source realpath/hash, expected `doctor` contract, and required `run` flags. |
| `parent_runner_invocation` | Object with exact schema `goal-plan.parent-runner-invocation-definition/v2` binding the parent to the same runner prefix/identity and compiled `provider`; symbolic `os_cwd_policy: "target_repo"`; literal `runner_cwd_arg: "."`; exact parent DOT path `pipelines/PLAN_SLUG/PLAN_SLUG.dot`; `parent_dot_hash_policy: "execution_source_blob_and_compiled_manifest"`; exact parent logs-root policy `state_root/parent-attractor-run`; required runtime-bundle hash and trusted-runtime binding path/hash inputs; canonical Linux process-identity policy; immutable evidence schema `goal-plan.parent-runner-invocation/v2`; and `definition_sha256`. It embeds no parent-DOT digest, avoiding a `plan_sha256`/parent-DOT hash cycle; admission derives the expected digest from `execution_source_sha` and the compiled-source manifest. |
| `trusted_runtime_definition` | Object with exact schema `goal-plan.trusted-runtime-definition/v1`; repository-relative runtime and supervisor source paths, Git blob IDs, modes, lengths, and SHA-256 values expected at `execution_source_sha`; canonical `runtime_bundle_hash` derivation; exact absolute `trusted_git_argv_prefix` and `trusted_interpreter_argv_prefix`; executable/interpreter realpaths, file hashes, and required permission policies; closed Git `rev-parse`/`cat-file blob` materialization suffixes; external directory/binding paths; atomic write/fsync/non-writable/reread rules; trusted binding schema; exact runtime and supervisor suffix schemas; and `definition_sha256`. PATH lookup, `/usr/bin/env`, relative executables/scripts, `-m`, shell strings, wrappers with unbound targets, and extra prefix tokens are forbidden. |
| `trusted_runtime_binding_policy` | Object requiring exact external path `state_root/trusted-runtime/<runtime-bundle-hash>/trusted-runtime-binding.json`, binding schema `goal-plan.trusted-runtime-binding/v1`, immutable exact `trusted_runtime_argv_prefix` and `trusted_supervisor_argv_prefix`, per-invocation validation policy, no in-run replacement/rotation policy, deterministic prelaunch/recovery rehydration policy, safety-critical command allowlist, separately validated supervisor-only termination exception, and failure token/evidence mapping. |
| `provider` | Non-empty compiled provider ID. Every parent-spawned lane, correction, and delivery runner argv contains exact `--provider <provider>`; the value is immutable across restart/resume. |
| `integration_correction_child` | Immutable child-pipeline path/hash, exact prefix/provider/argv contract, `integration_worktree` CWD policy, positive `max_child_seconds`, result schema, and process-supervision contract for bounded integration correction. |
| `delivery_child` | Required only for `delivery_mode: "pr"`; immutable adapted `deliver_pr.dot` path/hash, exact prefix/provider/argv contract, `delivery_worktree` CWD policy, positive `max_child_seconds`, external-state policy, delivery-result schema, and process-supervision contract. Forbidden for `delivery_mode: "none"`. |
| `pre_terminal_cleanup` | Object binding the external trusted-runtime definition/binding hashes, exact `trusted_runtime_argv_prefix + pre-terminal-cleanup` argv schemas, fresh trusted-runtime/parent-runner/target-source/compiled-source gate policy, explicit cleanup-record fields `trusted_runtime_binding_verdict`, `parent_binding_verdict`, and `mutation_authority`, bounded identity-safe process-reconciliation policy, authority-scoped run-owned-worktree lifecycle rules including `PRESERVED_RESIDUAL`, required gate-evidence hashes, permitted/attempted/skipped action records, unresolved-resource evidence, cleanup-verdict/final-status mapping, evidence schema `goal-plan.pre-terminal-cleanup/v2`, token mapping, and `definition_sha256`. It forbids execution of the target-repository runtime copy. |
| `engine_step_budget` | Object with exact positive integers `poll_wait_seconds: 30` and `engine_step_multiplier: 50`; compiled parent node/step totals; and, for every lane, correction, and delivery branch, `branch_nonpoll_steps`, `branch_node_count`, and `max_poll_cycles`. |
| `global_budgets` | Object with positive integer `max_total_attempts` for verification-bearing adaptive attempts only, positive integer `max_process_launches` for supervisor starts/restarts, positive integer `max_integration_corrections` for supervised correction-child launches, positive integer `max_pipeline_seconds`, exact ledger schema `goal-plan.run-budget/v3`, locked trusted-runtime binding identity, locking policy `fcntl_flock_exclusive`, clock policy `linux_clock_boottime`, correction-reservation state contract, and budget-ledger implementation hash. |
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

#### Parent runner target-repository binding

The parent invocation is repository-bound before the parent CLI starts. The
launcher canonicalizes the requested `target_repo`, requires it to be the
target Git top-level, changes its own OS CWD to that realpath, and only then
`execve`s the exact immutable `attractor_runner_argv_prefix` plus the closed
parent argv. The resulting parent Attractor process therefore starts with:

```text
realpath(/proc/self/cwd) == canonical_target_repo
realpath(resolve_runner_cwd("--cwd", ".")) == canonical_target_repo
realpath(resolve_dot_operand("pipelines/PLAN_SLUG/PLAN_SLUG.dot"))
  == canonical_target_repo/pipelines/PLAN_SLUG/PLAN_SLUG.dot
```

The first admission node re-observes all three equalities before any repository,
Git-common-directory, ref, branch, worktree, `worktree_root`, or
`delivery_state_root` mutation. It hashes the invoked parent DOT's exact bytes,
requires those bytes to equal
`execution_source_sha:pipelines/PLAN_SLUG/PLAN_SLUG.dot`, and requires the same
path/mode/length/SHA-256 tuple in
`compiled-source-manifest.json`. A symlink alias, different current directory,
different runner `--cwd` resolution, alternate DOT copy, wrong path spelling,
or byte/hash mismatch is `INFRA_FAILURE`. That parent process may write the
failure evidence only below external `state_root`; it performs no repository or
worktree mutation.

Every initial start and resume writes a new immutable, atomically-created
`state_root/admission/parent-runner-invocations/NNNN.json` record with schema
`goal-plan.parent-runner-invocation/v2`. The record contains:

- the exact parent `attractor_runner_argv_prefix`, prefix hash, runner
  executable/module/source identity, and compiled provider;
- the complete parent argv and its canonical hash;
- literal parent `--cwd .`, its runner-resolved realpath, and the observed OS
  CWD from `/proc/self/cwd`;
- canonical `target_repo`;
- repository-relative and absolute parent DOT paths, exact observed DOT
  SHA-256, execution-source blob SHA-256, and compiled-manifest entry/hash;
- exact `execution_source_sha`;
- exact `runtime_bundle_hash`, external `trusted_runtime_binding_path`, binding
  SHA-256, and trusted runtime/supervisor prefix SHA-256 values;
- exact absolute parent `--logs-root`, which must equal
  `state_root/parent-attractor-run`;
- the canonical Linux parent process identity, including boot ID, PID,
  starttime ticks, executable realpath, cmdline hash, PGID, and process CWD; and
- invocation ordinal, prior-invocation record hash on resume, creation
  boottime, and the record's canonical SHA-256.

The record is append-only and never rewritten. A resume may have a new parent
process identity and ordinal, but every static binding, CWD equality, DOT
path/hash, logs root, provider, prefix, target repository, and
`execution_source_sha`, runtime-bundle hash, and trusted-runtime binding must
match the compiled plan and durable run state before reconciliation can mutate
anything. A mismatch is terminal infrastructure failure for that invocation and
authorizes no repository mutation.

Each `lanes` entry contains:

| Field | Type and invariant |
|---|---|
| `id` | Unique lane-ID slug. |
| `origins` | Non-empty array of requirement identifiers or text. |
| `goal` | Non-empty, checkable end-state string. |
| `scope_outs` | String array. |
| `owned_paths` | Non-empty array of repository-relative path patterns. No pattern may equal, contain, or overlap `pipelines/PLAN_SLUG/**`. |
| `dependencies` | Array of lane IDs; references must exist and form an acyclic graph. |
| `verifier` | Object with exactly one of non-empty argv, or checked-in `script_path` plus `script_sha256`; exact symbolic `cwd_policies: ["lane_worktree", "candidate_verification_worktree", "integration_worktree"]`; positive integer `timeout_seconds`; `write_policy: "read_only"`; mandatory `--output-root {verifier_output_root}` argv interface and required containment environment; evidence schema version `goal-plan.lane-verifier/v1`; exit/token mapping; `envelope_definition_sha256`; and `definition_sha256`. |
| `review_criteria` | Array of qualitative criterion objects, or an empty array when no lane review is required. |
| `child_pipeline` | Object with repository-relative `dot_path`, exact `dot_sha256`, exact executable identity and argv/parameter contract defined below, symbolic `cwd_policy: "lane_worktree"`, expected evidence schema `goal-plan.lane-result/v2`, and a hash binding those immutable values. |
| `budgets` | Object with positive integer `max_attempts` for local verification-bearing adaptive attempts and positive integer `max_child_seconds`. Process launches are not attempts. |
| `process_supervision` | Object with exact `schema_version: "goal-plan.process-supervision/v4"`, `platform: "linux"`, `mode: "per_child_reaper"`, exact external `trusted_supervisor_argv_prefix` and prefix hash from the immutable trusted-runtime binding, bound supervisor/interpreter/runtime identity, per-invocation binding validation, exact positive integer `poll_wait_seconds: 30`, `pre_ledger_reconciliation_timeout_seconds`, and `term_grace_seconds`; canonical supervisor/child procfs identity requirements; deterministic intent/ledger/ack/result paths; exact closed suffixes for self-check/run/poll/terminate/reconcile; control-client schemas/tokens; and supervisor-definition hash. |

The composition layer owns decomposition, collision analysis, all typed values
above, and plan approval or explicit preapproval. It writes `plan.json`
canonically and computes `plan_sha256` over the exact UTF-8 bytes of that file.

The child launch command is an exact argv-array template, never a freeform shell
string. The parent mints:

```text
process_run_id = PLAN_ID/RUN_ID/PROCESS_KIND/PROCESS_ID/PROCESS_LAUNCH
```

`PROCESS_KIND` is exactly `lane`, `correction`, or `delivery`;
`PROCESS_ID` is the validated lane/correction/delivery ID; and
`PROCESS_LAUNCH` is the positive decimal process-launch ordinal. This is the
durable process-run identifier. It is intentionally independent from local
adaptive-attempt numbers. Individual child box-session IDs are optional
observability and never identity or completion evidence.

After resolving typed parameters, argv has exactly this order:

```text
<each token of attractor_runner_argv_prefix>
run
<repo-relative-child-dot>
--provider
<compiled-provider>
--cwd
.
--logs-root
<absolute state_root/lanes/<lane-id>/runs/<process-launch>/attractor-run>
--on-human-gate
fail
--param lane_id=<lane-id>
--param process_run_id=<plan-id>/<run-id>/lane/<lane-id>/<process-launch>
--param lane_state_root=<absolute state_root/lanes/<lane-id>>
--param lane_result_path=<absolute lane-attempt-root/lane-result.json>
--param lane_feedback_path=<absolute lane-state-root/feedback/current.md>
--param lane_attempt_root=<absolute state_root/lanes/<lane-id>/runs/<process-launch>>
--param lane_contract_snapshot_path=<absolute lane-state-root/contract.json>
--param run_budget_ledger_path=<absolute state_root/budgets/run-wide.json>
--param run_budget_lock_path=<absolute state_root/budgets/run-wide.lock>
--param candidate_branch=<validated lane branch name>
--param product_base_sha=<full product base SHA>
--param execution_source_sha=<full execution source SHA>
--param runtime_bundle_hash=<full trusted runtime bundle hash>
--param trusted_runtime_binding_path=<absolute trusted-runtime-binding.json>
--param trusted_runtime_argv_prefix_sha256=<full external runtime prefix hash>
--param trusted_supervisor_argv_prefix_sha256=<full external supervisor prefix hash>
--param provider=<compiled-provider>
--param attractor_runner_argv_prefix_sha256=<full prefix hash>
--param lane_verifier_definition_sha256=<full verifier contract hash>
--param ownership_contract_sha256=<full ownership contract hash>
```

The child DOT operand is repository-relative, contains no `..`, and resolves
under `pipelines/PLAN_SLUG/` in the lane worktree. `--cwd` is the literal token
`.`. `candidate_branch`, IDs, and SHA/hash params are typed strings with the
validation stated above. `--provider` is always explicit and equals the
immutable compiled `provider`; `--on-human-gate fail` prevents an unattended
child from inventing approval. `--logs-root` and every path-valued `--param` are
absolute, `realpath`-canonicalized, and must resolve beneath that lane's
run-scoped `state_root/lanes/<lane-id>/`, except the two exact shared budget
paths beneath `state_root/budgets/` and the one exact immutable
`trusted_runtime_binding_path` beneath
`state_root/trusted-runtime/<runtime-bundle-hash>/`; none may resolve beneath
immutable source.
No additional child parameter is permitted unless a new compiled-plan revision
adds it to this ordered schema and changes the launch-contract hash.

The launch environment is also closed and hashed. The plan declares the exact
allowed environment-key set. The ledger records non-secret values directly and
sensitive values only as `sha256(value)`; a canonical environment hash covers
the complete key set and value/value-hash representation. The immutable
launch-contract hash covers the exact runner-prefix tokens/hash, executable and
module/source identity, compiled provider, ordered argv template, typed
parameter schema, environment policy, child DOT hash, symbolic `lane_worktree`
CWD policy, shared budget-ledger paths, trusted-runtime binding/bundle/prefix
hashes, and expected lane-result schema.

At launch, the parent records the prefix hash, resolved executable and module
source realpaths/hashes, provider, exact argv, environment hash, lane-worktree
realpath, `process_run_id`, trusted-runtime binding path/hash, runtime-bundle
hash, and a `launch_command_sha256` over their canonical serialization. Plan/DOT
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
- `max_total_attempts` as adaptive verifier-bearing work and
  `max_process_launches` as the separate supervisor-start/restart ceiling;
- exact `poll_wait_seconds="30"`, `engine_step_multiplier="50"`, every
  branch's compiled non-poll/node/poll-cycle values, and parent total-step
  bound;
- the literal `product_base_sha` and the `execution_source_sha`
  containing-commit binding contract;
- every child DOT path/hash, launch-command contract, symbolic worktree-CWD
  policy, exact ordered parameter schema, expected child-evidence schema, and
  Linux process-supervision policy;
- exact `attractor_runner_argv_prefix` hash/module/source identity and compiled
  `provider`;
- the parent-runner invocation definition hash, symbolic target-repository CWD
  policy, literal `--cwd .`, exact parent DOT path and
  execution-source/compiled-manifest hash policy, parent logs-root policy, and
  parent invocation evidence schema;
- trusted-runtime definition/binding schema and hashes, runtime-bundle-hash
  derivation, exact source path/blob/mode/length/hash pairs, compile-bound
  Git/interpreter prefixes and identities, external path/permission/hash policy,
  and first-admission/rehydration contract;
- exact external `trusted_runtime_argv_prefix` and
  `trusted_supervisor_argv_prefix` hashes, executable/interpreter/script
  identities, CLI/schema versions, environment schema, self-check contract,
  every closed safety-critical subcommand suffix, and parent tool-command
  external-only policy;
- the shared verifier-envelope definition hash, canonical commands, and
  read-only/external-output policies;
- the aggregate-verifier definition hash;
- approval mode/transport requirements, delivery mode, and external
  `delivery_state_root` policy; and
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

Admission runs before approval and before any repository/process/worktree
mutation. It has one launcher prelude followed by the parent graph, and the
combined sequence is the first green admission:

1. The launcher binds `canonical_target_repo`, canonical external `state_root`,
   exact parent DOT path, adjacent `plan.json`, parent runner prefix/provider/
   logs-root contract, and the caller-supplied full `execution_source_sha`.
2. Without executing repository code, it recomputes `plan_sha256`,
   schema-validates `plan.json`, proves the selected target-repository identity,
   resolves the containing execution-source commit, walks its complete compiled
   pipeline tree, and constructs/persists the canonical external
   `compiled-source-manifest.json`.
3. It hashes the checked-out parent DOT and both checked-out runtime scripts,
   requires exact execution-source blob and compiled-manifest equality, and
   validates the compile-bound absolute Git/interpreter prefixes and
   executable realpaths/hashes/permissions without PATH, `/usr/bin/env`, shell
   lookup, or relative-path resolution.
4. It extracts exact runtime/supervisor Git blobs, materializes/seals/rereads the
   external trusted-runtime bundle, atomically writes the complete versioned
   binding and command evidence, and derives exact `runtime_bundle_hash`,
   `trusted_runtime_binding_path`, `trusted_runtime_argv_prefix`, and
   `trusted_supervisor_argv_prefix`. No extracted code runs before this entire
   step is green.
5. The launcher changes its OS CWD to `canonical_target_repo` and `execve`s the
   exact parent Attractor argv, including immutable runtime-bundle/binding
   parameters. The first parent safety command uses only
   `trusted_runtime_argv_prefix`, validates that external binding again, then
   requires `/proc/self/cwd`, literal runner `--cwd .`, canonical target repo,
   exact parent-DOT realpath, parent prefix/identity/provider/argv/process/logs
   root, and launcher evidence to agree.
6. The external trusted runtime independently recomputes the plan/DOT/
   execution-source/compiled-manifest relationships and parses the static DOT
   for exact lane IDs, waves, dependency edges, integration order, budgets,
   verifier hashes, both source-SHA contracts, child launch/monitor nodes,
   ordered argv/params, correction expansion, approval transport, delivery
   policy, trusted-runtime definition/binding policy, and every safety-critical
   external prefix-plus-suffix tool command.
7. It validates the child runner without PATH lookup: exact prefix form/hash,
   executable/module/source realpaths/hashes, successful `<prefix> doctor`,
   required `run --help` flags, compiled provider support, and credential.
8. It runs non-mutating external
   `<trusted-runtime-prefix> self-check --format json` and
   `<trusted-supervisor-prefix> self-check --format json`; both report exact
   CLI, schema, suffix, permission, and binding support.
9. It validates poll/branch/parent engine-step arithmetic, external roots,
   approval mode/transport, environment schemas, and every no-mutation
   precondition.
10. It atomically finalizes admission/render/tool/materialization evidence under
    external `state_root` and writes the immutable parent-runner invocation
    record referencing the compiled-source manifest and exact trusted-runtime
    binding path/hash.

No step in this sequence executes either target-repository Python script.

For the Python-module prefix, the absolute interpreter runs a deterministic
`importlib.util.find_spec("amplifier_module_pipeline_runner.cli")` probe and the
preflight records/rechecks the resolved module source bytes. For the absolute
console prefix, preflight hashes the console file, resolves its interpreter and
declared console entry point without PATH search, and performs the same module
probe in that interpreter. The observed executable/module/source identities
must equal `attractor_runner_identity`; a console wrapper whose target cannot be
resolved deterministically is rejected.

The target-repository runtime and supervisor files are source observations
during this first admission; they are never executed by the parent. The
external trusted-runtime copies are the only Python forms permitted to
self-check or execute. Each self-check is read-only: it writes no file, launches
no child, and emits one canonical JSON object on stdout. Any Git/interpreter
prefix, executable identity, source blob, checked-out byte, materialized byte,
permission, environment-schema, CLI-version, supported-schema, or
subcommand-signature mismatch fails admission before approval or mutation.

A parent CWD/`--cwd`/DOT-realpath mismatch, parent DOT byte/hash mismatch,
unbound parent prefix/provider/process/logs-root value, missing file, schema
failure, or graph/plan mismatch aborts admission as `INFRA_FAILURE`. The failing
parent invocation writes only immutable external evidence and performs no
repository mutation. Admission reads `plan.json` only to audit the
already-static program; it never dispatches work from the JSON.

#### Runtime invocation interface

Each compiled family member accepts only these runtime inputs:

| Input | Type and rule |
|---|---|
| `target_repo` | Required absolute path to the Git working repository. Before the parent CLI starts, the launcher must change OS CWD to its canonical realpath. Admission must prove that same realpath is the Git top-level, equals `/proc/self/cwd`, equals the runner's literal `--cwd .` resolution, and satisfies the `remote` or `history_anchor` identity policy from `plan.json.target_repo`. |
| `execution_source_sha` | Required full Git commit SHA. It must be the containing commit of the exact invoked parent DOT and adjacent `plan.json`, contain every immutable compiled source file, descend from `product_base_sha`, and satisfy the complete byte-manifest gate. The invoked DOT realpath and observed bytes/hash must equal the exact parent-DOT path/blob and compiled-manifest entry for this commit. |
| `run_id` | Required slug unique within the plan's run directory. |
| `state_root` | Effective value is a required absolute external path. The caller may omit it only to derive the canonical external user-state default defined below; it is never inside the target repository. |
| `runtime_bundle_hash` | Required launcher-derived full SHA-256 from `plan.json.trusted_runtime_definition` and exact `execution_source_sha`. It is not user-selectable and must equal both the trusted-runtime directory name and binding field. |
| `trusted_runtime_binding_path` | Required launcher-derived canonical absolute path equal to `state_root/trusted-runtime/<runtime-bundle-hash>/trusted-runtime-binding.json`. It is not a general path override; any other spelling, symlink, or location is rejected before the parent starts. |
| `worktree_root` | Required absolute external path dedicated to this run's lane, integration, candidate-verification, and delivery worktrees. It is separate from `state_root`. |
| `delivery_state_root` | Required absolute external path when `delivery_mode` is `pr`; forbidden when delivery is `none`. It contains delivery child logs, checkpoints, events, ledgers, and evidence and is separate from `state_root`, `worktree_root`, and every Git repository/worktree. |
| `approval_mode` | Required enum `required` or `preapproved`; must equal the compiled plan value. |
| `human_gate_transport` | Required enum `none` or `console`. `preapproved` requires `none`; `required` requires `console`, exact parent runner flag `--on-human-gate console`, and admission evidence for an attached readable/writable standalone TTY. |
| `delivery_mode` | Required enum `none` or `pr`; must equal the compiled plan value. |
| `github_repo` | `owner/repo` string required only when `delivery_mode` is `pr`; forbidden otherwise. |

The canonical unattended smoke uses the absolute-console prefix form. Its
launcher first canonicalizes `target_repo`, changes CWD before `exec`, and then
uses this closed parent argv shape (paths and SHAs shown symbolically):

```text
cd -- <canonical-absolute-target-repo>
exec /absolute/path/to/attractor
run
pipelines/goal_plan_smoke/goal_plan_smoke.dot
--provider
anthropic
--cwd
.
--logs-root
<absolute-state-root>/parent-attractor-run
--on-human-gate
fail
--param target_repo=<canonical-absolute-target-repo>
--param execution_source_sha=<full-containing-sha>
--param run_id=<run-id>
--param state_root=<absolute-state-root>
--param runtime_bundle_hash=<full-trusted-runtime-bundle-hash>
--param trusted_runtime_binding_path=<absolute-state-root>/trusted-runtime/<runtime-bundle-hash>/trusted-runtime-binding.json
--param worktree_root=<absolute-worktree-root>
--param delivery_state_root=<absolute-delivery-state-root>
--param approval_mode=preapproved
--param human_gate_transport=none
--param delivery_mode=pr
--param github_repo=<owner/repo>
```

`cd`/`exec` above describes the required pre-start sequence; the parent process
argv begins with `/absolute/path/to/attractor`, contains no shell token, and its
observed `/proc/self/cwd` is already the canonical target repository. The
launcher must reject a `target_repo` whose canonical realpath differs from the
directory it changed into. Admission then requires the literal `--cwd .` to
resolve to that same realpath, requires the DOT operand to resolve to exact
`<target_repo>/pipelines/goal_plan_smoke/goal_plan_smoke.dot`, and binds the
observed DOT hash to both `execution_source_sha` and the compiled-source
manifest before mutation.

The equally valid Python-module form retains the same `cd`/`exec` sequence and
replaces the console executable prefix after `exec` with
`/absolute/path/to/python -m amplifier_module_pipeline_runner.cli`; all
remaining parent argv tokens and their order are unchanged. An interactive
required-approval invocation changes exactly
`--on-human-gate fail` to `--on-human-gate console`,
`approval_mode=preapproved` to `approval_mode=required`, and
`human_gate_transport=none` to `human_gate_transport=console`. Admission also
requires the standalone parent process to prove that stdin is an attached TTY
and that `/dev/tty` is openable for both input and output. Hosted or unattended
headless execution cannot use `approval_mode=required`. The compiled provider is
not a runtime override: any other `--provider`, omitted explicit provider, or
provider change on resume fails admission.

The parent `--logs-root` is not a caller-selected alternate location. It must
realpath to exact `state_root/parent-attractor-run`. Before approval or
preapproval can advance, the parent persists the immutable invocation record
containing prefix/provider/cwd/DOT/hash, OS CWD, target repository,
`execution_source_sha`, process identity, logs root, runtime-bundle hash, and
trusted-runtime binding path/hash. A missing or inconsistent record is
`INFRA_FAILURE` and the parent performs no repository mutation.

If `state_root` is omitted, preflight derives:

```text
$XDG_STATE_HOME/amplifier/goal-plan/REPO_IDENTITY/PLAN_ID/RUN_ID
```

When `XDG_STATE_HOME` is unset or empty, the only fallback is:

```text
$HOME/.local/state/amplifier/goal-plan/REPO_IDENTITY/PLAN_ID/RUN_ID
```

`REPO_IDENTITY` is the stable SHA-256 identity token derived by admission, not a
raw remote or filesystem path. If neither an absolute `XDG_STATE_HOME` nor an
absolute `HOME` is available, admission fails; there is no repository-relative
or current-directory fallback.

Admission resolves every effective root through its nearest existing parent and
rejects symlink escapes. `state_root` and, when present,
`delivery_state_root` are absolute, external, pairwise disjoint, and neither
equal to, ancestors of, nor descendants of the target repository root, Git
common directory, compiled-source directory, any registered Git worktree, or
`worktree_root`.

`worktree_root` has phase-specific safety rules:

1. **Before approval or any repository mutation**, it must be absent or an empty
   directory dedicated to this run. It must not equal, contain, or be contained
   by `state_root`, `delivery_state_root`, the target repository root, the Git
   common directory, the compiled-source directory, or any pre-existing or
   foreign registered worktree. Its nearest existing parent must not carry a
   different run identity. Admission snapshots the complete directory entry set
   and `git worktree list --porcelain` before approval.
2. **After approval**, it may be an ancestor only of exact worktrees created by
   this run and recorded atomically in
   `state_root/run-owned-worktrees.json`. The registry uses schema
   `goal-plan.run-owned-worktrees/v1`; every entry records exact `kind`
   (`lane`, `integration`, `candidate`, or `delivery`), lane/process ID,
   canonical path, expected branch name or null, detached boolean, expected full
   HEAD SHA, target Git common directory, worktree-creation
   argv/exit/stdout/stderr evidence, creation boottime, and lifecycle state
   (`CREATING`, `ACTIVE`, `REMOVING`, `REMOVED`, or
   `PRESERVED_RESIDUAL`). `CREATING` is durable before `git worktree add`;
   `ACTIVE` is written only after exact path, registration, common directory,
   HEAD SHA, and branch/detached state are independently proved. Any intentional
   branch advance atomically updates expected HEAD with the command and old/new
   SHA evidence before later use.
3. At every post-approval gate, any unrecorded filesystem entry or foreign Git
   worktree beneath `worktree_root`, or any non-`REMOVED` recorded run-owned
   worktree outside `worktree_root`, is `INFRA_FAILURE`. Ordinary parent
   directories are not exempt: each immediate child of `worktree_root` is one
   exact recorded worktree root, and every deeper path must be contained by
   exactly one such recorded worktree. The canonical flat names are
   `lane-LANE_ID`, `integration`, `candidate-LANE_ID-SHA-ATTEMPT`, and
   `delivery-ATTEMPT`.

The lifecycle enum is exactly `CREATING`, `ACTIVE`, `REMOVING`, `REMOVED`, or
`PRESERVED_RESIDUAL`. `PRESERVED_RESIDUAL` is legal only during
`PreTerminalCleanup` for intended `RESIDUALS_READY`, only for an exact worktree
named in the durable residual-preservation manifest, and only after proving its
path, Git registration/common directory, branch/detached state, expected HEAD,
current dirtiness, residual ID, evidence paths, and identity-safe recovery
commands. It is intentional terminal custody, not an incomplete cleanup. No
lane, candidate, delivery, or integration worktree may enter that state merely
because removal is difficult or the path is dirty.

The post-approval exception is therefore a closed allowlist for this run's
worktrees, not a relaxation for arbitrary descendants. Root safety never
reapplies the pre-approval blanket prohibition to the run-owned worktrees it has
just created.

Lifecycle recovery is exact and mutation-authority-gated. Every cleanup
recovery or retry first validates the external trusted-runtime binding, enters
through exact `trusted_runtime_argv_prefix`, and reruns the current
parent-runner, target/source-identity, and compiled-source gates; it may never
infer authority from a prior cleanup record or reuse a prior
`mutation_authority: "FULL"`. Ordinary lifecycle reconciliation may mutate Git
only after the same current trusted-runtime plus repository/source gates grant
`FULL`.
A `CREATING` entry with no path/registration may
retry the same `git worktree add` only when durable command evidence proves add
never began; if the exact path and registration exist, recovery must validate
the expected common directory, HEAD, and branch/detached state before marking
`ACTIVE`. A `REMOVING` entry may become `REMOVED` only after path and
registration are both absent; otherwise recovery retries non-force removal only
for that exact clean recorded worktree. Partial, conflicting, dirty, or foreign
state is `INFRA_FAILURE`. A `PRESERVED_RESIDUAL` entry is accepted only for a
durably finalized `RESIDUALS_READY` run or an in-progress
`PreTerminalCleanup` whose residual manifest names that exact entry. Recovery
revalidates it without changing or removing it unless an operator later runs
the recorded recovery command as a separate, explicit action.

Preflight rejects non-Linux hosts, missing or unreadable required procfs
identity files, a parent OS CWD/runner `--cwd .`/canonical `target_repo`
mismatch, a parent DOT realpath/blob/manifest mismatch, incomplete parent
invocation evidence, relative or unsafe roots, mode/approval-transport
mismatches,
`required` approval without attached standalone console/TTY evidence,
`required` approval in unattended or hosted headless execution, failed
remote/history-anchor identity proofs, reused `run_id` with incompatible state,
an invalid child-runner or trusted-runtime/supervisor binding, identity,
self-check, command, permission, or materialization preflight, an invalid
provider/credential/doctor/flag preflight, an invalid
`product_base_sha`, or an `execution_source_sha` that does not contain the exact
compiled program being invoked. A `preapproved` standalone run is explicitly
valid in unattended headless execution.

Composition owns the immutable files under `pipelines/PLAN_SLUG/`. Runtime
reads but never rewrites them. All ordinary runtime-created filesystem state and
evidence live beneath external `state_root`; delivery-generated state lives
beneath external `delivery_state_root`; all Git worktrees live beneath external
`worktree_root`. Product changes leave worktrees only as explicit Git commits
and integrations.

Before approval, admission may create and atomically write only beneath
external `state_root`. It reads Git objects, refs, repository identity, and
compiled source without mutating them; compiled-source manifests, rendered-plan
evidence, approval packets, and admission logs are persisted externally.
`target_repo`, Git refs/branches, the Git common directory, registered
worktrees, `worktree_root`, and `delivery_state_root` remain byte- and
state-untouched.

Only after approval or explicit preapproval may the parent create
`worktree_root` or `delivery_state_root`, create branches/worktrees, mutate
refs, or launch a process.
Before each `git worktree add`, it writes the exact `CREATING` entry to
`run-owned-worktrees.json`; after creation it proves and records `ACTIVE` as
specified above. The integration worktree and every initially prepared lane
branch are then created at exact `execution_source_sha`. Before a later dependency wave
launches, its lane branch is advanced only to the current parent-verified
integration HEAD, which must descend from `execution_source_sha`; therefore
every lane always contains the compiled child DOT and supervisor. Lane-owned
candidate diffs and integration mutations are measured from
`execution_source_sha`, while final product reporting separately identifies the
known compiled-plan delta `product_base_sha..execution_source_sha` and the
lane-produced delta `execution_source_sha..final_integrated_head`.

The runtime graph is responsible for:

- deterministic preflight;
- isolated worktree preparation;
- explicit dependency-wave execution;
- supervised launch and monitoring of one headless child Attractor process per
  lane;
- supervised integration-correction and delivery child processes;
- parent-side evidence checks;
- sequential integration and rollback of failed candidates;
- aggregate and coherence gates;
- intended terminal classification and final cleanup-chosen status;
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
`plan.json`, parent DOT, lane/correction child DOTs, both runtime/supervisor
source files, verifier definitions, delivery subgraph when present, and every
other compiled-directory byte. Its
`manifest_sha256` covers the canonical JSON excluding only that hash field.
The manifest itself lives under `state_root`, so it does not create a
self-hashing source cycle.

The parent also runs a deterministic `ParentRunnerBindingGate`. It validates
the current `/proc/self/cwd`, runner-resolved literal `--cwd .`, canonical
`target_repo`, exact invoked parent-DOT realpath, observed DOT SHA-256,
execution-source blob SHA-256, compiled-manifest entry/hash, parent
prefix/provider/argv, process identity, and parent logs root against the
immutable invocation record. It runs during admission, before the first
repository mutation, on every resume before reconciliation may mutate, before
every dependency-wave/correction/delivery mutation phase, and immediately
before `PreTerminalCleanup`. Every parent-executed `CompiledSourceGate` first
requires `TrustedRuntimeBindingGate` and this parent binding gate to pass, and
the gate command itself is invoked only through the external trusted runtime.

A parent-binding mismatch is `INFRA_FAILURE` and disables repository mutation
for that parent invocation. The same restriction applies when target/source
identity or compiled-source binding is red or unknown. When the external
trusted-runtime binding is still independently green, pre-terminal cleanup
records `mutation_authority: "EXTERNAL_ONLY"`: it may atomically close external
evidence and identity-safely reconcile or stop a supervisor/child process group
only when the full recorded procfs identity remains valid, but it may not alter
target-repository files, refs, branches, Git registrations, worktree paths, or
Git common-directory state. If the external trusted-runtime binding is red,
unknown, missing, or permission-mismatched, authority is `NONE`; no general
cleanup/finalizer action or signal is attempted.

The deterministic `CompiledSourceGate` compares both the complete path set and
every entry's mode, length, and bytes against the admission manifest. It emits
only `COMPILED_SOURCE:PASS` or `COMPILED_SOURCE:INFRA`. The gate runs:

1. at admission in the execution-source checkout;
2. against each lane worktree immediately after every child exit;
3. against the candidate commit before parent candidate verification;
4. against the integration worktree before and after every post-merge aggregate
   envelope, and after every `IntegrationCorrection`;
5. against every clean disposable delivery worktree before and after its child;
6. against all existing run worktrees during restart reconciliation;
7. against the integration worktree immediately before delivery eligibility;
   and
8. immediately before `PreTerminalCleanup`, together with a fresh
   `ParentRunnerBindingGate`.

Any missing, added, mode-changed, or byte-changed compiled-source entry is
`INFRA_FAILURE`. It never enters a lane, integration-correction, or verifier
retry loop. Composition additionally rejects any lane `owned_paths` or
`integration_seams` pattern that could match `pipelines/PLAN_SLUG/**`.

### External trusted-runtime bootstrap and binding

The target-repository copies of `goal_plan_runtime.py` and
`goal_plan_supervisor.py` are immutable compiled source, but they are not a
stable terminal safety root: the very source mismatch that needs cleanup could
make those paths unreadable, changed, or absent. The first green admission
therefore treats the checked-out files as data, not executables, and creates one
external trusted-runtime bundle before any repository, ref, worktree, process,
`worktree_root`, or `delivery_state_root` mutation.

The trusted-runtime bundle path is exactly:

```text
state_root/trusted-runtime/<runtime-bundle-hash>/
  goal_plan_runtime.py
  goal_plan_supervisor.py
  trusted-runtime-binding.json
```

`runtime-bundle-hash` is the SHA-256 of canonical JSON containing the trusted
runtime definition version, exact `execution_source_sha`, both
repository-relative source paths, Git blob IDs, Git modes, byte lengths, and
content SHA-256 values, plus the trusted Git and interpreter prefix tokens,
prefix hashes, executable realpaths, executable byte hashes, permission
policies, and closed runtime/supervisor suffix-schema hashes. It contains no
working-tree absolute path, so the same approved execution source and toolchain
produce the same bundle identity across worktrees.

#### First-admission materialization

The launcher performs the trusted-runtime portion of first admission before
starting any parent DOT command that can mutate the repository. It is the same
already-bound launching process that canonicalizes `target_repo`, changes CWD,
and starts the parent CLI; the checked-out runtime is never used to bootstrap
itself. It performs this exact sequence:

1. Validate the absolute `trusted_git_argv_prefix` and
   `trusted_interpreter_argv_prefix` from `plan.json`: each prefix, canonical
   JSON hash, executable realpath, exact executable bytes/hash, `lstat` type,
   owner/group/mode, and executable permission must match the compiled
   definition. The Git and interpreter executable must not be group- or
   world-writable. No PATH lookup, `/usr/bin/env`, shell command, relative
   executable, symlink operand, or module lookup is allowed.
2. With the exact absolute Git prefix and `shell=False`, run the two closed
   object queries for each source:

   ```text
   <trusted-git-prefix> --git-dir <canonical-git-common-dir> rev-parse --verify <execution_source_sha>:<repo-relative-source-path>
   <trusted-git-prefix> --git-dir <canonical-git-common-dir> cat-file blob <expected-blob-id>
   ```

   The first stdout must be the exact expected blob ID from
   `plan.json.trusted_runtime_definition`; the second stdout is the source byte
   stream. Extra/reordered arguments, another Git common directory, another
   object ID, text decoding/newline conversion, filters, checkout, archive, or
   working-tree reads are forbidden.
3. Independently open the two checked-out source paths with no symlink
   traversal, require regular files at the exact compiled paths, and compare
   Git mode, byte length, and SHA-256 with both the just-read Git blob and the
   corresponding `compiled-source-manifest.json` entry. This proves the current
   checkout is green, but those reads are not used as materialization input.
4. Create a unique sibling staging directory beneath
   `state_root/trusted-runtime/` with mode `0700`. For each blob, write the exact
   `cat-file blob` stdout bytes to a same-directory `O_CREAT|O_EXCL|O_NOFOLLOW`
   temporary file, fsync the file, atomically rename it to the fixed basename,
   fsync the staging directory, set mode `0444`, and reread/hash/length-verify
   the final file. No data byte is sourced from a later working-tree read.
5. Canonically write `trusted-runtime-binding.json` through the same
   create/fsync/atomic-rename/fsync sequence, set all three files to `0444`,
   set the staging directory to `0555`, fsync it, atomically install it at the
   exact bundle-hash directory with no-replace semantics, and fsync
   `state_root/trusted-runtime/`. An already-existing final directory is accepted
   only after complete binding/path/type/permission/hash validation; it is never
   overwritten in place.
6. Reread the installed binding and every installed file using
   `O_NOFOLLOW`, require the bundle directory and all three files to have no
   write bits, revalidate every realpath/mode/length/hash and both tool
   executable identities, then execute the two external non-mutating
   self-checks. Extracted code is never executed before every byte, path,
   permission, interpreter, and binding check passes.

Every Git command receives a closed environment and has bounded stderr/stdout
capture. Admission persists exact argv, cwd, environment hash, executable
realpath/hash, exit code, stderr path/hash, stdout byte length/hash, expected and
observed blob ID, destination path, fsync/rename/chmod observations, and final
reread hash as materialization command evidence. A command or durability check
that cannot be proved is `INFRA_FAILURE` before repository mutation.

#### `trusted-runtime-binding.json`

The binding uses exact schema `goal-plan.trusted-runtime-binding/v1` and contains:

| Field | Contract |
|---|---|
| `schema_version`, `created_at` | Exact schema and RFC 3339 UTC creation timestamp. |
| `execution_source_sha`, `runtime_bundle_hash`, `trusted_runtime_definition_sha256` | Exact admitted source and compiled definition identities. |
| `source_blobs` | Ordered runtime/supervisor entries with role, repository-relative source path, Git blob ID, Git mode, byte length, and SHA-256. |
| `external_files` | Ordered runtime/supervisor entries with fixed absolute path, `realpath`, `lstat` type/mode/uid/gid, byte length, and SHA-256. |
| `trusted_git_argv_prefix`, `trusted_git_identity` | Exact absolute prefix, prefix hash, executable path/realpath, byte hash, mode/uid/gid, and closed environment hash used for object extraction. |
| `trusted_interpreter_argv_prefix`, `trusted_interpreter_identity` | Exact absolute prefix, prefix hash, executable path/realpath, byte hash, mode/uid/gid, and executable-permission evidence. |
| `trusted_runtime_argv_prefix` | Exact immutable list `[<interpreter-realpath>, <external-absolute-goal_plan_runtime.py>]` and canonical prefix SHA-256. |
| `trusted_supervisor_argv_prefix` | Exact immutable list `[<interpreter-realpath>, <external-absolute-goal_plan_supervisor.py>]` and canonical prefix SHA-256. |
| `materialization_commands` | For every `rev-parse` and `cat-file blob`, the exact absolute argv, cwd, environment hash, executable identity, exit code, stderr evidence, stdout length/hash, expected/observed blob identity, and destination-file fsync/rename/chmod/reread evidence. |
| `binding_sha256` | SHA-256 of canonical JSON excluding only this field. |

The binding is append-never and replace-never for a run. Non-safety work has no
operation that changes its path, prefixes, hashes, permissions, or selected
interpreter. A different interpreter or source revision requires a different
runtime-bundle hash and a new run; it cannot rotate a live run's binding.

#### Per-invocation validation and safety command boundary

Before every safety-critical action, the caller validates the binding itself,
the fixed bundle directory, both runtime files, the Git and interpreter
executables, and the selected prefix. Validation requires exact absolute path
and realpath, regular-file/directory type, recorded mode/uid/gid, no write bit on
the bundle directory or its three files, interpreter/Git executable permission
policy, byte length/hash, canonical prefix hash, definition hash, binding hash,
and `execution_source_sha`. It opens files without symlink traversal and
rechecks after command completion when the action can mutate Git, process, or
terminal state.

The safety-critical set is closed: parent/trusted-runtime/target-source/
compiled-source binding gates; root and ownership gates; all Git, ref, branch,
worktree, candidate-envelope, delivery-envelope, integration, rollback, budget,
deadline, process-launch, process-poll, process-termination, process-reconcile,
attempt-reservation/classification, `PreTerminalCleanup`, durable terminal
finalizer, and recovery actions. Every such parent action is exact
`trusted_runtime_argv_prefix + <closed suffix>`; every supervisor start or
control action is exact
`trusted_supervisor_argv_prefix + <closed run|poll|terminate|reconcile suffix>`.
Child Attractor and verifier execution remain separately bound by their own
contracts, but only the external trusted runtime may authorize or launch them.

A missing, unreadable, changed, writable, path-drifted, permission-drifted, or
hash-mismatched binding/runtime/interpreter/Git executable is `INFRA`. It grants
`mutation_authority: "NONE"`, forbids Git/repository/worktree mutation, and
forbids signalling. The only exception is process-safe termination through an
exact external `trusted_supervisor_argv_prefix` whose interpreter, supervisor
file, prefix, launch contract, durable process identity, and source hash remain
independently valid against the already-durable process record; that narrow
exception may terminate only the matching fully procfs-identity-valid process
group and may not write a general cleanup/finalizer success record.

#### Deterministic prelaunch and recovery rehydration

Before a new parent launch or recovery graph begins, the launcher first validates
the external trusted-runtime binding from durable `state_root`; recovery does
this before opening or hashing any current target-repository runtime script. If
the exact bundle directory is absent, the launcher may perform one deterministic
rehydration from the durable approved plan snapshot and exact Git objects. It:

1. validates the compile-bound absolute Git/interpreter prefixes and hashes from
   the durable plan snapshot;
2. resolves both expected paths at exact `execution_source_sha` to the expected
   blob IDs through the closed absolute Git argv;
3. extracts both exact blobs with `cat-file blob` into a new staging directory;
4. verifies blob IDs, lengths, SHA-256 values, modes, tool identities, and
   runtime-bundle-hash before executing any extracted code;
5. recreates and seals the same versioned binding with the atomic/fsync/
   no-write/reread procedure; and
6. only after complete validation invokes the external self-check and starts
   recovery through `trusted_runtime_argv_prefix`.

Rehydration never reads source bytes from the current working copy, never
executes current working-copy runtime code, and never overwrites or repairs a
present-but-mismatching bundle. A present mismatch blocks action and requires
operator custody of the suspect external directory. If exact blob,
interpreter/Git executable identity, permissions, atomic durability, or final
binding cannot be proved, the launcher writes only its own external
infrastructure-blocked evidence, starts no recovery/cleanup/finalizer command,
performs no Git mutation, and does not claim cleanup or terminal-finalizer
completion.

#### Parent DOT tool-command contract

`trusted_runtime_binding_path` and `runtime_bundle_hash` are immutable parent
context values established by the launcher and revalidated by admission. The
parent DOT has no safety-critical `tool_command` whose executable operand is
beneath `target_repo`. Its initial safety node and every later safety node use
the exact ordered argv represented by:

```text
<each token of trusted_runtime_argv_prefix>
<closed-runtime-subcommand>
<closed ordered arguments for that node>
--trusted-runtime-binding <absolute trusted-runtime-binding.json>
```

Supervisor nodes use the corresponding exact
`trusted_supervisor_argv_prefix + closed suffix`. The generated DOT embeds the
trusted-runtime definition hash, runtime-bundle hash derivation, suffix-schema
hashes, and symbolic binding-path policy; admission resolves the exact external
tokens and proves each rendered tool command token-for-token before it can run.
No shell interpolation, PATH lookup, target-repository script operand, mutable
context override, environment-selected executable, or unrecognized argument is
permitted. A non-safety LLM/tool node cannot write the binding directory and
cannot contribute or replace an argv prefix.

The same rule applies inside lane, correction, and delivery child DOTs. Their
launcher params carry the exact runtime-bundle hash, binding path, and external
prefix hashes. `ReserveGlobalAttempt`, attempt classification, budget/deadline
control, ownership/source gates, commit/ref operations, delivery Git/remote
mutation, evidence finalization, and every other deterministic safety node
executes only as `trusted_runtime_argv_prefix + closed child suffix`; supervisor
control uses only `trusted_supervisor_argv_prefix`. Adaptive product work may
write within its approved worktree ownership, but it has no command that can
replace or rebind either trusted prefix.

### Top-level topology

```text
Launcher preflight
  -> validate or exact-blob rehydrate external trusted-runtime binding
  -> reject before parent start if Git/interpreter/blob/binding proof is red
Start
  -> Bind typed runtime inputs
  -> TrustedRuntimeBindingGate on external bundle before reading target scripts
  -> Require launcher-started OS CWD realpath == canonical target_repo
  -> ParentRunnerBindingGate:
       /proc/self/cwd == runner --cwd . == canonical target_repo
       invoked DOT == target_repo/pipelines/PLAN_SLUG/PLAN_SLUG.dot
       observed DOT hash == execution_source blob == compiled-manifest entry
  -> Resolve and validate external state_root + worktree_root
     + conditional delivery_state_root
  -> Admission: validate plan/graph/repo + bind product_base_sha/execution_source_sha
  -> Persist immutable parent argv/prefix/provider/cwd/DOT/hash/process/logs evidence
  -> Prove checked-out runtime/supervisor bytes == Git blobs == compiled manifest
  -> Materialize/verify/seal trusted runtime from exact Git blob bytes
  -> Persist immutable trusted-runtime-binding.json and command evidence
  -> Validate child runner prefix/module/source/doctor/flags + compiled provider credentials
  -> Validate external trusted runtime/supervisor prefixes, permissions, hashes,
     self-checks, and subcommands
  -> Validate poll/branch/parent engine-step arithmetic
  -> Persist manifest/render/admission evidence under external state_root only
  -> Reconcile durable state only after current parent invocation is fully bound
  -> Plan approval through attached standalone console (or verify explicit preapproval)
  -> Create worktree_root; mint flock-protected run-wide budget/deadline ledger
  -> Prepare integration + Wave 1 worktrees from execution_source_sha
  -> component fan-out
       -> reserve process launch(A) -> mint intent + launch contract(A)
            -> exact trusted supervisor prefix + run suffix -> Popen reaper(A) in own session -> require ack
            -> long-poll(A, --wait-seconds 30) loop
            -> require authoritative supervisor-result(A) -> classify terminal A
       -> reserve process launch(B) -> mint intent + launch contract(B)
            -> exact trusted supervisor prefix + run suffix -> Popen reaper(B) in own session -> require ack
            -> long-poll(B, --wait-seconds 30) loop
            -> require authoritative supervisor-result(B) -> classify terminal B
       -> missing ledger/ack -> reconcile intent via bounded /proc discovery
       -> vanished reaper without result -> terminate valid orphan child -> INFRA
       -> global deadline -> control clients terminate all active reapers/groups
            -> active lanes BUDGET(global_deadline)
            -> unstarted lanes BLOCKED-global-deadline
  -> tripleoctagon fan-in
  -> Collect supervisor results + child artifacts
       -> missing/invalid supervisor result = INFRA, never PASS
       -> real child exit nonzero/signal/timeout = non-candidate even if artifacts exist
  -> CompiledSourceGate on every exited lane worktree
  -> For each candidate: CompiledSourceGate on candidate commit
       -> create clean detached candidate_verification_worktree at exact candidate SHA
       -> VerifierExecutionEnvelope(candidate_lane, expected candidate SHA)
       -> after envelope postconditions: remove/reconcile detached worktree
  -> Enforce ownership
  -> Integrate passing commits one at a time
       -> VerifierExecutionEnvelope(aggregate_after_merge, expected merged HEAD)
       -> on failure: undo candidate merge, return evidence to owning lane
  -> Prepare next explicit dependency wave
  -> ...
  -> VerifierExecutionEnvelope(pre_coherence_aggregate, expected current HEAD)
  -> Fresh cross-lane coherence review at that exact HEAD
       -> ITERATE: ReserveCorrectionRound(ordinal) + reserve process launch atomically
            -> exact supervisor prefix + run suffix -> valid ack marks correction STARTED
            -> child ReserveGlobalAttempt -> adaptive correction -> verifier classification
            -> authoritative supervisor terminal consumes correction round
            -> CompiledSourceGate after correction
            -> VerifierExecutionEnvelope for each affected-closure lane
            -> VerifierExecutionEnvelope(affected_closure_aggregate, expected current HEAD)
            -> VerifierExecutionEnvelope(pre_coherence_aggregate, expected current HEAD)
            -> fresh coherence review at that same HEAD
       -> residual classification when no bounded correction remains
       -> PASS: freeze exact final HEAD
            -> VerifierExecutionEnvelope for every final-sweep lane at frozen HEAD
            -> red: IntegrationCorrection within integration budget
            -> all green: VerifierExecutionEnvelope(final_aggregate_after_sweep)
               at frozen HEAD
  -> CompiledSourceGate before delivery/intended-status classification
  -> Classify intended convergence result
       -> fresh coherence + final sweep + final-aggregate-after-sweep all green
          at exact final HEAD
            -> delivery disabled -> intended COMPLETE
            -> delivery enabled -> clean disposable final-HEAD delivery worktree
                 -> pre-HEAD/status/full-filesystem/source gates
                 -> reserve process launch -> supervised adapted deliver_pr.dot child
                    with all generated state under delivery_state_root
                 -> post-HEAD/status/full-filesystem/source gates
                 -> exact-head PR verification -> intended COMPLETE
                 -> unverifiable delivery -> intended INFRA_FAILURE
       -> residuals -> residual disposition gate
            -> name exact preserved residual worktrees -> intended RESIDUALS_READY
       -> untrustworthy substrate -> intended INFRA_FAILURE
       -> rejected/cancelled before mutation -> intended ABORTED
  -> Fresh CleanupAuthorityGate before terminal cleanup
       -> recompute TrustedRuntimeBindingGate + ParentRunnerBindingGate
          + target/source identity + CompiledSourceGate; hash current evidence
       -> all green: trusted_runtime_binding_verdict=PASS,
          parent_binding_verdict=PASS, mutation_authority=FULL
       -> trusted runtime green but any repository/source gate red/unknown:
          mutation_authority=EXTERNAL_ONLY
          + intended/final INFRA_FAILURE
       -> trusted runtime red/unknown: mutation_authority=NONE
          + infrastructure-blocked; no cleanup/finalizer completion claim
  -> exact trusted_runtime_argv_prefix + PreTerminalCleanup(intended status,
     current authority)
       -> both authorities may reconcile/stop only fully procfs-identity-valid
          child supervisors and process groups
       -> FULL: perform bounded identity-matched Git cleanup/preservation
          according to COMPLETE/RESIDUALS/ABORTED/INFRA policy
       -> EXTERNAL_ONLY: write external evidence, skip every Git/repository
          action, and retain all worktrees/registrations as unresolved evidence
       -> bind permitted/attempted/skipped actions, unresolved resources,
          gate hashes, cleanup verdict, and chosen final status
       -> cleanup fault or restricted authority yields INFRA_FAILURE
  -> exact trusted_runtime_argv_prefix + DurableTerminalFinalizer(final status)
       -> atomically write result.json and goal_plan.status
       -> emit exactly one terminal token
  -> explicit terminal carrier publishes matching CLI outcome
```

Each dependency wave is drawn explicitly. `shape=component` and
`shape=tripleoctagon` provide concurrent fan-out/fan-in only within that visible
wave. Each branch contains its statically named launch and monitor/poll gates.
Launch nodes start the approved child process and atomically record the process
ledger; they perform no lane cognition. Monitor gates poll only their compiled
lane ID until the child is terminal, timed out, cancelled, or inconsistent.
Each poll is one supervisor long-poll with exact `--wait-seconds 30`, not a
sleep node or model turn.
The graph contains no generic "get next lane" operation, dynamic scheduler, or
work queue.

Composition expands the correction branch statically through the compiled
`max_integration_corrections`: each ordinal has explicit
`ReserveCorrectionRound`, supervisor-launch/ack, terminal-consumption, proof, and
exhaustion/residual nodes. Edges may loop through those statically named
ordinals, but no runtime counter chooses a hidden correction slot. Admission
parses the DOT and proves the ordinal set is exactly `1..N`, every
`correction_round_id` template is exact, and no route can reach ordinal `N+1`.

### Engine-step and long-poll contract

The parent DOT embeds graph attributes `poll_wait_seconds="30"` and
`engine_step_multiplier="50"`. Composition statically computes, records in
`plan.json`, and embeds for every lane, correction, and delivery monitor branch:

- `branch_nonpoll_steps`: the conservative maximum deterministic/LLM node
  executions outside the poll loop for one branch traversal;
- `branch_node_count`: the exact reachable node count in that static branch;
  and
- `max_poll_cycles = ceil(max_child_seconds / poll_wait_seconds)`.

Admission recomputes those values from the immutable DOT and enforces, for every
branch, exactly:

```text
ceil(max_child_seconds / poll_wait_seconds) + branch_nonpoll_steps
  < branch_node_count * 50
```

It also expands all statically possible branch traversals under
`max_process_launches`, `max_integration_corrections`, and the two-attempt
delivery limit, computes `parent_total_step_upper_bound`, and requires:

```text
parent_total_step_upper_bound < parent_node_count * engine_step_multiplier
```

A mismatch or non-strict inequality fails admission before mutation. The
supervisor `poll` client receives exact `--wait-seconds 30`, validates the
process identities and durable result before and after waiting, and returns
early on terminal state. Its monotonic wait is capped by the smaller remaining
lane wall and run-wide deadline, so it never sleeps past either deadline.

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
| Attempt budget | Maximum local verification-bearing adaptive attempts available to the lane. Every one is reserved by `ReserveGlobalAttempt` and consumed only at verifier-record classification; supervisor starts/restarts are separately bounded by run-wide `max_process_launches`. |

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
- every `ReserveGlobalAttempt` reservation/start/classification record and
  bound verifier-definition hash;
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

- the exact argv, or the checked-in script's content SHA-256;
- the exact ordered symbolic CWD policies `lane_worktree`,
  `candidate_verification_worktree`, and `integration_worktree`;
- the configured timeout;
- exact `write_policy: "read_only"` and run-scoped external output policy;
- the shared `envelope_definition_sha256`;
- lane-verifier evidence schema version `goal-plan.lane-verifier/v1`; and
- the exact exit/verdict/token mapping.

No resolved absolute path is part of the immutable hash. A child attempt selects
`lane_worktree`; pre-integration parent verification selects
`candidate_verification_worktree`; affected-closure and final-sweep
verification select `integration_worktree`.

At runtime:

- `lane_worktree` resolves to exact `worktree_root/lane-LANE_ID` and is rooted
  at the lane's current integration base, which descends from
  `execution_source_sha`;
- `candidate_verification_worktree` resolves to a unique disposable path under
  `worktree_root/candidate-LANE_ID-CANDIDATE_SHA-ATTEMPT`
  and is detached at that exact candidate SHA; and
- `integration_worktree` resolves beneath `worktree_root/integration`
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
2. atomically writes its exact `candidate` `CREATING` entry to
   `run-owned-worktrees.json`, creates the clean disposable detached worktree at
   the exact candidate SHA under the dedicated external worktree root, and marks
   it `ACTIVE` only after validating path, registration, common directory, and
   detached HEAD;
3. invokes the shared `VerifierExecutionEnvelope` with immutable
   `expected_head_sha = candidate_sha` and
   `cwd_policy = candidate_verification_worktree`;
4. records the complete envelope postconditions before any teardown begins;
5. marks the registry entry `REMOVING`, removes the detached worktree without
   `--force`, prunes/reconciles its Git registration, proves both filesystem
   path and worktree-list entry are absent, and marks it `REMOVED`; and
6. atomically records teardown command/result, registration reconciliation, and
   final candidate-verification disposition separately from envelope evidence.

Envelope teardown never starts until its post-HEAD, post-status, and
post-compiled-source records are durable. A wrong initial HEAD, path escape,
create failure, red envelope, remove failure, stale registration, or inability
to reconcile is `INFRA_FAILURE`, regardless of verifier exit. It never becomes
lane feedback. A verifier failure is product evidence only after the envelope
remains integral and clean teardown succeeds.

### VerifierExecutionEnvelope

Every parent-side lane or aggregate verifier runs through one checked-in
deterministic `VerifierExecutionEnvelope`. It is mandatory for:

- pre-integration candidate lane verification;
- aggregate verification immediately after each merge;
- every affected-closure lane and affected-closure aggregate verification;
- the pre-coherence aggregate at current HEAD before every coherence review;
- the final all-lane verifier sweep; and
- `final-aggregate-after-sweep`.

The caller supplies immutable `expected_head_sha`, one symbolic CWD policy, the
approved verifier argv/hash/timeout, and a run-scoped external evidence
directory at
`state_root/verifications/VERIFICATION_KIND/INVOCATION_ID/`. Candidate
verification selects
`candidate_verification_worktree`; every aggregate, affected-closure,
final-sweep, pre-coherence aggregate, and
`final-aggregate-after-sweep` invocation selects `integration_worktree`.
The caller cannot replace the envelope's HEAD, cleanliness, compiled-source, or
output-root policies.

For each invocation, the parent mints absolute
`verifier_output_root = state_root/verifications/VERIFICATION_KIND/INVOCATION_ID/output`.
The compiled verifier argv must contain exactly
`--output-root <verifier_output_root>`. Admission rejects any verifier template
that lacks that two-argument interface or allows another output root.

The envelope supplies this exact containment environment:

| Variable | Exact value |
|---|---|
| `GOAL_PLAN_VERIFIER_OUTPUT_ROOT` | `<verifier_output_root>` |
| `TMPDIR` | `<verifier_output_root>/tmp` |
| `XDG_CACHE_HOME` | `<verifier_output_root>/xdg-cache` |
| `PYTHONPYCACHEPREFIX` | `<verifier_output_root>/pycache` |
| `COVERAGE_FILE` | `<verifier_output_root>/coverage/.coverage` |

All values are absolute, external to every Git worktree and compiled source,
and created only beneath approved `state_root`.

#### Immutable envelope definition

`plan.json.verifier_execution_envelope` declares:

- schema version `goal-plan.verifier-envelope-definition/v2`;
- checked-in implementation path and content SHA-256;
- exact HEAD command `git rev-parse --verify HEAD`;
- exact full non-ignored status command
  `git status --porcelain=v2 --untracked-files=all --ignored=matching`;
- complete worktree-filesystem manifest algorithm defined below;
- exact verifier output-root argv/environment interface and containment check;
- compiled-source gate definition/hash;
- exact symbolic CWD policy allowlist;
- external output-root policy `state_root_only`;
- evidence schema `goal-plan.verifier-envelope/v2`;
- verdict/token mapping; and
- `definition_sha256`.

The definition hash covers all values above in canonical order. Each lane and
aggregate verifier definition includes
`envelope_definition_sha256`, `write_policy: "read_only"`, and an explicit
contract that all verifier stdout, stderr, structured results, coverage,
temporary output, caches, and reports are directed beneath the invocation's
run-scoped `state_root` evidence directory. A verifier definition that requires
any index or worktree write is invalid at composition/admission and is never
executed.

Verifier code is trusted deterministic code, not an adversarial sandbox
subject. The envelope detects accidental or contract-violating filesystem
effects and rejects their result; it does not claim to confine arbitrary
malicious code outside the observed worktree/output contracts.

#### Execution sequence

For each invocation the envelope performs exactly:

1. Resolve the symbolic CWD policy to its recorded worktree, canonicalize the
   path with `realpath`, prove the expected Git common directory, and require
   the evidence/output directory to be outside that worktree and beneath
   run-scoped `state_root`.
2. Run the exact HEAD command, record stdout/stderr/exit as `pre_head`, and
   require `pre_head == expected_head_sha`.
3. Run the exact status command, record stdout/stderr/exit as `pre_status`, and
   require successful exit and the approved baseline output. Porcelain v2 plus
   `--untracked-files=all --ignored=matching` makes tracked, index, untracked,
   and ignored state explicit.
4. Build and persist `pre_worktree_manifest` for the complete verification
   worktree, excluding only `.git` internals.
5. Run `CompiledSourceGate`, persist `pre_compiled_source`, and require exact
   admission-manifest match.
6. Create the verifier-output-root subdirectories, inject the exact containment
   environment, run verifier argv with the verified worktree as CWD and timeout
   from its immutable definition, and direct every log/result/output path under
   `verifier_output_root`.
7. Run the exact HEAD command again, persist `post_head`, and require
   `post_head == expected_head_sha == pre_head`.
8. Run the same exact status command again and persist `post_status`.
9. Build and persist `post_worktree_manifest`; require exact canonical equality
   with `pre_worktree_manifest`.
10. Run `CompiledSourceGate` again, persist `post_compiled_source`, and require
   exact admission-manifest match.
11. Independently walk `verifier_output_root`, persist its complete output
    manifest, and require every declared verifier output/log/cache/report to
    exist beneath that root and no declared output path to escape it.
12. Atomically write the complete evidence record and emit exactly one envelope
   token.

Postconditions run even when the verifier exits nonzero, times out, or cannot be
started. The verifier result is not classified until every postcondition has
finished.

The worktree manifest recursively uses `lstat` from the worktree root and
excludes only the `.git` file/directory and its internals. It includes tracked,
untracked, and ignored entries. Entries are sorted by normalized
repository-relative path and record path, file type, mode, and size; regular
files additionally record SHA-256 of exact bytes, symlinks record exact link
target bytes, and directories record mode. Added, removed, type-changed,
mode-changed, size-changed, target-changed, or byte-changed entries are red.

#### Evidence and verdict contract

Every invocation writes one atomic record with:

| Field | Contract |
|---|---|
| `schema_version` | Exact value `goal-plan.verifier-envelope/v2`. |
| `invocation_id`, `verification_kind` | Unique run-scoped ID and one of `candidate_lane`, `aggregate_after_merge`, `affected_closure_lane`, `affected_closure_aggregate`, `pre_coherence_aggregate`, `final_sweep_lane`, or `final_aggregate_after_sweep`. |
| `product_base_sha`, `execution_source_sha` | Exact admitted source SHAs. |
| `expected_head_sha`, `pre_head_sha`, `post_head_sha` | Full SHAs; all three must be equal for a non-infrastructure verdict. |
| `cwd_policy`, `cwd` | Approved symbolic token and canonical worktree realpath. |
| `pre_head_command`, `post_head_command` | Exact canonical HEAD argv plus stdout/stderr paths, exit codes, and captured values. |
| `pre_status_command`, `post_status_command` | Exact canonical status argv plus stdout/stderr paths, exit codes, and complete outputs. |
| `pre_worktree_manifest`, `post_worktree_manifest` | Paths and hashes for complete tracked/untracked/ignored filesystem manifests excluding only `.git` internals. |
| `pre_compiled_source_record`, `post_compiled_source_record` | Paths and hashes of both exact manifest-gate records. |
| `envelope_definition_sha256`, `verifier_definition_sha256` | Recomputed immutable definition hashes. |
| `verifier_argv`, `verifier_cwd`, `verifier_exit_code`, `verifier_timed_out` | Exact observed verifier invocation and result. |
| `verifier_stdout_path`, `verifier_stderr_path`, `verifier_result_paths` | Absolute paths beneath run-scoped `state_root`, never beneath the worktree. |
| `verifier_output_root`, `verifier_environment`, `verifier_output_manifest` | Canonical output root, exact containment environment, and parent-generated complete output manifest. |
| `verifier_result_discarded` | Boolean true whenever any envelope integrity check is red. |
| `verdict` | Exact value `PASS`, `FAIL`, or `INFRA`. |

The last non-empty stdout line is exactly:

| Condition | Verdict | Token |
|---|---|---|
| All envelope checks green; verifier exits `0` before timeout | `PASS` | `VERIFIER_ENVELOPE:PASS` |
| All envelope checks green; verifier exits `1` before timeout | `FAIL` | `VERIFIER_ENVELOPE:FAIL` |
| Any pre/post integrity check red; verifier exits `2+`; timeout; execution/hash/evidence failure | `INFRA` | `VERIFIER_ENVELOPE:INFRA` |

Any tracked mutation, index change, untracked or ignored path change, commit,
checkout, HEAD movement, filesystem-manifest change, output escape, worktree
dirtiness, or compiled-source mismatch sets
`verifier_result_discarded = true` and routes directly to `INFRA_FAILURE`.
Even a verifier exit `0` is discarded. Envelope `INFRA` never enters lane or
integration correction and can never become `PASS`.

### Child launch and process-supervision contract

`goal_plan_supervisor.py` provides one accountable long-lived reaper process per
lane, integration-correction, or delivery process launch. It is neither tmux
nor a shared daemon/service. Each supervisor owns exactly one child Attractor,
remains alive until that child is reaped and its authoritative result is
durable, then exits. Initial starts and all replacement starts use the same
contract and consume the separately bounded `max_process_launches`; they do not
consume `max_total_attempts`.

The immutable supervisor prefix is distinct from the child Attractor runner.
Every supervisor invocation is exactly the compiled
`trusted_supervisor_argv_prefix` from `trusted-runtime-binding.json` followed by
one of the closed suffixes below.
No caller may substitute the target-repository `goal_plan_supervisor.py`, a
PATH-resolved executable, a shell command, or another interpreter directly.

The non-mutating version/identity preflight is:

```text
<each token of trusted_supervisor_argv_prefix> self-check --format json
```

The exact reaper interface is:

```text
<each token of trusted_supervisor_argv_prefix> run --contract <absolute launch-contract.json> --intent <absolute launch-intent.json> --ledger <absolute process-ledger.json> --ack <absolute launch-ack.json> --result <absolute supervisor-result.json>
```

The short-lived deterministic control-client interfaces are:

```text
<each token of trusted_supervisor_argv_prefix> poll --contract <absolute launch-contract.json> --intent <absolute launch-intent.json> --ledger <absolute process-ledger.json> --ack <absolute launch-ack.json> --result <absolute supervisor-result.json> --budget-ledger <absolute run-wide.json> --budget-lock <absolute run-wide.lock> --wait-seconds 30 --output <absolute poll-result.json>
<each token of trusted_supervisor_argv_prefix> terminate --contract <absolute launch-contract.json> --intent <absolute launch-intent.json> --ledger <absolute process-ledger.json> --budget-ledger <absolute run-wide.json> --budget-lock <absolute run-wide.lock> --reason <token> --output <absolute termination-result.json>
<each token of trusted_supervisor_argv_prefix> reconcile --contract <absolute launch-contract.json> --intent <absolute launch-intent.json> --ledger <absolute process-ledger.json> --ack <absolute launch-ack.json> --result <absolute supervisor-result.json> --budget-ledger <absolute run-wide.json> --budget-lock <absolute run-wide.lock> --output <absolute reconciliation-result.json>
```

The suffixes, option order, option cardinality, and accepted schema versions are
immutable. `run`, `poll`, `terminate`, and `reconcile` reject extra, missing,
reordered, or unknown arguments. Each invocation uses the exact closed
supervisor environment schema and records the prefix hash, executable or
interpreter/script identity, CLI version, exact argv, environment hash, and
command hash before execution.

All paths are deterministic and absolute. Per-process outputs are beneath the
lane/correction `state_root` namespace or delivery `delivery_state_root`
namespace; the two shared budget paths are beneath `state_root/budgets/`.
Everything is outside every Git worktree. All JSON writes use same-directory
temporary files, fsync, atomic replace, and canonical JSON hashes.

#### Launch intent and parent spawn

After approval and an atomic process-launch reservation, the parent mints
`launch-intent.json` with schema `goal-plan.launch-intent/v3` before starting
the supervisor. It contains:

| Field | Contract |
|---|---|
| `schema_version` | Exact value `goal-plan.launch-intent/v3`. |
| `process_kind`, `process_id`, `process_launch`, `process_run_id` | Exact approved lane/correction/delivery identity, positive process-launch ordinal, and canonical process-run ID. |
| `launch_contract_path`, `launch_contract_sha256` | Absolute contract path and canonical hash. |
| `process_launch_reservation_id` | Exact live process-launch reservation from the run-wide budget ledger; never an adaptive-attempt reservation. |
| `correction_round_id` | Required canonical correction-round reservation ID for `process_kind: "correction"`; null otherwise. |
| `attractor_runner_argv_prefix_sha256`, `provider` | Exact immutable compiled child-runner prefix hash and provider. |
| `trusted_runtime_binding_path`, `trusted_runtime_binding_sha256`, `runtime_bundle_hash` | Exact external binding revalidated by the parent immediately before launch. |
| `trusted_supervisor_argv_prefix_sha256`, `trusted_supervisor_identity` | Exact immutable external supervisor prefix hash and executable/interpreter/script/CLI/schema identity from the validated trusted-runtime binding. |
| `supervisor_argv`, `supervisor_env`, `supervisor_cwd` | Exact prefix-plus-`run`-suffix argv, closed environment, and canonical lane, integration, or delivery worktree CWD. The argv and environment both contain exact `process_run_id`; environment key is `GOAL_PLAN_PROCESS_RUN_ID`. |
| `ledger_path`, `ack_path`, `supervisor_result_path` | Exact deterministic absolute output paths. |
| `identity_policy` | Exact value `goal-plan.linux-procfs-identity/v1`. |
| `supervisor_command_sha256` | Canonical hash of executable/argv/env/CWD/process-run/contract/output identities. |

The `goal-plan.process-launch-contract/v3` is immutable and contains exact
process kind/ID, correction-round ID when applicable, child
`attractor_runner_argv_prefix` tokens/hash,
executable/module/source identity, provider, closed child argv/env/CWD,
process-run ID, source identities, process-launch reservation,
trusted-runtime binding path/hash and runtime-bundle hash,
`trusted_supervisor_argv_prefix` tokens/hash and identity, exact supervisor
`run` suffix/environment, log descriptors, child result/evidence paths, wall
timeout, TERM grace, and child launch-command hash. Child argv includes exact
`--provider`, `--param process_run_id=...`, and `--on-human-gate fail`; child
environment contains exact `GOAL_PLAN_PROCESS_RUN_ID`.

The parent atomically persists the intent, then starts the reaper:

```python
subprocess.Popen(
    supervisor_argv,
    cwd=supervisor_cwd,
    env=supervisor_env,
    start_new_session=True,
)
```

Before `Popen`, the parent proves `supervisor_argv` equals the exact immutable
prefix plus the closed `run` suffix and proves the environment hash equals the
compiled schema. It records the provisional supervisor PID with the intent
invocation evidence. This PID is not trusted until ledger/ack identity
validation succeeds.

#### Reaper lifecycle and authoritative result

`run` first revalidates its external trusted-runtime binding, interpreter, own
supervisor file, and exact prefix, then validates intent, contract,
process-launch reservation, correction-round
reservation when applicable, child-runner prefix/module/source/provider,
trusted-supervisor prefix/executable/interpreter/script/CLI/schema identity,
hashes, paths, executable, CWD, environment, exact suffix, and output
descriptors. Before launching the child, it atomically records its own canonical
Linux procfs identity in `goal-plan.process-ledger/v4`. It then
launches the child Attractor as its direct child in a distinct child process
group, validates child PID/PGID/procfs identity, records child identity, and
atomically writes/fsyncs ledger then `goal-plan.launch-ack/v4`. Creation of the
reaper or child consumes the process-launch reservation exactly once; only
proof that no process was created permits `RELEASED_NO_PROCESS`.

The reaper remains alive and calls `wait`/`waitpid` until child termination. It
alone owns:

- child stdout/stderr descriptors;
- wall-timeout enforcement;
- forwarding parent-requested signals;
- TERM -> compiled grace -> KILL;
- child process-group cleanup;
- child reaping and zombie prevention; and
- authoritative raw OS wait-status capture.

After child termination, it proves the child process group is empty, hashes the
closed logs, and atomically writes `supervisor-result.json` with schema
`goal-plan.supervisor-result/v3`:

| Field | Contract |
|---|---|
| `schema_version`, `process_kind`, `process_id`, `process_run_id`, `process_launch_reservation_id`, `correction_round_id` | Exact run, process-launch, and optional correction-round identities. |
| `attractor_runner_argv_prefix_sha256`, `provider` | Exact compiled runner/provider bindings observed by the supervisor. |
| `trusted_runtime_binding_path`, `trusted_runtime_binding_sha256`, `runtime_bundle_hash` | External binding identity revalidated before supervisor action. |
| `trusted_supervisor_argv_prefix_sha256`, `trusted_supervisor_identity` | Exact external supervisor prefix and executable/interpreter/script/CLI/schema binding revalidated and observed by the supervisor. |
| `intent_sha256`, `launch_contract_sha256`, `ledger_sha256` | Exact bound artifact hashes. |
| `supervisor_identity`, `final_child_identity` | Canonical validated Linux identities. |
| `raw_wait_status` | Exact non-negative integer returned by `wait`/`waitpid`. |
| `normalized_exit_code` | Integer exit code when exited normally, otherwise null. |
| `terminating_signal`, `core_dumped` | Signal integer/boolean when signalled, otherwise null/false. |
| `timed_out`, `cancellation_reason` | Timeout flag and approved reason token or null. |
| `stdout_sha256`, `stderr_sha256`, `child_group_empty` | Closed-log hashes and cleanup proof. |
| `child_result_path`, `child_result_sha256`, `child_result_valid` | Child-written evidence reference only; never exit evidence. |
| `completed_at_boottime`, `verdict` | Durable observation and exact `EXITED`, `SIGNALED`, `TIMED_OUT`, `CANCELLED`, or `INFRA`. |

Only after this atomic result exists may `run` exit. Child-written result or
evidence can never substitute for missing `supervisor-result.json`, alter raw
wait status, or override normalized exit/signal/timeout classification.

#### Control-client contracts

Every client first validates the external trusted-runtime binding and proves its
own argv is the exact immutable trusted-supervisor prefix plus the compiled
control suffix, then validates interpreter/supervisor path, permissions and
hashes, prefix/identity/environment, intent/contract/binding hashes, and full
supervisor and child procfs identities before observation or signalling. It
rechecks the external identities after waiting and before any signal. Result
schemas reject unknown fields and share process-run ID, binding/artifact hashes,
observed boottime, identities, verdict, and failure reason.

`poll` writes `goal-plan.supervisor-poll/v2`. Exact `--wait-seconds 30` is
mandatory. The client validates intent, contract, budget ledger, supervisor and
child identities before waiting; waits internally on durable result/process
state without model or graph sleep; caps the monotonic wait at the smaller
remaining child-wall and run-wide deadline; validates identities and result
again after waking; and emits exactly:

- `SUPERVISOR:POLL_RUNNING`;
- `SUPERVISOR:POLL_TERMINAL` only for a complete valid supervisor result;
- `SUPERVISOR:POLL_SUPERVISOR_GONE`; or
- `SUPERVISOR:POLL_INFRA`.

`terminate` accepts only `global_deadline`, `child_wall_timeout`,
`child_cancelled`, `parent_aborted`, or `recovery_cleanup`. It signals the
identity-valid supervisor, which forwards/cleans/reaps its child, writes
`goal-plan.supervisor-termination/v2`, and emits exactly:

- `SUPERVISOR:TERMINATION_REQUESTED`;
- `SUPERVISOR:ALREADY_TERMINAL`; or
- `SUPERVISOR:TERMINATE_INFRA`.

`reconcile` writes `goal-plan.supervisor-reconciliation/v2` and emits exactly:

- `SUPERVISOR:RECONCILED_RUNNING`;
- `SUPERVISOR:RECONCILED_TERMINAL`;
- `SUPERVISOR:RECONCILED_INTERRUPTED_BEFORE_LAUNCH`; or
- `SUPERVISOR:RECONCILE_INFRA`.

#### Parent crash, supervisor crash, and pre-ledger discovery

A parent graph/CLI crash does not terminate the reaper: it is in its own
session/process group, continues waiting/reaping, and writes the authoritative
result. On restart, the parent reconciles deterministic intent/ledger/ack/result
paths and adopts only an identity-valid live supervisor or a complete valid
supervisor result.

If the supervisor disappears before a valid result, child evidence and process
absence are never success. If the ledger identifies a live identity-valid child,
the terminate client stops its process group and the run becomes
`INFRA_FAILURE`. If the child is absent and no authoritative result exists, the
run is `INFRA_FAILURE`. A live parent monitor detecting a vanished supervisor
applies this rule immediately and never continues trusting an orphan child.

For intent-without-ledger/ack recovery, `reconcile` performs a bounded Linux
procfs scan: at most one pass per second for the compiled
`pre_ledger_reconciliation_timeout_seconds`, capped at 3 full scans. It scans
`/proc/[0-9]*/cmdline` and `/proc/[0-9]*/environ` for the exact unique
`process_run_id`, then validates executable realpath, command hash, boot ID,
start ticks, PGID, CWD, contract path/hash, and
`GOAL_PLAN_PROCESS_RUN_ID`.

- Exactly one matching live supervisor is adopted and required to finish
  ledger/ack.
- A matching orphan child without its supervisor is identity-validated,
  terminated through the control path, and classified `INFRA_FAILURE`.
- Zero matches with no result becomes
  `INTERRUPTED_BEFORE_LAUNCH` only when the process-launch reservation remains
  `RESERVED` and reconciliation proves no reaper or child process was created;
  that process-launch reservation becomes `RELEASED_NO_PROCESS`. A consumed
  process-launch reservation is `INFRA_FAILURE`.
- Multiple or ambiguous matches are `INFRA_FAILURE` and none is signalled until
  identity becomes unambiguous.

The parent monitor checks run and child deadlines before each `poll`; `poll`
performs the same check internally and never waits beyond the remaining
deadline.
Cancellation and deadline handling always call `terminate`; no graph node
treats supervisor or child disappearance as lane completion.

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

Before a control client observes or signals either PID, it rereads and exactly
matches boot ID, PID start ticks, cmdline hash, PGID, executable realpath, CWD,
process-run token, and command hash. `kill -0` proves only liveness after full
identity validation. Mismatch/unreadable identity is `INFRA_FAILURE`; no
ambiguous PID/group is signalled or adopted.

Manual observation uses durable logs, ledger/ack/result history, child Attractor
events, `process_run_id`, and optional child box-session IDs.

### Aggregate verifier contract

The approved plan also contains one immutable aggregate-verifier contract. It
declares:

- either the exact non-interactive argv or the repository-relative path and
  content SHA-256 of a checked-in executable script;
- the symbolic cwd policy token `integration_worktree`;
- a configured timeout in seconds;
- exact `write_policy: "read_only"`, mandatory
  `--output-root {verifier_output_root}` interface, containment environment,
  and external run-scoped output paths;
- the shared `envelope_definition_sha256`;
- a SHA-256 verifier-definition hash;
- the stdout/stderr log location; and
- the JSON evidence-record location.

The immutable verifier-definition hash covers a canonical serialization of:

- the exact argv, or the checked-in script's content SHA-256;
- exact symbolic cwd policy token `integration_worktree`;
- the configured timeout;
- the read-only/external-output policy;
- the exact output-root argv/environment interface;
- the shared envelope-definition hash;
- evidence schema version `goal-plan.aggregate-verifier/v1`; and
- the exact exit/verdict/last-line-token mapping below.

The canonical hash input never contains a resolved absolute worktree path, so
the same approved verifier contract has the same hash across runs. Before every
aggregate run, the envelope recomputes the immutable definition hash and
compares it with the approved value. A mismatch is infrastructure failure; the
changed verifier is not run as though it were the approved definition of done.

At runtime, the envelope resolves `integration_worktree` from `target_repo`,
`state_root`, and `run_id`, canonicalizes it with `realpath`, requires equality
with the integration-worktree realpath in the durable run record, and confirms
that it uses the target repository's Git common object database. That resolved
absolute path is runtime evidence, not immutable contract input.

Every invocation supplies immutable `expected_head_sha` and
`cwd_policy = integration_worktree` to `VerifierExecutionEnvelope`. No aggregate
node executes the verifier directly. The envelope writes verifier stdout,
stderr, results, and integrity evidence beneath the run's integration evidence
directory. An adjacent aggregate projection is written atomically with:

| Field | Contract |
|---|---|
| `schema_version` | Exact value `goal-plan.aggregate-verifier/v1`. |
| `attempt` | Positive integer for this aggregate-verifier invocation. |
| `product_base_sha`, `execution_source_sha` | Exact admitted source SHAs. |
| `expected_head_sha` | Immutable full SHA supplied by the caller. |
| `verifier_hash` | Recomputed SHA-256 verifier-definition hash. |
| `envelope_hash` | Recomputed shared envelope-definition hash. |
| `envelope_evidence_path` | Path to the complete `goal-plan.verifier-envelope/v2` record. |
| `cwd_policy` | Exact value `integration_worktree`. |
| `cwd` | Absolute, `realpath`-canonicalized integration-worktree path from envelope evidence. |
| `exit_code`, `timed_out` | Verifier result copied from envelope evidence only after integrity classification. |
| `verdict` | Exact value `PASS`, `FAIL`, or `INFRA`. |

The deterministic aggregate classifier validates the envelope schema and hashes
and emits exactly one aggregate token:

| Observed result | JSON verdict | Last-line token |
|---|---|---|
| Envelope `PASS` | `PASS` | `AGGREGATE_VERIFY:PASS` |
| Envelope `FAIL` | `FAIL` | `AGGREGATE_VERIFY:FAIL` |
| Envelope `INFRA`, missing/stale evidence, or hash/schema mismatch | `INFRA` | `AGGREGATE_VERIFY:INFRA` |

Graph edges route on `tool.last_line`. Only `AGGREGATE_VERIFY:PASS` may advance
to another dependency wave, a coherence review, the post-sweep aggregate gate,
delivery eligibility, or completion. `FAIL` enters the responsible correction
loop; `INFRA` leaves product-correction loops and routes toward
`INFRA_FAILURE`.

## Lane Convergence Subgraph

Each headless child process runs the versioned, hash-checked `goal_lane.dot`
already present in its lane worktree. The subgraph adapts the proven task-runner
shape:

```text
Orient
  -> ReserveGlobalAttempt
  -> MarkAttemptStarted
  -> Adaptive Attempt
  -> Deterministic verifier
  -> ClassifyVerifierAndConsumeGlobalAttempt
       -> red -> classify failure
                    -> novel/actionable -> curate feedback -> ReserveGlobalAttempt
                    -> repeated signature -> root-cause diagnosis
                         -> actionable change of course -> ReserveGlobalAttempt
                         -> blocker -> BLOCKED
                    -> budget exhausted -> budget-exhausted
       -> green -> optional fresh qualitative critique
                    -> iterate -> curate feedback -> ReserveGlobalAttempt
                    -> pass -> ownership check -> commit check -> PASS candidate
```

`ReserveGlobalAttempt` is deterministic code whose checked-in bytes are part of
the compiled source, but the node executes only through the external
`trusted_runtime_argv_prefix`. Immediately before each adaptive `Attempt`, that
external command revalidates the binding, opens the external flocked budget
ledger, and reserves by exact tuple:

```text
(lane_or_correction_id, process_run_id, local_attempt, verifier_definition_sha256)
```

The tuple is unique and idempotent across child restart. It checks the child's
local `max_attempts`, run-wide `max_total_attempts`, boot identity, and deadline
before atomically writing `RESERVED`. It never increments or admits against
`max_integration_corrections`; that ceiling belongs exclusively to the
parent-side supervised correction-round reservation.
`MarkAttemptStarted` durably records that the adaptive node began before model
work starts. The deterministic verifier writes one immutable verifier record;
`ClassifyVerifierAndConsumeGlobalAttempt` binds that record's path/hash/verdict
to the reservation and transitions it to `CONSUMED` exactly once. A duplicate
classification is idempotent only when every bound value matches.

A crash after reservation consumes conservatively when
`MarkAttemptStarted` or verifier-start evidence exists: reconciliation writes a
synthetic crash classification and consumes that reservation. It may transition
to `RELEASED_NO_ATTEMPT` only when durable state plus process evidence prove the
adaptive attempt never started. Process launch/relaunch neither reserves nor
consumes an adaptive attempt by itself; conversely one healthy child process
may consume several bounded adaptive attempts.

The cheap deterministic verifier always precedes the expensive qualitative
gate. Feedback records the highest-leverage next correction and replaces stale
guidance rather than growing an unbounded transcript. Repeated identical
failure signatures route to diagnosis rather than another blind attempt.

The child lane graph does not mark the batch lane `PASS`, certify integration,
or certify batch completion. It produces a candidate commit and versioned
`goal-plan.lane-result/v2` evidence under
`state_root/lanes/<lane-id>/runs/<process-launch>/`. Parent verification in a
clean detached candidate worktree assigns the final `PASS` disposition.

### Integration-correction convergence subgraph

The supervised `integration_correction.dot` uses the same accounting skeleton:

```text
OrientCorrection
  -> ReserveGlobalAttempt
  -> MarkAttemptStarted
  -> Adaptive Correction
  -> Commit correction
  -> Deterministic correction verifier using aggregate verifier definition/hash
  -> ClassifyVerifierAndConsumeGlobalAttempt
       -> red -> curate findings -> ReserveGlobalAttempt
       -> green -> ownership check -> correction-result candidate
       -> local/global attempt budget exhausted -> residual
```

Its reservation tuple substitutes the immutable correction ID for lane ID and
uses the aggregate verifier's `definition_sha256`. The child verifier emits a
run-scoped correction-attempt record beneath external `state_root`; it never
certifies closure/coherence/completion. After an authoritative zero-exit child
result, the parent still reruns the complete affected-closure aggregate and
pre-coherence sequence. Crash release/consumption rules are identical to lane
attempts.

The terminal `correction-result.json` uses schema
`goal-plan.correction-result/v1` and binds correction/process IDs,
`correction_round_id`, process launch, both source SHAs, child- and
supervisor-runner/provider hashes, integration base and candidate correction
commit, ordered adaptive-attempt reservation/verifier records, ownership
evidence, and exact candidate disposition. It is a parent routing hint only.

## Deterministic and LLM Boundaries

| Responsibility | Owner | Reason |
|---|---|---|
| Parent pre-start CWD, runner `--cwd .`, target-repository, parent-DOT path/hash, argv/provider/process/logs binding | Deterministic launcher plus `ParentRunnerBindingGate` | The parent must execute the reviewed graph in the repository named by the plan; an alternate CWD or DOT copy cannot be repaired by model work. |
| Plan-schema validation, dependency-cycle checks, ownership-collision checks, source-SHA/compiled-manifest admission | Deterministic nodes | These are exact predicates. |
| Lane, candidate-verification, and integration worktree creation, cleanliness, cleanup, branch/source inspection | Deterministic nodes | Git state is observable and must be reproducible. |
| Child process launch, identity ledger, logs, timeout, TERM/grace/KILL, exit capture, and restart reconciliation | Deterministic supervisor and parent nodes | Process control is exact infrastructure state; artifacts cannot substitute for the real exit status. |
| `ReserveGlobalAttempt`, attempt-start marking, verifier-record classification, and exact-once consumption | Deterministic child/runtime nodes using the external flocked ledger | Verification-bearing work is the scarce attempt unit; process launches are a separate substrate budget. |
| Advancing a lane goal and adapting implementation | LLM lane worker inside the child Attractor process | The implementation path may change as the domain surprises the worker. |
| Running parent-side lane and aggregate verifiers plus pre/post integrity checks | Shared deterministic `VerifierExecutionEnvelope` | A verifier result is evidence only when immutable HEAD, cleanliness, compiled source, and external-output invariants survive. |
| Failure-signature comparison and budget accounting | Deterministic nodes | Loop control must not depend on model judgment. |
| Root-cause diagnosis after repeated failure | Fresh or gate-class LLM context | Classification may require semantic judgment, but its proposed correction is tested by the deterministic verifier. |
| Optional qualitative lane critique | Independent LLM gate plus deterministic artifact classifier | Some acceptance criteria cannot be reduced to a command; the reviewer must be outside the worker context, and its versioned artifact must be schema-valid and tied to the exact commit. |
| Ownership diff, commit existence, ancestry, clean-state checks | Deterministic nodes | A worker cannot attest its own git side effects. |
| Merge/cherry-pick, rollback of a failed candidate, merge journal | Deterministic nodes | Integration is state mutation with exact success criteria. |
| Trusted-runtime bootstrap, pre-terminal authority derivation, process reconciliation, authority-scoped run-owned worktree removal/preservation, foreign-path proof, and final-status choice | Deterministic launcher plus externally pinned `PreTerminalCleanup` | The launcher materializes exact Git blobs and validates the external binding before executing safety code. Cleanup receives `FULL` only from fresh green trusted-runtime, parent-runner, target/source, and compiled-source gates; a green trusted runtime plus red repository/source binding restricts it to `EXTERNAL_ONLY`; a red trusted runtime grants `NONE` and prohibits cleanup/finalizer completion. |
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
3. Complete verifier-envelope pre/post HEAD, cleanliness, compiled-source, and
   external-output integrity evidence.
4. Non-discarded verifier argv, exit status, timeout status, and captured
   output.
5. Deterministic ownership and dependency checks.
6. Independent qualitative review tied to an exact commit, only for criteria
   that genuinely require judgment.
7. Remote API state for delivery.

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
- process-launch record plus every adaptive-attempt reservation/start/verifier
  classification record;
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
| `schema_version` | Exact value `goal-plan.lane-result/v2`. |
| `lane_id`, `plan_hash` | Exact compiled lane ID and approved plan hash. |
| `process_run_id`, `process_launch` | Canonical process-run ID and matching positive process-launch ordinal. |
| `product_base_sha`, `execution_source_sha` | Exact admitted source SHAs. |
| `child_dot_sha256`, `launch_command_sha256` | Exact approved child DOT and launch-contract hashes. |
| `process_ledger_path`, `child_box_session_ids` | Path to the matching durable process record and optional observability-only box-session ID array. |
| `integration_base_sha`, `candidate_head_sha` | Full expected integration base and candidate commit SHA, or null candidate when no commit exists. Both must descend from `execution_source_sha`. |
| `attempts_used`, `max_attempts` | Non-negative count of classified/consumed verification-bearing adaptive attempts and approved positive local limit; process launches are excluded. |
| `attempt_reservation_paths` | Ordered non-empty array when an attempt started; every record binds lane ID, process-run ID, local attempt, verifier hash, and exact-once classification. |
| `candidate_disposition` | One of `CANDIDATE`, named `FAIL`, named `BLOCKED`, `PENDING_HUMAN`, or `BUDGET_EXHAUSTED`; never parent `PASS`. |
| `verifier_evidence_paths`, `review_evidence_paths`, `ownership_evidence_path` | Run-scoped evidence references; arrays may be empty only when the candidate disposition explains why the gate was unreachable. |
| `feedback_sha256` | Hash of the final curated feedback that informed the last correction, or null when no correction occurred. |

The parent requires the child process ledger and `lane-result.json` to agree on
lane ID, both source SHAs, plan/command/DOT hashes, `process_run_id`, launch
ordinal, adaptive-attempt reservation records, and terminal timing. This
agreement still supplies only a candidate
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
| `BUDGET(global_deadline)` | The run-wide deadline closed while the lane was active; the parent identity-validated and terminated its process group and preserved partial evidence. |
| `BLOCKED-global-deadline` | The approved lane never started because the run-wide deadline closed; no launch reservation or retry is allowed. |

`FAIL`, `BLOCKED`, `CRASHED`, `BUDGET_EXHAUSTED`,
`BUDGET(global_deadline)`, and `BLOCKED-global-deadline` are not
interchangeable. Their distinct causes determine dependent-lane handling and
the residual report.

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
- the immutable `attractor_runner_argv_prefix` executable/module/source
  identity, `doctor`, required flags, exact provider support/credential, and
  durable run binding remain green;
- process ledgers/evidence resolve beneath approved external `state_root`, and
  lane worktrees resolve beneath approved external `worktree_root`;
- every branch's `poll_wait_seconds`, `branch_nonpoll_steps`,
  `branch_node_count`, and `max_poll_cycles`, plus parent total-step arithmetic,
  match the compiled engine-step contract;
- the aggregate verifier is runnable;
- lane verifiers are present, non-interactive, read-only, and externally
  output-configured;
- the envelope implementation/hash and canonical commands match the plan; and
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
and then mechanically classifies authoritative supervisor status, missing artifacts, stale
identity, and clean terminal results before any integration begins.

## Parent Verification and Integration

For each candidate lane in stable plan order, the parent:

1. validates intent, ledger, ack, and authoritative supervisor result as one
   process-run chain; child evidence remains only a routing hint;
2. requires `normalized_exit_code == 0`, no signal/timeout/cancellation, empty
   child group, valid log hashes, and schema-valid lane evidence; missing result
   or nonzero/signal/timeout remains non-pass even when artifacts exist;
3. resolves the exact candidate commit from Git rather than from prose;
4. confirms the candidate and its integration base descend from
   `execution_source_sha`;
5. runs `CompiledSourceGate` against the candidate tree;
6. creates the clean disposable detached
   `candidate_verification_worktree` at that exact commit;
7. invokes `VerifierExecutionEnvelope(candidate_lane)` there with immutable
   `expected_head_sha`, then records postconditions before separately
   removing/reconciling the worktree;
8. records the cumulative candidate tree delta from `execution_source_sha`,
   subtracts the already-journaled cumulative delta through the exact current
   integration base to isolate this lane's mutation, and checks that isolated
   mutation against `owned_paths`, with compiled source categorically excluded;
9. checks required qualitative evidence, when declared;
10. records the parent verdict;
11. integrates only a `PASS` candidate into the integration branch;
12. invokes `VerifierExecutionEnvelope(aggregate_after_merge)` immediately
    after integration with expected post-merge HEAD; its pre/post
    compiled-source checks satisfy the required post-merge gate.

If candidate integration fails mechanically, or the aggregate envelope returns
`FAIL` with every integrity check green:

- the integration branch returns to the recorded pre-candidate HEAD;
- the failed candidate is not recorded as integrated;
- merge/verifier evidence is attached to the responsible lane;
- the lane re-enters its bounded correction loop from the current integrated
  base; and
- parent verification repeats before another integration attempt.

A compiled-source failure, candidate-verification worktree lifecycle failure,
or envelope `INFRA` bypasses rollback-as-product-correction and routes directly
to `INFRA_FAILURE`; the verifier's apparent result is discarded.

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
`IntegrationCorrection` child Attractor operating directly on the integration
branch under the same accountable supervisor contract. Its input contains the
complete fresh-review artifact, all findings, and the full
`responsible_lane_ids` array. Before the supervisor launch, the parent atomically
reserves both one correction round and one process launch under the same flocked
run-budget transaction. The correction child separately executes
`ReserveGlobalAttempt` before every verification-bearing adaptive correction.

After resolving typed values, every correction child uses this exact closed
argv:

```text
<each token of attractor_runner_argv_prefix>
run
<repo-relative-integration-correction-dot>
--provider
<compiled-provider>
--cwd
.
--logs-root
<absolute state_root/corrections/<correction-id>/runs/<process-launch>/attractor-run>
--on-human-gate
fail
--param correction_id=<validated-correction-id>
--param correction_round_id=<plan-id>/<run-id>/correction/<ordinal>
--param process_run_id=<canonical-correction-process-run-id>
--param correction_state_root=<absolute state_root/corrections/<correction-id>>
--param correction_result_path=<absolute correction-run-root/correction-result.json>
--param findings_path=<absolute external fresh-review artifact>
--param responsible_lane_ids_path=<absolute external canonical JSON>
--param run_budget_ledger_path=<absolute state_root/budgets/run-wide.json>
--param run_budget_lock_path=<absolute state_root/budgets/run-wide.lock>
--param product_base_sha=<full product base SHA>
--param execution_source_sha=<full execution source SHA>
--param runtime_bundle_hash=<full trusted runtime bundle hash>
--param trusted_runtime_binding_path=<absolute trusted-runtime-binding.json>
--param trusted_runtime_argv_prefix_sha256=<full external runtime prefix hash>
--param trusted_supervisor_argv_prefix_sha256=<full external supervisor prefix hash>
--param provider=<compiled-provider>
--param attractor_runner_argv_prefix_sha256=<full prefix hash>
--param aggregate_verifier_definition_sha256=<full aggregate verifier hash>
--param ownership_contract_sha256=<full correction ownership hash>
```

No extra/reordered argv or parameter is accepted. The
`correction_round_id=<plan-id>/<run-id>/correction/<ordinal>` and
`process_run_id` must equal the two live ledger reservations. All generated
child state is external, and the launch contract binds exact
prefix/module/source/provider, trusted-runtime binding/bundle/prefix hashes,
trusted-supervisor prefix/identity,
integration-worktree CWD, correction DOT/hash, environment, budget paths, and
result schema.

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
2. invokes `VerifierExecutionEnvelope(affected_closure_lane)` for every
   affected-closure lane against immutable expected current integration HEAD,
   in static integration order restricted to that closure;
3. rejects any envelope evidence whose expected/pre/post HEAD is not that
   current HEAD;
4. invokes `VerifierExecutionEnvelope(affected_closure_aggregate)` against that
   same expected current HEAD;
5. invokes `VerifierExecutionEnvelope(pre_coherence_aggregate)` against that
   same expected current HEAD;
6. reruns fresh cross-lane coherence review at that exact current HEAD; and
7. repeats only through the one supervised `IntegrationCorrection` loop when
   product evidence is red.

An affected-closure lane envelope `FAIL` with all integrity checks green adds
that lane ID to the next responsible set and routes back to
`IntegrationCorrection`. Envelope `INFRA` routes only to `INFRA_FAILURE`. One
correction round is one supervised integration-correction child launch. Its
reservation becomes `STARTED` after valid supervisor ack and `CONSUMED` when the
authoritative supervisor result becomes terminal, regardless of child success,
failure, signal, timeout, or cancellation. Each internal adaptive attempt still
consumes `max_total_attempts` only through `ReserveGlobalAttempt` and verifier
classification. A correction start/restart therefore requires and charges both
one correction round and one `max_process_launches` unit; it never charges only
the latter.
Exhaustion writes named
`BUDGET_EXHAUSTED(integration_correction:SORTED_LANE_IDS)` residuals with the
last findings, closure, ownership check, verifier logs, and integration HEAD.

### Final lane-verifier sweep

After coherence returns `PASS`, and before delivery eligibility or
`COMPLETE`, `CompiledSourceGate` passes and the graph runs every lane verifier
once more through `VerifierExecutionEnvelope(final_sweep_lane)` against the
exact frozen current integration HEAD in full static integration order. Each
final-sweep envelope is bound to that one SHA,
`product_base_sha`, and `execution_source_sha`.

If any final-sweep lane envelope returns `FAIL` with integrity green, its lane
ID becomes the responsible set for `IntegrationCorrection`; the graph computes
its transitive-dependent closure and re-enters the same bounded correction
loop. Envelope `INFRA` routes only to `INFRA_FAILURE`. After correction the run
must again pass affected-closure verification, the affected-closure aggregate,
the pre-coherence aggregate, coherence review, and the complete final sweep. No
pre-merge, lane-branch, pre-correction, or prior-HEAD verifier evidence can
satisfy completion.

Only after every final-sweep lane is green does
`VerifierExecutionEnvelope(final_aggregate_after_sweep)` run. This is the
machine gate named **`final-aggregate-after-sweep`** in the graph/report. It uses
the same frozen expected HEAD and must finish with identical expected/pre/post
HEAD plus an integrity-preserving aggregate `PASS`. Any `FAIL` routes to
`IntegrationCorrection`; `INFRA` routes only to `INFRA_FAILURE`.

## Pre-Coherence, Final Sweep, and Post-Sweep Aggregate Gates

After all runnable waves finish:

1. `VerifierExecutionEnvelope(pre_coherence_aggregate)` runs at immutable
   expected current integrated HEAD and must return an integrity-preserving
   aggregate `PASS`.
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
   `reviewed_head` to equal the pre-coherence aggregate HEAD, and routes only the exact
   `PASS`, `ITERATE`, or `BLOCKED` verdicts.
6. On coherence `PASS`, the graph freezes that same HEAD, runs the complete
   final all-lane sweep there, then runs `final-aggregate-after-sweep` there.
7. Only a current `CompiledSourceGate` plus those three fresh proof families at
   one exact HEAD may enter source gating and delivery/finalization.

Actionable coherence findings route only to `IntegrationCorrection`, carrying
all responsible lane IDs. They must survive affected-closure lane verification,
the affected-closure aggregate, the pre-coherence aggregate, a fresh coherence
review, the final all-lane verifier sweep, and
`final-aggregate-after-sweep`. If responsibility is ambiguous or correction budget is
exhausted, the finding becomes an evidence-backed residual rather than an
invented pass.

Final coherence review is unreachable until a complete pre-coherence aggregate envelope
and classifier emitted `AGGREGATE_VERIFY:PASS` for the same expected/pre/post
HEAD. A coherence `PASS` therefore cannot mask a red, stale, discarded, or
mutation-tainted mechanical result. `COMPLETE` additionally requires coherence,
the later final sweep, and `final-aggregate-after-sweep` all to be fresh and
bound to the exact final HEAD; a HEAD change invalidates all three.

## Budgets and Exhaustion

### Per-lane budget

Each lane and correction contract declares a local adaptive-attempt budget.
`max_total_attempts` counts only verification-bearing adaptive attempts whose
reservation is consumed when the verifier record is classified. Retries caused
by mechanical failure, qualitative refusal, or reintegration failure consume
only if they reach that verifier-bearing attempt cycle. Merely starting,
restarting, polling, or reaping a child process never counts as an adaptive
attempt.

The lane budget cannot be reset by re-entering from parent integration or
coherence review.

Each child process run also has one wall-clock limit, `max_child_seconds`, enforced by
the deterministic process supervisor across the entire child Attractor run.
That wall is a safety bound, not evidence of completion. When it fires, the
supervisor performs TERM -> grace -> KILL against the verified child process
group; the reaper persists authoritative timeout/wait status, and the parent classifies the
lane `CRASHED` or `BUDGET_EXHAUSTED` according to whether trustworthy
lane-attempt evidence exists.

### Run-wide budget

The parent mints an external run-wide budget ledger at
`state_root/budgets/run-wide.json` with schema
`goal-plan.run-budget/v3`. Every read-modify-write by the parent or any
`ReserveGlobalAttempt` node opens the dedicated
`state_root/budgets/run-wide.lock`, holds `fcntl.flock(LOCK_EX)`, rereads and
validates the current ledger, writes a same-directory temporary file, fsyncs,
atomically replaces the ledger, fsyncs the directory, and only then releases
the lock.

The ledger contains:

| Field | Contract |
|---|---|
| `schema_version` | Exact value `goal-plan.run-budget/v3`. |
| `plan_id`, `run_id`, `product_base_sha`, `execution_source_sha`, `provider`, `attractor_runner_argv_prefix_sha256`, `trusted_runtime_binding_sha256`, `runtime_bundle_hash`, `trusted_runtime_argv_prefix_sha256`, `trusted_supervisor_argv_prefix_sha256` | Exact immutable run, child-runner, external binding, safety-runtime, and external supervisor identities. |
| `boot_id` | Exact Linux boot ID at run admission. |
| `started_at_boottime`, `deadline_boottime` | `CLOCK_BOOTTIME` values captured with `clock_gettime`; deadline equals start plus `max_pipeline_seconds`. |
| `max_pipeline_seconds`, `max_total_attempts`, `max_process_launches`, `max_integration_corrections` | Exact positive compiled limits. `max_total_attempts` excludes all process launches. |
| `reserved_attempts`, `started_attempts`, `consumed_attempts` | Non-negative adaptive-attempt counts derived only from attempt-reservation records. |
| `reserved_process_launches`, `consumed_process_launches` | Non-negative process-start/restart counts derived only from process-launch records. |
| `active_reserved_corrections`, `consumed_corrections` | Non-negative correction-round counts derived only from correction-reservation records. `active_reserved_corrections` includes `RESERVED` and `STARTED`; `consumed_corrections` includes only `CONSUMED`. |
| `active_process_run_ids` | Sorted unique process-run IDs with consumed process launches not yet terminal. |
| `attempt_reservations` | Map keyed by canonical reservation ID to lane/correction ID, process-run ID, local attempt, verifier definition hash, timestamps, start/classification evidence, and exact state. |
| `process_launch_reservations` | Map keyed by canonical launch-reservation ID to process kind/ID, process-run ID, process-launch ordinal, timestamps, procfs/intent evidence, and exact state. |
| `correction_reservations` | Map keyed by exact `correction_round_id=<plan-id>/<run-id>/correction/<ordinal>` to ordinal, correction/process IDs, exact `process_run_id`, responsible-set/affected-closure evidence hashes, process-launch reservation ID, supervisor ack/result evidence, transition boottimes, and exact `RESERVED`, `STARTED`, `CONSUMED`, or `RELEASED` state. |
| `closed`, `closed_reason`, `closed_at_boottime` | Run-wide no-further-work wall. |

Admission records `boot_id = /proc/sys/kernel/random/boot_id`,
`started_at_boottime = clock_gettime(CLOCK_BOOTTIME)`, and the immutable
deadline. A boot-ID mismatch, unreadable `CLOCK_BOOTTIME`, decreasing boottime,
or deadline/limit mismatch is `INFRA_FAILURE`, never ordinary exhaustion.

#### Process-launch reservation and exactly-once accounting

Before every initial supervisor start or restart for a lane, correction, or
delivery child, the parent acquires the budget lock and checks:

1. the ledger is not closed;
2. boot ID still matches;
3. current `CLOCK_BOOTTIME` is strictly before the deadline; and
4. `consumed_process_launches + reserved_process_launches + 1 <=
   max_process_launches`.

If green, it creates one `RESERVED` process-launch record binding process
kind/ID, canonical `process_run_id`, process-launch ordinal, runner prefix hash,
provider, launch-contract hash, and boottime. That reservation ID is copied into
`launch-intent.json` and `launch-contract.json`. No `Popen` or replacement
start occurs without it. For `process_kind: "correction"`, these checks and the
process-launch record occur in the same atomic flock transaction as the required
correction-round reservation below; a correction may not reserve either unit
alone.

A process-launch reservation becomes `CONSUMED` exactly once when procfs/ack
evidence proves the supervisor or child process was created, or
`RELEASED_NO_PROCESS` only when reconciliation proves neither process ever
started. A consumed run is added to `active_process_run_ids`; terminal
poll/reconcile/termination removes it exactly once. Duplicate identical
transition is idempotent; a conflict is `INFRA_FAILURE`. Exhausting
`max_process_launches` cannot borrow from `max_total_attempts`.

#### Correction-round reservation and exactly-once accounting

One correction round means exactly one supervised integration-correction child
launch, including a replacement launch after a prior correction supervisor
failed. Before any correction supervisor `Popen`, the parent acquires the same
exclusive flock and atomically creates both the process-launch reservation and
one correction reservation only when:

1. the ledger is open and all immutable run, child-runner, and
   supervisor-runner identities match;
2. boot ID is unchanged and current `CLOCK_BOOTTIME` is strictly before the
   global deadline;
3. `consumed_corrections + active_reserved_corrections <
   max_integration_corrections`; and
4. the process-launch ceiling also admits the launch.

If any check fails, neither reservation is written. The correction key is
exactly
`correction_round_id=<plan-id>/<run-id>/correction/<ordinal>`, where `ordinal`
is the next positive compiled DOT ordinal, and the record binds the exact
correction `process_run_id`. The same IDs are copied into intent, launch
contract, ack, supervisor result, correction result, and parent journal.

The correction state machine is normative:

- `RESERVED` is durable before the supervisor launch.
- `STARTED` is written only after a schema-valid, identity-valid supervisor ack
  for the bound `process_run_id`.
- `CONSUMED` is written on the authoritative supervisor terminal result,
  regardless of success, nonzero exit, signal, timeout, cancellation, or
  infrastructure verdict.
- `RELEASED` is legal only while `RESERVED` and only when bounded reconciliation
  proves the supervisor launch never occurred. No `STARTED` or `CONSUMED`
  record can be released.

Every transition occurs under the flock. Repeating an identical transition with
identical evidence is idempotent; a changed process ID, ordinal, ack/result
hash, prior state, or terminal value is `INFRA_FAILURE`. A parent crash after
`STARTED` consumes the round conservatively: reconciliation obtains or drives
the identity-valid supervisor to an authoritative terminal result, then writes
`CONSUMED`. A `RESERVED` record abandoned without ack is released only after
the same bounded procfs/intent/ledger scan proves no launch occurred. If launch
may have occurred but no trustworthy ack/result can be recovered, the
reservation remains active, the run closes as `INFRA_FAILURE`, and the terminal
residual records that the correction capacity is unavailable; it is never
refunded or reused.

The parent reconciles correction reservations before admitting another
correction. Reaching
`consumed_corrections + active_reserved_corrections ==
max_integration_corrections` emits
`BUDGET_EXHAUSTED(integration_correction:SORTED_LANE_IDS)` with the ordered
correction IDs, process-run IDs, states, findings, closure, last trustworthy
supervisor/verifier evidence, and retained integration HEAD. No later restart,
coherence loop, or final-sweep failure may allocate another ordinal.

#### Adaptive-attempt reservation through `ReserveGlobalAttempt`

Immediately before every adaptive `Attempt` in every lane or correction child,
`ReserveGlobalAttempt` acquires the same flock and checks:

1. the ledger is not closed and immutable identity/provider/prefix values match;
2. boot ID and `CLOCK_BOOTTIME` are valid and before deadline;
3. the local attempt number is within the child's `max_attempts`;
4. `consumed_attempts + started_attempts + reserved_attempts + 1 <=
   max_total_attempts`.

It creates or idempotently reuses one `RESERVED` record keyed by canonical
serialization of lane/correction ID, `process_run_id`, positive local attempt,
and verifier-definition SHA-256. A different value reusing any tuple component
is `INFRA_FAILURE`. Immediately before model work, `MarkAttemptStarted`
transitions the record to `STARTED`. When the deterministic verifier record is
complete, `ClassifyVerifierAndConsumeGlobalAttempt` validates its schema,
verifier hash, subject/process/local-attempt tuple, path, content hash, and
verdict, then transitions the reservation to `CONSUMED` exactly once.

Crash reconciliation is conservative. A `RESERVED` record becomes
`RELEASED_NO_ATTEMPT` only when durable child-node state, supervisor result,
logs, and verifier state prove `MarkAttemptStarted` never occurred. Any start
marker, model-side effect, verifier start, or ambiguity causes a synthetic
`CRASHED` verifier-classification record and `CONSUMED`; the ceiling is not
refunded. A classified reservation can never be released. Only the brief ledger
transaction is serialized; parallel adaptive work and verifier execution never
hold the lock.

#### Deadline wall

The parent and each `ReserveGlobalAttempt` check boot identity and deadline
before every reservation; supervisor `poll` checks them before and after its
bounded long-poll. When
`CLOCK_BOOTTIME >= deadline_boottime`, one locked transition sets
`closed = true`, `closed_reason = "global_deadline"`, and permanently forbids
new process-launch, correction-round, or adaptive-attempt reservations.

The parent then enumerates the ledger's active process-run IDs. For each, it
calls the `terminate` control client with reason `global_deadline` after
full identity validation. Every active lane becomes
`BUDGET(global_deadline)`; every approved but unstarted lane whose work cannot
run becomes exact `BLOCKED-global-deadline`; an active correction records named
integration-correction budget exhaustion; and an active/unstarted delivery
records `BUDGET_EXHAUSTED(delivery:global_deadline)` and cannot emit
`COMPLETE`. Existing passing evidence is preserved. Termination/evidence
failures remain `INFRA_FAILURE`. The parent
records residuals and continues only to terminal classification. No restart,
new wave, reintegration, correction, or delivery retry can reopen the ledger.

The run-wide ledger and all three reservation maps are reconciled before process
ledgers on restart. It is the authoritative source for process-launch,
adaptive-attempt, correction, and deadline admission, not in-memory counters.
Neither ceiling is replenished by moving waves, aggregate failure, coherence
correction, restart, or delivery.

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
named terminal residuals for the responsible set and affected closure. The
residual binds the exact limit, `consumed_corrections`,
`active_reserved_corrections`, every correction-round/process-run state and
evidence path, last findings/verifier/supervisor evidence, and retained
integration HEAD. It never restores or resumes old lane branches and can never
route to `COMPLETE`.

`max_process_launches` exhaustion records
`BUDGET_EXHAUSTED(process_launches:PROCESS_KIND:PROCESS_ID)` for any child that
cannot be started/restarted, blocks dependents by name, and prevents delivery
when the required delivery child cannot launch. It is not silently converted to
an adaptive-attempt exhaustion and cannot be increased by releasing or
reclassifying attempt reservations.

## Human Gates

### Plan approval

The only pre-mutation gate presents:

- the full lane/dependency graph;
- `product_base_sha`, admitted `execution_source_sha`, their ancestry, and the
  known compiled-plan delta between them;
- the compiled-source manifest hash;
- ownership and collision analysis;
- lane and aggregate verifiers plus the shared envelope hash, canonical
  HEAD/status commands, read-only policy, and external output roots;
- child DOT/launch hashes, lane wall limits, and process-supervision policy;
- budgets;
- planned integration order; and
- delivery intent.

Before approval, only external `state_root` may be created or written. The
target repository, Git common directory, refs, branches, registered worktrees,
external `worktree_root`, and `delivery_state_root` remain untouched. An
invocation may carry explicit
preapproval, but the graph must still render and persist the same plan,
root-safety proof, and admission evidence externally before mutation.

`preapproved` is a valid unattended headless standalone mode. It bypasses the
interactive decision only after the same immutable admission/render packet is
durable; it does not bypass any source, budget, runner, provider, or verifier
gate. The canonical smoke uses `approval_mode=preapproved`,
`human_gate_transport=none`, and runner `--on-human-gate fail`.

`approval_mode=required` is valid only for a standalone parent invocation with
exact `human_gate_transport=console`, exact runner flag
`--on-human-gate console`, `isatty(stdin) == true`, and an attached `/dev/tty`
that admission can open for both reading and writing. Admission persists the
parent argv, TTY device identity, `isatty` result, and open-mode evidence before
mutation. It rejects `required` with unattended execution, hosted headless
execution, absent/closed/non-TTY console input, or `--on-human-gate fail`.
Lane, correction, and delivery children always use `--on-human-gate fail`; only
the attached standalone parent plan gate may interview a person.

Programmatic host-based interviewing is future separate work. It is not an open
question, transport enum, capability hook, or current v1 interface.

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
automatically delivered. If any worktree must remain for residual inspection,
the gate must name its exact run-owned registry entry, residual ID, reason,
evidence paths, expected current identity, and identity-safe recovery/removal
commands in the residual-preservation manifest. With current
`mutation_authority: "FULL"`, `PreTerminalCleanup` preserves only those named
entries as `PRESERVED_RESIDUAL` and cleans every other run-owned worktree.
Selecting no preserved worktrees is valid and still yields `RESIDUALS_READY`
after all entries are removed. `EXTERNAL_ONLY` cannot establish this terminal:
it leaves every worktree untouched and finalizes `INFRA_FAILURE`. An operator
stop after repository mutation remains an evidence-backed residual disposition;
`ABORTED` is reserved for rejection or cancellation before mutation.

There are no routine gates between waves.

## Durable State and Crash Recovery

Recovery is a graph pattern, not an assumption about engine checkpoints. Every
initial start and resume first validates or exact-blob rehydrates the external
trusted-runtime binding, enters recovery only through
`trusted_runtime_argv_prefix`, then satisfies the parent target-repository
binding and persists its immutable invocation record before deterministic
reconciliation.

### Durable state

The run persists:

- approved plan snapshot/hash and preapproval/approval evidence;
- exact trusted-runtime definition/hash, runtime-bundle hash, external bundle
  directory, versioned `trusted-runtime-binding.json` path/hash/content,
  runtime/supervisor source path/blob/mode/length/hash entries, external
  file/interpreter/Git executable path/realpath/mode/hash entries, exact
  runtime/supervisor prefix tokens/hashes, materialization command evidence,
  fsync/atomic-rename/chmod/reread evidence, and creation timestamp;
- compiled-pipeline path, embedded `plan_sha256`, typed runtime inputs,
  immutable `attractor_runner_argv_prefix`/identity/hash,
  append-only parent-runner invocation records with exact argv/prefix/provider,
  `/proc/self/cwd`, runner-resolved `--cwd .`, canonical `target_repo`, parent
  DOT path/observed/execution-source/manifest hashes, parent process identity,
  `execution_source_sha`, and exact parent logs root,
  `trusted_runtime_argv_prefix` and
  `trusted_supervisor_argv_prefix`/identity/hash/CLI/schema/self-check evidence,
  compiled `provider`, provider credential preflight, doctor/flag evidence, and engine-step budget,
  selected target-repository identity mode and its remote-match or
  history-anchor proof, exact `product_base_sha`, exact
  `execution_source_sha`, their ancestry proof, and the separated compiled-plan
  and lane-produced delta ranges;
- canonical external `state_root`, `worktree_root`, and conditional
  `delivery_state_root`, root-safety evidence, XDG/default derivation evidence,
  approval mode/transport, and approval boundary;
- atomic `run-owned-worktrees.json` with every lane, integration,
  candidate-verification, and delivery entry's kind, lane/process ID, canonical
  path, expected branch or detached SHA, Git common directory, creation
  evidence, and lifecycle transition;
- admission compiled-source manifest path/hash and every subsequent
  `CompiledSourceGate` record;
- flock-protected run-wide budget ledger, boot/deadline binding, separate
  process-launch, correction-round, and adaptive-attempt reservation
  transitions, verifier-bound exact-once consumption, active process-run IDs,
  and deadline closure evidence;
- run-wide process-launch/adaptive-attempt/correction counters and per-lane
  adaptive counters;
- the exact worktree/branch/base/head projection derived from
  `run-owned-worktrees.json`, never an independent looser mapping;
- per-lane/correction/delivery launch intent/contract, provisional supervisor PID, ledger, ack,
  poll/termination/reconciliation records, and authoritative supervisor result,
  including supervisor/child procfs identities, raw wait status, normalized
  exit/signal/timeout/cancellation, group cleanup, log hashes,
  process-launch/correction-round reservations, `process_run_id`, child- and
  supervisor-runner/provider bindings, and optional box-session IDs;
- lane contracts, evidence, and dispositions;
- parent-verification records, including detached candidate SHA/path,
  verifier/envelope hashes, complete envelope evidence, and
  removal/reconciliation proof;
- every `goal-plan.verifier-envelope/v2` record, including immutable expected
  HEAD, pre/post porcelain-v2 status, complete worktree manifests including
  ignored paths, compiled-source evidence, output-root environment/manifest,
  verifier outputs, and final envelope verdict;
- integration journal whose every entry binds `product_base_sha`,
  `execution_source_sha`, candidate SHA, and pre-merge/post-merge HEADs;
- integration-correction journal with each
  `correction_round_id`/`process_run_id`, correction
  RESERVED/STARTED/CONSUMED/RELEASED transition evidence, child/process launch,
  adaptive attempt reservation/classification, responsible set, affected
  closure, allowed write set, both source SHAs, compiled-source-gate evidence,
  evidence invalidations, commit, and budget count;
- aggregate-verifier records after each merge and affected closure;
- pre-coherence aggregate and versioned fresh-review records at exact HEAD;
- final-sweep lane-verifier records bound to final integration HEAD;
- `final-aggregate-after-sweep` record bound to that same final HEAD;
- terminal classification;
- `PreTerminalCleanup` intent, invocation, fresh
  `trusted_runtime_binding_verdict`, `parent_binding_verdict`,
  target/source-identity and compiled-source verdicts, `mutation_authority`,
  gate evidence paths/hashes, permitted actions, attempted actions, skipped Git
  actions, bounded process reconciliation,
  residual-preservation manifest, cleanup journal, final registry/filesystem/Git
  worktree-list projection, unresolved infrastructure resources, final cleanup
  verdict, chosen final status, and evidence hash;
- versioned `result.json`; and
- the versioned delivery-attempt ledger, external `delivery_state_root`,
  disposable delivery-worktree lifecycle and pre/post envelope, supervised
  delivery-child process records, branch, expected head, PR URL, observed remote
  head, and independent verification result.

State writes must be atomic. Human-readable reports are derived from structured
state; they are not the source of truth.

### Reconciliation rules

On restart, the graph compares state with reality:

Before opening any current target-repository runtime/supervisor script, the
launcher validates the external trusted-runtime binding from durable
`state_root`. If the exact bundle directory is absent, it may run only the
deterministic closed-argv rehydration procedure from the durable approved plan
snapshot and exact Git blobs at `execution_source_sha`. It never executes or
materializes from current working-copy runtime bytes. A present mismatching
bundle, or rehydration that cannot prove the exact blob, Git executable,
interpreter, permission, fsync, and final binding identities, stops as
infrastructure-blocked before the parent graph; no cleanup/finalizer completion
is claimed.

Only after the external binding is green does the launcher change into the
durable canonical `target_repo`, `exec` the parent, and invoke recovery through
exact `trusted_runtime_argv_prefix`. The new parent invocation reruns
`TrustedRuntimeBindingGate`, `ParentRunnerBindingGate`, target/source-identity
proof, and `CompiledSourceGate`, appends a hash-chained invocation record, and
matches the original trusted-runtime/prefix/provider/CWD/DOT/hash/logs/source
bindings. Only a current all-green set grants
`mutation_authority: "FULL"`. A green trusted runtime plus red/unknown
repository/source gate grants `EXTERNAL_ONLY`: recovery may write only below
external `state_root` and may terminate only a fully
procfs-identity-validated supervisor/child process group. It performs no
target-repository-file, ref, branch, Git-registration, worktree-path, or
Git-common-directory mutation. A red/unknown trusted runtime grants `NONE` and
no recovery action starts, except the separately validated supervisor-only
termination rule.

1. Re-resolve `state_root`, `worktree_root`, and conditional
   `delivery_state_root`, reject symlink drift, and require equality with the
   durable run binding. While approval is not yet restored, reapply the strict
   pre-approval overlap rules and write only under `state_root`.
2. After approval is restored, load and hash
   `state_root/run-owned-worktrees.json`; enumerate both the complete filesystem
   beneath `worktree_root` and `git worktree list --porcelain`; and require an
   exact bijection among non-`REMOVED` registry entries, canonical paths, Git
   registrations, expected Git common directory, expected branch/null-detached
   state and exact HEAD SHA, and lifecycle/creation evidence. Any unrecorded or foreign descendant,
   any recorded worktree outside `worktree_root`, any missing registration, or
   any wrong SHA/branch/common directory is `INFRA_FAILURE`, except the exact
   proven `CREATING`/`REMOVING` recovery transitions defined above. Recovery
   does not reapply the pre-approval blanket prohibition to this exact allowlist.
3. Reconcile the flock-protected run-wide budget ledger first. Require matching
   boot ID, monotonic `CLOCK_BOOTTIME`, all four limits, deadline, separate
   process-launch/correction-round/adaptive-attempt counts, and active process-run
   IDs.
4. Reconcile each process-launch reservation exactly once. Release only a
   `RESERVED` record proven never to have created a process; otherwise consume
   it and preserve/recover the bound process run. Never charge a process launch
   to `max_total_attempts`.
5. Reconcile each correction reservation by exact
   `correction_round_id`, ordinal, and `process_run_id`. Release a `RESERVED`
   record only when bounded process evidence proves launch never occurred;
   transition valid ack to `STARTED`; transition authoritative terminal result
   to `CONSUMED` regardless verdict; and conservatively consume after a crash
   from `STARTED`. A possibly launched but unrecoverable pre-ack reservation
   remains active and closes the run as `INFRA_FAILURE`; it is never reused.
6. Reconcile each adaptive-attempt reservation by its lane/correction ID,
   `process_run_id`, local attempt, and verifier hash. Release only when no
   attempt-start evidence exists; consume a started/classified attempt exactly
   once, using a synthetic crash classification when it started but lacks a
   complete verifier record.
7. Through exact external `trusted_runtime_argv_prefix`, rerun admission against
   immutable `plan.json` and embedded `plan_sha256`,
   including graph/plan correspondence, child-runner identity/doctor/flags,
   trusted runtime/supervisor prefix/executable/interpreter/external-script/
   environment identity, binding permissions/hashes, non-mutating self-check,
   exact CLI/schema/subcommand support, provider/credential, approval transport,
   and engine-step arithmetic. Every runner prefix and bound
   identity/hash/version must equal durable state; mismatch is
   `INFRA_FAILURE`, and resume cannot change them. Current target-repository
   runtime scripts are never executed, even when source binding is red.
8. Re-prove the selected target-repository identity policy, source
   SHAs/ancestry, and compiled-source manifest.
9. Run `CompiledSourceGate` against the execution source and every exact
   run-owned lane, candidate, integration, and delivery worktree. Any mismatch
   is immediate `INFRA_FAILURE`.
10. Reconcile any disposable candidate-verification worktree left by a crash
    through its exact `candidate` registry entry. Require recorded candidate
    SHA/path, detached HEAD, Git registration/common directory, and empty output
    from the canonical full non-ignored status command; dirty, wrong, foreign,
    or unremovable state is `INFRA_FAILURE`. Mark `REMOVING`, remove without
    force, prove path/registration absence, then mark `REMOVED`. Restart
    verification from worktree creation only when no envelope invocation began.
11. For every intent missing ledger/ack, invoke exact
    `trusted_supervisor_argv_prefix + reconcile suffix`. Its bounded `/proc`
    discovery adopts exactly one identity-valid live supervisor and consumes
    its process-launch reservation; an identity-valid orphan child is
    terminated and becomes `INFRA_FAILURE`; zero matches releases only a proven
    never-started process-launch reservation and corresponding correction
    reservation; multiple/ambiguous matches are never signalled and are
    `INFRA_FAILURE`.
12. For every acknowledged nonterminal run, invoke exact
    `trusted_supervisor_argv_prefix + poll suffix` with `--wait-seconds 30` and
    validate both identities before and after its bounded wait. At or beyond
    deadline, close the budget ledger first and invoke exact prefix plus
    `terminate --reason global_deadline` for every active process-run ID.
13. If the supervisor disappears before a complete authoritative result,
    immediately terminate any identity-valid live child group and classify
    `INFRA_FAILURE`; child absence/evidence never means success.
14. Resolve recorded commits directly from Git and require every work commit and
    current integration HEAD to descend from `execution_source_sha`.
15. Reclassify a purported completed lane whose artifact or commit is missing as
    `CRASHED` or `INFRA_FAILURE`, depending on whether lane work or substrate is
    untrustworthy.
16. Require every supervisor result to match intent/ledger, process-launch and
    correction-round reservations, both immutable runner bindings, provider, and
    real child exit. Nonzero exit, signal, timeout, cancellation, missing
    result, or child-only evidence cannot become `PASS`.
17. Reconcile every verifier envelope against immutable expected HEAD,
    verifier/envelope hashes, exact output-root interface/environment, output
    containment manifest, pre/post porcelain-v2 status, complete
    tracked/untracked/ignored filesystem manifests, and compiled-source
    evidence. Missing/red/incomplete evidence is `INFRA_FAILURE`.
18. Start pre-integration parent verification through a newly registered clean
    candidate worktree only when no envelope invocation was durably started.
    Once it starts, missing/incomplete postconditions follow rule 17 only.
19. Reconcile the integration journal against actual HEAD and Git ancestry
    before another merge. Recompute every correction's affected closure from
    the static DAG and enforce all recorded invalidations.
20. Before starting or restarting a correction child, atomically reserve one
    statically named correction round and one process launch. Its child graph
    performs `ReserveGlobalAttempt` immediately before each adaptive attempt; no
    parent restart may pre-consume an adaptive attempt or omit a new correction
    round.
21. If a correction commit exists but proof is incomplete, run
    `CompiledSourceGate`, affected-closure lane envelopes,
    `affected_closure_aggregate`, and `pre_coherence_aggregate` at current HEAD
    before coherence. Do not rerun the correction worker.
22. Invoke a new aggregate envelope only when the integration worktree is
    independently clean at the intended HEAD and lacks a completed bound record.
23. Reject a fresh-review artifact whose source SHAs differ or whose
    `reviewed_head` does not equal actual HEAD.
24. Restore completion eligibility only when one exact actual integration HEAD
    has fresh passing coherence evidence, a complete all-lane final sweep,
    `final-aggregate-after-sweep`, and a current compiled-source pass.
25. Reconcile any delivery worktree through its exact `delivery` registry entry,
    pre/post HEAD, full status, complete non-`.git` filesystem manifests, and
    source gates. Dirty, wrong-HEAD, foreign, state-bearing, or unremovable
    worktrees are `INFRA_FAILURE`.
26. Reconcile every delivery process through the same process-launch/supervisor
    rules and exact child-runner/supervisor-runner/provider binding. No generated
    `.resolve` or other delivery state in the delivery worktree is accepted.
27. Reconcile the external delivery ledger, then independently query remote PR
    state at its exact expected head if delivery may already have occurred;
    never open a duplicate merely because local state is incomplete.
28. If a durable intended-status or partial `PreTerminalCleanup` journal exists
    but no valid `result.json` exists, validate the external binding and resume
    only `PreTerminalCleanup` through exact `trusted_runtime_argv_prefix`. Every
    retry creates a new cleanup-attempt record and recomputes current
    `TrustedRuntimeBindingGate`, `ParentRunnerBindingGate`,
    target/source-identity, and `CompiledSourceGate` evidence before any action.
    A prior
    `mutation_authority: "FULL"` is historical evidence only and is rejected
    when the current gate set is red or unknown. Current `FULL` may
    idempotently finish exact process and Git lifecycle transitions; current
    `EXTERNAL_ONLY` may finish external evidence and fully
    procfs-identity-validated process termination only, records every Git action
    as skipped, leaves worktrees/refs/registrations unresolved, and chooses
    `INFRA_FAILURE`. Current `NONE` starts no cleanup/finalizer and claims no
    completion. Do not re-enter product work or delivery.
29. If valid durable terminal `result.json`, `goal_plan.status`, and terminal
    token evidence exist, verify they match the cleanup record's chosen status,
    `trusted_runtime_binding_verdict`, `parent_binding_verdict`,
    `mutation_authority`, current-gate evidence hashes, and cleanup verdict, and
    perform no post-terminal cleanup or repository mutation. If matching CLI
    carrier evidence is absent, revalidate the binding and resume only the
    idempotent carrier outcome from that final status; do not rewrite
    result/status/token or rerun cleanup. A mismatch is an externally reported
    infrastructure inconsistency, never a reason to rewrite a prior `COMPLETE`
    in place.

Reconciliation is idempotent. It skips work only when durable evidence and real
state agree. Ambiguous or contradictory infrastructure state fails loudly as
`INFRA_FAILURE`.

## Terminal and Failure Behavior

| Terminal | Required condition | Delivery behavior |
|---|---|---|
| `COMPLETE` | Both source SHAs, the immutable external trusted-runtime/parent/child/supervisor bindings, provider, and current parent invocation remain bound; all product and delivery proof is green at one exact final HEAD; and externally invoked `PreTerminalCleanup` records `mutation_authority: "FULL"`, proves no live supervisor/child process group or foreign path, and marks every run-owned lane/candidate/delivery/integration worktree and Git registration `REMOVED`. | May auto-deliver one PR before cleanup/finalization. |
| `RESIDUALS_READY` | All lanes are terminal or dependency-blocked and every residual has evidence. Under current `FULL` authority, `PreTerminalCleanup` proves no live process group, marks only explicitly named residual worktrees `PRESERVED_RESIDUAL` with evidence/recovery commands, removes every other run-owned worktree/registration, and finds no unidentified or foreign path. | Never auto-delivers; requires residual disposition. |
| `INFRA_FAILURE` | Any external-root/approval boundary, trusted-runtime/parent/child/supervisor runner binding, source/compiled identity, accounting, process, Git/worktree, verifier, delivery, cleanup, or recovery state cannot be trusted. With a green trusted-runtime binding, `PreTerminalCleanup` records `FULL` or `EXTERNAL_ONLY`, performs only bounded actions that authority permits, and names every unresolved resource. Red/unknown parent, target/source, or compiled-source binding yields `EXTERNAL_ONLY` and leaves all Git/repository resources untouched. Red/unknown trusted runtime yields `NONE`; the launcher reports infrastructure-blocked without claiming cleanup/finalizer completion. | No delivery. |
| `ABORTED` | The plan was rejected or cancelled before mutation, current cleanup authority is `FULL`, and `PreTerminalCleanup` proves no run-owned process, worktree, Git registration, `worktree_root`, or `delivery_state_root` mutation exists. A red/unknown binding yields `INFRA_FAILURE`, not `ABORTED`. | No delivery. |

### `PreTerminalCleanup` and durable finalizer machine contract

Every intended terminal route first enters the explicit deterministic
`PreTerminalCleanup` phase. The phase runs after the final
cleanup-authority decision, before durable terminal finalization, and before any
terminal token, `goal_plan.status`, `result.json`, or CLI carrier outcome is
published.

Every cleanup attempt freshly recomputes and durably hashes:

1. `TrustedRuntimeBindingGate`, including the binding path/schema/hash,
   runtime-bundle hash, external runtime/supervisor path/type/mode/uid/gid/
   length/hash, interpreter/Git executable path/realpath/mode/hash, and exact
   runtime/supervisor prefix hashes;
2. `ParentRunnerBindingGate`, including the current parent procfs/CWD,
   runner/DOT/argv/provider/logs-root, and invocation-record binding;
3. target/source identity, including canonical target Git top-level/common
   directory, selected remote/history-anchor proof, `product_base_sha`,
   `execution_source_sha`, ancestry, and containing-commit binding; and
4. `CompiledSourceGate` against the execution source and every current
   non-`REMOVED` run-owned worktree that still exists.

The command cannot start unless item 1 is `PASS`. The checks remain
dependency-ordered. A red/unknown parent-runner gate prevents
target-bound downstream gate execution; each blocked current verdict is
recorded `UNKNOWN` with its prerequisite evidence rather than bypassing the red
gate.

The cleanup record's required `trusted_runtime_binding_verdict` is exact `PASS`
for the invocation. The required `parent_binding_verdict` is exactly `PASS`,
`RED`, or `UNKNOWN` for item 2. Separate
`target_source_binding_verdict` and `compiled_source_verdict` fields use the
same enum. Missing, unreadable, stale, or incomplete current evidence is
`UNKNOWN`, never a reason to trust a prior pass.

The required `mutation_authority` is derived, not supplied:

- `FULL` only when all four current verdicts are exactly `PASS`. It permits
  the bounded, identity-matched status-specific Git worktree/ref/registration
  actions below.
- `EXTERNAL_ONLY` only while `trusted_runtime_binding_verdict == PASS` and any
  parent/target-source/compiled-source verdict is `RED` or `UNKNOWN`. It may
  write only external state/evidence and may terminate only supervisor/child
  process groups whose complete canonical procfs identity matches durable
  process evidence. It must not modify target-repository files, refs, branches,
  Git registrations, worktree paths, or Git common-directory state. Every
  run-owned or foreign worktree remains untouched and is recorded as unresolved
  external evidence. The chosen final status is always `INFRA_FAILURE`.
- `NONE` when trusted-runtime validation is `RED` or `UNKNOWN` before
  invocation, or becomes red during the attempt. It permits no Git mutation,
  general signalling, cleanup publication, or terminal finalizer. Only the
  separately still-valid trusted-supervisor termination exception may stop one
  exact identity-valid process group. The launcher records
  infrastructure-blocked evidence and makes no completion claim.

No prior cleanup record, lifecycle state, or prior `FULL`/`EXTERNAL_ONLY`
authority can satisfy this decision. A later retry with a freshly green
trusted-runtime binding and all-green repository/source gate set may receive
`FULL`; a current red/unknown set never does.

The DOT invokes only the external pinned runtime with this exact ordered
command:

```text
<each token of trusted_runtime_argv_prefix>
pre-terminal-cleanup
--trusted-runtime-binding <absolute-state-root>/trusted-runtime/<runtime-bundle-hash>/trusted-runtime-binding.json
--target-repo <canonical-target-repo>
--execution-source-sha <full-execution-source-sha>
--state-root <absolute-state-root>
--worktree-root <absolute-worktree-root>
--run-owned-worktrees <absolute-state-root/run-owned-worktrees.json>
--cleanup-attempt <positive-decimal>
--gate-evidence-root <absolute-state-root/cleanup/gates/CLEANUP_ATTEMPT>
--intended-status <COMPLETE|RESIDUALS_READY|INFRA_FAILURE|ABORTED>
--output <absolute-state-root/cleanup/attempts/CLEANUP_ATTEMPT.json>
```

For intended `RESIDUALS_READY`, exact
`--residual-manifest
<absolute-state-root/cleanup/residual-preservation.json>` is appended after
`--intended-status` and before `--output`; that option is forbidden for every
other intended status. The command rejects reordered, missing, extra, relative,
or hash-unbound arguments. It does not accept `--mutation-authority`; the
runtime derives authority only from the current attempt's new gate records
beneath `--gate-evidence-root`. Its script/interpreter identity, suffix schemas,
evidence schema `goal-plan.pre-terminal-cleanup/v2`, and token map are part of
`plan.json.pre_terminal_cleanup`. Each attempt output is immutable once
atomically published; the finalizer consumes the highest current attempt whose
ordinal, gate paths/hashes, authority, and journal predecessor hash all validate.
No cleanup or finalization route contains the target-repository
`goal_plan_runtime.py` path.

The status-specific cleanup rules are normative. Every Git/worktree action in
these rules is reachable only with `mutation_authority: "FULL"`:

- **Intended `COMPLETE`:** reconcile every process-launch intent, ledger, ack,
  and result; request termination only through the immutable supervisor control
  client for a still-live fully identity-valid supervisor; verify every
  supervisor is terminal and every child process group is empty; mark each
  clean run-owned lane, candidate, delivery, and integration worktree
  `REMOVING`; remove it without `--force`; prune/reconcile exact Git worktree
  registrations; prove path and registration absence; and mark every mapping
  entry `REMOVED`. The final filesystem/registry/worktree-list projection must
  contain no foreign path. Any stop, group-empty, cleanliness, removal, prune,
  mapping, or foreign-path failure changes the chosen final status to
  `INFRA_FAILURE` before finalization.
- **Intended `ABORTED`:** this route is legal only before repository mutation.
  Prove there is no process intent/ledger/ack, no live run process, no
  run-owned registry entry or worktree, no Git registration, and no created
  `worktree_root` or `delivery_state_root`. Any mismatch chooses
  `INFRA_FAILURE`; it is never explained away as cancellation.
- **Intended `RESIDUALS_READY`:** reconcile all processes to terminal and prove
  no live process group. Preserve only registry entries explicitly named in the
  durable residual manifest, mark each `PRESERVED_RESIDUAL`, and bind its exact
  residual ID, path/registration/HEAD/status evidence, reason, and
  identity-safe recovery/removal commands. Clean every other run-owned
  worktree exactly as on the complete path. Preservation is an intentional,
  gating terminal state, not a cleanup fault. Any unidentified or foreign path,
  dirty non-residual worktree, non-residual removal/prune failure, or mismatch
  between manifest and registry chooses `INFRA_FAILURE`.
- **Intended `INFRA_FAILURE` with `FULL`:** perform bounded best-effort cleanup.
  Reconcile known process state; signal only a supervisor/child process group
  whose complete canonical identity matches the durable record; attempt
  non-force removal only for exact clean identity-matched run-owned worktrees;
  never signal an unverified PID and never delete an unrecorded/foreign path.
  Persist every unresolved process, worktree, registration, dirty path,
  ambiguous identity, attempted command, and recovery command.
- **Intended `INFRA_FAILURE` with `EXTERNAL_ONLY`:** reconcile external process
  evidence and, when complete procfs identity is valid, terminate the matching
  supervisor/child process group. Do not run `git`, remove/rename/write a
  worktree path, change a branch/ref/registration, or touch target-repository or
  Git-common-directory state. Record all otherwise applicable Git actions in
  `skipped_git_actions`; record every run-owned and foreign worktree,
  registration, ref, branch, and path as an unresolved resource with
  operator-facing evidence. Cleanliness or apparent run ownership never widens
  this authority.

`PreTerminalCleanup` atomically writes one
`goal-plan.pre-terminal-cleanup/v2` record with at least:

| Field | Contract |
|---|---|
| `schema_version`, `cleanup_attempt`, `intended_status` | Exact schema, positive attempt ordinal, and requested intended terminal status. |
| `trusted_runtime_binding_verdict`, `trusted_runtime_binding_path`, `trusted_runtime_binding_sha256` | Exact current external binding pass and immutable binding identity used to invoke this attempt. |
| `parent_binding_verdict` | Exact current `PASS`, `RED`, or `UNKNOWN`; never copied from an earlier attempt. |
| `target_source_binding_verdict`, `compiled_source_verdict` | Exact current `PASS`, `RED`, or `UNKNOWN` for the other two authority gates. |
| `mutation_authority` | Exact derived `FULL` or `EXTERNAL_ONLY`; a record cannot be published under `NONE`. `FULL` iff all four current verdicts are `PASS`; `EXTERNAL_ONLY` requires trusted runtime `PASS`. |
| `gate_evidence` | Current attempt's trusted-runtime, parent, target/source, and compiled-source record paths and canonical SHA-256 values. Unreadable/missing repository/source evidence records null hash plus the observation error and forces `UNKNOWN`. |
| `permitted_actions` | Closed ordered action descriptors allowed by the derived authority and intended-status policy, including exact resource identities. |
| `attempted_actions` | Every attempted process or Git action with exact argv/operation, resource identity, output/evidence path, exit/result, and before/after observation. |
| `skipped_git_actions` | Every otherwise-applicable Git/repository/worktree action omitted because authority is `EXTERNAL_ONLY`, with resource identity and gate reason. Empty only when no action was skipped. |
| `process_reconciliation_results` | Every identity check, termination attempt, and group-empty result. |
| `registry_and_worktree_projections` | Pre/post registry, filesystem, and Git worktree-list evidence when readable; observation alone does not permit mutation. |
| `preserved_residual_manifest` | Path/hash and bound entries for current `FULL` residual cleanup, otherwise null. |
| `unresolved_resources` | Every unresolved process, worktree, registration, ref, branch, path, foreign resource, dirty state, ambiguous identity, and operator recovery command/evidence. |
| `final_cleanup_verdict` | Exact `FULL_COMPLETE`, `EXTERNAL_ONLY_COMPLETE`, or `INCOMPLETE`. The middle value means the restricted policy completed, not that Git resources were cleaned. |
| `chosen_final_status` | The intended status only for a green `FULL_COMPLETE` status-specific cleanup; otherwise exact `INFRA_FAILURE`. |
| `record_sha256` | Canonical hash binding all fields above plus current parent invocation hash and exact commands/outputs. |

Cleanup faults under either executable authority do not change the
already-infrastructure
status, but remain visible in terminal evidence. `EXTERNAL_ONLY_COMPLETE` always
maps to `INFRA_FAILURE`; `INCOMPLETE` always maps to `INFRA_FAILURE`.
The cleanup record's last non-empty stdout line is exactly
`PRE_TERMINAL_CLEANUP:<CHOSEN_FINAL_STATUS>`. A missing, malformed, or
incomplete cleanup record is itself `INFRA_FAILURE`; the graph reruns/reconciles
cleanup with a fresh authority decision rather than publishing a terminal.

Only after that record is durable does the deterministic finalizer revalidate
the external binding and execute this exact prefix/suffix:

```text
<each token of trusted_runtime_argv_prefix>
terminal-finalize
--trusted-runtime-binding <absolute trusted-runtime-binding.json>
--pre-terminal-cleanup <absolute cleanup-attempt.json>
--result <absolute-state-root>/result.json
--status <absolute-state-root>/goal_plan.status
--output <absolute-state-root>/terminal/finalizer.json
```

It rejects extra/reordered arguments and atomically writes the run root's
versioned `result.json` with, at minimum:

- `schema_version` with exact value `goal-plan.result/v3`;
- `status` with exact value `COMPLETE`, `RESIDUALS_READY`, `INFRA_FAILURE`, or
  `ABORTED`;
- `plan_hash`;
- `product_base_sha` and `execution_source_sha`;
- `attractor_runner_argv_prefix_sha256`, runner module/source identity, and
  compiled `provider`;
- `parent_runner_invocation_definition_sha256`,
  `parent_runner_invocation_paths`, and current parent invocation evidence hash;
- `trusted_runtime_binding_path`, `trusted_runtime_binding_sha256`,
  `runtime_bundle_hash`, and materialization-command evidence paths/hashes;
- `trusted_runtime_argv_prefix_sha256`,
  `trusted_supervisor_argv_prefix_sha256`, and bound
  executable/interpreter/script/CLI/schema identity;
- `compiled_source_manifest_path` and `compiled_source_manifest_sha256`;
- `integrated_head_sha`, or `null` when no integration HEAD exists;
- `compiled_plan_delta` describing `product_base_sha..execution_source_sha`;
- `lane_produced_delta` describing
  `execution_source_sha..integrated_head_sha`, or null when no integration HEAD
  exists;
- `lane_dispositions`;
- `child_process_evidence_paths` and authoritative `supervisor_result_paths`;
- `run_budget_ledger_path` and `run_budget_ledger_sha256`;
- `run_owned_worktrees_path`, `run_owned_worktrees_sha256`, and final lifecycle
  state for every recorded worktree;
- `pre_terminal_cleanup_path`, `pre_terminal_cleanup_sha256`,
  `intended_status`, `trusted_runtime_binding_verdict`,
  `parent_binding_verdict`,
  `target_source_binding_verdict`, `compiled_source_verdict`,
  `mutation_authority`, `cleanup_gate_evidence_hashes`,
  `cleanup_permitted_actions`, `cleanup_attempted_actions`,
  `cleanup_skipped_git_actions`, `final_cleanup_verdict`,
  `unresolved_resource_evidence`, and `preserved_residual_worktrees`;
- `verifier_envelope_evidence_paths`;
- `integration_correction_records`, including every `correction_round_id`,
  `process_run_id`, and terminal correction-reservation state;
- `pre_coherence_aggregate_evidence_path`;
- `fresh_review_evidence_paths`;
- `final_sweep_evidence_paths`;
- `final_aggregate_after_sweep_evidence_path`;
- `residual_evidence_paths`;
- `delivery_state_root`, `delivery_worktree_evidence_path`,
  `delivery_supervisor_result_paths`, and `delivery_ledger_path`; and
- `delivery_pr_url` and `delivery_verified_head_sha` when delivery was
  requested, otherwise `null`.

The finalizer copies only the cleanup record's chosen final status into
`result.json`, sets `goal_plan.status` to that same exact value, and emits
exactly one of these strings as its last non-empty stdout line, with no prose
after it:

| `goal_plan.status` | Last-line token |
|---|---|
| `COMPLETE` | `GOAL_PLAN:COMPLETE` |
| `RESIDUALS_READY` | `GOAL_PLAN:RESIDUALS_READY` |
| `INFRA_FAILURE` | `GOAL_PLAN:INFRA_FAILURE` |
| `ABORTED` | `GOAL_PLAN:ABORTED` |

The finalizer completes its writes successfully so the graph can route on
`tool.last_line`; only then does the explicit terminal carrier publish the
matching CLI outcome. `COMPLETE` is the only successful and deliverable outcome.
The other three remain distinct non-success, evidence-bearing outcomes rather
than aliases for a generic failure.

If trusted-runtime validation fails before or during the finalizer, it writes no
valid finalizer record and cannot claim `result.json`, status, token, cleanup, or
finalizer completion. The launcher/carrier may report only
`INFRASTRUCTURE_BLOCKED` with the external validation/rehydration evidence; it
must not synthesize `GOAL_PLAN:INFRA_FAILURE` as though the durable terminal
machine completed.

There is no post-terminal repository/process/worktree cleanup phase. After
`result.json`, `goal_plan.status`, terminal token, and carrier outcome are
published, only immutable external evidence retention is permitted. In
particular, no later cleanup can downgrade an already-written `COMPLETE`; all
conditions capable of changing it to `INFRA_FAILURE` are resolved inside
`PreTerminalCleanup` first.

Terminal nodes must route explicitly to the graph exit with the cleanup-chosen
final machine status. They must not dead-end and become `no_matching_edge`
authoring errors.
Failure routes must account for real node outcomes; no "successful failure"
sentinel may rely on an unreachable `outcome=fail` edge.

## PR Delivery

The intended-`COMPLETE` path is the only automatic-delivery path. A run becomes
eligible only after fresh coherence, the final all-lane sweep,
`final-aggregate-after-sweep`, and `CompiledSourceGate` all pass at one exact
final HEAD. When delivery is enabled, independent remote verification produces
only intended `COMPLETE`; actual `COMPLETE` is emitted only after a fresh
cleanup-authority decision grants `FULL` and `PreTerminalCleanup` also removes
the delivery worktree and every other run-owned worktree/registration and proves
no live process group or foreign path. Red/unknown binding grants
`EXTERNAL_ONLY`, leaves those Git resources untouched, and finalizes
`INFRA_FAILURE`.

The implementation starts from the proven portable `deliver_pr.dot` topology,
as required by `AGENTS.md` and `docs/RUBRIC.md` section 5, but adapts every
generated-state edge. Checkpoints, events, session metadata, logs, request/
response files, delivery result, and attempt ledger all go beneath the required
external `delivery_state_root`. The adapted graph is prohibited from creating
`.resolve` or any other generated state in the verified delivery worktree.
Independent push/PR-existence checks are retained, and the parent adds the
exact-head remote assertion.

For each delivery attempt, the parent creates a clean disposable registered
delivery worktree at exact `worktree_root/delivery-ATTEMPT`, at the frozen final
HEAD, on the validated delivery branch. It first writes the exact
`delivery` `CREATING` entry to `run-owned-worktrees.json`, then marks it
`ACTIVE` only after path/registration/common-directory/branch/HEAD proof.
Before child launch it:

1. requires exact `git rev-parse --verify HEAD == final_head`;
2. requires empty output from the canonical full ignored-aware porcelain-v2
   status command;
3. writes a complete non-`.git` filesystem manifest using the same `lstat`
   algorithm as `VerifierExecutionEnvelope`;
4. runs `CompiledSourceGate`; and
5. proves the complete worktree manifest contains no `.resolve` generated
   state and equals the approved final-HEAD tree.

The parent reserves one process-launch unit and starts the delivery child with
the exact immutable external `trusted_supervisor_argv_prefix + run suffix`.
After
resolving typed values, exact child argv is:

```text
<each token of attractor_runner_argv_prefix>
run
<repo-relative-adapted-deliver-pr-dot>
--provider
<compiled-provider>
--cwd
.
--logs-root
<absolute delivery_state_root/runs/<attempt>/<process-launch>/attractor-run>
--on-human-gate
fail
--param delivery_attempt=<1-or-2>
--param process_run_id=<plan-id>/<run-id>/delivery/pr/<process-launch>
--param delivery_state_root=<absolute delivery_state_root>
--param delivery_result_path=<absolute delivery_state_root/runs/<attempt>/delivery-result.json>
--param delivery_ledger_path=<absolute delivery_state_root/attempts.jsonl>
--param delivery_branch=<validated-delivery-branch>
--param expected_head_sha=<exact frozen final HEAD>
--param github_repo=<owner/repo>
--param product_base_sha=<full product base SHA>
--param execution_source_sha=<full execution source SHA>
--param runtime_bundle_hash=<full trusted runtime bundle hash>
--param trusted_runtime_binding_path=<absolute trusted-runtime-binding.json>
--param trusted_runtime_argv_prefix_sha256=<full external runtime prefix hash>
--param trusted_supervisor_argv_prefix_sha256=<full external supervisor prefix hash>
--param provider=<compiled-provider>
--param attractor_runner_argv_prefix_sha256=<full prefix hash>
```

The launch contract forbids extra/reordered argv and binds the exact adapted
delivery DOT hash, child-runner prefix/module/source/provider,
trusted-runtime binding/bundle/prefix hashes, trusted-supervisor
prefix/identity/suffix/environment, `delivery_worktree` CWD, external delivery
roots, closed environment, final HEAD, and result schema.
Delivery has no adaptive `Attempt` node and consumes no
`max_total_attempts`; each supervisor start/restart consumes
`max_process_launches`.

`delivery-result.json` uses schema `goal-plan.delivery-result/v1` and binds
delivery attempt, process-run/launch IDs, both source SHAs, exact expected HEAD,
child-runner/supervisor-runner/provider hashes, external ledger/result/log
paths, push/open action, candidate PR URL, and child disposition. It is not
remote proof and cannot override supervisor exit or parent query evidence.

After an authoritative zero-exit supervisor result, the parent reruns the exact
HEAD and full status commands, rebuilds the complete non-`.git` filesystem
manifest, and reruns `CompiledSourceGate`. Expected/pre/post HEAD must equal the
frozen final HEAD, pre/post status must both be clean, pre/post manifests must
be identical, all compiled-source checks must pass, and no `.resolve` path may
be newly created or changed relative to final HEAD. Postconditions run even
after nonzero exit, timeout, or cancellation.
Any local mutation, generated-state leak, missing supervisor result, or stale
registration is `INFRA_FAILURE`, even if a PR exists. The validated delivery
worktree remains an exact `ACTIVE` run-owned entry until
`PreTerminalCleanup`. With `FULL`, a non-force removal, prune, or mapping
failure there changes intended `COMPLETE` to final `INFRA_FAILURE` before any
terminal publication. With `EXTERNAL_ONLY`, removal/prune is skipped, the
worktree/registration remains unresolved evidence, and final status is
`INFRA_FAILURE`.

Delivery has a hard limit of two attempts total for the run, including across
crash recovery. Before any network mutation, each attempt appends a durable
`started` entry to `delivery_state_root/attempts.jsonl`. Every ledger entry
uses schema version `goal-plan.delivery-attempt/v2` and records:

- `schema_version` with exact value `goal-plan.delivery-attempt/v2`;
- `attempt` as integer `1` or `2`;
- `product_base_sha` and `execution_source_sha`;
- `provider`, `attractor_runner_argv_prefix_sha256`,
  `trusted_supervisor_argv_prefix_sha256`, and `process_run_id`;
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

Before each attempt, the parent queries the remote for an existing PR whose head
is the recorded branch at exact expected HEAD. If one exists, the child performs
no duplicate open operation. If none exists, the adapted delivery child may
push/open the PR. In both cases, after local postconditions the parent performs
a separate authenticated remote query and requires the PR to exist with remote
head SHA exactly equal to the frozen final HEAD. Child output, delivery-result
JSON, and `OpenPR` self-report are never sufficient.

Immediately before and after any delivery query/mutation, both source SHAs,
child-runner/supervisor-runner/provider binding, final-sweep evidence,
`final-aggregate-after-sweep`, and delivery ledger must match the frozen final
HEAD. Delivery evidence and the PR report preserve the known compiled-plan
delta separately from the lane-produced delta.

An incomplete ledger entry discovered during recovery counts as an attempt and
is reconciled against remote state before another attempt can start. No third
attempt is possible. If neither attempt obtains independent exact-head
verification, the integrated branch, verifier/review evidence, and ledger are
preserved, and the graph selects intended `INFRA_FAILURE`, runs bounded
`PreTerminalCleanup`, and only then finalizes `GOAL_PLAN:INFRA_FAILURE`; the
pipeline does not claim `COMPLETE`. Delivery network attempts cannot
consume/reset adaptive attempt budget, and delivery process launches cannot
exceed `max_process_launches`.

## Reusable Precedent

Implementation should copy these proven shapes rather than inventing new ones:

| Precedent | Reuse |
|---|---|
| Attractor bundle `examples/patterns/task-runner.dot` | `goal_lane.dot`'s attempt -> deterministic verify -> triage/diagnose -> critique -> curated feedback convergence skeleton, plus explicit budget/postmortem behavior. |
| `pipelines/pr_review/pr_review.dot` | `shape=component` fan-out, `shape=tripleoctagon` fan-in, file-backed cross-branch results, and explicit missing-artifact/crashed-lane detection. |
| `pipelines/resolve_expert_builder/resolve_expert_builder.dot` | One run-wide corrective-work ceiling that cannot be replenished by entering another fix loop, and evidence-rich exhaustion reporting. |
| Existing `subgraphs/deliver_pr.dot` | Reuse its commit/push/PR and downstream real-remote-state topology, but adapt every state/evidence path to external `delivery_state_root`, run it as a supervised child in a clean disposable final-HEAD worktree, and retain independent parent exact-head verification. |
| Existing `goaltractor` composition behavior | Design-time materialization of arbitrary approved plans as static DOT. Reuse it as the composition front end; do not copy its intelligence into runtime. |
| The bounded CWD, convergence, and macro-control probes | Evidence for the process boundary, external correction cycle, and real-exit ledger requirement. They inform production tests but are not copied or shipped as production pipelines. |

## Anticipated File Changes

This repository implements one canonical, statically compiled member of the
family, the reusable local subgraphs, and the deterministic per-child reaper
support that `goaltractor` copies into arbitrary real plan directories. It does
not add a generic root graph, compiler, or runtime scheduler. The expected
footprint is:

```text
pipelines/goal_plan_smoke/goal_plan_smoke.dot
pipelines/goal_plan_smoke/plan.json
pipelines/goal_plan_smoke/goal_plan_smoke.md
pipelines/goal_plan_smoke/subgraphs/goal_lane.dot
pipelines/goal_plan_smoke/subgraphs/integration_correction.dot
pipelines/goal_plan_smoke/subgraphs/deliver_pr.dot
pipelines/goal_plan_smoke/python/goal_plan_runtime.py
pipelines/goal_plan_smoke/python/goal_plan_supervisor.py
pipelines/goal_plan_smoke/python/tests/test_goal_plan_runtime.py
pipelines/goal_plan_smoke/python/tests/test_goal_plan_supervisor.py
pipelines/goal_plan_smoke/python/tests/test_goal_plan_trusted_runtime.py
README.md
```

`goal_plan_runtime.py` is the single deterministic home for source-SHA
admission, parent target-repository/CWD/DOT invocation binding and immutable
invocation evidence, trusted-runtime definition/binding validation and
materialization primitives, compiled-source manifests/gates, ownership-pattern
rejection,
candidate-verification worktree lifecycle, the shared
`VerifierExecutionEnvelope`, phase-split external-root safety,
`run-owned-worktrees.json` lifecycle/recovery, run-budget
process-launch/correction-round/adaptive-attempt reservation/reconciliation,
child-runner/trusted-supervisor/provider preflight, engine-step admission,
delivery-worktree envelope, `PreTerminalCleanup`, durable final-status
selection, and delta reporting. First admission validates its checked-in bytes
as source data, while every parent safety-critical DOT node calls only its
sealed external trusted-runtime copy rather than duplicating shell logic or
executing the target-repository path. `goal_plan_supervisor.py` remains the
single source home for the lane, correction, and delivery reaper, immutable
self-check/CLI-schema report, authoritative wait-status capture, Linux process
identity, long-poll/control-client schemas, and closed tokens; every runtime
invocation uses its sealed external trusted-supervisor copy.

The implementation also materializes run-scoped external artifacts, not checked
in repository files:

```text
state_root/trusted-runtime/<runtime-bundle-hash>/goal_plan_runtime.py
state_root/trusted-runtime/<runtime-bundle-hash>/goal_plan_supervisor.py
state_root/trusted-runtime/<runtime-bundle-hash>/trusted-runtime-binding.json
```

The launcher/CWD bootstrap gains the deterministic direct-Git-object
materialization/rehydration sequence defined above. It contains no product
scheduler or model logic.

The smoke exemplar proves orchestration rather than product behavior. In a
temporary repository, two Wave 1 fixture lanes each produce a file in disjoint
owned paths; one Wave 2 integration fixture lane depends on both and produces a
third fixture file. Each fixture lane runs as a separately supervised child
Attractor process. Its graph is fixed and self-contained. The existing
`goaltractor` remains the composition front end that materializes arbitrary
real plans to the same directory and contract; it is not reimplemented here.
The canonical compiled `provider` is `anthropic`; the smoke runs headless with
`approval_mode=preapproved`, `human_gate_transport=none`, and external
`state_root`, `worktree_root`, and `delivery_state_root`.

This design-document revision does not implement those files.

## Verification Strategy

Verification follows the repository's live-run gradient because this is
orchestration behavior, not a library-only change.

### Verification matrix

| Claim | Verification level | Required proof |
|---|---|---|
| Adaptive attempts, process launches, and correction rounds are separate | Unit + concurrent live fault injection | Flocked v3 ledger binds the trusted runtime and shows `ReserveGlobalAttempt` consumed at verifier classification, every supervised correction-child launch transitions its own `correction_round_id`, and every supervisor start changes `max_process_launches`; no counter borrows from another. |
| Parent runner is bound to `target_repo` | Launcher/admission/recovery faults | Parent starts only after `chdir(realpath(target_repo))`; `/proc/self/cwd`, runner `--cwd .`, and canonical target repo are equal; parent DOT realpath is exact; observed/execution-source/manifest hashes agree; and immutable argv/prefix/provider/process/logs evidence is durable before mutation. |
| Terminal runtime remains trustworthy after source failure | First-admission + live mutation/recovery faults | Checked-out runtime/supervisor bytes equal exact plan/manifest/Git blobs before mutation; sealed external copies and `trusted-runtime-binding.json` are atomically/fsync durably materialized from `cat-file blob`; every safety command revalidates and uses only external prefixes; source mutation reaches external-only final INFRA evidence, while external-copy/interpreter/hash drift blocks action. |
| Final proof and cleanup order is sound | Static topology + live smoke | Current-HEAD closure lanes -> affected-closure aggregate -> pre-coherence aggregate -> coherence -> one-HEAD final sweep -> `final-aggregate-after-sweep` -> optional delivery -> intended status -> `PreTerminalCleanup` -> durable terminal publication. |
| Long polling cannot exhaust engine steps prematurely | Static arithmetic + timed live run | Recomputed branch inequality, parent total-step inequality, exact 30-second poll argv, identity checks, and observed deadline-capped waits. |
| Delivery preserves verified source | Live Git/remote probe | Disposable final-HEAD worktree has equal pre/post HEAD/status/full-filesystem/source records, no generated `.resolve` delta, external delivery evidence, and parent-observed PR exact head. |
| Child-runner, trusted-supervisor, and provider identity cannot drift | Admission/recovery faults | Allowed child-runner forms and exact external trusted-supervisor prefix pass; PATH/shell/executable/interpreter/source-blob/external-script/hash/permission/environment/CLI/schema/subcommand/flag/credential faults and any binding/prefix/provider change on resume fail before mutation. |
| Worktree ownership and terminal cleanup are phase-safe | Unit + live Git recovery/finalization faults | Preapproval rejects every overlap; postapproval accepts only the exact mapping; fresh all-green trusted-runtime/parent/target-source/compiled gates grant `FULL`; a green trusted runtime plus red repository/source binding grants `EXTERNAL_ONLY`; red trusted runtime grants `NONE`; complete removes exact run-owned worktrees only under `FULL`; residual preserves only named `PRESERVED_RESIDUAL` entries under `FULL`; restricted cleanup touches no Git state, may stop only fully procfs-identity-valid process groups, records skipped/unresolved resources, and publishes no terminal first. |
| Approval modes are operationally honest | Standalone admission probes | Preapproved unattended headless passes; required attached standalone console/TTY passes; required without TTY or on unattended/hosted headless execution fails before mutation. |
| DOT remains inspectable | Graphviz + lint | Every DOT renders to a non-empty PNG with recorded hashes and passes strict lint; any render failure is loud. |
| Python implementation is clean without cache mutation | Static + unit | `python_check`, system `python3 -m pytest`, clean diff, and no changed managed-cache path. |

### Static checks

1. Parse and render the parent, lane, correction, and delivery DOT files with
   Graphviz using fail-loud commands such as
   `dot -Tpng INPUT.dot -o OUTPUT.png`. Preserve exact argv, exit status,
   stdout/stderr, source SHA-256, PNG SHA-256, and nonzero output size as render
   evidence. A missing `dot`, nonzero exit, empty PNG, or missing evidence is a
   verification failure; rendering is never optional.
2. Run the immutable runner prefix's `lint --strict` on the entry graph and all
   three subgraphs.
3. Run `python_check` on both checked-in Python implementation files and their
   tests, then run the tests with system Python exactly as
   `python3 -m pytest pipelines/goal_plan_smoke/python/tests -q`. Do not use,
   patch, or write any interpreter/module beneath `~/.amplifier/cache` or another
   managed Amplifier cache.
4. Audit the implementation against every item in `docs/RUBRIC.md`.
5. Confirm all deterministic routes use observed state and explicit failure
   edges; no LLM judgment gate uses `shape=diamond`.
6. Confirm every terminal is reachable and routes explicitly to the exit.
7. Confirm the README and companion guide describe the actual graph.
8. Validate the aggregate-verifier evidence schema, all verification kinds,
   exit/token normalization, shared envelope schema/hash/token map,
   verifier-hash guard, fresh-review schema, finalizer token map, and
   two-attempt delivery ledger.
9. Validate `plan.json` schema and exact-byte hash, embedded `plan_sha256`,
   graph/plan correspondence, both target-repository identity modes,
   `trusted_runtime_definition`, binding policy, exact runtime-bundle-hash
   derivation, and typed runtime-input rejection cases.
10. Validate the only two permitted `attractor_runner_argv_prefix` forms,
    canonical prefix hash, executable/module/source identity, `doctor`,
    required run flags, exact compiled provider support/credential, explicit
    `--provider` on every child argv, and immutable provider/prefix on resume.
    Validate the compile-bound absolute Git/interpreter prefixes and hashes,
    both source path/blob/mode/length/hash identities, exact `cat-file blob`
    materialization argv/evidence, atomic writes/fsyncs/non-writable modes/final
    rereads, complete `trusted-runtime-binding.json` schema/hash, exact external
    `trusted_runtime_argv_prefix`, and exact external
    `trusted_supervisor_argv_prefix` form from the binding,
    executable/interpreter realpath/hash,
    repository-relative source path/blob identity, external script path/hash and
    non-writable permissions, closed environment schema/hash, non-mutating
    self-check, exact CLI/supported-schema versions and subcommand suffixes, and
    identical binding on recovery.
11. Recompute `poll_wait_seconds=30`, `engine_step_multiplier=50`,
    `branch_nonpoll_steps`, `branch_node_count`, `max_poll_cycles`, each strict
    branch inequality, and parent total-step inequality from DOT.
12. Prove the graph contains no manifest-driven scheduler: lane, wave,
    dependency, integration-order, process-launch budget, adaptive-attempt
    budget, and every statically expanded correction ordinal's reserve/start/
    consume/exhaustion routes remain explicit DOT nodes/edges/constants.
13. Prove lane verifier-definition hashes include all three symbolic CWD
    policies and no absolute paths; aggregate hashes retain only
    `integration_worktree`; every invocation records and validates its resolved
    `realpath` separately.
14. Validate `product_base_sha`, the non-self-referential containing-commit
    binding for exact `execution_source_sha`, their graph attributes/ancestry,
    and separate compiled-plan/lane-produced reporting ranges.
15. Validate lane/correction/delivery child DOT hashes, exact closed
    prefix-plus-argv schemas, provider, environments, `process_run_id` template,
    `correction_round_id` template, supervisor prefix-plus-suffix argv,
    reaper/intent/ack/result hashes, evidence schemas, wall budgets, and static
    launch/long-poll node correspondence.
16. Validate `max_total_attempts` counts only `ReserveGlobalAttempt` records
    consumed at verifier classification; supervisor starts/restarts count
    against `max_process_launches`; and every integration-correction supervisor
    launch also reserves/transitions exactly one correction round against
    `max_integration_corrections`.
17. Validate ownership/integration-seam schemas reject every pattern matching
    `pipelines/PLAN_SLUG/**`; validate manifest path-set/mode/length/byte
    comparisons at every `CompiledSourceGate`.
18. Unit-test external trusted-supervisor self-check, per-invocation binding
    validation, and exact prefix-plus-subcommand argv/intent schemas,
    executable/interpreter/external-script/permission/environment identity,
    supervisor/child procfs identity, ledger/ack ordering, direct-child
    wait-status normalization, exact
    `--wait-seconds 30` long-poll/deadline cap, log hashes,
    timeout/cancellation/group cleanup, control-client schemas/tokens,
    pre-ledger `/proc` discovery, and result atomicity.
19. Unit-test verifier and delivery envelopes' immutable expected-HEAD binding,
    pre/post HEAD/status/full-filesystem/source gates, exact external output
    roots, `.resolve` rejection, discarded-result behavior, token mapping,
    teardown, and recovery classification.
20. Unit-test `fcntl.flock` serialization and atomic replacement for separate
    process-launch, correction-round, and adaptive-attempt maps; simultaneous
    correction reservation at the ceiling; exact correction key/process binding;
    RESERVED/STARTED/CONSUMED/RELEASED idempotence; pre-ack abandoned
    reservation handling; crash-after-STARTED conservative consumption;
    `ReserveGlobalAttempt` tuple identity; exact-once verifier-bound consumption;
    active process-run tracking; all budget ceilings; `CLOCK_BOOTTIME` deadline
    closure; boot-ID failure; and restart recovery.
21. Unit-test first-admission checked-out-byte/blob/manifest equivalence,
    direct-Git-object materialization, atomic/no-replace writes, fsync ordering,
    non-writable permissions, final reread verification, complete
    `trusted-runtime-binding.json`, per-invocation path/permission/hash checks,
    absent-bundle rehydration, and present-mismatch refusal. Also unit-test
    phase-split root safety, exact run-owned worktree registration and recovery,
    preapproved headless success, required+attached-console/TTY success,
    required+unattended-or-hosted-headless rejection, and read-only preapproval
    admission that writes only external state.
22. Run `git diff --check`, assert only the planned implementation footprint is
    modified, and explicitly fail if any changed path resolves beneath a managed
    cache.
23. Validate the parent launch definition and every immutable invocation record:
    trusted-runtime validation/rehydration precedes parent start; launcher CWD
    changes before `exec`; `/proc/self/cwd`, runner `--cwd .`, and canonical
    `target_repo` are equal; the parent DOT realpath is exact; its
    observed/execution-source/compiled-manifest hashes agree; external binding,
    argv prefixes, provider, process identity, logs root, and resume hash chain
    are exact; and every mismatch fails before repository mutation.
24. Validate the exact external-prefix `pre-terminal-cleanup` and
    `terminal-finalize` command schemas; fresh
    `trusted_runtime_binding_verdict`, `parent_binding_verdict`, target/source,
    and compiled-source gate records and hashes; derived `FULL`,
    `EXTERNAL_ONLY`, or `NONE` authority; status-specific process/worktree rules;
    `PRESERVED_RESIDUAL` evidence/recovery contract; all-`REMOVED` complete
    mapping; pre-mutation aborted proof; bounded `FULL` infrastructure cleanup;
    external-only process/evidence allowlist and Git denylist; permitted,
    attempted, skipped, and unresolved action records; rejection of stale prior
    `FULL` on retry; final cleanup verdict/chosen-status token; refusal to claim
    cleanup/finalizer completion when trusted-runtime binding is red; and strict
    ordering before `result.json`, `goal_plan.status`, terminal token, and CLI
    carrier publication.

### Primary live smoke scenario

Run the canonical `goal_plan_smoke` pipeline against a temporary,
GitHub-backed Git repository with a known aggregate verifier and three fixed
fixture lanes. Its immutable `attractor_runner_argv_prefix` uses one permitted
absolute form, its compiled `provider` is `anthropic`, and admission proves the
Anthropic credential before the headless `preapproved` run:

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

1. The launcher changes into canonical `target_repo` before parent `exec`;
   `/proc/self/cwd`, literal runner `--cwd .`, and canonical `target_repo`
   resolve equally; the invoked parent DOT realpath is exact; its
   observed/execution-source/compiled-manifest hashes agree; immutable parent
   argv/prefix/provider/process/logs evidence is durable; and the adjacent
   `plan.json` hash, graph/plan correspondence, normalized fetch-remote
   identity, both source SHAs/ancestry, child-runner binding, and supervisor
   source identity all pass before mutation. The checked-out runtime/supervisor
   files equal plan-declared Git blobs and compiled-manifest entries; exact blob
   bytes are atomically materialized and sealed under `state_root`; the complete
   versioned binding and materialization command evidence are durable; and both
   external self-checks pass before mutation.
2. Typed runtime inputs are bound; `state_root` resolves under
   `$XDG_STATE_HOME` or the external user-state fallback; `worktree_root` and
   `delivery_state_root` are separate safe external roots; strict preapproval
   overlap checks pass before mutation; `approval_mode=preapproved`,
   `human_gate_transport=none`, and parent/children use the compiled headless
   gate flags; `runtime_bundle_hash` and `trusted_runtime_binding_path` equal the
   launcher-derived external binding; only external admission evidence is
   written before preapproval.
3. The integration worktree and prepared Wave 1 branches begin at exact
   `execution_source_sha`; a later-wave lane begins at a parent-verified
   integration HEAD descended from it. Every lane/integration/candidate/delivery
   worktree has an exact `run-owned-worktrees.json` entry and exact Git
   registration/branch-or-detached-SHA/common-directory mapping, with no foreign
   descendant. Product reporting separately names the compiled-plan and
   lane-produced delta ranges.
4. Wave 1 launches two concurrent child Attractor processes in distinct
   worktrees. Process and child evidence show that each OS CWD and Attractor
   root CWD is its assigned worktree and that its box-session relative writes
   remain there.
5. Every lane has a separately reserved process launch, atomic launch intent,
   accountable live reaper identity, ledger/ack, exact `--wait-seconds 30`
   long-poll/reconcile records, canonical process-run token, exact child and
   supervisor prefixes/identities/closed argv/environments, exact provider in
   child argv/env, and authoritative supervisor result with raw wait status,
   normalized exit/signal, cleanup proof, and log hashes.
6. `lane_b`'s first failure is visible and causes a corrective cycle rather
   than a silent pass or blind restart.
7. Before each lane/correction adaptive attempt, `ReserveGlobalAttempt` binds
   lane/correction ID, `process_run_id`, local attempt, and verifier hash. Its
   reservation is consumed exactly once at verifier classification; process
   launches do not change `max_total_attempts`.
8. The correction is genuinely dependent on the changed verifier feedback: a
   control run with unchanged/withheld feedback remains red, while the changed
   feedback produces a different candidate hash and later green evidence.
9. Parent verification creates a clean detached
   `candidate_verification_worktree` at the exact candidate SHA, runs the
   shared envelope only there, proves expected/pre/post HEAD equality and clean
   pre/post status, records both compiled-source checks, then
   removes/reconciles it with separately durable teardown evidence.
10. Ownership checks pass, reject an out-of-scope write, and categorically
   reject any compiled-pipeline write or integration seam.
11. Integration occurs in stable order, with an
    `aggregate_after_merge` envelope after each merge. Its immutable expected,
    pre-, and post-HEADs are equal; pre/post porcelain-v2 status records and
    complete ignored-aware worktree manifests match; both compiled-source
    checks pass; all verifier outputs are contained beneath its output root; and
    its aggregate token agrees with the envelope verdict.
12. `lane_c` starts only after both dependencies are integrated and green.
13. Cross-lane `ITERATE` atomically reserves one exact
    `correction_round_id` and one process launch, invokes one supervised
    `IntegrationCorrection` child on the integration branch, marks correction
    `STARTED` only after valid ack and `CONSUMED` on authoritative terminal
    result, and never uses old lane branches; its internal attempts use only
    `ReserveGlobalAttempt`, and its write set is limited to responsible
    ownership plus seams.
14. Correction invalidates prior proof, then at one current HEAD runs all
    affected-closure lane envelopes, `affected_closure_aggregate`,
    `pre_coherence_aggregate`, and a fresh coherence review in that order.
15. After coherence passes, the final sweep runs every lane verifier through a
    `final_sweep_lane` envelope at one frozen final HEAD, followed by
    `final-aggregate-after-sweep`; both and the coherence record name that exact
    SHA and both source SHAs.
16. The pre-delivery and pre-`PreTerminalCleanup` trusted-runtime,
    parent-runner, target/source-identity, and compiled-source gates freshly
    match immutable admission evidence; the cleanup record binds their hashes,
    `trusted_runtime_binding_verdict: "PASS"`,
    `parent_binding_verdict: "PASS"`, and `mutation_authority: "FULL"`.
17. Delivery runs through a separately supervised child in a clean disposable
    final-HEAD worktree. Pre/post HEAD, full status, complete non-`.git`
    filesystem manifests, and source gates remain equal/green; every generated
    file is beneath `delivery_state_root`, and no new/changed `.resolve` entry
    appears relative to final HEAD.
18. The external delivery ledger records no more than two attempts, both source
    SHAs, runner/provider/process identities, and manifest hash; the parent's
    independent remote query observes a PR head equal to exact final HEAD.
19. Under the current `FULL` authority, the exact external
    `trusted_runtime_argv_prefix + pre-terminal-cleanup` invocation reconciles
    every supervisor/process group to terminal, removes exact
    lane/candidate/delivery/integration worktrees without force,
    prunes/reconciles registrations, proves the complete run-owned mapping is
    `REMOVED`, finds no foreign path, records permitted/attempted/skipped actions
    and no unresolved resource, and durably chooses `FULL_COMPLETE` plus
    `COMPLETE`.
20. Only after item 19, the exact external
    `trusted_runtime_argv_prefix + terminal-finalize` invocation writes
    `result.json` with both delta ranges, trusted-runtime binding, and cleanup
    evidence; `result.json`, `goal_plan.status`, the last-line token, and CLI
    carrier outcome agree on `COMPLETE` only after all nineteen preceding
    observations hold.

### Fault and recovery probes

The implementation is not ready until live probes also demonstrate:

- deleting one lane's required result before fan-in yields `CRASHED`, not a
  clean result;
- launching the parent from the repository's parent directory, a symlink alias,
  a different worktree, or an unrelated CWD; changing literal `--cwd .`;
  invoking a copied/renamed parent DOT; changing its bytes; changing parent
  prefix/provider/logs root; or resuming with a non-matching parent invocation
  record yields `INFRA_FAILURE` before any repository mutation, with immutable
  external evidence for the observed OS CWD, CLI CWD, DOT realpath/hash,
  target repository, source SHA, process identity, and argv;
- after green admission, byte-mutating or deleting the target-repository
  `goal_plan_runtime.py` while leaving the external trusted bundle intact makes
  the source gate red, invokes `PreTerminalCleanup` only through the exact
  external `trusted_runtime_argv_prefix`, derives
  `mutation_authority: "EXTERNAL_ONLY"`, performs no Git/worktree mutation, and
  writes final `INFRA_FAILURE` cleanup/result/status/token evidence through the
  externally pinned runtime; the same probe is repeated for
  `goal_plan_supervisor.py`;
- byte-mutating, permission-widening, path-replacing, or deleting the external
  trusted runtime or supervisor copy makes the next per-invocation binding gate
  red before action, grants `mutation_authority: "NONE"`, and performs no Git
  mutation, general signalling, cleanup, or finalizer publication; only a
  separately still-valid trusted-supervisor identity may exercise the narrow
  exact-process termination exception;
- with the external trusted-runtime directory absent and the current
  target-repository runtime files deleted or mutated, recovery rehydration uses
  the compile-bound absolute Git argv to extract the exact plan-declared blobs
  from `execution_source_sha`, recreates byte-identical non-writable external
  files and `trusted-runtime-binding.json`, verifies all hashes/permissions,
  then starts recovery only through the recreated external prefix;
- a wrong plan-declared blob ID, Git object whose bytes do not match the
  expected hash, substituted interpreter realpath or bytes, wrong Git
  executable hash, widened materialized-file permissions, or mismatched
  runtime-bundle/binding hash fails prelaunch/rehydration before any extracted
  code executes and records infrastructure-blocked without claiming
  cleanup/finalizer completion;
- a child that writes its expected artifact and then exits nonzero remains
  non-pass because the supervisor result preserves authoritative wait status;
- parent crash while supervisor and child run leaves the reaper alive in its own
  session; it waits/reaps and writes an authoritative result that restart
  reconciliation accepts only after full identity/hash validation;
- normal child exit `0`, nonzero exit, and signal termination produce exact raw
  wait status and correct normalized exit/signal fields;
- child artifact plus nonzero exit remains non-candidate because only the
  supervisor result owns exit truth;
- supervisor crash with an identity-valid live child triggers immediate
  control-client group termination and `INFRA_FAILURE`; supervisor disappearance
  plus absent child and missing result is also infrastructure failure;
- crash before ledger/ack exercises bounded `/proc` discovery by exact
  `process_run_id` in supervisor argv/environment: one supervisor is adopted,
  an orphan child is terminated, zero matches releases only a proven
  never-started process-launch reservation, and ambiguous duplicate tokens are
  never signalled;
- `poll --wait-seconds 30` distinguishes running, terminal-result,
  supervisor-gone, and infra, validates identity before/after its internal
  long-poll, and never exceeds remaining child/run deadline; parent cancellation
  uses only `terminate` with an approved reason token;
- timeout and cancellation perform supervisor-owned TERM -> grace -> KILL,
  reap the direct child, empty the whole child group, and write result atomically;
- killing the reaper while it writes result cannot expose a partial valid JSON;
  missing result is never success;
- stale supervisor or child identity probes independently change PID start
  ticks, cmdline, PGID, CWD, executable, token, or command hash and never signal;
- changing the supervisor prefix, executable/interpreter realpath or bytes,
  checked-in script path/hash, closed environment, CLI version, supported schema,
  or any run/poll/terminate/reconcile suffix after admission fails recovery as
  `INFRA_FAILURE` before another supervisor operation;
- normal and failure cases prove no zombie children, orphan child groups, or
  lingering reapers remain after authoritative completion/cleanup;
- a candidate-verification worktree with wrong HEAD, dirty-before state,
  dirty-after state, failed non-force removal, stale worktree registration, or
  crash-left incomplete envelope evidence yields `INFRA_FAILURE`; a clean
  crash-left worktree is removed/reconciled and verification starts in a new
  detached worktree only when no envelope invocation had begun;
- a normal read-only verifier receives the exact output-root interface and
  environment, writes all outputs beneath `verifier_output_root`, leaves
  expected/pre/post HEAD equal, leaves porcelain-v2 status and complete
  ignored-aware worktree manifests unchanged, preserves both compiled-source
  checks, and returns the expected envelope `PASS` or `FAIL`;
- a verifier that modifies a tracked file and then exits `0` produces envelope
  `INFRA`, discards the apparent pass, and enters no correction loop;
- a verifier that creates any untracked file and then exits `0` produces
  envelope `INFRA`;
- a verifier that writes an ignored cache directory or ignored report inside the
  worktree and exits `0` produces envelope `INFRA`; porcelain-v2 ignored output
  and the complete filesystem manifest both preserve evidence;
- a verifier that stages a file and then exits `0` produces envelope `INFRA`
  because post-status exposes index dirtiness;
- a verifier that commits a change and then exits `0` produces envelope `INFRA`
  because post-HEAD differs from immutable expected/pre HEAD;
- a verifier that checks out another commit and then exits `0` produces envelope
  `INFRA` because post-HEAD moved; and
- a verifier that mutates any compiled-source byte and then exits `0` produces
  envelope `INFRA` even when ordinary status output is empty, because the post
  manifest gate is independently authoritative;
- a verifier whose argv lacks exact `--output-root`, whose containment
  environment points into a worktree, or whose declared output escapes
  `verifier_output_root` fails admission/envelope integrity; a normal verifier's
  output-root manifest contains all logs, caches, temp files, coverage, and
  reports;
- simultaneous process-launch reservations serialize under `fcntl.flock`,
  receive distinct IDs, never exceed `max_process_launches`, and do not change
  `max_total_attempts` while child processes still overlap;
- simultaneous correction launches serialize under `fcntl.flock`, atomically
  receive distinct monotonic `correction_round_id` and process-launch
  reservations, satisfy
  `consumed_corrections + active_reserved_corrections <
  max_integration_corrections` before each reservation, and never admit an
  ordinal beyond the static DOT expansion;
- correction reservation becomes `STARTED` only from a valid supervisor ack and
  `CONSUMED` on every authoritative terminal outcome; duplicate identical
  transitions are no-ops, conflicting transitions are INFRA, crash after
  `STARTED` consumes conservatively, and `RELEASED` occurs only with proof the
  supervisor launch never happened;
- an abandoned pre-ack correction reservation with ambiguous launch evidence is
  not released, blocks its capacity, and produces a named terminal
  infrastructure residual; exhaustion preserves the last findings, responsible
  set, affected closure, process IDs, and integration HEAD and never launches an
  extra correction;
- simultaneous lane/correction `ReserveGlobalAttempt` calls bind distinct
  subject/process/local-attempt/verifier tuples and never exceed
  `max_total_attempts`; each consumes exactly once only when its verifier record
  is classified;
- process crash after reservation but before creation releases only with proof
  of no process; crash after creation consumes. Adaptive crash after reservation
  releases only with proof no attempt started; any start/ambiguity writes a
  synthetic crash classification and consumes conservatively;
- exhausting `max_process_launches` prevents another supervisor start/restart
  without borrowing an adaptive attempt, while one surviving child may consume
  multiple adaptive attempts;
- when `CLOCK_BOOTTIME` reaches the deadline with active children, the ledger
  closes, every matching active process group is terminated through
  `terminate --reason global_deadline`, active lanes become
  `BUDGET(global_deadline)`, unstarted dependents become
  `BLOCKED-global-deadline`, and no future retry reserves;
- a reboot/boot-ID mismatch or invalid/decreasing boottime during budget
  recovery is `INFRA_FAILURE`, not a refreshed deadline;
- preapproved headless admission snapshots target Git refs, branch/worktree
  list, Git common-directory metadata, target-tree status, `worktree_root`, and
  `delivery_state_root`; after external manifest/render persistence those
  observations are unchanged and neither mutable root exists;
- `approval_mode=required` succeeds only with attached standalone
  `--on-human-gate console` plus recorded TTY evidence and is rejected before
  mutation without that evidence or on unattended/hosted headless execution;
- before approval, state/worktree/delivery roots equal to or overlapping the
  target repository, Git common directory, compiled source, any pre-existing
  or foreign worktree, or each other are rejected, including symlink aliases;
  after approval, only exact registry-owned lane/integration/candidate/delivery
  worktrees may descend from `worktree_root`; unset `XDG_STATE_HOME` uses only
  the external `$HOME/.local/state` fallback;
- creating an unrecorded file/worktree beneath `worktree_root`, registering a
  foreign worktree there, moving a recorded worktree outside it, changing a
  recorded branch/detached SHA/common directory, or deleting its registration
  yields `INFRA_FAILURE`; `FULL` intended-infrastructure cleanup may remove only
  an exact clean identity-validated run-owned worktree, while
  `EXTERNAL_ONLY` leaves every run-owned/foreign path, ref, registration,
  branch, and Git common-directory state untouched;
- with the external trusted runtime still green, a red/unknown current parent,
  target/source, or compiled-source binding and an otherwise clean, exact
  run-owned worktree records `trusted_runtime_binding_verdict: "PASS"`,
  `parent_binding_verdict`, `mutation_authority: "EXTERNAL_ONLY"`, the skipped
  removal/prune actions, and unresolved path/registration evidence; direct filesystem and
  `git worktree list --porcelain` observations prove the worktree was not
  removed;
- the same red/unknown repository/source binding may use the still-green
  trusted supervisor prefix to terminate one fully
  procfs-identity-validated supervisor/child process group and prove it empty,
  but before/after target-tree, ref, branch, registration, worktree-path, and
  Git-common-directory observations prove no Git/repository mutation occurred;
- a current all-green trusted-runtime/parent/target-source/compiled gate set
  grants `FULL` and removes one exact recorded clean run-owned worktree without
  force, reconciles only its exact registration, proves path/registration
  absence, and records its lifecycle as `REMOVED`;
- a crash-left cleanup record with prior `mutation_authority: "FULL"` followed
  by a current green trusted runtime but red/unknown repository/source gate is
  resumed as a new `EXTERNAL_ONLY` attempt; the stale authority is rejected,
  every pending Git action is skipped, and the final status is `INFRA_FAILURE`;
- under current `FULL`, intended `COMPLETE` with a live supervisor/group, dirty
  run-owned worktree, non-force removal failure, prune/registration failure,
  non-`REMOVED` mapping, or foreign path is changed by `PreTerminalCleanup` to
  final `INFRA_FAILURE` before any `result.json`, status, token, or carrier
  outcome;
- under current `FULL`, intended pre-mutation `ABORTED` finalizes only when no
  process/worktree/root mutation exists; an injected process intent, registry
  entry, worktree, registration, or created mutable root changes it to
  `INFRA_FAILURE`;
- under current `FULL`, intended `RESIDUALS_READY` preserves only explicitly
  named worktrees as `PRESERVED_RESIDUAL` with exact evidence and recovery
  commands, removes all others, treats intentional preservation as green, and
  changes any unidentified/dirty non-residual or removal failure to
  `INFRA_FAILURE`;
- intended `INFRA_FAILURE` with `FULL` performs bounded best-effort exact
  identity-matched Git/process cleanup; with `EXTERNAL_ONLY` it performs only
  external evidence writes and fully procfs-identity-validated process-group
  termination, skips all Git actions, and records every unresolved resource and
  recovery command before finalization;
- crashing during `PreTerminalCleanup` resumes the exact cleanup journal
  idempotently only after recomputing current authority and publishes no
  terminal first; stale prior `FULL` never authorizes a retry. After durable
  terminal publication, no cleanup command runs and an already-written
  `COMPLETE` can never be downgraded by post-terminal work;
- two consecutive runs leave source DOT, scripts, and committed fixtures
  byte-clean, with every generated log, event, checkpoint, feedback, and result
  beneath the appropriate external `state_root`/`delivery_state_root`; no
  `.resolve` appears in any verified worktree;
- deleting, adding, mode-changing, or byte-changing any compiled-source entry
  is detected after child exit, before candidate verification, after merge,
  after integration correction, during restart, before delivery, and before
  `PreTerminalCleanup`; while the external trusted runtime remains green, a
  current pre-cleanup mismatch grants only `EXTERNAL_ONLY`, and every case
  reaches `INFRA_FAILURE` without lane correction or Git cleanup;
- an impossible verifier exhausts its lane budget, produces a postmortem,
  blocks dependents by name, reaches `RESIDUALS_READY`, and opens no automatic
  PR;
- an out-of-ownership write is rejected even when the lane verifier passes;
- an aggregate failure after a candidate merge restores the pre-merge HEAD and
  routes evidence back to the responsible lane;
- a `plan.json` byte change, DOT/plan lane mismatch, relative runtime path,
  wrong `product_base_sha`, non-containing or non-descendant
  `execution_source_sha`, invalid runner-prefix form/hash/module/source,
  failed doctor/missing required flag, unsupported/missing-credential provider,
  provider change on resume, parent OS-CWD/CLI-CWD/target-repo inequality,
  parent DOT realpath/blob/manifest mismatch, incomplete parent invocation
  evidence, argv/param order mismatch, output-path escape, engine-step
  inequality, incompatible reused `run_id`, non-Linux platform, or
  mode/approval-transport mismatch fails admission before mutation;
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
  reserves one correction round plus one process launch, runs as a supervised
  correction child with per-attempt `ReserveGlobalAttempt`, runs
  `CompiledSourceGate`, and invalidates old evidence;
- a red affected-closure or final-sweep lane verifier routes back to
  `IntegrationCorrection`, while correction-budget exhaustion records named
  residuals and never resumes old lane branches;
- every correction proof route runs affected-closure lane envelopes, the
  affected-closure aggregate, the pre-coherence aggregate, and coherence at one
  HEAD; coherence `PASS` then requires a fresh all-lane sweep and
  `final-aggregate-after-sweep` at that same final HEAD;
- restarting after an integration-correction commit resumes closure proof at
  current integration HEAD rather than duplicating the correction;
- restarting after a lane commit but before integration reconciles the commit
  without duplicate work or duplicate merge;
- a delivery child runs under the accountable supervisor in a clean disposable
  final-HEAD worktree, preserves pre/post HEAD/status/full-filesystem/source
  gates, writes generated state only below `delivery_state_root`, and is
  rejected if it creates `.resolve`;
- restarting after remote PR creation discovers the existing PR and the parent
  independently verifies its exact final head instead of opening another;
- two unverifiable delivery attempts preserve the integrated branch and end
  with `GOAL_PLAN:INFRA_FAILURE`, with no third attempt; and
- an unavailable or untrustworthy verifier/git/remote substrate reaches
  `INFRA_FAILURE` rather than consuming model-correction budget.

The smoke evidence consists of the exact commands, exit statuses, git SHAs,
verifier logs, state artifacts, rendered graph, and remote PR/API output. Lane
or reviewer prose alone cannot satisfy any check.

## Open Questions

None.
