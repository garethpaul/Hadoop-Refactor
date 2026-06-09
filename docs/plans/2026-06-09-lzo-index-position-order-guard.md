# LZO Index Position Order Guard

status: completed

## Context

`LzoIndex.readIndex` already rejects malformed index files whose byte counts are
not aligned to 8-byte block offsets. The loaded offsets also need validation:
negative, duplicate, or decreasing positions violate the sorted index
assumption used by binary search and split alignment.

## Completed Scope

- Added index block position validation for negative and non-increasing offsets.
- Applied the validation while reading sidecar `.lzo.index` files.
- Extended the no-Ant Java smoke harness and static baseline guard for malformed
  index positions.
- Documented the corrupt-index boundary in README, VISION, CHANGES, and
  SECURITY.

## Verification

- `scripts/check-baseline.py`
- `make check`
- `git diff --check`
