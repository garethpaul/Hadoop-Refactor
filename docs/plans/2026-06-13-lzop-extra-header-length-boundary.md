# Bound Lzop Extra Header Lengths

status: completed

## Context

When the lzop extra-field flag is set, `LzopInputStream.readHeader` reads an
untrusted four-byte length and passes it directly to `new byte[hitem]`. A
negative signed value raises an unchecked `NegativeArraySizeException`, while a
large positive value can request a multi-gigabyte allocation before the field
checksum is validated.

## Priority

Compressed files may be untrusted input, and header parsing occurs before block
decompression. The parser should reject impossible allocation requests with a
checked `IOException` at the same bounded-input layer already used for LZO
block sizes.

## Scope

1. Validate extra-header lengths before allocation, accepting zero through
   `LzoCodec.MAX_BLOCK_SIZE` and rejecting negative or larger values.
2. Add a Java 6-compatible smoke harness that compiles the real production
   validator with the maintained Hadoop jar and lightweight logging stubs.
3. Add source contracts and mutation-resistant checks for the call ordering and
   accepted/rejected boundaries.
4. Synchronize the README, security guidance, vision, change history, and this
   completed plan.

## Verification Plan

- Run the focused Java smoke harness, checker compilation, all four Make gates,
  maintained shell syntax checks, XML parsing, diff checks, and intended-file
  artifact and secret scans.
- Remove the validator call, remove negative-length rejection, remove the upper
  bound, and remove the harness contract; every hostile mutation must fail.
- Push a stacked pull request and take bounded exact-head workflow, check, and
  CodeQL snapshots without an unbounded polling loop.

## Risk And Rollback

Extra fields larger than 64 MiB will now be rejected even if enough memory is
available. Zero-length and bounded fields retain their current parsing and
checksum behavior. Rollback restores unbounded allocation from file-controlled
metadata; there is no stored-data migration.

## Work Completed

- Added a package-private production validator that accepts zero through the
  existing 64 MiB maximum block size and returns checked `IOException` failures
  for negative or oversized extra-header lengths.
- Routed the lzop extra-field allocation through that validator before creating
  the byte array or reading checksum-covered field data.
- Added a Java 6-compatible smoke harness that compiles and invokes the real
  validator at both accepted and rejected boundaries.
- Extended source, harness, documentation, and plan contracts across the
  maintained baseline.

## Verification Completed

- The focused lzop extra-header smoke harness passed for zero, 64 MiB, negative
  one, and 64 MiB plus one.
- All four Make gates passed with the updated deterministic baseline.
- `python3 -m py_compile scripts/check-baseline.py`, maintained shell syntax,
  XML parsing, and `git diff --check` passed.
- Validator-call removal failed the source contract.
- Negative-bound removal and upper-bound removal each failed both the source
  contract and executable Java harness.
- Harness-invocation removal failed the smoke-coverage contract.
- Intended-file generated-artifact and secret-pattern scans passed.
- The hosted pull-request and CodeQL snapshot is recorded separately after
  push; this plan claims only the completed pre-push verification above.
