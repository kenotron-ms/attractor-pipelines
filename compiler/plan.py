"""Plan-spec loading and validation for the goal-plan compiler.

A ``plan.json``-shaped spec is the *input* the compiler reads to generate a
``goal_plan_smoke``-family parent ``.dot`` (see the design doc,
``docs/plans/2026-08-24-goal-plan-compiler-resolve-design.md``). This module
turns that raw dict into a validated, normalized in-memory model, and raises a
single, clearly-named error (:class:`PlanValidationError`) the moment a required
field is missing or the wave/integration structure is internally inconsistent --
never a malformed graph downstream.

Determinism is the whole point: this module contains no LLM call and no
randomness. Same spec in, same model out.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Family defaults -- applied only when the spec omits an optional field, so the
# compiler stays faithful to the hand-authored ``goal_plan_smoke`` exemplar it
# generalizes while accepting minimal specs.
DEFAULT_TERMINALS = ["COMPLETE", "RESIDUALS_READY", "INFRA_FAILURE", "ABORTED"]
DEFAULT_CHILD_DOT = "subgraphs/goal_lane.dot"
DEFAULT_CORRECTION_CHILD_DOT = "subgraphs/integration_correction.dot"
DEFAULT_DELIVERY_CHILD_DOT = "subgraphs/deliver_pr.dot"
DEFAULT_MAX_ATTEMPTS = 3


class PlanValidationError(ValueError):
    """Raised when a plan spec is missing a required field or is structurally
    inconsistent. The message always names the offending field/lane so a caller
    (human or Wave-2 integrating skill) gets an actionable error, not a stack
    trace deep inside graph emission.
    """


@dataclass(frozen=True)
class Lane:
    """One validated lane, as the generator consumes it."""

    lane_id: str
    wave: int
    depends_on: tuple[str, ...]
    verifier_argv: tuple[str, ...]
    marker_file: str
    marker_content: str
    seeded_failure: bool = False
    child_dot: str = DEFAULT_CHILD_DOT
    branch: str = ""  # resolved by Plan.__post_init__ if left empty


@dataclass(frozen=True)
class Plan:
    """A validated, normalized plan spec.

    Construct via :func:`load_plan` (from a file) or :func:`build_plan` (from an
    already-parsed dict). Both run full validation before returning.
    """

    plan_id: str
    lanes: dict[str, Lane]
    waves: tuple[int, ...]
    integration_order: tuple[str, ...]
    terminals: tuple[str, ...]
    branch_namespace: str
    max_attempts: int
    correction_child_dot: str
    delivery_child_dot: str
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def lane_ids_sorted(self) -> list[str]:
        return sorted(self.lanes.keys())

    def first_wave(self) -> int:
        return self.waves[0]

    def wave_of(self, lane_id: str) -> int:
        return self.lanes[lane_id].wave

    def first_wave_lane_ids(self) -> list[str]:
        """Lanes in the first wave, in integration order."""
        fw = self.first_wave()
        return [lid for lid in self.integration_order if self.lanes[lid].wave == fw]


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise PlanValidationError(message)


def _default_branch_namespace(plan_id: str) -> str:
    # "goal_plan_smoke" -> "goal-plan-smoke" (matches the exemplar's lane branch
    # prefix), while remaining deterministic for any plan_id.
    return plan_id.replace("_", "-")


def build_plan(spec: dict[str, Any]) -> Plan:
    """Validate and normalize a raw plan dict into a :class:`Plan`.

    Raises :class:`PlanValidationError` with a named field on the first problem.
    """

    _require(isinstance(spec, dict), "plan spec must be a JSON object")

    plan_id = spec.get("plan_id")
    _require(
        isinstance(plan_id, str) and bool(plan_id),
        "plan spec missing required field 'plan_id' (non-empty string)",
    )
    assert isinstance(plan_id, str)  # for type-checkers

    raw_lanes = spec.get("lanes")
    _require(
        isinstance(raw_lanes, dict) and len(raw_lanes) > 0,
        "plan spec missing required field 'lanes' (non-empty object keyed by lane id)",
    )
    assert isinstance(raw_lanes, dict)

    lanes: dict[str, Lane] = {}
    for lane_id, raw in raw_lanes.items():
        lanes[lane_id] = _build_lane(lane_id, raw)

    # ---- waves ---------------------------------------------------------
    raw_waves = spec.get("waves")
    _require(
        isinstance(raw_waves, list) and len(raw_waves) > 0,
        "plan spec missing required field 'waves' (non-empty list)",
    )
    assert isinstance(raw_waves, list)
    waves: list[int] = []
    for idx, w in enumerate(raw_waves):
        _require(
            isinstance(w, dict) and "wave" in w,
            f"waves[{idx}] missing required field 'wave'",
        )
        wnum = w["wave"]
        _require(isinstance(wnum, int), f"waves[{idx}].wave must be an integer")
        waves.append(wnum)
    _require(
        waves == sorted(waves) and len(set(waves)) == len(waves),
        f"waves must be strictly increasing and unique, got {waves}",
    )

    declared_wave_numbers = set(waves)
    for lane_id, lane in lanes.items():
        _require(
            lane.wave in declared_wave_numbers,
            f"lane '{lane_id}' has wave {lane.wave} not declared in top-level 'waves' {waves}",
        )

    # ---- integration_order --------------------------------------------
    order = spec.get("integration_order")
    _require(
        isinstance(order, list) and len(order) > 0,
        "plan spec missing required field 'integration_order' (non-empty list)",
    )
    assert isinstance(order, list)
    _require(
        sorted(order) == sorted(lanes.keys()),
        "integration_order must be a permutation of the lane ids; "
        f"got {order}, lanes {sorted(lanes.keys())}",
    )
    # Wave-monotonic: the structural wave-gating pattern requires every lane of
    # an earlier wave to be integrated before any lane of a later wave.
    prev_wave = None
    for lane_id in order:
        w = lanes[lane_id].wave
        if prev_wave is not None:
            _require(
                w >= prev_wave,
                "integration_order must be non-decreasing by wave "
                f"(lane '{lane_id}' wave {w} follows wave {prev_wave})",
            )
        prev_wave = w

    # ---- depends_on references ----------------------------------------
    for lane_id, lane in lanes.items():
        for dep in lane.depends_on:
            _require(
                dep in lanes,
                f"lane '{lane_id}' depends_on unknown lane '{dep}'",
            )

    # ---- optional / defaulted fields ----------------------------------
    terminals = spec.get("terminals", DEFAULT_TERMINALS)
    _require(
        isinstance(terminals, list)
        and all(isinstance(t, str) for t in terminals)
        and len(terminals) > 0,
        "'terminals' must be a non-empty list of strings when provided",
    )

    branch_namespace = spec.get("branch_namespace") or _default_branch_namespace(
        plan_id
    )

    budgets = spec.get("budgets") or {}
    _require(isinstance(budgets, dict), "'budgets' must be an object when provided")
    max_attempts = budgets.get("max_adaptive_attempts_per_lane", DEFAULT_MAX_ATTEMPTS)
    _require(
        isinstance(max_attempts, int) and max_attempts >= 1,
        "budgets.max_adaptive_attempts_per_lane must be an integer >= 1 when provided",
    )

    correction = spec.get("correction") or {}
    _require(
        isinstance(correction, dict), "'correction' must be an object when provided"
    )
    correction_child_dot = correction.get("child_dot", DEFAULT_CORRECTION_CHILD_DOT)

    delivery = spec.get("delivery") or {}
    _require(isinstance(delivery, dict), "'delivery' must be an object when provided")
    delivery_child_dot = delivery.get("child_dot", DEFAULT_DELIVERY_CHILD_DOT)

    # Resolve empty lane branches now that the namespace is known.
    resolved_lanes: dict[str, Lane] = {}
    for lane_id, lane in lanes.items():
        branch = lane.branch or f"{branch_namespace}/{lane_id}"
        resolved_lanes[lane_id] = Lane(
            lane_id=lane.lane_id,
            wave=lane.wave,
            depends_on=lane.depends_on,
            verifier_argv=lane.verifier_argv,
            marker_file=lane.marker_file,
            marker_content=lane.marker_content,
            seeded_failure=lane.seeded_failure,
            child_dot=lane.child_dot,
            branch=branch,
        )

    return Plan(
        plan_id=plan_id,
        lanes=resolved_lanes,
        waves=tuple(waves),
        integration_order=tuple(order),
        terminals=tuple(terminals),
        branch_namespace=branch_namespace,
        max_attempts=max_attempts,
        correction_child_dot=correction_child_dot,
        delivery_child_dot=delivery_child_dot,
        raw=spec,
    )


def _build_lane(lane_id: str, raw: Any) -> Lane:
    _require(isinstance(raw, dict), f"lane '{lane_id}' must be an object")

    _require("wave" in raw, f"lane '{lane_id}' missing required field 'wave'")
    wave = raw["wave"]
    _require(
        isinstance(wave, int) and wave >= 1,
        f"lane '{lane_id}' field 'wave' must be an integer >= 1",
    )

    _require(
        "depends_on" in raw,
        f"lane '{lane_id}' missing required field 'depends_on' (list; may be empty)",
    )
    depends_on = raw["depends_on"]
    _require(
        isinstance(depends_on, list) and all(isinstance(d, str) for d in depends_on),
        f"lane '{lane_id}' field 'depends_on' must be a list of lane-id strings",
    )

    _require(
        "verifier_argv" in raw,
        f"lane '{lane_id}' missing required field 'verifier_argv'",
    )
    verifier_argv = raw["verifier_argv"]
    _require(
        isinstance(verifier_argv, list)
        and len(verifier_argv) > 0
        and all(isinstance(a, str) for a in verifier_argv),
        f"lane '{lane_id}' field 'verifier_argv' must be a non-empty list of strings",
    )

    _require(
        "marker_file" in raw, f"lane '{lane_id}' missing required field 'marker_file'"
    )
    marker_file = raw["marker_file"]
    _require(
        isinstance(marker_file, str) and bool(marker_file),
        f"lane '{lane_id}' field 'marker_file' must be a non-empty string",
    )

    _require(
        "marker_content" in raw,
        f"lane '{lane_id}' missing required field 'marker_content'",
    )
    marker_content = raw["marker_content"]
    _require(
        isinstance(marker_content, str),
        f"lane '{lane_id}' field 'marker_content' must be a string",
    )

    seeded_failure = raw.get("seeded_failure", False)
    _require(
        isinstance(seeded_failure, bool),
        f"lane '{lane_id}' field 'seeded_failure' must be a boolean",
    )

    child_dot = raw.get("child_dot", DEFAULT_CHILD_DOT)
    _require(
        isinstance(child_dot, str) and bool(child_dot),
        f"lane '{lane_id}' field 'child_dot' must be a non-empty string",
    )

    branch = raw.get("branch", "")
    _require(
        isinstance(branch, str),
        f"lane '{lane_id}' field 'branch' must be a string when provided",
    )

    return Lane(
        lane_id=lane_id,
        wave=wave,
        depends_on=tuple(depends_on),
        verifier_argv=tuple(verifier_argv),
        marker_file=marker_file,
        marker_content=marker_content,
        seeded_failure=seeded_failure,
        child_dot=child_dot,
        branch=branch,
    )


def load_plan(path: str | Path) -> Plan:
    """Load and validate a plan spec from a JSON file path."""

    p = Path(path)
    _require(p.is_file(), f"plan spec file not found: {p}")
    try:
        spec = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise PlanValidationError(f"plan spec {p} is not valid JSON: {e}") from e
    return build_plan(spec)
