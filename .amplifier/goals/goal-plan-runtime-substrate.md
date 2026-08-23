# Goal: prove the deterministic goal-plan runtime substrate

Produce a committed, tested Wave-2 runtime that safely manages external state, worktrees, budgets, verifier envelopes, integration, and terminal evidence, or terminate with named blockers.

## Lane contract

- Work only in `/home/ken/workspace/attractor-pipelines/worktrees/goal-plan-impl-runtime`.
- Branch: `goal-plan-impl/runtime`.
- Base SHA: `BASE_SHA_AFTER_SUPERVISOR_MERGE` — replace and commit before launch.
- Read repository doctrine and final design.
- Own only:
  - `pipelines/goal_plan_smoke/python/goal_plan_runtime.py`
  - `pipelines/goal_plan_smoke/python/tests/test_goal_plan_runtime.py`
  - `pipelines/goal_plan_smoke/python/tests/test_goal_plan_trusted_runtime.py`
- Bootstrap and supervisor contracts are fixed dependencies. Do not edit them or any DOT/plan/docs file.
- Cross-boundary changes become `BLOCKED-ownership` residuals.
- Never merge. Commit early; push when available.
- Wall-clock bound: 90 minutes. Reaching it is terminal `BLOCKED-budget`, not permission to skip proof.

## Closed items

Each item ends `PASS`, `FAIL-<reason>`, `BLOCKED-<reason>`, or `PENDING-HUMAN`:

1. **Admission and roots** — canonical identity, external non-overlapping state/worktree roots, compiled-source manifest/gate, and parent/source binding.
2. **Worktree lifecycle** — exact run-owned registry for lane, integration, candidate, and delivery worktrees; phase-safe recovery and cleanup.
3. **Budgets** — flocked, atomic, idempotent attempt/process/correction/deadline reservations with closed exhaustion tokens.
4. **Child verifier envelope** — preserve legitimate dirty candidate state while proving the verifier caused no tracked, untracked, ignored, staged, HEAD, index, or source mutation.
5. **Parent verifier envelope** — clean exact-SHA detached verification, external output containment, immutable pre/post HEAD/filesystem/source proof.
6. **Candidate and ownership** — resolve candidate from Git, enforce owned paths, record durable evidence and schema/hash bindings.
7. **Integration** — stable sequential journal, aggregate-after-merge hooks, rollback to exact pre-merge head, affected-closure invalidation.
8. **Terminal safety** — cleanup authority, preterminal cleanup, immutable results, carrier evidence, and honest residual/infra/aborted outcomes.
9. **Fault proof** — focused tests exercise root overlap, budget races, stale state, verifier mutations, aggregate rollback, recovery boundaries, and cleanup authority.

Complete when all nine are terminal or all unresolved items have conclusive named blockers.

## Scope-outs

- No DOT graphs, plan.json, README, Graphviz, local live Attractor run, DTU, Resolve, or delivery side effect.
- No bootstrap/supervisor edits or managed-cache changes.

## Final act

After commits, write ignored root `DONE.json` with lane `runtime-substrate`, this session ID, verdict `COMPLETE|BLOCKED|PARTIAL`, real branch/head/push state, nine item results, residuals, pending-human items, and exact suite evidence. Do not commit it.
