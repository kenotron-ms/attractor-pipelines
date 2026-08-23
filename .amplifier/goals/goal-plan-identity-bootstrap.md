# Goal: prove the goal-plan history anchor and trusted bootstrap

Produce a committed, tested Wave-0 implementation whose history anchor and bootstrap trust boundary satisfy the final goal-plan design, or terminate with a named blocker for each item that cannot be completed.

## Lane contract

- Work only in `/home/ken/workspace/attractor-pipelines/worktrees/goal-plan-impl-bootstrap`.
- Branch: `goal-plan-impl/bootstrap`.
- Product base SHA: `b366fa18f79117dee3ec4ed03381299a96784fa2`; launch base is the goal-contract commit recorded by the orchestrator manifest.
- Read `AGENTS.md`, `docs/primer.md`, `docs/RUBRIC.md`, and `docs/plans/2026-08-22-goal-plan-attractor-design.md` before editing.
- Own only:
  - `pipelines/goal_plan_smoke/goal_plan_smoke.md`
  - `pipelines/goal_plan_smoke/python/goal_plan_bootstrap.py`
  - `pipelines/goal_plan_smoke/python/tests/test_goal_plan_bootstrap.py`
- Any needed edit outside these paths is `BLOCKED-ownership`; record it as a residual and do not make it.
- Never merge to `main` or another branch. Commit early and push `goal-plan-impl/bootstrap` when remote access works.
- Wall-clock bound: 45 minutes. Reaching it is terminal `BLOCKED-budget`, not permission to skip proof.

## Closed items

Each item must end as `PASS`, `FAIL-<named-reason>`, `BLOCKED-<named-reason>`, or `PENDING-HUMAN`:

1. **History anchor** — first lane commit changes only `goal_plan_smoke.md`; record product base SHA, anchor SHA, and blob hash.
2. **Descriptor-first trust** — authenticate the harness-owned launch descriptor and committed plan bytes before reading plan-controlled trust fields.
3. **Exact materialization** — extract runtime/supervisor bytes from exact Git blobs, install them under an external state root atomically, seal and re-hash them.
4. **Recovery and handoff** — implement rehydration and exact parent `chdir`/`execve` handoff without importing mutable target-repository runtime code.
5. **Negative controls** — tests reject wrong descriptor, plan blob, launcher, Git/interpreter identity, target working-copy tampering, and external bootstrap tampering.
6. **Quality evidence** — run focused pytest plus Python static checks available on the host; quote exact commands, exit status, and counts in the final report.

Complete when either all six items are terminal and passing where achievable, or every non-passing item has a conclusive named blocker with evidence. A blocker becomes a residual; it does not authorize fabricated success.

## Scope-outs

- No supervisor, runtime substrate, DOT graphs, plan.json, README, Graphviz, DTU, Resolve, or PR delivery work.
- No managed-cache edits.
- No generic compiler or scheduler.

## Known

- Source worktree base is clean at the pinned SHA.
- The source-backed Attractor runner and provider credentials are available; Graphviz is not required for this lane.

## Final act

After committing all real work, write ignored worktree-root `DONE.json` as the final act with:

```json
{"lane":"identity-bootstrap","session_id":"<this session>","verdict":"COMPLETE|BLOCKED|PARTIAL","branch":"goal-plan-impl/bootstrap","head":"<actual HEAD>","pushed":"<actual true|false>","items":[],"residuals":[],"pending_human":[],"suite":[]}
```

The `head` and `session_id` must be real. Do not commit `DONE.json`.
