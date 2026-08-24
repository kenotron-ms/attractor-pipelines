"""The compiler: a ``plan.json``-shaped spec -> a ``goal_plan_smoke``-family
parent ``.dot``.

Deterministic Python. **No LLM call anywhere in this code path** -- that is a
hard design requirement (design doc: an LLM re-authoring the parent graph per
request risks reintroducing the exact class of bug fixed in commit ``fc27a29``).
Same spec in, byte-identical DOT out.

What it generalizes from the hand-authored exemplar
(``pipelines/goal_plan_smoke/goal_plan_smoke.dot``):

* the ``LaunchLaneX`` / ``ParentVerifyX`` / ``IntegrateX`` node triples, emitted
  per-lane instead of hand-duplicated;
* the wave-gating edges -- a lane in wave N+1 is reachable *only* via wave N's
  ``ACCEPTED`` edges, exactly as the exemplar does today, but constructed rather
  than copied;
* the aggregation / coherence shell loops -- ``for f in <lane ids>`` becomes
  data-driven from the spec instead of the literal ``lane_a lane_b lane_c``.

Execution model (faithful to the exemplar):

* **First wave** -- every lane launched concurrently from ``$product_base_sha``
  via a ``component`` fan-out into a ``tripleoctagon`` fan-in, then classified.
* **Later waves** -- each lane launched just-in-time, sequentially, from the
  current integration ``HEAD`` (which already contains every prior integrated
  lane -- this is what structurally guarantees the wave gate). This mirrors the
  exemplar's ``LaunchLaneC`` (Wave 2, sequential, forks the integration HEAD).
* All lanes are parent-verified and integrated one at a time in
  ``integration_order``.
"""

from __future__ import annotations

from .plan import Plan, build_plan

# --------------------------------------------------------------------------
# Position -> letter suffix (0 -> A, 1 -> B, ... 25 -> Z, 26 -> AA, ...).
# The exemplar names lane nodes by position in integration order
# (lane_a -> LaunchLaneA), not by lane id -- reproduced here so arbitrary lane
# ids get clean, collision-free node names.
# --------------------------------------------------------------------------


def _suffix(index: int) -> str:
    letters = ""
    n = index
    while True:
        letters = chr(ord("A") + (n % 26)) + letters
        n = n // 26 - 1
        if n < 0:
            break
    return letters


def _dot_escape(s: str) -> str:
    """Escape an intended tool_command/label/prompt body for emission inside a
    double-quoted DOT attribute value. Round-trips through the engine's
    ``parse_dot`` back to the original string (verified by the compiler tests).
    """
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    return s


def _pyliteral(items: tuple[str, ...] | list[str]) -> str:
    """Render a list of strings as a Python list literal for embedding inside a
    ``python3 - <<'PYEOF'`` heredoc. ``repr`` prefers single quotes when a
    string contains double quotes, which keeps shell verifier argvs
    (``[ "$(cat x)" = "y" ]``) readable and avoids nested-quote escaping.
    """
    return "[" + ", ".join(repr(a) for a in items) + "]"


class _Emitter:
    def __init__(self) -> None:
        self._lines: list[str] = []

    def line(self, text: str = "") -> None:
        self._lines.append(text)

    def node(self, node_id: str, attrs: list[tuple[str, str, bool]]) -> None:
        """Emit a node. ``attrs`` is a list of (name, value, quoted) triples."""
        rendered = []
        for name, value, quoted in attrs:
            if quoted:
                rendered.append(f'{name}="{_dot_escape(value)}"')
            else:
                rendered.append(f"{name}={value}")
        self._lines.append(f"  {node_id} [")
        self._lines.append("    " + ",\n    ".join(rendered))
        self._lines.append("  ];")

    def edge(self, src: str, dst: str, condition: str = "", weight: str = "") -> None:
        parts = []
        if condition:
            parts.append(f'condition="{_dot_escape(condition)}"')
        if weight:
            parts.append(f'weight="{weight}"')
        suffix = ""
        if parts:
            suffix = " [" + ", ".join(parts) + "]"
        self._lines.append(f"  {src} -> {dst}{suffix};")

    def render(self) -> str:
        return "\n".join(self._lines) + "\n"


# --------------------------------------------------------------------------
# tool_command body templates (intended scripts; @@TOKEN@@ placeholders are
# substituted via str.replace to avoid brace-escaping against the embedded JSON).
# --------------------------------------------------------------------------

_LAUNCH_WAVE1_BODY = """#!/bin/sh
set -e
python3 - <<'PYEOF'
import sys, json, subprocess
sys.path.insert(0, "$runtime_py_dir")
import goal_plan_runtime as gpr
registry = gpr.WorktreeRegistry("$state_root/run-owned-worktrees.json", "$state_root/run-owned-worktrees.lock")
wt = gpr.create_registered_worktree(registry, ("$git_bin",), "$target_repo", "$worktree_root", "@@LANE@@", kind="lane", commit_sha="$product_base_sha", branch="@@BRANCH@@")
contract = {
    "schema_version": "goal-plan.process-launch-contract/v1",
    "process_kind": "lane", "process_id": "@@LANE@@", "process_run_id": "$run_id-@@LANE@@",
    "child_argv": ["python3", "-m", "amplifier_module_pipeline_runner.cli", "run",
                   "$subgraphs_dir/@@CHILD_DOT@@", "--cwd", ".", "--on-human-gate", "fail",
                   "--param", "lane_id=@@LANE@@", "--param", "marker_file=@@MARKER_FILE@@",
                   "--param", "marker_content=@@MARKER_CONTENT@@", "--param", "seeded_failure=@@SEEDED@@",
                   "--param", "runtime_py_dir=$runtime_py_dir",
                   "--param", "output_root=$state_root/verify-out/@@LANE@@",
                   "--param", "evidence_path=$state_root/evidence/@@LANE@@.json",
                   "--param", "lane_result_path=$state_root/lane-results/@@LANE@@.json",
                   "--param", "ledger_path=$state_root/budgets/@@LANE@@.json",
                   "--param", "ledger_lock_path=$state_root/budgets/@@LANE@@.lock",
                   "--param", "run_id=$run_id", "--param", "max_attempts=@@MAX_ATTEMPTS@@"],
    "child_cwd": wt, "child_env": {"PYTHONPATH": "$runner_pythonpath"},
    "wall_timeout_seconds": 600, "term_grace_seconds": 10,
    "stdout_path": "$state_root/logs/@@LANE@@.stdout", "stderr_path": "$state_root/logs/@@LANE@@.stderr",
}
import os
os.makedirs("$state_root/contracts", exist_ok=True)
os.makedirs("$state_root/lane-results", exist_ok=True)
os.makedirs("$state_root/logs", exist_ok=True)
os.makedirs("$state_root/acks", exist_ok=True)
os.makedirs("$state_root/results", exist_ok=True)
import hashlib
with open("$state_root/contracts/@@LANE@@.json", "w") as f:
    json.dump(contract, f, sort_keys=True)
contract_sha = hashlib.sha256(open("$state_root/contracts/@@LANE@@.json", "rb").read()).hexdigest()
intent = {"schema_version": "goal-plan.launch-intent/v1", "process_run_id": "$run_id-@@LANE@@", "contract_sha256": contract_sha}
with open("$state_root/contracts/@@LANE@@.intent.json", "w") as f:
    json.dump(intent, f, sort_keys=True)
rc = subprocess.run(["python3", "$runtime_py_dir/goal_plan_supervisor.py", "run",
    "--contract", "$state_root/contracts/@@LANE@@.json", "--intent", "$state_root/contracts/@@LANE@@.intent.json",
    "--ledger", "$state_root/supervisor-ledger.json", "--ack", "$state_root/acks/@@LANE@@.json",
    "--result", "$state_root/results/@@LANE@@.json"])
print("launched" if rc.returncode == 0 else "supervisor_infra_failure")
PYEOF"""

_LAUNCH_SEQUENTIAL_BODY = """#!/bin/sh
set -e
python3 - <<'PYEOF'
import sys, json, subprocess, os, hashlib
sys.path.insert(0, "$runtime_py_dir")
import goal_plan_runtime as gpr
registry = gpr.WorktreeRegistry("$state_root/run-owned-worktrees.json", "$state_root/run-owned-worktrees.lock")
integration_head = subprocess.run(["$git_bin", "rev-parse", "HEAD"], cwd="$target_repo", capture_output=True, text=True, check=True).stdout.strip()
wt = gpr.create_registered_worktree(registry, ("$git_bin",), "$target_repo", "$worktree_root", "@@LANE@@", kind="lane", commit_sha=integration_head, branch="@@BRANCH@@")
contract = {
    "schema_version": "goal-plan.process-launch-contract/v1",
    "process_kind": "lane", "process_id": "@@LANE@@", "process_run_id": "$run_id-@@LANE@@",
    "child_argv": ["python3", "-m", "amplifier_module_pipeline_runner.cli", "run",
                   "$subgraphs_dir/@@CHILD_DOT@@", "--cwd", ".", "--on-human-gate", "fail",
                   "--param", "lane_id=@@LANE@@", "--param", "marker_file=@@MARKER_FILE@@",
                   "--param", "marker_content=@@MARKER_CONTENT@@", "--param", "seeded_failure=@@SEEDED@@",
                   "--param", "runtime_py_dir=$runtime_py_dir",
                   "--param", "output_root=$state_root/verify-out/@@LANE@@",
                   "--param", "evidence_path=$state_root/evidence/@@LANE@@.json",
                   "--param", "lane_result_path=$state_root/lane-results/@@LANE@@.json",
                   "--param", "ledger_path=$state_root/budgets/@@LANE@@.json",
                   "--param", "ledger_lock_path=$state_root/budgets/@@LANE@@.lock",
                   "--param", "run_id=$run_id", "--param", "max_attempts=@@MAX_ATTEMPTS@@"],
    "child_cwd": wt, "child_env": {"PYTHONPATH": "$runner_pythonpath"},
    "wall_timeout_seconds": 600, "term_grace_seconds": 10,
    "stdout_path": "$state_root/logs/@@LANE@@.stdout", "stderr_path": "$state_root/logs/@@LANE@@.stderr",
}
os.makedirs("$state_root/contracts", exist_ok=True)
os.makedirs("$state_root/lane-results", exist_ok=True)
os.makedirs("$state_root/logs", exist_ok=True)
os.makedirs("$state_root/acks", exist_ok=True)
os.makedirs("$state_root/results", exist_ok=True)
with open("$state_root/contracts/@@LANE@@.json", "w") as f:
    json.dump(contract, f, sort_keys=True)
contract_sha = hashlib.sha256(open("$state_root/contracts/@@LANE@@.json", "rb").read()).hexdigest()
intent = {"schema_version": "goal-plan.launch-intent/v1", "process_run_id": "$run_id-@@LANE@@", "contract_sha256": contract_sha}
with open("$state_root/contracts/@@LANE@@.intent.json", "w") as f:
    json.dump(intent, f, sort_keys=True)
rc = subprocess.run(["python3", "$runtime_py_dir/goal_plan_supervisor.py", "run",
    "--contract", "$state_root/contracts/@@LANE@@.json", "--intent", "$state_root/contracts/@@LANE@@.intent.json",
    "--ledger", "$state_root/supervisor-ledger.json", "--ack", "$state_root/acks/@@LANE@@.json",
    "--result", "$state_root/results/@@LANE@@.json"])
sup = json.load(open("$state_root/results/@@LANE@@.json")) if rc.returncode == 0 and os.path.exists("$state_root/results/@@LANE@@.json") else {}
print("launched" if sup.get("verdict") == "EXITED" and sup.get("normalized_exit_code") == 0 else "crashed")
PYEOF"""

_CLASSIFY_BODY_HEAD = """#!/bin/sh
set -e
python3 - <<'PYEOF'
import json, os
def classify(lane):
    sup_path = "$state_root/results/" + lane + ".json"
    res_path = "$state_root/lane-results/" + lane + ".json"
    if not os.path.exists(sup_path):
        return "crashed"
    sup = json.load(open(sup_path))
    if sup.get("verdict") != "EXITED" or sup.get("normalized_exit_code") != 0:
        return "crashed"
    if not os.path.exists(res_path):
        return "crashed"
    lane_result = json.load(open(res_path))
    return lane_result.get("result", "crashed")
"""

_PARENT_VERIFY_BODY = """#!/bin/sh
set -e
python3 - <<'PYEOF'
import sys, json
sys.path.insert(0, "$runtime_py_dir")
import goal_plan_runtime as gpr
lane_result = json.load(open("$state_root/lane-results/@@LANE@@.json"))
if lane_result.get("result") != "candidate":
    print("skip:" + lane_result.get("blocker_reason", "unknown"))
else:
    registry = gpr.WorktreeRegistry("$state_root/run-owned-worktrees.json", "$state_root/run-owned-worktrees.lock")
    result = gpr.run_parent_verifier_envelope(
        registry=registry, git_argv_prefix=("$git_bin",), target_repo="$target_repo",
        worktree_root="$worktree_root", worktree_id="candidate-@@LANE@@",
        candidate_sha=lane_result["candidate_sha"],
        verifier_argv=@@VERIFIER@@,
        timeout_seconds=30, output_root="$state_root/verify-out/candidate-@@LANE@@",
        evidence_path="$state_root/evidence/candidate-@@LANE@@.json",
    )
    print(result.verdict)
PYEOF"""

_INTEGRATE_BODY = """#!/bin/sh
set -e
python3 - <<'PYEOF'
import sys, json
sys.path.insert(0, "$runtime_py_dir")
import goal_plan_runtime as gpr
lane_result = json.load(open("$state_root/lane-results/@@LANE@@.json"))
journal = gpr.IntegrationJournal("$state_root/integration-journal.json", "$state_root/integration-journal.lock")
entry = gpr.integrate_candidate(
    git_argv_prefix=("$git_bin",), integration_worktree="$target_repo", journal=journal,
    lane_id="@@LANE@@", candidate_sha=lane_result["candidate_sha"],
    aggregate_verifier_argv=@@AGG@@,
    aggregate_timeout_seconds=30, output_root="$state_root/verify-out/aggregate-after-@@LANE@@",
    evidence_path="$state_root/evidence/aggregate-after-@@LANE@@.json",
)
print(entry["result"])
PYEOF"""

_CORRECTION_BODY = """#!/bin/sh
set -e
python3 - <<'PYEOF'
import sys, json, subprocess, os, hashlib
sys.path.insert(0, "$runtime_py_dir")
integration_head = subprocess.run(["$git_bin", "rev-parse", "HEAD"], cwd="$target_repo", capture_output=True, text=True, check=True).stdout.strip()
branch = subprocess.run(["$git_bin", "rev-parse", "--abbrev-ref", "HEAD"], cwd="$target_repo", capture_output=True, text=True, check=True).stdout.strip()
with open("$state_root/aggregate_verifier_argv.json", "w") as f:
    json.dump(@@AGG@@, f)
contract = {
    "schema_version": "goal-plan.process-launch-contract/v1",
    "process_kind": "correction", "process_id": "integration_correction", "process_run_id": "$run_id-correction",
    "child_argv": ["python3", "-m", "amplifier_module_pipeline_runner.cli", "run",
                   "$subgraphs_dir/@@CORRECTION_DOT@@", "--cwd", ".", "--on-human-gate", "fail",
                   "--param", "integration_branch=" + branch,
                   "--param", "allowed_paths_csv=@@ALLOWED_PATHS@@",
                   "--param", "runtime_py_dir=$runtime_py_dir",
                   "--param", "ledger_path=$state_root/budgets/correction.json",
                   "--param", "ledger_lock_path=$state_root/budgets/correction.lock",
                   "--param", "run_id=$run_id",
                   "--param", "aggregate_verifier_argv_json=$state_root/aggregate_verifier_argv.json",
                   "--param", "output_root=$state_root/verify-out/correction",
                   "--param", "evidence_path=$state_root/evidence/correction.json",
                   "--param", "correction_result_path=$state_root/lane-results/correction.json"],
    "child_cwd": "$target_repo", "child_env": {"PYTHONPATH": "$runner_pythonpath"},
    "wall_timeout_seconds": 600, "term_grace_seconds": 10,
    "stdout_path": "$state_root/logs/correction.stdout", "stderr_path": "$state_root/logs/correction.stderr",
}
with open("$state_root/contracts/correction.json", "w") as f:
    json.dump(contract, f, sort_keys=True)
contract_sha = hashlib.sha256(open("$state_root/contracts/correction.json", "rb").read()).hexdigest()
intent = {"schema_version": "goal-plan.launch-intent/v1", "process_run_id": "$run_id-correction", "contract_sha256": contract_sha}
with open("$state_root/contracts/correction.intent.json", "w") as f:
    json.dump(intent, f, sort_keys=True)
rc = subprocess.run(["python3", "$runtime_py_dir/goal_plan_supervisor.py", "run",
    "--contract", "$state_root/contracts/correction.json", "--intent", "$state_root/contracts/correction.intent.json",
    "--ledger", "$state_root/supervisor-ledger.json", "--ack", "$state_root/acks/correction.json",
    "--result", "$state_root/results/correction.json"])
sup = json.load(open("$state_root/results/correction.json")) if rc.returncode == 0 and os.path.exists("$state_root/results/correction.json") else {}
if sup.get("verdict") != "EXITED" or sup.get("normalized_exit_code") != 0:
    print("crashed"); sys.exit(0)
result = json.load(open("$state_root/lane-results/correction.json"))
print(result.get("result", "crashed"))
PYEOF"""

_COHERENCE_CHECK_BODY = (
    "#!/bin/sh\nset -e\n"
    "finding=$(python3 -c \"import json;print(json.load(open('.resolve/coherence/review.json'))['finding'])\" 2>/dev/null || echo False)\n"
    "if [ \"$finding\" = \"True\" ]; then printf 'finding'; else printf 'no_finding'; fi"
)

_CHECK_ABORT_BODY = (
    "#!/bin/sh\nset -e\n"
    "if [ -f \"$state_root/ABORT_REQUESTED\" ]; then printf 'abort_requested'; else printf 'proceed'; fi"
)

_CHECK_CORRESPONDENCE_BODY = """#!/bin/sh
set -e
python3 - <<'PYEOF'
import json, re
with open("$plan_json_path") as f:
    plan = json.load(f)
with open("$parent_dot_path") as f:
    dot_src = f.read()
def attr(name):
    m = re.search(name + r'="([^"]*)"', dot_src)
    return m.group(1) if m else None
ok = True
ok &= attr("plan_lanes") == ",".join(sorted(plan["lanes"].keys()))
ok &= attr("plan_waves") == ",".join(str(w["wave"]) for w in plan["waves"])
ok &= attr("plan_integration_order") == ",".join(plan["integration_order"])
ok &= attr("plan_terminals") == ",".join(plan["terminals"])
print("correspondence_ok" if ok else "correspondence_mismatch")
PYEOF"""

_ADMIT_BODY = """#!/bin/sh
set -e
python3 - <<'PYEOF'
import sys
sys.path.insert(0, "$runtime_py_dir")
import goal_plan_runtime as gpr
try:
    gpr.admit_run(
        target_repo="$target_repo",
        state_root="$state_root",
        worktree_root="$worktree_root",
        delivery_state_root="$delivery_state_root",
        compiled_source_paths={"runtime": "$runtime_py_dir/goal_plan_runtime.py"},
        parent_binding={"run_id": "$run_id"},
        git_argv_prefix=("$git_bin",),
    )
    print("admitted")
except gpr.GoalPlanRuntimeError as e:
    print("blocked:" + str(e))
PYEOF"""

_CLEANUP_BODY = """#!/bin/sh
set -e
python3 - <<'PYEOF'
import sys
sys.path.insert(0, "$runtime_py_dir")
import goal_plan_runtime as gpr
registry = gpr.WorktreeRegistry("$state_root/run-owned-worktrees.json", "$state_root/run-owned-worktrees.lock")
authority = gpr.derive_cleanup_authority(trusted_runtime_verdict="PASS", parent_binding_verdict="PASS")
record = gpr.pre_terminal_cleanup(
    registry=registry, git_argv_prefix=("$git_bin",), target_repo="$target_repo",
    authority=authority, result_path="@@RESULT_PATH@@",
)
print("cleaned")
PYEOF"""


# --------------------------------------------------------------------------
# Shell-loop builders (data-driven from the spec's lane ids).
# --------------------------------------------------------------------------


def _marker_pattern() -> str:
    return "SMOKE_MARKER_$f.txt"


def _aggregate_argv(lane_ids: list[str]) -> list[str]:
    """Cumulative existence-aggregate over lane ids, family convention
    (SMOKE_MARKER_<id>.txt). One lane -> a plain ``test -f``; many -> a loop.
    """
    if len(lane_ids) == 1:
        return ["/bin/sh", "-c", f"test -f SMOKE_MARKER_{lane_ids[0]}.txt"]
    ids = " ".join(lane_ids)
    return [
        "/bin/sh",
        "-c",
        f"for f in {ids}; do test -f {_marker_pattern()} || exit 1; done",
    ]


def _aggregate_gate_body(lane_ids: list[str]) -> str:
    ids = " ".join(lane_ids)
    return (
        "#!/bin/sh\nset -e\n"
        f"for f in {ids}; do test -f {_marker_pattern()} || {{ printf 'aggregate_fail'; exit 0; }}; done\n"
        "printf 'aggregate_ok'"
    )


def _final_freeze_body(lane_ids: list[str]) -> str:
    ids = " ".join(lane_ids)
    return (
        "#!/bin/sh\nset -e\n"
        "final_head=$($git_bin rev-parse HEAD)\n"
        'printf \'%s\' "$final_head" > "$state_root/final_head.txt"\n'
        f"for f in {ids}; do\n"
        f'  test -f {_marker_pattern()} && [ "$(cat {_marker_pattern()})" = "$f:ok" ] || {{ printf \'sweep_fail\'; exit 0; }}\n'
        "done\n"
        "printf 'sweep_ok'"
    )


# --------------------------------------------------------------------------
# The compiler.
# --------------------------------------------------------------------------

_HEADER_COMMENT = """// GENERATED by compiler/ (goal-plan compiler) -- do not edit by hand.
// Regenerate from the plan spec instead. Deterministic output; no LLM.
//
// A {plan_id} member of the Goal Plan Attractor family: a static parent program
// that launches, parent-verifies, and integrates {n_lanes} lane(s) across
// {n_waves} wave(s). Wave 1 lanes run concurrently from $product_base_sha;
// later-wave lanes launch sequentially from the integration HEAD. This parent
// never trusts a child's self-report -- outcomes come from the supervisor
// result file and independent parent-side verification via
// pipelines/goal_plan_smoke/python/goal_plan_runtime.py.
//
// Required context ($param) supplied by the harness/backend at launch:
//   $target_repo, $state_root, $worktree_root, $delivery_state_root
//   $run_id, $repo, $delivery_enabled ("true"|"false")
//   $product_base_sha   - base commit every wave-1 lane worktree forks from
//   $runtime_py_dir      - absolute path to the goal_plan runtime python dir
//   $subgraphs_dir       - absolute path to the reused subgraphs dir
//   $git_bin             - absolute, authenticated git argv prefix (single token)
//   $runner_pythonpath   - PYTHONPATH (colon-joined) for the child runner
//   $plan_json_path      - path to this pipeline's plan.json (correspondence)
//   $parent_dot_path     - path to this generated parent .dot (correspondence)"""


def compile_plan(spec: dict | Plan) -> str:
    """Compile a plan spec (raw dict or validated :class:`Plan`) into a
    ``goal_plan_smoke``-family parent ``.dot`` source string.
    """
    plan = spec if isinstance(spec, Plan) else build_plan(spec)

    order = list(plan.integration_order)
    fw = plan.first_wave()
    fw_lanes = plan.first_wave_lane_ids()
    suffix_of = {lane_id: _suffix(i) for i, lane_id in enumerate(order)}

    em = _Emitter()
    em.line(
        _HEADER_COMMENT.format(
            plan_id=plan.plan_id,
            n_lanes=len(order),
            n_waves=len(plan.waves),
        )
    )
    em.line(f"digraph {plan.plan_id} {{")

    # ---- graph attributes ---------------------------------------------
    graph_label = f"{plan.plan_id} -- Goal Plan Attractor family, static parent"
    em.line("  graph [")
    em.line("    rankdir=TB,")
    em.line(f'    label="{_dot_escape(graph_label)}",')
    em.line("    default_max_retry=1,")
    em.line('    default_fidelity="summary:high",')
    em.line(f'    plan_lanes="{",".join(plan.lane_ids_sorted())}",')
    em.line(f'    plan_waves="{",".join(str(w) for w in plan.waves)}",')
    em.line(f'    plan_integration_order="{",".join(order)}",')
    em.line(f'    plan_terminals="{",".join(plan.terminals)}"')
    em.line("  ];")
    em.line("")
    em.line('  Start [shape=Mdiamond, label="Start"];')
    em.line('  Exit  [shape=Msquare,  label="Exit"];')
    em.line("")

    # ---- Wave 0: abort / correspondence / admission -------------------
    em.node(
        "CheckAbortRequested",
        [
            ("shape", "parallelogram", False),
            ("label", "Check Abort Requested", True),
            ("tool_command", _CHECK_ABORT_BODY, True),
        ],
    )
    em.edge("Start", "CheckAbortRequested")
    em.edge(
        "CheckAbortRequested",
        "CheckPlanCorrespondence",
        "context.tool.last_line=proceed",
        "2",
    )
    em.edge(
        "CheckAbortRequested",
        "AbortedCarrier",
        "context.tool.last_line=abort_requested",
    )

    em.node(
        "CheckPlanCorrespondence",
        [
            ("shape", "parallelogram", False),
            ("label", "Check Plan<->DOT Correspondence", True),
            ("tool_command", _CHECK_CORRESPONDENCE_BODY, True),
        ],
    )
    em.edge("Start", "CheckPlanCorrespondence")
    em.edge(
        "CheckPlanCorrespondence",
        "Admit",
        "context.tool.last_line=correspondence_ok",
        "2",
    )
    em.edge(
        "CheckPlanCorrespondence",
        "PrelaunchBlocked",
        "context.tool.last_line=correspondence_mismatch",
    )

    em.node(
        "Admit",
        [
            ("shape", "parallelogram", False),
            ("label", "Admit Run", True),
            ("tool_command", _ADMIT_BODY, True),
        ],
    )
    first_launch_target = f"Wave{fw}Launch"
    em.edge("Admit", first_launch_target, "context.tool.last_line=admitted", "2")
    em.edge("Admit", "PrelaunchBlocked", "context.tool.last_line!=admitted")

    em.node(
        "PrelaunchBlocked",
        [
            ("shape", "parallelogram", False),
            ("label", "Prelaunch Infrastructure Blocked", True),
            (
                "tool_command",
                'printf \'{"terminal.status": "PRELAUNCH_INFRASTRUCTURE_BLOCKED"}\'',
                True,
            ),
            ("parse_json", "true", True),
        ],
    )
    em.edge("PrelaunchBlocked", "InfraCarrier")
    em.line("")

    # ---- First wave: concurrent fan-out / fan-in ----------------------
    em.node(
        f"Wave{fw}Launch",
        [
            ("shape", "component", False),
            ("label", f"Wave {fw}: Launch {' + '.join(fw_lanes)}", True),
            ("join_policy", "wait_all", True),
            ("error_policy", "continue", True),
            ("max_parallel", str(len(fw_lanes)), False),
        ],
    )
    for lane_id in fw_lanes:
        em.edge(f"Wave{fw}Launch", f"LaunchLane{suffix_of[lane_id]}")

    for lane_id in fw_lanes:
        lane = plan.lanes[lane_id]
        em.node(
            f"LaunchLane{suffix_of[lane_id]}",
            [
                ("shape", "parallelogram", False),
                ("label", f"Launch {lane_id}", True),
                ("tool_command", _render_launch(_LAUNCH_WAVE1_BODY, lane, plan), True),
            ],
        )
        em.edge(f"LaunchLane{suffix_of[lane_id]}", f"Wave{fw}Collect")

    em.node(
        f"Wave{fw}Collect",
        [
            ("shape", "tripleoctagon", False),
            ("label", f"Wave {fw}: Collect {' + '.join(fw_lanes)}", True),
        ],
    )
    em.edge(f"Wave{fw}Collect", f"ClassifyWave{fw}")

    em.node(
        f"ClassifyWave{fw}",
        [
            ("shape", "parallelogram", False),
            ("label", f"Classify Wave {fw} Lane Outcomes", True),
            ("tool_command", _render_classify(fw_lanes), True),
        ],
    )
    em.edge(
        f"ClassifyWave{fw}",
        f"ParentVerify{suffix_of[order[0]]}",
        "context.tool.last_line!=''",
    )
    em.line("")

    # ---- Parent-verify + sequential integration in integration_order --
    integrated_so_far: list[str] = []
    for i, lane_id in enumerate(order):
        lane = plan.lanes[lane_id]
        sfx = suffix_of[lane_id]
        integrated_so_far.append(lane_id)

        # A later-wave lane is launched just-in-time (sequential, forks HEAD).
        if lane.wave != fw:
            em.node(
                f"LaunchLane{sfx}",
                [
                    ("shape", "parallelogram", False),
                    ("label", f"Launch {lane_id} (Wave {lane.wave}, sequential)", True),
                    (
                        "tool_command",
                        _render_launch(_LAUNCH_SEQUENTIAL_BODY, lane, plan),
                        True,
                    ),
                ],
            )
            em.edge(
                f"LaunchLane{sfx}",
                f"ParentVerify{sfx}",
                "context.tool.last_line=launched",
                "2",
            )
            em.edge(
                f"LaunchLane{sfx}", "InfraCarrier", "context.tool.last_line=crashed"
            )

        # ParentVerify
        em.node(
            f"ParentVerify{sfx}",
            [
                ("shape", "parallelogram", False),
                ("label", f"Parent-Verify {lane_id} Candidate", True),
                (
                    "tool_command",
                    _PARENT_VERIFY_BODY.replace("@@LANE@@", lane_id).replace(
                        "@@VERIFIER@@", _pyliteral(lane.verifier_argv)
                    ),
                    True,
                ),
            ],
        )
        em.edge(
            f"ParentVerify{sfx}", f"Integrate{sfx}", "context.tool.last_line=PASS", "2"
        )
        em.edge(f"ParentVerify{sfx}", "InfraCarrier", "context.tool.last_line=INFRA")
        em.edge(f"ParentVerify{sfx}", "Residuals", "context.tool.last_line=FAIL")
        em.edge(f"ParentVerify{sfx}", "Residuals", "context.tool.last_line!=PASS")

        # Integrate
        agg = _aggregate_argv(list(integrated_so_far))
        em.node(
            f"Integrate{sfx}",
            [
                ("shape", "parallelogram", False),
                ("label", f"Integrate {lane_id} (merge + aggregate)", True),
                (
                    "tool_command",
                    _INTEGRATE_BODY.replace("@@LANE@@", lane_id).replace(
                        "@@AGG@@", _pyliteral(agg)
                    ),
                    True,
                ),
            ],
        )
        # Successor of this Integrate's ACCEPTED edge.
        if i + 1 < len(order):
            nxt = order[i + 1]
            if plan.lanes[nxt].wave == fw:
                successor = f"ParentVerify{suffix_of[nxt]}"
            else:
                successor = f"LaunchLane{suffix_of[nxt]}"
        else:
            successor = "PreCoherenceAggregate"
        em.edge(f"Integrate{sfx}", successor, "context.tool.last_line=ACCEPTED", "2")
        em.edge(
            f"Integrate{sfx}", "InfraCarrier", "context.tool.last_line=AGGREGATE_INFRA"
        )
        em.edge(f"Integrate{sfx}", "Residuals", "context.tool.last_line=MERGE_CONFLICT")
        em.edge(f"Integrate{sfx}", "Residuals", "context.tool.last_line=AGGREGATE_FAIL")
        em.line("")

    # ---- Coherence, bounded correction, final sweep -------------------
    all_ids = order  # integration order == full lane list
    em.node(
        "PreCoherenceAggregate",
        [
            ("shape", "parallelogram", False),
            ("label", "Pre-Coherence Aggregate", True),
            ("tool_command", _aggregate_gate_body(all_ids), True),
        ],
    )
    em.edge(
        "PreCoherenceAggregate", "Coherence", "context.tool.last_line=aggregate_ok", "2"
    )
    em.edge(
        "PreCoherenceAggregate", "InfraCarrier", "context.tool.last_line=aggregate_fail"
    )

    coherence_prompt = (
        f"All {len(all_ids)} lanes ({', '.join(all_ids)}) are integrated and each marker file is present and "
        "independently verified. Review the integrated state for any cross-lane interaction defect (an unintended "
        "conflict pattern between the marker files, anything inconsistent across lanes). This is a real run with "
        "deliberately scoped per-lane tasks, so in the common case there is nothing to find -- do NOT invent a "
        'finding to justify a correction. Write .resolve/coherence/review.json with {"finding": true|false, '
        '"description": "..."}. Print the single line: reviewed'
    )
    em.node(
        "Coherence",
        [
            ("shape", "box", False),
            ("fidelity", "full", True),
            ("label", "Cross-Lane Coherence Review", True),
            ("prompt", coherence_prompt, True),
        ],
    )
    em.edge("Coherence", "CoherenceCheck")

    em.node(
        "CoherenceCheck",
        [
            ("shape", "parallelogram", False),
            ("label", "Coherence Check", True),
            ("tool_command", _COHERENCE_CHECK_BODY, True),
        ],
    )
    em.edge("CoherenceCheck", "Correction", "context.tool.last_line=finding")
    em.edge("CoherenceCheck", "FinalFreeze", "context.tool.last_line=no_finding", "2")

    correction_agg = _aggregate_argv(list(all_ids))
    em.node(
        "Correction",
        [
            ("shape", "parallelogram", False),
            ("label", "Launch Integration Correction (bounded, 1 round)", True),
            (
                "tool_command",
                _CORRECTION_BODY.replace("@@AGG@@", _pyliteral(correction_agg))
                .replace("@@CORRECTION_DOT@@", _basename(plan.correction_child_dot))
                .replace("@@ALLOWED_PATHS@@", ",".join(all_ids)),
                True,
            ),
        ],
    )
    em.edge(
        "Correction",
        "AffectedClosureAggregate",
        "context.tool.last_line=corrected",
        "2",
    )
    em.edge("Correction", "Residuals", "context.tool.last_line=blocked")
    em.edge("Correction", "InfraCarrier", "context.tool.last_line=crashed")

    em.node(
        "AffectedClosureAggregate",
        [
            ("shape", "parallelogram", False),
            ("label", "Affected-Closure + Fresh Coherence Aggregate", True),
            ("tool_command", _aggregate_gate_body(all_ids), True),
        ],
    )
    em.edge(
        "AffectedClosureAggregate",
        "FinalFreeze",
        "context.tool.last_line=aggregate_ok",
        "2",
    )
    em.edge(
        "AffectedClosureAggregate",
        "InfraCarrier",
        "context.tool.last_line=aggregate_fail",
    )

    em.node(
        "FinalFreeze",
        [
            ("shape", "parallelogram", False),
            ("label", "Freeze Final HEAD + Lane Sweep", True),
            ("tool_command", _final_freeze_body(all_ids), True),
        ],
    )
    em.edge(
        "FinalFreeze",
        "FinalAggregateAfterSweep",
        "context.tool.last_line=sweep_ok",
        "2",
    )
    em.edge("FinalFreeze", "InfraCarrier", "context.tool.last_line=sweep_fail")

    em.node(
        "FinalAggregateAfterSweep",
        [
            ("shape", "parallelogram", False),
            ("label", "Final Aggregate After Sweep", True),
            ("tool_command", _aggregate_gate_body(all_ids), True),
        ],
    )
    em.edge(
        "FinalAggregateAfterSweep",
        "DeliveryGate",
        "context.tool.last_line=aggregate_ok",
        "2",
    )
    em.edge(
        "FinalAggregateAfterSweep",
        "InfraCarrier",
        "context.tool.last_line=aggregate_fail",
    )
    em.line("")

    # ---- Delivery -----------------------------------------------------
    em.node(
        "DeliveryGate",
        [
            ("shape", "parallelogram", False),
            ("label", "Delivery Enabled?", True),
            (
                "tool_command",
                "#!/bin/sh\nset -e\nif [ \"$delivery_enabled\" = \"true\" ]; then printf 'deliver'; else printf 'skip_delivery'; fi",
                True,
            ),
        ],
    )
    em.edge("DeliveryGate", "Deliver", "context.tool.last_line=deliver", "2")
    em.edge(
        "DeliveryGate", "PreTerminalCleanup", "context.tool.last_line=skip_delivery"
    )

    em.node(
        "Deliver",
        [
            ("shape", "folder", False),
            ("label", "Deliver PR (subgraph)", True),
            ("dot_file", plan.delivery_child_dot, True),
            ("outputs", "delivery.pr_url,delivery.result", True),
        ],
    )
    em.edge("Deliver", "PreTerminalCleanup")
    em.line("")

    # ---- Cleanup + terminals ------------------------------------------
    em.node(
        "PreTerminalCleanup",
        [
            ("shape", "parallelogram", False),
            ("label", "Pre-Terminal Cleanup", True),
            (
                "tool_command",
                _CLEANUP_BODY.replace(
                    "@@RESULT_PATH@@", "$state_root/cleanup-result.json"
                ),
                True,
            ),
        ],
    )
    em.edge("PreTerminalCleanup", "Complete")

    em.node(
        "Complete",
        [
            ("shape", "parallelogram", False),
            ("label", "Complete", True),
            ("tool_command", 'printf \'{"terminal.status": "COMPLETE"}\'', True),
            ("parse_json", "true", True),
        ],
    )
    em.edge("Complete", "CompleteCarrier")

    em.node(
        "Residuals",
        [
            ("shape", "parallelogram", False),
            ("label", "Residuals (named, evidence-backed)", True),
            ("tool_command", 'printf \'{"terminal.status": "RESIDUALS_READY"}\'', True),
            ("parse_json", "true", True),
        ],
    )
    em.edge("Residuals", "ResidualsCleanup")

    em.node(
        "ResidualsCleanup",
        [
            ("shape", "parallelogram", False),
            ("label", "Pre-Terminal Cleanup (residuals path)", True),
            (
                "tool_command",
                _CLEANUP_BODY.replace(
                    "@@RESULT_PATH@@", "$state_root/cleanup-result-residuals.json"
                ),
                True,
            ),
        ],
    )
    em.edge("ResidualsCleanup", "ResidualsCarrier")

    em.node(
        "CompleteCarrier",
        [
            ("shape", "parallelogram", False),
            ("label", "CompleteCarrier", True),
            ("tool_command", "printf 'COMPLETE'", True),
        ],
    )
    em.edge("CompleteCarrier", "Exit")
    em.node(
        "ResidualsCarrier",
        [
            ("shape", "parallelogram", False),
            ("label", "ResidualsCarrier", True),
            ("tool_command", "printf 'RESIDUALS_READY'", True),
        ],
    )
    em.edge("ResidualsCarrier", "Exit")
    em.node(
        "InfraCarrier",
        [
            ("shape", "parallelogram", False),
            ("label", "InfraCarrier", True),
            ("tool_command", "printf 'INFRA_FAILURE'", True),
        ],
    )
    em.edge("InfraCarrier", "Exit")
    em.node(
        "AbortedCarrier",
        [
            ("shape", "parallelogram", False),
            ("label", "AbortedCarrier", True),
            ("tool_command", "printf 'ABORTED'", True),
        ],
    )
    em.edge("AbortedCarrier", "Exit")

    em.line("}")
    return em.render()


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _render_launch(template: str, lane, plan: Plan) -> str:
    return (
        template.replace("@@LANE@@", lane.lane_id)
        .replace("@@BRANCH@@", lane.branch)
        .replace("@@CHILD_DOT@@", _basename(lane.child_dot))
        .replace("@@MARKER_FILE@@", lane.marker_file)
        .replace("@@MARKER_CONTENT@@", lane.marker_content)
        .replace("@@SEEDED@@", "true" if lane.seeded_failure else "false")
        .replace("@@MAX_ATTEMPTS@@", str(plan.max_attempts))
    )


def _render_classify(lane_ids: list[str]) -> str:
    body = _CLASSIFY_BODY_HEAD
    assigns = []
    var_names = []
    for idx, lane_id in enumerate(lane_ids):
        var = f"r{idx}"
        var_names.append(var)
        assigns.append(f'{var} = classify("{lane_id}")')
    body += "\n".join(assigns) + "\n"
    body += 'print(",".join([' + ", ".join(var_names) + "]))\n"
    body += "PYEOF"
    return body
