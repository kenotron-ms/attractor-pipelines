# Goal: materialize and prove the static goal-plan graph family

Produce the committed Wave-3 parent and child DOT family plus audited plan metadata and documentation, with local proof of the graph basin, or terminate with named blockers.

## Lane contract

- Work only in `/home/ken/workspace/attractor-pipelines/worktrees/goal-plan-impl-graphs`.
- Branch: `goal-plan-impl/graphs`.
- Base SHA: `BASE_SHA_AFTER_RUNTIME_MERGE` — replace and commit before launch.
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
- Wall-clock bound: 120 minutes. Reaching it is terminal `BLOCKED-budget`, not permission to skip proof.

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
- Graphviz is currently missing and must be installed by the orchestrator; until then render is a named blocker.

## Final act

After commits, write ignored root `DONE.json` with lane `static-graph-family`, this session ID, verdict `COMPLETE|BLOCKED|PARTIAL`, real branch/head/push state, per-wave terminal results, residuals, pending-human items, and exact lint/render/live commands. Do not commit it.
