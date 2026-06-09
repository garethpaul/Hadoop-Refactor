# Hadoop-Refactor

<!-- README-OVERVIEW-IMAGE -->
![Project overview](docs/readme-overview.svg)

## Overview

`garethpaul/Hadoop-Refactor` is a public sample, documentation, or utility project. Refactor of Hadoop with compression

This README is based on the checked-in source, manifests, scripts, and repository metadata on the `master` branch. The project language mix found during review was: Java (29), shell (4), C (2), C/C++ headers (2).

## Repository Contents

- `CHANGES.md` - concise history of maintenance changes
- `Makefile` - local verification entry point
- `README.md` - project overview and local usage notes
- `build.xml` and `ivy.xml` - legacy Ant/Ivy build metadata
- `ivy` - source or example code
- `lib/hadoop-core-0.20.2-cdh3u1.jar` - checked-in legacy Hadoop dependency
- `scripts/check-baseline.py` - static legacy build verifier
- `SECURITY.md` - security reporting and disclosure guidance
- `src` - source or example code
- `VISION.md` - project direction and maintenance guardrails

Additional scan context:

- Source directories: ivy, src
- Dependency and build manifests: build.xml, ivy.xml, ivy/libraries.properties
- Entry points or build surfaces: `make check`, `ant test` in a matching legacy environment
- Test-looking files: src/test/com/hadoop/compression/lzo/TestLzoCodec.java, src/test/com/hadoop/compression/lzo/TestLzoRandData.java, src/test/com/hadoop/compression/lzo/TestLzopInputStream.java, src/test/com/hadoop/compression/lzo/TestLzopOutputStream.java, src/test/com/hadoop/mapreduce/TestLzoTextInputFormat.java, src/test/data/0.txt, src/test/data/100.txt, src/test/data/1000.txt, and 2 more

## Getting Started

### Prerequisites

- Git
- Python 3 for local static verification
- Java 8 is sufficient for the static baseline used here
- Ant, Ivy, native LZO headers/libraries, and a Hadoop 0.20/CDH3-compatible environment for full legacy builds

### Setup

```bash
git clone https://github.com/garethpaul/Hadoop-Refactor.git
cd Hadoop-Refactor
```

The checked-in Ant build targets Java 6 bytecode and uses legacy Hadoop 0.20/CDH3-era APIs. Use a matching Ant/Ivy/native LZO toolchain before treating full `ant test` results as authoritative.

## Running or Using the Project

- `build.xml` is the legacy build entry point.
- `src/java` contains the Hadoop/LZO Java implementation.
- `src/native` contains the native LZO build scripts and C bindings.

## Testing and Verification

Run the local static baseline:

```bash
make check
```

The baseline runs `scripts/check-baseline.py`, validates Ant/Ivy XML, checks shell syntax for native packaging scripts, verifies the Java/native/test source inventory, and confirms the checked-in Maven/Ivy download endpoints use HTTPS. It does not require Ant.
It also exercises `src/native/packageNativeHadoop.sh` with temporary native
library fixtures and `src/get_build_revision.sh` with archive-export fixtures
so quoted path handling stays covered.

For full legacy verification in a matching environment, run:

```bash
ant test
```

When the required SDK or runtime is unavailable, use static checks and source review first, then verify on a machine that has the matching platform toolchain.

## Configuration and Secrets

- No required secret or credential file was identified in the repository scan. If you add integrations later, keep secrets out of git.

## Security and Privacy Notes

- Review changes touching network requests, sockets, or service endpoints; examples from the scan include build.xml, ivy/ivysettings.xml, ivy.xml, src/java/com/hadoop/compression/lzo/CChecksum.java, and 6 more.
- Review changes touching file, media, JSON, XML, CSV, OCR, or data parsing; examples from the scan include build.xml, ivy/ivysettings.xml, ivy.xml, src/get_build_revision.sh, and 4 more.
- Review changes touching shell execution, subprocess, or dynamic evaluation; examples from the scan include src/native/config/ltmain.sh.
- Review changes touching database, model, or persistence code; examples from the scan include build.xml.

## Maintenance Notes

- See `SECURITY.md` for vulnerability reporting and safe research guidance.
- See `VISION.md` for project direction and contribution guardrails.
- Run `make check` before pushing changes to build metadata, native scripts, Java source, tests, or dependency download configuration.
- See `docs/plans/2026-06-08-native-packaging-guard.md` for the current native packaging guardrail.
- See `docs/plans/2026-06-08-build-revision-helper-guard.md` for the current build revision helper guardrail.

## Contributing

Keep changes small and tied to the project that is already present in this repository. For code changes, document the toolchain used, avoid committing generated dependency directories or local configuration, and update this README when setup or verification steps change.
