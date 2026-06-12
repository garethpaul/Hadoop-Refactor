# Distributed Index Rename Guard

status: completed

## Context

Direct index generation already checks the boolean returned by
`FileSystem.rename`, removes the abandoned temporary file, and throws when the
final `.lzo.index` cannot be published. The distributed
`LzoIndexRecordWriter` had a separate close path that ignored the same return
value, allowing a task to report success even though no final index existed.

## Completed Scope

- Made the checked `LzoIndex` commit helper available to distributed writers.
- Routed `LzoIndexRecordWriter.close` through that shared publication path.
- Compiled the distributed writer in the no-Ant Java smoke gate and added a
  static regression assertion that prevents bypassing the checked helper.
- Documented identical rename-failure semantics for direct and distributed
  index generation.

## Verification

- `make lint`
- `make test`
- `make build`
- `make check`
- `git diff --check`
