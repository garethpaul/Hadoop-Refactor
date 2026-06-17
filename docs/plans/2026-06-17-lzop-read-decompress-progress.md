# Reject Zero-Progress Lzop Read Decompression

status: completed

## Context

`LzopInputStream.decompress` loops while the decompressor returns zero. It can
load more compressed data when `needsInput()` is true, but an unfinished
decompressor that returns zero without requesting input changes no state and
can hold a normal read thread indefinitely. The existing close-drain guard does
not cover this read path.

## Priority

This is a distinct malformed-stream denial-of-service boundary. It is reachable
during ordinary reads, can be reproduced with a deterministic fake
decompressor, and can be fixed without changing valid headers, checksums,
blocks, indexes, native code, or public APIs.

## Scope

1. Add a package-private helper that requires more input after a zero-output
   read iteration and otherwise raises a descriptive `IOException`.
2. Call the helper before loading the next compressed chunk, preserving valid
   zero-output transitions that explicitly request input.
3. Add a Java 6-compatible smoke harness for accepted input requests and
   rejected stalled decompression under a bounded subprocess timeout.
4. Add mutation-sensitive source, harness, guidance, and completed-plan
   contracts to the maintained baseline.

## Verification Plan

- Reproduce the pre-fix read hang with a bounded standalone harness.
- Run the focused Java harness, all four Make gates, the absolute external
  Makefile gate, checker compilation, XML and shell syntax checks, and
  `git diff --check`.
- Remove the progress guard, remove the stalled scenario, remove the accepted
  input-request scenario, remove the subprocess timeout, and stale the plan;
  every hostile mutation must fail.
- Run final generated-artifact, dependency, credential-pattern,
  conflict-marker, file-mode, clean-worktree, and upstream-alignment audits.
- Push a stacked pull request and take one bounded exact-head workflow and
  security-alert snapshot without polling.

## Risk And Rollback

Conforming decompressors that request input after producing no output remain
unchanged. An unfinished decompressor that neither produces output nor requests
input now fails closed instead of spinning. Rollback restores the unbounded
read loop; no persisted data, index, or wire-format change exists.

## Work Completed

- Added `requireInputAfterZeroProgress` and called it after zero-output
  decompression iterations that have not reached a valid terminal boundary.
- Preserved the existing transition that loads another compressed chunk when
  the decompressor explicitly requests input.
- Added a Java 6-compatible fake-decompressor harness for accepted input
  requests and rejected stalled states under a bounded subprocess timeout.
- Added mutation-sensitive source, scenario, timeout, guidance, and plan
  contracts to the maintained baseline.

## Verification Completed

- The pre-fix read hang reproduced under a two-second standalone timeout.
- The focused Lzop read-decompress progress smoke harness passed.
- All four Make gates passed separately: `make lint`, `make test`, `make build`,
  and `make check`.
- The absolute Makefile check passed from an external directory.
- `python3 -m py_compile scripts/check-baseline.py`, maintained shell syntax,
  XML parsing, and `git diff --check` passed.
- Six isolated mutations were rejected: guard-call removal, weakened predicate,
  stalled-scenario removal, input-request scenario removal, timeout removal,
  and guidance removal.
- Compound Engineering review found no actionable findings.
- Generated-artifact, dependency, credential-pattern, conflict-marker,
  file-mode, clean-worktree, and exact-upstream audits passed.
- Both canonical implementation-head checks passed at
  `dd362ef705d1c48c1b00e7581450a9365b73ee22`: push run 27664412273 and
  pull-request run 27664415741. PR #9 was OPEN, CLEAN, and MERGEABLE, and the
  exact branch had zero open code-scanning, Dependabot, and secret-scanning
  alerts.
- Ant, native LZO libraries, a Hadoop cluster, and production compressed
  corpora were not available or exercised.
