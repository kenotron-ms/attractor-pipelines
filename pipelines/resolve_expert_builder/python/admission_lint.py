#!/usr/bin/env python3
# Ported verbatim from microsoft/amplifier-resolver-dot-graph's
# src/amplifier_resolver_dot_graph/admission/lint.py + admission/__init__.py.
# Reference only -- see resolve_expert_builder.md for why this is not directly
# runnable in this repo (it still imports as amplifier_resolver_dot_graph.admission.lint).
#
# Source package docstring (admission/__init__.py):
#   "Autonomous admission gate: deterministic lint + descent router."
"""Deterministic admission lint + descent router.

Reads `.ai/admission.yaml`, validates it against the admission schema and the
citation rules, counts unresolved items, compares that count against the
previous pass, and emits exactly one routing sentinel as its LAST stdout line:

    admit | enrich | escalate | reject

Routing is on DESCENT, not on a revision budget:

    open_count == 0                     -> admit
    open_count dropped since last pass  -> enrich
    open_count did not drop (stall)     -> escalate   (first stall in this run)
    stall, and already escalated once   -> reject

The pass-cap is a runaway guard, NOT the termination mechanism. If it fires it
is reported as such.

Side effects (all under `.ai/`):
    .ai/admission/NN.yaml       append-only snapshot of each pass
    .ai/admission/state.json    pass counter, previous open_count, escalations
    .ai/admission_report.md     violations + open items, read by the next pass
    .ai/escalation.md           question set, written only on `escalate`

Stdlib + PyYAML only. Always exits 0 so the engine routes on the sentinel
rather than on the process exit code.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

import yaml

VALID_SOURCES = ("stated", "entailed", "repo", "convention")
# Sources whose citation must resolve to a real file on disk. This is what
# makes "the answer already existed" mechanically checkable rather than
# assertable, and is the whole discriminator between a repo-backed run and a
# greenfield one.
FILE_BACKED_SOURCES = ("repo", "convention")

ADMISSION_FILE = ".ai/admission.yaml"
HISTORY_DIR = ".ai/admission"
STATE_FILE = ".ai/admission/state.json"
REPORT_FILE = ".ai/admission_report.md"
ESCALATION_FILE = ".ai/escalation.md"


@dataclass
class Result:
    violations: list[str] = field(default_factory=list)
    blocking: list[dict[str, Any]] = field(default_factory=list)
    criteria_count: int = 0
    assumptions_count: int = 0
    regime: str = "unknown"

    @property
    def open_count(self) -> int:
        """The single descent metric: everything still unresolved.

        Violations and blocking unknowns are both things a further pass is
        supposed to reduce, so they share one number. A criterion that cites
        nothing is spec-writing; a blocking unknown is an honest gap. Both
        must go down.
        """
        return len(self.violations) + len(self.blocking)


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


# Matches a trailing line-number suffix: `:N` (a single line) or `:N-M` (a
# range). Anything else after the last colon (prose, a Windows drive letter,
# a non-digit range) is left alone and treated as part of the path.
_LINE_SUFFIX_RE = re.compile(r"^(?P<start>\d+)(?:-(?P<end>\d+))?$")

# Citations are sometimes written as a full GitHub URL rather than a
# repo-relative path -- an LLM asked to cite the repo will often just quote
# the URL it saw the request or a doc reference written as. Both shapes name
# a real path inside the same repo the engine already has checked out
# locally; only the scheme/host/owner/repo/ref segments need stripping to
# recover the repo-relative path underneath.
_GITHUB_BLOB_RE = re.compile(
    r"^https?://github\.com/[^/]+/[^/]+/blob/[^/]+/(?P<path>.+)$"
)
_RAW_GITHUBUSERCONTENT_RE = re.compile(
    r"^https?://raw\.githubusercontent\.com/[^/]+/[^/]+/[^/]+/(?P<path>.+)$"
)


def _strip_known_url_prefix(path: str) -> str:
    """Reduce a recognized GitHub blob/raw URL to its repo-relative path.

    Any other string (a plain repo-relative path, or a URL shape we don't
    recognize) passes through unchanged.
    """
    for pattern in (_GITHUB_BLOB_RE, _RAW_GITHUBUSERCONTENT_RE):
        match = pattern.match(path)
        if match:
            return match.group("path")
    return path


def _resolve_citation(citation: str, repo_root: str | None) -> str | None:
    """Return None if the citation resolves, else a human-readable reason.

    Accepts a bare `path`, `path:line`, or `path:start-end`. `path` itself
    may be a repo-relative path, a `github.com/.../blob/...` URL, or a
    `raw.githubusercontent.com/...` URL for the same repo -- all three name
    a file the engine can check on disk once the URL wrapping is stripped.
    Resolution is attempted relative to the repo root when one is supplied.
    """
    raw = citation.strip()
    line_no: int | None = None
    end_line_no: int | None = None
    path = raw

    # Split a trailing :N or :N-M, but only when the tail matches a line
    # spec -- Windows drive letters and prose colons must not be mistaken
    # for one.
    if ":" in raw:
        head, _, tail = raw.rpartition(":")
        match = _LINE_SUFFIX_RE.match(tail)
        if head and match:
            path = head
            line_no = int(match.group("start"))
            end_group = match.group("end")
            end_line_no = int(end_group) if end_group else None

    path = _strip_known_url_prefix(path)

    # Resolution is confined to the supplied repo root. There is deliberately
    # no independent working-directory fallback here: a citation that
    # resolves against whatever directory the run happens to start in,
    # unconnected to any supplied repo, is unfalsifiable. No repo supplied
    # means no repo evidence. (main()'s CLI handling may itself resolve a
    # non-path repo identifier to the working directory before it ever
    # reaches this function -- that is a repo being supplied, not a fallback
    # around one being absent.)
    candidates = [os.path.join(repo_root, path)] if repo_root else []

    for candidate in candidates:
        if os.path.isfile(candidate):
            if line_no is None:
                return None
            try:
                with open(candidate, encoding="utf-8", errors="replace") as handle:
                    total = sum(1 for _ in handle)
            except OSError as exc:  # pragma: no cover - unreadable file
                return f"could not read {candidate}: {exc}"
            last_line = end_line_no if end_line_no is not None else line_no
            if last_line <= total:
                return None
            span = (
                f"{line_no}-{end_line_no}" if end_line_no is not None else str(line_no)
            )
            return f"{path}:{span} out of range (file has {total} lines)"

    where = (
        f" (searched repo root {repo_root!r})"
        if repo_root
        else " (no repo supplied)"
    )
    return f"{path!r} does not resolve to a file{where}"


def lint(doc: Any, repo_root: str | None) -> Result:
    result = Result()

    if not isinstance(doc, dict):
        result.violations.append("admission.yaml does not parse as a YAML mapping")
        return result

    regime = doc.get("regime")
    if regime in ("greenfield", "feature"):
        result.regime = regime
    else:
        result.violations.append(
            f"regime must be 'greenfield' or 'feature' (got {regime!r})"
        )

    if not _is_nonempty_str(doc.get("request")):
        result.violations.append("request is missing or empty")

    # ---- criteria ----------------------------------------------------------
    criteria = doc.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        result.violations.append("criteria must be a non-empty list")
        criteria = []
    result.criteria_count = len(criteria)

    seen_ids: set[str] = set()
    for index, item in enumerate(criteria):
        label = f"criteria[{index}]"
        if not isinstance(item, dict):
            result.violations.append(f"{label} is not a mapping")
            continue

        cid = item.get("id")
        if not isinstance(cid, str) or not cid.strip():
            result.violations.append(f"{label} has no id")
        else:
            label = f"criterion {cid}"
            if cid in seen_ids:
                result.violations.append(f"{label} duplicate id")
            seen_ids.add(cid)

        if not _is_nonempty_str(item.get("text")):
            result.violations.append(f"{label} has no text")

        source = item.get("source")
        if source not in VALID_SOURCES:
            # There is deliberately no 'invented' value. A criterion that
            # cannot name one of these sources has nowhere to go, which is
            # exactly the intended failure for scope expansion.
            result.violations.append(
                f"{label} source {source!r} not in {list(VALID_SOURCES)}"
            )
            continue

        citation = item.get("citation") or ""
        if source == "stated":
            continue

        if not _is_nonempty_str(citation):
            result.violations.append(
                f"{label} source '{source}' requires a non-empty citation"
            )
            continue

        if source in FILE_BACKED_SOURCES:
            reason = _resolve_citation(citation, repo_root)
            if reason:
                result.violations.append(
                    f"{label} source '{source}' citation does not resolve: {reason}"
                )

    # ---- blocking unknowns -------------------------------------------------
    blocking = doc.get("blocking_unknowns") or []
    if not isinstance(blocking, list):
        result.violations.append("blocking_unknowns must be a list")
        blocking = []

    seen_bids: set[str] = set()
    for index, item in enumerate(blocking):
        label = f"blocking_unknowns[{index}]"
        if not isinstance(item, dict):
            result.violations.append(f"{label} is not a mapping")
            continue
        bid = item.get("id")
        if not isinstance(bid, str) or not bid.strip():
            result.violations.append(f"{label} has no id")
        else:
            label = f"blocking unknown {bid}"
            if bid in seen_bids:
                result.violations.append(f"{label} duplicate id")
            seen_bids.add(bid)
        if not _is_nonempty_str(item.get("text")):
            result.violations.append(f"{label} has no text")
        if not _is_nonempty_str(item.get("why_blocking")):
            result.violations.append(f"{label} has no why_blocking")
        result.blocking.append(item)

    # ---- assumptions -------------------------------------------------------
    assumptions = doc.get("assumptions") or []
    if not isinstance(assumptions, list):
        result.violations.append("assumptions must be a list")
        assumptions = []
    for index, item in enumerate(assumptions):
        if not isinstance(item, dict):
            result.violations.append(f"assumptions[{index}] is not a mapping")
            continue
        if not _is_nonempty_str(item.get("id")):
            result.violations.append(f"assumptions[{index}] has no id")
        if not _is_nonempty_str(item.get("text")):
            result.violations.append(f"assumptions[{index}] has no text")
    result.assumptions_count = len(assumptions)

    return result


def route(
    open_count: int,
    prev_open: int | None,
    escalations: int,
    passes: int,
    max_passes: int,
) -> tuple[str, str]:
    """Return (sentinel, reason)."""
    if open_count == 0:
        return "admit", "no violations and no blocking unknowns"

    if passes >= max_passes:
        return (
            "escalate",
            (
                f"runaway guard: pass cap {max_passes} reached with {open_count} "
                "open item(s); this is a safety net, not the descent rule"
            ),
        )

    if prev_open is None:
        return "enrich", f"first pass, {open_count} open item(s) to work on"

    if open_count < prev_open:
        return (
            "enrich",
            f"descending: open items {prev_open} -> {open_count}",
        )

    if escalations >= 1:
        return (
            "reject",
            (
                f"stalled at {open_count} open item(s) after an escalation "
                f"(previous pass had {prev_open})"
            ),
        )

    return (
        "escalate",
        f"stalled: open items {prev_open} -> {open_count}, no descent",
    )


def _write_report(
    path: str, result: Result, sentinel: str, reason: str, passes: int
) -> None:
    lines = [
        "# Admission lint report",
        "",
        f"- pass: {passes}",
        f"- verdict: **{sentinel}** ({reason})",
        f"- regime: {result.regime}",
        f"- criteria: {result.criteria_count}",
        f"- assumptions: {result.assumptions_count}",
        (
            f"- open items: {result.open_count} "
            f"({len(result.violations)} violation(s) + {len(result.blocking)} blocking unknown(s))"
        ),
        "",
    ]

    lines.append("## Violations -- fix these first")
    lines.append("")
    if result.violations:
        lines += [f"{n}. {v}" for n, v in enumerate(result.violations, 1)]
    else:
        lines.append("None.")
    lines.append("")

    lines.append(
        "## Blocking unknowns -- resolve with a citable source, or keep and justify"
    )
    lines.append("")
    if result.blocking:
        for item in result.blocking:
            bid = item.get("id", "?")
            text = item.get("text", "")
            why = item.get("why_blocking", "")
            lines.append(f"- **{bid}**: {text}")
            lines.append(f"  - why blocking: {why}")
    else:
        lines.append("None.")
    lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _write_escalation(path: str, result: Result, reason: str) -> None:
    lines = [
        "# Escalation -- admission cannot proceed without answers",
        "",
        f"Reason: {reason}",
        "",
        "The graph could not resolve the following from the request, from what the",
        "term entails, or from any citable repo or convention evidence. Answer these",
        "and resubmit; the prior admission state is preserved under `.ai/admission/`.",
        "",
        "## Questions",
        "",
    ]
    if result.blocking:
        for n, item in enumerate(result.blocking, 1):
            lines.append(f"{n}. {item.get('text', '')}")
            lines.append(
                "   - why this blocks writing acceptance criteria: "
                + str(item.get("why_blocking", ""))
            )
    else:
        lines.append("(No blocking unknowns were declared.)")
    lines.append("")

    if result.violations:
        lines.append("## Unresolved lint violations at the point of escalation")
        lines.append("")
        lines += [f"- {v}" for v in result.violations]
        lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Admission lint + descent router")
    parser.add_argument("--repo", default="", help="path to the target repo, if any")
    parser.add_argument("--max-passes", type=int, default=6, help="runaway guard")
    parser.add_argument("--admission-file", default=ADMISSION_FILE)
    args = parser.parse_args(argv)

    repo_root = args.repo.strip() or None
    if repo_root is not None and not os.path.isdir(repo_root):
        # A repo WAS requested (--repo was non-empty) but it does not name an
        # existing directory. This is a WIRING error, not a greenfield run:
        # the caller is responsible for handing lint the path of an
        # already-staged repo (a reconciliation node in expert_builder.dot
        # supplies the validated staged path). Do NOT silently degrade to
        # repo_root=None -- that would make a mis-wired caller
        # indistinguishable from an honest greenfield run ("no repo
        # supplied") and let repo-backed citations quietly fail to resolve.
        # Fail LOUD with a distinct message so the mistake is visible.
        print(
            f"ERROR: repo path {repo_root!r} is not a staged directory; "
            "lint expects --repo to name an already-staged repo checkout. "
            "This is a caller wiring error, not a greenfield run "
            "(an absent repo is expressed by omitting --repo, not by "
            "pointing it at a missing path).",
            file=sys.stderr,
        )
        return 2

    os.makedirs(HISTORY_DIR, exist_ok=True)

    state: dict[str, Any] = {"passes": 0, "prev_open": None, "escalations": 0}
    if os.path.isfile(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as handle:
                state.update(json.load(handle))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"note: state unreadable ({exc}); starting fresh", file=sys.stderr)

    doc: Any = None
    parse_error: str | None = None
    if not os.path.isfile(args.admission_file):
        parse_error = f"{args.admission_file} was not written"
    else:
        try:
            with open(args.admission_file, encoding="utf-8") as handle:
                doc = yaml.safe_load(handle)
        except (OSError, yaml.YAMLError) as exc:
            parse_error = f"{args.admission_file} could not be parsed: {exc}"

    if parse_error:
        result = Result(violations=[parse_error])
    else:
        result = lint(doc, repo_root)

    passes = int(state["passes"]) + 1
    prev_open = state["prev_open"]
    escalations = int(state["escalations"])

    sentinel, reason = route(
        result.open_count, prev_open, escalations, passes, args.max_passes
    )

    if sentinel == "escalate":
        escalations += 1
        _write_escalation(ESCALATION_FILE, result, reason)

    # Append-only per-pass snapshot: the descent record, readable after the run.
    snapshot = {
        "pass": passes,
        "open_count": result.open_count,
        "prev_open": prev_open,
        "violations": result.violations,
        "blocking_unknowns": [i.get("id") for i in result.blocking],
        "criteria_count": result.criteria_count,
        "regime": result.regime,
        "verdict": sentinel,
        "reason": reason,
    }
    with open(
        os.path.join(HISTORY_DIR, f"{passes:02d}.yaml"), "w", encoding="utf-8"
    ) as handle:
        yaml.safe_dump(snapshot, handle, sort_keys=False)

    with open(STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "passes": passes,
                "prev_open": result.open_count,
                "escalations": escalations,
            },
            handle,
        )

    _write_report(REPORT_FILE, result, sentinel, reason, passes)

    # Diagnostics on stderr so they cannot pollute the routing sentinel.
    print(
        f"[admission_lint] pass={passes} open={result.open_count} prev={prev_open} "
        f"violations={len(result.violations)} blocking={len(result.blocking)} "
        f"verdict={sentinel} reason={reason}",
        file=sys.stderr,
    )
    for violation in result.violations:
        print(f"[admission_lint]   violation: {violation}", file=sys.stderr)

    # LAST stdout line is the routing signal.
    print(sentinel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
