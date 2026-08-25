"""Unit tests for scripts/dot_to_mermaid.py.

Falsifiable checks on the deterministic DOT -> Mermaid renderer: shape mapping,
edge-condition labelling, the ``!=''`` catch-all -> ``else`` rule, label
escaping, and the ``<->``-in-a-label anti-false-match guard.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import dot_to_mermaid as d  # pyright: ignore[reportMissingImports]


def test_shapes_and_plain_edge() -> None:
    src = """
    digraph G {
      Start [shape=Mdiamond, label="Start"];
      Gate  [shape=parallelogram, label="Gate"];
      Start -> Gate;
    }
    """
    out = d.dot_to_mermaid(src)
    assert out.startswith("flowchart TD\n")
    assert '  Start(["Start"])' in out
    assert '  Gate[/"Gate"/]' in out
    assert "  Start --> Gate" in out


def test_condition_labels_and_else() -> None:
    src = """
    A [shape=parallelogram, label="A"];
    B [shape=box, label="B"];
    C [shape=box, label="C"];
    A -> B [condition="context.tool.last_line=PASS", weight="2"];
    A -> C [condition="context.tool.last_line!=PASS"];
    A -> C [condition="context.tool.last_line!=''"];
    """
    out = d.dot_to_mermaid(src)
    assert "  A -->|PASS| B" in out
    assert "  A -->|\u2260 PASS| C" in out
    assert "  A -->|else| C" in out


def test_label_with_angle_brackets_is_escaped_not_an_edge() -> None:
    # The "<->" inside the label must NOT be parsed as an edge, and the angle
    # brackets must be HTML-escaped so Mermaid does not choke.
    src = 'N [shape=parallelogram, label="Check Plan<->DOT Correspondence"];'
    out = d.dot_to_mermaid(src)
    assert "&lt;-&gt;" in out
    assert "-->" not in out  # no spurious edge produced from the label


def test_multiline_node_declaration() -> None:
    src = """
    Wave1Launch [
      shape=component,
      label="Wave 1: Launch"
    ];
    Wave1Collect [
      shape=tripleoctagon,
      label="Wave 1: Collect"
    ];
    Wave1Launch -> Wave1Collect;
    """
    out = d.dot_to_mermaid(src)
    assert '  Wave1Launch[["Wave 1: Launch"]]' in out
    assert '  Wave1Collect{{"Wave 1: Collect"}}' in out


def test_deterministic() -> None:
    src = 'A [shape=box, label="A"];\nB [shape=box, label="B"];\nA -> B;'
    assert d.dot_to_mermaid(src) == d.dot_to_mermaid(src)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
