# amplifier-bundle-attractor — The Misses (Gap vs Potential)

Captured 2026-07-28. Source: attractor-expert (resumed session
`0000000000000000-91c3f8ab75694a91_attractor-expert`), which **ran the shipped engine
against its own examples** — findings below marked "verified" are empirical probes,
not doc reading.

## One-sentence version

> The bundle is an **excellent implementation of the spec** and a **poor teacher of
> the idea** — and the gap is measurable: 12 of 24 example graphs have no cycle, 8 of
> the remaining 12 have a *provably dead* corrective edge, 1 accumulates feedback, and
> the engine cannot tell you whether iteration N beat N−1 because it overwrites N−1.
> The team built the marble, the bowl's mathematics, and a very good alarm for when
> the marble is dropped — but shipped a **flat table with a bowl painted on it**, and
> no instrument that measures height.

---

## Part 0: Two verified corrections to our prior understanding

### Correction 1 — "silent SUCCESS on no matching edge" is half-true; the source-of-truth doc is stale
`context/engine-semantics.md:93` claims no-edge + non-FAIL → branch terminates
SUCCESS. **Verified false for the main loop**: since commit `5ae3118` (#66,
2026-06-22) the main engine hard-fails loudly (`engine.py:773`,
`PIPELINE_ERROR`/`no_matching_edge`). The doc predates the change by 5 days and was
never updated — **the doc that exists specifically to out-rank stale spec prose has
itself drifted.**

BUT `run_subgraph` (`engine.py:915`) still returns the last outcome — verified: a
parallel branch that dead-ends **reports SUCCESS**. So the rim hole is real, re-aimed:
**the engine has two routing implementations with different fail semantics, and the
permissive one is the compositional one** (parallel branches, `folder` subgraphs,
`house` manager children) — exactly the layer manager stacks depend on.

### Correction 2 — THE finding: 8 of 24 shipped examples have DEAD corrective edges (verified)
Every `practical/` pipeline gates with `shape=diamond` + `outcome=` conditions.
`ConditionalHandler` (`handlers/conditional.py:47`) **unconditionally returns
SUCCESS**, discarding the upstream outcome. Combined with FAIL fail-fast:

| upstream returns | actual behavior |
|---|---|
| FAIL | fail-fast → gate never executes → pipeline terminates |
| PARTIAL_SUCCESS | gate overwrites with its own SUCCESS → routes to done (**reports success with failing tests**) |
| SUCCESS | routes to done (correct by accident) |

**The `outcome!=success` back-edge is unreachable in every one of these graphs.**
Affected: practical/bug-fix, feature-build, refactor, test-gen,
03-conditional-routing (the tutorial that TEACHES routing), 09-manager-supervisor,
10-full-attractor, 12-graph-resume.

`convergence-factory.dot` works correctly (verified: generate ran 3x, feedback 2x)
because it routes on `context.preferred_label`, not `outcome=` through a diamond.

**The headline examples are drawn as attractors and execute as flowcharts. The
back-edges are decoration.** This is also a live demonstration of the
wrong-but-plausible failure class: it shipped with a green test suite because the
pipelines "complete successfully."

---

## Part 1: Misses vs the StrongDM aspiration

**a1. "Software factory" ported as vocabulary, not capability.** What shipped is a
job runner: one graph, one run, temp-dir logs, no run index, no cross-run anything.
A factory implies many runs, a product line, yield metrics, accumulation.
*Could be:* run registry (`~/.attractor/runs/`), pipeline library with provenance,
per-pipeline yield stats. *Cost:* small.

**a2. Headless engine shipped; the frontends never did.** 21 typed events, hook
bridge, aggregator — faithful to spec §9.6. But `tool-dashboard-query` is an HTTP
client for a server that doesn't exist in-repo; spec §9.5's nine endpoints: none
implemented. *Why it matters:* **convergence is a temporal property — you can't see
it in a scrolling log. The absent frontend is why nobody noticed the dead edges.**
*Could be:* single-file SSE + static HTML viewer over existing events (~300 lines,
80% of value). The React SPA is a trap. *Cost:* days.

**a3. Manager stacks: recursive vision, non-recursively implemented.** `house` is
experimental; example 09 has zero parallelogram nodes AND a dead corrective edge;
example 11 is known-failing (interviewer doesn't thread through the manager); manager
children run through the permissive `run_subgraph` path. "Factories supervising
factories" is the aspiration and it's the layer where basin guarantees are weakest.
*Cost:* medium; prerequisite for the factory story.

**a4. NLSpec regenerability quietly abandoned.** 23 extensions, behavioral
divergences — and no updated spec. Regenerating from `attractor-spec.md` today gives
you a different system than what ships. `engine-semantics.md` is a manually-synced
delta list, and per Correction 1 it drifts. *Could be:* regenerate spec from
implementation as a build step, or drop the claim honestly. Doing neither is what
produced the stale doc.

## Part 2: Does the bundle TEACH the attractor concept? No. (verified census)

```
24 example graphs; 12 acyclic; of the 12 cyclic, 8 close the cycle with a DEAD edge.
Working convergence loops shipped: 2 (convergence-factory, conversational-gate) —
both filed under patterns/ as "snippets."
Graphs using loop_restart (accumulating feedback): 1
Graphs using tool_command (mechanical gates): 3
```

**b1. Teaching order inverts the design order.** Docs say design the gate first;
tutorials go linear → linear+goal_gate → conditional-routing (dead edge) → first real
loop at 04. A reader who stops at 03 learns "attractor = flowchart with shapes."
*Fix:* tutorial 01 IS the convergence loop (attempt → mechanical gate → back-edge,
4 nodes); everything else is variation. *Cost:* cheap, enormous leverage.

**b2. convergence-factory.dot is buried and mislabeled** — it's not a snippet, it's
THE shape. *Fix:* promote to `00-the-shape.dot` + first code block in README.

**b3. Docs preach evidence-based routing; examples do the opposite.** AP-2 warns at
length against LLM-typed routing sentinels; then 15 of 18 pipelines route on
`outcome=` and 8 are broken because of it. **The anti-pattern catalog documents the
exact mistake the examples make.** *Fix:* convert practical examples to parallelogram
gates — same edit as the Correction-2 fix.

**b4. Prompts teach position-responsibility** ("Stage 3: implement the fix...") not
goal-responsibility ("Advance $goal; read .ai/feedback/; code will verify"). Only
convergence-factory prompts for the contractive regime.

## Part 3: Missing mechanisms the concept demands

**c1. Feedback accumulation is a convention, not a mechanism (verified).**
`.ai/feedback/` exists only as prose in two prompt strings of one example. The engine
doesn't know it exists. If the generator forgets to read it, iteration N+1 is an
independent coin flip — an infinite loop with a nicer name.
*Could be:* first-class `feedback_from="node_id"` attribute — engine collects that
node's output per iteration and injects prior critiques with iteration numbering.
Convention → contract. *Cost:* ~150 lines. **Highest mechanism-value-per-line.**

**c2. Zero convergence observability (verified).** `iteration_N/` dirs are created
and never written; node status goes to a shared path so **each iteration destroys the
previous record** — after 10 iterations you have 1 data point. `$iteration`/`$attempt`
are not substituted in prompts. "Is N better than N−1?" is not hard — it's
*impossible*. Gates every regime/descent/oscillation question.
*Could be:* per-iteration status dirs, `$iteration` substitution, `convergence.jsonl`
scalar per iteration, `attractor trace <run>` printing the descent curve.
*Cost:* ~1 day. **Unlocks c3, c4, c7.**

**c3. No oscillation detection — despite the codebase containing one.** `loop-agent`
ships `LoopDetector` (period-1/2/3 repeat detection); the pipeline engine never
lifted it a level. Period-2 oscillation (two models disagreeing forever) burns to the
step cap indistinguishable from progress. *Cost:* small, after c2.

**c4. No basin/rim-coverage lint.** 14 lint rules, all structural, none topological:
no "graph has a cycle" check, no rim coverage (every non-terminal node's failure
route defined), no **statically-unreachable conditional edge** detection (would have
caught all 8 dead edges), no "loop has deterministic exit predicate," no "exit gated
on evidence." Also: **the CLI has only `run` and `doctor` — you cannot validate a
graph without running it.** *Could be:* ~200 lines of rules + `attractor lint`.
Mechanizes the playbook's rim-coverage question. *Cost:* ~2 days, best ratio here.

**c5. run_subgraph permissive fail semantics** (Correction 1). Unify or document.

**c6. No gate-primitive library.** Gates are the load-bearing element; authors
hand-write `pytest -q && printf green || printf red` or reach for the diamond
foot-gun. *Could be:* `gates/*.dot` snippets (a day); `gate="pytest"` sugar (a week).

**c7. No cross-run learning.** Nothing reads prior runs; 50 runs = 50 independent
samples. The team does this analysis manually (RECURRING-BUG-CLASSES.md) — the
system can't. *Cost:* real, but small first version after c2.

## Part 4: Misses vs the Amplifier ecosystem

**d1. "Consult the expert" is a workaround presented as a feature.** Mandatory
expert consultation is a tax levied because the artifact is hard to get right — and
the enforcement already failed (the dead-edge bug lives in the examples the expert
points at). *Could be:* `attractor new <name> --pattern convergence` scaffolding the
7-node reference shape; `attractor lint` at author time; `graph [profile="convergence"]`
making evidence-gated exit the default (opt-OUT). **Make the right shape the easy
shape.** *Cost:* ~1 week; retires most of the friction doc.

**d2. Zero composition with skills/knowledge/delegation.** References no foundation
skills; no authoring skill exists; nodes can't load_skill; nothing writes to team
knowledge. A faithful port that never got naturalized into the ecosystem.

**d3. Recipes-vs-attractor answered by capability list, not shape.** The real rule —
"recipes = staged sequential + human approval; attractor = machine-verified
convergence; **no cycle → should have been a recipe**" — appears nowhere. Which is
why 12 of 24 shipped examples are acyclic: *they should have been recipes.*
*Cost:* one paragraph + an acyclic-lint warning. Nearly free.

## Part 5: Everything else

**e1. Checkpoint that doesn't resume.** Written after every node, read by nothing.
200-step cap + non-resumability = a long convergence run that trips the cap **loses
everything**. Resume was reassigned to a graph pattern requiring 5 hand-rolled guard
nodes (exactly the playbook's "idempotency widens the basin," offloaded to authors
with no primitive). *Fix:* `attractor run --resume` (~a day) or delete the checkpoint
(honest). Writing a file nothing reads is the worst of both.

**e2. Remote pipelines: infrastructure for a library that doesn't exist.** git+https
DOT fetching with content-addressed caching shipped; no registry/index/published set.
*Fix:* an in-repo `pipelines/` index is nearly free.

**e3. `attractor doctor` checks the environment, not the pipeline** — aimed at the
wrong target given the failure mode is silent wrongness.

**e4. Model stylesheets: mechanism without doctrine.** No guidance on tier placement.
Playbook doctrine: **the expensive model belongs in the GATE** — gate quality
determines basin depth; generator quality only affects iteration count. Stylesheet
examples route by node name, not role. Nearly free to fix; changes how money is spent.

---

## Leverage ranking

**Tier 0 — correctness of the teaching material (do this week)**
1. Fix the 8 dead corrective edges (diamond+`outcome=` → parallelogram+`tool.last_line`) — days
2. Fix stale `engine-semantics.md` no-matching-edge claim — 1 hour
3. Unify/document `run_subgraph` permissive fail path — days

**Tier 1 — mechanisms the concept demands**
4. Convergence observability (per-iteration records, `$iteration`, convergence.jsonl, `attractor trace`) — ~1 day, unlocks everything
5. Basin lint + `attractor lint` CLI (incl. unreachable-conditional-edge, acyclic warning) — ~2 days
6. `feedback_from=` mechanism (convention → contract) — ~2 days

**Tier 2 — make the right shape the easy shape**
7. `attractor new --pattern convergence` scaffold + convergence-first profile defaults — ~1 week
8. Invert tutorial order; promote convergence-factory to 00 — ~2 days
9. Gate-primitive library — ~1 week
10. One-sentence recipes-vs-attractor rule + acyclic lint — hours

**Tier 3 — the concept's deeper additions**
11. Failure-class taxonomy → differentiated fix-phase routing (spec-revision, postmortem-on-budget) — ~2 weeks
12. Oscillation/regime detection (lift LoopDetector) — ~1 week after #4
13. Minimal SSE + static HTML run viewer (skip the SPA) — ~3 days
14. Cross-run learning — weeks, needs #4

**Tier 4 — the aspiration**
15. Manager stacks made real (interviewer threading, examples 09/11, subgraph semantics) — weeks
16. NLSpec regenerability: regenerate from implementation or drop the claim — decide
17. Ecosystem naturalization (skills, knowledge, delegation) — ongoing

**Expert's bottom line: fix the eight dead edges, and make iteration N−1 survive.
The first makes the examples true; the second makes every other question answerable.**
