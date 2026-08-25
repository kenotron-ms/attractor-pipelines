# Lane add-smoke-marker

## Outcome

Create the file `BATCH_SMOKE.md` at the repository root. The file must contain the exact line:

    batch delivery verified

## Steps

1. Create (or overwrite) the file `BATCH_SMOKE.md` at the repository root with content that includes the line `batch delivery verified`.
2. A minimal file body is sufficient — for example:

```
batch delivery verified
```

3. Stage and commit the file to the lane's working branch.

## Done when

The following command exits 0 (run from the repository root):

```
grep -q "batch delivery verified" BATCH_SMOKE.md
```

This is the exact verifier that the parent pipeline runs to confirm the lane's deliverable is present.

## Final step (REQUIRED)

After the work is done and the check above passes, write the file `artifacts/add-smoke-marker.done` containing exactly:

    add-smoke-marker:ok

and nothing else (no trailing newline beyond what the tool adds, no extra text). This marker file is how the batch orchestrator confirms the lane finished — it must be the LAST action taken.
