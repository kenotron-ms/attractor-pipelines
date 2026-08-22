"""Write an evidence-bearing non-success terminal and exit nonzero."""

from __future__ import annotations

import argparse
import sys

from probe_common import (
    ATTEMPT_STATE_PATH,
    PARENT_EVIDENCE_PATH,
    TERMINAL_PATH,
    VERIFIER_HISTORY_PATH,
    atomic_write_json,
    read_json,
    relative_path,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reason")
    args = parser.parse_args()

    evidence: dict[str, object] = {
        "schema_version": "goal-plan.convergence-terminal/v1",
        "result": "BLOCKED" if args.reason.startswith("BLOCKED_") else "FAIL",
        "reason": args.reason,
        "attempt_state_path": relative_path(ATTEMPT_STATE_PATH),
        "verifier_history_path": relative_path(VERIFIER_HISTORY_PATH),
    }
    try:
        state = read_json(ATTEMPT_STATE_PATH)
        evidence["attempt_count"] = state.get("attempt_count")
        evidence["max_attempts"] = state.get("max_attempts")
    except Exception:  # noqa: BLE001 - preserve named terminal on malformed state
        evidence["attempt_count"] = None
        evidence["max_attempts"] = None
    if PARENT_EVIDENCE_PATH.exists():
        evidence["parent_evidence_path"] = relative_path(PARENT_EVIDENCE_PATH)

    try:
        atomic_write_json(TERMINAL_PATH, evidence)
    except Exception as error:  # noqa: BLE001 - preserve the intended nonzero exit
        print(
            f"{args.reason}: terminal evidence write failed: {error}", file=sys.stderr
        )
        return 1

    print(args.reason, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
