Produce a runnable Attractor CLI isolation probe that conclusively establishes whether concurrent folder-lane box sessions honor distinct lane-specific worktree working directories.

Complete when either strict lane CWD isolation is demonstrated with machine evidence, or the current engine limitation is conclusively demonstrated with observed session paths and a named blocker. Either result is a valid terminal outcome; no optimistic inference is allowed.

ITEMS
1. PROBE_GRAPH: PASS when all committed probe implementation files are contained under `pipelines/goal_plan_cwd_probe/**`, the DOT parses with zero ERROR diagnostics, and Attractor lint exits 0; otherwise FAIL-named or BLOCKED-named.
2. DISTINCT_TARGETS: PASS when the probe deterministically creates two distinct temporary lane worktrees/directories and records their canonical realpaths before spawning concurrent folder branches; otherwise FAIL-named or BLOCKED-named.
3. BOX_SESSION_CWD: PASS only if each box session independently records `pwd` and writes its sentinel inside its assigned target directory, with no sentinel or mutation in the root or sibling target. If both sessions remain rooted at the CLI root or otherwise violate assignment, record `BLOCKED-engine-session-cwd` with the observed paths; otherwise FAIL-named.
4. PARENT_EVIDENCE: PASS when an independent deterministic verifier records the exact run command, exit code, expected and observed paths, sentinel locations, mutation scan, and verdict in `pipelines/goal_plan_cwd_probe/evidence.json`; otherwise FAIL-named or BLOCKED-named.
5. DURABILITY: PASS when all probe files and evidence are committed on branch `goal-plan-attractor-smoke/cwd`, the worktree is clean, and the commit SHA is recorded in DONE.json; otherwise FAIL-named or BLOCKED-named.

WORKSPACE AND OWNERSHIP
- Work only in `/home/ken/workspace/attractor-pipelines/worktrees/goal-plan-attractor-smoke-cwd` on branch `goal-plan-attractor-smoke/cwd`, based on `1de2ee50df012ff6c1fbc80c644658de306a0f5d`.
- Own only `pipelines/goal_plan_cwd_probe/**` plus the worktree-root ignored `DONE.json` signal.
- Do not modify the main checkout, sibling worktrees, README.md, docs, other pipeline folders, `.gitignore`, or `.amplifier/goals/**`.
- Crossing an ownership boundary is a defect: record the needed edit as a residual and stop that item.

EXECUTION CONTRACT
- Use real box nodes and the source-backed Attractor CLI; do not replace the box sessions with deterministic fixture workers.
- Use provider credentials already present. Do not wait for human input.
- Record future evidence inline in the transcript and in the committed evidence artifact.
- Commit early and push the branch if the configured remote accepts it. Never merge to main.
- If the 20-minute wall or 15-turn bound is reached, record BUDGET as a named residual and commit all real work.
- Write worktree-root DONE.json as the final act with fields `lane`, `session_id`, `verdict`, `branch`, `head`, `pushed`, `items`, `residuals`, `pending_human`, and `suite`. `verdict` is exactly COMPLETE, BLOCKED, or PARTIAL.

SCOPE-OUTS
- No engine fix is required.
- No production `goal_plan` implementation is required.
- No Graphviz rendering is required.
- No PR creation or delivery verification is required.
- A conclusively demonstrated CWD limitation is a valid outcome and must not be disguised as success.

KNOWN — speed aid only; these facts do not replace completion criteria
- Current reconnaissance indicates box sessions receive one runner-global session CWD while tool nodes can honor `context.target_dir`; this lane must prove or refute that with a fresh run.
- Source-backed CLI prefix:
  `BASE=/home/ken/.amplifier/cache/amplifier-bundle-attractor-10534381a6383d20/modules; PYTHONPATH="$BASE/pipeline-runner:$BASE/loop-pipeline:$BASE/unified-llm-client:$BASE/remote-source" /home/ken/.local/share/uv/tools/amplifier/bin/python -m amplifier_module_pipeline_runner.cli`
- Base SHA is `1de2ee50df012ff6c1fbc80c644658de306a0f5`.
- The approved design is `docs/plans/2026-08-22-goal-plan-attractor-design.md`.

RESUME 1 — prior bounded run checkpoint
- Prior lane session: `3357d673-8494-440e-bd99-e612e982f1c8`.
- Treat commits `449068135103438e80fd687cfe5a3acbffcc57ab` and `0854feda39a9aefdcd8ea2f9967f576632200f1b` as your own completed prior work. Do not redo the probe.
- Existing `pipelines/goal_plan_cwd_probe/evidence.json` was independently parsed and hash-checked by the orchestrator. It records PROBE_GRAPH PASS, DISTINCT_TARGETS PASS, PARENT_EVIDENCE PASS, and BOX_SESSION_CWD BLOCKED-engine-session-cwd.
- Remaining work: inspect the existing evidence and git state, preserve the named blocker, push the committed branch if possible, then write a matching-session DONE.json as the final act. Do not rerun the expensive Attractor probe unless the existing evidence is missing or no longer verifies.
