# Lzop output compression progress design

## Problem

`LzopOutputStream` repeatedly calls a `Compressor` while it still has input or
is finishing. A hostile or defective compressor can return zero bytes without
changing any public state, leaving both loops able to run forever.

## Options considered

1. Retry a fixed number of times. This is simple but arbitrary and can delay a
   deterministic failure.
2. Reject every zero-byte compression result. This can reject legitimate calls
   that consume input or transition compressor state without emitting output.
3. Compare observable compressor state before and after each call, accepting
   output, byte-count changes, input-demand changes, or completion and rejecting
   only a fully unchanged result.

## Decision

Use option 3. Keep the check Java 6-compatible and package-visible so the
portable hostile-stream harness can exercise it without loading native LZO.
Call the check immediately after every `compressor.compress(...)` invocation,
before writing a block or allowing either caller loop to continue.

## Verification

- Add executable cases for consumed input, input-demand transitions,
  completion, and a true unchanged-state stall.
- Add a mutation that removes the production call site.
- Run the portable baseline, mutation suite, Java compilation, and hosted CI.
