# Attractor Doctrine Primer

**Read this before working any task in this backlog.** It is the shared context that
makes each task self-sufficient. Deeper source material lives beside it in this
directory (`NOTES-*.md`) and in the two upstream repos.

---

## 1. What an attractor pipeline is

An attractor, in dynamical systems, is a state a system falls into from a wide range
of starting conditions and returns to when perturbed — a marble in a bowl. An
attractor *pipeline* shapes work the same way: **the correct, verified outcome is the
low point of the bowl**, and the graph is carved so that wherever the model starts
and however it wanders, work tends back toward that outcome.

> A pipeline's job is not to describe the steps. It is to shape a space so that
> quality becomes the only stable resting place.

An LLM node is a **noisy operator**. You cannot make a single call reliable. You CAN
build a shape where noise gets corrected instead of accumulated:

| Shape | Per-step reliability | 6 steps |
|---|---|---|
| Linear chain A→B→C→D→E→F | 0.90 | **0.53** — a coin flip |
| Same steps, each wrapped in verify→retry | 0.90 → ~0.99 effective | **0.94** |

**Chains multiply variance; loops divide it.** Adding steps makes linear pipelines
worse. Adding gates makes looped pipelines better. You are not orchestrating LLM
calls — you are building an error-correcting code around a noisy channel.

This also redefines "done." Conventional automation is done when the script
completes. That definition cannot survive a nondeterministic actor: a model can
finish a step and still be wrong — **wrong-but-plausible is the failure class that
matters**, and it does not announce itself. An attractor-shaped workflow is judged by
one question: *did the system converge to the desired state?*

## 2. The three-question test

Ask of any pipeline (`.dot` or otherwise). If any answer is "no," it's a flowchart,
not an attractor:

1. **Is there a cycle?** No corrective back-edges → a script with extra syntax.
2. **Is the exit gated on evidence, not step-completion?** Tests passed, validator
   returned 0, file exists — not "the last node finished talking."
3. **Would it still land if any one LLM node had a bad day?** If one mediocre
   generation silently propagates to the output, there is no basin.

## 3. Design order (invert the instinct)

1. **Name the sink.** What command, run by a machine, proves this is done?
2. **Build the gate.** A deterministic node that runs it and emits a token.
3. **Build the loop.** Failure routes back to the node that can fix it.
4. **Only then** write the work nodes.

The gate is the pipeline. The steps are implementation detail.

## 4. Core doctrine

1. **Tier discipline.** Models for judgment; deterministic code (`parallelogram`
   nodes / scripts) for everything else. Test per LLM node: "is the model here for
   judgment, or just to type?" Never use a model as a format translator.
2. **Cheap gate first, expensive gate second.** pytest before LLM critique. Always.
3. **Route on observed evidence, not typed sentinels.** Exit codes, file presence,
   `git diff` — not "the model emitted the keyword SUCCESS."
4. **Feedback must accumulate.** A retry without critique of the prior attempt is a
   coin re-flip — same distribution, new sample. A retry with written critique is
   descent. Feedback channels must be *curated* (single highest-leverage change,
   consolidate stale entries), or accumulated critique becomes context sludge.
5. **Loops need a bound — and the bound is a decision point, not a fuse.** Budget
   exhaustion should route to a postmortem/escalation, not a bare FAIL.
6. **Differentiated failure edges.** The basin has multiple walls. Route each
   failure class back to the phase that can fix *it*: failing test → diagnosis (not
   a blind patch); contradiction discovered → spec revision; uncertainty → human
   escalation; repeated identical failure → root-cause postmortem. One generic
   retry edge is a degenerate basin.
7. **Don't let the loop absorb deterministic bugs.** An attractor absorbs *model
   drift*, not broken tools or specs. If a corrective edge fires repeatedly on the
   same failure signature, stop iterating and fix the root cause.
8. **Idempotency widens the basin.** If re-running a step converges toward the
   outcome instead of compounding a mess, the basin is wider and the equilibrium
   more stable. Design steps to be safely re-runnable; treat resumability as basin
   width, not crash plumbing.
9. **Watch the regime.** Iterative loops are contractive (converging), oscillatory
   (ping-ponging between states), or exploratory (wandering). Prompt design
   controls the regime. Instrument so you can tell which one you're in — "is
   iteration N better than N−1?" must be answerable.
10. **Parallelism is for disagreement, not throughput.** Fan out independent
    lenses; treat divergence as signal.
11. **Prompt for goal-responsibility, not position-responsibility.** Not "Step 3 of
    6: write the unit tests" but "Advance the goal. Read prior critique and address
    it. Your work will be verified by code."
12. **Expensive model in the gate.** Gate quality determines basin depth; generator
    quality only affects iteration count. Spend accordingly.

## 5. The reference shape

Seven nodes, two gates, two cycles. Inner loop = tight mechanical fix cycle. Outer
loop = quality convergence with accumulated feedback.

```
start → attempt → verify(cheap, deterministic) →[red]→ attempt
                          ↓ [green]
                  critique(expensive, judgment) → gate →[iterate]→ feedback → attempt (fresh iteration)
                          ↓ [ship]
                        done   ← exit structurally unreachable until gates pass
```

The working exemplar: `amplifier-bundle-attractor/examples/patterns/convergence-factory.dot`.

## 6. Amplifier attractor engine — foot-gun card

If your task touches `.dot` files or the engine, these are the verified behaviors
that will bite you (source of truth: `context/engine-semantics.md` in the bundle
repo, plus verified probes recorded in `NOTES-bundle-misses.md`):

1. **The diamond trap (why 8 shipped examples are broken):** `shape=diamond`
   conditional nodes return their own SUCCESS, overwriting the upstream outcome —
   so `condition="outcome!=success"` edges after a diamond can never fire. And FAIL
   is fail-fast: a real FAIL never *reaches* the diamond via plain edges. Route on
   evidence instead: `parallelogram` gate + `condition="context.tool.last_line=..."`.
2. **FAIL doesn't traverse plain edges.** It routes only via
   `condition="outcome=fail"` edges, `runs_on=always|failure` nodes, or
   `retry_target`. Otherwise the branch halts.
3. **`last_response` between nodes truncates to 200 chars** except `fidelity=full`.
   Pass real data via files, not node-to-node prose.
4. **Route on `tool.last_line`** (last non-empty stdout line), never `tool.output`.
5. **`outcome=` resolves `preferred_label` first**, then status.
6. **Main loop hard-fails on no-matching-edge, but `run_subgraph` (parallel
   branches, folder sub-pipelines, manager children) silently returns the last
   outcome** — dead-ends inside compositional layers report SUCCESS.
7. **Tool nodes' cwd** = `context.target_dir` → `graph.source_dir` → process cwd;
   for box-node pipelines the process cwd must equal `--cwd` (known CLI issue).
8. **Checkpoints don't resume.** The engine always starts from the start node;
   resume is a graph pattern (file-state guard nodes).
9. **`$iteration` is not substituted in prompts** and per-iteration logs are
   overwritten — track iteration state in files yourself if you need it.
10. **`house` (manager) is experimental**; example 11 is a known-failing fixture.

## 7. Working agreements for backlog tasks

- **Goal over steps.** Each task transfers a goal, rationale, and definition of
  done. The *how* is yours — but honor each repo's own conventions (`AGENTS.md`,
  design docs, PR templates) when working inside it.
- **Evidence over claims.** Every DoD item is either satisfied with real evidence
  (command output, file paths, live run logs) or explicitly reported as unmet.
  Never fabricate. The mechanical DoD script is necessary but not sufficient — the
  judgment criteria in each task matter too.
- **Walk upstream first.** The bundle's PRINCIPLES.md requires it: if a fix belongs
  in the canonical spec/engine rather than an example or doc, say so.
- **Leave a trail.** Record what you tried, what failed, and what you learned —
  these runs feed an evals loop that measures whether this whole approach works.

## 8. Deeper sources (in this repo and beside it)

| Source | What it gives you |
|---|---|
| `context/NOTES-attractor-assessment.md` | Full expertise baseline: both repos, engine mechanics, principles |
| `context/NOTES-playbook-alignment.md` | The doctrine additions (failure classes, rim coverage, regimes, budget-as-decision) |
| `context/NOTES-bundle-misses.md` | The verified gap analysis this backlog was generated from |
| `amplifier-bundle-attractor/context/engine-semantics.md` | Shipped engine source of truth (note: has known drift — see T0-2) |
| `amplifier-bundle-attractor/docs/` | DOT authoring guide, routing reference, design principles, patterns |
| `attractor/attractor-spec.md` | The canonical StrongDM NLSpec (§3.3 edge selection, §3.4 goal gates, §5.4 fidelity, App C status contract) |
| `agent-building-playbook/patterns/shape-work-as-an-attractor.md` | The topology doctrine ("the missing manifesto") |
