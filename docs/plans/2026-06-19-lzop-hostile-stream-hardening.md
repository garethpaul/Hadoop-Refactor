# Lzop hostile-stream hardening

status: completed

## Scope

Review the stacked parser changes in pull requests #3 through #9 against
malformed or adversarial lzop streams, with executable Java evidence rather
than source-shape checks alone.

## Correctness boundaries

- Require the mandatory four-byte block terminator and reject partial or
  missing block-size words as truncation.
- Interpret block-size words as unsigned before applying the 64 MiB limit.
- Reject unknown header flags and stream bounded extra-header bytes through a
  fixed-size checksum buffer.
- Cap decompressor writes to the remaining declared block length and reject
  negative or oversized decompressor results.
- Verify a completed block before accepting the next size or end marker.
- Distinguish a legitimate decompressor input request from a true read or
  close-time stall.
- Return pooled decompressors exactly once, including constructor failures.

## Verification completed

- The focused hostile-stream harness reproduced the pre-fix truncation,
  signed-length, output-overrun, header-allocation, checksum, progress, and
  lifecycle failures before the production fixes.
- `make check` passed with the focused Java harness and twelve isolated hostile
  mutations rejected.
- The absolute Makefile gate passed from an external working directory.
- The complete production Java source tree compiled with OpenJDK 11 using the
  checked-in Hadoop jar and the declared commons-logging 1.0.4 dependency.
- Python checker sources compiled and `git diff --check` passed.

## Residual integration risk

Apache Ant, a native LZO library, a Hadoop cluster, and representative
production lzop corpora were unavailable locally. The review therefore does
not claim JNI decompression, native library loading, Hadoop split execution,
distributed filesystem behavior, or performance compatibility under a real
cluster. Hosted gates provide the authoritative repository baseline; native
and cluster integration still require an environment with the legacy Hadoop
0.20/CDH3 and LZO toolchain.
