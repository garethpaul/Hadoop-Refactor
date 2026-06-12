# Distributed Input Error Propagation

status: completed

## Context

`DistributedLzoIndexer.walkPath` catches every `IOException`, logs a warning,
and returns normally. A missing path, permission failure, or directory listing
error can therefore remove inputs from the indexing set without failing the
command. When no paths remain, `run` prints that everything may already be
indexed and returns success.

Silent traversal failures are especially misleading for batch maintenance:
operators can receive a zero exit status even though no requested data was
examined or indexed.

## Priority

Input discovery defines the distributed job's scope. Filesystem errors must be
observable to automation before a partial or empty job can be reported as
successful.

## Prioritized Engineering Backlog

1. Propagate distributed input traversal failures now.
2. Preserve existing indexes until replacement publication succeeds in a
   dedicated filesystem-transaction design.
3. Add a maintained Hadoop integration environment if the project is revived.

## Requirements

- R1. `walkPath` must declare and propagate `IOException` from status, listing,
  existence, and index metadata operations.
- R2. Recursive traversal must stop on the first filesystem failure instead of
  silently omitting the affected path.
- R3. `run` and `main` must retain their existing exception-capable signatures
  so the Hadoop tool exits unsuccessfully when traversal fails.
- R4. Successful input discovery, existing-index skips, zero-length-index
  regeneration, and job configuration must remain unchanged.
- R5. The canonical baseline must reject a reintroduced local
  `catch (IOException)` in `walkPath` and require the throwing signature.

## Implementation Units

### U1. Fail fast during path discovery

- **Files:** `src/java/com/hadoop/compression/lzo/DistributedLzoIndexer.java`
- Remove the local filesystem exception handler and let `IOException`
  propagate through recursive discovery and `run`.

### U2. Extend the legacy baseline

- **Files:** `scripts/check-baseline.py`
- Isolate the `walkPath` method source and enforce its throwing, non-swallowing
  contract without downloading the historical dependency graph.

### U3. Update maintenance documentation

- **Files:** `README.md`, `SECURITY.md`, `VISION.md`, `CHANGES.md`
- Record that distributed input discovery fails closed on filesystem errors.

## Scope Boundaries

- Do not change MapReduce job configuration, index publication, or traversal
  filtering.
- Do not add dependencies or modernize Hadoop APIs.
- Do not continue with a partial indexing job after a requested path fails.

## Verification

- `make check`
- `python3 -m py_compile scripts/check-baseline.py`
- `git diff --check`
- A mutation restoring the `walkPath` exception-swallowing block must fail the
  baseline.

Completed on 2026-06-12 with `make check`, Python checker compilation, diff
hygiene, and an exception-swallowing mutation rejected by the baseline.
