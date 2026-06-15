# Reject Zero-Progress Lzop Close Drains

status: planned

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

