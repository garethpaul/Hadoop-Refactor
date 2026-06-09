# LzoIndex Open Failure Guard

status: completed

## Context

`LzoIndex.readIndex` should return an empty index when the sidecar
`.lzo.index` file is absent so the input format can fall back to unsplittable
processing. The previous catch block handled every `IOException` from opening
the index path, which could also hide permission, filesystem, or transient
storage failures as a normal missing-index case.

## Objectives

- Keep missing index files returning an empty `LzoIndex`.
- Propagate non-missing index open failures to callers.
- Cover both paths in the no-Ant Java smoke harness.
- Document the guard in the local baseline and maintenance notes.

## Verification

- `python3 scripts/check-baseline.py`
- `make check`
- `git diff --check`
