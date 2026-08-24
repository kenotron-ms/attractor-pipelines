"""Unit tests for the goal-plan compiler (D2, D3, D4).

Covers, per the lane goal:

* **D2** -- regenerating the known-good exemplar: feed the compiler a
  ``plan.json``-shaped spec equivalent to
  ``pipelines/goal_plan_smoke/plan.json`` and prove the *parsed graph
  structure* (node ids, shapes, edges, wave-gating topology, graph attrs) is
  equivalent to the hand-authored ``goal_plan_smoke.dot`` -- structural, not
  byte-for-byte.
* **D3** -- generated output validates against the engine's own
  ``parse_dot`` / ``validate`` with zero ERROR-severity diagnostics (for both
  the 3-lane/2-wave and 2-lane/1-wave plans).
* **D4** -- a 2-lane single-wave plan, the 3-lane/2-wave plan, and an invalid
  plan (missing a required field) producing a clear, named error.

Engine-dependent checks (D2, D3) locate the attractor engine via
``compiler.validate.load_engine`` and ``pytest.skip`` gracefully when it is not
present, so the pure-Python D4 tests still run in any environment.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the ``compiler`` package importable when this file is run directly or via
# a bare ``pytest`` from anywhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from compiler import build_plan, compile_plan, load_plan
from compiler.plan import PlanValidationError
from compiler.validate import EngineUnavailable, load_engine

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PLAN_3LANE = FIXTURES / "plan_3lane_2wave.json"
PLAN_2LANE = FIXTURES / "plan_2lane_1wave.json"
PLAN_INVALID = FIXTURES / "plan_invalid_missing_wave.json"

EXEMPLAR_DOT = _REPO_ROOT / "pipelines" / "goal_plan_smoke" / "goal_plan_smoke.dot"


def _engine_or_skip():
    try:
        return load_engine()
    except EngineUnavailable as e:  # pragma: no cover - environment dependent
        pytest.skip(f"attractor engine unavailable: {e}")


def _structure(graph):
    """(nodes->shape dict, sorted edge tuples, graph_attrs, default_max_retry, name)."""
    nodes = {nid: n.shape for nid, n in graph.nodes.items()}
    edges = sorted((e.from_node, e.to_node, e.condition, e.weight) for e in graph.edges)
    return nodes, edges, dict(graph.graph_attrs), graph.default_max_retry, graph.name


# ----------------------------------------------------------------------------
# D4: build the two well-formed plans; reject the invalid one.
# ----------------------------------------------------------------------------


def test_d4_build_2lane_single_wave():
    dot = compile_plan(load_plan(PLAN_2LANE))
    assert dot.startswith("//")
    assert "digraph two_lane_single_wave {" in dot
    # Two lanes, one wave -> concurrent launch block, no sequential launch and
    # no second-wave nodes.
    assert "Wave1Launch" in dot
    assert "LaunchLaneA" in dot and "LaunchLaneB" in dot
    assert "Wave2" not in dot
    assert "LaunchLaneC" not in dot


def test_d4_build_3lane_two_wave():
    dot = compile_plan(load_plan(PLAN_3LANE))
    assert "digraph goal_plan_smoke {" in dot
    # Wave 2 lane_c is launched sequentially (just-in-time) as LaunchLaneC.
    assert "LaunchLaneC" in dot
    assert 'plan_waves="1,2"' in dot


def test_d4_invalid_plan_missing_field_named_error():
    with pytest.raises(PlanValidationError) as exc:
        load_plan(PLAN_INVALID)
    msg = str(exc.value)
    # The error must name the offending lane and field, not be a generic crash.
    assert "lane_b" in msg
    assert "wave" in msg


@pytest.mark.parametrize(
    "spec, needle",
    [
        ({"plan_id": "p"}, "lanes"),  # missing lanes
        (
            {
                "plan_id": "p",
                "lanes": {
                    "a": {
                        "wave": 1,
                        "depends_on": [],
                        "verifier_argv": ["x"],
                        "marker_file": "m",
                        "marker_content": "c",
                    }
                },
                "waves": [{"wave": 1, "lanes": ["a"]}],
            },
            "integration_order",
        ),  # missing integration_order
    ],
)
def test_d4_invalid_specs_are_named(spec, needle):
    with pytest.raises(PlanValidationError) as exc:
        build_plan(spec)
    assert needle in str(exc.value)


def test_d4_integration_order_must_be_wave_monotonic():
    spec = {
        "plan_id": "p",
        "lanes": {
            "a": {
                "wave": 1,
                "depends_on": [],
                "verifier_argv": ["x"],
                "marker_file": "ma",
                "marker_content": "ca",
            },
            "b": {
                "wave": 2,
                "depends_on": [],
                "verifier_argv": ["x"],
                "marker_file": "mb",
                "marker_content": "cb",
            },
        },
        "waves": [{"wave": 1, "lanes": ["a"]}, {"wave": 2, "lanes": ["b"]}],
        "integration_order": ["b", "a"],  # wave 2 before wave 1 -- invalid
    }
    with pytest.raises(PlanValidationError) as exc:
        build_plan(spec)
    assert "non-decreasing" in str(exc.value)


# ----------------------------------------------------------------------------
# D2: structural equivalence to the hand-authored exemplar.
# ----------------------------------------------------------------------------


def test_d2_structural_equivalence_to_exemplar():
    parse_dot, _validate = _engine_or_skip()

    generated = compile_plan(load_plan(PLAN_3LANE))
    g_gen = parse_dot(generated)
    g_ref = parse_dot(EXEMPLAR_DOT.read_text(encoding="utf-8"))

    n_gen, e_gen, a_gen, dmr_gen, name_gen = _structure(g_gen)
    n_ref, e_ref, a_ref, dmr_ref, name_ref = _structure(g_ref)

    # Same node ids.
    assert set(n_gen) == set(n_ref), (
        f"node id mismatch; +{sorted(set(n_gen) - set(n_ref))} -{sorted(set(n_ref) - set(n_gen))}"
    )
    # Same shape for every node.
    shape_diffs = {
        nid: (n_gen[nid], n_ref[nid]) for nid in n_gen if n_gen[nid] != n_ref[nid]
    }
    assert not shape_diffs, f"shape diffs: {shape_diffs}"
    # Same edges (source, target, condition, weight) -- this is the wave-gating
    # topology.
    assert set(e_gen) == set(e_ref), (
        f"edge mismatch; +{sorted(set(e_gen) - set(e_ref))} -{sorted(set(e_ref) - set(e_gen))}"
    )
    # Same graph-level attributes and promoted fields.
    assert a_gen == a_ref
    assert dmr_gen == dmr_ref
    assert name_gen == name_ref


def test_d2_wave_gating_topology_reachability():
    """Wave 2's lane_c is reachable only via wave 1's ACCEPTED edges."""
    parse_dot, _validate = _engine_or_skip()
    g = parse_dot(compile_plan(load_plan(PLAN_3LANE)))

    incoming = {}
    for e in g.edges:
        incoming.setdefault(e.to_node, []).append(e)

    # LaunchLaneC (wave 2) has exactly one predecessor: IntegrateB's ACCEPTED edge.
    lc_in = incoming["LaunchLaneC"]
    assert len(lc_in) == 1
    assert lc_in[0].from_node == "IntegrateB"
    assert lc_in[0].condition == "context.tool.last_line=ACCEPTED"

    # IntegrateB's only non-failure successor is LaunchLaneC (ACCEPTED), and
    # IntegrateA's is ParentVerifyB (ACCEPTED) -- wave 2 sits structurally behind
    # both wave-1 ACCEPTED edges.
    accepted = {
        (e.from_node, e.to_node)
        for e in g.edges
        if e.condition == "context.tool.last_line=ACCEPTED"
    }
    assert ("IntegrateA", "ParentVerifyB") in accepted
    assert ("IntegrateB", "LaunchLaneC") in accepted
    assert ("IntegrateC", "PreCoherenceAggregate") in accepted


# ----------------------------------------------------------------------------
# D3: generated output validates (zero ERROR diagnostics).
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("plan_path", [PLAN_3LANE, PLAN_2LANE])
def test_d3_generated_output_validates(plan_path):
    parse_dot, validate = _engine_or_skip()
    graph = parse_dot(compile_plan(load_plan(plan_path)))
    diagnostics = validate(graph)
    errors = [d for d in diagnostics if getattr(d, "severity", "") == "ERROR"]
    assert not errors, "engine reported ERROR diagnostics: " + "; ".join(
        f"[{d.rule}] {d.message}" for d in errors
    )


# ----------------------------------------------------------------------------
# Escaping round-trip: an intended tool_command survives DOT emission and
# engine re-parse unchanged (the correctness guarantee behind D2/D3).
# ----------------------------------------------------------------------------


def test_toolcommand_roundtrips_through_parse_dot():
    parse_dot, _validate = _engine_or_skip()
    g = parse_dot(compile_plan(load_plan(PLAN_3LANE)))

    pv = g.nodes["ParentVerifyA"].attrs.get("tool_command")
    # Real newlines (not literal backslash-n) after DOT unescaping.
    assert pv.startswith("#!/bin/sh\nset -e\n")
    # The lane's verifier argv is embedded as a Python literal, with the shell
    # command-substitution left intact (not mangled by engine $-substitution or
    # our escaping).
    assert "'/bin/sh', '-c'" in pv
    assert '"$(cat SMOKE_MARKER_lane_a.txt)"' in pv

    # Per-lane data-driven fields.
    assert "seeded_failure=true" in g.nodes["LaunchLaneB"].attrs.get("tool_command")
    assert "seeded_failure=false" in g.nodes["LaunchLaneA"].attrs.get("tool_command")
    # Cumulative + full aggregate loops are data-driven from the lane ids.
    assert "for f in lane_a lane_b;" in g.nodes["IntegrateB"].attrs.get("tool_command")
    assert "for f in lane_a lane_b lane_c;" in g.nodes[
        "PreCoherenceAggregate"
    ].attrs.get("tool_command")


def test_launch_forks_base_sha_in_wave1_and_head_in_later_wave():
    parse_dot, _validate = _engine_or_skip()
    g = parse_dot(compile_plan(load_plan(PLAN_3LANE)))
    # Wave-1 lane forks the immutable base SHA.
    assert 'commit_sha="$product_base_sha"' in g.nodes["LaunchLaneA"].attrs.get(
        "tool_command"
    )
    # Wave-2 lane forks the current integration HEAD (post wave-1 integration).
    lc = g.nodes["LaunchLaneC"].attrs.get("tool_command")
    assert "integration_head = subprocess.run" in lc
    assert "commit_sha=integration_head" in lc


def test_determinism_same_spec_same_output():
    spec = load_plan(PLAN_3LANE)
    assert compile_plan(spec) == compile_plan(spec)
