# Reject Zero-Progress Lzop Reads

status: completed

## Context

`LzopInputStream.readFully` loops until a requested byte count is satisfied and
already fails on end-of-stream. If an input implementation returns zero for a
positive-length read, however, neither the remaining length nor offset changes,
so malformed or non-conforming input can hold a worker in an unbounded loop.

## Priority

This is the highest-value remaining isolated Lzop input boundary because it can
turn one stalled stream into permanent CPU occupancy. The fix is local to the
existing read helper and does not change valid LZO headers, blocks, checksums,
index formats, or native decompression.

## Scope

1. Reject zero-progress positive-length reads with a descriptive `IOException`.
2. Preserve successful multi-read completion and existing `EOFException`
   behavior.
3. Add a generated Java smoke harness with a bounded subprocess timeout.
4. Add mutation-sensitive source, harness, plan, and project-guidance contracts.

## Verification Plan

- Run the focused Java harness, all four Make gates, checker compilation, XML
  parsing, maintained shell syntax, `git diff --check`, and intended-file
  artifact and secret scans.
- Remove the zero-progress rejection, remove the harness scenario, and remove
  the subprocess timeout; every hostile mutation must fail.
- Push a stacked pull request and take one bounded exact-head workflow and
  code-scanning snapshot without polling.

## Risk And Rollback

Conforming blocking streams are unchanged because positive-length reads return
data or EOF. A non-conforming stream that previously spun forever now fails
closed. Rollback restores the unbounded loop; no persisted data or index format
changes exist.

## Work Completed

- Added a checked zero-progress failure to the existing `readFully` loop while
  preserving chunked reads and `EOFException` behavior.
- Added a Java 6-compatible smoke harness compiled from the extracted production
  helper and bounded its execution with a five-second timeout.
- Added source, harness, plan, and project-guidance contracts.

## Verification Completed

- The focused Lzop read-progress smoke harness passed.
- All four Make gates passed with the updated deterministic baseline.
- `python3 -m py_compile scripts/check-baseline.py`, maintained shell syntax,
  XML parsing, and `git diff --check` passed.
- The zero-progress rejection removal mutation failed.
- The harness-scenario removal mutation failed.
- The subprocess-timeout removal mutation failed.
- Intended-file generated-artifact and secret-pattern scans passed.
- The hosted pull-request and CodeQL snapshot is recorded separately after
  push; this plan claims only completed pre-push verification above.
