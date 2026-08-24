# generated/ — machine-generated, ephemeral, NOT curated

**Read this before assuming anything under `generated/` is a reviewed
reference pipeline. It is not.**

Everything the rest of this repo says about itself — "Public, real-world DOT
pipelines... shared for reference and reuse — not fixtures, not throwaway
samples" — is the exact opposite of what this namespace is for. `generated/`
is the one explicit, documented exception to that identity. Nothing here is
hand-authored, reviewed, or meant to be copied and adapted. If you are
looking for a pipeline to learn from or reuse, look in `pipelines/`, never
here.

## What lands here, and only here

`generated/` is the **fallback landing zone** for the goal-plan compiler
(see `docs/plans/2026-08-24-goal-plan-compiler-resolve-design.md`,
"Repository placement decision rule"). The compiler turns a `plan.json`-shaped
spec into a `goal_plan_smoke`-family parent `.dot`, then that task-specific
artifact has to be committed somewhere GitHub-hosted before it can be
submitted to the Amplifier Resolve `dot-graph` resolver over `git+https://`.

The placement rule picks that "somewhere" by the **target** repo's host:

- **Target repo is on GitHub** → the generated artifact commits onto a
  disposable `resolve/goal-plan-<run-id>` branch **in the target repo
  itself**. It never touches this repo. This is the normal path.
- **Target repo is NOT on GitHub** → *only then* does the artifact fall back
  to committing here, into `generated/`, because the pipeline-source fetch is
  GitHub-only while the actual target repo reaches the worker through separate
  Gitea-sidecar mirroring (`workspace_repo`). This namespace exists purely so
  that non-GitHub target repos still have a GitHub-hosted place to park the
  compiled `.dot` + its `plan.json`.

A dedicated third "goal-plan-runs" repo was considered and rejected (design
doc, "Rejected Alternatives") — it would cost an extra repo to provision and
keep alive. Segregating into `generated/` here, on disposable branches, gives
the same isolation with no new infrastructure.

## The hard rules

1. **Never on `main`.** Generated artifacts only ever live on disposable
   `resolve/goal-plan-<run-id>` branches, exactly like the Amplifier Resolve
   platform's own `resolve/{instance_id}` bookkeeping branches. If you ever
   see a task-specific `plan.json` or a compiled parent `.dot` under
   `generated/` on `main`, that is a mistake to be reverted, not a reference
   to be preserved.
2. **Not curated content.** These files are never reviewed as reference
   pipelines. They are the byproduct of one compiler run against one piece of
   work, and they are disposable the moment that run is delivered.
3. **Pruneable by design.** Because they are disposable, they are expected to
   be deleted on a schedule — see "Retention / prune policy" below.

## What lives here permanently (on `main`)

The **only** things under `generated/` that belong on `main` are this
`README.md` and the prune tool `prune-branches.sh`. They are the namespace's
documentation and housekeeping — the scaffolding that describes and cleans up
the ephemeral branches, not ephemeral artifacts themselves. Everything else
that ever appears under `generated/` is machine-generated and belongs on a
`resolve/goal-plan-*` branch, never here on `main`.

**No `.gitignore` entry is used for `generated/`, by design.** There is no
local-only scratch path here to ignore: the compiled `plan.json` + parent
`.dot` are the deliverable and *must* be committed (onto a disposable branch,
then fetched over `git+https://`), while this `README.md` and
`prune-branches.sh` are intentional `main` content. The same artifact is
forbidden on `main` but required on `resolve/goal-plan-*` branches — a
distinction `.gitignore` cannot make, since it is branch-blind. Keeping those
artifacts off `main` is therefore a **branch-discipline** guarantee (always
commit them on `resolve/goal-plan-<run-id>`, never `main`), not something a
`.gitignore` rule could or should enforce.

## Retention / prune policy

There is **no CI cron in this repo** (verified: `.github/workflows/` contains
only `pr-review-exhaustive.yml`, which triggers on `pull_request` only — no
`schedule:` trigger anywhere). So retention is a **documented, manual**
operation for now. That is acceptable; leaving it undocumented is not.

**Policy: delete any `resolve/goal-plan-*` branch in this repo whose tip
commit is older than 30 days.** Thirty days is a deliberate default — long
enough that an in-flight or recently-delivered submission is never yanked out
from under a running or just-finished job, short enough that abandoned
one-off branches do not accumulate indefinitely. These branches are
disposable by construction (rule 1 above), so there is nothing to preserve
past the life of the run that created them; adjust the window with `--days`
if a longer audit trail is ever needed.

Run the bundled script from a checkout of this repo. It is **dry-run by
default** and only deletes when you pass `--delete`:

```bash
# Preview what a 30-day prune would delete (safe, no writes):
./generated/prune-branches.sh

# Actually delete branches older than 30 days on origin:
./generated/prune-branches.sh --delete

# Use a different age window (e.g. 14 days):
./generated/prune-branches.sh --days 14 --delete
```

If you would rather not run the script, the equivalent copy-pasteable command
is:

```bash
# Dry run: list resolve/goal-plan-* branches on origin older than 30 days.
git fetch --prune origin
cutoff=$(( $(date +%s) - 30*24*60*60 ))
git for-each-ref --format='%(refname:short) %(committerdate:unix)' \
  'refs/remotes/origin/resolve/goal-plan-*' \
| while read -r ref ts; do
    [ "$ts" -lt "$cutoff" ] && echo "stale: ${ref#origin/}"
  done

# To delete one, once you've reviewed the list:
#   git push origin --delete resolve/goal-plan-<run-id>
```

See `prune-branches.sh` for the safe, flag-driven version of exactly this.
