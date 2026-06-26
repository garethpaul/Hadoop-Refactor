# Lzop output close cleanup design

status: approved

## Problem

`LzopOutputStream.close()` performs finish, trailer, data-stream close, index-stream close, and compressor return in one success-only sequence. An IOException from any earlier step skips every later cleanup action and leaves the stream retryable after partial finalization.

## Decision

Mark the stream closed before finalization, preserve the first IOException, attempt both output closes independently, and return the compressor from a `finally` block. Keep Java 6 compatibility and do not add suppressed-exception APIs.

## Verification

- Extract and execute the production close helper against two failing tracking streams.
- Require the first failure to remain authoritative while both streams are closed.
- Mutation-test the output-close helper and compressor-finally contract.
