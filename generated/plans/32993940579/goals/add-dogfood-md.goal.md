# Lane add-dogfood-md

## Outcome

Create the file `DOGFOOD.md` at the repository root containing exactly one line: `dogfood-ok`.

- File path (repo-relative): `DOGFOOD.md`
- File content: exactly the single line `dogfood-ok` (no trailing blank lines beyond the newline that terminates the line)

## Steps

1. In the repository root, create the file `DOGFOOD.md`.
2. Write exactly the text `dogfood-ok` followed by a newline as the sole content of that file.
3. Stage and commit the file.

## Done when

Run from the repo root:

```
bash -c "test -f DOGFOOD.md && grep -qx 'dogfood-ok' DOGFOOD.md"
```

This command must exit 0. It confirms the file exists and that `dogfood-ok` is a complete line in it.

## Final step (REQUIRED)

After the work is done and the check above passes, write the marker file:

```
artifacts/add-dogfood-md.done
```

containing exactly:

```
add-dogfood-md:ok
```

and nothing else (no trailing newline beyond what the file system requires is fine, but no extra text). This marker is how the batch orchestrator confirms the lane finished — it must be the LAST action taken.
