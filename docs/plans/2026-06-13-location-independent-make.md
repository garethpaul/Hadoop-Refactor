# Location-Independent Hadoop Verification

status: completed

## Context

The maintained baseline passes from the checkout, but invoking the absolute
Makefile from another working directory makes Python resolve
`scripts/check-baseline.py` relative to the caller. Automation should be able
to load the repository Makefile without first changing directories.

## Priority

This is the next narrow reliability gap because it affects local wrappers and
multi-repository automation while requiring no change to legacy Hadoop, Java,
native LZO, dependency, or workflow behavior.

## Scope

1. Derive the repository root from `MAKEFILE_LIST`.
2. Invoke the maintained Python checker through that rooted path.
3. Add completed-plan, external-run, guidance, and hostile-mutation contracts.
4. Preserve all Java, native, Ant/Ivy, dependency, and workflow files.

## Verification Plan

- Run lint, test, build, and check from the checkout and from a temporary
  directory through the absolute Makefile path.
- Run Python compilation, maintained shell syntax, Ant/Ivy XML parsing, and
  `git diff --check`.
- Reject root derivation, checker invocation, plan status/evidence, and
  documentation mutations.
- Inspect exact intended paths, secrets, and generated artifacts.

## Risk And Rollback

The change affects only verification path resolution. Rollback restores the
caller-relative recipe; no runtime state or data migration exists.

## Work Completed

- Derived `ROOT` from the loaded Makefile and invoked the maintained Python
  checker through its absolute repository path.
- Added baseline contracts for rooted invocation, completed plan evidence, and
  synchronized README/changelog guidance.
- Preserved all Java, native, Ant/Ivy, dependency, and workflow files.

## Verification Completed

- Root and external-directory Make gates passed for `lint`, `test`, `build`,
  and `check`; every target exercised the complete legacy baseline.
- The root-derivation mutation failed.
- The checker-invocation mutation failed.
- The plan-status mutation failed.
- The plan-evidence mutation failed.
- The documentation mutation failed.
- Python compilation, maintained shell syntax, Ant/Ivy XML parsing, diff
  hygiene, exact intended-path review, secret scanning, and generated-artifact
  inspection passed.
