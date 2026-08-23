# Goal Plan Attractor Implementation Plan

**Status:** Final plan, ready for implementation

**Design reference:** `docs/plans/2026-08-22-goal-plan-attractor-design.md`

**Design status:** Approved and amended 2026-08-23

## Goal

Implement the canonical `goal_plan_smoke` member of the approved Goal Plan
Attractor family.

The pipeline executes a fixed, reviewed dependency plan as visible DOT control
flow. It runs each lane in a separate Git worktree and a separate headless child
Attractor process, accepts only independently verified commits, integrates
passing commits sequentially, proves the aggregate after every merge, proves all
lane contracts again at one final HEAD, and optionally delivers one pull request
whose remote head is independently confirmed to equal that HEAD.

The implementation preserves the useful behavior of `/goal`, `goalify`, and
`goal-batch` without invoking those app-cli mechanisms at runtime.

## Non-Goals

- Do not invoke literal `/goal` or launch `amplifier run` child processes.
- Do not use tmux as a process container, liveness signal, or recovery anchor.
- Do not add a resolver or change the pipeline engine's CWD behavior.
- Do not build a hidden scheduler, work queue, fixed-width pool, or generic root
  graph that conceals lane topology from DOT.
- Do not compile child DOT during a run.
- Do not let a lane, review node, delivery node, or artifact certify its own
  success.
- Do not reimplement or wrap `goaltractor`; it remains the composition front end
  for arbitrary plans.
- Do not automatically deliver residual or partial work.
- Do not merge or deploy the delivered pull request.
- Do not support non-Linux process supervision in schema version 1.
- Do not add programmatic host interviewing; interactive approval is limited to
  an attached standalone console.

## Architecture

### Static parent program

`goal_plan_smoke.dot` is the reviewed parent program. It contains the exact
three-lane exemplar, explicit dependency waves, fan-out and fan-in, stable
integration order, bounded correction rounds, aggregate gates, final sweep,
delivery route, cleanup, and terminal carriers.

`plan.json` is immutable design-time and audit data. Runtime validates its
correspondence with DOT but never iterates its lane or wave arrays to decide what
runs next.

Wave 1 contains `lane_a` and `lane_b` as explicit concurrent branches. Wave 2
contains `lane_c`, which starts only after both Wave 1 lanes are parent-verified,
sequentially integrated, and followed by green aggregate verification.

### Process and worktree isolation

Each lane gets one branch, one worktree, and one headless child Attractor process
whose OS CWD is that worktree. The child runs `goal_lane.dot` with literal
`--cwd .` and `--on-human-gate fail`.

There is no tmux layer. A separately sealed `goal_plan_supervisor.py` process is
the accountable long-lived reaper for exactly one child. It launches the child
in a process group, remains alive until `wait` or `waitpid` returns, records raw
wait status, normalizes exit or signal truth, enforces timeout and cancellation,
proves the process group is empty, writes the authoritative result atomically,
and only then exits.

A child-written result is a routing hint. Missing supervisor result, nonzero
exit, signal, timeout, cancellation, or ambiguous process identity can never be
accepted as lane success even when expected artifacts exist.

### Trust and external state

A harness-owned immutable `launch_descriptor.json` is the first trust root. It
lives outside the target repository and every run or worktree root. A separately
installed external bootstrap authenticates itself, Git, the interpreter or
executable, the exact committed plan blob, and checked-out plan bytes before it
parses plan-controlled trust fields.

The bootstrap extracts exact committed runtime and supervisor blobs, seals them
beneath external `state_root`, records their binding, changes OS CWD to the
canonical target repository, and `execve`s the exact parent Attractor argv.
Checked-in Python remains source evidence; safety-critical commands use only the
sealed external runtime and supervisor prefixes.

Run state is external:

- `launch_control_root` holds the descriptor and harness-only blocked results.
- `state_root` holds admission, budgets, supervisor records, verifier evidence,
  feedback, integration journals, cleanup records, and terminal evidence.
- `worktree_root` holds only registered run-owned worktrees.
- `delivery_state_root` holds delivery state when pull-request delivery is enabled.

The roots are absolute, pairwise disjoint where applicable, and disjoint from
the target repository, Git common directory, compiled source, and all worktrees.

### Budgets and correction

A flock-protected ledger separately accounts for adaptive verifier-bearing
attempts, supervisor process launches, integration-correction launches, and the
run-wide `CLOCK_BOOTTIME` deadline. One counter cannot borrow from or reset
another.

Every lane or integration-correction adaptive attempt reserves a global attempt
immediately before model work. The reservation is consumed exactly once when the
child verifier envelope is classified. Starts, restarts, and polls do not count
as adaptive attempts.

Verifier failure feedback replaces stale guidance. The smoke requires one seeded
`lane_b` failure where unchanged or withheld feedback remains red, while changed
curated feedback produces a different candidate and a later pass.

### Verification and integration

Every dirty child attempt uses `ChildAttemptVerifierEnvelope`. It snapshots
HEAD, index, staged entries, the complete tracked, untracked, and ignored
filesystem, and compiled source before verification, then proves the candidate
is byte-identical afterward and all verifier output stayed external.

Every parent check uses `VerifierExecutionEnvelope`. Candidate verification runs
in a clean disposable detached worktree at the exact candidate commit.
Aggregate, affected-closure, pre-coherence, final-sweep, and post-sweep checks
run in the integration worktree at an immutable expected HEAD.

The parent verifies ownership and the candidate commit before integration.
Passing commits integrate one at a time in stable order. The aggregate verifier
runs after every merge. A product failure rolls back that candidate and returns
evidence to the responsible lane. Envelope or source-integrity failure routes to
infrastructure failure instead of product correction.

After all waves, a pre-coherence aggregate must pass. A fresh cross-lane review
may request a statically bounded integration correction. The parent then
re-verifies the affected transitive closure, reruns aggregate and coherence,
freezes one final HEAD, reruns every lane verifier there, and runs
`final-aggregate-after-sweep` at the same HEAD.

### Delivery, cleanup, and terminals

Pull-request delivery is optional and reachable only from the fully green final
HEAD. It adapts the proven `deliver_pr.dot` topology into a supervised child in
a clean disposable final-HEAD worktree. Generated delivery state is external.
The branch is compile-bound, created from the final HEAD, pushed without force,
and rejected on unexplained ownership or head collision. The parent independently
queries both the remote ref and pull request head.

Every intended terminal enters `PreTerminalCleanup` before publication. Cleanup
recomputes current trust and mutation authority, stops only identity-valid
process groups, and mutates Git only under current `FULL` authority. Terminal
state is finalized immutably and routed through exactly one of
`CompleteCarrier`, `ResidualsCarrier`, `InfraCarrier`, or `AbortedCarrier`.

The graph terminal states are `COMPLETE`, `RESIDUALS_READY`, `INFRA_FAILURE`,
and `ABORTED`. Harness failures before the graph starts remain separate
`PRELAUNCH_INFRASTRUCTURE_BLOCKED` or `RECOVERY_INFRASTRUCTURE_BLOCKED` outcomes
with exit code 78. Only `COMPLETE` is workflow success.

## Exact Intended File Footprint

Implementation may change exactly these checked-in files and no others:

```text
pipelines/goal_plan_smoke/goal_plan_smoke.dot
pipelines/goal_plan_smoke/plan.json
pipelines/goal_plan_smoke/goal_plan_smoke.md
pipelines/goal_plan_smoke/subgraphs/goal_lane.dot
pipelines/goal_plan_smoke/subgraphs/integration_correction.dot
pipelines/goal_plan_smoke/subgraphs/deliver_pr.dot
pipelines/goal_plan_smoke/python/goal_plan_bootstrap.py
pipelines/goal_plan_smoke/python/goal_plan_runtime.py
pipelines/goal_plan_smoke/python/goal_plan_supervisor.py
pipelines/goal_plan_smoke/python/tests/test_goal_plan_bootstrap.py
pipelines/goal_plan_smoke/python/tests/test_goal_plan_runtime.py
pipelines/goal_plan_smoke/python/tests/test_goal_plan_supervisor.py
pipelines/goal_plan_smoke/python/tests/test_goal_plan_trusted_runtime.py
README.md
```

External run artifacts belong beneath the four approved roots and are never
checked in.

## Cross-Task Rules

- Complete tasks in numerical order unless a task explicitly permits internal
  parallel work.
- Keep the three Python implementation files standard-library-only.
- Use explicit UTF-8, canonical JSON, atomic writes, required fsyncs, absolute
  executable paths, and argv arrays rather than shell-built commands.
- Never modify managed Amplifier cache files.
- Before editing DOT in Tasks 6 through 10, reread `AGENTS.md`, `docs/primer.md`,
  and `docs/RUBRIC.md`.
- Reuse the nearest proven graph topology, especially delivery topology.
- Commit the history anchor before materializing files that refer to it.
- Create the compiled-program commit only after all hashes and graph-plan
  correspondence values are final.
- Treat every self-reported external side effect as untrusted until a separate
  deterministic check observes real state.

## Ordered Tasks

### Task 1: Create the history anchor commit
**Outcome:** `goal_plan_smoke.md` is committed alone as the identity-stable
history anchor. Its parent is the approved product baseline, and the file omits
values that would create a Git content-address cycle.
**Files:**
- Create `pipelines/goal_plan_smoke/goal_plan_smoke.md`.
**Steps:**
1. Record current HEAD as `product_base_sha`.
2. Write a concise guide covering the static graph, prerequisites, terminals,
   and verification route.
3. Exclude embedded product-base, plan-commit, execution-source, descriptor, and
   blob identity values.
4. Commit only the guide with repository-required attribution.
5. Record the new commit as `plan_commit_sha` and its parent as product baseline.
**Dependencies:** None.
**Verification:** Run
`test "$(git diff-tree --no-commit-id --name-only -r "$PLAN_COMMIT_SHA")" = "pipelines/goal_plan_smoke/goal_plan_smoke.md" && test "$(git rev-parse "$PLAN_COMMIT_SHA^")" = "$PRODUCT_BASE_SHA"`.
The command must exit 0.

### Task 2: Implement descriptor authentication and trusted bootstrap
**Outcome:** The external bootstrap authenticates descriptor-bound launcher,
Git, interpreter, committed plan blob, and checked-out plan bytes before reading
plan-controlled trust, then seals runtime blobs and launches the parent from
canonical repository CWD.
**Files:**
- Create `pipelines/goal_plan_smoke/python/goal_plan_bootstrap.py`.
- Exercise it through `test_goal_plan_bootstrap.py` in Task 11.
**Steps:**
1. Implement strict descriptor and command parsing with unknown-field, path,
   writable-file, prefix, identity, environment, and hash rejection.
2. Read the plan blob through descriptor-bound Git and require checked-out byte
   equality before validating the plan launcher binding.
3. Implement exact-blob extraction, no-replace staging, fsync, non-writable
   sealing, reread verification, and immutable runtime binding output.
4. Rehydrate only an absent bundle; reject a present mismatching bundle.
5. Validate parent argv, change to target repo, prove CWD, and call `execve`.
6. Emit the defined external blocked result and exit 78 when trust fails.
**Dependencies:** Task 1.
**Verification:** `python3 -m pytest pipelines/goal_plan_smoke/python/tests/test_goal_plan_bootstrap.py -q` exits 0 and its spy proves no plan binding read precedes descriptor, identity, and committed-blob validation.

### Task 3: Implement the accountable per-child supervisor
**Outcome:** Every lane, correction, and delivery launch has one reaper that owns
the direct child, authoritative `waitpid` truth, timeout, cancellation, logs,
process-group cleanup, and durable result.
**Files:**
- Create `pipelines/goal_plan_smoke/python/goal_plan_supervisor.py`.
- Exercise it through `test_goal_plan_supervisor.py` in Task 11.
**Steps:**
1. Implement strict `self-check`, `run`, `poll`, `terminate`, and `reconcile`.
2. Bind intent, contract, reservation, process-run ID, CWD, provider, runner,
   environment, and external result paths.
3. Launch a direct child in a new group and atomically write ledger then ack.
4. Wait, preserve raw status, normalize exit or signal, enforce TERM/grace/KILL,
   prove group emptiness, hash logs, and atomically write the result.
5. Make poll wait internally for at most 30 seconds and remaining deadlines.
6. Reconcile through bounded exact process-run discovery; process absence and
   child artifacts never imply success.
**Dependencies:** Task 2 defines the sealed supervisor identity and prefix.
**Verification:** `python3 -m pytest pipelines/goal_plan_smoke/python/tests/test_goal_plan_supervisor.py -q` exits 0 with distinct cases for exit 0, nonzero exit, signal, timeout, missing result, and orphan cleanup.

### Task 4: Implement runtime admission, roots, budgets, and worktrees
**Outcome:** The sealed runtime validates the static program and trust bindings,
protects external roots, accounts for budgets, and records every run-owned
worktree lifecycle.
**Files:**
- Create `pipelines/goal_plan_smoke/python/goal_plan_runtime.py`.
- Exercise it through runtime and trusted-runtime tests in Task 11.
**Steps:**
1. Validate the sealed runtime binding before every safety command.
2. Admit repository identity, source ancestry, parent CWD, runner CWD, invoked
   DOT, provider, approval transport, compiled source, graph-plan correspondence,
   and engine-step bounds.
3. Enforce preapproval and postapproval root safety with canonical paths.
4. Record lane, integration, candidate, and delivery worktrees with exact branch,
   HEAD, common directory, registration, lifecycle, and recovery proof.
5. Implement flocked atomic accounting for attempts, process launches,
   correction rounds, and the global deadline.
6. Close the ledger permanently at deadline and block later reservations.
**Dependencies:** Tasks 2 and 3.
**Verification:** `python3 -m pytest pipelines/goal_plan_smoke/python/tests/test_goal_plan_runtime.py -q -k 'admission or root or budget or worktree or deadline'` exits 0 and concurrent reservations never exceed ceilings.

### Task 5: Implement child and parent verifier envelopes
**Outcome:** Dirty adaptive state and clean parent verification state are bound
to exact pre/post evidence, and verifier mutation discards an apparent pass as
infrastructure failure.
**Files:**
- Modify `pipelines/goal_plan_smoke/python/goal_plan_runtime.py`.
- Exercise envelopes through `test_goal_plan_runtime.py` in Task 11.
**Steps:**
1. Implement the dirty child envelope over HEAD, raw index, staged projection,
   complete non-Git filesystem, compiled source, and output baseline.
2. Run child verifiers read-only with all generated output external.
3. Recompute the candidate snapshot after exit or timeout and require equality.
4. Implement the clean parent envelope with expected HEAD, clean ignored-aware
   status, full manifest, compiled-source gates, and output containment.
5. Support candidate, aggregate-after-merge, affected-closure, pre-coherence,
   final-sweep, and final-aggregate verification kinds.
6. Bind classification to verifier definition and attempt or parent identity.
**Dependencies:** Task 4.
**Verification:** `python3 -m pytest pipelines/goal_plan_smoke/python/tests/test_goal_plan_runtime.py -q -k 'child_attempt_envelope or verifier_envelope'` exits 0, including mutation plus exit zero classified as infrastructure failure.

### Task 6: Author the bounded child convergence graphs
**Outcome:** `goal_lane.dot` performs feedback-informed bounded lane correction,
and `integration_correction.dot` performs bounded shared-branch correction using
the same accounting and child verifier envelope.
**Files:**
- Create `pipelines/goal_plan_smoke/subgraphs/goal_lane.dot`.
- Create `pipelines/goal_plan_smoke/subgraphs/integration_correction.dot`.
- Modify runtime only for deterministic child commands required by these graphs.
**Steps:**
1. Copy the proven orient, reserve, attempt, verify, classify, feedback,
   diagnosis, and honest exhaustion shape.
2. Reserve immediately before each adaptive node and consume exactly once after
   complete envelope classification.
3. Replace stale feedback and diagnose repeated failure signatures.
4. Let lane success produce only a candidate commit and evidence.
5. Restrict integration correction to current integration branch, responsible
   ownership union, and declared seams.
6. Make blocker and exhaustion exits explicit and evidence-bearing.
**Dependencies:** Tasks 4 and 5.
**Verification:** Both child DOT files pass strict Attractor lint, and the lane test proves withheld feedback remains red while changed feedback changes the candidate hash and later passes.

### Task 7: Author static parent waves and sequential integration
**Outcome:** The parent visibly runs Wave 1 lanes, waits for authoritative
results, parent-verifies candidates, integrates sequentially with aggregate
proof after each merge, and only then starts `lane_c`.
**Files:**
- Create `pipelines/goal_plan_smoke/goal_plan_smoke.dot`.
- Create `pipelines/goal_plan_smoke/plan.json`, finalized in Task 10.
- Modify runtime for collection, ownership, integration, rollback, and journals.
**Steps:**
1. Encode each lane launch and monitor branch explicitly in DOT.
2. Use component fan-out and triple-octagon fan-in only for Wave 1.
3. Classify missing supervisor result as infrastructure failure and missing child
   result as crashed, never as empty success.
4. Parent-verify each candidate in a registered detached exact-commit worktree.
5. Enforce ownership and categorically exclude compiled pipeline paths.
6. Integrate in stable order and run aggregate after each merge; restore the
   pre-merge HEAD on product failure.
7. Gate `lane_c` on both dependencies being integrated and aggregate-green.
**Dependencies:** Tasks 3 through 6.
**Verification:** Static topology and live fixtures prove `lane_a` and `lane_b` overlap, `lane_c` starts later, and the journal contains one green aggregate record after each accepted merge.

### Task 8: Add coherence, final sweep, recovery, and terminals
**Outcome:** Late cross-lane findings converge through bounded correction, final
proof binds one HEAD, recovery reconciles state with reality, and cleanup selects
one honest terminal before publication.
**Files:**
- Modify `goal_plan_smoke.dot`, `plan.json`, and `goal_plan_runtime.py`.
**Steps:**
1. Run pre-coherence aggregate before every fresh coherence review.
2. Expand correction ordinals statically and reserve one correction round plus
   one process launch before each correction supervisor starts.
3. Compute responsible set and affected closure, invalidate stale proof, and
   rerun closure lanes, closure aggregate, pre-coherence aggregate, and review.
4. Freeze final HEAD after coherence; rerun every lane and
   `final-aggregate-after-sweep` there.
5. Reconcile budgets, supervisors, worktrees, candidates, integration,
   corrections, and proof before resuming action.
6. Implement current cleanup authority, status-specific cleanup, immutable
   finalization, four carriers, canonical token conditions, and failure routes.
7. Preserve residual, infrastructure, and aborted states as non-success.
**Dependencies:** Task 7.
**Verification:** A terminal-contract test proves all four states are reachable, all eight token edges require exact token plus successful tool outcome, and every tool command has a separate infrastructure route.

### Task 9: Add external-state delivery and exact-head proof
**Outcome:** Delivery runs as a supervised child from a clean final-HEAD
worktree, writes generated state only outside Git, uses one immutable no-force
branch contract, and passes only after independent remote proof.
**Files:**
- Create `pipelines/goal_plan_smoke/subgraphs/deliver_pr.dot`.
- Modify parent DOT, plan, and runtime.
**Steps:**
1. Adapt proven delivery topology and move all generated state external.
2. Compile one canonical branch, full ref, remote, no-force refspec, collision
   policy, and final-HEAD source.
3. Reject stale, unexplained, differently owned, wrong-remote, or wrong-head
   branch collisions before network mutation.
4. Register a clean delivery worktree and prove pre/post HEAD, status, manifest,
   and compiled-source equality.
5. Supervise delivery with the same reaper and allow at most two attempts.
6. Independently query remote ref and pull request at the frozen final HEAD.
7. Route unverifiable delivery to infrastructure failure without a third attempt.
**Dependencies:** Task 8.
**Verification:** In a temporary remote,
`test "$(gh pr view "$PR_URL" --json headRefOid --jq .headRefOid)" = "$FINAL_HEAD"`
exits 0, and recorded push argv contains no force option.

### Task 10: Finalize the immutable compiled family and documentation
**Outcome:** The static family is content-bound, graph and plan agree, source
hashes are final, the containing execution-source commit is recorded without
self-reference, and README exposes the pipeline.
**Files:**
- Finalize all 13 files under `pipelines/goal_plan_smoke/`.
- Modify `README.md` with one concise pipeline entry.
**Steps:**
1. Canonicalize the plan with lanes, waves, integration order, ownership,
   verifiers, budgets, trust bindings, delivery, and terminal contracts.
2. Embed plan hash and static correspondence values in parent DOT.
3. Prove every lane, dependency, wave, correction ordinal, integration step,
   budget, verifier, child hash, delivery route, and terminal agrees.
4. Create the compiled-program commit while preserving the earlier anchor.
5. Treat that containing commit as `execution_source_sha` and prove ancestry.
6. Ensure runtime never mutates checked-in pipeline bytes.
**Dependencies:** Tasks 1 through 9.
**Verification:** `git diff-tree --no-commit-id --name-only -r "$EXECUTION_SOURCE_SHA" | sort` equals the approved compiled-commit footprint, and graph-plan correspondence validation exits 0.

### Task 11: Add tests, fault matrix, lint, render, and doc checks
**Outcome:** Focused unit, integration, and recovery tests cover the named fault
matrix; every DOT strict-lints and renders; Python checks pass; docs match graph.
**Files:**
- Create all four test files in the exact footprint.
- Modify README and companion guide only if verification exposes a real mismatch.
**Steps:**
1. Cover bootstrap trust order, Git blobs, materialization, rehydration, parent
   CWD and blocked exit 78.
2. Cover roots, source, worktrees, ownership, concurrent budgets, deadline, both
   envelopes, rollback, correction, final sweep, cleanup, carriers, and delivery.
3. Cover supervisor exits, signals, timeout, cancellation, crashes, discovery,
   stale identity, atomic result, zombies, and orphan groups.
4. Run the approved complete fault matrix and preserve command, exit, evidence,
   and disposition for every case.
5. Strict-lint the parent and three subgraphs with the immutable runner prefix.
6. Render all four DOT files to non-empty external PNG evidence with hashes.
7. Run Python checks and system-Python tests without managed-cache mutation.
8. Audit every DOT against `docs/RUBRIC.md` and check docs against topology.
**Dependencies:** Task 10.
**Verification:** One combined quality command runs Python checks,
`python3 -m pytest pipelines/goal_plan_smoke/python/tests -q`, four strict lints,
four non-empty Graphviz renders, footprint validation, and `git diff --check`;
every component exits 0.

### Task 12: Run the real end-to-end smoke
**Outcome:** A temporary GitHub-backed repository demonstrates trusted bootstrap,
concurrent isolated lanes, waitpid truth, feedback-dependent correction, parent
re-verification, sequential integration, aggregate after each merge, bounded
coherence correction, final proof, cleanup, terminal publication, and exact-head
pull-request delivery.
**Files:**
- Change no checked-in file.
- Write smoke evidence only beneath approved external roots.
**Steps:**
1. Create the temporary remote, compile-bound branch, roots, descriptor, staged
   bootstrap, provider credentials, and immutable runner prefixes.
2. Launch only through bootstrap self-check, materialization, and parent handoff;
   prove parent CWD and source binding before mutation.
3. Observe `lane_a` and `lane_b` concurrently in distinct worktrees and processes.
4. Prove supervisor wait status, not artifacts, determines child truth.
5. Force `lane_b` failure; show unchanged feedback stays red and changed curated
   feedback produces a different candidate and later pass.
6. Observe parent candidate verification, ownership, stable merges, and aggregate
   proof after every merge before `lane_c` starts.
7. Force one coherence iteration, affected-closure proof, fresh coherence, full
   final sweep, and post-sweep aggregate at one HEAD.
8. Deliver through the clean external-state worktree and independently prove
   remote ref and pull request both point to final HEAD.
9. Observe cleanup remove all run-owned worktrees and process groups before
   finalizer and `CompleteCarrier` evidence.
10. Inject representative faults for nonzero artifact-producing child, missing
    result, verifier mutation, source drift, deadline, recovery, branch collision,
    and restricted cleanup.
**Dependencies:** Task 11 and all mandatory external prerequisites.
**Verification:** The harness exits 0 only when result status and carrier are
`COMPLETE`, cleanup reports no live process or run-owned worktree, all proof
binds the accepted history, and queried pull-request head equals final HEAD.

## Acceptance Checklist

- [ ] The checked-in footprint is exactly the listed 13 pipeline files plus
  `README.md`.
- [ ] Parent DOT directly shows lanes, waves, corrections, integration, delivery,
  and terminals.
- [ ] `lane_a` and `lane_b` run concurrently in distinct worktrees and child
  Attractor processes.
- [ ] Each child and box session resolves relative CWD to its assigned worktree.
- [ ] No tmux process or status signal participates in execution.
- [ ] Every child has one accountable reaper and raw wait status owns exit truth.
- [ ] An artifact-producing nonzero child remains non-pass.
- [ ] Unchanged feedback remains red; changed feedback changes the candidate and
  produces later green proof.
- [ ] Dirty child verification preserves HEAD, index, staged, tracked, untracked,
  ignored, and compiled-source state.
- [ ] Parent re-verifies the exact candidate commit in a clean detached worktree.
- [ ] Ownership passes before integration and rejects compiled-pipeline writes.
- [ ] Passing commits integrate sequentially in stable order.
- [ ] Aggregate verification runs after every merge.
- [ ] Failed post-merge aggregate restores pre-merge HEAD and returns evidence.
- [ ] Dependencies start only after parent pass, integration, and green aggregate.
- [ ] Coherence correction uses current integration branch, one supervised child,
  one correction reservation, and the affected closure.
- [ ] Coherence, final lane sweep, and post-sweep aggregate bind one final HEAD.
- [ ] Attempts, process launches, corrections, and deadline stay separately
  bounded and recovery-safe.
- [ ] Generated state is external; source remains immutable; verified worktrees
  gain no `.resolve` state.
- [ ] Recovery validates descriptor and runtime before mutating processes or Git.
- [ ] Cleanup signals only identity-valid groups and mutates Git only under
  current `FULL` authority.
- [ ] Successful cleanup leaves no live child or non-preserved run-owned worktree
  or registration.
- [ ] All four terminal states remain distinct and only `COMPLETE` is success.
- [ ] Harness-only blocked outcomes use external evidence, exact token, and exit 78.
- [ ] Delivery uses the compile-bound branch and exact no-force refspec.
- [ ] Parent independently confirms remote ref and pull request at final HEAD.
- [ ] Strict lint, Graphviz render, Python checks, full tests, fault matrix,
  footprint, and `git diff --check` all pass with evidence.

## Honest Blockers

Graphviz is mandatory. If `dot` is unavailable, rendering fails, a PNG is empty,
or render evidence cannot be recorded, Task 11 and final acceptance are blocked.
Static reading or strict lint does not waive rendering.

A delivery-enabled smoke requires a temporary remote plus credentials and
permissions to create and query a branch and pull request. Without them,
non-delivery checks may run, but Task 12 and full acceptance remain blocked. The
report names the missing credential or permission class without printing secrets.

Provider credentials, a source-backed Attractor runner with required flags,
Linux procfs, Git worktree support, or pairwise-disjoint external roots can also
block the live smoke. Such a gap is infrastructure evidence, not a pass.

## Explicit Execution Order

Execute Tasks 1 through 12 in order. Tasks 2 through 5 may use short internal
increments, but Task 6 waits for stable bootstrap, supervisor, runtime, budget,
worktree, and envelope interfaces. Task 7 consumes them. Tasks 8 and 9 extend a
proven base parent. Task 10 freezes hashes only after source and DOT are final.
Task 11 verifies that compiled program. Task 12 is final live proof and changes
no checked-in file.

## Stop Condition

Stop successfully only when all twelve task outcomes are complete, every
acceptance item has real evidence, the footprint is exact, all gates pass,
cleanup leaves the required terminal state, and the real delivery smoke
independently proves the pull request points to the exact final integrated HEAD.

Stop blocked rather than claiming success when a mandatory prerequisite or gate
cannot be satisfied. Name the missing capability and evidence that would clear
it. Stop as failed when trustworthy evidence shows a contract violation. Never
convert blocked, residual, infrastructure, or aborted outcomes into completion.