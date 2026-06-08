# Hadoop Refactor Legacy Build Baseline Plan

status: completed

## Context

`Hadoop-Refactor` is a preserved Hadoop-LZO project with Ant/Ivy Java builds and native LZO build scripts. This host has Java 8 but does not have Ant installed, so local verification needs a static baseline plus any available syntax checks unless a maintainer provides the full legacy Hadoop/LZO toolchain.

## Objectives

- Keep legacy Ant/Ivy build metadata explicit and safer for future rebuilds.
- Use HTTPS for checked-in Maven/Ivy download endpoints where those endpoints are controlled by the build file.
- Add a local `make check` baseline that verifies XML, shell syntax, source inventory, and documentation guardrails without requiring Ant.
- Document the Ant, Java 8, Hadoop 0.20/CDH3, native LZO, and static-check expectations.

## Verification

- `make check`
- `python3 scripts/check-baseline.py`
- `git diff --check`
