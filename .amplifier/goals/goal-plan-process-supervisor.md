# Goal: prove accountable child-process supervision

Produce a committed, tested Wave-1 supervisor that captures authoritative child-process truth and cleans process groups, or terminate with a named blocker for each item that cannot be completed.

## Lane contract

- Work only in `/home/ken/workspace/attractor-pipelines/worktrees/goal-plan-impl-supervisor`.
- Branch: `goal-plan-impl/supervisor`.
- Base SHA: `BASE_SHA_AFTER_BOOTSTRAP_MERGE` — the orchestrator must replace and commit this value before launch.
- Read repository doctrine and the final design before editing.
- Own only:
  - `pipelines/goal_plan_smoke/python/goal_plan_supervisor.py`
  - `pipelines/goal_plan_smoke/python/tests/test_goal_plan_supervisor.py`
- Treat Wave-0 schemas as fixed inputs. Do not edit bootstrap, runtime, DOT, plan, or docs.
- Cross-boundary changes are `BLOCKED-ownership` residuals.
- Never merge. Commit early; push branch when available.
- Wall-clock bound: 60 minutes. Reaching it is terminal `BLOCKED-budget`, not permission to skip proof.

## Closed items

Each item ends `PASS`, `FAIL-<reason>`, `BLOCKED-<reason>`, or `PENDING-HUMAN`:

1. **Accountable reaper** — launch the Attractor child as a direct child, remain alive, and capture raw wait status plus normalized exit/signal.
2. **Durable protocol** — atomically write and validate intent, ledger, acknowledgement, polling, termination, reconciliation, and final result records.
3. **Identity safety** — validate Linux boot ID, PID start ticks, PGID, executable/cmdline/CWD identity before observation or signalling.
4. **Termination** — enforce wall timeout and TERM→grace→KILL for the complete child process group without signalling an unverified PID.
5. **Failure truth** — artifact plus nonzero exit remains non-pass; missing result, signal, timeout, cancellation, and supervisor disappearance remain distinguishable.
6. **Recovery** — bounded pre-ledger discovery/adoption and orphan-child termination behave deterministically.
7. **Fault proof** — focused tests cover exit 0, nonzero, signal, timeout, cancellation, parent crash, supervisor crash, stale PID, atomic result, and no zombie/orphan.

Complete when all seven are terminal, or every unresolved item has a conclusive named blocker and evidence.

## Scope-outs

- No runtime substrate, worktree manager, verifier envelope, DOT, Graphviz, DTU, Resolve, or delivery implementation.
- No changes to Wave-0 files or managed cache.

## Final act

After commits, write ignored root `DONE.json` with lane `process-supervisor`, this session ID, verdict `COMPLETE|BLOCKED|PARTIAL`, real branch/head/push state, item results, residuals, pending-human items, and exact suite commands. Do not commit it.
