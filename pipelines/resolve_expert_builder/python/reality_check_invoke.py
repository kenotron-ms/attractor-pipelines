# Ported verbatim from microsoft/amplifier-resolver-dot-graph's
# src/amplifier_resolver_dot_graph/handlers/reality_check_invoke.py.
# Reference only -- see resolve_expert_builder.md for why this is not directly
# runnable in this repo (it imports amplifier_resolver_sdk and aiohttp, neither
# of which is part of this repo or its context).
"""Live-SDK invocation entry point for the RealityCheck pipeline node.

Called as a subprocess from ``reality_check.dot``'s ``RealityCheck`` ``tool_command``::

    /opt/uv-tools/amplifier/bin/python -m amplifier_resolver_dot_graph.handlers.reality_check_invoke

Inputs (read from filesystem):
    .resolve/reality_check/artifact.json   {"software_path": "..."}        from BuildArtifact
    /project/.resolve/config.json          {"params": {"acceptance_criteria": ...}, "work_dir": ...}

Output (written on broker-completed runs):
    .resolve/reality_check/verdict.json    envelope consumed by RenderVerdict

The verdict envelope on broker-completed runs (status in {completed, failed, cancelled})::

    {
      "session_id":       <str>,           # broker session id
      "verdict":          <str | null>,    # "pass" | "partial" | "fail" | None
      "failure_mode":     <str | null>,    # "software" | "infrastructure" | "config" | "timeout" | "cancelled"
      "report_yaml_path": <str | null>,    # first artifact_paths entry, normalised
      "status":           <str>,           # "completed" | "failed" | "cancelled"
      "report":           <dict>,          # free-form report from the broker run; {} when absent
    }

The error envelope written by ``build_error_verdict()`` carries the same keys, with
``report`` set to ``{"error": <failure_mode>}``.

Why a separate script vs. an inline ``tool_command`` heredoc:
    - Tool_commands run with ``python3`` on PATH, which inside the worker container is
      a system Python that does NOT have ``aiohttp`` or ``amplifier-resolver-sdk``.
      The SDK-enabled interpreter is at ``/opt/uv-tools/amplifier/bin/python``.
      The .dot tool_command invokes that interpreter directly.
    - Heredocs that span 50+ lines are escape-sensitive when embedded in DOT
      attributes (every ``\\\\n`` line separator gets de-escaped by the parser);
      keeping the logic in a real .py file sidesteps that whole class of issue.
    - This module is testable in isolation (``python -m amplifier_resolver_dot_graph
      .handlers.reality_check_invoke`` from any directory with the right input files
      reproduces the node's behaviour).

Failure policy: NO synthetic fallback. Every infrastructure failure path writes
a clear, descriptive error to stderr and exits non-zero so the pipeline node fails
hard and loud. There is no degraded "synthetic" mode and no automatic recovery.
This is intentional: the live SDK path is the only correct path. If the broker
isn't reachable, the feature flag isn't set, the SDK isn't installed, or any other
infrastructure precondition isn't met, the run MUST fail visibly so the operator
fixes the underlying problem instead of papering over it.

Distinction between script failures and real verdicts:
    - Script failure (exit non-zero, NO verdict.json written):
        * artifact.json or config.json missing or malformed
        * acceptance_criteria not provided in instance params
        * import error (SDK or aiohttp not installed in /opt/uv-tools/amplifier)
        * broker rejects the call (HTTP 501 feature_disabled, HTTP 429 capacity,
          HTTP 401 auth, network unreachable)
        * SDK exception during start or wait
        * wall-clock timeout exceeded
    - Real verdict (exit 0, verdict.json written): the broker session ran to a
      terminal state and returned a RealityCheckResult. That envelope is written
      verbatim — including status=failed, status=cancelled, or any failure_mode.
      Those are the real verdicts of the real reality check, not infrastructure
      failures.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys
import traceback
from typing import Any, Literal, NoReturn

WORK_DIR = pathlib.Path("/project/.resolve")
ARTIFACT_PATH = pathlib.Path(".resolve/reality_check/artifact.json")
VERDICT_PATH = pathlib.Path(".resolve/reality_check/verdict.json")

# 45 min broker + 120 s margin so the broker's own timeout verdict fires first.
# A spec-bounded run (DeriveSpec produces 3-6 tight tests) should converge well
# under 45 min; the hard cap is here to protect against runaway open-ended runs.
# 24h ceiling. Per the reality-check bundle owner, on-target discovery runs can
# legitimately exceed an hour; this is a SAFETY cap to prevent a hung run from
# blocking forever, NOT a target. Runs normally converge in ~1h.
BROKER_TIMEOUT_S = 86400
WALL_CLOCK_TIMEOUT_S = 86520


def _die(reason: str, *, exc: BaseException | None = None) -> NoReturn:
    """Print a descriptive error to stderr and exit non-zero. No verdict written.

    The pipeline engine sees the non-zero exit and fails the RealityCheck node,
    which short-circuits the pipeline with a visible, diagnosable failure
    (instead of advancing to RenderVerdict with a placeholder envelope).
    """
    print(f"reality_check_invoke: FAIL — {reason}", file=sys.stderr)
    if exc is not None:
        print(f"  exception: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
    sys.exit(2)


def _write_verdict(envelope: dict[str, Any]) -> None:
    VERDICT_PATH.parent.mkdir(parents=True, exist_ok=True)
    VERDICT_PATH.write_text(json.dumps(envelope, indent=2))


def build_error_verdict(failure_mode: str) -> dict[str, Any]:
    """Build an error verdict envelope for SDK/infra failure paths.

    Distinct from a clean broker verdict: ``verdict`` is null and
    ``failure_mode`` carries the diagnostic. The failure_mode field is
    consumed by the Phase-3 oracle (load-bearing — the E2E oracle asserts
    failure_mode is null for a clean discovery).
    """
    return {
        "session_id": None,
        "verdict": None,
        "failure_mode": failure_mode,
        "report_yaml_path": None,
        "status": "failed",
        # Keep the envelope shape symmetric with the success path (#376):
        # error-shaped, not empty, so a consumer can tell "no report because
        # infra failed" apart from "no report because the field was absent" --
        # same precedent as pipelines/experiments/reality_report.dot:59's
        # 'report': {'error': type(e).__name__} on its own error path.
        "report": {"error": failure_mode},
    }


def _fail_with_verdict(
    failure_mode: str, reason: str, *, exc: BaseException | None = None
) -> int:
    """Write a failure verdict and return 0.

    Used ONLY for SDK-execution failures (timeout / import / SDK exception)
    so runs_on=always Harvest/Emit nodes proceed.

    Input-contract failures (missing artifact.json/config.json, empty spec)
    stay hard fails (``_die``, exit 2, no verdict) — they mean the node was
    misconfigured upstream and must be loud.
    """
    print(f"reality_check_invoke: {failure_mode} failure — {reason}", file=sys.stderr)
    if exc is not None:
        print(f"  exception: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
    _write_verdict(build_error_verdict(failure_mode))
    return 0


def build_acceptance_criteria(params: Any) -> dict[str, Any]:
    """Map pipeline params to a structured acceptance-criteria dict for the RC broker.

    Channels:
        spec                 -- Precedence order (highest wins):
                                1. ``params['spec']`` -- explicit enumerated spec written
                                   by DeriveSpec (e.g. ``rc_spec.md``).  This is the
                                   primary bounding lever; when present it is transcribed
                                   verbatim by intent-analyzer, suppressing broad inference.
                                2. ``area_focus`` -- one-liner from the exploratory loop.
                                3. ``acceptance_criteria`` -- legacy directed-path string.
        conversation         -- Adversarial end-user prose from DeriveConversation,
                                forwarded as its own channel so the RC runner can use it
                                for richer scenario generation.
        software_description -- Optional deploy hint (e.g. the SUT repo's committed DTU
                                profile text). When present and non-empty, forwarded
                                as-is so the runner can deploy the SUT without drifting.

    Special behaviour:
        When ``rc_conversation_in_spec`` is truthy (Phase 0 smoke-check workaround for
        runner images that ignore the ``conversation`` key), the conversation prose is
        folded into ``spec`` and the ``conversation`` key is omitted.
        ``software_description`` is always forwarded independently (never folded).
    """
    if not isinstance(params, dict):
        params = {}

    explicit_spec = str(params.get("spec") or "").strip()
    area_focus = str(params.get("area_focus") or "").strip()
    legacy = str(params.get("acceptance_criteria") or "").strip()
    conversation = str(params.get("conversation") or "").strip()
    spec = explicit_spec or area_focus or legacy
    fold = bool(params.get("rc_conversation_in_spec", False))
    software_description = str(params.get("software_description") or "").strip()

    if fold and conversation:
        spec = f"{spec}\n\n{conversation}".strip() if spec else conversation
        result: dict[str, Any] = {"spec": spec}
        if software_description:
            result["software_description"] = software_description
        return result

    criteria: dict[str, Any] = {"spec": spec}
    if conversation:
        criteria["conversation"] = conversation
    if software_description:
        criteria["software_description"] = software_description
    return criteria


async def _run_reality_check(
    software_path: str,
    acceptance_criteria: dict[str, Any],
    dtu_lifecycle: Literal["auto", "keep", "destroy"] = "destroy",
) -> dict[str, Any]:
    """Drive the live SDK call. Raises on infrastructure / SDK errors.

    Returns the verdict envelope shape consumed by RenderVerdict. The envelope's
    ``status`` is whatever the broker emitted (``completed`` / ``failed`` /
    ``cancelled``); a non-completed status is still a real verdict from the real
    broker run, not an infrastructure failure of the script itself.

    ``dtu_lifecycle`` controls what happens to the sibling DTU after the run:
    ``"destroy"`` (default — torn down at session end), ``"keep"`` (kept alive
    for manual verification, subject to broker LRU caps), or ``"auto"``
    (destroy on pass / keep on partial-or-fail). The launch form's "Keep SUT
    for manual verification" toggle drives this via the ``keep_sut`` instance
    param.
    """
    from amplifier_resolver_sdk import Resolver

    class _RealityCheckInvoker(Resolver):
        """Minimal Resolver subclass — we only need the inherited public methods."""

    resolver = _RealityCheckInvoker()
    # The SDK's start/wait methods read self.config["work_dir"] to locate the
    # runner config.json that holds platform_url + sub_container_token.
    resolver.config = {"work_dir": str(WORK_DIR)}

    handle = await resolver.start_reality_check(
        acceptance_criteria=acceptance_criteria,
        software_path=software_path,
        environment={},
        dtu_lifecycle=dtu_lifecycle,
        timeout_seconds=BROKER_TIMEOUT_S,
    )
    result = await resolver.wait_for_reality_check(handle, poll_interval=5.0)

    report_yaml_path = result.artifact_paths[0] if result.artifact_paths else None
    return {
        "session_id": handle.session_id,
        "verdict": result.verdict,
        "failure_mode": result.failure_mode,
        "report_yaml_path": report_yaml_path,
        "status": result.status,
        "report": result.report,
    }


def main() -> int:
    # ── Read inputs (config errors fail hard, no envelope written) ───────
    if not ARTIFACT_PATH.exists():
        _die(
            f"artifact missing at {ARTIFACT_PATH} — BuildArtifact node did not run or its output was lost"
        )

    try:
        artifact = json.loads(ARTIFACT_PATH.read_text())
    except json.JSONDecodeError as exc:
        _die(f"malformed artifact.json at {ARTIFACT_PATH}", exc=exc)

    software_path = (
        artifact.get("software_path") if isinstance(artifact, dict) else None
    )
    if not software_path:
        _die(f"artifact.json at {ARTIFACT_PATH} missing required 'software_path' field")

    config_path = WORK_DIR / "config.json"
    if not config_path.exists():
        _die(
            f"runner config.json missing at {config_path} — orchestrator did not seed config "
            "(check that the worker container was spawned by the resolve backend, not started manually)"
        )

    try:
        cfg = json.loads(config_path.read_text())
    except json.JSONDecodeError as exc:
        _die(f"malformed runner config at {config_path}", exc=exc)

    params = cfg.get("params") if isinstance(cfg, dict) else None
    acceptance = build_acceptance_criteria(params)
    if not acceptance.get("spec", "").strip():
        _die(
            "acceptance_criteria has no usable 'spec' — provide an 'area_focus' one-liner "
            "(or legacy 'acceptance_criteria') in instance params"
        )

    # The launch form's "Keep SUT for manual verification" toggle submits a
    # ``keep_sut`` boolean param. Map it to the SDK's ``dtu_lifecycle`` enum:
    # off → "destroy" (default — auto-teardown after run), on → "keep" (sibling
    # DTU stays alive subject to broker LRU caps until the user clicks Destroy
    # in the UI). We don't expose the third ``"auto"`` value (destroy on pass /
    # keep on partial-or-fail) — operators who want it can drive the resolver
    # directly via SDK.
    keep_sut = (
        bool((params or {}).get("keep_sut", False))
        if isinstance(params, dict)
        else False
    )
    dtu_lifecycle: Literal["auto", "keep", "destroy"] = (
        "keep" if keep_sut else "destroy"
    )

    # ── Drive the live SDK (SDK/infra failures write verdict + exit 0) ───
    try:
        envelope = asyncio.run(
            asyncio.wait_for(
                _run_reality_check(software_path, acceptance, dtu_lifecycle),
                timeout=WALL_CLOCK_TIMEOUT_S,
            )
        )
    except asyncio.TimeoutError as exc:
        return _fail_with_verdict(
            "timeout",
            f"wall-clock timeout exceeded ({WALL_CLOCK_TIMEOUT_S}s) — broker did not return a "
            "terminal status; broker is hung or unreachable",
            exc=exc,
        )
    except ImportError as exc:
        return _fail_with_verdict(
            "config",
            "amplifier_resolver_sdk import failed — verify the SDK is installed in "
            "/opt/uv-tools/amplifier/ via the resolver manifest setup_commands",
            exc=exc,
        )
    except BaseException as exc:  # noqa: BLE001 — capture every SDK failure path
        # Catches RealityCheckUnavailableError (501 — flag not set),
        # RealityCheckConcurrencyError (429 — capacity), RealityCheckCancelledError,
        # RealityCheckError (transport / config), and any unexpected exception.
        cls = type(exc).__name__
        if "Unavailable" in cls:
            return _fail_with_verdict(
                "config",
                "broker returned 501 (feature_disabled). Set "
                "AMPLIFIER_RESOLVE_ENABLE_REALITY_CHECK=true on the resolve backend.",
                exc=exc,
            )
        elif "Concurrency" in cls:
            return _fail_with_verdict(
                "concurrency",
                "broker at capacity (HTTP 429). Wait and retry, or scale the broker.",
                exc=exc,
            )
        else:
            return _fail_with_verdict(
                "infrastructure",
                f"SDK call failed: {cls}",
                exc=exc,
            )

    # ── Real verdict from a completed broker session ─────────────────────
    _write_verdict(envelope)
    return 0


if __name__ == "__main__":
    sys.exit(main())
