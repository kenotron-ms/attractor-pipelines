# Lane goal: real-work-brick

/ goal

## Outcome (checkable end state)

A NEW reusable lane brick exists at
`pipelines/goal_plan_smoke/subgraphs/goal_lane_impl.dot` that:
(a) resolves a `$goal_condition_file` param and drives a real, iterative
`/goal`-style convergence loop against the CONTENTS of that referenced file —
i.e. it implements the referenced goal, instead of writing a fixed marker
string; (b) commits candidate work via a node that writes the SAME
`$lane_result_path` JSON contract the parent reads (`{"result": "candidate",
"candidate_sha": "<sha>"}`); and (c) parses/validates with ZERO ERROR-severity
diagnostics. The existing `subgraphs/goal_lane.dot` is left BYTE-FOR-BYTE
unchanged.

## Disjunctive exit (the load-bearing sentence)

Complete when **either** every item below reaches a terminal state, **or** it is
conclusively demonstrated the remainder cannot, naming the blocker for each.
Items ending FAIL or BLOCKED are residuals, not failures of the goal.

## Items (each resolves to its own terminal)

Each item resolves to exactly one of: `PASS` / `FAIL-<named reason>` /
`BLOCKED-<named reason>` / `PENDING-HUMAN-<what you need>`.

1. `pipelines/goal_plan_smoke/subgraphs/goal_lane_impl.dot` exists and parses.
2. Its "attempt"/implement node reads `$goal_condition_file` (the param name is
   exact) and instructs the actor to READ that file and implement its stated
   goal — NOT to write `$marker_content`. Model it on the proven `Implement`
   node in `pipelines/idea_to_pr/idea_to_pr.dot` (reads a referenced file, does
   real work, gathers evidence), contrasted with `goal_lane.dot`'s marker-only
   `Attempt` node.
3. It keeps the lane→parent contract: an independent verify step, then a commit-
   candidate node that writes `$lane_result_path` with `result=candidate` and
   `candidate_sha=<HEAD sha>`, plus the same diagnose/retry/budget backstop shape
   as `goal_lane.dot` so the parent graph can consume it unchanged.
4. It lints with ZERO ERROR diagnostics (machine check below).
5. `subgraphs/goal_lane.dot` is unchanged from base (verified by diff).

## The machine check (run it; show the output in the transcript)

```
cd /home/ken/workspace/attractor-pipelines/.worktrees/glf-real-work-brick
python3 -c "import sys; from compiler.validate import validate_dot_source; src=open('pipelines/goal_plan_smoke/subgraphs/goal_lane_impl.dot').read(); g,d,n=validate_dot_source(src); print('ERROR_COUNT', n); sys.exit(0 if n==0 else 1)"
grep -q 'goal_condition_file' pipelines/goal_plan_smoke/subgraphs/goal_lane_impl.dot && echo READS_PARAM_OK
grep -q 'lane_result_path' pipelines/goal_plan_smoke/subgraphs/goal_lane_impl.dot && grep -q 'candidate_sha' pipelines/goal_plan_smoke/subgraphs/goal_lane_impl.dot && echo CONTRACT_OK
git diff --quiet HEAD -- pipelines/goal_plan_smoke/subgraphs/goal_lane.dot && echo GOAL_LANE_UNCHANGED_OK
```

PASS = the lint line prints `ERROR_COUNT 0` and exits 0, AND `READS_PARAM_OK`,
`CONTRACT_OK`, and `GOAL_LANE_UNCHANGED_OK` all print. Paste the real output into
the transcript.

Note: behavioral end-to-end proof (a live compiled run that drives a real goal
file to a real commit) is the ORCHESTRATOR's job at integration — NOT yours. Your
bar is: the brick is structurally correct and lints clean. Do not attempt a full
model-driven pipeline run inside this lane.

## Working directory, branch, base

- Work ONLY in this worktree: `/home/ken/workspace/attractor-pipelines/.worktrees/glf-real-work-brick`.
- Your branch is `goal-batch/glf/real-work-brick`. Record your base with
  `git rev-parse HEAD` as your first act. Do NOT rebase, reset, or checkout
  another branch. Do NOT touch the main checkout or any sibling worktree.

## File ownership (touching anything else is a defect)

You OWN, and may CREATE/modify ONLY:
- `pipelines/goal_plan_smoke/subgraphs/goal_lane_impl.dot` (new)
- optionally `pipelines/goal_plan_smoke/subgraphs/goal_lane_impl.md` (a short
  companion note) and a trivial fixture goal-condition file UNDER
  `pipelines/goal_plan_smoke/fixtures/` if you want one for your own reasoning.

Do NOT edit `compiler/` anything, do NOT edit `goal_lane.dot`, `deliver_pr.dot`,
or `integration_correction.dot`. The compiler-side param plumbing is a SIBLING
lane's job. If your work seems to need a compiler change, record it as a residual
and keep going.

## Pinned seam (do not deviate — the sibling compiler lane emits this)

- The param you read is EXACTLY `$goal_condition_file`.
- Your commit-candidate node MUST write `$lane_result_path` as
  `{"result": "candidate", "candidate_sha": "<sha>"}` and print the
  `lane.result` / `lane.candidate_sha` line, exactly as `goal_lane.dot`'s
  `Candidate` node does — the parent graph reads that contract.

## Commit protocol

- Commit early and often to your own branch. LOCAL-ONLY batch: do NOT push.
- NEVER merge to main. NEVER `git merge`/`git rebase`. The orchestrator integrates.

## Host + capability limits

- `python3` and this repo are local and sufficient. The lint uses
  `compiler.validate` which locates the attractor engine from the installed
  `amplifier-bundle-attractor` cache; if it raises `EngineUnavailable`, that is a
  `BLOCKED-engine-unavailable` terminal for item 4 — report it, do not fake a
  pass.
- This box authors a `.dot`; it does not need to EXECUTE the pipeline. Do not
  ship a brick you could not lint.

## Time bound

Wall-clock bound is enforced externally. Hitting it is a terminal `BUDGET`
state — commit what is real, write DONE.json, stop.

## KNOWN (speed aid — not acceptance criteria)

Read these at base before authoring (per repo `AGENTS.md`: read `docs/primer.md`
+ `docs/RUBRIC.md` before touching any `.dot`; RUBRIC §5: copy the nearest proven
brick rather than inventing nodes):
- `pipelines/goal_plan_smoke/subgraphs/goal_lane.dot` — the marker brick to copy
  the SHAPE of (attempt → child-verify → candidate → diagnose → retry/budget).
  Its `Attempt` node (~`:76-80`) writes `$marker_content`; your implement node
  replaces that with "read `$goal_condition_file` and implement its goal."
- Its `Candidate` node (~`:106-111`) is the exact `$lane_result_path` /
  `candidate_sha` contract to reproduce.
- `pipelines/idea_to_pr/idea_to_pr.dot` — its `Implement` node (~`:183-187`) and
  `AcceptDesign` node (~`:158-162`) show the proven pattern of interpolating a
  file/context reference into a real coding prompt. Copy that idea.
- `docs/primer.md` "engine foot-gun card" and `docs/RUBRIC.md` §3 — every node
  must have a matching outgoing edge for each outcome it can produce; no dead
  ends. A brick that lints clean but dead-ends is not done.

## DONE.json (your final act)

`/DONE.json` is already gitignored — do NOT commit it. As your FINAL act, write
`DONE.json` in the worktree root:

```
{
  "lane": "real-work-brick",
  "session_id": "<your own session id>",
  "verdict": "COMPLETE | BLOCKED | PARTIAL",
  "branch": "goal-batch/glf/real-work-brick",
  "head": "<git rev-parse HEAD>",
  "pushed": false,
  "items": [ {"id": 1, "state": "PASS|FAIL-...|BLOCKED-..."}, ... ],
  "residuals": [ ],
  "pending_human": [ ],
  "suite": "lint => ERROR_COUNT 0; READS_PARAM_OK; CONTRACT_OK; GOAL_LANE_UNCHANGED_OK"
}
```

`verdict` is exactly one of `COMPLETE` / `BLOCKED` / `PARTIAL`.
