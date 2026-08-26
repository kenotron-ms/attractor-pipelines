# Lane add-batch-smoke-marker

## Outcome

Create the file `BATCH_SMOKE.md` at the repository root. The file must contain, on its own line, the exact text:

    batch delivery verified

## Steps

1. Create (or overwrite) the file `BATCH_SMOKE.md` at the repository root with the following content:

```
batch delivery verified
```

   The file may contain only that line, or that line plus any surrounding whitespace — what matters is that `grep -q "batch delivery verified" BATCH_SMOKE.md` exits 0.

2. Stage and commit the file to the lane's working branch.

## Done when

The command:

    grep -q "batch delivery verified" BATCH_SMOKE.md

exits 0 when run from the repository root. This is the exact check the parent verifier runs.

## Final step (REQUIRED)

After the work is done and the check above passes, write the file `artifacts/add-batch-smoke-marker.done` containing exactly the text:

    add-batch-smoke-marker:ok

and nothing else (no trailing newline beyond what the tool writes). This marker is how the batch orchestrator confirms the lane finished — it must be the LAST action taken in this lane.
