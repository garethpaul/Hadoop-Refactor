# LzoIndex Byte Count Guard

status: completed

## Context

LZO index files contain 8-byte block offsets. `LzoIndex.readIndex` previously
computed the block count with integer division, which could silently ignore
trailing bytes in a malformed index file.

## Objectives

- Reject index byte counts that are not divisible by 8.
- Keep valid index byte counts converting to block counts unchanged.
- Cover the malformed byte-count boundary in the no-Ant Java smoke harness.
- Document the guard in the baseline and maintenance notes.

## Verification

- `make check`
- `git diff --check`
