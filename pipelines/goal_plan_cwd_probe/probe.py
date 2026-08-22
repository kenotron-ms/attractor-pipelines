#!/usr/bin/env python3
"""Run and independently verify the concurrent box-session CWD probe."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parents[1]
ENTRY_DOT = PIPELINE_DIR / "goal_plan_cwd_probe.dot"
LANE_DOT = PIPELINE_DIR / "subgraphs" / "lane_probe.dot"
EVIDENCE_PATH = PIPELINE_DIR / "evidence.json"

SOURCE_BASE = Path(
    "/home/ken/.amplifier/cache/amplifier-bundle-attractor-10534381a6383d20/modules"
)
SOURCE_PYTHON = Path("/home/ken/.local/share/uv/tools/amplifier/bin/python")
SOURCE_PATHS = (
    SOURCE_BASE / "pipeline-runner",
    SOURCE_BASE / "loop-pipeline",
    SOURCE_BASE / "unified-llm-client",
    SOURCE_BASE / "remote-source",
)
SOURCE_PYTHONPATH = ":".join(str(path) for path in SOURCE_PATHS)
RUNNER_MODULE = "amplifier_module_pipeline_runner.cli"

SCHEMA_VERSION = "goal-plan.cwd-probe/v1"
STATE_SCHEMA_VERSION = "goal-plan.cwd-probe-state/v1"
LANES = ("lane-a", "lane-b")
MAX_INLINE_CAPTURE_BYTES = 32_768
PWD_PATTERN = re.compile(r"(?<![A-Za-z0-9_])pwd(?:\s+-P)?(?![A-Za-z0-9_])")


def utc_now() -> str:
    """Return an RFC 3339 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write_json(path: Path, value: Any) -> None:
    """Write JSON through a same-directory temporary file and atomic rename."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object at {path}")
    return value


def source_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = SOURCE_PYTHONPATH
    return env


def run_process(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """Run a command and retain exact argv, output, and exit status."""

    try:
        completed = subprocess.run(
            list(argv),
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        timeout_stdout = (
            exc.stdout.decode(errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        timeout_stderr = (
            exc.stderr.decode(errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        return {
            "argv": list(argv),
            "command": shlex.join(list(argv)),
            "cwd": str(cwd.resolve()) if cwd else None,
            "exit_code": 124,
            "stdout": timeout_stdout,
            "stderr": timeout_stderr + f"\nTimed out after {timeout}s.\n",
            "timed_out": True,
        }
    return {
        "argv": list(argv),
        "command": shlex.join(list(argv)),
        "cwd": str(cwd.resolve()) if cwd else None,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "timed_out": False,
    }


def checked(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    result = run_process(argv, cwd=cwd, timeout=timeout)
    if result["exit_code"] != 0:
        raise RuntimeError(
            f"Command failed ({result['exit_code']}): {result['command']}\n"
            f"stdout:\n{result['stdout']}\nstderr:\n{result['stderr']}"
        )
    return result


def git_output(path: Path, *args: str) -> str:
    result = checked(("git", "-C", str(path), *args))
    return str(result["stdout"]).strip()


def canonical(path: Path) -> str:
    return str(path.resolve(strict=True))


def artifact_contract(lane: str) -> dict[str, str]:
    suffix = lane.replace("-", "_")
    return {
        "pwd_artifact": f"box_pwd_{suffix}.txt",
        "sentinel_artifact": f"sentinel_{suffix}.txt",
        "sentinel_payload": f"cwd-probe:{lane}",
    }


def prepare(args: argparse.Namespace) -> int:
    """Create one temporary git root and two distinct lane worktrees."""

    run_root = Path(args.run_root).resolve()
    state_path = Path(args.state).resolve()
    root = run_root / "root"
    root.mkdir(parents=True, exist_ok=True)

    if state_path.exists():
        raise RuntimeError(f"Refusing to reuse existing probe state: {state_path}")
    if any(root.iterdir()):
        raise RuntimeError(f"Fresh CLI root is not empty before prepare: {root}")

    commands: list[dict[str, Any]] = []
    commands.append(checked(("git", "init", "--initial-branch=main", "."), cwd=root))
    commands.append(checked(("git", "config", "user.name", "CWD Probe"), cwd=root))
    commands.append(
        checked(("git", "config", "user.email", "cwd-probe@example.invalid"), cwd=root)
    )
    (root / "baseline.txt").write_text("cwd probe baseline\n", encoding="utf-8")
    commands.append(checked(("git", "add", "baseline.txt"), cwd=root))
    commands.append(
        checked(
            (
                "git",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-m",
                "test: initialize cwd probe",
            ),
            cwd=root,
        )
    )
    base_commit = git_output(root, "rev-parse", "HEAD")

    lane_records: dict[str, dict[str, Any]] = {}
    for lane in LANES:
        target = run_root / lane
        commands.append(
            checked(
                (
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    f"probe/{lane}",
                    str(target),
                    base_commit,
                ),
                cwd=root,
            )
        )
        lane_records[lane] = {
            "branch": f"probe/{lane}",
            "target_realpath": canonical(target),
            "git_common_dir": git_output(
                target, "rev-parse", "--path-format=absolute", "--git-common-dir"
            ),
            **artifact_contract(lane),
        }

    root_realpath = canonical(root)
    target_realpaths = [lane_records[lane]["target_realpath"] for lane in LANES]
    state: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSION,
        "prepared_at": utc_now(),
        "prepared_at_ns": int(datetime.now(timezone.utc).timestamp() * 1_000_000_000),
        "prepared_phase": "before-component-fan-out",
        "prepare_process_cwd": canonical(Path.cwd()),
        "run_root_realpath": canonical(run_root),
        "root_realpath": root_realpath,
        "root_git_common_dir": git_output(
            root, "rev-parse", "--path-format=absolute", "--git-common-dir"
        ),
        "base_commit": base_commit,
        "lanes": lane_records,
        "distinct_targets": len(set(target_realpaths)) == len(LANES)
        and root_realpath not in target_realpaths,
        "worktree_list_porcelain": git_output(root, "worktree", "list", "--porcelain"),
        "initial_mutation_scans": {
            "root": git_output(
                root, "status", "--porcelain=v1", "--untracked-files=all"
            ),
            **{
                lane: git_output(
                    Path(lane_records[lane]["target_realpath"]),
                    "status",
                    "--porcelain=v1",
                    "--untracked-files=all",
                )
                for lane in LANES
            },
        },
        "prepare_commands": commands,
    }
    atomic_write_json(state_path, state)

    print(
        json.dumps(
            {
                "probe_prepared": True,
                "prepared_at": state["prepared_at"],
                "root_realpath": root_realpath,
                "lane_a_target": lane_records["lane-a"]["target_realpath"],
                "lane_b_target": lane_records["lane-b"]["target_realpath"],
                "distinct_targets": state["distinct_targets"],
            },
            sort_keys=True,
        )
    )
    return 0


def control_path(state: dict[str, Any], scope: str, phase: str) -> Path:
    run_root = Path(str(state["run_root_realpath"]))
    safe_scope = scope.replace("/", "_")
    safe_phase = phase.replace("/", "_")
    return run_root / "controls" / f"{safe_scope}-{safe_phase}.json"


def write_control(
    state: dict[str, Any],
    *,
    scope: str,
    phase: str,
    assigned_target: str | None,
) -> Path:
    path = control_path(state, scope, phase)
    atomic_write_json(
        path,
        {
            "schema_version": STATE_SCHEMA_VERSION,
            "scope": scope,
            "phase": phase,
            "recorded_at": utc_now(),
            "cwd_realpath": canonical(Path.cwd()),
            "assigned_target": assigned_target,
        },
    )
    return path


def bind_target(args: argparse.Namespace) -> int:
    """Record inherited tool CWD and bind this cloned branch to its lane target."""

    state = load_json(Path(args.state).resolve())
    lane = str(args.lane)
    if lane not in LANES:
        raise ValueError(f"Unknown lane {lane!r}; expected one of {LANES}")
    lane_record = state["lanes"][lane]
    target = str(lane_record["target_realpath"])
    write_control(
        state,
        scope=lane,
        phase="bind",
        assigned_target=target,
    )
    print(
        json.dumps(
            {
                "context.target_dir": target,
                "pwd_artifact": lane_record["pwd_artifact"],
                "sentinel_artifact": lane_record["sentinel_artifact"],
                "sentinel_payload": lane_record["sentinel_payload"],
            },
            sort_keys=True,
        )
    )
    return 0


def record_control(args: argparse.Namespace) -> int:
    state = load_json(Path(args.state).resolve())
    scope = str(args.scope)
    assigned_target: str | None
    if scope in LANES:
        assigned_target = str(state["lanes"][scope]["target_realpath"])
    elif scope == "parent":
        assigned_target = str(state["root_realpath"])
    else:
        raise ValueError(f"Unknown control scope: {scope}")
    path = write_control(
        state,
        scope=scope,
        phase=str(args.phase),
        assigned_target=assigned_target,
    )
    print(f"control-recorded:{path.name}")
    return 0


def diagnostics_for(path: Path) -> dict[str, Any]:
    for source_path in reversed(SOURCE_PATHS):
        source = str(source_path)
        if source not in sys.path:
            sys.path.insert(0, source)

    dot_parser = importlib.import_module("amplifier_module_loop_pipeline.dot_parser")
    validation = importlib.import_module("amplifier_module_loop_pipeline.validation")

    graph = dot_parser.parse_dot(path.read_text(encoding="utf-8"))
    graph.source_dir = str(path.parent)
    diagnostics = validation.validate(graph)
    serialized = [
        {
            "rule": diagnostic.rule,
            "severity": diagnostic.severity,
            "message": diagnostic.message,
            "node_id": diagnostic.node_id,
            "edge": list(diagnostic.edge) if diagnostic.edge else None,
            "fix": diagnostic.fix,
        }
        for diagnostic in diagnostics
    ]
    return {
        "file": str(path),
        "diagnostics": serialized,
        "diagnostic_count": len(serialized),
        "error_count": sum(1 for item in serialized if item["severity"] == "ERROR"),
    }


def static_checks(run_root: Path) -> dict[str, Any]:
    parse_results = [diagnostics_for(path) for path in (ENTRY_DOT, LANE_DOT)]

    lint_results = []
    for path in (ENTRY_DOT, LANE_DOT):
        result = run_process(
            (
                str(SOURCE_PYTHON),
                "-m",
                RUNNER_MODULE,
                "lint",
                str(path),
            ),
            cwd=REPO_ROOT,
            env=source_env(),
            timeout=120,
        )
        result["source_prefix"] = {
            "BASE": str(SOURCE_BASE),
            "PYTHONPATH": SOURCE_PYTHONPATH,
        }
        lint_results.append(result)

    compile_env = source_env()
    compile_env["PYTHONPYCACHEPREFIX"] = str(run_root / "pycache")
    compile_result = run_process(
        (str(SOURCE_PYTHON), "-m", "py_compile", str(Path(__file__).resolve())),
        cwd=REPO_ROOT,
        env=compile_env,
        timeout=120,
    )
    return {
        "python_compile": compile_result,
        "parse": parse_results,
        "lint": lint_results,
        "pass": (
            compile_result["exit_code"] == 0
            and all(result["error_count"] == 0 for result in parse_results)
            and all(result["exit_code"] == 0 for result in lint_results)
        ),
    }


def bounded_capture(path: Path, content: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    encoded = content.encode("utf-8")
    record: dict[str, Any] = {
        "path": str(path),
        "bytes": len(encoded),
        "sha256": sha256_bytes(encoded),
        "truncated": len(encoded) > MAX_INLINE_CAPTURE_BYTES,
    }
    if len(encoded) <= MAX_INLINE_CAPTURE_BYTES:
        record["inline"] = content
    else:
        half = MAX_INLINE_CAPTURE_BYTES // 2
        record["head"] = encoded[:half].decode("utf-8", errors="replace")
        record["tail"] = encoded[-half:].decode("utf-8", errors="replace")
    return record


def mutation_scan(path: Path) -> dict[str, Any]:
    result = run_process(
        (
            "git",
            "-C",
            str(path),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ),
        timeout=120,
    )
    lines = [line for line in str(result["stdout"]).splitlines() if line]
    return {
        **result,
        "realpath": canonical(path),
        "entries": lines,
        "paths": [line[3:] if len(line) >= 4 else line for line in lines],
        "clean": result["exit_code"] == 0 and not lines,
    }


def artifact_observations(state: dict[str, Any]) -> dict[str, Any]:
    scopes = {
        "root": Path(str(state["root_realpath"])),
        **{lane: Path(str(state["lanes"][lane]["target_realpath"])) for lane in LANES},
    }
    observations: dict[str, Any] = {}
    for lane in LANES:
        lane_record = state["lanes"][lane]
        lane_observation: dict[str, Any] = {}
        for kind in ("pwd_artifact", "sentinel_artifact"):
            filename = str(lane_record[kind])
            locations = []
            for scope, directory in scopes.items():
                candidate = directory / filename
                if candidate.is_file():
                    raw = candidate.read_bytes()
                    locations.append(
                        {
                            "scope": scope,
                            "path": str(candidate),
                            "realpath": canonical(candidate),
                            "bytes": len(raw),
                            "sha256": sha256_bytes(raw),
                            "content": raw.decode("utf-8", errors="replace"),
                        }
                    )
            lane_observation[kind] = {
                "filename": filename,
                "expected_scope": lane,
                "expected_path": str(scopes[lane] / filename),
                "locations": locations,
            }
        observations[lane] = lane_observation
    return observations


def read_control_observations(state: dict[str, Any]) -> dict[str, Any]:
    expected = []
    for lane in LANES:
        expected.extend(((lane, "bind"), (lane, "before-box"), (lane, "after-box")))
    expected.append(("parent", "after-fan-in"))

    controls: dict[str, Any] = {}
    for scope, phase in expected:
        path = control_path(state, scope, phase)
        key = f"{scope}:{phase}"
        controls[key] = {
            "path": str(path),
            "exists": path.is_file(),
            "record": load_json(path) if path.is_file() else None,
        }
    return controls


def session_observation(
    logs_root: Path,
    lane: str,
    lane_record: dict[str, Any],
) -> dict[str, Any]:
    folder_name = "LaneA" if lane == "lane-a" else "LaneB"
    stage_dir = logs_root / f"subgraph_{folder_name}" / "BoxProbe"
    status_path = stage_dir / "status.json"
    prompt_path = stage_dir / "prompt.md"
    status = load_json(status_path) if status_path.is_file() else {}
    session_id = status.get("session_id")
    events_path = (
        stage_dir / "sessions" / str(session_id) / "events.jsonl"
        if session_id
        else None
    )
    records = []
    invalid_lines = []
    if events_path and events_path.is_file():
        for number, line in enumerate(
            events_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines.append(number)
                continue
            if isinstance(value, dict):
                records.append(value)

    bash_commands = []
    for record in records:
        if record.get("event") != "tool:pre":
            continue
        data = record.get("data")
        if not isinstance(data, dict) or data.get("tool_name") != "bash":
            continue
        tool_input = data.get("tool_input")
        if isinstance(tool_input, dict) and isinstance(tool_input.get("command"), str):
            bash_commands.append(tool_input["command"])

    timestamps = [
        str(record["timestamp"])
        for record in records
        if isinstance(record.get("timestamp"), str)
    ]
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    target = str(lane_record["target_realpath"])
    pwd_artifact = str(lane_record["pwd_artifact"])
    sentinel_artifact = str(lane_record["sentinel_artifact"])
    return {
        "lane": lane,
        "stage_dir": str(stage_dir),
        "status_path": str(status_path),
        "status_exists": status_path.is_file(),
        "status": status.get("outcome") or status.get("status"),
        "session_id": session_id,
        "prompt_path": str(prompt_path),
        "prompt_exists": prompt_path.is_file(),
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")) if prompt else None,
        "assigned_target_in_prompt": target in prompt,
        "events_path": str(events_path) if events_path else None,
        "events_exist": bool(events_path and events_path.is_file()),
        "event_count": len(records),
        "invalid_event_lines": invalid_lines,
        "first_event_at": timestamps[0] if timestamps else None,
        "last_event_at": timestamps[-1] if timestamps else None,
        "bash_commands": bash_commands,
        "pwd_command_observed": any(
            PWD_PATTERN.search(command) for command in bash_commands
        ),
        "relative_artifact_write_observed": any(
            pwd_artifact in command
            and sentinel_artifact in command
            and target not in command
            for command in bash_commands
        ),
        "directory_change_observed": any(
            re.search(
                r"(?<![A-Za-z0-9_])(?:cd|chdir|pushd|popd)(?![A-Za-z0-9_])", command
            )
            for command in bash_commands
        ),
    }


def concurrency_observation(
    sessions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Prove distinct session identities and overlapping observed intervals."""

    session_ids = [sessions[lane]["session_id"] for lane in LANES]
    intervals: dict[str, dict[str, str | None]] = {
        lane: {
            "start": sessions[lane]["first_event_at"],
            "end": sessions[lane]["last_event_at"],
        }
        for lane in LANES
    }

    parsed_intervals = []
    for lane in LANES:
        start = intervals[lane]["start"]
        end = intervals[lane]["end"]
        if not start or not end:
            parsed_intervals = []
            break
        parsed_intervals.append(
            (
                datetime.fromisoformat(start.replace("Z", "+00:00")),
                datetime.fromisoformat(end.replace("Z", "+00:00")),
            )
        )

    overlap = bool(parsed_intervals) and max(
        interval[0] for interval in parsed_intervals
    ) <= min(interval[1] for interval in parsed_intervals)
    distinct_session_ids = all(
        isinstance(session_id, str) and session_id for session_id in session_ids
    ) and len(set(session_ids)) == len(LANES)
    return {
        "structural_fan_out": {
            "shape": "component",
            "folder_nodes": ["LaneA", "LaneB"],
            "join_shape": "tripleoctagon",
            "max_parallel": 2,
        },
        "session_ids": session_ids,
        "distinct_session_ids": distinct_session_ids,
        "intervals": intervals,
        "intervals_overlap": overlap,
        "pass": distinct_session_ids and overlap,
    }


def prepared_before_sessions(
    state_path: Path,
    sessions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    state_mtime_ns = state_path.stat().st_mtime_ns
    comparisons = {}
    for lane, session in sessions.items():
        status_path = Path(str(session["status_path"]))
        status_mtime_ns = (
            status_path.stat().st_mtime_ns if status_path.is_file() else None
        )
        comparisons[lane] = {
            "state_mtime_ns": state_mtime_ns,
            "session_status_mtime_ns": status_mtime_ns,
            "prepared_before_status": (
                status_mtime_ns is not None and state_mtime_ns < status_mtime_ns
            ),
        }
    return {
        "method": "state-file mtime is strictly earlier than each box status.json mtime",
        "comparisons": comparisons,
        "pass": all(
            comparison["prepared_before_status"] for comparison in comparisons.values()
        ),
    }


def expected_control_cwd(state: dict[str, Any], scope: str, phase: str) -> str:
    if scope == "parent" or phase == "bind":
        return str(state["root_realpath"])
    return str(state["lanes"][scope]["target_realpath"])


def controls_pass(state: dict[str, Any], controls: dict[str, Any]) -> bool:
    for key, observation in controls.items():
        if not observation["exists"] or not isinstance(observation["record"], dict):
            return False
        scope, phase = key.split(":", maxsplit=1)
        if observation["record"].get("cwd_realpath") != expected_control_cwd(
            state, scope, phase
        ):
            return False
    return True


def only_scope(
    artifacts: dict[str, Any],
    lane: str,
    kind: str,
    scope: str,
) -> bool:
    locations = artifacts[lane][kind]["locations"]
    return len(locations) == 1 and locations[0]["scope"] == scope


def artifact_content(
    artifacts: dict[str, Any],
    lane: str,
    kind: str,
) -> str | None:
    locations = artifacts[lane][kind]["locations"]
    return locations[0]["content"].strip() if len(locations) == 1 else None


def classify(
    *,
    static: dict[str, Any],
    cli_exit_code: int,
    state: dict[str, Any],
    prep_order: dict[str, Any],
    concurrency: dict[str, Any],
    sessions: dict[str, dict[str, Any]],
    controls: dict[str, Any],
    artifacts: dict[str, Any],
    mutations: dict[str, dict[str, Any]],
) -> tuple[str, str | None]:
    if not static["pass"]:
        return "FAIL-probe-graph", "Static parse, lint, or Python compile failed."
    if not state.get("distinct_targets"):
        return "FAIL-distinct-targets", "Prepared target realpaths were not distinct."
    if not prep_order["pass"]:
        return (
            "FAIL-prepare-order",
            "Could not prove targets were recorded before both box sessions completed.",
        )
    if cli_exit_code != 0:
        return "FAIL-cli-run", f"Source-backed Attractor CLI exited {cli_exit_code}."
    if not concurrency["pass"]:
        return (
            "FAIL-concurrency-unobserved",
            "Distinct overlapping box-session identities were not observed.",
        )
    if not controls_pass(state, controls):
        return (
            "FAIL-tool-control-cwd",
            "One or more deterministic tool CWD controls were missing or unexpected.",
        )
    if not all(session["status"] == "success" for session in sessions.values()):
        return (
            "FAIL-box-session-status",
            "One or more box sessions did not report success.",
        )
    if not all(session["pwd_command_observed"] for session in sessions.values()):
        return (
            "FAIL-pwd-command-unobserved",
            "A box worker event stream did not independently show a bash pwd command.",
        )
    if not all(
        session["relative_artifact_write_observed"]
        and not session["directory_change_observed"]
        and not session["assigned_target_in_prompt"]
        for session in sessions.values()
    ):
        return (
            "FAIL-box-command-contract",
            "A box command did not prove relative writes without a directory change, "
            + "or its assigned absolute target leaked into the prompt.",
        )

    strict_isolation = True
    for lane in LANES:
        lane_record = state["lanes"][lane]
        strict_isolation = strict_isolation and all(
            (
                only_scope(artifacts, lane, "pwd_artifact", lane),
                only_scope(artifacts, lane, "sentinel_artifact", lane),
                artifact_content(artifacts, lane, "pwd_artifact")
                == lane_record["target_realpath"],
                artifact_content(artifacts, lane, "sentinel_artifact")
                == lane_record["sentinel_payload"],
                set(mutations[lane]["paths"])
                == {
                    lane_record["pwd_artifact"],
                    lane_record["sentinel_artifact"],
                },
            )
        )
    strict_isolation = strict_isolation and mutations["root"]["clean"]
    if strict_isolation:
        return "PASS", None

    root_realpath = str(state["root_realpath"])
    runner_global_root = True
    for lane in LANES:
        lane_record = state["lanes"][lane]
        runner_global_root = runner_global_root and all(
            (
                only_scope(artifacts, lane, "pwd_artifact", "root"),
                only_scope(artifacts, lane, "sentinel_artifact", "root"),
                artifact_content(artifacts, lane, "pwd_artifact") == root_realpath,
                artifact_content(artifacts, lane, "sentinel_artifact")
                == lane_record["sentinel_payload"],
                mutations[lane]["clean"],
            )
        )
    if runner_global_root:
        return (
            "BLOCKED-engine-session-cwd",
            (
                "Both independent box sessions ran at the runner-global CLI root "
                "while deterministic tool controls ran at their assigned lane targets."
            ),
        )

    evidence_counts = [
        len(artifacts[lane]["pwd_artifact"]["locations"])
        + len(artifacts[lane]["sentinel_artifact"]["locations"])
        for lane in LANES
    ]
    if any(count < 2 for count in evidence_counts):
        return (
            "FAIL-missing-box-evidence",
            "One or more required box artifacts are missing.",
        )

    observed_pwd = [artifact_content(artifacts, lane, "pwd_artifact") for lane in LANES]
    if observed_pwd[0] != observed_pwd[1]:
        return (
            "FAIL-asymmetric-session-cwd",
            f"Lane box CWD observations differ asymmetrically: {observed_pwd}.",
        )
    return (
        "FAIL-unclassified-session-cwd",
        (
            "Observed paths did not satisfy isolation or the known global-root "
            f"pattern: {observed_pwd}."
        ),
    )


def shell_run_command(argv: Sequence[str], cwd: Path) -> str:
    return (
        f"cd {shlex.quote(str(cwd))} && "
        f"BASE={shlex.quote(str(SOURCE_BASE))}; "
        f"PYTHONPATH={shlex.quote(SOURCE_PYTHONPATH)} "
        f"{shlex.join(list(argv))}"
    )


def verify(_: argparse.Namespace) -> int:
    """Run a fresh real CLI probe and atomically publish parent evidence."""

    invocation_cwd = Path.cwd().resolve()
    if invocation_cwd != REPO_ROOT:
        raise RuntimeError(
            f"Run verify from repository root {REPO_ROOT}; observed {invocation_cwd}"
        )

    run_root = Path(tempfile.mkdtemp(prefix="goal-plan-cwd-probe-")).resolve()
    cli_root = run_root / "root"
    cli_root.mkdir()
    state_path = run_root / "state.json"
    logs_root = run_root / "logs"

    static = static_checks(run_root)
    if not static["pass"]:
        evidence = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": utc_now(),
            "verdict": "FAIL-probe-graph",
            "invocation": {
                "argv": [str(Path(__file__).resolve()), "verify"],
                "cwd": str(invocation_cwd),
            },
            "run_root": str(run_root),
            "static_analysis": static,
            "blocker": "Static parse, lint, or Python compile failed.",
        }
        atomic_write_json(EVIDENCE_PATH, evidence)
        print("FAIL-probe-graph")
        return 1

    cli_argv = [
        str(SOURCE_PYTHON),
        "-m",
        RUNNER_MODULE,
        "run",
        str(ENTRY_DOT),
        "--provider",
        "anthropic",
        "--cwd",
        str(cli_root),
        "--logs-root",
        str(logs_root),
        "--param",
        f"probe_python={SOURCE_PYTHON}",
        "--param",
        f"probe_script={Path(__file__).resolve()}",
        "--param",
        f"probe_root={run_root}",
        "--param",
        f"probe_state={state_path}",
    ]
    cli_result = run_process(
        cli_argv,
        cwd=cli_root,
        env=source_env(),
        timeout=900,
    )
    stdout_record = bounded_capture(
        run_root / "cli.stdout.log", str(cli_result["stdout"])
    )
    stderr_record = bounded_capture(
        run_root / "cli.stderr.log", str(cli_result["stderr"])
    )

    if not state_path.is_file():
        evidence = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": utc_now(),
            "verdict": "FAIL-prepare-missing",
            "invocation": {
                "argv": [str(Path(__file__).resolve()), "verify"],
                "cwd": str(invocation_cwd),
            },
            "source_backed_cli": {
                "BASE": str(SOURCE_BASE),
                "PYTHONPATH": SOURCE_PYTHONPATH,
                "python": str(SOURCE_PYTHON),
                "module": RUNNER_MODULE,
                "command_argv": cli_argv,
                "command": shell_run_command(cli_argv, cli_root),
                "cwd": str(cli_root),
                "exit_code": cli_result["exit_code"],
                "stdout": stdout_record,
                "stderr": stderr_record,
            },
            "run_root": str(run_root),
            "static_analysis": static,
            "blocker": f"Prepare node did not create {state_path}.",
        }
        atomic_write_json(EVIDENCE_PATH, evidence)
        print("FAIL-prepare-missing")
        return 1

    state = load_json(state_path)
    sessions = {
        lane: session_observation(logs_root, lane, state["lanes"][lane])
        for lane in LANES
    }
    concurrency = concurrency_observation(sessions)
    controls = read_control_observations(state)
    artifacts = artifact_observations(state)
    mutations = {
        "root": mutation_scan(Path(str(state["root_realpath"]))),
        **{
            lane: mutation_scan(Path(str(state["lanes"][lane]["target_realpath"])))
            for lane in LANES
        },
    }
    prep_order = prepared_before_sessions(state_path, sessions)
    verdict, blocker = classify(
        static=static,
        cli_exit_code=int(cli_result["exit_code"]),
        state=state,
        prep_order=prep_order,
        concurrency=concurrency,
        sessions=sessions,
        controls=controls,
        artifacts=artifacts,
        mutations=mutations,
    )

    expected_paths = {
        "cli_root": state["root_realpath"],
        "lanes": {
            lane: {
                "target": state["lanes"][lane]["target_realpath"],
                "pwd_artifact": str(
                    Path(str(state["lanes"][lane]["target_realpath"]))
                    / str(state["lanes"][lane]["pwd_artifact"])
                ),
                "sentinel_artifact": str(
                    Path(str(state["lanes"][lane]["target_realpath"]))
                    / str(state["lanes"][lane]["sentinel_artifact"])
                ),
            }
            for lane in LANES
        },
    }
    observed_paths = {
        lane: {
            "pwd": artifact_content(artifacts, lane, "pwd_artifact"),
            "pwd_artifact_locations": artifacts[lane]["pwd_artifact"]["locations"],
            "sentinel_locations": artifacts[lane]["sentinel_artifact"]["locations"],
        }
        for lane in LANES
    }

    evidence = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "verdict": verdict,
        "blocker": (
            {"name": verdict, "detail": blocker}
            if verdict == "BLOCKED-engine-session-cwd"
            else blocker
        ),
        "invocation": {
            "argv": [str(Path(__file__).resolve()), "verify"],
            "cwd": str(invocation_cwd),
        },
        "source_backed_cli": {
            "BASE": str(SOURCE_BASE),
            "PYTHONPATH": SOURCE_PYTHONPATH,
            "python": str(SOURCE_PYTHON),
            "module": RUNNER_MODULE,
            "provider": "anthropic",
            "credential_presence": {
                "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY"))
            },
            "command_argv": cli_argv,
            "command": shell_run_command(cli_argv, cli_root),
            "cwd": str(cli_root),
            "exit_code": cli_result["exit_code"],
            "stdout": stdout_record,
            "stderr": stderr_record,
        },
        "probe_files": {
            "entry_dot": str(ENTRY_DOT),
            "lane_dot": str(LANE_DOT),
            "verifier": str(Path(__file__).resolve()),
            "evidence": str(EVIDENCE_PATH),
        },
        "static_analysis": static,
        "prepared": state,
        "prepared_before_sessions": prep_order,
        "concurrency": concurrency,
        "expected_paths": expected_paths,
        "observed_paths": observed_paths,
        "sessions": sessions,
        "tool_cwd_controls": controls,
        "artifact_scan": artifacts,
        "mutation_scans": mutations,
        "cleanup": {
            "performed": False,
            "preserved_run_root": str(run_root),
            "reason": "Preserved for independent inspection of committed evidence paths.",
        },
        "items": {
            "PROBE_GRAPH": "PASS" if static["pass"] else "FAIL-probe-graph",
            "DISTINCT_TARGETS": (
                "PASS"
                if state.get("distinct_targets") and prep_order["pass"]
                else "FAIL-distinct-targets"
            ),
            "BOX_SESSION_CWD": verdict,
            "PARENT_EVIDENCE": "PASS",
            "DURABILITY": "PENDING-orchestrator-DONE.json",
        },
    }
    atomic_write_json(EVIDENCE_PATH, evidence)
    print(verdict)
    if blocker:
        print(blocker)
    return 0 if verdict in {"PASS", "BLOCKED-engine-session-cwd"} else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser(
        "verify", help="run a fresh source-backed CLI probe and write evidence.json"
    )
    verify_parser.set_defaults(func=verify)

    prepare_parser = subparsers.add_parser(
        "prepare", help="prepare the temporary git root and lane worktrees"
    )
    prepare_parser.add_argument("--run-root", required=True)
    prepare_parser.add_argument("--state", required=True)
    prepare_parser.set_defaults(func=prepare)

    bind_parser = subparsers.add_parser(
        "bind-target", help="bind one branch context to its prepared lane target"
    )
    bind_parser.add_argument("--state", required=True)
    bind_parser.add_argument("--lane", required=True, choices=LANES)
    bind_parser.set_defaults(func=bind_target)

    control_parser = subparsers.add_parser(
        "record-control", help="record a deterministic tool node's actual CWD"
    )
    control_parser.add_argument("--state", required=True)
    control_parser.add_argument("--scope", required=True)
    control_parser.add_argument("--phase", required=True)
    control_parser.set_defaults(func=record_control)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - CLI boundary must fail loud and named
        print(f"probe.py: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
