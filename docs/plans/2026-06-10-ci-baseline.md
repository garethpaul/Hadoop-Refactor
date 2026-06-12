# CI Baseline

status: completed

## Context

The repository had a local `make check` baseline for legacy Hadoop/LZO metadata,
native shell scripts, and Java smoke checks, but no hosted workflow ran it for
pushes and pull requests.

## Changes

- Added a least-privilege GitHub Actions workflow that installs Python 3.12 and
  Temurin Java 8 before running `make check`.
- Pinned checkout, setup-python, and setup-java by commit; cancelled superseded
  runs and bounded execution with a timeout.
- Disabled checkout credential persistence and retained read-only repository
  permissions.
- Extended the baseline checker and documentation so the hosted CI path stays
  visible, structurally enforced, and covered by local verification.

## Verification

- `make check`
- Workflow YAML parse
- Hostile workflow mutation checks
- Hosted Python 3.12 and Temurin Java 8 GitHub Actions run
