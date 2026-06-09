# LZO Block Size Boundary

status: completed

## Context

LZO index generation, stream decompression, and split-record scanning all read
block-size fields from compressed files. Existing guards rejected malformed
index byte counts and some nonpositive compressed block lengths, but oversized
block sizes could still drive seeks or decompression work across corrupt input.

## Completed Scope

- Added an indexer block-size validator for uncompressed and compressed sizes.
- Rejected oversized LZO block sizes before `LzoIndex.createIndex` seeks to the
  next block.
- Rejected zero, negative, and oversized compressed sizes in `LzopInputStream`.
- Rejected oversized sizes in `LzoSplitRecordReader` before split indexing seeks
  across the file.
- Extended the Java smoke harness and static baseline guard, then documented
  the corrupt-input boundary in README, VISION, CHANGES, and SECURITY.

## Verification

- `make check`
- `git diff --check`
