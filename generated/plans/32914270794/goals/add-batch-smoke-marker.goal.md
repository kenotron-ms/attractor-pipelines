# Lane add-batch-smoke-marker

## Outcome

Create the file `BATCH_SMOKE.md` at the repository root. The file must contain the exact line:

    batch delivery verified

## Steps

1. Create (or overwrite) the file `BATCH_SMOKE.md` at the repository root with content that includes the line `batch delivery verified`. A minimal file with just that single line is sufficient.

## Done when

The following command exits 0:

    grep -q "batch delivery verified" BATCH_SMOKE.md

This is the machine check that confirms the file exists and contains the required line.

## Final step (REQUIRED)

After the work is done and the check above passes, write the file `artifacts/add-batch-smoke-marker.done` containing exactly the text:

    add-batch-smoke-marker:ok

and nothing else (no trailing newline beyond what is required, no extra content). This marker file is how the batch orchestrator confirms this lane finished -- it must be the LAST action taken.
