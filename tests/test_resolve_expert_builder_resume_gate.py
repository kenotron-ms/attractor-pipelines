"""Regression coverage for resolve_expert_builder's deterministic ResumeGate.

The routing unit tests execute the exact Python heredoc embedded in the DOT
node. The engine test then drives a minimal graph that copies the real node,
its ingress edge, and its four outgoing edges verbatim through parse_dot,
PipelineEngine, HandlerRegistry, and ToolHandler.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest
from amplifier_module_loop_pipeline.context import PipelineContext
from amplifier_module_loop_pipeline.dot_parser import parse_dot
from amplifier_module_loop_pipeline.engine import PipelineEngine
from amplifier_module_loop_pipeline.handlers import HandlerRegistry
from amplifier_module_loop_pipeline.handlers.context import HandlerContext
from amplifier_module_loop_pipeline.validation import validate

EXPERT_BUILDER_DOT = (
    Path(__file__).resolve().parent.parent
    / "pipelines"
    / "resolve_expert_builder"
    / "resolve_expert_builder.dot"
)
LANDINGS = ("VerifyPlan", "Synthesize", "Decompose", "AdmissionInit")
WORKER_FIRST_INTERPRETER_SHIM = (
    "PYTHON=$( [ -x /opt/uv-tools/amplifier/bin/python ] "
    "&& echo /opt/uv-tools/amplifier/bin/python "
    "|| echo python3 ); $PYTHON <<'PYEOF'"
)


def _content() -> str:
    return EXPERT_BUILDER_DOT.read_text(encoding="utf-8")


def _resume_gate_node_source() -> str:
    """Extract the complete ResumeGate DOT declaration from the real graph."""
    content = _content()
    start = content.find("\n    ResumeGate [\n")
    assert start >= 0, "Could not find ResumeGate node block"
    end = content.find("\n    ]", start)
    assert end >= 0, "Could not find ResumeGate node closing bracket"
    return content[start : end + len("\n    ]")]


def _resume_gate_python() -> str:
    """Extract ResumeGate's exact stdlib Python heredoc."""
    node_source = _resume_gate_node_source()
    marker = "<<'PYEOF'"
    start = node_source.find(marker)
    assert start >= 0, "Could not find ResumeGate Python heredoc"
    start += len(marker) + 1
    end = node_source.find("\nPYEOF", start)
    assert end >= 0, "Could not find ResumeGate Python heredoc terminator"
    return node_source[start:end]


def _resume_gate_edges() -> list[str]:
    """Return ResumeGate's four real outgoing edge declarations verbatim."""
    edges = [
        line
        for line in _content().splitlines()
        if line.strip().startswith("ResumeGate") and "->" in line
    ]
    assert len(edges) == 4, f"Expected exactly four ResumeGate edges, got {edges!r}"
    return edges


def _resume_gate_ingress_edge() -> str:
    """Return the real start-to-ResumeGate edge declaration verbatim."""
    edges = [
        line
        for line in _content().splitlines()
        if line.strip().startswith("start") and "-> ResumeGate" in line
    ]
    assert len(edges) == 1, f"Expected one ResumeGate ingress edge, got {edges!r}"
    return edges[0]


def _write_state(tmp_path: Path, state: str) -> None:
    ai_dir = tmp_path / ".ai"
    if state == "admitted":
        ai_dir.mkdir()
        (ai_dir / "outcome.txt").write_text("  admit  | complete  ", encoding="utf-8")
    elif state == "single_solution":
        _write_state(tmp_path, "admitted")
        solution = ai_dir / "hard_parts" / "slot_1" / "SOLUTION.md"
        solution.parent.mkdir(parents=True, exist_ok=True)
        solution.write_text("slot_1 solution", encoding="utf-8")
    elif state == "solutions":
        _write_state(tmp_path, "admitted")
        for slot in ("slot_1", "slot_2"):
            solution = ai_dir / "hard_parts" / slot / "SOLUTION.md"
            solution.parent.mkdir(parents=True, exist_ok=True)
            solution.write_text(f"{slot} solution", encoding="utf-8")
    elif state == "pieces":
        _write_state(tmp_path, "solutions")
        index = ai_dir / "pieces" / "INDEX.md"
        index.parent.mkdir()
        index.write_text("pieces", encoding="utf-8")
    elif state == "plan":
        _write_state(tmp_path, "pieces")
        index = ai_dir / "plan" / "INDEX.md"
        index.parent.mkdir()
        index.write_text("plan", encoding="utf-8")
    elif state != "fresh":
        raise ValueError(f"Unknown marker state: {state}")


def _run_resume_gate(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _resume_gate_python()],
        capture_output=True,
        check=False,
        cwd=tmp_path,
        text=True,
    )


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("fresh", "AdmissionInit"),
        ("admitted", "Decompose"),
        ("solutions", "Synthesize"),
        ("pieces", "Synthesize"),
        ("plan", "VerifyPlan"),
    ],
)
def test_resume_gate_routes_markers_by_descending_phase(
    tmp_path: Path, state: str, expected: str
) -> None:
    """The exact embedded script chooses the highest completed phase."""
    _write_state(tmp_path, state)

    result = _run_resume_gate(tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [expected]


def test_resume_gate_does_not_skip_unfavorable_admission(tmp_path: Path) -> None:
    for verdict in ("reject|lint", "escalate|unknown"):
        case_dir = tmp_path / verdict.partition("|")[0]
        ai_dir = case_dir / ".ai"
        ai_dir.mkdir(parents=True)
        (ai_dir / "admission.yaml").write_text(
            "written for every loop", encoding="utf-8"
        )
        (ai_dir / "outcome.txt").write_text(verdict, encoding="utf-8")

        result = _run_resume_gate(case_dir)

        assert result.returncode == 0, result.stderr
        assert result.stdout.splitlines() == ["AdmissionInit"]


def test_resume_gate_does_not_treat_admission_yaml_as_admitted(tmp_path: Path) -> None:
    ai_dir = tmp_path / ".ai"
    ai_dir.mkdir()
    (ai_dir / "admission.yaml").write_text("not a verdict", encoding="utf-8")

    result = _run_resume_gate(tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["AdmissionInit"]


def test_resume_gate_preserves_worker_first_interpreter_shim() -> None:
    node_source = _resume_gate_node_source()

    assert node_source.count(WORKER_FIRST_INTERPRETER_SHIM) == 1


def test_resume_gate_dot_structure_and_full_graph_validation() -> None:
    graph = parse_dot(_content())
    errors = [diagnostic for diagnostic in validate(graph) if diagnostic.severity == "ERROR"]

    assert not errors, "\n".join(str(error) for error in errors)
    assert "ResumeGate" in graph.nodes
    assert graph.nodes["ResumeGate"].shape == "parallelogram"
    assert all(
        edge.from_node != "start" or edge.to_node != "AdmissionInit"
        for edge in graph.edges
    )
    assert any(
        edge.from_node == "start" and edge.to_node == "ResumeGate"
        for edge in graph.edges
    )

    edges = [edge for edge in graph.edges if edge.from_node == "ResumeGate"]
    assert {(edge.to_node, edge.condition) for edge in edges} == {
        ("VerifyPlan", "context.tool.last_line=VerifyPlan"),
        ("Synthesize", "context.tool.last_line=Synthesize"),
        ("Decompose", "context.tool.last_line=Decompose"),
        ("AdmissionInit", "context.tool.last_line=AdmissionInit"),
    }
    assert all(edge.condition for edge in edges)


def _live_graph_source() -> str:
    """Build a graph from the real node and edge source plus simple landings."""
    node_source = _resume_gate_node_source()
    landing_nodes = "\n".join(
        f'    {landing} [shape=parallelogram, tool_command="printf \\"landed:{landing}\\\\n\\""]'
        for landing in LANDINGS
    )
    landing_edges = "\n".join(f"    {landing} -> done" for landing in LANDINGS)
    return "\n".join(
        [
            "digraph ResumeGateLive {",
            "    start [shape=Mdiamond]",
            "    done [shape=Msquare]",
            node_source,
            landing_nodes,
            _resume_gate_ingress_edge(),
            *(_resume_gate_edges()),
            landing_edges,
            "}",
        ]
    )


def test_live_graph_copies_resume_gate_source_verbatim() -> None:
    live_source = _live_graph_source()

    assert _resume_gate_node_source() in live_source
    assert _resume_gate_ingress_edge() in live_source
    assert all(edge in live_source for edge in _resume_gate_edges())


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("fresh", "AdmissionInit"),
        ("admitted", "Decompose"),
        ("single_solution", "Decompose"),
        ("solutions", "Synthesize"),
        ("pieces", "Synthesize"),
        ("plan", "VerifyPlan"),
    ],
)
def test_resume_gate_routes_through_real_pipeline_engine(
    tmp_path: Path, state: str, expected: str
) -> None:
    """Exercise the real parser, engine, registry, and ToolHandler end to end."""
    _write_state(tmp_path, state)
    graph = parse_dot(_live_graph_source())
    context = PipelineContext()
    context.set("context.target_dir", str(tmp_path))
    engine = PipelineEngine(
        graph=graph,
        context=context,
        handler_registry=HandlerRegistry(HandlerContext()),
        logs_root=str(tmp_path / "pipeline_logs"),
    )

    outcome = asyncio.run(engine.run())
    trace = " -> ".join([*engine.completed_nodes, "done"])
    print(f"VERBATIM_LIVE_ROUTE state={state} expected={expected} trace={trace}")

    assert outcome.is_success
    assert engine.completed_nodes == ["start", "ResumeGate", expected]
    assert context.get("tool.last_line") == f"landed:{expected}"
