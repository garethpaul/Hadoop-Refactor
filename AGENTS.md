# AGENTS.md

## Repository purpose

`garethpaul/Hadoop-Refactor` is a public sample, documentation, or utility project. Refactor of Hadoop with compression

## Project structure

- `Makefile` - repository verification targets
- `scripts` - baseline checks and helper scripts
- `docs` - plans, notes, and generated README assets
- `src` - primary source code
- `lib` - library source code

## Development commands

- Install dependencies: no repository-specific install command is documented.
- Full baseline: `make check`
- If a command above skips because a platform toolchain is missing, verify on a machine with that SDK before claiming platform behavior is tested.

## Coding conventions

- Language mix noted in the README: Java (29), shell (4), C (2), C/C++ headers (2).

## Testing guidance

- Test-related files detected: `src/test/`, `src/test/com/hadoop/mapreduce/TestLzoTextInputFormat.java`
- Start with the narrowest relevant test or Make target, then run `make check` before handing off if the change is not documentation-only.
- Keep README verification notes in sync when commands, fixtures, or supported toolchains change.

## PR / change guidance

- Keep diffs focused on the requested repository and avoid unrelated modernization or formatting churn.
- Preserve public APIs, sample behavior, file formats, and documented environment variables unless the task explicitly changes them.
- Update tests, README notes, or docs/plans when behavior, security posture, or validation commands change.
- Call out skipped platform validation, legacy toolchain assumptions, and any risky files touched in the final summary.

## Safety and gotchas

- No required secret or credential file was identified in the repository scan. If you add integrations later, keep secrets out of git.
- Keep LZO block-size validation explicit for index generation, split readers, and stream decompression because compressed files may be untrusted input.
- Keep `LzopInputStream.readFully` fail-closed when a positive-length read returns zero bytes so malformed streams cannot spin indefinitely.
- Close-time Lzop decompression rejects zero progress so malformed streams cannot hang cleanup.
- See `SECURITY.md` for vulnerability reporting and safe research guidance.
- See `VISION.md` for project direction and contribution guardrails.
- Run `make lint`, `make test`, `make build`, and `make check` before pushing changes to build metadata, native scripts, Java source, tests, or dependency download configuration.
- See `docs/plans/2026-06-08-native-packaging-guard.md` for the current native packaging guardrail.

## Agent workflow

1. Inspect the README, Makefile, manifests, and the files directly related to the request.
2. Make the smallest source or docs change that satisfies the task; avoid generated, vendored, or local-environment files unless required.
3. Run the narrowest useful validation first, then `make check` or the documented package/platform gate when available.
4. If a required SDK, service credential, or external runtime is unavailable, record the skipped command and why.
5. Summarize changed files, commands run, and remaining risks or follow-up validation.
