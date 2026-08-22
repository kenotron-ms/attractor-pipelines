"""Reset durable probe state and seed deterministic invalid candidate attempt 1."""

from __future__ import annotations

import shutil

from probe_common import (
    ATTEMPT_STATE_PATH,
    CANDIDATE_PATH,
    INVALID_CANDIDATE,
    MAX_ATTEMPTS,
    STATE_DIR,
    VERIFIER_HISTORY_PATH,
    VERIFIER_PATH,
    atomic_write_bytes,
    atomic_write_json,
    relative_path,
    sha256_bytes,
    sha256_file,
)


def main() -> int:
    try:
        shutil.rmtree(STATE_DIR, ignore_errors=True)
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(CANDIDATE_PATH, INVALID_CANDIDATE)

        initial_candidate_sha256 = sha256_bytes(INVALID_CANDIDATE)
        verifier_sha256 = sha256_file(VERIFIER_PATH)
        state = {
            "schema_version": "goal-plan.convergence-attempt-state/v1",
            "attempt_count": 1,
            "max_attempts": MAX_ATTEMPTS,
            "initial_candidate_sha256": initial_candidate_sha256,
            "verifier_path": relative_path(VERIFIER_PATH),
            "verifier_sha256_initial": verifier_sha256,
            "attempts": [
                {
                    "attempt": 1,
                    "origin": "deterministic_invalid_seed",
                    "candidate_sha256_before_verification": initial_candidate_sha256,
                }
            ],
        }
        atomic_write_json(ATTEMPT_STATE_PATH, state)
        atomic_write_json(
            VERIFIER_HISTORY_PATH,
            {
                "schema_version": "goal-plan.convergence-verifier-history/v1",
                "records": [],
            },
        )
    except Exception:  # noqa: BLE001 - normalize setup failure for graph routing
        print("RESET:INFRA")
        return 0

    print("RESET:OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
