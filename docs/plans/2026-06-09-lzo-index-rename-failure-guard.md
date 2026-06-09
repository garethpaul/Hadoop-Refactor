# LZO Index Rename Failure Guard

status: completed

## Context

`LzoIndex.createIndex` writes a temporary `.index.tmp` file and then renames it
to the final `.index` path after the compressed file scan succeeds. Hadoop
`FileSystem.rename` reports failure with a boolean return value, but the
previous code ignored that value and could report successful indexing even when
the final index file was not published.

## Completed Scope

- Added a small `commitIndexFile` helper that fails when the temporary index
  cannot be renamed to the final index path.
- Cleaned up the temporary index file on rename failure.
- Covered the failure path in the existing Java smoke harness with a fake
  filesystem that refuses the rename.
- Extended the static baseline and docs to preserve the temporary index
  publication guard.

## Verification

- `make check`
- `git diff --check`
