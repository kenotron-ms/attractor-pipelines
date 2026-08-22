Produce a runnable Attractor CLI convergence probe that demonstrates a candidate can fail an external deterministic verifier, receive bounded feedback, correct the artifact, and terminate only after independent parent re-verification.

Complete when either the full correction cycle reaches PASS with machine evidence for every item below, or each remaining item has a named FAIL or BLOCKED reason that conclusively identifies why it cannot be demonstrated in this environment. Items ending FAIL or BLOCKED are residuals, not failures of this goal.

ITEMS
1. PROBE_GRAPH: PASS when all committed probe implementation files are contained under `pipelines/goal_plan_convergence_probe/**`, the DOT parses with zero ERROR diagnostics, and Attractor lint exits 0; otherwise FAIL-named or BLOCKED-named.
2. INITIAL_FAILURE: PASS when a fresh Attractor CLI run records a first candidate verification failure produced by an external deterministic verifier rather than worker self-report; otherwise FAIL-named or BLOCKED-named.
3. FEEDBACK_AND_CORRECTION: PASS when the graph routes the verifier's observed failure into a bounded feedback edge, a subsequent adaptive attempt changes the candidate, and the verifier then passes; otherwise FAIL-named or BLOCKED-named.
4. PARENT_REVERIFY: PASS when a separate parent-side verifier runs after the corrective loop, binds evidence to the final artifact hash, and emits the sole success token; otherwise FAIL-named or BLOCKED-named.
5. DURABLE_EVIDENCE: PASS when `pipelines/goal_plan_convergence_probe/evidence.json` records commands, exit codes, attempt count, first failure, feedback, candidate hashes before and after correction, parent-verification result, and terminal token; otherwise FAIL-named or BLOCKED-named.
6. DURABILITY: PASS when all probe files and evidence are committed on branch `goal-plan-attractor-smoke/convergence`, the worktree is clean, and the commit SHA is recorded in DONE.json; otherwise FAIL-named or BLOCKED-named.

WORKSPACE AND OWNERSHIP
- Work only in `/home/ken/workspace/attractor-pipelines/worktrees/goal-plan-attractor-smoke-convergence` on branch `goal-plan-attractor-smoke/convergence`, based on `1de2ee50df012ff6c1fbc80c644658de306a0f5d`.
- Own only `pipelines/goal_plan_convergence_probe/**` plus the worktree-root ignored `DONE.json` signal.
- Do not modify the main checkout, sibling worktrees, README.md, docs, other pipeline folders, `.gitignore`, or `.amplifier/goals/**`.
- Crossing an ownership boundary is a defect: record the needed edit as a residual and stop that item.

EXECUTION CONTRACT
- Use a real adaptive box node and an external deterministic verifier. The worker may create candidates but may not certify them.
- Use the source-backed Attractor CLI and provider credentials already present. Do not wait for human input.
- Bound the corrective loop with a persistent attempt counter and a hard maximum of three candidate attempts.
- Record future evidence inline in the transcript and in the committed evidence artifact.
- Commit early and push the branch if the configured remote accepts it. Never merge to main.
- If the 30-minute wall or 20-turn bound is reached, record BUDGET as a named residual and commit all real work.
- Write worktree-root DONE.json as the final act with fields `lane`, `session_id`, `verdict`, `branch`, `head`, `pushed`, `items`, `residuals`, `pending_human`, and `suite`. `verdict` is exactly COMPLETE, BLOCKED, or PARTIAL.

SCOPE-OUTS
- No production `goal_plan` implementation is required.
- No strict per-lane LLM worktree isolation claim is required in this lane.
- No Graphviz rendering is required.
- No PR creation or delivery verification is required.
- No open-ended quality iteration is required.

KNOWN — speed aid only; these facts do not replace completion criteria
- Source-backed CLI prefix:
  `BASE=/home/ken/.amplifier/cache/amplifier-bundle-attractor-10534381a6383d20/modules; PYTHONPATH="$BASE/pipeline-runner:$BASE/loop-pipeline:$BASE/unified-llm-client:$BASE/remote-source" /home/ken/.local/share/uv/tools/amplifier/bin/python -m amplifier_module_pipeline_runner.cli`
- Doctor confirms Anthropic and OpenAI credentials are present.
- Base SHA is `1de2ee50df012ff6c1fbc80c644658de306a0f5`.
- The approved design is `docs/plans/2026-08-22-goal-plan-attractor-design.md`.
