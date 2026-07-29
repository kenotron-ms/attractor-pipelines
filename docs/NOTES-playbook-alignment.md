# Playbook "Shape Work as an Attractor" vs StrongDM NLSpec — Alignment Analysis

Captured 2026-07-28. Source doc: `agent-building-playbook/patterns/shape-work-as-an-attractor.md`.
Cross-checked by attractor-expert (resumed session) against both repos.

## Verdict: strong alignment — and it's the missing manifesto

The pattern does not stray from the nlspec; it sits **upstream** of it. StrongDM's spec
answers "how do I build a loop" (mechanics: goal gates, retry_target, edge selection).
The playbook pattern answers "what property must the whole graph have" (topology:
correct outcome = stable equilibrium; judge by convergence, not step completion).

Notably: the StrongDM repo **never explains its own name** — zero occurrences of
basin/converge/dynamical language. The dynamical-systems reading we'd been treating as
inference is independently articulated here, with theoretical grounding
(Tacheny, arXiv:2512.10350 — iterative LLM systems as discrete dynamical systems) and
empirical support (Bricknell, LessWrong 2026 — LLM outputs cluster into stable attractor
regions). **This pattern is effectively the missing README of both attractor repos.**

## What the pattern ADDS that neither repo articulates

All confirmed by the expert against both codebases:

### 1. Differentiated failure-class edges → DIFFERENT fix-phases
The playbook enumerates distinct corrective edges per perturbation class:
- review failure → back to implementation
- failing test → **diagnosis** (not a blind patch)
- discovered contradiction → **spec revision** (the spec itself is mutable state in the basin!)
- uncertainty threshold → human escalation (an edge of the bowl, not an exit)
- repeated failure → **postmortem** (not unbounded retry)

The bundle has only `retry_target` (a single scalar) + `fallback_retry_target` + one
back-edge. No failure taxonomy exists anywhere. "Contradiction → spec revision" has no
DOT expression at all. **Insight: the basin has multiple walls; route each failure class
back to the phase that can fix it — not just "back."**

### 2. The rim-coverage question (completeness check)
"Does every plausible way this can go wrong have an edge that bends it back — or are
there failures that simply run off the rim?" This is a design-review discipline beyond
our three-question test: enumerate plausible failure modes → verify each has a
corrective edge. See NOTES-bundle-misses.md for where the shipped engine's rim actually
leaks (subgraphs/parallel branches + dead conditional edges).

### 3. Idempotency widens the basin
Idempotent + resumable steps = re-running converges instead of compounding = wider
basin, more stable equilibrium. The nlspec has checkpoint/resume as crash-recovery
plumbing; it never frames idempotency as a *basin-width* property. (Bundle moved the
wrong way: removed engine-level resume, offloaded to authors with no primitive.)

### 4. The root-cause anti-pattern (loop absorbing deterministic bugs)
"An attractor absorbs model drift, not broken tools or specs." If a feedback edge keeps
"recovering" from the same deterministic failure, the loop is papering over a bug that
should be fixed. Genuinely new caution — absent from bundle docs and the expert's own
prior briefing. Playbook has `fix-the-root-cause.md`; bundle has no analogue.

### 5. Convergence regimes: contractive / oscillatory / exploratory
From Tacheny: loops can converge to attractors, **oscillate** (ping-pong between two
wrong answers), or wander (random walk) — and **prompt design directly controls the
regime**. Two consequences:
- A new failure class beyond "doesn't converge": oscillation without descent.
- Prompting affects the convergence *regime*, not just per-step quality.
The engine has zero regime vocabulary; all three regimes look identical at runtime
(repeated node executions until a cap).

### Expert's four extensions beyond my list

**6. The perturbation reframe — wrong-but-plausible vs loud failure.** The bundle's
enormous fail-loud investment (fail-fast, raises, contract violations) catches only
failures that *announce themselves*. The attractor premise is the other class: a step
that reports SUCCESS while producing a wrong-but-plausible artifact. Fail-loud machinery
is structurally blind to it. **Fail-loud is necessary and insufficient; the bundle
mistook it for the whole job.** (The dead-gate bug in the bundle's own examples is
exactly this failure class — it shipped with a green test suite.)

**7. Basin WIDTH — convergence "from a wide range of starting points."** Every bundle
pipeline assumes a clean, well-formed start. No robustness notion for bad initial
conditions (half-done work, dirty tree, misread goal). Width is half the definition of
an attractor; entirely missing.

**8. Bounded budget as ESCALATION, not termination.** Playbook: repeated failure →
postmortem. Bundle: caps produce `FAIL: exceeded 200 steps` — a fuse, not a decision
point. No postmortem-node pattern, no escalate-on-budget-exhaustion exemplar.
**A cap is a fuse; a budget is a decision point.**

**9. "Judge by convergence" is a MEASUREMENT claim.** The pattern redefines the success
metric. The bundle's only success notion is terminal `Outcome.status`; no measured
convergence property exists anywhere in the codebase.

## Adjacent playbook insight (scope-and-expire-memory)

Attractors in the BAD sense: stale memories become attractors — early ideas crowd out
new directions (stagnation, context poisoning). Tension with "feedback must
accumulate": an append-only `.ai/feedback/` channel can itself become a stagnation
attractor / context sludge. **Discipline: accumulated critique must be curated — the
convergence-factory's "write the SINGLE highest-leverage next change" is implicitly this
guard. Feedback channels need consolidation/expiry, not unbounded append.**

## Additions to our working doctrine

1. Enumerate failure classes per pipeline; give each its own back-edge to the phase
   that can fix it (including spec-revision and postmortem destinations).
2. Rim-coverage review as a standard design gate (mechanizable — see misses notes).
3. Design work nodes idempotent; treat resumability as basin width, not crash plumbing.
4. Watch for loops absorbing deterministic bugs — a corrective edge firing repeatedly
   on the same signature = fix the root cause instead.
5. Instrument for regime, not just termination: is iteration N better than N−1?
   Descending, oscillating, or wandering? (Requires per-iteration records.)
6. Prompt for the contractive regime: goal-responsibility + read-prior-critique, not
   position-in-script responsibility.
7. Curate the feedback channel; cap it at highest-leverage findings.
8. Budget exhaustion routes to a postmortem/human node, never a bare FAIL.
