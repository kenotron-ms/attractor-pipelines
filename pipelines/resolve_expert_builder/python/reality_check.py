# Ported verbatim from microsoft/amplifier-resolver-dot-graph's
# src/amplifier_resolver_dot_graph/handlers/reality_check.py.
# Reference only -- see resolve_expert_builder.md. Not invoked by any node in
# subgraphs/reality_check.dot directly (that composes reality_check_invoke.py's
# main() as a subprocess instead) -- this module is the copy-paste SDK starting
# point for resolver developers wiring reality-check into their own run().
"""Pipeline node handlers for the general-purpose Reality Check pipeline.

These async functions map one-to-one to the nodes in reality_check.dot:

    build_artifact_node  ->  BuildArtifact (parallelogram)
    reality_check_node   ->  RealityCheck  (parallelogram)
    render_verdict_node  ->  RenderVerdict (parallelogram)

Copy-paste starting point
─────────────────────────
Resolver developers who want to add reality-check verification to their own
pipeline should:

1.  Copy this module into their resolver package.
2.  Call these functions from within their resolver's ``run()`` method,
    after building their own SessionFactory (see DotGraphResolver.run() for
    the boilerplate).
3.  Pass ``self`` (the Resolver instance) as ``resolver`` so the SDK methods
    are available.

Example (inside a Resolver subclass's run()):

    from amplifier_resolver_dot_graph.handlers.reality_check import (
        build_artifact_node,
        reality_check_node,
        render_verdict_node,
    )

    artifact = await build_artifact_node(resolver=self, instance=instance_id)
    verdict   = await reality_check_node(resolver=self, instance=instance_id,
                                          **artifact)
    summary   = await render_verdict_node(resolver=self, instance=instance_id,
                                           **verdict)
    print(summary["verdict_markdown"])

SDK surface used (amplifier-resolver-sdk)
──────────────────────────────────────────────────────────────────────
    Resolver.start_reality_check(software_path, acceptance_criteria,
                                  environment, dtu_lifecycle, timeout_seconds)
    Resolver.wait_for_reality_check(handle)
    Resolver.cancel_reality_check(handle)       # optional / cleanup
    Resolver.reality_check_events(handle)       # optional / streaming updates

Result shape (RealityCheckResult)
──────────────────────────────────
    session_id      str               — Amplifier session ID
    status          str               — "completed" | "failed" | "cancelled"
    verdict         str | None        — "pass" | "partial" | "fail" | None
    failure_mode    str | None        — "software" | "infrastructure" | …
    report          dict              — free-form report from the pipeline
    artifact_paths  list[str]         — paths to artifacts produced by the check
    events_url      str               — URL of the session's events stream

Form parameters read
────────────────────
workspace_repo       GitHub repo as "owner/repo" (set via the launch form
                     workspace field).  Normalised to a full HTTPS URL.
acceptance_criteria  Free-text acceptance spec pasted into the large textarea
                     on the launch form.  Passed as {"spec": ...} to the SDK.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from amplifier_resolver_sdk import Resolver


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_params(resolver: "Resolver | None") -> dict[str, Any]:
    """Extract the instance params dict from the resolver's config.

    Returns an empty dict when ``resolver`` is None (test/isolated usage).
    """
    if resolver is None:
        return {}
    config = getattr(resolver, "config", None)
    if not isinstance(config, dict):
        return {}
    return config.get("params", {})


# ── Node handlers ─────────────────────────────────────────────────────────────


async def build_artifact_node(
    *,
    resolver: "Resolver | None",
    instance: str,
    **_: Any,
) -> dict[str, Any]:
    """Resolve the workspace repo URL as the software_path for reality-check.

    Reads ``workspace_repo`` from the launch form (via
    ``resolver.config["params"]``).  Normalises "owner/repo" shorthand to a
    full GitHub HTTPS URL.

    Args:
        resolver: The SDK Resolver instance (provides config and reality-check
            methods).  May be ``None`` in unit-test contexts.
        instance: Resolver instance identifier (for logging).

    Returns:
        dict with ``software_path`` key consumed by ``reality_check_node``.

    Raises:
        ValueError: If ``workspace_repo`` is absent or empty.
    """
    params = _get_params(resolver)
    workspace_repo: str = params.get("workspace_repo") or ""
    if not workspace_repo:
        raise ValueError(
            "workspace_repo is required (fill in the 'Workspace GitHub repo' field on the launch form)"
        )

    software_path = (
        workspace_repo
        if workspace_repo.startswith("http")
        else f"https://github.com/{workspace_repo}"
    )
    return {"software_path": software_path}


async def reality_check_node(
    *,
    resolver: "Resolver",
    instance: str,
    software_path: str,
    **_: Any,
) -> dict[str, Any]:
    """Submit the SUT to reality-check, wait for the verdict.

    Reads ``acceptance_criteria`` from the launch form (via
    ``resolver.config["params"]``).  Passes ``environment={}`` so the
    recipe's intent-analyzer infers language / type / port from the SUT
    itself, making this pipeline universal across stacks.

    Args:
        resolver:      The SDK Resolver instance.
        instance:      Resolver instance identifier.
        software_path: Full HTTPS URL to the SUT (from ``build_artifact_node``).

    Returns:
        dict with verdict envelope keys: session_id, verdict, failure_mode,
        artifact_paths, report, status.

    Raises:
        ValueError: If ``acceptance_criteria`` is absent or empty.
    """
    params = _get_params(resolver)
    acceptance_criteria_spec: str = params.get("acceptance_criteria") or ""
    if not acceptance_criteria_spec:
        raise ValueError(
            "acceptance_criteria is required (fill in the 'Acceptance criteria' textarea on the launch form)"
        )

    handle = await resolver.start_reality_check(
        software_path=software_path,
        acceptance_criteria={"spec": acceptance_criteria_spec},
        # Empty dict signals "auto-infer" — the recipe's intent-analyzer reads
        # the SUT to discover language / type / port.  This makes the pipeline
        # universal across stacks (Python, Node, Go, etc.).
        environment={},
        dtu_lifecycle="destroy",
        timeout_seconds=1800,
    )
    result = await resolver.wait_for_reality_check(handle)
    return {
        "session_id": handle.session_id,
        "verdict": result.verdict,
        "failure_mode": result.failure_mode,
        "artifact_paths": result.artifact_paths,
        "report": result.report,
        "status": result.status,
    }


async def render_verdict_node(
    *,
    resolver: "Resolver | None",
    instance: str,
    **state: Any,
) -> dict[str, Any]:
    """Render the verdict envelope as a human-readable markdown summary.

    Args:
        resolver: The SDK Resolver instance.
        instance: Resolver instance identifier.
        **state:  Verdict envelope keys forwarded from ``reality_check_node``.

    Returns:
        dict with ``verdict_markdown`` key plus all forwarded state keys.
    """
    session_id = state.get("session_id", "n/a")
    verdict = state.get("verdict", "unknown")
    failure_mode = state.get("failure_mode") or "null"
    artifact_paths: list[str] = state.get("artifact_paths") or []
    report_summary = artifact_paths[0] if artifact_paths else "n/a"

    summary = (
        "# Reality-check verdict\n\n"
        f"- **Session**: `{session_id}`\n"
        f"- **Verdict**: `{verdict}`\n"
        f"- **Failure mode**: `{failure_mode}`\n"
        f"- **Report artifact**: `{report_summary}`\n"
        "\n"
        f"Full report artifacts: {artifact_paths}\n"
    )
    return {"verdict_markdown": summary, **state}
