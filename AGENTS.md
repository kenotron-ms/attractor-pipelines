# AGENTS.md

Instructions for any agent (or human) creating, modifying, or reviewing
pipelines in this repo.

## Required reading before touching any `.dot` file

1. **`docs/primer.md`** -- the attractor doctrine: what makes a pipeline an
   attractor rather than a flowchart, and why (the three-question test, the
   design order, the core doctrine, the engine foot-gun card).
2. **`docs/RUBRIC.md`** -- the actionable checklist derived from that
   doctrine and from real bugs already found and fixed in this repo's own
   pipelines. This is the rubric to build against and to review against --
   every item cites either doctrine or a concrete incident.

Read the primer for the *why*. Use the rubric as the *checklist* -- both
when authoring a new pipeline and when reviewing a PR that touches one.

## Working agreements

- **Copy the nearest proven pipeline before inventing a new bespoke node.**
  See `docs/RUBRIC.md` §5. This repo's shared `subgraphs/deliver_pr.dot` is
  the proven pattern for "deliver work as a PR" -- reuse it rather than
  writing a new commit/push/PR sequence from scratch.
- **Self-reported success from an LLM node is not evidence.** Any node that
  claims an external side effect (a GitHub comment posted, a push landed, a
  file written) needs an independent verification step downstream that
  checks the real state. See `docs/RUBRIC.md` §2 for the recurring incident
  class this rule exists to prevent.
- **If you fix a bug in a shared `subgraphs/*.dot` file, check every
  consumer of that subgraph**, not just the pipeline that surfaced the bug.
- **Update `docs/RUBRIC.md` when a new pipeline bug teaches us something
  new.** Add a case study line to the relevant section (or a new checklist
  item if it's a new class of bug). `docs/RUBRIC.md` and `docs/primer.md`
  are the only docs here -- keep them living and current rather than
  spinning off separate notes files.

## Repo layout

Each pipeline lives in its own `pipelines/[name]/` folder containing its
entry `.dot` file (`pipelines/[name]/[name].dot`), any `subgraphs/`, and
optional companion docs. See `README.md` for the full list of pipelines and
what each one does.
