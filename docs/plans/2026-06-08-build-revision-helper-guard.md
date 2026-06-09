# Build Revision Helper Guard

status: completed

## Context

`src/get_build_revision.sh` is used by the legacy Ant build to stamp artifacts
with a package-provided revision, the current Git revision, or the
`.archive-version` value present in exported source archives. The helper used
unquoted shell expansions, which made overrides and archive fallbacks brittle
when paths or values contained spaces.

## Objectives

- Preserve the existing revision source order: `BUILD_REVISION`, Git, archive
  version, then `Unknown build revision`.
- Quote revision output and script-relative archive paths.
- Keep archive fallback working when the exported source path contains spaces.
- Add no-Ant static fixture coverage to `scripts/check-baseline.py`.

## Verification

- `make check`
- `python3 scripts/check-baseline.py`
- `git diff --check`
