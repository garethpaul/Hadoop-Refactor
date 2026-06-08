# Hadoop Refactor Native Packaging Guard Plan

status: completed

## Context

`src/native/packageNativeHadoop.sh` copies prebuilt and custom-built native
libraries into the Ant distribution tree. The legacy script parsed `ls` output
and used unquoted paths, which made packaging brittle for platform or build
directories containing spaces.

## Objectives

- Preserve the existing native library packaging behavior.
- Avoid parsing `ls` output for platform directories.
- Quote native build, source, and distribution paths.
- Add a no-Ant fixture test to the static `make check` baseline.
- Document the native packaging guardrail.

## Work Items

1. Reworked `packageNativeHadoop.sh` around a quoted `copy_libraries` helper.
2. Added required environment validation for the Ant-provided native directory variables.
3. Extended `scripts/check-baseline.py` with a temporary prebuilt/custom native library fixture.
4. Updated README, VISION, CHANGES, and this plan with the new guardrail.

## Verification

- `make check`
- `python3 scripts/check-baseline.py`
- `git diff --check`
