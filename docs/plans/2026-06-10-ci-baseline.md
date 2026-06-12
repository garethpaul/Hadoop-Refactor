# CI Baseline

status: completed

## Context

The repository had a local `make check` baseline for legacy Hadoop/LZO metadata,
native shell scripts, and Java smoke checks, but no hosted workflow ran it for
pushes and pull requests.

## Changes

- Added a GitHub Actions workflow that installs Python 3.12 and Java 8 before
  running `make check`.
- Extended the baseline checker and documentation so the hosted CI path stays
  visible and covered by local verification.

## Verification

- `make check`
