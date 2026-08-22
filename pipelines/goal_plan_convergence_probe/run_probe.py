"""Run source-backed parse, lint, and one fresh convergence probe.

The harness captures exact argv/cwd/exit-code evidence after each subprocess
exits. It reads the parent verifier's already-written token into evidence.json;
it never prints or creates that token itself.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from scripts.probe_common import (
    ARTIFACTS_DIR,
    ATTEMPT_STATE_PATH,
    CANDIDATE_PATH,
    CURRENT_FEEDBACK_PATH,
    PARENT_EVIDENCE_PATH,
    PIPELINE_DIR,
    STATE_DIR,
    TERMINAL_PATH,
    VERIFIER_HISTORY_PATH,
    VERIFIER_PATH,
    atomic_write_json,
    atomic_write_text,
    read_json,
    relative_path,
    sha256_file,
)

SOURCE_BASE = Path(
    os.environ.get(
        "ATTRACTOR_SOURCE_BASE",
        "/home/ken/.amplifier/cache/"
        "amplifier-bundle-attractor-10534381a6383d20/modules",
    )
)
SOURCE_PYTHON = Path(
    os.environ.get(
        "ATTRACTOR_SOURCE_PYTHON",
        "/home/ken/.local/share/uv/tools/amplifier/bin/python",
    )
)
DOT_PATH = PIPELINE_DIR / "goal_plan_convergence_probe.dot"
EVIDENCE_PATH = PIPELINE_DIR / "evidence.json"
COMMAND_LOG_DIR = ARTIFACTS_DIR / "commands"
ATTRACTOR_LOG_DIR = ARTIFACTS_DIR / "attractor"

PARSE_PROGRAM = """\
import json
import sys
from pathlib import Path
from amplifier_module_loop_pipeline.dot_parser import parse_dot

path = Path(sys.argv[1])
graph = parse_dot(path.read_text(encoding="utf-8"))
print(json.dumps({
    "parse": "PASS",
    "error_diagnostics": 0,
    "node_count": len(graph.nodes),
    "edge_count": len(graph.edges),
}, sort_keys=True))
"""


def _source_env() -> dict[str, str]:
    env = os.environ.copy()
    source_paths = [
        SOURCE_BASE / "pipeline-runner",
        SOURCE_BASE / "loop-pipeline",
        SOURCE_BASE / "unified-llm-client",
        SOURCE_BASE / "remote-source",
    ]
    env["PYTHONPATH"] = ":".join(str(path) for path in source_paths)
    return env


def _run_command(name: str, argv: list[str], env: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        cwd=PIPELINE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout_path = COMMAND_LOG_DIR / f"{name}.stdout.log"
    stderr_path = COMMAND_LOG_DIR / f"{name}.stderr.log"
    atomic_write_text(stdout_path, completed.stdout)
    atomic_write_text(stderr_path, completed.stderr)
    return {
        "name": name,
        "argv": argv,
        "cwd": str(PIPELINE_DIR),
        "environment": {
            "PYTHONPATH": env["PYTHONPATH"],
        },
        "exit_code": completed.returncode,
        "stdout_path": relative_path(stdout_path),
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_path": relative_path(stderr_path),
        "stderr_sha256": sha256_file(stderr_path),
    }


def _optional_json(path: Path) -> dict[str, Any]:
    return read_json(path) if path.exists() else {}


def _raw_output_record(path: Path) -> dict[str, Any]:
    return {
        "path": relative_path(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def _collect_evidence(commands: list[dict[str, Any]]) -> dict[str, Any]:
    state = _optional_json(ATTEMPT_STATE_PATH)
    history = _optional_json(VERIFIER_HISTORY_PATH)
    feedback = _optional_json(CURRENT_FEEDBACK_PATH)
    parent = _optional_json(PARENT_EVIDENCE_PATH)
    terminal = _optional_json(TERMINAL_PATH)

    records_value = history.get("records", [])
    records = records_value if isinstance(records_value, list) else []
    first_failure = records[0] if records else None
    passing_records = [
        record
        for record in records
        if isinstance(record, dict) and record.get("verdict") == "PASS"
    ]
    attempts_value = state.get("attempts", [])
    attempts = attempts_value if isinstance(attempts_value, list) else []
    initial_hash = state.get("initial_candidate_sha256")
    final_hash = sha256_file(CANDIDATE_PATH) if CANDIDATE_PATH.exists() else None
    terminal_token = parent.get("terminal_token")

    raw_paths = [
        PIPELINE_DIR / command[key]
        for command in commands
        for key in ("stdout_path", "stderr_path")
    ]
    raw_paths.extend(
        PIPELINE_DIR / str(record["raw_log_path"])
        for record in records
        if isinstance(record, dict) and record.get("raw_log_path")
    )
    parent_log = parent.get("parent_raw_log_path")
    if parent_log:
        raw_paths.append(PIPELINE_DIR / str(parent_log))
    raw_outputs = [_raw_output_record(path) for path in raw_paths if path.is_file()]

    parent_stage_outputs = sorted(ATTRACTOR_LOG_DIR.glob("**/parent_verify/output.txt"))
    raw_outputs.extend(_raw_output_record(path) for path in parent_stage_outputs)

    command_by_name = {command["name"]: command for command in commands}
    parse_ok = command_by_name.get("parse", {}).get("exit_code") == 0
    lint_ok = command_by_name.get("lint", {}).get("exit_code") == 0
    run_ok = command_by_name.get("run", {}).get("exit_code") == 0
    first_failure_ok = (
        isinstance(first_failure, dict)
        and first_failure.get("attempt") == 1
        and first_failure.get("verdict") == "FAIL"
        and first_failure.get("child_exit_code") == 1
        and first_failure.get("external_verifier_process") is True
    )
    correction_ok = (
        2 <= int(state.get("attempt_count", 0)) <= 3
        and initial_hash is not None
        and final_hash is not None
        and initial_hash != final_hash
        and bool(feedback)
        and bool(passing_records)
    )
    parent_ok = (
        parent.get("result") == "PASS"
        and bool(terminal_token)
        and parent.get("final_candidate_sha256") == final_hash
    )

    items = {
        "PROBE_GRAPH": {
            "status": "PASS" if parse_ok and lint_ok else "FAIL_PARSE_OR_LINT",
        },
        "INITIAL_FAILURE": {
            "status": "PASS" if first_failure_ok else "FAIL_NO_EXTERNAL_FIRST_FAILURE",
        },
        "FEEDBACK_AND_CORRECTION": {
            "status": "PASS" if correction_ok else "FAIL_NO_BOUNDED_CORRECTION",
        },
        "PARENT_REVERIFY": {
            "status": "PASS" if parent_ok else "FAIL_PARENT_REVERIFY",
        },
        "DURABLE_EVIDENCE": {
            "status": "PASS"
            if run_ok and bool(raw_outputs)
            else "FAIL_INCOMPLETE_EVIDENCE",
        },
        "DURABILITY": {
            "status": "BLOCKED_PENDING_FINISH_STAGE_DONE_JSON",
        },
    }

    return {
        "schema_version": "goal-plan.convergence-probe-evidence/v1",
        "cwd": str(PIPELINE_DIR),
        "source_backed_cli": {
            "base": str(SOURCE_BASE),
            "python": str(SOURCE_PYTHON),
            "pythonpath": _source_env()["PYTHONPATH"],
        },
        "commands": commands,
        "outer_exit_codes": {
            command["name"]: command["exit_code"] for command in commands
        },
        "run_log_path": relative_path(ATTRACTOR_LOG_DIR),
        "raw_outputs": raw_outputs,
        "attempt_count": state.get("attempt_count"),
        "max_attempts": state.get("max_attempts"),
        "attempts": attempts,
        "first_failure": first_failure,
        "feedback": feedback,
        "initial_candidate_sha256": initial_hash,
        "final_candidate_sha256": final_hash,
        "candidate_hashes_by_attempt": [
            {
                "attempt": record.get("attempt"),
                "sha256": record.get("candidate_sha256"),
                "verdict": record.get("verdict"),
            }
            for record in records
            if isinstance(record, dict)
        ],
        "verifier_results": records,
        "verifier_definition": {
            "path": relative_path(VERIFIER_PATH),
            "sha256_initial": state.get("verifier_sha256_initial"),
            "sha256_after_worker": sha256_file(VERIFIER_PATH),
            "matches": (
                state.get("verifier_sha256_initial") == sha256_file(VERIFIER_PATH)
            ),
        },
        "parent_verification": parent,
        "terminal": terminal,
        "terminal_token": terminal_token,
        "items": items,
        "suite": {
            "parse_exit_code": command_by_name.get("parse", {}).get("exit_code"),
            "lint_exit_code": command_by_name.get("lint", {}).get("exit_code"),
            "run_exit_code": command_by_name.get("run", {}).get("exit_code"),
            "all_required_passed": (
                parse_ok
                and lint_ok
                and run_ok
                and first_failure_ok
                and correction_ok
                and parent_ok
            ),
        },
    }


def main() -> int:
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)
    shutil.rmtree(STATE_DIR, ignore_errors=True)
    CANDIDATE_PATH.unlink(missing_ok=True)
    EVIDENCE_PATH.unlink(missing_ok=True)
    COMMAND_LOG_DIR.mkdir(parents=True, exist_ok=True)

    env = _source_env()
    parse_argv = [str(SOURCE_PYTHON), "-c", PARSE_PROGRAM, str(DOT_PATH)]
    lint_argv = [
        str(SOURCE_PYTHON),
        "-m",
        "amplifier_module_pipeline_runner.cli",
        "lint",
        str(DOT_PATH),
    ]
    run_argv = [
        str(SOURCE_PYTHON),
        "-m",
        "amplifier_module_pipeline_runner.cli",
        "run",
        str(DOT_PATH),
        "--provider",
        "anthropic",
        "--logs-root",
        str(ATTRACTOR_LOG_DIR),
        "--cwd",
        str(PIPELINE_DIR),
    ]

    commands = [
        _run_command("parse", parse_argv, env),
        _run_command("lint", lint_argv, env),
    ]
    if all(command["exit_code"] == 0 for command in commands):
        commands.append(_run_command("run", run_argv, env))

    evidence = _collect_evidence(commands)
    atomic_write_json(EVIDENCE_PATH, evidence)

    if evidence["suite"]["all_required_passed"]:
        print("HARNESS_RESULT:PASS")
        print(f"evidence={EVIDENCE_PATH}")
        return 0

    print("HARNESS_RESULT:FAIL")
    print(f"evidence={EVIDENCE_PATH}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
