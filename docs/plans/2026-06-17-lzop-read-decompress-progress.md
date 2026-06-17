# Reject Zero-Progress Lzop Read Decompression

status: active

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

Pending implementation.

## Verification Completed

Pending implementation and validation.
