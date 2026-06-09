# Changes

## 2026-06-09

- Hardened `LzoIndex` empty-index boundary helpers so direct callers receive
  `NOT_FOUND` or file-size alignment instead of a null-pointer failure.
- Rejected malformed index byte counts that are not aligned to 8-byte block
  offsets.

## 2026-06-08

- Switched checked-in Ivy and Maven Ant task download endpoints from HTTP to HTTPS.
- Added `make check` and a static baseline verifier for legacy build metadata, shell syntax, source inventory, and documentation guardrails.
- Hardened native packaging path handling and added a fixture check for prebuilt and custom native libraries.
- Hardened the build revision helper quoting and added archive fallback fixture coverage for paths containing spaces.
- Documented the Java 8, Ant/Ivy, Hadoop 0.20/CDH3, and native LZO expectations for future rebuilds.
