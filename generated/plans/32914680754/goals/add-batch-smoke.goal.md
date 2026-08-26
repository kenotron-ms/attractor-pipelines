# Lane add-batch-smoke

## Outcome

Create the file `BATCH_SMOKE.md` at the repository root. The file must contain the exact line:

    batch delivery verified

## Steps

1. In the lane's git worktree, create (or overwrite) the file `BATCH_SMOKE.md` at the repository root with at minimum the following content:

```
batch delivery verified
```

The file may contain additional lines (e.g. a heading or timestamp), but must include `batch delivery verified` as a complete line.

2. Stage and commit the file.

## Done when

The following command exits 0 when run at the repository root inside the lane's worktree:

```
grep -q "batch delivery verified" BATCH_SMOKE.md
```

This is the exact check the parent verifier runs (`verifier_argv`).

## Final step (REQUIRED)

After the work is done and the check above passes, write the file `artifacts/add-batch-smoke.done` containing exactly:

    add-batch-smoke:ok

and nothing else (no trailing newline beyond what is required — the content must be exactly `add-batch-smoke:ok`).

This marker file is how the batch orchestrator confirms the lane finished. It must be the LAST action taken.
