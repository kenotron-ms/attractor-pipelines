# Lane goal: compiler-goalref

/ goal

## Outcome (checkable end state)

The deterministic compiler in this repo accepts an OPTIONAL per-lane string
field `goal_condition_file` and threads it, verbatim, as an ADDITIVE, LAST
`--param goal_condition_file=<value>` entry in every lane's child launch argv —
AND when the field is omitted the generated `.dot` output is BYTE-IDENTICAL to
today's output. Proven by `python3 -m pytest compiler/tests/ -q` exiting 0 with
at least 83 passing tests (80 baseline + your new tests), where the new tests
prove BOTH the byte-identical-when-omitted behavior and the field-threaded-when-
present behavior.

## Disjunctive exit (the load-bearing sentence)

Complete when **either** every item below reaches a terminal state, **or** it is
conclusively demonstrated the remainder cannot, naming the blocker for each.
Items ending FAIL or BLOCKED are residuals, not failures of the goal.

## Items (each resolves to its own terminal)

Each item resolves to exactly one of: `PASS` / `FAIL-<named reason>` /
`BLOCKED-<named reason>` / `PENDING-HUMAN-<what you need>`.

1. `Lane` dataclass gains `goal_condition_file: str = ""` (optional, defaults
   empty).
2. `_build_lane` reads and validates the field: must be a string when provided;
   if non-empty, validate it with the same path/charset validator the sibling
   path-like field uses. Unknown/absent → default `""`.
3. The field survives `build_plan`'s lane re-construction (the second
   `Lane(...)` built after branch-namespace resolution) — it must NOT silently
   revert to the default.
4. The generator emits the field as the LAST `--param` in BOTH launch template
   bodies (wave-1 concurrent AND later-wave sequential), conditionally: present
   only when the field is non-empty; when empty the emitted argv is byte-for-byte
   what it is today.
5. `compiler/README.md` documents the new field: a row in the per-lane field
   schema table AND a note in the runtime `--param` contract that the value is
   passed opaquely to the child brick (the compiler never reads its contents).
6. New tests in `compiler/tests/test_compiler.py` prove: (a) omitting the field
   yields output byte-identical to the pre-change exemplar compile, and (b) a
   lane with `goal_condition_file` set emits exactly one
   `--param goal_condition_file=<value>` in each of its launches. Full suite
   green.

## The machine check (run it; show the output in the transcript)

```
cd /home/ken/workspace/attractor-pipelines/.worktrees/glf-compiler-goalref
python3 -m pytest compiler/tests/ -q
```

PASS = exit 0 AND the reported count is >= 83. Paste the real tail of the output
(the `NN passed` line) into the transcript. A green suite you did not run is not
evidence.

## Working directory, branch, base

- Work ONLY in this worktree: `/home/ken/workspace/attractor-pipelines/.worktrees/glf-compiler-goalref`.
- Your branch is `goal-batch/glf/compiler-goalref`. Record your base with
  `git rev-parse HEAD` as your first act. Do NOT rebase, reset, or checkout
  another branch. Do NOT touch the main checkout or any sibling worktree.

## File ownership (touching anything else is a defect)

You OWN, and may modify ONLY:
- `compiler/plan.py`
- `compiler/generator.py`
- `compiler/README.md`
- `compiler/tests/test_compiler.py`

If your work seems to require editing ANY other file, do NOT edit it. Record the
needed edit as a residual (file, exact change, why) in your final report and keep
going. The new lane brick that CONSUMES this param is a SIBLING lane's job — do
not create or edit any `.dot` file.

## Pinned seam (do not deviate — a sibling depends on this exact name)

- The param name is EXACTLY `goal_condition_file`. Not `goalref`, not
  `goal_file`, not `goal_condition`. The sibling brick reads `$goal_condition_file`.
- Emit it as `--param goal_condition_file=<value>`, appended AFTER the existing
  `max_attempts` param, in both launch bodies.

## Commit protocol

- Commit early and often to your own branch. This is a LOCAL-ONLY batch: do NOT
  push; commits on your branch are safe in the shared object store.
- NEVER merge to main. NEVER `git merge`/`git rebase` another branch. The
  orchestrator integrates.
- Keep each commit focused; conventional-commit messages.

## Host + capability limits

- Everything you need is local: `python3`, `pytest`, this repo. No network is
  required and none should be relied on.
- Do not weaken, delete, or `xfail` an existing test to make the suite pass. The
  suite is the acceptance gate; defeating it fails the goal.

## Time bound

Your wall-clock bound is enforced externally. If you hit it, that is a terminal
`BUDGET` state — commit what is real, write DONE.json, and stop. Do not rush the
work or skip the commit to beat the clock.

## KNOWN (speed aid — not acceptance criteria)

Verified insertion points (from a fresh reading of the code at base; confirm
before trusting):
- `compiler/plan.py:79-91` — `Lane` dataclass; add `goal_condition_file: str = ""`
  after `branch: str = ""`.
- `compiler/plan.py:439-511` — `_build_lane`; add the optional read+validate near
  the `child_dot` handling (~`:490`), and pass it into the `Lane(...)` return
  (~`:501-511`).
- `compiler/plan.py:407-420` — `build_plan` rebuilds each lane as
  `resolved_lanes[lane_id] = Lane(...)`; thread the field here too or it reverts
  to default.
- `compiler/generator.py:142-186` (`_LAUNCH_WAVE1_BODY`) and `:188-232`
  (`_LAUNCH_SEQUENTIAL_BODY`) — the `child_argv` list; the last existing param is
  `max_attempts=@@MAX_ATTEMPTS@@`. Append a new `@@GOAL_CONDITION_FILE_PARAM@@`
  token after it in BOTH.
- `compiler/generator.py:1008-1018` (`_render_launch`) — add a conditional
  `.replace("@@GOAL_CONDITION_FILE_PARAM@@", ...)` yielding `""` when
  `lane.goal_condition_file` is empty, else
  `, "--param", "goal_condition_file=<value>"`. Empty-default => byte-identical.
- Backward-compat tests to keep green: `test_d2_structural_equivalence_to_exemplar`
  (~`:191`), `test_determinism_same_spec_same_output` (~`:314`),
  `test_minimal_spec_all_optional_fields_omitted_compiles_and_corresponds`
  (~`:446`). Baseline before you start: 80 passed.
- Per-repo rule: read `docs/RUBRIC.md` §2 (self-report is not evidence) — your
  proof is the pytest output, pasted.

## DONE.json (your final act)

`/DONE.json` is already gitignored — do NOT commit it. As your FINAL act, write
`DONE.json` in the worktree root with exactly these fields:

```
{
  "lane": "compiler-goalref",
  "session_id": "<your own session id>",
  "verdict": "COMPLETE | BLOCKED | PARTIAL",
  "branch": "goal-batch/glf/compiler-goalref",
  "head": "<git rev-parse HEAD>",
  "pushed": false,
  "items": [ {"id": 1, "state": "PASS|FAIL-...|BLOCKED-..."}, ... ],
  "residuals": [ ],
  "pending_human": [ ],
  "suite": "python3 -m pytest compiler/tests/ -q => <the NN passed line>"
}
```

`verdict` is exactly one of `COMPLETE` / `BLOCKED` / `PARTIAL`. Without DONE.json
your lane cannot be told apart from a killed one.
