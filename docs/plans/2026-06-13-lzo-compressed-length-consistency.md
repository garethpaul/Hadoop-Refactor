# LZO Compressed Length Consistency

status: completed

## Context

LZO block headers declare both uncompressed and compressed lengths. A valid
compressed block is shorter than its uncompressed form, while an uncompressed
block uses equal lengths. A compressed length greater than the uncompressed
length is malformed.

The current stream reader treats greater lengths as uncompressed, and the
indexing paths can seek across them. This lets corrupt input select inconsistent
checksum handling and block boundaries instead of failing at the header.

## Priority

Compressed files are untrusted input. Rejecting an impossible length relation
before allocation, checksum selection, or seeking is a focused integrity guard
that does not require modernizing the historical Hadoop dependency graph.

## Requirements

- R1. Index generation must reject a compressed length greater than the
  declared uncompressed length before seeking.
- R2. Stream decompression must reject that malformed relation before checksum
  selection, allocation, or reading block data.
- R3. Distributed split scanning must reject the same relation before recording
  or seeking to the next block.
- R4. Equal lengths must remain the supported uncompressed-block form, and
  shorter compressed lengths must remain supported.
- R5. The deterministic baseline must execute a regression for the shared index
  validator and enforce the stream and split-reader contracts.

## Implementation Units

### U1. Enforce the block-header invariant

- **Files:** `src/java/com/hadoop/compression/lzo/LzoIndex.java`,
  `src/java/com/hadoop/compression/lzo/LzopInputStream.java`,
  `src/java/com/hadoop/mapreduce/LzoSplitRecordReader.java`
- Reject impossible compressed-length relations before the paths diverge into
  seeking, checksum handling, or decompression.

### U2. Extend deterministic verification

- **Files:** `scripts/check-baseline.py`
- Add an executable Java smoke assertion and source contracts covering all
  three maintained consumers.

### U3. Record the integrity boundary

- **Files:** `README.md`, `SECURITY.md`, `VISION.md`, `CHANGES.md`
- Document malformed compressed-length rejection and completed verification.

## Scope Boundaries

- Do not change valid compressed or uncompressed block behavior.
- Do not alter checksum algorithms, Hadoop APIs, or native LZO code.
- Do not download or modernize the historical Ant/Ivy dependency graph.

## Verification

- `make lint`
- `make test`
- `make build`
- `make check`
- `python3 -m py_compile scripts/check-baseline.py`
- `git diff --check`
- Hostile mutations removing each production guard, the smoke assertion, plan
  completion, or verification evidence must be rejected.

## Work Completed

- Rejected compressed lengths greater than declared uncompressed lengths in
  index generation, stream decompression, and distributed split scanning.
- Preserved equal-length uncompressed blocks and shorter compressed blocks.
- Added an executable Java smoke regression plus static contracts for all three
  production paths.
- Updated README, security, vision, and change documentation with the malformed
  input boundary.

## Verification Completed

- All four Make gates (`make lint`, `make test`, `make build`, and `make check`)
  passed locally with the executable `assertCompressedLengthConsistency` Java
  smoke regression.
- `python3 -m py_compile scripts/check-baseline.py` passed.
- `git diff --check` passed.
- Seven isolated hostile mutations were rejected: removal of each production
  guard, restoration of greater-than-or-equal uncompressed classification,
  removal of the smoke invocation, stale plan status, and missing verification
  evidence.
