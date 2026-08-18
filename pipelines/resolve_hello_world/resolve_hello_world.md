# resolve_hello_world -- reference example for remote PR delivery via Amplifier Resolve

This pipeline is the reference example in this repo for how a **remote
dot-graph pipeline delivers a real, durable GitHub PR** through the
Amplifier Resolve platform. If you're building a new pipeline that needs to
open a PR from a Resolve worker container, start here.

The important lesson this pipeline exists to teach: **PR delivery is not
something a pipeline can fully control by itself.** The platform's
`promote/pr` mechanism enforces two prerequisites at the *instance
submission* layer, not the pipeline layer. Get the submission wrong and the
pipeline will fail late, deep in the `DeliverPRResolve` subgraph, with an
error that looks like a pipeline bug but is actually a job-submission bug.

## Submit this job correctly

To open a real PR, the Resolve instance must be created with **both** of
these instantiation params, alongside the usual `repo_url`:

| Param | Value | Why it's required |
|---|---|---|
| `delivery_mode` | `"promote"` | Without it, the platform's `promote/pr` endpoint returns HTTP 409 `"Promotion was not requested"` before it does anything else. This is a hard gate, verified directly against `amplifier-resolve/src/amplifier_resolve/routes/internal.py`. |
| `branch_name` | `"resolve/<repo-name>-<first-8-chars-of-instance-id>"` | Optional. If you don't supply it, the platform computes this exact value itself as the *expected* branch and will 422 with `"Promotion branch does not match submitted instance"` if the branch actually pushed doesn't match. Only supply it explicitly if you need to know the branch name before the instance starts (e.g. to link to it in advance). |

### In natural language

> "Submit a dot-graph job using pipeline
> `git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/resolve_hello_world/resolve_hello_world.dot`,
> against `repo_url=https://github.com/<owner>/<repo>`, with
> `delivery_mode=promote`. Let the platform derive `branch_name` itself
> unless you have a specific reason to pin it."

### Via the CLI / `remote.py`

```bash
remote.py call dot-graph \
  "git+https://github.com/kenotron-ms/attractor-pipelines@main#subdirectory=pipelines/resolve_hello_world/resolve_hello_world.dot" \
  --params '{"repo_url": "https://github.com/<owner>/<repo>", "delivery_mode": "promote"}'
```

Then watch it:

```bash
remote.py watch <instance_id>
```

### What happens if you forget `delivery_mode=promote`

The pipeline will run all the way through `WriteHelloWorld` and
`CommitPush`/`CheckPush` successfully -- the file gets written, the branch
gets pushed to the Gitea sidecar mirror, everything *looks* fine right up
until the PR-open step. Then the platform's `promote/pr` call fails with a
409, which surfaces in the pipeline as a delivery failure at the
`DeliverPRResolve` subgraph. The failure is real, but its root cause is
one layer up, at job submission -- not in the `.dot` file.

## Why this matters more broadly

Every pipeline in this repo that ends in a real (non-ephemeral) GitHub PR
via the Amplifier Resolve platform is subject to the same two
prerequisites. If you're adapting `resolve_hello_world.dot` into a new
pipeline, carry this submission recipe forward with it -- it's not
optional plumbing, it's part of the contract.

## Pipeline shape

```
pipelines/resolve_hello_world/
  resolve_hello_world.dot         # entry pipeline: Start -> WriteHelloWorld -> DeliverPRResolve -> Report -> Exit
  subgraphs/
    deliver_pr_resolve.dot          # Start -> CommitPush -> CheckPush -> OpenPRResolve -> CheckPROpened -> MarkOpened/Failed -> Exit
```

See the header comments in `resolve_hello_world.dot` and
`subgraphs/deliver_pr_resolve.dot` for the node-by-node mechanics and the
history of bugs fixed in this pipeline (goal_gate misuse on non-evidence
nodes, dead edges, a context-key typo, and a missing `Start` edge) -- each
one is documented in place, citing the exact engine semantics that made it
a bug.
