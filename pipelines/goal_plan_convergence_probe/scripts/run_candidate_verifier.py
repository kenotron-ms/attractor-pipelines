"""Run the external verifier and expose safe graph-routing tokens.

Candidate failure is a normal classifier result: the child verifier exits 1,
that real exit code is durably recorded, and this wrapper exits 0 with a
CANDIDATE_VERIFY:FAIL last-line token. Infrastructure remains distinct.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from probe_common import (
    ACCEPTED_PASS_PATH,
    ARTIFACTS_DIR,
    ATTEMPT_STATE_PATH,
    CANDIDATE_PATH,
    CURRENT_FEEDBACK_PATH,
    FEEDBACK_CODE,
    PIPELINE_DIR,
    VERIFIER_HISTORY_PATH,
    VERIFIER_PATH,
    atomic_write_json,
    atomic_write_text,
    read_json,
    relative_path,
    sha256_file,
)


def _append_record(record: dict[str, Any]) -> None:
    history = read_json(VERIFIER_HISTORY_PATH)
    records = history.get("records")
    if not isinstance(records, list):
        raise TypeError("verifier history records must be a list")
    records.append(record)
    atomic_write_json(VERIFIER_HISTORY_PATH, history)


def _update_attempt(record: dict[str, Any]) -> None:
    state = read_json(ATTEMPT_STATE_PATH)
    attempts = state.get("attempts")
    if not isinstance(attempts, list):
        raise TypeError("attempts must be a list")
    current = int(state["attempt_count"])
    matching = [
        attempt
        for attempt in attempts
        if isinstance(attempt, dict) and int(attempt.get("attempt", -1)) == current
    ]
    if len(matching) != 1:
        raise ValueError(f"expected one attempt record for attempt {current}")
    matching[0]["candidate_sha256_after_worker"] = record["candidate_sha256"]
    matching[0]["verifier_verdict"] = record["verdict"]
    matching[0]["external_verifier_exit_code"] = record["child_exit_code"]
    atomic_write_json(ATTEMPT_STATE_PATH, state)


def _write_raw_log(
    *,
    attempt: int,
    argv: list[str],
    exit_code: int | None,
    stdout: str,
    stderr: str,
) -> Path:
    log_path = ARTIFACTS_DIR / "verifier" / f"attempt-{attempt}.log"
    content = (
        f"argv={json.dumps(argv)}\n"
        f"exit_code={exit_code}\n"
        "--- stdout ---\n"
        f"{stdout}"
        "--- stderr ---\n"
        f"{stderr}"
    )
    atomic_write_text(log_path, content)
    return log_path


def _infra_record(
    *,
    attempt: int,
    verifier_initial: str | None,
    verifier_current: str | None,
    reason: str,
) -> dict[str, Any]:
    candidate_sha256 = sha256_file(CANDIDATE_PATH) if CANDIDATE_PATH.exists() else None
    return {
        "schema_version": "goal-plan.convergence-verifier-invocation/v1",
        "attempt": attempt,
        "candidate_sha256": candidate_sha256,
        "verdict": "INFRA",
        "feedback": None,
        "verifier_sha256_initial": verifier_initial,
        "verifier_sha256_before": verifier_current,
        "verifier_sha256_matches_initial": (
            verifier_initial is not None and verifier_initial == verifier_current
        ),
        "external_verifier_process": False,
        "child_argv": None,
        "child_exit_code": None,
        "child_stdout": "",
        "child_stderr": "",
        "reason": reason,
        "raw_log_path": None,
    }


def main() -> int:
    try:
        state = read_json(ATTEMPT_STATE_PATH)
        attempt = int(state["attempt_count"])
        verifier_initial = str(state["verifier_sha256_initial"])
        verifier_current = sha256_file(VERIFIER_PATH)

        if verifier_current != verifier_initial:
            record = _infra_record(
                attempt=attempt,
                verifier_initial=verifier_initial,
                verifier_current=verifier_current,
                reason="verifier SHA-256 changed before candidate verification",
            )
            _append_record(record)
            _update_attempt(record)
            print("CANDIDATE_VERIFY:INFRA")
            return 0

        argv = [
            sys.executable,
            str(VERIFIER_PATH),
            str(CANDIDATE_PATH),
            "--attempt",
            str(attempt),
            "--phase",
            "candidate",
        ]
        completed = subprocess.run(
            argv,
            cwd=PIPELINE_DIR,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        log_path = _write_raw_log(
            attempt=attempt,
            argv=argv,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

        child_data = json.loads(completed.stdout)
        if not isinstance(child_data, dict):
            raise TypeError("external verifier output must be a JSON object")
        expected_verdict = {0: "PASS", 1: "FAIL"}.get(completed.returncode)
        child_verdict = child_data.get("verdict")
        verdict = (
            expected_verdict
            if expected_verdict is not None and child_verdict == expected_verdict
            else "INFRA"
        )
        candidate_sha256 = sha256_file(CANDIDATE_PATH)
        if child_data.get("candidate_sha256") != candidate_sha256:
            verdict = "INFRA"

        feedback_value = child_data.get("feedback") if verdict == "FAIL" else None
        feedback = feedback_value if isinstance(feedback_value, dict) else None
        if verdict == "FAIL" and (
            feedback is None or feedback.get("code") != FEEDBACK_CODE
        ):
            verdict = "INFRA"
            feedback = None

        record = {
            "schema_version": "goal-plan.convergence-verifier-invocation/v1",
            "attempt": attempt,
            "candidate_sha256": candidate_sha256,
            "verdict": verdict,
            "feedback": feedback,
            "verifier_sha256_initial": verifier_initial,
            "verifier_sha256_before": verifier_current,
            "verifier_sha256_matches_initial": verifier_current == verifier_initial,
            "external_verifier_process": True,
            "child_argv": argv,
            "child_exit_code": completed.returncode,
            "child_stdout": completed.stdout,
            "child_stderr": completed.stderr,
            "reason": child_data.get("reason"),
            "raw_log_path": relative_path(log_path),
        }
        _append_record(record)
        _update_attempt(record)

        if verdict == "FAIL":
            assert feedback is not None
            feedback_json = json.dumps(feedback, sort_keys=True)
            if len(feedback_json) > 500:
                raise ValueError("curated feedback exceeds 500-character bound")
            atomic_write_json(
                CURRENT_FEEDBACK_PATH,
                {
                    "schema_version": "goal-plan.convergence-feedback/v1",
                    "source_attempt": attempt,
                    "source_verdict": "FAIL",
                    "source_external_exit_code": completed.returncode,
                    "source_verification_record": len(
                        read_json(VERIFIER_HISTORY_PATH)["records"]
                    )
                    - 1,
                    "bounded_chars": len(feedback_json),
                    "feedback": feedback,
                },
            )
            print(f"FEEDBACK: {feedback['message']}")
            print("CANDIDATE_VERIFY:FAIL")
            return 0

        if verdict == "PASS":
            atomic_write_json(
                ACCEPTED_PASS_PATH,
                {
                    "schema_version": "goal-plan.convergence-accepted-pass/v1",
                    "attempt": attempt,
                    "candidate_sha256": candidate_sha256,
                    "verifier_sha256": verifier_current,
                    "verification_record": len(
                        read_json(VERIFIER_HISTORY_PATH)["records"]
                    )
                    - 1,
                },
            )
            if attempt == 1:
                print("CANDIDATE_VERIFY:UNEXPECTED_INITIAL_PASS")
            else:
                print("CANDIDATE_VERIFY:PASS")
            return 0

        print("CANDIDATE_VERIFY:INFRA")
        return 0
    except Exception as error:  # noqa: BLE001 - normalize classifier infrastructure
        try:
            state = read_json(ATTEMPT_STATE_PATH)
            attempt = int(state.get("attempt_count", 0))
            verifier_initial_value = state.get("verifier_sha256_initial")
            verifier_initial = (
                str(verifier_initial_value)
                if verifier_initial_value is not None
                else None
            )
            verifier_current = (
                sha256_file(VERIFIER_PATH) if VERIFIER_PATH.exists() else None
            )
            record = _infra_record(
                attempt=attempt,
                verifier_initial=verifier_initial,
                verifier_current=verifier_current,
                reason=f"classifier error: {type(error).__name__}: {error}",
            )
            _append_record(record)
            _update_attempt(record)
        except Exception as record_error:  # noqa: BLE001 - best-effort infra record
            print(
                f"classifier infrastructure evidence write failed: {record_error}",
                file=sys.stderr,
            )
        print("CANDIDATE_VERIFY:INFRA")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
