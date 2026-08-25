# Lane Goal-Condition File Contract Design

## Outcome

Each parallel lane in a compiled batch is driven by a real, self-checkable goal condition — carried in by reference to its goal-condition file, the composition every autonomous goal already uses. Today the compiled path keeps only the machine check and collapses the outcome into a placeholder marker, dropping intent. This design threads intent through so each lane delivers implemented work, while an independent parent-side verifier stays the sole acceptance authority.

## Scope and Non-goals

In scope: carrying a composed goal-condition file into each lane by reference; a real-work lane brick running an autonomous goal loop against it; keeping the marker lane brick for smoke testing; keeping the compiler mechanical. Out of scope: parent-pipeline or compiler responsibility changes; the compiler reading goal content; the single-lane-wave legality defect, tracked separately.

## Evidence and Constraints

The composer already emits the fixed-structure file, and the sibling orchestrator already feeds each lane its full file as an autonomous goal — a proven pattern to copy. Half the contract flows today: the machine check survives as the verifier, but intent collapses into a marker. Doctrine: lane self-report is not evidence. The compiler stays deterministic, threading the reference opaquely; bricks are hand-authored; each isolated workspace must reach its file.

## Decisions

| ID | Decision | Rationale | Ranked alternatives |
| D-01 | Carry the goal condition into a lane by reference to its composed file | Reuses composer output, matches the sibling orchestrator, keeps the plan small and inspectable | 1) Inline fields (re-implements composer); 2) Freeform blob (loses structure) |
| D-02 | Add a real-work lane brick that resolves the file, runs a goal loop to convergence, commits work; keep the marker brick | Preserves the swappable-brick seam, keeps smoke testing, copies the proven pattern | 1) Modify existing brick (loses fixture); 2) Non-iterative step (weaker); 3) Parent implements (breaks thin-parent) |
| D-03 | The parent-side verifier is sole acceptance authority; lane self-assessment is advisory | Self-report is not evidence | 1) Trust lane verdict (unverified); 2) Require both (redundant) |
| D-04 | The compiler threads the reference as an opaque parameter, never parsing content | Keeps compiler deterministic; discipline stays with composer | 1) Compiler validates structure (couples, drifts) |
| D-05 | The front end composes one file per lane and records its reference and verifier | Decomposition lives in the front end; compiler stays mechanical | 1) Inline goal text in prose (not reusable) |

## Components and Boundaries

| Component | Owns | Does not own | Expected file or subsystem boundary |
| Goal-condition composer | The fixed structure and its lint discipline | Lane decomposition or verification | Goal-condition authoring subsystem |
| Batch-authoring front end | Lane decomposition, per-lane authoring, wave grouping, plan emission | Graph generation or lane execution | Batch-authoring subsystem |
| Deterministic plan compiler | Lowering the plan to the parent graph, threading each reference and verifier | Goal content, bricks, execution | Plan-to-graph compilation subsystem |
| Real-work lane brick | Running the goal loop against the condition in an isolated workspace, committing work | Acceptance or integration | Lane execution subgraph |
| Parent orchestration pipeline | Wave fan-out, verification, integration, correction, terminal selection | Lane-internal work | Parent orchestration graph |

## Interfaces and Flow

The composer produces a fixed-structure file with a machine check. The front end decomposes work into lanes, recording per lane the reference, verifier, ownership, wave, dependency, and delivery branch. The compiler emits the parent graph, wires each real-work brick with its reference plus plumbing, and passes the verifier to the verification stage. The brick resolves its reference in its isolated workspace, runs the goal loop to convergence, and commits candidate work. The parent independently runs the verifier; only a pass advances a lane, a failure yields a negative terminal without blocking siblings.

## Failure Handling

A lane that cannot converge yields a per-lane negative terminal — blocked-with-named-reason — captured as a residual, without aborting the batch. A lane self-claiming success but failing the verifier is failed and not integrated. A missing or unreachable reference surfaces as a distinct infrastructure failure, separate from a work failure. The verifier stays authoritative when self-assessment disagrees.

## Verification Outcomes

| Outcome | Observable evidence | Acceptance signal |
| Real work reaches a lane | A referenced lane commits changes beyond a placeholder | The commit satisfies the condition, not just a marker |
| Independent acceptance holds | The parent verifier passes against produced state | Pass comes from real evidence, not self-report |
| Intent survives the pipeline | Outcome, scope-outs, and known facts reach the lane | Behavior reflects the condition, not a default |
| Smoke path preserved | The marker brick still validates orchestration | A marker batch completes orchestration unchanged |
| Sibling-fork isolation | A blocked lane yields a residual without aborting the batch | Batch reaches a residuals-ready terminal, siblings unaffected |

## Assumptions and Risks

| ID | Assumption or risk | Consequence if false | Containment |
| R-01 | The file is reachable in each lane's isolated workspace | Lane cannot resolve its goal; misread as work failure | Treat as infrastructure failure; ensure files exist on each lane's base |
| R-02 | The goal loop terminates within budget | Lanes hang or exhaust budget | Lane budget and parent wall timeout cap it; over-budget becomes a negative terminal |
| R-03 | Composed intent suffices without mid-loop human input | Lanes stall awaiting input | Composer forbids mid-loop human-in-the-loop; lint detects it |
| R-04 | The verifier distinguishes real from plausible non-completion | False acceptance | Verifier is a real machine check run independently |
| R-05 | Scope creep into the single-lane-wave legality defect | Design loses focus | Out of scope; tracked separately |

## Shared Seams

| ID | Shared surface | Owning component | Consumers | Collision rule |
| S-01 | Per-lane plan fields (reference, verifier, ownership, wave, dependency, branch) | The compilation input contract | Front end (writer), compiler (reader) | Compiler's input contract is authoritative; unknown fields ignored |
| S-02 | The goal-condition file contract (fixed sections plus machine check) | The goal-condition composer | The real-work brick and later inspection | Composer structure is the single source of truth; consumers never redefine it |
| S-03 | The brick invocation parameter contract | The compiler's brick-launch surface | The marker brick and the real-work brick | Both conform to one contract; the goal-condition parameter is additive and optional |
| S-04 | The parent-side verification stage | The parent orchestration pipeline | Every lane | Parent verification is sole acceptance authority; self-assessment never bypasses it |
