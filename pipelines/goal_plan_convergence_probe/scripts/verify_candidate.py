"""External deterministic candidate predicate.

This script is intentionally self-contained. It reads candidate bytes, computes
their SHA-256, prints one JSON record, and exits 1 for a normal candidate
failure. Exit 2 is reserved for verifier infrastructure/input failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = "goal-plan.convergence-candidate-verifier/v1"
FEEDBACK_CODE = "EXTERNAL_VERIFIER_REQUIRES_VALID_STATUS"
EXPECTED_BYTES = b"status=valid\nfeedback_ack=EXTERNAL_VERIFIER_REQUIRES_VALID_STATUS\n"


def _record(
    *,
    attempt: int,
    phase: str,
    candidate_sha256: str | None,
    verdict: str,
    feedback: dict[str, str] | None,
    reason: str,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "attempt": attempt,
        "phase": phase,
        "candidate_sha256": candidate_sha256,
        "verdict": verdict,
        "feedback": feedback,
        "reason": reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--phase", choices=("candidate", "parent"), default="candidate")
    args = parser.parse_args()

    if args.attempt < 1:
        print(
            json.dumps(
                _record(
                    attempt=args.attempt,
                    phase=args.phase,
                    candidate_sha256=None,
                    verdict="INFRA",
                    feedback=None,
                    reason="attempt must be positive",
                ),
                sort_keys=True,
            )
        )
        return 2

    try:
        candidate_bytes = args.candidate.read_bytes()
    except OSError as error:
        print(
            json.dumps(
                _record(
                    attempt=args.attempt,
                    phase=args.phase,
                    candidate_sha256=None,
                    verdict="INFRA",
                    feedback=None,
                    reason=f"cannot read candidate: {error}",
                ),
                sort_keys=True,
            )
        )
        return 2

    candidate_sha256 = hashlib.sha256(candidate_bytes).hexdigest()
    if candidate_bytes == EXPECTED_BYTES:
        print(
            json.dumps(
                _record(
                    attempt=args.attempt,
                    phase=args.phase,
                    candidate_sha256=candidate_sha256,
                    verdict="PASS",
                    feedback=None,
                    reason="candidate bytes satisfy the exact predicate",
                ),
                sort_keys=True,
            )
        )
        return 0

    feedback = {
        "code": FEEDBACK_CODE,
        "message": (
            "Set status=valid and acknowledge this verifier feedback with "
            "feedback_ack=EXTERNAL_VERIFIER_REQUIRES_VALID_STATUS."
        ),
        "required_candidate_utf8": EXPECTED_BYTES.decode("utf-8"),
    }
    print(
        json.dumps(
            _record(
                attempt=args.attempt,
                phase=args.phase,
                candidate_sha256=candidate_sha256,
                verdict="FAIL",
                feedback=feedback,
                reason="candidate bytes do not satisfy the exact predicate",
            ),
            sort_keys=True,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
