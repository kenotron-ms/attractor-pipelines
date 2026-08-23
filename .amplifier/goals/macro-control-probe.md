Produce a runnable Attractor CLI macro-control probe that conclusively demonstrates whether a fixed graph can execute two independent first-wave goals followed by one dependent goal, with deterministic parent evidence and a terminal verdict.

Complete when either the probe reaches PASS with machine evidence for every item below, or each remaining item has a named FAIL or BLOCKED reason that conclusively identifies why it cannot be demonstrated in this environment. Items ending FAIL or BLOCKED are residuals, not failures of this goal.

ITEMS
1. PROBE_GRAPH: PASS when all committed probe implementation files are contained under `pipelines/goal_plan_macro_probe/**`, the DOT parses with zero ERROR diagnostics, and Attractor lint exits 0; otherwise FAIL-named or BLOCKED-named.
2. WAVE_EXECUTION: PASS when a fresh Attractor CLI run shows two first-wave branches both reach terminal result artifacts and the dependent goal begins only after both first-wave results exist; otherwise FAIL-named or BLOCKED-named.
3. PARENT_EVIDENCE: PASS when an independent deterministic verifier reruns after the graph and records the exact command, exit code, observed artifact paths, ordering facts, and final token in `pipelines/goal_plan_macro_probe/evidence.json`; otherwise FAIL-named or BLOCKED-named.
4. DURABILITY: PASS when all probe files and evidence are committed on branch `goal-plan-attractor-smoke/macro`, the worktree is clean, and the commit SHA is recorded in DONE.json; otherwise FAIL-named or BLOCKED-named.

WORKSPACE AND OWNERSHIP
- Work only in `/home/ken/workspace/attractor-pipelines/worktrees/goal-plan-attractor-smoke-macro` on branch `goal-plan-attractor-smoke/macro`, based on `1de2ee50df012ff6c1fbc80c644658de306a0f5d`.
- Own only `pipelines/goal_plan_macro_probe/**` plus the worktree-root ignored `DONE.json` signal.
- Do not modify the main checkout, sibling worktrees, README.md, docs, other pipeline folders, `.gitignore`, or `.amplifier/goals/**`.
- Crossing an ownership boundary is a defect: record the needed edit as a residual and stop that item.

EXECUTION CONTRACT
- Use the source-backed Attractor CLI invocation from KNOWN; do not install or copy tools into the repository.
- Use bounded, non-interactive commands. Do not wait for human input.
- Record future evidence inline in the lane transcript as commands run and also in the committed evidence artifact.
- Commit early and push the branch if the configured remote accepts it. Never merge to main.
- If the 30-minute wall or 20-turn bound is reached, record BUDGET as a named residual and commit all real work.
- Write worktree-root DONE.json as the final act with fields `lane`, `session_id`, `verdict`, `branch`, `head`, `pushed`, `items`, `residuals`, `pending_human`, and `suite`. `verdict` is exactly COMPLETE, BLOCKED, or PARTIAL.

SCOPE-OUTS
- No production `goal_plan` implementation is required.
- No strict per-lane LLM worktree isolation claim is required in this lane.
- No Graphviz rendering is required.
- No PR creation or delivery verification is required.
- No changes outside the owned probe directory are required.

KNOWN — speed aid only; these facts do not replace completion criteria
- The repository baseline is clean at base SHA `1de2ee50df012ff6c1fbc80c644658de306a0f5d`.
- Source-backed CLI prefix:
  `BASE=/home/ken/.amplifier/cache/amplifier-bundle-attractor-10534381a6383d20/modules; PYTHONPATH="$BASE/pipeline-runner:$BASE/loop-pipeline:$BASE/unified-llm-client:$BASE/remote-source" /home/ken/.local/share/uv/tools/amplifier/bin/python -m amplifier_module_pipeline_runner.cli`
- Doctor and parser baselines exit 0; Graphviz `dot` is absent.
- The approved design is `docs/plans/2026-08-22-goal-plan-attractor-design.md`.
