# Attractor Pipeline Rubric

**Use this when authoring or reviewing any `.dot` pipeline in this repo.** It is
a checklist, not a philosophy essay -- read `primer.md` first for the *why*.
Every item below traces back either to primer.md's doctrine or to a real bug
that shipped in one of this repo's own pipelines and had to be fixed (cited
inline). If you're reviewing a PR that touches a `.dot` file, this is the
review checklist.

---

## 0. Before you write a single node

1. **Name the sink.** What command, run by a machine, proves this is done?
2. **Build the gate** that runs it and emits a token.
3. **Build the loop** -- failure routes back to the node that can fix it.
4. **Only then** write the work nodes.

If you can't answer #1, you're not ready to write nodes yet.

## 1. Structural checklist (fail any of these -> it's a flowchart, not an attractor)

- [ ] **Is there a cycle?** If not, this is fine ONLY if the pipeline is a
      deterministic dispatcher/infra-deploy script with no LLM judgment to
      converge (e.g. `ship_ready.dot`'s runtime-mode deploy branches). If any
      node in the acyclic chain is an LLM making a judgment call, it needs a
      loop. No cycle + LLM judgment = should probably have been a recipe, not
      an attractor pipeline.
- [ ] **Is the exit gated on evidence**, not step-completion? (test passed /
      file exists / API confirms the state / validator returned 0 -- never
      "the last node finished talking.")
- [ ] **Would it still land if any one LLM node had a bad day?** If one
      mediocre generation silently propagates to the output, there is no
      basin -- it's a conveyor belt with extra syntax.

## 2. Self-reported claims are not evidence (recurring root cause in this repo)

**Every pipeline bug we've fixed so far traces back to this one rule being
skipped somewhere.** A `box` node prompted to "post a comment" / "commit and
push" / "write a file" can emit a compliant-looking success line without the
underlying action having actually happened against the real target. The
engine has no built-in check that a node's claimed tool calls actually ran.

- [ ] Does every node that claims an **external side effect** (GitHub API
      call, git push, file write that a later step depends on) have an
      **independent verification step** downstream that checks the real state
      -- not the claiming node's own printed line?
- [ ] Is that verification step `shape=box` (or `parallelogram` +
      `tool.last_line`), never `shape=diamond`? (See §3.1 -- diamond is a
      documented foot-gun for exactly this kind of gate.)

**Case studies (this repo):**
| Pipeline | What happened | Fix |
|---|---|---|
| `ship_ready.dot` bootstrap mode | Agent committed against a local scratch checkout instead of `$repo`; `BootstrapReport` claimed success anyway | Added `VerifyRepoTarget` deterministic gate before any write; routed PR delivery through `deliver_pr.dot`'s evidence-gated `CheckPush` |
| `pr-review-exhaustive.dot` `comment_draft` | Node could emit success JSON without ever calling curl | Added `verify_review_posted` -- independently GETs `/pulls/.../reviews` and confirms a matching review exists |
| `pr_review.dot` (fast variant) | Same bug as above, but the sibling pipeline was never patched | Ported the same `verify_review_posted` gate |

## 3. Foot-gun checklist (verified engine behaviors -- audit every node against these)

1. **The diamond trap.** `shape=diamond` conditional nodes have been observed
   to return their own SUCCESS regardless of prompt content, overwriting the
   upstream outcome -- so `condition="outcome!=success"` edges after a
   diamond can never fire, and an LLM prompt attached to a diamond node may
   never even execute. **Never use `shape=diamond` for an LLM
   judgment/verification gate.** Use `shape=box` (proven to execute prompts)
   or `shape=parallelogram` + `condition="context.tool.last_line=..."`.
   *(Fixed in `pr-review-exhaustive.dot`'s `quality_eval` and
   `verify_review_posted`, both converted diamond -> box.)*
2. **FAIL doesn't traverse plain edges.** It only routes via
   `condition="outcome=fail"` edges, `runs_on=always|failure` nodes, or
   `retry_target`. A plain edge after a node that can FAIL will silently
   dead-end the branch.
3. **A "successful failure" node is just as dead an edge as the diamond trap.**
   If a node deliberately reports a failure state via `context_updates` (e.g.
   `{"delivery.result": "failed"}`) but itself exits with tool-success, any
   downstream `condition="outcome=fail"` edge is **unreachable** -- outcome
   was never actually `fail`. Route on the reported field instead:
   `condition="context.delivery.result=failed"`.
   *(Fixed repo-wide: `subgraphs/deliver_pr.dot`'s `Failed` node exits 0;
   all 4 consumers -- `hello_world`, `idea_to_pr`, `idea_to_shipped`,
   `ship_ready` -- had a dead `outcome=fail` edge until this was corrected.)*
4. **`last_response` between nodes truncates to 200 chars** except
   `fidelity=full`. Any gate that greps `$last_response` for a marker/verdict
   line risks the marker being truncated away if the preceding prompt writes
   a long response with the marker at the end. Prefer routing on a **file**
   the preceding node already writes (`cat foo.json | python3 -c "..."`)
   over parsing `$last_response`. If you must use `$last_response` (e.g. a
   human's freeform approval reply), set `fidelity="full"` on that specific
   edge.
   *(Fixed: `build_verify.dot`'s `CheckRubric` now reads
   `.resolve/verify/rubric_result.json` directly instead of grepping
   `$last_response`; `idea_to_shipped.dot`'s `CheckPlanApproval` and
   `merge_gate.dot`'s `CheckHumanResponse` got `fidelity="full"` on their
   incoming edges since they gate on a human's actual reply text.)*
5. **Route on `tool.last_line`** (the last non-empty stdout line), never
   `tool.output` (which may include multi-line noise the condition matcher
   won't parse cleanly).
6. **`outcome=` resolves `preferred_label` first**, then status. If a node
   also sets a label, double-check which one your condition is actually
   matching.
7. **`run_subgraph` (parallel branches, folder sub-pipelines, manager
   children) silently returns the last outcome** -- a dead-end inside a
   compositional layer reports SUCCESS to the parent graph even though
   nothing meaningful happened. Don't assume a `folder`-shape subgraph node's
   outcome reflects real success; check its actual reported
   `context_updates` fields instead (see #3 above).
8. **Tool nodes' cwd** resolves `context.target_dir` -> `graph.source_dir` ->
   process cwd. For box-node pipelines, the process cwd must equal `--cwd`
   passed to the CLI (known issue) -- don't assume a tool node is running
   where you think it is without checking.
9. **Checkpoints don't resume.** The engine always restarts from the start
   node. If you need resumability, build it as a graph pattern (a
   `parallelogram` guard node that checks file state and skips already-done
   work), not by relying on any checkpoint file.
10. **`$iteration` is not substituted in prompts**, and per-iteration logs
    get overwritten. If you need to know "is this attempt N better than
    N-1," you must track that yourself in a file (e.g. append a scored
    JSON line per iteration) -- the engine gives you nothing for free here.
11. **`house` (manager) is experimental.** Don't build load-bearing pipeline
    logic on it without a smoke-test run first.

## 4. Core doctrine checklist

- [ ] **Tier discipline.** For every LLM (`box`) node, ask: "is the model
      here for judgment, or just to type?" If it's just typing/formatting,
      it should be a `parallelogram` doing it deterministically instead.
- [ ] **Cheap gate first, expensive gate second.** A deterministic check
      (file exists, exit code, `git diff`) should run before an LLM
      critique/adversarial-review gate, not after.
- [ ] **Route on observed evidence, not typed sentinels.** Exit codes, file
      presence, API responses -- not "the model emitted the keyword SUCCESS."
- [ ] **Feedback accumulates, and is curated.** A retry without critique of
      the prior attempt is a coin re-flip. A retry with written critique is
      descent. But an unbounded append-only feedback channel becomes context
      sludge -- write the single highest-leverage next change, not
      everything ever said.
- [ ] **Loops have a bound, and the bound is a decision point.** Budget
      exhaustion should route to an escalation/postmortem node, not a bare
      FAIL or a silent `Exit`.
- [ ] **Differentiated failure edges.** Route each failure class back to the
      phase that can fix *it* specifically: failing test -> diagnosis (not a
      blind patch); contradiction discovered -> spec revision; uncertainty ->
      human escalation; repeated identical failure -> root-cause postmortem.
- [ ] **A crashed/timed-out parallel branch must not look identical to a
      branch that cleanly found nothing.** If you use `fan_out` with
      `error_policy="continue"`, make sure the collector node distinguishes
      "lane produced a file saying '(none found)'" from "lane's result file
      doesn't exist at all," and that distinction propagates into any
      downstream report as a visible coverage gap.
      *(Fixed: `pr_review.dot`'s `collect_lane_results` now emits an explicit
      `lane_failures` list, and `merge_findings`'s prompt is instructed to
      surface it as a "Coverage gap" note rather than silently treating a
      crashed lane the same as a clean pass.)*
- [ ] **Idempotency widens the basin.** If a pipeline persists state across
      runs in a file (fix-round counters, workflow markers, etc.), does a
      fresh run reset that state, or could a stale file from a prior run
      (e.g. a reused CI checkout) skew this run's behavior?
      *(Fixed: `idea_to_pr.dot` now has a `ResetFixState` node right after
      `Start` that clears `.resolve/fix_state.json`.)*
- [ ] **Expensive model in the gate, not just the generator.** Gate quality
      determines basin depth; generator quality only affects iteration
      count. Spend reasoning effort accordingly (see `reasoning_effort` on
      the adversarial gates in `pr-review-exhaustive.dot`).
- [ ] **Parallelism is for disagreement, not just throughput.** Fan out
      independent lenses/reviewers; treat divergence between them as signal,
      not noise to average away.

## 5. Reuse discipline

- **Copy the nearest proven pipeline before inventing a new bespoke node.**
  This repo's shared `subgraphs/deliver_pr.dot` (commit, push, verify the
  push landed via `CheckPush`, open the PR) is the proven pattern for
  "deliver work as a PR" -- used by `hello_world`, `idea_to_pr`,
  `idea_to_shipped`, and `ship_ready`. If you're writing a bespoke
  commit/push/PR box node instead of reusing this subgraph, you are very
  likely reintroducing a bug that's already been fixed once (see §2's
  `ship_ready` case study -- its original bespoke `CommitWorkflow` node is
  exactly this mistake).
- If you fix a bug in a shared subgraph, **check every consumer of that
  subgraph**, not just the one pipeline that surfaced the bug. (The dead
  `outcome=fail` edge in §3.3 existed identically in 4 different pipelines
  before it was caught.)

## 6. PR review checklist (concrete, mechanical)

When reviewing a PR that adds or modifies a `.dot` file in this repo, check:

- [ ] Ran the three-question test (§1) against every node/cycle in the diff.
- [ ] No `shape=diamond` used for an LLM judgment or verification gate (§3.1).
- [ ] Every claimed external side effect has an independent verification
      step reading real state, not a trusted self-report (§2).
- [ ] Every `condition="outcome=..."` edge after a node is actually
      reachable -- trace what that node's real exit status/outcome will be,
      don't assume it matches what the prompt "says" (§3.2, §3.3).
- [ ] Any gate parsing `$last_response` either has `fidelity="full"` on its
      incoming edge, or (better) reads a file instead (§3.4).
- [ ] Any persistent state file written across runs gets reset/scoped
      correctly for a fresh run (§4, idempotency).
- [ ] Fan-out/parallel branches distinguish "crashed" from "clean" results
      downstream (§4).
- [ ] Budget/retry exhaustion routes to an escalation node, not a bare fail.
- [ ] If touching a shared `subgraphs/*.dot` file, checked all its consumers
      for the same class of bug, not just the one pipeline in front of you.

## 7. Where to look for deeper background

- `primer.md` -- the philosophy and doctrine this rubric distills from.
- `archive/NOTES-attractor-assessment.md` -- broader ecosystem context (the
  two upstream attractor repos, canonical examples, design principles) from
  the initial repo assessment. Useful background reading, not required for
  day-to-day pipeline authoring.
- `archive/NOTES-bundle-misses.md` -- the original verified gap analysis of
  the shipped engine (the dead-edge census, engine gotchas verified against
  source) that this repo's early fixes were generated from.
- `archive/NOTES-playbook-alignment.md` -- the doctrine additions (failure
  classes, rim coverage, regimes, budget-as-decision) sourced from the
  upstream agent-building-playbook pattern.

These archive docs are historical research notes -- point-in-time captures
that fed into this rubric and primer.md. When they conflict with this
rubric or with primer.md, **this rubric and primer.md win** -- they're the
living, maintained documents. Update this rubric (not the archive) when a
new pipeline bug teaches us something new.
