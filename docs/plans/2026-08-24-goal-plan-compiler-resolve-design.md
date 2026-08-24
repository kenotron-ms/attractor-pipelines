# Goal Plan Compiler and Resolve Submission Design

**Status:** Design approved 2026-08-24, ready for implementation planning

**Builds on:** `docs/plans/2026-08-22-goal-plan-attractor-design.md` and
`docs/plans/2026-08-23-goal-plan-attractor-implementation.md` (the `goal_plan_smoke`
family this design generalizes), plus the live bug-fix evidence in commit `fc27a29`.

## Goal

Generalize `goal_plan_smoke` from a fixed, hand-authored 3-lane exemplar into a
**compiler**: an LLM decomposition step produces a `plan.json`-shaped spec for
*arbitrary* user work, and a deterministic Python generator turns that spec into
a `goal_plan_smoke`-family DOT pipeline. The compiled pipeline is runnable either
locally (existing bootstrap+supervisor architecture) or submitted once to the
Amplifier Resolve platform to run goal-batch work at scale, in the cloud, against
any target repo -- while reusing every already-generic building block unchanged.

## Background and Source Analysis

Three research passes grounded this design in source, not assumption:

**1. `goal_plan_smoke` genericity audit** (`foundation:explorer` against this
repo). Verdict: 5 of 7 artifacts need zero change to support arbitrary N
lanes/M waves --

| Artifact | Verdict |
|---|---|
| `python/goal_plan_runtime.py` | Fully generic -- `worktree_id`/`ledger_path`/`lane_id` are opaque caller-supplied strings, zero lane literals in 1204 lines |
| `python/goal_plan_supervisor.py` | Fully generic -- pure argv/cwd/timeout contract, no lane concept |
| `python/goal_plan_bootstrap.py` | Fully generic -- pure supply-chain-integrity launcher, orthogonal to plan structure |
| `subgraphs/goal_lane.dot` | Reusable per-lane child graph, `$param`-driven already (one inert `seeded_failure` test-fixture wrinkle, drop for reuse) |
| `subgraphs/deliver_pr.dot` | Fully generic, lane-count-agnostic |
| `subgraphs/integration_correction.dot` | Reusable body; parent must build its `$aggregate_verifier_argv_json` input |
| `goal_plan_smoke.dot` (the parent) | **The one artifact that must be generated, not reused** -- lane triples (`LaunchLaneX`/`ParentVerifyX`/`IntegrateX`), wave-gating edges, and aggregation shell loops are hand-duplicated literal node blocks |
| `plan.json` | Already shaped like compiler input (`lanes{}`, `waves[]`, `depends_on`, `budgets`, `delivery`) but currently inert -- only used for a correspondence check, never as a scheduling input |

**2. Resolve platform submission mechanics** (`resolve:resolve-expert`, reading
`amplifier-resolve`/`amplifier-resolver-dot-graph`/`amplifier-bundle-attractor`
source directly, flagging 3 items of doc drift along the way). Key findings:

- Multi-file DOT trees (parent + subgraphs) must ship via
  `git+https://github.com/...#subdirectory=...` -- inline `dot_content` only
  carries one file.
- **Pipeline-source host allowlist is `github.com` only.** `workspace_repo` (the
  actual target repo the work happens against) goes through separate
  `workspace_spec()` + Gitea-sidecar mirroring and is not host-restricted the
  same way.
- Companion Python (`goal_plan_runtime.py`, `goal_plan_supervisor.py`) never
  rides the DOT-file fetch -- only `.dot` files get recursively resolved. Must
  arrive via a declared `workspace_repo`/submodule clone instead.
- `goal_plan_smoke`'s external-bootstrap/launch-descriptor/sealed-runtime layer
  defends against an untrusted checkout on a *shared dev host* -- a threat
  model the Resolve container already closes structurally (isolated, resource-
  capped, lifetime-bounded). Nothing external can install a bootstrap into a
  worker container (container setup is fixed by the resolver's manifest), so
  that layer is both unnecessary and unsatisfiable there.
- Delivery is an artifact-file contract: `.resolve/branch_name.txt` +
  `.resolve/pr_url.txt` are mandatory ("do NOT skip step 7") -- without them
  delivery isn't recorded even if a PR really exists.
- The platform already checkpoints its own bookkeeping onto disposable
  `resolve/{instance_id}` branches, independent of pipeline logic -- the
  precedent this design's branch convention borrows.
- Worktree isolation is not a native DOT primitive anywhere (on Resolve or
  off it) -- `shape=component` isolates context, not filesystem.
  `goal_plan_smoke`'s `tool_command`-based `git worktree add` + supervisor
  pattern remains the only way; it ports to a Resolve worker directly (the
  worker container already has `pipeline-runner` installed and 2 CPU / 8G /
  256 PIDs to work with).

**3. `dot_file=` remote-resolution investigation** (`foundation:explorer`
against `amplifier-bundle-attractor/modules/loop-pipeline` source). Verdict:
remote resolution of `dot_file=` is a **single top-level-only gate**
(`load_remote_or_local_graph`, `remote_dot.py:249`) -- triggered only when the
*entry* pipeline source itself starts with `git+https://`, at which point the
recursive fetch (`materialize_remote_dot`) rewrites every ref (same-repo
relative *and* cross-repo `git+https://`) to a local path before `parse_dot()`
ever runs. The per-node resolver (`resolve_dot_path_candidates()`,
`handlers/pipeline.py:73-139`) has zero `git+https://` awareness -- it only
ever tries local-path tiers. Consequence: **an inline `dot_content` parent
cannot reference a remote subgraph today; a `git+https://` *entry* pipeline
absolutely can reference cross-repo subgraphs today** (already proven,
already tested -- `materialize_remote_dot` doesn't check `referrer == child`).

## Decision

Build one deterministic compiler consuming a `plan.json`-shaped spec, reused
identically by two thin front-end skills (local, cloud). The local skill lives
at `skills/goal-batch-attractor/` in this repo, with an explicit
`shortcut: goal-batch-attractor` (`/goal-batch-attractor`). **It does not
claim the `/goal-batch` shortcut name** -- that name isn't ours to take yet.
This is a from-scratch, unproven up-and-comer aiming to eventually earn a
claim on that behavior, not a finalized replacement for it; `/goal-batch`
stays reserved until it's actually proven out.
The `amplifier-module-loop-pipeline` engine change identified during research
(provenance-independent `dot_file=` resolution) is **deferred indefinitely --
not being pursued.** The cross-repo, SHA-pinned `git+https://` entry-pipeline
path already works and is sufficient on its own. Package the compiled,
task-specific pipeline as a small commit on a disposable branch, location
chosen by a simple host-based rule (below), never as a permanent addition to
this repo's curated content. Drop the bootstrap/descriptor/sealing trust
layer for the cloud backend only; keep it as the local backend's default
(free to reuse, already generic), with a lighter no-bootstrap direct-run mode
available for small local batches.

## Goals

- A deterministic Python compiler: `plan.json` (real scheduling input, not
  just audit data) -> a generated `goal_plan_smoke`-family parent `.dot`,
  correct for arbitrary N lanes across M waves.
- Zero modification to the 5 already-generic building blocks beyond dropping
  the inert `seeded_failure` test fixture from `goal_lane.dot` when reused
  outside the original smoke test.
- A local execution backend (attractor CLI / `pipeline-runner`, this repo).
- A cloud execution backend (Amplifier Resolve `dot-graph` resolver,
  submitted from `amplifier-bundle-resolve`).
- A packaging rule that works for target repos on any host, not just GitHub.
- SHA-pinned consistency between the compiled DOT's cross-repo subgraph
  references and the `workspace_repo` clone providing the runtime Python.

## Non-Goals

- Do not reimplement or replace the `goaltractor` skill (kenergy bundle). It
  remains its own separate, simpler, local-only tool (folder/`goal_runner.dot`
  shape) for unrelated ad hoc goal batches -- this design does not touch it.
  A *new*, separate local skill in this repo (`skills/goal-batch-attractor/`,
  `shortcut: goal-batch-attractor` -> `/goal-batch-attractor`) covers the
  `goal_plan_smoke`-family compiler specifically. It does **not** claim the
  `/goal-batch` shortcut -- that name isn't ours yet, and this is an unproven
  up-and-comer, not a finalized replacement.
- **Do not pursue the `amplifier-module-loop-pipeline` engine change** for
  provenance-independent `dot_file=` resolution identified during research.
  This is deferred indefinitely, not filed as a follow-up, not planned --
  it is real and would be cross-cutting (async materialization mid-node-walk,
  cache/cleanup lifecycle threaded through `PipelineEngine`, and a second
  consumer `handlers/manager_loop.py` sharing `resolve_dot_path()`), but the
  already-working SHA-pinned cross-repo `git+https://` entry-pipeline path
  makes it unnecessary for this design.
- Do not invent a dedicated third "scratch" repo for generated pipeline
  artifacts.
- Do not require target repos to be GitHub-hosted to be worked against --
  only the pipeline *source* fetch is GitHub-only; `workspace_repo` handles
  arbitrary hosts via existing Gitea-sidecar mirroring.
- Do not change `subgraphs/deliver_pr.dot`, `subgraphs/integration_correction.dot`,
  `python/goal_plan_runtime.py`, or `python/goal_plan_supervisor.py`.

## Rejected Alternatives

### Reusing `goaltractor`'s architecture directly
Its `shape=folder, dot_file="goal_runner.dot"` shape has no worktree isolation,
no per-lane budget ledgers, and no supervisor exit-truth guarantee -- exactly
the three classes of bug `fc27a29` found and fixed live. Not a substitute for
the `goal_plan_smoke` mechanism; kept as a wholly separate, simpler tool for
its own simpler use case.

### A dedicated "goal-plan-runs" landing-zone repo
Cleaner separation of concerns in the abstract, but costs an extra repo to
provision, grant push access to, and keep alive as a submission dependency.
The disposable-branch convention (mirroring the platform's own
`resolve/{instance_id}` checkpoint push) achieves the same isolation --
nothing lands on any repo's `main` -- without new infrastructure.

### Pursuing the `loop-pipeline` engine change
Real gap, would let a compiler skip even the small generated-artifact commit
and submit ad hoc inline content against permanently-hosted lego pieces. But
it is upstream, cross-cutting work in a different module, and the SHA-pinned
cross-repo `git+https://` entry-pipeline path already works today. **Decision:
deferred indefinitely, not being actioned** -- not filed as a follow-up
proposal, not planned for a future iteration of this design.

### Always committing generated artifacts into `attractor-pipelines`
Simpler (one repo, no host-based branching logic) but pollutes this repo's
curated, reviewed content with every task-specific one-off, contradicting its
own stated purpose ("shared for reference and reuse -- not fixtures, not
throwaway samples"). Used only as the documented fallback for non-GitHub
target repos, in a namespace explicitly segregated from `pipelines/`.

## Architecture

### `plan.json`: from audit artifact to real compiler input

The schema already has the right shape (`lanes{}` keyed by lane id with `wave`,
`depends_on`, `verifier_argv`; `waves[]`; `integration_order`; `budgets`;
`correction`; `delivery`). This design repurposes it from "diffed against the
DOT for correspondence" to "the actual input the compiler reads to generate
the DOT." An LLM decomposition step (reusing `goalify`'s discipline: every
lane needs a machine-checkable stop condition) produces this spec; a
deterministic script consumes it.

### The compiler

A deterministic Python generator, no LLM in this step. Input: a `plan.json`-
shaped spec. Output: a `goal_plan_smoke`-family parent `.dot`, generalizing
the hand-written `LaunchLaneX`/`ParentVerifyX`/`IntegrateX` node triples,
wave-gating edges (a lane in wave N+1 is reachable only via wave N's
`ACCEPTED` edges, exactly as `goal_plan_smoke.dot` does today, just emitted
per-lane instead of hand-duplicated), and the aggregation/coherence shell
loops (`for f in <lane ids>...` becomes data-driven from the spec instead of
literal `lane_a lane_b lane_c` strings). Determinism here is deliberate: RUBRIC
§2's whole point ("self-reported claims are not evidence") applies just as
much to hand-authored DOT drifting out of sync across copies -- an LLM
re-authoring the parent graph per request would risk reintroducing exactly
the class of bug `fc27a29` fixed, every time. Must produce output that passes
`attractor lint` before being handed to either backend.

### Reused building blocks

Unchanged, per the genericity audit above: `python/goal_plan_runtime.py`,
`python/goal_plan_supervisor.py`, `python/goal_plan_bootstrap.py` (local
backend only, see Trust model below), `subgraphs/goal_lane.dot` (minus the
`seeded_failure` test fixture for non-smoke-test reuse), `subgraphs/deliver_pr.dot`,
`subgraphs/integration_correction.dot`.

### Local backend

Runs the compiled family directly via `attractor`/`pipeline-runner` CLI against
a local target repo checkout. Keeps the bootstrap/descriptor/sealing trust
layer by default (it is already generic and free to reuse; local hosts can be
shared/CI too). A lighter no-bootstrap direct-run mode (supervisor + worktrees
only) is available for small ad hoc local batches where that ceremony is
unwarranted -- a flag on the local-facing skill, not a separate architecture.

### Cloud backend

Submits the compiled family to the Amplifier Resolve `dot-graph` resolver.
Drops the bootstrap/descriptor/sealing layer entirely -- the worker container
is already the trust boundary that layer exists to provide, and nothing
external can install a bootstrap into a fixed-manifest container regardless.
Ports the supervisor (bounded wall timeout, term grace, normalized exit
codes) and the worktree/budget-ledger registry unchanged.

### Repository placement decision rule

The pipeline-*source* fetch is GitHub-only; `workspace_repo` (the actual
target repo the work happens against) is host-agnostic via existing Gitea
mirroring. This forces a decision on where the generated, task-specific
`plan.json` + parent `.dot` get committed before submission:

- **Target repo is on GitHub:** commit onto a disposable
  `resolve/goal-plan-<run-id>` branch *in the target repo itself* -- never
  `main`. Submit the entry as
  `git+https://github.com/<owner>/<target-repo>@<sha>#subdirectory=.../parent.dot`.
  `dot_file=` references to the lego-piece subgraphs become cross-repo,
  SHA-pinned: `git+https://github.com/kenotron-ms/attractor-pipelines@<sha>#subdirectory=subgraphs/goal_lane.dot`.
- **Target repo is not on GitHub:** fall back to committing the generated
  artifact into `attractor-pipelines`' own repo, in a `generated/` namespace
  explicitly segregated from the curated `pipelines/` tree (documented in the
  README as machine-generated/ephemeral, with a retention/prune policy), also
  on a disposable `resolve/goal-plan-<run-id>` branch. `workspace_repo` still
  points at the real target repo via Gitea mirroring, fully decoupled from
  where the pipeline definition lives.

Either path requires push access to wherever the artifact lands, before
submission -- already implied by the end goal of eventually landing a PR.

### SHA pinning

Hard requirement, not optional: the cross-repo `dot_file=` references to
`attractor-pipelines` subgraphs and the separately-declared `workspace_repo`
clone of `attractor-pipelines` (providing the companion Python runtime) must
be pinned to the **exact same commit SHA**. Otherwise a lane's DOT-side
contract can drift out of sync with the runtime module actually executing
it -- a version-skew bug that would be hard to diagnose after the fact.

### Delivery contract

Cloud backend must write `.resolve/branch_name.txt` and `.resolve/pr_url.txt`
per the platform's mandatory artifact-file contract. Local backend continues
using `subgraphs/deliver_pr.dot` as-is.

### Trust model per backend

| | Local (default) | Local (light) | Cloud |
|---|---|---|---|
| Bootstrap / descriptor / sealing | Yes | No | No (unsatisfiable in a fixed-manifest container; unnecessary given container isolation) |
| Supervisor | Yes | Yes | Yes |
| Worktree + budget-ledger registry | Yes | Yes | Yes |

## Anticipated File Footprint

```
attractor-pipelines/
  compiler/                          # NEW -- deterministic plan.json -> DOT generator
  skills/goal-batch-attractor/        # NEW -- local-facing decompose/compile/run skill,
    SKILL.md                         #   shortcut: goal-batch-attractor -> /goal-batch-attractor
                                      #   (does NOT claim /goal-batch; unproven up-and-comer,
                                      #   not finalized)
  generated/                          # NEW -- documented fallback landing zone for
                                       #   non-GitHub target repos (segregated, pruneable)
  pipelines/goal_plan_smoke/
    subgraphs/goal_lane.dot           # MODIFY -- drop seeded_failure test fixture for reuse
  README.md                           # MODIFY -- document generated/ namespace + its policy

amplifier-bundle-resolve/
  skills/goal-plan-submit/            # NEW -- cloud-facing decompose/compile/submit skill,
    SKILL.md                         #   sibling to the existing resolve-expertise skill
```

## Open Items / Follow-Ups

1. ~~Engine proposal against `amplifier-module-loop-pipeline`~~ -- **decided:
   deferred indefinitely, not being actioned** (see Decision and Non-Goals).
   The seam (`resolve_dot_path_candidates()`, `handlers/pipeline.py:73-161`;
   also `handlers/manager_loop.py`'s shared consumption of `resolve_dot_path()`)
   remains documented above for reference only, in case this is revisited
   later.
2. ~~Skill-hosting scaffolding for `attractor-pipelines`~~ -- **decided:** add
   a root-level `skills/` directory to this repo, hosting
   `skills/goal-batch-attractor/` with an explicit
   `shortcut: goal-batch-attractor` (`/goal-batch-attractor`). It does
   **not** claim `/goal-batch`; that name isn't ours yet, and this skill is
   an unproven up-and-comer, not a finalized replacement.
3. Retention/prune policy mechanics for the `generated/` fallback namespace
   (age-based? branch-count cap? manual?) -- not designed yet, needed before
   that path sees real traffic.
