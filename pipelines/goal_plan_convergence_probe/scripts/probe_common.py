"""Shared paths and atomic file helpers for the convergence probe."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parents[1]
CANDIDATE_PATH = PIPELINE_DIR / "candidate.txt"
STATE_DIR = PIPELINE_DIR / "run_state"
ARTIFACTS_DIR = PIPELINE_DIR / "artifacts"
VERIFIER_PATH = PIPELINE_DIR / "scripts" / "verify_candidate.py"

ATTEMPT_STATE_PATH = STATE_DIR / "attempt_state.json"
VERIFIER_HISTORY_PATH = STATE_DIR / "verifier_history.json"
CURRENT_FEEDBACK_PATH = STATE_DIR / "current_feedback.json"
ACCEPTED_PASS_PATH = STATE_DIR / "accepted_pass.json"
PARENT_EVIDENCE_PATH = STATE_DIR / "parent_evidence.json"
TERMINAL_PATH = STATE_DIR / "terminal.json"

MAX_ATTEMPTS = 3
FEEDBACK_CODE = "EXTERNAL_VERIFIER_REQUIRES_VALID_STATUS"
INVALID_CANDIDATE = b"status=invalid\nfeedback_ack=none\n"
VALID_CANDIDATE = (
    b"status=valid\nfeedback_ack=EXTERNAL_VERIFIER_REQUIRES_VALID_STATUS\n"
)


def sha256_bytes(content: bytes) -> str:
    """Return the SHA-256 hex digest for bytes."""

    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest for a file."""

    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object from *path*."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"expected JSON object at {path}")
    return data


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Atomically replace *path* with *content*."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace *path* with UTF-8 text."""

    atomic_write_bytes(path, content.encode("utf-8"))


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically replace *path* with canonical, human-readable JSON."""

    serialized = json.dumps(data, indent=2, sort_keys=True) + "\n"
    atomic_write_text(path, serialized)


def relative_path(path: Path) -> str:
    """Return a pipeline-directory-relative path string."""

    return str(path.resolve().relative_to(PIPELINE_DIR))
