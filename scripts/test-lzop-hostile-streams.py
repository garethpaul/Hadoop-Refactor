#!/usr/bin/env python3

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/java/com/hadoop/compression/lzo/LzopInputStream.java"
OUTPUT_SOURCE = ROOT / "src/java/com/hadoop/compression/lzo/LzopOutputStream.java"
CODEC_SOURCE = ROOT / "src/java/com/hadoop/compression/lzo/LzopCodec.java"
HADOOP_JAR = ROOT / "lib/hadoop-core-0.20.2-cdh3u1.jar"


def extract_method(source, signature):
    match = re.search(signature, source, flags=re.MULTILINE)
    if match is None:
        raise AssertionError("missing production method: " + signature)
    start = match.start()
    brace = source.find("{", match.end() - 1)
    if brace < 0:
        raise AssertionError("missing method body")
    depth = 0
    for offset in range(brace, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                return source[start:offset + 1]
    raise AssertionError("unterminated method body")


def main():
    source = SOURCE.read_text(encoding="utf-8")
    output_source = OUTPUT_SOURCE.read_text(encoding="utf-8")
    codec_source = CODEC_SOURCE.read_text(encoding="utf-8")
    if "if (closed)" not in source or "closed = true;" not in source:
        raise AssertionError("LzopInputStream close must be idempotent")
    if "readNextBlockSize(in, tempBuf)" not in source:
        raise AssertionError("block parsing must use strict physical EOF handling")
    if "validateDecompressedLength(n, noUncompressedBytes" not in source:
        raise AssertionError("decompressor output validation must guard the read path")
    if "limitDecompressionLength(len, noUncompressedBytes" not in source:
        raise AssertionError("decompressor writes must be capped before output")
    checksum_boundary = source.find("if (uncompressedBlockSize > 0) {")
    next_size_boundary = source.find("readNextBlockSize(in, tempBuf)")
    if checksum_boundary < 0 or checksum_boundary > next_size_boundary \
            or "verifyChecksums();" not in source[checksum_boundary:next_size_boundary] \
            or "checkStream();\n    verifyChecksums();" in source:
        raise AssertionError("completed blocks must be verified before the next size")
    if "validateHeaderFlags(hitem);" not in source:
        raise AssertionError("header flag validation must guard the header path")
    if "readHeaderBytes(in, extraFieldLength" not in source \
            or "new byte[extraFieldLength]" in source \
            or "Math.min(8192, Math.max(1, len))" not in source:
        raise AssertionError("extra headers must use bounded streaming")
    if "verifyChecksums();\n      }\n    } catch (IOException e) {\n      closeFailure = e;" not in source \
            or "Incorrect LZO file format" in source:
        raise AssertionError("close-time checksum corruption must be propagated")
    if "CodecPool.returnDecompressor(decompressor);" not in codec_source \
            or "catch (IOException e)" not in codec_source \
            or "catch (RuntimeException e)" not in codec_source \
            or "catch (Error e)" not in codec_source:
        raise AssertionError("borrowed decompressors must be returned on construction failure")
    methods = [
        extract_method(source, r"^\s*private static void readFully\("),
        extract_method(source, r"^\s*static long readNextBlockSize\("),
        extract_method(source, r"^\s*static void validateDecompressedLength\("),
        extract_method(source, r"^\s*static int limitDecompressionLength\("),
        extract_method(source, r"^\s*static void validateHeaderFlags\("),
        extract_method(source, r"^\s*static void readHeaderBytes\("),
        extract_method(source, r"^\s*static void drainDecompressor\("),
        extract_method(output_source, r"^\s*static IOException closeOutput\("),
    ]

    with tempfile.TemporaryDirectory(prefix="hadoop-lzop-hostile-") as workdir:
        workdir = Path(workdir)
        source_file = workdir / "LzopHostileStreamHarness.java"
        class_dir = workdir / "classes"
        class_dir.mkdir()
        source_file.write_text(
            """
import java.io.ByteArrayInputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.zip.Adler32;
import java.util.zip.CRC32;
import org.apache.hadoop.io.compress.Decompressor;

public class LzopHostileStreamHarness {
""".lstrip()
            + "\n\n".join(methods)
            + r'''

  public static void main(String[] args) throws Exception {
    rejectsPartialBlockTrailer();
    rejectsMissingBlockTerminator();
    preservesUnsignedBlockLengthsForValidation();
    rejectsDeclaredBlockOverrun();
    capsOutputBeforeDecompression();
    rejectsNegativeDecompressorOutput();
    rejectsUnknownHighHeaderFlags();
    streamsHeaderBytesWithoutLargeAllocation();
    stopsCloseDrainWhenMoreInputIsRequired();
    rejectsTrueCloseDrainStalls();
    closesAllOutputsAndPreservesFirstFailure();
  }

  private static void rejectsPartialBlockTrailer() throws Exception {
    try {
      readNextBlockSize(new ByteArrayInputStream(new byte[] { 0, 0, 0 }),
        new byte[4]);
      throw new AssertionError("partial block trailer was accepted");
    } catch (EOFException expected) {
    }
  }

  private static void rejectsMissingBlockTerminator() throws Exception {
    try {
      readNextBlockSize(new ByteArrayInputStream(new byte[0]), new byte[4]);
      throw new AssertionError("missing block terminator was accepted");
    } catch (EOFException expected) {
    }
  }

  private static void preservesUnsignedBlockLengthsForValidation()
      throws Exception {
    long result = readNextBlockSize(new ByteArrayInputStream(new byte[] {
      (byte)0xff, (byte)0xff, (byte)0xff, (byte)0xff }), new byte[4]);
    if (result != 4294967295L) {
      throw new AssertionError("high-bit block length became EOF: " + result);
    }
  }

  private static void rejectsDeclaredBlockOverrun() throws Exception {
    try {
      validateDecompressedLength(5, 4, 8);
      throw new AssertionError("declared block overrun was accepted");
    } catch (IOException expected) {
    }
  }

  private static void rejectsNegativeDecompressorOutput() throws Exception {
    try {
      validateDecompressedLength(-1, 0, 8);
      throw new AssertionError("negative decompressor output was accepted");
    } catch (IOException expected) {
    }
  }

  private static void capsOutputBeforeDecompression() throws Exception {
    int limited = limitDecompressionLength(4096, 7, 9);
    if (limited != 2) {
      throw new AssertionError("decompressor output was not capped: " + limited);
    }
  }

  private static void rejectsUnknownHighHeaderFlags() throws Exception {
    validateHeaderFlags(0x00003fff);
    try {
      validateHeaderFlags(0x80000000);
      throw new AssertionError("unknown high header flag was accepted");
    } catch (IOException expected) {
    }
  }

  private static void streamsHeaderBytesWithoutLargeAllocation() throws Exception {
    byte[] bytes = new byte[16385];
    for (int i = 0; i < bytes.length; i++) {
      bytes[i] = (byte)(i * 31);
    }
    Adler32 expectedAdler = new Adler32();
    expectedAdler.update(bytes, 0, bytes.length);
    CRC32 expectedCrc = new CRC32();
    expectedCrc.update(bytes, 0, bytes.length);
    Adler32 actualAdler = new Adler32();
    CRC32 actualCrc = new CRC32();
    readHeaderBytes(new ByteArrayInputStream(bytes), bytes.length,
      actualAdler, actualCrc);
    if (actualAdler.getValue() != expectedAdler.getValue()
        || actualCrc.getValue() != expectedCrc.getValue()) {
      throw new AssertionError("streamed header checksums differ");
    }
  }

  private static void stopsCloseDrainWhenMoreInputIsRequired() throws Exception {
    drainDecompressor(new SequenceDecompressor(new int[] { 0 }, true));
  }

  private static void rejectsTrueCloseDrainStalls() throws Exception {
    try {
      drainDecompressor(new SequenceDecompressor(new int[] { 0 }, false));
      throw new AssertionError("true close drain stall was accepted");
    } catch (IOException expected) {
    }
  }

  private static final class SequenceDecompressor implements Decompressor {
    private final int[] outputs;
    private final boolean needsInput;
    private int offset;

    SequenceDecompressor(int[] outputs, boolean needsInput) {
      this.outputs = outputs;
      this.needsInput = needsInput;
    }

    public void setInput(byte[] b, int off, int len) { }
    public boolean needsInput() { return needsInput; }
    public void setDictionary(byte[] b, int off, int len) { }
    public boolean needsDictionary() { return false; }
    public boolean finished() { return offset >= outputs.length; }
    public int decompress(byte[] b, int off, int len) {
      return outputs[Math.min(offset++, outputs.length - 1)];
    }
    public void reset() { offset = 0; }
    public void end() { }
  }

  private static void closesAllOutputsAndPreservesFirstFailure() throws Exception {
    TrackingOutput first = new TrackingOutput("first");
    TrackingOutput second = new TrackingOutput("second");
    IOException failure = closeOutput(first, null);
    failure = closeOutput(second, failure);
    if (!first.closed || !second.closed) {
      throw new AssertionError("all outputs were not closed");
    }
    if (failure == null || !"first".equals(failure.getMessage())) {
      throw new AssertionError("first close failure was not preserved");
    }
  }

  private static final class TrackingOutput extends OutputStream {
    private final String message;
    private boolean closed;
    TrackingOutput(String message) { this.message = message; }
    public void write(int value) { }
    public void close() throws IOException {
      closed = true;
      throw new IOException(message);
    }
  }
}
''',
            encoding="utf-8",
        )
        compile_result = subprocess.run(
            [
                "javac", "-source", "1.6", "-target", "1.6",
                "-cp", str(HADOOP_JAR), "-d", str(class_dir), str(source_file),
            ],
            cwd=str(ROOT), text=True, capture_output=True, check=False,
        )
        if compile_result.returncode != 0:
            print(compile_result.stderr, file=sys.stderr)
            return compile_result.returncode
        try:
            run_result = subprocess.run(
                ["java", "-cp", str(class_dir) + os.pathsep + str(HADOOP_JAR),
                 "LzopHostileStreamHarness"],
                cwd=str(ROOT), text=True, capture_output=True, check=False,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            print("hostile Lzop stream harness hung", file=sys.stderr)
            return 1
        if run_result.returncode != 0:
            print(run_result.stderr or run_result.stdout, file=sys.stderr)
            return run_result.returncode

    print("Lzop hostile stream tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
