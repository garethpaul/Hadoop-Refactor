# Lzop Output Construction Pool Ownership

Status: Completed
Date: 2026-06-26

## Problem

The no-argument output factories borrow a compressor from `CodecPool` before
native-library checks, configuration parsing, and `LzopOutputStream` header
construction. Unlike the equivalent input factory, failures in those steps do
not return the borrowed compressor, so repeated invalid configuration or
failing output streams can drain pooled native resources.

## Decision

- Route both internally pooled output factories through one ownership helper.
- Return the borrowed compressor on checked construction failure, runtime
  configuration/native failure, and `Error`, then rethrow the original failure.
- Transfer ownership to `LzopOutputStream` only after successful construction;
  its existing idempotent close remains the normal return path.
- Preserve the explicit-compressor overload behavior and Java 6 compatibility.

## Verification

- Add a RED source contract matching the existing pooled-decompressor failure
  boundary.
- Add hostile mutations for missing checked, runtime, and `Error` cleanup.
- Run the focused hostile harness, mutation suite, `make check`, full Java
  source compilation, syntax checks, and hosted CodeQL.

## Results

- RED: the hostile-stream source contract failed because no pooled-output
  ownership helper existed.
- GREEN: both internally borrowing output factories now use one helper that
  returns the compressor for `IOException`, `RuntimeException`, and `Error`.
- All 18 isolated hostile mutations were rejected, including bypass of either
  borrowing factory, removal of each new throwable-class cleanup, and the
  previously protected input constructor `Error` cleanup.
- `make check`, external-directory `make check`, Python compilation, shell
  syntax, and `git diff --check` pass.
- The complete production Java tree compiles with `javac -source 1.6 -target
  1.6` against the checked-in Hadoop jar and commons-logging API.
- Native LZO and legacy Ant/Ivy integration remain dependent on the documented
  external toolchain; hosted checks and CodeQL remain required before merge.
