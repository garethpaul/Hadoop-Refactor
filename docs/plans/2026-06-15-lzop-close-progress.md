# Reject Zero-Progress Lzop Close Drains

status: completed

## Context

`LzopInputStream.close` repeatedly calls `Decompressor.decompress` until the
decompressor reports `finished()`. If an unfinished decompressor returns zero,
for example because it needs more input, the loop changes no state and can hold
the closing thread indefinitely.

## Priority

This is a distinct denial-of-service boundary after the read-path progress
guard. The failure is reachable while closing a partially consumed or malformed
stream, and the fix can remain isolated from valid headers, checksums, block
formats, indexes, and native decompression behavior.

## Scope

1. Move close-time decompressor draining into a package-private helper.
2. Reject zero or negative decompression progress while `finished()` remains
   false with a descriptive `IOException`.
3. Preserve successful multi-step draining and existing close, checksum, and
   `CodecPool` cleanup ordering.
4. Add a Java 6-compatible fake-decompressor harness with a bounded subprocess
   timeout.
5. Add mutation-sensitive source, harness, plan, and project-guidance contracts.

## Verification Plan

- Reproduce the pre-fix close hang with a bounded standalone harness.
- Run the focused Java harness, all four Make gates, checker compilation, XML
  parsing, maintained shell syntax, `git diff --check`, and intended-file
  artifact and secret scans.
- Remove the progress rejection, remove the unfinished zero-progress scenario,
  remove successful multi-step coverage, and remove the subprocess timeout;
  every hostile mutation must fail.
- Push a stacked pull request and take one bounded exact-head workflow and
  security-alert snapshot without polling.

## Risk And Rollback

Conforming decompressors that produce bytes until completion are unchanged. An
unfinished decompressor that cannot produce output now fails closed instead of
spinning. Rollback restores the unbounded close loop; no persisted data, index,
or wire-format change exists.

## Work Completed

- Added a package-private close-drain helper that rejects non-positive progress.
- Preserved underlying-stream closure, checksum behavior for successful drains,
  pooled-decompressor return, and propagation of the first close failure.
- Added a Java 6-compatible fake-decompressor smoke harness covering successful
  multi-step draining and zero-progress rejection under a bounded timeout.
- Added source, harness, cleanup, plan, and project-guidance contracts.

## Verification Completed

- The pre-fix close hang reproduced under a two-second standalone timeout.
- The focused Lzop close-progress smoke harness passed.
- All four Make gates passed from the repository root, and the absolute
  Makefile passed from an external directory.
- `python3 -m py_compile scripts/check-baseline.py`, maintained shell syntax,
  XML parsing, and `git diff --check` passed.
- The progress-rejection removal mutation failed.
- The successful-drain scenario removal mutation failed.
- The cleanup-preservation mutation failed.
- The subprocess-timeout removal mutation failed.
- The plan-evidence removal mutation failed.
- Intended-file generated-artifact, dependency, secret-pattern, conflict-marker,
  and whitespace audits passed.
- The hosted pull-request and security-alert snapshot is recorded separately
  after push; this plan claims only completed pre-push verification above.
