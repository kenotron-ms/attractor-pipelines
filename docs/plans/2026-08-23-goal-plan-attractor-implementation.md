# Goal Plan Attractor Implementation Plan

**Status:** Final plan, ready for implementation

**Design reference:** `docs/plans/2026-08-22-goal-plan-attractor-design.md`

**Design status:** Approved and amended 2026-08-23

## Goal

Implement the canonical `goal_plan_smoke` member of the approved Goal Plan
Attractor family.

The finished pipeline must execute a fixed, reviewed dependency plan as visible
DOT control flow. It must run each lane in a separate Git worktree and a separate
headless child Attractor process, accept only independently verified commits,
integrate passing commits sequentially, prove the aggregate after every merge,
prove all lane contracts again at one final HEAD, and optionally deliver one
pull request whose remote head is independently confirmed to equal that HEAD.

The implementation preserves the useful behavior of `/goal`, `goalify`, and
`goal-batch` without invoking those app-cli mechanisms at runtime.

## Non-Goals

- Do not invoke literal `/goal` or launch `amplifier run` child processes.
- Do not use tmux as a process container, liveness signal, or recovery anchor.
- Do not add a resolver or change the pipeline engine's CWD behavior.
- Do not build a dynamic scheduler, work queue, fixed-width pool, or generic root
  graph that hides lane topology from DOT.
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
delivery route, cleanup, and four terminal carriers.

`plan.json` is immutable design-time and audit data. Runtime validates its
correspondence with DOT, but never iterates its lane or wave arrays to decide
what runs next.

Wave 1 contains `lane_a` and `lane_b` as explicit concurrent branches. Wave 2
contains `lane_c`, which cannot start until both Wave 1 lanes are parent-verified,
sequentially integrated, and followed by green aggregate verification.

### Process and worktree isolation

Each lane gets one dedicated Git branch, one dedicated worktree, and one
headless child Attractor process whose OS CWD is that worktree. The child runs
`goal_lane.dot` with literal `--cwd .` and `--on-human-gate fail`.

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
Checked-in Python remains source evidence; safety-critical runtime commands use
only the sealed external runtime and supervisor prefixes.

All ordinary run state is external:

- `launch_control_root` holds the immutable descriptor and harness-only blocked
  results.
- `state_root` holds admission, budgets, supervisor records, verifier evidence,
  feedback, integration journals, cleanup records, and terminal evidence.
- `worktree_root` holds only registered run-owned worktrees.
- `delivery_state_root` holds delivery logs, ledgers, checkpoints, and results
  when pull-request delivery is enabled.

The four roots are absolute, pairwise disjoint where applicable, and disjoint
from the target repository, Git common directory, compiled source, and every
worktree.

### Budgets and correction

A flock-protected external ledger separately accounts for adaptive verifier-bearing
attempts, supervisor process launches, integration-correction launches, and the
run-wide `CLOCK_BOOTTIME` deadline. One counter cannot borrow from or reset
another.

Every lane or integration-correction adaptive attempt reserves a global attempt
immediately before model work. The reservation is consumed exactly once when the
child verifier envelope is classified. Starts, restarts, and polls do not count
as adaptive attempts.

Verifier failure feedback replaces stale guidance. The smoke requires one seeded
`lane_b` failure where unchanged or withheld feedback remains red, while changed
curated feedback produces a different candidate state and a later pass.

### Verification and integration

Every dirty child attempt uses `ChildAttemptVerifierEnvelope`. It snapshots
HEAD, index, staged entries, the complete tracked, untracked, and ignored
filesystem, and compiled source before verification; after verification it
proves the candidate is byte-identical and all verifier output stayed beneath an
external output root.

Every parent lane or aggregate check uses `VerifierExecutionEnvelope`. Candidate
verification runs in a clean disposable detached worktree at the exact candidate
commit. Aggregate, affected-closure, pre-coherence, final-sweep, and post-sweep
checks run in the integration worktree at an immutable expected HEAD.

The parent verifies ownership and the candidate commit before integration.
Passing commits integrate one at a time in stable order. The aggregate verifier
runs after every merge. A product aggregate failure rolls back that candidate
and returns evidence to the responsible lane. Envelope or source-integrity
failure routes to infrastructure failure instead of product correction.

After all waves, a pre-coherence aggregate must pass. A fresh cross-lane review
may request one statically bounded integration correction. The parent then
re-verifies the affected transitive closure, reruns the aggregate and coherence
checks, freezes one final HEAD, reruns every lane verifier there, and finally
runs `final-aggregate-after-sweep` at the same HEAD.

### Delivery, cleanup, and terminals

Pull-request delivery is optional and reachable only from the fully green final
HEAD. It adapts the proven `deliver_pr.dot` topology into a supervised child
running in a clean disposable final-HEAD worktree. All generated delivery state
is external. The branch is compile-bound, created from the exact final HEAD,
pushed without force, and rejected on unexplained ownership or head collision.
The parent independently queries both the remote ref and pull request head.

Every intended terminal route enters `PreTerminalCleanup` before terminal state
is published. Cleanup recomputes current trust and mutation authority, stops only
identity-valid process groups, and mutates Git only under current `FULL`
authority. Terminal state is then finalized immutably and routed through exactly
one of `CompleteCarrier`, `ResidualsCarrier`, `InfraCarrier`, or
`AbortedCarrier`.

The only graph terminal states are:

- `COMPLETE`
- `RESIDUALS_READY`
- `INFRA_FAILURE`
- `ABORTED`

Harness failures before the parent graph starts remain separate
`PRELAUNCH_INFRASTRUCTURE_BLOCKED` or `RECOVERY_INFRASTRUCTURE_BLOCKED` outcomes
with exit code 78.

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

The implementation creates external run artifacts beneath the four approved
roots, but those artifacts are never checked in.

## Cross-Task Rules

- Complete tasks in numerical order unless a task explicitly permits parallel
  work.
- Keep `goal_plan_bootstrap.py`, `goal_plan_runtime.py`, and
  `goal_plan_supervisor.py` standard-library-only.
- Use explicit UTF-8 for text I/O, canonical JSON, atomic writes, fsync where the
  design requires durability, absolute executable paths, and argv arrays rather
  than shell-built commands.
- Never modify managed Amplifier cache files.
- Before editing any DOT in Tasks 6 through 10, reread `AGENTS.md`,
  `docs/primer.md`, and `docs/RUBRIC.md`.
- Reuse the nearest proven graph topology, especially the shared delivery
  topology, rather than inventing a second delivery protocol.
- Commit the history anchor before materializing files that refer to it.
- Create the compiled-program commit only after all source hashes and graph-plan
  correspondence values are final.
- Treat every self-reported external side effect as untrusted until a separate
  deterministic check observes real state.

## Ordered Tasks

### Task 1: Create the history anchor commit

**Outcome:** `goal_plan_smoke.md` is committed alone as the identity-stable
history anchor. Its parent is the approved product baseline, and the file does
not contain values that would create a Git content-address cycle.

**Files:**

- Create `pipelines/goal_plan_smoke/goal_plan_smoke.md`.

**Steps:**

1. Record current HEAD as `product_base_sha`.
2. Write a concise companion guide describing the static three-lane graph,
   prerequisites, terminal contract, and verification route.
3. Exclude embedded product-base, plan-commit, execution-source, descriptor, and
   blob identity values from the guide.
4. Commit only the companion guide with the repository-required attribution.
5. Record the new commit as `plan_commit_sha` and its parent as the immutable
   product baseline.

**Dependencies:** None.

**Verification:** Run
`test "$(git diff-tree --no-commit-id --name-only -r "$PLAN_COMMIT_SHA")" = "pipelines/goal_plan_smoke/goal_plan_smoke.md" && test "$(git rev-parse "$PLAN_COMMIT_SHA^")" = "$PRODUCT_BASE_SHA"`.
The command must exit 0.

### Task 2: Implement descriptor authentication and trusted bootstrap

**Outcome:** The external bootstrap authenticates descriptor-bound launcher,
Git, interpreter, committed plan blob, and checked-out plan bytes before reading
plan-controlled trust, then materializes or rehydrates sealed runtime blobs and
launches the parent from canonical repository CWD.

**Files:**

- Create `pipelines/goal_plan_smoke/python/goal_plan_bootstrap.py`.
- Exercise it through `test_goal_plan_bootstrap.py` in Task 11.

**Steps:**

1. Implement strict descriptor and command parsing with unknown-field,
   path-alias, writable-file, prefix, identity, environment, and hash rejection.
2. Read the exact plan blob through descriptor-bound Git and require byte equality
   with the checked-out plan before validating the plan's launcher binding.
3. Implement exact-blob runtime and supervisor extraction, no-replace staging,
   fsync, non-writable sealing, reread verification, and immutable binding output.
4. Implement deterministic absent-bundle rehydration and reject a present but
   mismatching bundle instead of repairing it.
5. Implement parent argv validation, `chdir` to canonical target repo, CWD proof,
   closed environment construction, and direct `execve`.
6. Emit only the defined external blocked result and exit 78 when first launch or
   recovery cannot establish trust.

**Dependencies:** Task 1.

**Verification:** `python3 -m pytest pipelines/goal_plan_smoke/python/tests/test_goal_plan_bootstrap.py -q` exits 0 and its trust-order spy proves no plan binding read precedes descriptor, identity, and committed-blob validation.

### Task 3: Implement the accountable per-child supervisor

**Outcome:** Every lane, correction, and delivery launch has one long-lived
reaper that owns the direct child, authoritative `waitpid` truth, timeout,
cancellation, logs, process-group cleanup, and durable result.

**Files:**

- Create `pipelines/goal_plan_smoke/python/goal_plan_supervisor.py`.
- Exercise it through `test_goal_plan_supervisor.py` in Task 11.

**Steps:**

1. Implement strict `self-check`, `run`, `poll`, `terminate`, and `reconcile`
   command surfaces with exact ordered arguments.
2. Bind intent, launch contract, budget reservation, process-run ID, CWD,
   provider, runner identity, environment, and external result paths.
3. Launch the child as a direct child in a new process group and atomically write
   ledger then acknowledgement after validating procfs identity.
4. Wait for the child, preserve raw wait status, normalize exit or signal,
   enforce TERM/grace/KILL, prove group emptiness, hash logs, and atomically write
   the supervisor result.
5. Make poll wait internally for at most 30 seconds and no longer than remaining
   child or run deadline.
6. Reconcile intent-without-ledger through bounded exact process-run discovery;
   never infer success from process absence or child artifacts.

**Dependencies:** Task 2 defines the sealed supervisor identity and prefix.

**Verification:** `python3 -m pytest pipelines/goal_plan_smoke/python/tests/test_goal_plan_supervisor.py -q` exits 0 and includes distinct passing assertions for normal exit 0, nonzero exit, signal termination, timeout, missing result, and orphan cleanup.

### Task 4: Implement runtime admission, roots, budgets, and worktrees

**Outcome:** The sealed runtime owns all post-handoff deterministic safety
operations, validates the static program and trust bindings, protects external
roots, accounts for all budgets, and records every run-owned worktree lifecycle.

**Files:**

- Create `pipelines/goal_plan_smoke/python/goal_plan_runtime.py`.
- Exercise it through `test_goal_plan_runtime.py` and
  `test_goal_plan_trusted_runtime.py` in Task 11.

**Steps:**

1. Implement strict runtime binding validation before every safety-critical
   command and reject target-working-copy execution as a substitute.
2. Implement admission for repository identity, source ancestry, parent CWD,
   literal runner CWD, invoked DOT identity, provider, approval transport,
   compiled-source manifest, graph-plan correspondence, and engine-step bounds.
3. Implement preapproval and postapproval root safety with canonical path and
   symlink checks.
4. Implement `run-owned-worktrees.json` transitions for lane, integration,
   candidate, and delivery worktrees, including exact branch, HEAD, common-dir,
   registration, and recovery proof.
5. Implement flocked, atomic, boot-bound accounting for adaptive attempts,
   process launches, correction rounds, and the global deadline.
6. Close the ledger permanently at the deadline and block every later launch or
   attempt reservation.

**Dependencies:** Tasks 2 and 3.

**Verification:** `python3 -m pytest pipelines/goal_plan_smoke/python/tests/test_goal_plan_runtime.py -q -k 'admission or root or budget or worktree or deadline'` exits 0 and concurrent reservation tests never exceed any configured ceiling.

### Task 5: Implement child and parent verifier envelopes

**Outcome:** Dirty adaptive state and clean parent verification state are both
bound to exact pre/post evidence, and any verifier-caused mutation discards an
apparent pass as infrastructure failure.

**Files:**

- Modify `pipelines/goal_plan_smoke/python/goal_plan_runtime.py`.
- Exercise envelope behavior through `test_goal_plan_runtime.py` in Task 11.

**Steps:**

1. Implement the dirty child envelope over HEAD, raw index, staged projection,
   complete non-Git filesystem, compiled source, and external output baseline.
2. Run child verifiers read-only with temp, cache, coverage, logs, and results
   beneath one external output root.
3. Recompute the entire candidate snapshot after verifier exit or timeout and
   require exact equality before classifying product pass or fail.
4. Implement the clean parent envelope with immutable expected HEAD, clean
   ignored-aware status, full worktree manifest, compiled-source gates, and
   external output containment.
5. Support candidate lane, aggregate-after-merge, affected-closure,
   pre-coherence, final-sweep, and final-aggregate verification kinds.
6. Bind every envelope classification to the exact verifier definition and
   attempt or parent invocation identity.

**Dependencies:** Task 4.

**Verification:** `python3 -m pytest pipelines/goal_plan_smoke/python/tests/test_goal_plan_runtime.py -q -k 'child_attempt_envelope or verifier_envelope'` exits 0, including a mutation-plus-exit-zero case that is classified as infrastructure failure.

### Task 6: Author the bounded child convergence graphs

**Outcome:** `goal_lane.dot` performs feedback-informed bounded lane correction,
and `integration_correction.dot` performs bounded shared-branch correction using
the same attempt accounting and child verifier envelope.

**Files:**

- Create `pipelines/goal_plan_smoke/subgraphs/goal_lane.dot`.
- Create `pipelines/goal_plan_smoke/subgraphs/integration_correction.dot`.
- Modify `pipelines/goal_plan_smoke/python/goal_plan_runtime.py` only for the
  deterministic child commands these graphs require.

**Steps:**

1. Copy the proven task-runner convergence shape: orient, reserve, attempt,
   deterministic verify, classify, curate feedback, diagnose repeated failure,
   and terminate honestly on pass, blocker, or exhaustion.
2. Require `ReserveGlobalAttempt` immediately before each adaptive node and
   exact-once consumption only after complete envelope classification.
3. Replace stale feedback rather than accumulating an unbounded transcript.
4. Make repeated identical failure signatures route to diagnosis rather than a
   blind retry.
5. Let lane success produce only a candidate commit and evidence; reserve final
   pass classification for the parent.
6. Make integration correction operate only on the current integration branch,
   the responsible ownership union, and declared integration seams.

**Dependencies:** Tasks 4 and 5.

**Verification:** Both child DOT files pass strict Attractor lint, and the lane test proves withheld feedback remains red while changed feedback changes the candidate hash and reaches a later verifier pass.

### Task 7: Author static parent waves and sequential integration

**Outcome:** The parent graph visibly launches and monitors the two Wave 1 lanes,
waits for authoritative terminal results, parent-verifies candidates, integrates
them sequentially with an aggregate check after each merge, and only then starts
Wave 2 lane `lane_c`.

**Files:**

- Create `pipelines/goal_plan_smoke/goal_plan_smoke.dot`.
- Create `pipelines/goal_plan_smoke/plan.json` with final hashes completed in
  Task 10.
- Modify `pipelines/goal_plan_smoke/python/goal_plan_runtime.py` for parent
  collection, ownership, integration, rollback, and journaling commands.

**Steps:**

1. Encode each lane launch and monitor branch explicitly in DOT; do not dispatch
   by iterating `plan.json`.
2. Use component fan-out and triple-octagon fan-in only for the two independent
   Wave 1 lanes.
3. Classify missing or invalid supervisor result as infrastructure failure and a
   missing child result as crashed, never as an empty success.
4. Parent-verify each candidate in a newly registered detached worktree at its
   exact commit, then remove and reconcile that worktree after evidence is
   durable.
5. Enforce lane ownership and exclude the compiled pipeline directory from every
   mutable path contract.
6. Integrate in stable plan order and run the aggregate envelope immediately
   after every merge; on product failure restore the recorded pre-merge HEAD.
7. Gate `lane_c` on both dependencies being parent-pass, integrated, and followed
   by green aggregate evidence.

**Dependencies:** Tasks 3 through 6.

**Verification:** A static topology test and live fixture assert that `lane_a` and `lane_b` overlap in wall time, `lane_c` starts later, and the integration journal contains one green aggregate record after each accepted merge.

### Task 8: Add coherence, final sweep, recovery, and terminal machinery

**Outcome:** Late cross-lane findings converge through bounded integration
correction, final proof binds one exact HEAD, recovery reconciles durable state
with reality, and cleanup selects one honest terminal before publication.

**Files:**

- Modify `pipelines/goal_plan_smoke/goal_plan_smoke.dot`.
- Modify `pipelines/goal_plan_smoke/plan.json`.
- Modify `pipelines/goal_plan_smoke/python/goal_plan_runtime.py`.

**Steps:**

1. Run pre-coherence aggregate verification before every fresh coherence review.
2. Expand each allowed correction ordinal statically in DOT and atomically
   reserve one correction round plus one process launch before supervisor start.
3. Compute the responsible set and transitive affected closure, invalidate stale
   evidence, and rerun closure lane checks, closure aggregate, pre-coherence
   aggregate, and fresh coherence at one current HEAD.
4. Freeze the final HEAD only after coherence passes; rerun every lane verifier
   there and run `final-aggregate-after-sweep` at that same SHA.
5. Reconcile budgets, supervisors, worktrees, candidates, integration journal,
   correction journal, and proof records before resuming any action.
6. Implement fresh cleanup-authority derivation, status-specific
   `PreTerminalCleanup`, immutable finalization, four carriers, canonical token
   conditions, and separate command-failure routes.
7. Preserve `RESIDUALS_READY`, `INFRA_FAILURE`, and `ABORTED` as explicit
   non-success outcomes; only `COMPLETE` is workflow success.

**Dependencies:** Task 7.

**Verification:** A terminal-contract test proves all four statuses are reachable, all eight token edges require exact last-line token plus successful tool outcome, and every tool command has a separate infrastructure failure route.

### Task 9: Add external-state pull-request delivery and exact-head proof

**Outcome:** Delivery runs as a supervised child from a clean disposable
final-HEAD worktree, writes generated state only outside Git, uses one immutable
no-force branch contract, and is accepted only after independent remote exact-head
verification.

**Files:**

- Create `pipelines/goal_plan_smoke/subgraphs/deliver_pr.dot`.
- Modify `pipelines/goal_plan_smoke/goal_plan_smoke.dot`.
- Modify `pipelines/goal_plan_smoke/plan.json`.
- Modify `pipelines/goal_plan_smoke/python/goal_plan_runtime.py`.

**Steps:**

1. Adapt the proven delivery topology while moving logs, events, checkpoints,
   ledgers, and results beneath `delivery_state_root`.
2. Compile one canonical delivery branch, full ref, remote, exact no-force
   refspec, collision policy, and final-HEAD source.
3. Reject stale, unexplained, differently owned, wrong-remote, or wrong-head
   local and remote branch collisions before network mutation.
4. Register a clean delivery worktree at the frozen final HEAD and prove pre/post
   HEAD, status, filesystem, and compiled-source equality.
5. Supervise the delivery child through the same reaper and process-launch
   accounting; allow at most two crash-recoverable delivery attempts.
6. Independently query the remote full ref and pull request, requiring both heads
   to equal the frozen final HEAD.
7. Route unverifiable delivery to infrastructure failure and never create a
   third attempt or claim complete.

**Dependencies:** Task 8.

**Verification:** In a temporary remote, `test "$(gh pr view "$PR_URL" --json headRefOid --jq .headRefOid)" = "$FINAL_HEAD"` exits 0, and the recorded push command contains no force option.

### Task 10: Finalize the immutable compiled family and documentation

**Outcome:** The complete static family is content-bound, graph and plan agree,
all source hashes are final, the containing execution-source commit is recorded
without self-reference, and users can discover the pipeline from the README.

**Files:**

- Finalize all six files directly under `pipelines/goal_plan_smoke/` and its
  `subgraphs/` directory.
- Finalize all three Python implementation files.
- Modify `README.md` with one concise pipeline entry.

**Steps:**

1. Canonicalize `plan.json` with approved lanes, waves, integration order,
   ownership, verifiers, budgets, runner and trust bindings, delivery contract,
   terminal contract, and exact definition hashes.
2. Embed the plan hash and static correspondence values in the parent DOT.
3. Prove every lane, dependency, wave, correction ordinal, integration step,
   budget, verifier, child hash, delivery route, and terminal route agrees between
   plan and graph.
4. Create the compiled-program commit containing the complete pipeline directory
   and README entry, preserving the earlier anchor commit.
5. Treat the compiled-program commit as `execution_source_sha` and prove it
   descends from the product baseline through the plan anchor.
6. Ensure runtime never mutates any checked-in pipeline byte.

**Dependencies:** Tasks 1 through 9.

**Verification:** `git diff-tree --no-commit-id --name-only -r "$EXECUTION_SOURCE_SHA" | sort` equals the approved footprint for the compiled commit, and graph-plan correspondence validation exits 0.

### Task 11: Add tests, fault matrix, lint, render, and documentation checks

**Outcome:** The implementation has focused unit coverage, integration and
recovery coverage, a named complete fault matrix, strict DOT lint, Graphviz
render evidence, clean Python checks, and documentation that matches the graph.

**Files:**

- Create `pipelines/goal_plan_smoke/python/tests/test_goal_plan_bootstrap.py`.
- Create `pipelines/goal_plan_smoke/python/tests/test_goal_plan_runtime.py`.
- Create `pipelines/goal_plan_smoke/python/tests/test_goal_plan_supervisor.py`.
- Create `pipelines/goal_plan_smoke/python/tests/test_goal_plan_trusted_runtime.py`.
- Modify `README.md` and `goal_plan_smoke.md` only if verification finds a real
  mismatch with the implemented contract.

**Steps:**

1. Cover bootstrap trust order, strict paths and schemas, exact Git blobs,
   materialization, rehydration, parent CWD, argv, environment, and blocked exit
   78 behavior.
2. Cover root disjointness, source immutability, worktree lifecycle, ownership,
   separate concurrent budgets, deadline closure, both verifier envelopes,
   integration rollback, coherence correction, final sweep, cleanup authority,
   carriers, and delivery collision policy.
3. Cover supervisor exit 0, nonzero, signal, timeout, cancellation, parent crash,
   supervisor crash, pre-ledger discovery, stale PID identity, atomic result, and
   no-zombie or orphan-group postconditions.
4. Run the complete fault matrix from the approved design, preserving each exact
   command, exit status, evidence path, and resulting disposition.
5. Strict-lint the parent and all three subgraphs with the immutable runner
   prefix.
6. Render all four DOT files to non-empty PNG evidence with Graphviz and record
   source and output hashes outside the repository.
7. Run Python quality checks and the full system-Python test suite without
   touching managed caches.
8. Audit every DOT against `docs/RUBRIC.md` and confirm the guides describe actual
   topology and terminal behavior.

**Dependencies:** Task 10.

**Verification:** The combined quality command runs Python checks, `python3 -m pytest pipelines/goal_plan_smoke/python/tests -q`, strict lint for all four DOT files, four non-empty Graphviz renders, footprint validation, and `git diff --check`; every component must exit 0.

### Task 12: Run the real end-to-end smoke

**Outcome:** A real temporary GitHub-backed repository demonstrates the complete
trusted bootstrap, concurrent isolated lanes, authoritative wait status,
feedback-dependent correction, parent re-verification, sequential integration,
aggregate-after-each-merge, bounded coherence correction, one-HEAD final proof,
cleanup, terminal publication, and exact-head pull-request delivery.

**Files:**

- Change no checked-in file.
- Write all smoke evidence beneath external launch, state, worktree, delivery,
  and test-evidence roots.

**Steps:**

1. Create the temporary remote repository, compile-bound delivery branch, external
   roots, descriptor, staged bootstrap, provider credentials, and immutable
   runner prefixes.
2. Launch the parent only through bootstrap `self-check`, runtime materialization,
   and `launch-parent`; prove canonical parent CWD and source binding before
   mutation.
3. Observe `lane_a` and `lane_b` concurrently in distinct worktrees and child
   processes; prove all writes remain in the assigned worktree.
4. Prove supervisor `waitpid` records, not artifacts, determine child success or
   failure.
5. Force `lane_b`'s first verifier failure, retain its evidence, show the unchanged
   feedback control stays red, then show changed curated feedback produces a
   different candidate and later pass.
6. Observe clean parent candidate re-verification, ownership checks, stable
   sequential merges, and green aggregate evidence after every merge before
   `lane_c` starts.
7. Force one coherence iteration, run the supervised integration correction,
   affected-closure proof, fresh coherence, full final sweep, and
   `final-aggregate-after-sweep` at one frozen HEAD.
8. Deliver through the clean external-state worktree and independently prove the
   remote ref and pull request both point to the frozen HEAD.
9. Observe `PreTerminalCleanup` remove all run-owned worktrees and process groups,
   then verify immutable finalizer and `CompleteCarrier` evidence.
10. Run selected live fault injections for nonzero artifact-producing child,
    missing supervisor result, verifier mutation, source drift, deadline closure,
    restart reconciliation, delivery collision, and restricted cleanup.

**Dependencies:** Task 11 and all mandatory external prerequisites.

**Verification:** The smoke harness exits 0 only when `result.json` reports `COMPLETE`, the carrier emits `GOAL_PLAN:COMPLETE`, every lane and aggregate proof binds one accepted Git history, cleanup reports no live process or run-owned worktree, and the independently queried pull-request head equals the recorded final HEAD.

## Acceptance Checklist

- [ ] The source footprint is exactly the 13 pipeline files plus one `README.md`
  entry listed above.
- [ ] The parent DOT shows the approved lanes, dependency waves, correction
  ordinals, integration order, delivery route, and terminal routes directly.
- [ ] `lane_a` and `lane_b` run concurrently in distinct worktrees and distinct
  headless child Attractor processes.
- [ ] Each child and its box sessions resolve relative CWD to its assigned
  worktree, with no cross-lane writes.
- [ ] No tmux process, session, pane, or status probe participates in execution.
- [ ] Every child has one accountable reaper, and authoritative raw wait status
  determines exit, signal, timeout, and cancellation truth.
- [ ] An artifact-producing nonzero child remains non-pass.
- [ ] The seeded verifier failure cannot pass with withheld or unchanged feedback;
  changed feedback produces a different candidate state and later green proof.
- [ ] Dirty child verification preserves exact pre/post HEAD, index, staged,
  tracked, untracked, ignored, and compiled-source state.
- [ ] Parent candidate verification runs against the exact durable commit in a
  clean detached worktree, not the lane's dirty worktree or prose report.
- [ ] Ownership passes before integration and rejects any compiled-pipeline write.
- [ ] Passing commits integrate sequentially in stable order.
- [ ] The aggregate verifier runs through the parent envelope after every merge.
- [ ] A failed post-merge aggregate restores the recorded pre-merge HEAD and
  returns evidence to the responsible lane.
- [ ] A dependency lane starts only after every dependency is parent-pass,
  integrated, and followed by a green aggregate.
- [ ] Coherence correction uses the current integration branch, one supervised
  correction child, one correction-round reservation, and the affected closure.
- [ ] Fresh coherence, every final lane verifier, and
  `final-aggregate-after-sweep` all bind the same frozen final HEAD.
- [ ] Run-wide attempts, process launches, correction rounds, and deadline remain
  separate, flocked, bounded, and recovery-safe.
- [ ] All generated state is external; checked-in pipeline source remains
  byte-immutable and no verified worktree gains `.resolve` state.
- [ ] Recovery validates descriptor and external runtime identity before
  reconciling budgets, processes, worktrees, Git history, or delivery.
- [ ] `PreTerminalCleanup` stops only identity-valid process groups, mutates Git
  only under current `FULL` authority, and records skipped or unresolved actions.
- [ ] Successful cleanup leaves no live lane, correction, or delivery process and
  no non-preserved run-owned worktree or Git worktree registration.
- [ ] The four graph terminals remain distinct, and only `COMPLETE` is success.
- [ ] Harness-only blocked outcomes use their external records, exact token, and
  exit 78 without fabricating a graph terminal.
- [ ] Delivery uses the compile-bound branch and exact no-force refspec from the
  frozen final HEAD.
- [ ] The parent independently confirms the remote ref and pull request head both
  equal the exact final integrated HEAD.
- [ ] Strict lint, Graphviz render, Python checks, full tests, fault matrix, clean
  footprint, and `git diff --check` all pass with preserved evidence.

## Honest Blockers

Graphviz is mandatory. If `dot` is unavailable, any DOT fails to render, a PNG is
empty, or render evidence cannot be recorded, Task 11 and final acceptance are
blocked. Static reading or strict lint does not waive the render requirement.

A delivery-enabled real smoke requires a temporary remote plus credentials and
permissions that can create a branch and pull request and can query their exact
heads. If those credentials or permissions are unavailable, non-delivery tests
may still run, but Task 12 and full acceptance remain blocked. The report must
name the missing credential or permission class without printing secret values.

Provider credentials, a source-backed Attractor runner with the required flags,
Linux procfs, Git worktree support, or the ability to create pairwise-disjoint
external roots can likewise block the live smoke. Such a gap is infrastructure
evidence, not a passing substitute.

## Explicit Execution Order

Execute Tasks 1 through 12 in order.

Tasks 2 through 5 may be developed in short internal increments, but Task 6 must
not begin until bootstrap, supervisor, runtime safety, budgets, worktrees, and
both verifier envelopes have stable interfaces. Task 7 consumes those interfaces.
Tasks 8 and 9 extend the parent only after base waves and sequential integration
are proven. Task 10 freezes hashes and commit identities only after source and
DOT content are final. Task 11 runs the complete static and fault suite against
that compiled program. Task 12 is the final live proof and changes no checked-in
file.

## Stop Condition

Stop successfully only when all twelve task outcomes are complete, every item in
the acceptance checklist has real evidence, the checked-in footprint is exact,
all verification gates pass, cleanup leaves the required terminal state, and the
real delivery smoke independently proves the pull request points to the exact
final integrated HEAD.

Stop blocked rather than claiming success when a mandatory prerequisite or gate
cannot be satisfied. Name the missing capability and the exact evidence that
would clear it. Stop as failed when trustworthy evidence shows a contract
violation. Do not convert blocked, residual, infrastructure, or aborted outcomes
into completion.