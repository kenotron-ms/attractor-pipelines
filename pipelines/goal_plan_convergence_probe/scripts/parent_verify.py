"""Independent parent-side verifier and sole success-token authority."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from probe_common import (
    ACCEPTED_PASS_PATH,
    ARTIFACTS_DIR,
    ATTEMPT_STATE_PATH,
    CANDIDATE_PATH,
    CURRENT_FEEDBACK_PATH,
    FEEDBACK_CODE,
    PARENT_EVIDENCE_PATH,
    PIPELINE_DIR,
    VERIFIER_HISTORY_PATH,
    VERIFIER_PATH,
    atomic_write_json,
    atomic_write_text,
    read_json,
    relative_path,
    sha256_file,
)

SUCCESS_TOKEN = "CONVERGENCE_PROBE:PASS"


def _write_parent_evidence(data: dict[str, Any]) -> None:
    atomic_write_json(PARENT_EVIDENCE_PATH, data)


def main() -> int:
    try:
        state = read_json(ATTEMPT_STATE_PATH)
        history = read_json(VERIFIER_HISTORY_PATH)
        accepted = read_json(ACCEPTED_PASS_PATH)
        feedback = read_json(CURRENT_FEEDBACK_PATH)

        records = history.get("records")
        attempts = state.get("attempts")
        if not isinstance(records, list) or not isinstance(attempts, list):
            raise TypeError("attempt and verifier history records must be lists")

        attempt_count = int(state["attempt_count"])
        max_attempts = int(state["max_attempts"])
        initial_hash = str(state["initial_candidate_sha256"])
        final_hash = sha256_file(CANDIDATE_PATH)
        accepted_hash = str(accepted["candidate_sha256"])
        verifier_initial = str(state["verifier_sha256_initial"])
        verifier_after_worker = sha256_file(VERIFIER_PATH)
        first = records[0] if records else {}

        child_argv = [
            sys.executable,
            str(VERIFIER_PATH),
            str(CANDIDATE_PATH),
            "--attempt",
            str(attempt_count),
            "--phase",
            "parent",
        ]
        child_exit_code: int | None = None
        child_stdout = ""
        child_stderr = ""
        child_data: dict[str, Any] = {}

        if verifier_after_worker == verifier_initial:
            completed = subprocess.run(
                child_argv,
                cwd=PIPELINE_DIR,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            child_exit_code = completed.returncode
            child_stdout = completed.stdout
            child_stderr = completed.stderr
            parsed = json.loads(child_stdout)
            if isinstance(parsed, dict):
                child_data = parsed

        parent_log_path = ARTIFACTS_DIR / "parent_verifier.log"
        atomic_write_text(
            parent_log_path,
            (
                f"argv={json.dumps(child_argv)}\n"
                f"exit_code={child_exit_code}\n"
                "--- stdout ---\n"
                f"{child_stdout}"
                "--- stderr ---\n"
                f"{child_stderr}"
            ),
        )

        feedback_data = feedback.get("feedback")
        feedback_code = (
            feedback_data.get("code") if isinstance(feedback_data, dict) else None
        )
        candidate_text = CANDIDATE_PATH.read_text(encoding="utf-8")
        checks = {
            "verifier_sha256_unchanged": verifier_after_worker == verifier_initial,
            "accepted_pass_bound_to_final_sha256": accepted_hash == final_hash,
            "accepted_attempt_is_final_attempt": int(accepted["attempt"])
            == attempt_count,
            "first_attempt_failed_externally": (
                first.get("attempt") == 1
                and first.get("verdict") == "FAIL"
                and first.get("external_verifier_process") is True
                and first.get("child_exit_code") == 1
            ),
            "attempt_count_within_bound": 2 <= attempt_count <= max_attempts == 3,
            "candidate_hash_changed": initial_hash != final_hash,
            "feedback_nonempty": (
                isinstance(feedback_data, dict)
                and bool(feedback_data)
                and int(feedback.get("bounded_chars", 501)) <= 500
            ),
            "feedback_reflected_in_candidate": (
                feedback_code == FEEDBACK_CODE
                and f"feedback_ack={feedback_code}\n" in candidate_text
            ),
            "parent_rerun_exit_zero": child_exit_code == 0,
            "parent_rerun_predicate_passed": child_data.get("verdict") == "PASS",
            "parent_rerun_hash_matches_final": (
                child_data.get("candidate_sha256") == final_hash
            ),
        }
        result = "PASS" if all(checks.values()) else "FAIL"
        evidence = {
            "schema_version": "goal-plan.convergence-parent-verifier/v1",
            "result": result,
            "checks": checks,
            "attempt_count": attempt_count,
            "max_attempts": max_attempts,
            "initial_candidate_sha256": initial_hash,
            "final_candidate_sha256": final_hash,
            "accepted_candidate_sha256": accepted_hash,
            "verifier_sha256_initial": verifier_initial,
            "verifier_sha256_after_worker": verifier_after_worker,
            "first_failure": first,
            "feedback": feedback,
            "parent_child_argv": child_argv,
            "parent_child_exit_code": child_exit_code,
            "parent_child_stdout": child_stdout,
            "parent_child_stderr": child_stderr,
            "parent_raw_log_path": relative_path(parent_log_path),
            "terminal_token": SUCCESS_TOKEN if result == "PASS" else None,
        }
        _write_parent_evidence(evidence)

        if result == "PASS":
            print(SUCCESS_TOKEN)
        else:
            print("PARENT_VERIFY:FAIL")
        return 0
    except Exception as error:  # noqa: BLE001 - normalize parent infrastructure
        try:
            _write_parent_evidence(
                {
                    "schema_version": "goal-plan.convergence-parent-verifier/v1",
                    "result": "INFRA",
                    "reason": f"{type(error).__name__}: {error}",
                    "terminal_token": None,
                }
            )
        except Exception as write_error:  # noqa: BLE001 - preserve routing token
            print(
                f"parent infrastructure evidence write failed: {write_error}",
                file=sys.stderr,
            )
        print("PARENT_VERIFY:INFRA")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
