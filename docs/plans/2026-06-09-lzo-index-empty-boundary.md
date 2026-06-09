# LzoIndex Empty Boundary Guard

status: completed

## Context

`LzoIndex.readIndex` returns an empty index when an `.lzo.index` file is
missing, allowing input formats to fall back to unsplittable processing. The
public `findNextPosition` and alignment helpers could still be called directly
on an empty index and dereference the unset block array.

## Objectives

- Keep empty indexes reporting `isEmpty() == true`.
- Return a zero block count for empty indexes.
- Return `LzoIndex.NOT_FOUND` from `findNextPosition` when no block positions
  exist.
- Keep `alignSliceStartToIndex` and `alignSliceEndToIndex` safe for direct
  empty-index callers.
- Add runnable no-Ant smoke coverage to `scripts/check-baseline.py` and mirror
  the expectation in the legacy JUnit test.

## Verification

- `make check`
- `git diff --check`
