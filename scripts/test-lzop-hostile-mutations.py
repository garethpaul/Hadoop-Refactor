#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MUTATIONS = (
    (
        "plain output factory pool helper bypass",
        "src/java/com/hadoop/compression/lzo/LzopCodec.java",
        "    return createPooledOutputStream(out, null);",
        "    return createOutputStream(out, getCompressor());",
    ),
    (
        "indexed output factory pool helper bypass",
        "src/java/com/hadoop/compression/lzo/LzopCodec.java",
        "    return createPooledOutputStream(out, indexOut);",
        "    return createIndexedOutputStream(out, indexOut, getCompressor());",
    ),
    (
        "output constructor IOException pool leak",
        "src/java/com/hadoop/compression/lzo/LzopCodec.java",
        "    } catch (IOException e) {\n"
        "      CodecPool.returnCompressor(compressor);\n"
        "      throw e;\n",
        "    } catch (IOException e) {\n      throw e;\n",
    ),
    (
        "output constructor runtime pool leak",
        "src/java/com/hadoop/compression/lzo/LzopCodec.java",
        "    } catch (RuntimeException e) {\n"
        "      CodecPool.returnCompressor(compressor);\n"
        "      throw e;\n",
        "    } catch (RuntimeException e) {\n      throw e;\n",
    ),
    (
        "output constructor Error pool leak",
        "src/java/com/hadoop/compression/lzo/LzopCodec.java",
        "    } catch (Error e) {\n"
        "      CodecPool.returnCompressor(compressor);\n"
        "      throw e;\n",
        "    } catch (Error e) {\n      throw e;\n",
    ),
    (
        "output compression stall guard removal",
        "src/java/com/hadoop/compression/lzo/LzopOutputStream.java",
        "    validateCompressionProgress(bytesReadBefore, bytesWrittenBefore,\n"
        "      needsInputBefore, len, compressor);\n",
        "",
    ),
    (
        "partial block trailer acceptance",
        "src/java/com/hadoop/compression/lzo/LzopInputStream.java",
        "readFully(in, blockSizeBuffer, 0, 4);",
        "return 0;",
    ),
    (
        "signed block length confusion",
        "src/java/com/hadoop/compression/lzo/LzopInputStream.java",
        "return ((long)(0xFF & blockSizeBuffer[0]) << 24)",
        "return ((0xFF & blockSizeBuffer[0]) << 24)",
    ),
    (
        "decompressed length overrun",
        "src/java/com/hadoop/compression/lzo/LzopInputStream.java",
        "if (consumed > expected - decompressed) {",
        "if (false && consumed > expected - decompressed) {",
    ),
    (
        "unknown high header flags",
        "src/java/com/hadoop/compression/lzo/LzopInputStream.java",
        "if ((flags & ~0x00003FFF) != 0) {",
        "if ((flags & 0x000FC000) != 0) {",
    ),
    (
        "file-sized extra header allocation",
        "src/java/com/hadoop/compression/lzo/LzopInputStream.java",
        "new byte[Math.min(8192, Math.max(1, len))]",
        "new byte[Math.max(1, len)]",
    ),
    (
        "close input starvation rejection",
        "src/java/com/hadoop/compression/lzo/LzopInputStream.java",
        "if (decompressor.needsInput()) {",
        "if (false && decompressor.needsInput()) {",
    ),
    (
        "non-idempotent decompressor return",
        "src/java/com/hadoop/compression/lzo/LzopInputStream.java",
        "if (closed) {",
        "if (false && closed) {",
    ),
    (
        "constructor Error pool leak",
        "src/java/com/hadoop/compression/lzo/LzopCodec.java",
        "    } catch (Error e) {\n      CodecPool.returnDecompressor(decompressor);\n      throw e;\n",
        "",
    ),
    (
        "close checksum corruption suppression",
        "src/java/com/hadoop/compression/lzo/LzopInputStream.java",
        "    } catch (IOException e) {\n      closeFailure = e;\n    } finally{",
        "    } catch (IOException e) {\n      LOG.warn(\"ignored checksum failure\", e);\n    } finally{",
    ),
    (
        "read-path output guard removal",
        "src/java/com/hadoop/compression/lzo/LzopInputStream.java",
        "    validateDecompressedLength(n, noUncompressedBytes, uncompressedBlockSize);\n",
        "",
    ),
    (
        "pre-write output cap removal",
        "src/java/com/hadoop/compression/lzo/LzopInputStream.java",
        "limitDecompressionLength(len, noUncompressedBytes,\n      uncompressedBlockSize)",
        "len",
    ),
    (
        "final block checksum omission",
        "src/java/com/hadoop/compression/lzo/LzopInputStream.java",
        "      if (uncompressedBlockSize > 0) {\n        verifyChecksums();\n      }\n",
        "",
    ),
)


def main():
    environment = os.environ.copy()
    for name, relative_path, original, replacement in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="hadoop-lzop-mutation-") as directory:
            mutation_root = Path(directory) / "repo"
            shutil.copytree(
                ROOT,
                mutation_root,
                ignore=shutil.ignore_patterns(".git", "build", "target", "*.class"),
            )
            target = mutation_root / relative_path
            content = target.read_text(encoding="utf-8")
            if content.count(original) != 1:
                print("mutation anchor mismatch for " + name, file=sys.stderr)
                return 1
            target.write_text(content.replace(original, replacement, 1),
                              encoding="utf-8")
            try:
                result = subprocess.run(
                    [sys.executable, "scripts/test-lzop-hostile-streams.py"],
                    cwd=str(mutation_root), env=environment, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    check=False, timeout=15,
                )
            except subprocess.TimeoutExpired:
                print("mutation hung instead of failing: " + name, file=sys.stderr)
                return 1
            if result.returncode == 0:
                print("mutation survived: " + name, file=sys.stderr)
                return 1
    print("Rejected %d hostile Lzop mutations." % len(MUTATIONS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
