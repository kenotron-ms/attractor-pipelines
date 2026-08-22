# Goal Plan Attractor Design

**Status:** Approved

**Date:** 2026-08-22

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
| `goal-batch` | Work is decomposed before launch, conflicts and dependencies are analyzed, the user approves the lane split, lanes work in isolated worktrees, results are merged sequentially, and the parent reruns verification. | tmux, launcher/status scripts, manifest/`DONE.json` process coordination, nested `/goal` CLI processes, and a runtime lane scheduler. |

The important correction is that `/goal`'s transcript evaluator is not
independent machine evidence. In `goal_plan`, a deterministic verifier outside
the lane worker decides mechanical satisfaction, and the parent reruns that
verifier against the durable commit before integration.

## Decision

Implement `goal_plan` as a **statically compiled goal-plan attractor**.

`goalify`/goal-batch-style decomposition remains the composition layer. It
produces a human-approved set of lane goals, owned paths, dependencies,
verifiers, qualitative criteria, and budgets. Before runtime, that plan is
materialized as a fixed DOT graph with explicit dependency waves and lane
subgraphs. Changing lane count, dependencies, ownership, or verifier contracts
requires changing and reviewing the graph.

Runtime does not compile another graph and does not discover or schedule work
from a queue. It executes the reviewed graph that is already present.

This is a narrow executor for an approved goal plan, not another generic
goaltractor and not a replacement for the composition mechanisms that create
the plan.

## Goals

- Make every approved lane and dependency visible in DOT.
- Preserve adaptive, feedback-informed goal pursuit inside each bounded lane.
- Isolate concurrent lanes in separate git worktrees.
- Accept lane completion only after an exact non-interactive verifier passes.
- Require a durable commit before a lane can be integrated.
- Have the parent independently rerun each lane verifier against the exact
  commit proposed for integration.
- Enforce declared path ownership before integration.
- Integrate passing lane commits sequentially.
- Run the aggregate verifier after every integration and again at final HEAD.
- Run a fresh cross-lane coherence review against the fully integrated result.
- Optionally deliver one PR through the proven `deliver_pr.dot` pattern and
  independently verify that the remote PR points at the exact integrated HEAD.
- Recover by reconciling durable state with real git, worktree, verifier,
  merge, and remote PR state.
- End in one of four explicit terminal states:
  `COMPLETE`, `RESIDUALS_READY`, `INFRA_FAILURE`, or `ABORTED`.

## Non-Goals

- Invoking literal `/goal`.
- Launching tmux sessions or nested Amplifier processes.
- Depending on private app-cli internals.
- Creating a new resolver.
- Creating a hidden runtime scheduler, generic work queue, or fixed-width pool
  that conceals the actual plan from the graph.
- Dynamically compiling child DOT during a run.
- Letting a lane certify its own success.
- Automatically delivering partial or residual work.
- Merging or deploying the PR after delivery.
- Replacing `goalify` or goal-batch-style composition.

## Rejected Alternatives

### Literal `/goal` lanes

Rejected because the DOT graph would wrap a second orchestration and recovery
system. The design would inherit tmux/process/environment sensitivity, split
observability across nested runs, and leave the outer graph unable to own the
true convergence budget.

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

The composition layer produces the approved plan. It is responsible for:

- decomposing the objective into bounded goals;
- defining scope-outs and ownership;
- identifying dependencies and collision risks;
- selecting exact lane and aggregate verifiers;
- defining optional qualitative criteria;
- assigning per-lane and run-wide budgets; and
- obtaining plan approval, unless the invocation carries explicit preapproval.

The runtime attractor receives only that fixed plan. It is responsible for:

- deterministic preflight;
- isolated worktree preparation;
- explicit dependency-wave execution;
- lane convergence;
- parent-side evidence checks;
- sequential integration and rollback of failed candidates;
- aggregate and coherence gates;
- terminal classification;
- recovery; and
- optional PR delivery.

### Top-level topology

```text
Start
  -> Reconcile durable state
  -> Validate/render plan and preflight
  -> Plan approval (or verify explicit preapproval)
  -> Prepare worktrees for Wave 1
  -> component fan-out
       -> goal_lane(A)
       -> goal_lane(B)
  -> tripleoctagon fan-in
  -> Collect artifacts; missing artifact = CRASHED
  -> Parent reruns lane verifiers at exact commit SHAs
  -> Enforce ownership
  -> Integrate passing commits one at a time
       -> aggregate verifier after each merge
       -> on failure: undo candidate merge, return evidence to owning lane
  -> Prepare next explicit dependency wave
  -> ...
  -> Aggregate verifier at final HEAD
  -> Fresh cross-lane coherence review at final HEAD
       -> correction edge to the explicit responsible lane when actionable
       -> residual classification when no bounded correction remains
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
wave. The graph contains no generic "get next lane" operation.

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
| Verifier | Exact, non-interactive command with a defined working directory and timeout. Exit zero means the mechanical condition passed; any other result is evidence to classify. |
| Qualitative criteria | Optional criteria that require an independent judgment gate after the mechanical verifier passes. |
| Attempt budget | Maximum verification-bearing attempts available to the lane. |

A lane may read outside its owned paths as needed to understand the repository,
but it may not modify outside them. Generated files and repository-wide files
must be assigned deliberately during composition; undeclared writes are an
ownership failure.

The lane result must bind evidence to:

- the lane ID;
- the approved plan revision;
- its dependency/base commit;
- the exact lane head commit;
- the verifier command and exit status;
- verifier output;
- ownership-check output;
- qualitative-review output, when applicable; and
- the attempt and budget counters.

The lane's prose summary is informational. The bound artifacts above determine
its disposition.

### Aggregate verifier contract

The approved plan also contains one immutable aggregate-verifier contract. It
declares:

- either the exact non-interactive command string or the repository-relative
  path of a checked-in executable script;
- the absolute path of the integration worktree as its working directory;
- a configured timeout in seconds;
- a SHA-256 verifier-definition hash;
- the stdout/stderr log location; and
- the JSON evidence-record location.

The verifier-definition hash covers the canonical command or script invocation,
the checked-in script bytes when a script is used, the absolute working
directory, and the configured timeout. Before every aggregate run, the wrapper
recomputes that definition hash and compares it with the approved value. A
mismatch is infrastructure failure; the changed verifier is not run as though
it were the approved definition of done.

Every invocation runs from the declared absolute integration-worktree path.
Combined stdout and stderr are written to an `attempt-N.log` file under the
run's integration evidence directory. An adjacent `attempt-N.json` evidence
record is written atomically with these required fields:

| Field | Contract |
|---|---|
| `schema_version` | Exact value `goal-plan.aggregate-verifier/v1`. |
| `attempt` | Positive integer for this aggregate-verifier invocation. |
| `head_sha` | Full SHA returned by `git rev-parse HEAD` immediately before the run. |
| `verifier_hash` | Recomputed SHA-256 verifier-definition hash. |
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

`goal_lane.dot` adapts the proven task-runner shape:

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

The lane does not mark itself `PASS`. It produces a candidate commit and
evidence. Parent verification assigns the final `PASS` disposition.

## Deterministic and LLM Boundaries

| Responsibility | Owner | Reason |
|---|---|---|
| Plan-schema validation, dependency-cycle checks, ownership-collision checks, repo/preflight checks | Deterministic nodes | These are exact predicates. |
| Worktree creation, cleanup, branch/base inspection | Deterministic nodes | Git state is observable and must be reproducible. |
| Advancing a lane goal and adapting implementation | LLM lane worker | The implementation path may change as the domain surprises the worker. |
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

1. Git object and worktree state observed by deterministic commands.
2. Verifier command, exit status, timeout status, and captured output.
3. Deterministic ownership and dependency checks.
4. Independent qualitative review tied to an exact commit, only for criteria
   that genuinely require judgment.
5. Remote API state for delivery.

Worker self-report is never in this hierarchy.

### Required lane artifacts

Each lane writes durable, lane-scoped artifacts under a run-scoped state
directory. The implementation may choose the exact serialization, but the
state must include:

- contract snapshot and hash;
- base and head commit SHAs;
- attempt/convergence record;
- latest verifier log and status;
- curated feedback and diagnosis;
- ownership diff/check result;
- optional qualitative verdict;
- candidate commit reference; and
- final disposition with a named reason.

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
| `reviewed_head` | Full commit SHA reviewed from actual repository state. |
| `verdict` | Exact value `PASS`, `ITERATE`, or `BLOCKED`; no other verdict is valid. |
| `findings` | JSON array of objects with required `id`, `summary`, `evidence` string array, and `disposition_detail` string fields. |
| `responsible_lane_ids` | Non-empty JSON array containing only lane IDs from the approved plan. |

For `review_kind: "lane"`, `responsible_lane_ids` must be the singleton array
containing the current lane ID. For `review_kind: "cross_lane"`, it contains one
or more approved lane IDs: all integrated lanes covered by a `PASS` review, or
the specific correction owners for `ITERATE` and `BLOCKED`.

A deterministic classifier schema-validates the artifact, resolves current
HEAD directly from Git, and requires `reviewed_head == current HEAD`. It then
routes:

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

Every lane runs in a dedicated git worktree and branch rooted at the integrated
HEAD that satisfies its dependencies. Lane state and evidence are namespaced by
run and lane ID.

Before a wave starts, deterministic preflight confirms:

- the repository identity and approved base HEAD;
- worktree paths are available or reconcilable;
- lane branches do not point at unexpected commits;
- the aggregate verifier is runnable;
- lane verifiers are present and non-interactive; and
- declared ownership for concurrently running lanes does not overlap.

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
pool. Fan-in waits for every branch and then mechanically classifies missing
artifacts before any integration begins.

## Parent Verification and Integration

For each candidate lane in stable plan order, the parent:

1. resolves the exact candidate commit from Git rather than from prose;
2. confirms the commit descends from the expected lane base;
3. reruns the lane verifier against that exact commit in a clean verification
   context;
4. checks the diff against the lane's owned paths;
5. checks required qualitative evidence, when declared;
6. records the parent verdict;
7. integrates only a `PASS` candidate into the integration branch; and
8. runs the aggregate verifier immediately after the integration.

If candidate integration or the aggregate verifier fails:

- the integration branch returns to the recorded pre-candidate HEAD;
- the failed candidate is not recorded as integrated;
- merge/verifier evidence is attached to the responsible lane;
- the lane re-enters its bounded correction loop from the current integrated
  base; and
- parent verification repeats before another integration attempt.

This is the integration-level corrective cycle. It prevents a lane-local green
result from poisoning the shared branch.

After every wave, the parent records the integrated HEAD and aggregate result
before the next dependency wave is prepared.

## Final Aggregate and Coherence Gates

After all runnable waves finish:

1. The deterministic aggregate verifier runs at final integrated HEAD.
2. A fresh independent reviewer reads the approved plan, lane evidence, final
   diff, and actual repository state at that HEAD.
3. The reviewer checks cross-lane coherence: compatible interfaces, preserved
   assumptions, no duplicated or contradictory implementations, and complete
   satisfaction of qualitative criteria.
4. The reviewer writes the versioned fresh-review artifact.
5. The shared deterministic classifier schema-validates it, requires
   `reviewed_head` to equal final integrated HEAD, and routes only the exact
   `PASS`, `ITERATE`, or `BLOCKED` verdicts.

Actionable coherence findings route to the explicitly responsible lane's
correction edge and must survive that lane's verifier, parent verification,
reintegration, aggregate verification, and a fresh coherence review. If
responsibility is ambiguous or correction budget is exhausted, the finding
becomes an evidence-backed residual rather than an invented pass.

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

## Human Gates

### Plan approval

The only pre-mutation gate presents:

- the full lane/dependency graph;
- ownership and collision analysis;
- lane and aggregate verifiers;
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
- repository identity and original base HEAD;
- run-wide and per-lane counters;
- worktree/branch/base/head mapping;
- lane contracts, evidence, and dispositions;
- parent-verification records;
- integration journal with pre-merge and post-merge HEADs;
- aggregate-verifier records after each merge;
- final aggregate and versioned fresh-review records;
- terminal classification;
- versioned `result.json`; and
- the versioned delivery-attempt ledger, branch, expected head, PR URL, observed
  remote head, and verification result.

State writes must be atomic. Human-readable reports are derived from structured
state; they are not the source of truth.

### Reconciliation rules

On restart, the graph compares state with reality:

1. Confirm the plan hash, repository identity, and original base still match.
2. Enumerate actual worktrees and branches.
3. Resolve recorded commits directly from Git.
4. Reclassify a purported completed lane whose artifact or commit is missing
   as `CRASHED` or `INFRA_FAILURE`, depending on whether lane work or the
   substrate is untrustworthy.
5. Rerun a verifier when the recorded result is absent, stale, or not bound to
   the recorded commit.
6. Reconcile the integration journal against the actual integration HEAD and
   Git ancestry before attempting another merge.
7. Rerun the aggregate verifier if the actual HEAD lacks a bound passing
   record.
8. Reject a fresh-review artifact whose `reviewed_head` does not equal actual
   HEAD.
9. Reconcile the delivery ledger, then query remote PR state at the ledger's
   exact expected head if delivery may already have occurred; never open a
   duplicate merely because local state is incomplete.

Reconciliation is idempotent. It skips work only when durable evidence and real
state agree. Ambiguous or contradictory infrastructure state fails loudly as
`INFRA_FAILURE`.

## Terminal and Failure Behavior

| Terminal | Required condition | Delivery behavior |
|---|---|---|
| `COMPLETE` | Every approved lane is `PASS`; all passing work is integrated; the aggregate verifier passes at final HEAD; fresh coherence review passes at that same HEAD; and, when delivery is enabled, the PR is independently confirmed at exact HEAD. | May auto-deliver one PR. |
| `RESIDUALS_READY` | All lanes are terminal or dependency-blocked, but at least one is not `PASS`, or final aggregate/coherence criteria remain unsatisfied. Passing work and every residual have evidence. | Never auto-delivers; requires residual disposition. |
| `INFRA_FAILURE` | Git/worktree state, verifier execution substrate, credentials, remote API, or recovery state cannot be trusted enough to classify product work honestly. | No delivery. |
| `ABORTED` | The plan was rejected/cancelled before mutation, or the operator explicitly stopped the run at an allowed gate. | No delivery. |

### Finalizer machine contract

Every terminal route passes through one deterministic finalizer. It atomically
writes the run root's versioned `result.json` with, at minimum:

- `schema_version` with exact value `goal-plan.result/v1`;
- `status` with exact value `COMPLETE`, `RESIDUALS_READY`, `INFRA_FAILURE`, or
  `ABORTED`;
- `plan_hash`;
- `integrated_head_sha`, or `null` when no integration HEAD exists;
- `lane_dispositions`;
- `aggregate_evidence_path`;
- `fresh_review_evidence_paths`;
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
equal the exact final integrated HEAD that passed aggregate and coherence
verification. A real PR at the wrong head is not successful delivery.

Delivery must not mutate that verified HEAD. If the delivery subgraph changes
local HEAD, the exact-head assertion fails; the run cannot claim `COMPLETE`
without re-establishing the aggregate and coherence evidence for the new HEAD.

Delivery has a hard limit of two attempts total for the run, including across
crash recovery. Before any network mutation, each attempt appends a durable
`started` entry to the run root's `delivery/attempts.jsonl`. Every ledger entry
uses schema version `goal-plan.delivery-attempt/v1` and records:

- `schema_version` with exact value `goal-plan.delivery-attempt/v1`;
- `attempt` as integer `1` or `2`;
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

## Anticipated File Changes

Implementation is expected to touch only:

```text
pipelines/goal_plan/goal_plan.dot
pipelines/goal_plan/goal_plan.md
pipelines/goal_plan/subgraphs/goal_lane.dot
pipelines/goal_plan/subgraphs/deliver_pr.dot
README.md
```

This design document does not implement those changes.

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

### Primary live smoke scenario

Run the real pipeline against a disposable GitHub repository with a known
aggregate verifier and three approved lanes:

- `lane_a` and `lane_b` own disjoint files and run concurrently in Wave 1.
- `lane_b` is seeded so its first verifier run fails with a stable, actionable
  error; it must consume one attempt, preserve the log, use curated feedback,
  and pass on a later attempt.
- `lane_c` depends on both Wave 1 lanes and cannot start until both commits are
  parent-verified, integrated sequentially, and followed by green aggregate
  checks.
- Delivery is enabled, producing one real PR.

The live smoke passes only if direct observation proves:

1. The rendered graph and persisted plan match the approved three-lane plan.
2. No mutation occurs before approval/preapproval validation.
3. Wave 1 lanes use distinct worktrees and actually overlap in execution.
4. `lane_b`'s first failure is visible and causes a corrective cycle rather
   than a silent pass or blind restart.
5. Parent verifier logs are produced for the exact candidate commits.
6. Ownership checks pass and would have rejected an out-of-scope write.
7. Integration occurs in stable order, with an aggregate-verifier record after
   each merge that names the exact HEAD and verifier hash and whose last-line
   token agrees with its JSON verdict.
8. `lane_c` starts only after both dependencies are integrated and green.
9. Final aggregate and fresh-review records are schema-valid and name the same
   final HEAD.
10. The delivery ledger records no more than two attempts, and the remote PR
    exists with a head SHA equal to its exact expected head.
11. `result.json`, `goal_plan.status`, and last-line token agree on `COMPLETE`
    only after all ten observations hold.

### Fault and recovery probes

The implementation is not ready until live probes also demonstrate:

- deleting one lane's required result before fan-in yields `CRASHED`, not a
  clean result;
- an impossible verifier exhausts its lane budget, produces a postmortem,
  blocks dependents by name, reaches `RESIDUALS_READY`, and opens no automatic
  PR;
- an out-of-ownership write is rejected even when the lane verifier passes;
- an aggregate failure after a candidate merge restores the pre-merge HEAD and
  routes evidence back to the responsible lane;
- changing the aggregate verifier definition after approval yields
  `AGGREGATE_VERIFY:INFRA` before the changed verifier runs;
- a missing, malformed, or stale fresh-review artifact is rejected and never
  advances as `PASS`;
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