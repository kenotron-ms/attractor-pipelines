# Goal: materialize and prove the static goal-plan graph family

Produce the committed Wave-3 parent and child DOT family plus audited plan metadata and documentation, with local proof of the graph basin, or terminate with named blockers.

## Lane contract

- Work only in `/home/ken/workspace/attractor-pipelines/worktrees/goal-plan-impl-graphs`.
- Branch: `goal-plan-impl/graphs`.
- Base SHA: `888c6a6` (merge commit landing this lane's own prior RESUME-0 work — the full static DOT family — onto `goal-batch`; independently re-verified: `attractor lint --strict` on `goal_lane.dot` is clean, plain lint on the other three graphs shows only the pre-existing single `acyclic_graph` warning class, 104/104 Python tests still pass — the orchestrator will use the full 40-hex SHA when cutting the worktree).
- Read `AGENTS.md`, primer, RUBRIC, final design, and existing proven graph precedents.
- Own only:
  - `pipelines/goal_plan_smoke/goal_plan_smoke.dot`
  - `pipelines/goal_plan_smoke/plan.json`
  - `pipelines/goal_plan_smoke/subgraphs/goal_lane.dot`
  - `pipelines/goal_plan_smoke/subgraphs/integration_correction.dot`
  - `pipelines/goal_plan_smoke/subgraphs/deliver_pr.dot`
  - `README.md`
- Consume Python command contracts unchanged. Any required Python edit is `BLOCKED-ownership`.
- Never merge. Commit early; push when available.
- Wall-clock bound: 150 minutes. Reaching it is terminal `BLOCKED-budget`, not permission to skip proof.

## Closed proof waves

Each wave ends `PASS`, `FAIL-<reason>`, `BLOCKED-<reason>`, or `PENDING-HUMAN`:

0. **Static structure** — parser, strict lint, canonical token conditions/failure routes, plan↔DOT correspondence, and Graphviz render when available.
1. **Worktree isolation** — child process started in a lane worktree with `--cwd .`; relative box/tool writes stay there and external logs stay outside.
2. **Exit truth** — expected artifact plus nonzero/signal/timeout remains non-candidate through supervisor evidence.
3. **Lane convergence** — first external verifier failure, one bounded feedback item, changed candidate, later pass; withheld-feedback control remains red.
4. **Parent verification** — dishonest/stale child PASS is rejected in a clean exact-candidate verification worktree.
5. **Parallel wave** — explicit A/B `component` fan-out and `tripleoctagon` fan-in; intervals overlap; missing/dead/nonzero results remain distinct.
6. **MVP** — stable A then B integration with aggregate verification after each merge; C starts only after A+B are green; final lane sweep and final aggregate bind one frozen HEAD.
7. **Late correction** — aggregate-red rollback, one bounded correction, affected-closure verification, fresh coherence and final aggregate.
8. **Delivery** — adapted external-state delivery in a clean final-HEAD worktree; parent independently verifies remote branch and PR head equal final HEAD. If remote side effects are unavailable, record `BLOCKED-delivery-environment` without weakening Waves 0–7.

Complete when all nine waves are terminal or all non-passing waves have conclusive named blockers with evidence.

## Scope-outs

- No Python edits, dynamic scheduler/compiler, Attractor/Resolve engine changes, tmux, literal `/goal`, production deploy, or PR merge.
- DTU and Resolve execution are orchestrator landing checks, not lane-owned work.

## Known

- Source-backed Attractor runner and Anthropic/OpenAI credentials are available.
- Graphviz remains unavailable. The orchestrator attempted installation before
  this launch: no root/sudo is available in this environment (privilege
  escalation is denied by the sandbox), and a non-root `apt-get download` +
  `dpkg -x` extraction of the `graphviz` .deb produced a `dot` "binary" that is
  actually a symlink to `../sbin/libgvc6-config-update` (a postinst trigger
  helper, not extracted, not a working renderer) — a known Debian packaging
  quirk that this extraction path cannot resolve without dpkg triggers/root.
  Do not re-attempt installation; record `Wave 0 (static structure)`'s render
  sub-step as `BLOCKED-graphviz-unavailable` with this evidence and proceed
  with parser/lint/correspondence proof, which do not require Graphviz.

## Final act

After commits, write ignored root `DONE.json` with lane `static-graph-family`, this session ID, verdict `COMPLETE|BLOCKED|PARTIAL`, real branch/head/push state, per-wave terminal results, residuals, pending-human items, and exact lint/render/live commands. Do not commit it.

## RESUME 1

- Prior session `7844184e-b55c-4cce-aa61-e47cb2f89347` reached its 120-minute
  wall bound with verdict `PARTIAL`, committed as `2d6f17b` (now merged to
  `goal-batch` at `888c6a6` — that IS your new base). Treat commit `2d6f17b`
  as this lane's own prior work; do not redo it.
- That session's own report that "no remote was configured/available to
  push" was **false** — the orchestrator pushed the same branch from the
  same worktree layout with no issue. Lane self-reports are hints, not
  evidence; verify your own git/push state directly rather than trusting a
  prior session's narration of it.
- Already closed and PASS, confirmed independently by the orchestrator —
  do not re-prove from scratch, just don't regress them:
  - **Wave 0 (static structure)**: parser/strict-lint/plan↔DOT-correspondence
    all PASS. Render remains `BLOCKED-graphviz-unavailable` (see Known
    section above) — do not re-attempt installing Graphviz.
  - **Wave 3 (lane convergence)**: two real bugs found via a live partial run
    and fixed (heredoc `$n` non-expansion in `ChildVerify`; `goal_gate=true`
    on a plain-text box node tripping the engine's fail-closed contract).
    The full closed loop (seeded-fail attempt → diagnose → retry with
    changed feedback → PASS → candidate commit) was authored and
    structurally verified but not witnessed to full completion — finish
    that one live run first as your fastest path to a fully-closed Wave 3,
    using the exact `live_test_command` your prior session recorded in its
    `DONE.json` (still readable via `git show 2d6f17b^{/DONE.json}` is not
    valid since it was gitignored — reconstruct the equivalent invocation
    of `subgraphs/goal_lane.dot` from the file itself and the design doc).
- Remaining, still open — this is the actual remaining scope of this lane:
  - **Wave 1 (worktree isolation)**, **Wave 2 (exit truth)**,
    **Wave 4 (parent verification)**, **Wave 5 (parallel wave)**,
    **Wave 6 (MVP)**, **Wave 7 (late correction)** — all require live,
    end-to-end exercise of `goal_plan_smoke.dot` itself (real supervisor
    child processes via `goal_plan_supervisor.py`, real registered
    worktrees via `goal_plan_runtime.py`, real parent verifier envelopes),
    not just the child subgraph in isolation. Budget your 150 minutes across
    these six; if you cannot finish all six, finish as many as you can
    end-to-end with real evidence and record named `BLOCKED-budget` for the
    rest — do not thin the proof to fit the clock.
  - **Wave 8 (delivery)** is explicitly **out of scope for this resume**.
    No PR-delivery credentials have been provisioned to this lane and none
    will be during this run. Record it as `PENDING-HUMAN` (not
    `BLOCKED-delivery-environment` — this is a real, not environmental,
    gap: a human must decide whether/how to provision temporary delivery
    credentials before Wave 8 can be proven). Do not attempt a workaround.
- This is RESUME 1 of max 2; original disjunctive-exit and wall-bound
  semantics are unchanged. If 150 minutes is not enough for the six
  remaining live waves, that is itself useful signal for the orchestrator's
  next resume decision — report it plainly rather than compressing scope
  silently.
