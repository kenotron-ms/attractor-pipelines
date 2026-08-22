"""Atomically reserve the next adaptive candidate attempt."""

from __future__ import annotations

from probe_common import (
    ATTEMPT_STATE_PATH,
    CURRENT_FEEDBACK_PATH,
    atomic_write_json,
    read_json,
    relative_path,
)


def main() -> int:
    try:
        state = read_json(ATTEMPT_STATE_PATH)
        attempt_count = int(state["attempt_count"])
        max_attempts = int(state["max_attempts"])
        if attempt_count >= max_attempts:
            print("CORRECTION:EXHAUSTED")
            return 0

        feedback = read_json(CURRENT_FEEDBACK_PATH)
        next_attempt = attempt_count + 1
        attempts = state.get("attempts")
        if not isinstance(attempts, list):
            raise TypeError("attempts must be a list")
        attempts.append(
            {
                "attempt": next_attempt,
                "origin": "adaptive_box_correction",
                "feedback_path": relative_path(CURRENT_FEEDBACK_PATH),
                "feedback_source_attempt": feedback["source_attempt"],
            }
        )
        state["attempt_count"] = next_attempt
        atomic_write_json(ATTEMPT_STATE_PATH, state)
    except Exception:  # noqa: BLE001 - normalize state failure for graph routing
        print("CORRECTION:INFRA")
        return 0

    print("CORRECTION:READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
