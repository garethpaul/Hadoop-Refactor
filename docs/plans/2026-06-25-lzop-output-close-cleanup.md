# Lzop output close cleanup implementation plan

status: completed

1. Add a failing executable output-close lifecycle contract.
2. Add a Java 6-compatible first-failure close helper.
3. Make output close idempotent and cleanup-complete.
4. Add mutation-sensitive source contracts and change history.
5. Run portable Java and Python validation plus hosted CI.

## Verification completed

- The executable hostile-stream harness failed first because the production close helper was absent.
- The harness now proves both failing outputs close and the first IOException remains authoritative.
- `make check`, Python compilation, shell syntax, and diff validation pass locally.
- The complete production Java tree compiles at source/target 1.6 with the checked-in Hadoop jar and commons-logging API dependency.
