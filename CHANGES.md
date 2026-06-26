# Changes

## 2026-06-26 13:40 UTC - P1 - output compression progress

- Summary: reject zero-byte Lzop compression calls that leave byte counts,
  input demand, and completion state unchanged, preventing unbounded write and
  finish loops while preserving legitimate state-only progress.
- Files: `LzopOutputStream.java`, hostile-stream and mutation harnesses,
  baseline contracts, maintenance docs, and the implementation plan.
- Tests: executable Java 6-compatible progress cases, production call-site
  mutation rejection, `make check`, source compilation, and hosted CI.
- Findings: the legacy output path inherited an unbounded compressor loop and
  had no executable small/uncompressible-output progress contract.
- Blockers: full native LZO/Ant integration remains dependent on the documented
  Hadoop 0.20/CDH3-era toolchain.
- Next action: refresh small/uncompressible file and index-generation coverage
  without combining it with native or Hadoop API modernization.

## 2026-06-26 01:48 UTC - P1 - output close cleanup

- Made `LzopOutputStream.close()` idempotent before finalization and preserved
  the first IOException while independently closing data and index outputs.
- Guaranteed compressor-pool return after finish, trailer, or close failures.
- Added an executable Java 6-compatible lifecycle harness proving that both
  failing outputs close while the first failure remains authoritative.

- Rejected missing or partial block trailers, unknown high header flags, negative or
  oversized decompressor output, and true read/close stalls while preserving
  legitimate input requests.
- Streamed bounded lzop extra-header fields through fixed-size checksum buffers
  and made decompressor-pool release idempotent on close and construction
  failure.

- Close-time Lzop decompression rejects zero progress so malformed streams cannot hang cleanup.
- Read-time Lzop decompression rejects zero progress without an input request so malformed streams cannot hang normal reads.

## 2026-06-13

- Made every Make verification target derive the checkout root so the legacy
  baseline works from external directories.
- Rejected zero-progress positive-length Lzop reads so malformed or
  non-conforming streams cannot hold the read loop indefinitely.
- Bounded lzop extra-header field allocation at the existing maximum block size
  and added an executable Java 6-compatible boundary harness.
- Rejected compressed LZO block lengths larger than their declared
  uncompressed lengths before decompression, index generation, or split
  scanning can continue across malformed input.

## 2026-06-12

- Propagated distributed input traversal failures so missing, inaccessible, or
  unreadable paths cannot be omitted from a successful indexing command.

## 2026-06-10

- Routed distributed index-writer publication through the checked LZO index
  commit helper so failed filesystem renames cannot be reported as success.
- Added a pinned, least-privilege GitHub Actions workflow that installs Python
  3.12 and Temurin Java 8 before running `make check`, with credential-free
  checkout.
- Extended the baseline checker and docs to require the hosted CI verification
  path.

## 2026-06-09

- Added `make lint`, `make test`, and `make build` aliases so local verification
  has the expected pre-push gate targets in addition to `make check`.
- Hardened `LzoIndex` empty-index boundary helpers so direct callers receive
  `NOT_FOUND` or file-size alignment instead of a null-pointer failure.
- Rejected malformed index byte counts that are not aligned to 8-byte block
  offsets.
- Rejected malformed index positions that are negative, duplicate, or
  decreasing before split alignment relies on them.
- Rejected oversized LZO block sizes before index generation, split readers, or
  stream decompression continue across a corrupt file.
- Preserved missing-index fallback while surfacing non-missing `LzoIndex`
  index open failures.
- Surfaced LZO index rename failures so failed temporary index publication is
  cleaned up instead of reported as success.

## 2026-06-08

- Switched checked-in Ivy and Maven Ant task download endpoints from HTTP to HTTPS.
- Added `make check` and a static baseline verifier for legacy build metadata, shell syntax, source inventory, and documentation guardrails.
- Hardened native packaging path handling and added a fixture check for prebuilt and custom native libraries.
- Hardened the build revision helper quoting and added archive fallback fixture coverage for paths containing spaces.
- Documented the Java 8, Ant/Ivy, Hadoop 0.20/CDH3, and native LZO expectations for future rebuilds.
