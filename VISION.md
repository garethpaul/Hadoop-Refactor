## Hadoop Refactor Vision

This document explains the current state and direction of the project.
Project overview and developer docs: [`README.md`](README.md)

Hadoop Refactor is a Hadoop-LZO compression codebase focused on splittable LZO
support for Hadoop.

The repository is useful as a preserved Hadoop/LZO project with Java, native
build scripts, Ivy dependencies, and documentation around indexing compressed
files for parallel MapReduce processing. Project details live in
[`README.md`](README.md).

The goal is to keep the compression project buildable, license-compliant, and
clear about its legacy Hadoop/LZO assumptions.

The current focus is:

Priority:

- Preserve splittable LZO input/output and indexing behavior
- Keep native LZO, Java, Hadoop, Ant, and Ivy build requirements documented
- Maintain troubleshooting notes for headers, shared libraries, and `JAVA_HOME`
- Keep `scripts/check-baseline.py`, `make lint`, `make test`, `make build`,
  and `make check` passing for XML, shell, source inventory, native packaging,
  build revision stamping, and HTTPS build-download guardrails
- Keep GitHub Actions aligned with the Python and Java requirements of the
  local `make check` baseline
- Preserve propagation of distributed input traversal failures to automation
- Avoid broad Hadoop upgrades without compatibility planning

Next priorities:

- Separate native build modernization from Hadoop API changes
- Add or refresh tests around small/uncompressible files and index generation
- Clarify artifact publication status if the project is revived

Contribution rules:

- One PR = one focused compression, native build, Java API, or documentation change.
- Run the documented build/test path in a matching environment when possible.
- Preserve COPYING/license files and upstream-origin context.
- Document any Hadoop or LZO version compatibility change.

## Security And Integrity

Canonical security policy and reporting:

- [`SECURITY.md`](SECURITY.md)

Compression libraries process untrusted data. Changes should avoid unsafe native
memory behavior and keep malformed input handling explicit.

Native binaries and generated artifacts need provenance and should not be
silently replaced.

Current baseline: `make lint`, `make test`, `make build`, and `make check` run
`scripts/check-baseline.py`, which validates legacy Ant/Ivy metadata, native
shell script syntax, source/test inventory, build revision helper fallback
behavior, `LzoIndex` empty-index handling, malformed index byte counts,
malformed index positions, oversized LZO block sizes, impossible compressed
length relations, index open failures, index rename failures in direct and
distributed paths, distributed input traversal failures, and HTTPS download endpoints
without requiring Ant on the local host.
GitHub Actions installs Python 3.12 and Temurin Java 8 with pinned actions,
credential-free checkout, and read-only permissions, then runs `make check`
for pushes and pull requests.

## What We Will Not Merge (For Now)

- Native artifact replacements without build provenance
- Hadoop major-version migrations without compatibility notes
- License or attribution removals
- Compression behavior changes without tests or reproduction steps

This list is a roadmap guardrail, not a permanent rule.
Strong user demand and strong technical rationale can change it.
