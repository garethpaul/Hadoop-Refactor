# Changes

## 2026-06-13

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
