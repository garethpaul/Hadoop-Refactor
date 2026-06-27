#!/usr/bin/env python3
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/plans/2026-06-08-legacy-build-baseline.md"
EMPTY_INDEX_PLAN = ROOT / "docs/plans/2026-06-09-lzo-index-empty-boundary.md"
INDEX_BYTE_PLAN = ROOT / "docs/plans/2026-06-09-lzo-index-byte-count-guard.md"
INDEX_OPEN_PLAN = ROOT / "docs/plans/2026-06-09-lzo-index-open-failure-guard.md"
BLOCK_SIZE_PLAN = ROOT / "docs/plans/2026-06-09-lzo-block-size-boundary.md"
MAKE_GATES_PLAN = ROOT / "docs/plans/2026-06-09-make-gate-aliases.md"
INDEX_RENAME_PLAN = ROOT / "docs/plans/2026-06-09-lzo-index-rename-failure-guard.md"
INDEX_POSITION_PLAN = ROOT / "docs/plans/2026-06-09-lzo-index-position-order-guard.md"
CI_PLAN = ROOT / "docs/plans/2026-06-10-ci-baseline.md"
RECORD_WRITER_RENAME_PLAN = ROOT / "docs/plans/2026-06-10-distributed-index-rename-guard.md"
INPUT_TRAVERSAL_PLAN = ROOT / "docs/plans/2026-06-12-distributed-input-error-propagation.md"
COMPRESSED_LENGTH_PLAN = ROOT / "docs/plans/2026-06-13-lzo-compressed-length-consistency.md"
EXTRA_HEADER_LENGTH_PLAN = ROOT / "docs/plans/2026-06-13-lzop-extra-header-length-boundary.md"
ZERO_PROGRESS_READ_PLAN = ROOT / "docs/plans/2026-06-13-lzop-zero-progress-read.md"
LOCATION_INDEPENDENT_MAKE_PLAN = ROOT / "docs/plans/2026-06-13-location-independent-make.md"
CLOSE_PROGRESS_PLAN = ROOT / "docs/plans/2026-06-15-lzop-close-progress.md"
READ_DECOMPRESS_PROGRESS_PLAN = ROOT / "docs/plans/2026-06-17-lzop-read-decompress-progress.md"
OUTPUT_COMPRESSION_PROGRESS_PLAN = ROOT / "docs/plans/2026-06-26-lzop-output-progress.md"
OUTPUT_CONSTRUCTION_POOL_PLAN = ROOT / "docs/plans/2026-06-26-lzop-output-construction-pool.md"
CI_WORKFLOW = ROOT / ".github/workflows/check.yml"


def require(condition, message, failures):
    if not condition:
        failures.append(message)


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8", errors="replace")


def extract_java_block(source, signature_pattern):
    signature = re.search(signature_pattern, source, re.MULTILINE)
    if signature is None:
        return None

    brace_start = source.find("{", signature.start())
    depth = 0
    for index in range(brace_start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[signature.start():index + 1]
    return None


def run(command):
    return subprocess.run(command, cwd=str(ROOT), text=True, capture_output=True, check=False)


def verify_native_packaging_script(failures):
    with tempfile.TemporaryDirectory(prefix="hadoop-refactor-native-") as workdir:
        workdir = Path(workdir)
        base_native = workdir / "base native"
        build_native = workdir / "build native"
        dist_native = workdir / "dist native"

        prebuilt_platform = base_native / "linux x86"
        built_platform = build_native / "mac arm" / "lib"
        prebuilt_platform.mkdir(parents=True)
        built_platform.mkdir(parents=True)
        dist_native.mkdir(parents=True)

        (prebuilt_platform / "libgplcompression-prebuilt.so").write_text("prebuilt", encoding="utf-8")
        (built_platform / "libgplcompression-built.so").write_text("built", encoding="utf-8")

        env = os.environ.copy()
        env.update({
            "BASE_NATIVE_LIB_DIR": str(base_native),
            "BUILD_NATIVE_DIR": str(build_native),
            "DIST_LIB_DIR": str(dist_native),
        })

        result = subprocess.run(
            ["sh", str(ROOT / "src/native/packageNativeHadoop.sh")],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        require(
            result.returncode == 0,
            "packageNativeHadoop.sh must copy native libraries from quoted paths: "
            + result.stderr.strip(),
            failures,
        )
        prebuilt_output = dist_native / "linux x86" / "libgplcompression-prebuilt.so"
        built_output = dist_native / "mac arm" / "libgplcompression-built.so"
        require(
            prebuilt_output.is_file()
            and prebuilt_output.read_text(encoding="utf-8") == "prebuilt",
            "packageNativeHadoop.sh must preserve prebuilt native libraries",
            failures,
        )
        require(
            built_output.is_file()
            and built_output.read_text(encoding="utf-8") == "built",
            "packageNativeHadoop.sh must preserve custom-built native libraries",
            failures,
        )


def verify_build_revision_script(failures):
    with tempfile.TemporaryDirectory(prefix="hadoop-refactor revision-") as workdir:
        fixture_root = Path(workdir) / "archive root with spaces"
        fixture_src = fixture_root / "src"
        fixture_src.mkdir(parents=True)
        fixture_script = fixture_src / "get_build_revision.sh"
        shutil.copy2(ROOT / "src/get_build_revision.sh", fixture_script)

        def run_fixture(extra_env=None):
            env = os.environ.copy()
            env.pop("BUILD_REVISION", None)
            if extra_env:
                env.update(extra_env)
            return subprocess.run(
                ["bash", str(fixture_script)],
                cwd=str(fixture_root),
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

        result = run_fixture({"BUILD_REVISION": "manual revision with spaces"})
        require(result.returncode == 0 and result.stdout == "manual revision with spaces\n",
                "get_build_revision.sh must preserve quoted BUILD_REVISION overrides",
                failures)

        archive_version = fixture_root / ".archive-version"
        archive_version.write_text("archive revision with spaces\n", encoding="utf-8")
        result = run_fixture()
        require(result.returncode == 0 and result.stdout == "archive revision with spaces\n",
                "get_build_revision.sh must read archive revisions from script-relative paths with spaces",
                failures)

        archive_version.write_text("$Format:%H$\n", encoding="utf-8")
        result = run_fixture()
        require(result.returncode == 0 and result.stdout == "Unknown build revision\n",
                "get_build_revision.sh must ignore unexpanded archive-version placeholders",
                failures)


def verify_lzo_index_empty_alignment(failures):
    if shutil.which("javac") is None or shutil.which("java") is None:
        failures.append("javac and java must be available for the LzoIndex smoke check")
        return

    with tempfile.TemporaryDirectory(prefix="hadoop-refactor-lzo-index-") as workdir:
        workdir = Path(workdir)
        class_dir = workdir / "classes"
        class_dir.mkdir()
        harness = workdir / "LzoIndexEmptyHarness.java"
        stub_dir = workdir / "com/hadoop/compression/lzo"
        stub_dir.mkdir(parents=True)
        logging_stub_dir = workdir / "org/apache/commons/logging"
        logging_stub_dir.mkdir(parents=True)
        codec_stub = stub_dir / "LzoCodec.java"
        decompressor_stub = stub_dir / "LzopDecompressor.java"
        log_stub = logging_stub_dir / "Log.java"
        log_factory_stub = logging_stub_dir / "LogFactory.java"
        codec_stub.write_text(
            """
package com.hadoop.compression.lzo;

public class LzoCodec {
  public static final int MAX_BLOCK_SIZE = 64 * 1024 * 1024;
}
""".lstrip(),
            encoding="utf-8",
        )
        decompressor_stub.write_text(
            """
package com.hadoop.compression.lzo;

import java.io.IOException;
import org.apache.hadoop.io.compress.Decompressor;

public class LzopDecompressor implements Decompressor {
  public int getCompressedChecksumsCount() {
    return 0;
  }

  public int getDecompressedChecksumsCount() {
    return 0;
  }

  public void setInput(byte[] b, int off, int len) { }
  public boolean needsInput() { return true; }
  public void setDictionary(byte[] b, int off, int len) { }
  public boolean needsDictionary() { return false; }
  public boolean finished() { return true; }
  public int decompress(byte[] b, int off, int len) throws IOException { return 0; }
  public void reset() { }
  public void end() { }
}
""".lstrip(),
            encoding="utf-8",
        )
        log_stub.write_text(
            """
package org.apache.commons.logging;

public interface Log {
  void debug(Object message);
  void debug(Object message, Throwable throwable);
  void info(Object message);
  void info(Object message, Throwable throwable);
  void warn(Object message);
  void warn(Object message, Throwable throwable);
  void error(Object message);
  void error(Object message, Throwable throwable);
  void fatal(Object message);
  void fatal(Object message, Throwable throwable);
  void trace(Object message);
  void trace(Object message, Throwable throwable);
  boolean isDebugEnabled();
  boolean isInfoEnabled();
  boolean isWarnEnabled();
  boolean isErrorEnabled();
  boolean isFatalEnabled();
  boolean isTraceEnabled();
}
""".lstrip(),
            encoding="utf-8",
        )
        log_factory_stub.write_text(
            """
package org.apache.commons.logging;

public class LogFactory {
  private static final Log LOG = new NoopLog();

  public static Log getLog(Class<?> clazz) {
    return LOG;
  }

  private static class NoopLog implements Log {
    public void debug(Object message) { }
    public void debug(Object message, Throwable throwable) { }
    public void info(Object message) { }
    public void info(Object message, Throwable throwable) { }
    public void warn(Object message) { }
    public void warn(Object message, Throwable throwable) { }
    public void error(Object message) { }
    public void error(Object message, Throwable throwable) { }
    public void fatal(Object message) { }
    public void fatal(Object message, Throwable throwable) { }
    public void trace(Object message) { }
    public void trace(Object message, Throwable throwable) { }
    public boolean isDebugEnabled() { return false; }
    public boolean isInfoEnabled() { return false; }
    public boolean isWarnEnabled() { return false; }
    public boolean isErrorEnabled() { return false; }
    public boolean isFatalEnabled() { return false; }
    public boolean isTraceEnabled() { return false; }
  }
}
""".lstrip(),
            encoding="utf-8",
        )
        harness.write_text(
            """
package com.hadoop.compression.lzo;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.net.URI;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.FSDataInputStream;
import org.apache.hadoop.fs.FSDataOutputStream;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.fs.permission.FsPermission;
import org.apache.hadoop.util.Progressable;

public class LzoIndexEmptyHarness {
  public static void main(String[] args) throws Exception {
    LzoIndex empty = new LzoIndex();
    assertEquals(0, empty.getNumberOfBlocks(), "getNumberOfBlocks");
    assertEquals(LzoIndex.NOT_FOUND, empty.findNextPosition(0), "findNextPosition");
    assertEquals(LzoIndex.NOT_FOUND, empty.alignSliceStartToIndex(1, 20), "alignSliceStartToIndex");
    assertEquals(20, empty.alignSliceEndToIndex(5, 20), "alignSliceEndToIndex");
    assertEquals(2, LzoIndex.getBlockCount(16), "getBlockCount");
    assertCorruptIndexByteCountRejected();
    assertInvalidIndexPositionsRejected();
    assertOversizedIndexBlockSizesRejected();
    assertCompressedLengthConsistency();
    assertMissingIndexReturnsEmpty();
    assertOpenFailurePropagates();
    assertRenameFailurePropagates();
  }

  private static void assertEquals(long expected, long actual, String label) {
    if (expected != actual) {
      throw new AssertionError(label + " expected " + expected + " but got " + actual);
    }
  }

  private static void assertCorruptIndexByteCountRejected() throws Exception {
    try {
      LzoIndex.getBlockCount(7);
      throw new AssertionError("Corrupt index byte count was accepted");
    } catch (java.io.IOException expected) {
      if (expected.getMessage().indexOf("multiple of 8") < 0) {
        throw new AssertionError("Unexpected corrupt index message: " + expected.getMessage());
      }
    }
  }

  private static void assertInvalidIndexPositionsRejected() throws Exception {
    LzoIndex.validateBlockPosition(0, -1);
    LzoIndex.validateBlockPosition(10, 0);
    assertIndexPositionRejected(-1, -1, "negative block position");
    assertIndexPositionRejected(4, 4, "strictly increasing");
    assertIndexPositionRejected(3, 4, "strictly increasing");
  }

  private static void assertIndexPositionRejected(long position,
      long previousPosition, String expectedMessage) throws Exception {
    try {
      LzoIndex.validateBlockPosition(position, previousPosition);
      throw new AssertionError("Malformed LZO index position was accepted");
    } catch (java.io.IOException expected) {
      if (expected.getMessage().indexOf(expectedMessage) < 0) {
        throw new AssertionError("Unexpected index position message: " +
          expected.getMessage());
      }
    }
  }

  private static void assertOversizedIndexBlockSizesRejected() throws Exception {
    assertBlockSizeRejected(LzoCodec.MAX_BLOCK_SIZE + 1, 1, "Uncompressed block size");
    assertBlockSizeRejected(1, 0, "Could not read compressed block size");
    assertBlockSizeRejected(1, LzoCodec.MAX_BLOCK_SIZE + 1, "Compressed block size");
  }

  private static void assertCompressedLengthConsistency() throws Exception {
    LzoIndex.validateBlockSizes(8, 8);
    LzoIndex.validateBlockSizes(8, 4);
    assertBlockSizeRejected(8, 9, "exceeds uncompressed block size");
  }

  private static void assertBlockSizeRejected(int uncompressedBlockSize,
      int compressedBlockSize, String expectedMessage) throws Exception {
    try {
      LzoIndex.validateBlockSizes(uncompressedBlockSize, compressedBlockSize);
      throw new AssertionError("Malformed LZO block sizes were accepted");
    } catch (java.io.IOException expected) {
      if (expected.getMessage().indexOf(expectedMessage) < 0) {
        throw new AssertionError("Unexpected block-size message: " + expected.getMessage());
      }
    }
  }

  private static void assertMissingIndexReturnsEmpty() throws Exception {
    LzoIndex missing = LzoIndex.readIndex(
        new ThrowingFileSystem(new FileNotFoundException("missing index")),
        new Path("/data/example.lzo"));
    if (!missing.isEmpty()) {
      throw new AssertionError("Missing index should return an empty LzoIndex");
    }
  }

  private static void assertOpenFailurePropagates() throws Exception {
    try {
      LzoIndex.readIndex(
          new ThrowingFileSystem(new IOException("permission denied")),
          new Path("/data/example.lzo"));
      throw new AssertionError("Non-missing index open failure was swallowed");
    } catch (IOException expected) {
      if (expected.getMessage().indexOf("permission denied") < 0) {
        throw new AssertionError("Unexpected open failure: " + expected.getMessage());
      }
    }
  }

  private static void assertRenameFailurePropagates() throws Exception {
    RenameFailureFileSystem fs = new RenameFailureFileSystem();
    Path tmpIndex = new Path("/data/example.lzo.index.tmp");
    try {
      LzoIndex.commitIndexFile(fs, tmpIndex, new Path("/data/example.lzo.index"));
      throw new AssertionError("Temporary index rename failure was swallowed");
    } catch (IOException expected) {
      if (expected.getMessage().indexOf("Failed to move temporary LZO index") < 0) {
        throw new AssertionError("Unexpected rename failure: " + expected.getMessage());
      }
    }
    if (!fs.deletedTempIndex) {
      throw new AssertionError("Temporary index file was not deleted after rename failure");
    }
  }

  private static class RenameFailureFileSystem extends ThrowingFileSystem {
    boolean deletedTempIndex = false;

    RenameFailureFileSystem() {
      super(new FileNotFoundException("not used"));
    }

    public boolean rename(Path src, Path dst) throws IOException {
      return false;
    }

    public boolean delete(Path f, boolean recursive) throws IOException {
      deletedTempIndex = f.toString().endsWith(".index.tmp");
      return true;
    }
  }

  private static class ThrowingFileSystem extends FileSystem {
    private final IOException openException;

    ThrowingFileSystem(IOException openException) {
      this.openException = openException;
      setConf(new Configuration());
    }

    public URI getUri() {
      return URI.create("throwing:///");
    }

    public FSDataInputStream open(Path f, int bufferSize) throws IOException {
      throw openException;
    }

    public FSDataOutputStream create(Path f, FsPermission permission, boolean overwrite,
        int bufferSize, short replication, long blockSize, Progressable progress)
        throws IOException {
      throw new UnsupportedOperationException();
    }

    public FSDataOutputStream append(Path f, int bufferSize, Progressable progress)
        throws IOException {
      throw new UnsupportedOperationException();
    }

    public boolean rename(Path src, Path dst) throws IOException {
      return false;
    }

    public boolean delete(Path f) throws IOException {
      return false;
    }

    public boolean delete(Path f, boolean recursive) throws IOException {
      return false;
    }

    public FileStatus[] listStatus(Path f) throws IOException {
      return new FileStatus[0];
    }

    public void setWorkingDirectory(Path newDir) { }

    public Path getWorkingDirectory() {
      return new Path("/");
    }

    public boolean mkdirs(Path f, FsPermission permission) throws IOException {
      return false;
    }

    public FileStatus getFileStatus(Path f) throws IOException {
      throw new FileNotFoundException(f.toString());
    }
  }
}
""".lstrip(),
            encoding="utf-8",
        )
        hadoop_jar = ROOT / "lib/hadoop-core-0.20.2-cdh3u1.jar"
        lzo_index = ROOT / "src/java/com/hadoop/compression/lzo/LzoIndex.java"
        lzo_index_record_writer = ROOT / "src/java/com/hadoop/mapreduce/LzoIndexRecordWriter.java"
        classpath = str(hadoop_jar)

        compile_result = subprocess.run(
            [
                "javac",
                "-cp",
                classpath,
                "-d",
                str(class_dir),
                str(log_stub),
                str(log_factory_stub),
                str(codec_stub),
                str(decompressor_stub),
                str(lzo_index),
                str(lzo_index_record_writer),
                str(harness),
            ],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        require(
            compile_result.returncode == 0,
            "LzoIndex smoke check must compile: " + compile_result.stderr.strip(),
            failures,
        )
        if compile_result.returncode != 0:
            return

        run_result = subprocess.run(
            ["java", "-cp", f"{class_dir}:{hadoop_jar}", "com.hadoop.compression.lzo.LzoIndexEmptyHarness"],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        require(
            run_result.returncode == 0,
            "LzoIndex smoke harness must return safe boundaries and propagate open failures: "
            + (run_result.stderr or run_result.stdout).strip(),
            failures,
        )


def verify_lzop_extra_header_length(failures):
    if shutil.which("javac") is None or shutil.which("java") is None:
        failures.append("javac and java must be available for the lzop header smoke check")
        return

    with tempfile.TemporaryDirectory(prefix="hadoop-refactor-lzop-header-") as workdir:
        workdir = Path(workdir)
        class_dir = workdir / "classes"
        class_dir.mkdir()
        package_dir = workdir / "com/hadoop/compression/lzo"
        package_dir.mkdir(parents=True)
        codec_stub = package_dir / "LzoCodec.java"
        harness = package_dir / "LzopHeaderValidationHarness.java"
        codec_stub.write_text(
            """
package com.hadoop.compression.lzo;

public class LzoCodec {
  public static final int MAX_BLOCK_SIZE = 64 * 1024 * 1024;
}
""".lstrip(),
            encoding="utf-8",
        )
        harness.write_text(
            """
package com.hadoop.compression.lzo;

import java.io.IOException;

public class LzopHeaderValidationHarness {
  public static void main(String[] args) throws Exception {
    assertEquals(0, LzopHeaderValidation.validateExtraFieldLength(0));
    assertEquals(LzoCodec.MAX_BLOCK_SIZE,
      LzopHeaderValidation.validateExtraFieldLength(LzoCodec.MAX_BLOCK_SIZE));
    assertRejected(-1, "must not be negative");
    assertRejected(LzoCodec.MAX_BLOCK_SIZE + 1, "exceeds max block size");
  }

  private static void assertEquals(int expected, int actual) {
    if (expected != actual) {
      throw new AssertionError("Expected " + expected + " but got " + actual);
    }
  }

  private static void assertRejected(int length, String expectedMessage)
      throws Exception {
    try {
      LzopHeaderValidation.validateExtraFieldLength(length);
      throw new AssertionError("Malformed extra header length was accepted: " + length);
    } catch (IOException expected) {
      if (expected.getMessage().indexOf(expectedMessage) < 0) {
        throw new AssertionError("Unexpected extra header message: " +
          expected.getMessage());
      }
    }
  }
}
""".lstrip(),
            encoding="utf-8",
        )
        validator = ROOT / "src/java/com/hadoop/compression/lzo/LzopHeaderValidation.java"
        compile_result = subprocess.run(
            [
                "javac",
                "-source",
                "1.6",
                "-target",
                "1.6",
                "-d",
                str(class_dir),
                str(codec_stub),
                str(validator),
                str(harness),
            ],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        require(
            compile_result.returncode == 0,
            "Lzop header smoke check must compile: " + compile_result.stderr.strip(),
            failures,
        )
        if compile_result.returncode != 0:
            return

        run_result = subprocess.run(
            [
                "java",
                "-cp",
                str(class_dir),
                "com.hadoop.compression.lzo.LzopHeaderValidationHarness",
            ],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        require(
            run_result.returncode == 0,
            "Lzop header smoke harness must enforce bounded lengths: " +
            (run_result.stderr or run_result.stdout).strip(),
            failures,
        )


def verify_lzop_read_progress(failures):
    if shutil.which("javac") is None or shutil.which("java") is None:
        failures.append("javac and java must be available for the lzop read-progress smoke check")
        return

    source = read("src/java/com/hadoop/compression/lzo/LzopInputStream.java")
    read_fully = extract_java_block(
        source,
        r"^\s*private static void readFully\( InputStream in, byte buf\[\],\s*\n\s*int off, int len \) throws IOException, EOFException \{",
    )
    if read_fully is None:
        failures.append("Lzop read-progress smoke check must extract readFully")
        return

    with tempfile.TemporaryDirectory(prefix="hadoop-refactor-lzop-read-") as workdir:
        workdir = Path(workdir)
        class_dir = workdir / "classes"
        class_dir.mkdir()
        harness = workdir / "LzopReadFullyHarness.java"
        harness.write_text(
            """
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.util.Arrays;

public class LzopReadFullyHarness {
""".lstrip() + read_fully + """

  public static void main(String[] args) throws Exception {
    assertChunkedReadCompletes();
    assertPrematureEofRejected();
    assertZeroProgressRejected();
  }

  private static void assertChunkedReadCompletes() throws Exception {
    byte[] expected = new byte[] { 1, 2, 3, 4 };
    byte[] actual = new byte[expected.length];
    readFully(new OneByteInputStream(expected), actual, 0, actual.length);
    if (!Arrays.equals(expected, actual)) {
      throw new AssertionError("Chunked read did not fill the requested buffer");
    }
  }

  private static void assertPrematureEofRejected() throws Exception {
    try {
      readFully(new OneByteInputStream(new byte[] { 1 }), new byte[2], 0, 2);
      throw new AssertionError("Premature EOF was accepted");
    } catch (EOFException expected) {
      // Expected.
    }
  }

  private static void assertZeroProgressRejected() throws Exception {
    try {
      readFully(new ZeroProgressInputStream(), new byte[1], 0, 1);
      throw new AssertionError("Zero-progress read was accepted");
    } catch (IOException expected) {
      if (expected.getMessage().indexOf("made no progress") < 0) {
        throw new AssertionError("Unexpected zero-progress message: " +
          expected.getMessage());
      }
    }
  }

  private static final class OneByteInputStream extends InputStream {
    private final byte[] data;
    private int offset;

    OneByteInputStream(byte[] data) {
      this.data = data;
    }

    public int read() {
      return offset < data.length ? data[offset++] & 0xff : -1;
    }

    public int read(byte[] buffer, int bufferOffset, int length) {
      if (offset >= data.length) {
        return -1;
      }
      buffer[bufferOffset] = data[offset++];
      return 1;
    }
  }

  private static final class ZeroProgressInputStream extends InputStream {
    public int read() {
      return 0;
    }

    public int read(byte[] buffer, int offset, int length) {
      return 0;
    }
  }
}
""",
            encoding="utf-8",
        )
        compile_result = subprocess.run(
            [
                "javac",
                "-source",
                "1.6",
                "-target",
                "1.6",
                "-d",
                str(class_dir),
                str(harness),
            ],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        require(
            compile_result.returncode == 0,
            "Lzop read-progress smoke check must compile: " + compile_result.stderr.strip(),
            failures,
        )
        if compile_result.returncode != 0:
            return

        try:
            run_result = subprocess.run(
                ["java", "-cp", str(class_dir), "LzopReadFullyHarness"],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            failures.append("Lzop read-progress smoke harness must not hang on zero-progress input")
            return
        require(
            run_result.returncode == 0,
            "Lzop read-progress smoke harness must preserve reads and reject stalls: " +
            (run_result.stderr or run_result.stdout).strip(),
            failures,
        )


def verify_lzop_close_progress(failures):
    if shutil.which("javac") is None or shutil.which("java") is None:
        failures.append("javac and java must be available for the lzop close-progress smoke check")
        return

    source = read("src/java/com/hadoop/compression/lzo/LzopInputStream.java")
    drain_decompressor = extract_java_block(
        source,
        r"^\s*static void drainDecompressor\(Decompressor decompressor\) throws IOException \{",
    )
    if drain_decompressor is None:
        failures.append("Lzop close-progress smoke check must extract drainDecompressor")
        return

    with tempfile.TemporaryDirectory(prefix="hadoop-refactor-lzop-close-") as workdir:
        workdir = Path(workdir)
        class_dir = workdir / "classes"
        class_dir.mkdir()
        harness = workdir / "LzopCloseProgressHarness.java"
        hadoop_jar = ROOT / "lib/hadoop-core-0.20.2-cdh3u1.jar"
        harness.write_text(
            """
import java.io.IOException;
import org.apache.hadoop.io.compress.Decompressor;

public class LzopCloseProgressHarness {
""".lstrip() + drain_decompressor + """

  public static void main(String[] args) throws Exception {
    assertMultiStepDrainCompletes();
    assertInputRequestStopsDrain();
    assertZeroProgressCloseRejected();
  }

  private static void assertMultiStepDrainCompletes() throws Exception {
    drainDecompressor(new SequenceDecompressor(new int[] { 2, 1 }, false));
  }

  private static void assertInputRequestStopsDrain() throws Exception {
    drainDecompressor(new SequenceDecompressor(new int[] { 0 }, true));
  }

  private static void assertZeroProgressCloseRejected() throws Exception {
    try {
      drainDecompressor(new SequenceDecompressor(new int[] { 0 }, false));
      throw new AssertionError("Zero-progress close drain was accepted");
    } catch (IOException expected) {
      if (expected.getMessage().indexOf("made no progress") < 0) {
        throw new AssertionError("Unexpected close-progress message: " +
          expected.getMessage());
      }
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
      return outputs[offset++];
    }
    public void reset() { offset = 0; }
    public void end() { }
  }
}
""",
            encoding="utf-8",
        )
        compile_result = subprocess.run(
            [
                "javac",
                "-source",
                "1.6",
                "-target",
                "1.6",
                "-cp",
                str(hadoop_jar),
                "-d",
                str(class_dir),
                str(harness),
            ],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        require(
            compile_result.returncode == 0,
            "Lzop close-progress smoke check must compile: " + compile_result.stderr.strip(),
            failures,
        )
        if compile_result.returncode != 0:
            return

        try:
            run_result = subprocess.run(
                ["java", "-cp", str(class_dir) + os.pathsep + str(hadoop_jar),
                 "LzopCloseProgressHarness"],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            failures.append("Lzop close-progress smoke harness must not hang on zero-progress decompression")
            return
        require(
            run_result.returncode == 0,
            "Lzop close-progress smoke harness must preserve draining and reject stalls: " +
            (run_result.stderr or run_result.stdout).strip(),
            failures,
        )


def verify_lzop_read_decompress_progress(failures):
    if shutil.which("javac") is None or shutil.which("java") is None:
        failures.append("javac and java must be available for the lzop read-decompress progress smoke check")
        return

    source = read("src/java/com/hadoop/compression/lzo/LzopInputStream.java")
    require_input = extract_java_block(
        source,
        r"^\s*static void requireInputAfterZeroProgress\(Decompressor decompressor\)",
    )
    if require_input is None:
        failures.append("Lzop read-decompress progress smoke check must extract requireInputAfterZeroProgress")
        return

    with tempfile.TemporaryDirectory(prefix="hadoop-refactor-lzop-read-decompress-") as workdir:
        workdir = Path(workdir)
        class_dir = workdir / "classes"
        class_dir.mkdir()
        harness = workdir / "LzopReadDecompressProgressHarness.java"
        hadoop_jar = ROOT / "lib/hadoop-core-0.20.2-cdh3u1.jar"
        harness.write_text(
            """
import java.io.IOException;
import org.apache.hadoop.io.compress.Decompressor;

public class LzopReadDecompressProgressHarness {
""".lstrip() + require_input + """

  public static void main(String[] args) throws Exception {
    assertInputRequestAccepted();
    assertStalledDecompressorRejected();
  }

  private static void assertInputRequestAccepted() throws Exception {
    requireInputAfterZeroProgress(new ProgressDecompressor(true));
  }

  private static void assertStalledDecompressorRejected() throws Exception {
    try {
      requireInputAfterZeroProgress(new ProgressDecompressor(false));
      throw new AssertionError("Stalled read decompressor was accepted");
    } catch (IOException expected) {
      if (expected.getMessage().indexOf("made no progress") < 0) {
        throw new AssertionError("Unexpected read-progress message: " +
          expected.getMessage());
      }
    }
  }

  private static final class ProgressDecompressor implements Decompressor {
    private final boolean needsInput;

    ProgressDecompressor(boolean needsInput) {
      this.needsInput = needsInput;
    }

    public void setInput(byte[] b, int off, int len) { }
    public boolean needsInput() { return needsInput; }
    public void setDictionary(byte[] b, int off, int len) { }
    public boolean needsDictionary() { return false; }
    public boolean finished() { return false; }
    public int decompress(byte[] b, int off, int len) { return 0; }
    public void reset() { }
    public void end() { }
  }
}
""",
            encoding="utf-8",
        )
        compile_result = subprocess.run(
            [
                "javac",
                "-source",
                "1.6",
                "-target",
                "1.6",
                "-cp",
                str(hadoop_jar),
                "-d",
                str(class_dir),
                str(harness),
            ],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        require(
            compile_result.returncode == 0,
            "Lzop read-decompress progress smoke check must compile: " + compile_result.stderr.strip(),
            failures,
        )
        if compile_result.returncode != 0:
            return

        try:
            run_result = subprocess.run(
                ["java", "-cp", str(class_dir) + os.pathsep + str(hadoop_jar),
                 "LzopReadDecompressProgressHarness"],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            failures.append("Lzop read-decompress progress smoke harness must not hang on stalled decompression")
            return
        require(
            run_result.returncode == 0,
            "Lzop read-decompress progress smoke harness must preserve input requests and reject stalls: " +
            (run_result.stderr or run_result.stdout).strip(),
            failures,
        )


def main():
    failures = []
    required_files = [
        ".gitignore",
        ".github/workflows/check.yml",
        "CHANGES.md",
        "COPYING",
        "Makefile",
        "README.md",
        "SECURITY.md",
        "VISION.md",
        "build.xml",
        "ivy.xml",
        "ivy/ivysettings.xml",
        "ivy/libraries.properties",
        "lib/hadoop-core-0.20.2-cdh3u1.jar",
        "src/get_build_revision.sh",
        "src/native/bootstrap.sh",
        "src/native/packageNativeHadoop.sh",
        "src/java/com/hadoop/compression/lzo/LzoCodec.java",
        "src/java/com/hadoop/compression/lzo/LzoIndex.java",
        "src/java/com/hadoop/compression/lzo/LzopHeaderValidation.java",
        "scripts/test-lzop-hostile-streams.py",
        "scripts/test-lzop-hostile-mutations.py",
        "scripts/test-make-spaced-path.py",
        "src/test/com/hadoop/compression/lzo/TestLzoCodec.java",
        "docs/plans/2026-06-08-legacy-build-baseline.md",
        "docs/plans/2026-06-08-native-packaging-guard.md",
        "docs/plans/2026-06-08-build-revision-helper-guard.md",
        "docs/plans/2026-06-09-lzo-index-empty-boundary.md",
        "docs/plans/2026-06-09-lzo-index-byte-count-guard.md",
        "docs/plans/2026-06-09-lzo-index-open-failure-guard.md",
        "docs/plans/2026-06-09-lzo-block-size-boundary.md",
        "docs/plans/2026-06-09-make-gate-aliases.md",
        "docs/plans/2026-06-09-lzo-index-rename-failure-guard.md",
        "docs/plans/2026-06-09-lzo-index-position-order-guard.md",
        "docs/plans/2026-06-10-ci-baseline.md",
        "docs/plans/2026-06-10-distributed-index-rename-guard.md",
        "docs/plans/2026-06-12-distributed-input-error-propagation.md",
        "docs/plans/2026-06-13-lzo-compressed-length-consistency.md",
        "docs/plans/2026-06-13-lzop-extra-header-length-boundary.md",
        "docs/plans/2026-06-13-lzop-zero-progress-read.md",
        "docs/plans/2026-06-13-location-independent-make.md",
        "docs/plans/2026-06-15-lzop-close-progress.md",
        "docs/plans/2026-06-17-lzop-read-decompress-progress.md",
        "docs/plans/2026-06-25-lzop-output-close-cleanup-design.md",
        "docs/plans/2026-06-25-lzop-output-close-cleanup.md",
        "docs/plans/2026-06-26-lzop-output-progress.md",
        "docs/plans/2026-06-26-lzop-output-construction-pool.md",
    ]

    for relative_path in required_files:
        require((ROOT / relative_path).is_file(), f"Required file missing: {relative_path}", failures)

    build_xml = read("build.xml")
    ivysettings = read("ivy/ivysettings.xml")
    lzo_index_source = read("src/java/com/hadoop/compression/lzo/LzoIndex.java")
    lzop_input_source = read("src/java/com/hadoop/compression/lzo/LzopInputStream.java")
    lzop_output_source = read("src/java/com/hadoop/compression/lzo/LzopOutputStream.java")
    lzop_codec_source = read("src/java/com/hadoop/compression/lzo/LzopCodec.java")
    lzop_header_validation_source = read("src/java/com/hadoop/compression/lzo/LzopHeaderValidation.java")
    split_record_reader_source = read("src/java/com/hadoop/mapreduce/LzoSplitRecordReader.java")
    index_record_writer_source = read("src/java/com/hadoop/mapreduce/LzoIndexRecordWriter.java")
    distributed_indexer_source = read("src/java/com/hadoop/compression/lzo/DistributedLzoIndexer.java")
    makefile = read("Makefile")
    package_script = read("src/native/packageNativeHadoop.sh")
    build_revision_script = read("src/get_build_revision.sh")
    readme = read("README.md")
    vision = read("VISION.md")
    security = read("SECURITY.md")
    changes = read("CHANGES.md")
    gitignore = read(".gitignore")
    ci_workflow = CI_WORKFLOW.read_text(encoding="utf-8") if CI_WORKFLOW.exists() else ""
    ci_plan = CI_PLAN.read_text(encoding="utf-8") if CI_PLAN.exists() else ""
    record_writer_rename_plan = RECORD_WRITER_RENAME_PLAN.read_text(encoding="utf-8") if RECORD_WRITER_RENAME_PLAN.exists() else ""
    input_traversal_plan = INPUT_TRAVERSAL_PLAN.read_text(encoding="utf-8") if INPUT_TRAVERSAL_PLAN.exists() else ""
    compressed_length_plan = COMPRESSED_LENGTH_PLAN.read_text(encoding="utf-8") if COMPRESSED_LENGTH_PLAN.exists() else ""
    extra_header_length_plan = EXTRA_HEADER_LENGTH_PLAN.read_text(encoding="utf-8") if EXTRA_HEADER_LENGTH_PLAN.exists() else ""
    zero_progress_read_plan = ZERO_PROGRESS_READ_PLAN.read_text(encoding="utf-8") if ZERO_PROGRESS_READ_PLAN.exists() else ""
    location_independent_make_plan = LOCATION_INDEPENDENT_MAKE_PLAN.read_text(encoding="utf-8") if LOCATION_INDEPENDENT_MAKE_PLAN.exists() else ""
    close_progress_plan = CLOSE_PROGRESS_PLAN.read_text(encoding="utf-8") if CLOSE_PROGRESS_PLAN.exists() else ""
    read_decompress_progress_plan = READ_DECOMPRESS_PROGRESS_PLAN.read_text(encoding="utf-8") if READ_DECOMPRESS_PROGRESS_PLAN.exists() else ""
    output_compression_progress_plan = OUTPUT_COMPRESSION_PROGRESS_PLAN.read_text(encoding="utf-8") if OUTPUT_COMPRESSION_PROGRESS_PLAN.exists() else ""
    plan = PLAN.read_text(encoding="utf-8") if PLAN.exists() else ""
    empty_index_plan = EMPTY_INDEX_PLAN.read_text(encoding="utf-8") if EMPTY_INDEX_PLAN.exists() else ""
    index_byte_plan = INDEX_BYTE_PLAN.read_text(encoding="utf-8") if INDEX_BYTE_PLAN.exists() else ""
    index_open_plan = INDEX_OPEN_PLAN.read_text(encoding="utf-8") if INDEX_OPEN_PLAN.exists() else ""
    block_size_plan = BLOCK_SIZE_PLAN.read_text(encoding="utf-8") if BLOCK_SIZE_PLAN.exists() else ""
    index_rename_plan = INDEX_RENAME_PLAN.read_text(encoding="utf-8") if INDEX_RENAME_PLAN.exists() else ""
    index_position_plan = INDEX_POSITION_PLAN.read_text(encoding="utf-8") if INDEX_POSITION_PLAN.exists() else ""
    native_plan = read("docs/plans/2026-06-08-native-packaging-guard.md")
    revision_plan = read("docs/plans/2026-06-08-build-revision-helper-guard.md")

    for xml_file in ["build.xml", "ivy.xml", "ivy/ivysettings.xml"]:
        try:
            ET.parse(str(ROOT / xml_file))
        except ET.ParseError as error:
            failures.append(f"{xml_file} is not well-formed XML: {error}")

    require("https://repo1.maven.org/maven2" in build_xml and "https://repo1.maven.org/maven2" in ivysettings,
            "build.xml must use HTTPS Maven Central download endpoints",
            failures)
    require("https://repository.apache.org/snapshots/" in ivysettings,
            "ivysettings.xml must use the HTTPS Apache snapshot repository",
            failures)
    require("https://docs.oracle.com/javase/6/docs/api/" in build_xml,
            "build.xml must use the HTTPS Java 6 javadoc URL",
            failures)
    for forbidden_url in [
        "http://repo1.maven.org",
        "http://repo2.maven.org",
        "http://people.apache.org/repo/m2-snapshot-repository",
        "http://java.sun.com/javase/6/docs/api",
    ]:
        require(forbidden_url not in build_xml + ivysettings,
            f"controlled build metadata must not use {forbidden_url}",
            failures)
    require('javac.version" value="1.6"' in build_xml and "hadoop-core-0.20.2-cdh3u1.jar" in "\n".join(str(path) for path in (ROOT / "lib").glob("*.jar")),
            "baseline must preserve legacy Java 6 target and checked-in Hadoop 0.20/CDH3 jar",
            failures)
    require('target name="test"' in build_xml and '<junit ' in build_xml,
            "build.xml must keep the Ant JUnit test target",
            failures)
    require(".PHONY: build check lint test" in makefile and "lint test build: check" in makefile,
            "Makefile must expose lint, test, build, and check gate targets",
            failures)
    require("override makefile_space := __HADOOP_REFACTOR_MAKEFILE_SPACE__" in makefile and
            "override encoded_makefile_list := $(patsubst $(makefile_space)%,%,$(subst $(space),$(makefile_space),$(MAKEFILE_LIST)))" in makefile and
            "override ROOT := $(subst $(makefile_space),$(space),$(abspath $(dir $(lastword $(encoded_makefile_list)))))" in makefile and
            '@python3 "$(ROOT)/scripts/check-baseline.py"' in makefile and
            '@python3 "$(ROOT)/scripts/test-make-spaced-path.py"' in makefile,
            "Makefile must invoke the baseline checker through the loaded repository root",
            failures)
    workflow_lines = ci_workflow.splitlines()
    require(workflow_lines.count("permissions:") == 1 and
            workflow_lines.count("  contents: read") == 1 and
            not re.search(r"^[ \t]+permissions:", ci_workflow, re.MULTILINE) and
            not re.search(r"^[ \t]+[^#][^:]*:[ \t]*write(?:[ \t]*#.*)?$", ci_workflow, re.MULTILINE) and
            "write-all" not in ci_workflow,
            "GitHub Actions must keep one top-level read-only permissions block",
            failures)
    require(ci_workflow.count("uses: actions/checkout@") == 1 and
            "uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6.0.3" in ci_workflow and
            workflow_lines.count("          persist-credentials: false") == 1,
            "GitHub Actions must keep one pinned, credential-free checkout step",
            failures)
    require(ci_workflow.count("uses: actions/setup-python@") == 1 and
            "uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0" in ci_workflow and
            workflow_lines.count('          python-version: "3.12"') == 1 and
            ci_workflow.count("uses: actions/setup-java@") == 1 and
            "uses: actions/setup-java@be666c2fcd27ec809703dec50e508c2fdc7f6654 # v5.2.0" in ci_workflow and
            workflow_lines.count("          distribution: temurin") == 1 and
            workflow_lines.count('          java-version: "8"') == 1 and
            workflow_lines.count("      - run: make check") == 1 and
            "cancel-in-progress: true" in ci_workflow and
            "runs-on: ubuntu-24.04" in ci_workflow and
            "timeout-minutes: 10" in ci_workflow and
            "workflow_dispatch:" in ci_workflow,
            "GitHub Actions must keep the pinned Python 3.12 and Java 8 check contract",
            failures)

    java_sources = sorted((ROOT / "src/java").rglob("*.java"))
    java_tests = sorted((ROOT / "src/test").rglob("Test*.java"))
    native_sources = sorted((ROOT / "src/native").rglob("*.c"))
    require(len(java_sources) >= 20,
            "expected Hadoop/LZO Java source inventory is missing",
            failures)
    require(len(java_tests) >= 5,
            "expected Hadoop/LZO Java test inventory is missing",
            failures)
    require(len(native_sources) >= 2,
            "expected native LZO C source inventory is missing",
            failures)

    for script in ["src/get_build_revision.sh", "src/native/bootstrap.sh", "src/native/packageNativeHadoop.sh"]:
        if (ROOT / script).exists():
            result = run(["bash", "-n", script])
            require(result.returncode == 0,
                    f"{script} must pass bash syntax checks: {result.stderr.strip()}",
                    failures)

    require("for platform in `ls" not in package_script and 'for platform_dir in "$source_root"/*' in package_script,
            "packageNativeHadoop.sh must avoid parsing ls output for platform directories",
            failures)
    require('mkdir -p "$dist_platform_dir"' in package_script and 'cd "$source_dir"' in package_script,
            "packageNativeHadoop.sh must quote native package paths",
            failures)
    verify_native_packaging_script(failures)
    require("set -euo pipefail" in build_revision_script and '"${BUILD_REVISION:-}"' in build_revision_script and "printf '%s\\n'" in build_revision_script and 'dirname "${BASH_SOURCE[0]}"' in build_revision_script and 'cat "$ARCHIVE_VERSION_FILE"' in build_revision_script,
            "get_build_revision.sh must quote overrides and script-relative archive fallback paths",
            failures)
    verify_build_revision_script(failures)
    require("static int getBlockCount(int indexByteCount)" in lzo_index_source and "indexByteCount % 8" in lzo_index_source and "multiple of 8" in lzo_index_source and "getBlockCount(bytesIn.remaining())" in lzo_index_source,
            "LzoIndex must reject malformed index files whose byte count is not 8-byte aligned",
            failures)
    require("assertCorruptIndexByteCountRejected" in Path(__file__).read_text(encoding="utf-8"),
            "LzoIndex smoke check must cover malformed index byte counts",
            failures)
    require("static void validateBlockPosition" in lzo_index_source and "position < 0" in lzo_index_source and "position <= previousPosition" in lzo_index_source and "validateBlockPosition(position, previousPosition)" in lzo_index_source,
            "LzoIndex.readIndex must reject negative or non-increasing block positions",
            failures)
    require("assertInvalidIndexPositionsRejected" in Path(__file__).read_text(encoding="utf-8"),
            "LzoIndex smoke check must cover malformed index block positions",
            failures)
    require("static void validateBlockSizes" in lzo_index_source and "uncompressedBlockSize > LzoCodec.MAX_BLOCK_SIZE" in lzo_index_source and "compressedBlockSize > LzoCodec.MAX_BLOCK_SIZE" in lzo_index_source,
            "LzoIndex.createIndex must reject oversized LZO block sizes before seeking",
            failures)
    require("assertOversizedIndexBlockSizesRejected" in Path(__file__).read_text(encoding="utf-8"),
            "LzoIndex smoke check must cover malformed LZO block sizes",
            failures)
    require("compressedBlockSize > uncompressedBlockSize" in lzo_index_source,
            "LzoIndex.createIndex must reject compressed lengths larger than the declared uncompressed length",
            failures)
    checker_source = Path(__file__).read_text(encoding="utf-8")
    bounded_timeout_count = len(re.findall(
        r"^\s*timeout=5,\s*$", checker_source, flags=re.MULTILINE
    ))
    require(checker_source.count("assertCompressedLengthConsistency();") == 2
            and "private static void assertCompressedLengthConsistency()" in checker_source,
            "LzoIndex smoke check must cover compressed-length consistency",
            failures)
    require("nextBlockSize > LzoCodec.MAX_BLOCK_SIZE" in lzop_input_source and "compressedLen <= 0" in lzop_input_source and "compressedLen > LzoCodec.MAX_BLOCK_SIZE" in lzop_input_source,
            "LzopInputStream must reject invalid compressed and uncompressed block sizes",
            failures)
    require("compressedLen > uncompressedBlockSize" in lzop_input_source and "compressedLen == uncompressedBlockSize" in lzop_input_source,
            "LzopInputStream must reject impossible compressed lengths and only treat equal lengths as uncompressed",
            failures)
    require("extraFieldLength < 0" in lzop_header_validation_source and
            "extraFieldLength > LzoCodec.MAX_BLOCK_SIZE" in lzop_header_validation_source and
            "LzopHeaderValidation.validateExtraFieldLength(hitem)" in lzop_input_source and
            "readHeaderBytes(in, extraFieldLength, adler, crc32)" in lzop_input_source and
            "new byte[extraFieldLength]" not in lzop_input_source,
            "LzopInputStream must bound and stream extra-header fields",
            failures)
    hostile_stream_test = read("scripts/test-lzop-hostile-streams.py")
    hostile_mutation_test = read("scripts/test-lzop-hostile-mutations.py")
    require("scripts/test-lzop-hostile-streams.py" in makefile and
            "scripts/test-lzop-hostile-mutations.py" in makefile and
            all(name in hostile_stream_test for name in (
                "rejectsPartialBlockTrailer",
                "rejectsDeclaredBlockOverrun",
                "rejectsUnknownHighHeaderFlags",
                "streamsHeaderBytesWithoutLargeAllocation",
                "stopsCloseDrainWhenMoreInputIsRequired",
                "rejectsTrueCloseDrainStalls",
                "acceptsObservableCompressionProgress",
                "rejectsUnchangedCompressionState",
            )),
            "Make check must execute the hostile Lzop stream boundary suite",
            failures)
    require("MUTATIONS = (" in hostile_mutation_test and
            "Rejected %d hostile Lzop mutations." in hostile_mutation_test,
            "Make check must execute mutation-sensitive Lzop stream proofs",
            failures)
    require("verify_lzo_index_empty_alignment(failures)\n    verify_lzop_extra_header_length(failures)" in checker_source and
            "assertRejected(-1, \"must not be negative\")" in checker_source and
            checker_source.count("assertRejected(LzoCodec.MAX_BLOCK_SIZE + 1") == 2,
            "Lzop extra-header smoke coverage must execute both rejected boundaries",
            failures)
    require("if ( ret == 0 )" in lzop_input_source and
            "Input stream made no progress while reading" in lzop_input_source,
            "LzopInputStream.readFully must reject zero-progress reads",
            failures)
    require(checker_source.count("assertZeroProgressRejected();") == 2 and
            bounded_timeout_count == 3 and
            "verify_lzop_read_progress(failures)" in checker_source,
            "Lzop read-progress smoke coverage must execute with a bounded timeout",
            failures)
    require("static void drainDecompressor(Decompressor decompressor)" in lzop_input_source and
            "decompressed <= 0" in lzop_input_source and
            "Decompressor made no progress while closing" in lzop_input_source,
            "LzopInputStream close draining must reject zero progress",
            failures)
    require("IOException closeFailure = null" in lzop_input_source and
            "drainDecompressor(decompressor);" in lzop_input_source and
            "CodecPool.returnDecompressor(decompressor);" in lzop_input_source and
            "throw closeFailure;" in lzop_input_source,
            "LzopInputStream close failures must preserve stream and decompressor cleanup",
            failures)
    require("if (closed) {\n      return;\n    }\n    closed = true;" in lzop_output_source and
            "static IOException closeOutput(OutputStream output," in lzop_output_source and
            "closeFailure = closeOutput(out, closeFailure);" in lzop_output_source and
            "closeFailure = closeOutput(indexOut, closeFailure);" in lzop_output_source and
            "CodecPool.returnCompressor(compressor);" in lzop_output_source and
            "throw closeFailure;" in lzop_output_source,
            "LzopOutputStream close failures must preserve output and compressor cleanup",
            failures)
    require("static void validateCompressionProgress(" in lzop_output_source and
            "Compressor made no progress" in lzop_output_source and
            "validateCompressionProgress(bytesReadBefore, bytesWrittenBefore," in lzop_output_source,
            "LzopOutputStream compression must reject unchanged-state stalls",
            failures)
    require("private CompressionOutputStream createPooledOutputStream(" in lzop_codec_source and
            lzop_codec_source.count("return createPooledOutputStream(out, null);") == 1 and
            lzop_codec_source.count("return createPooledOutputStream(out, indexOut);") == 1 and
            "Compressor compressor = getCompressor();" in lzop_codec_source and
            "return createIndexedOutputStream(out, indexOut, compressor);" in lzop_codec_source and
            lzop_codec_source.count("CodecPool.returnCompressor(compressor);") == 3 and
            "catch (IOException e)" in lzop_codec_source and
            "catch (RuntimeException e)" in lzop_codec_source and
            "catch (Error e)" in lzop_codec_source,
            "LzopCodec must return internally borrowed compressors on output construction failure",
            failures)
    require(checker_source.count("assertMultiStepDrainCompletes();") == 2 and
            checker_source.count("assertZeroProgressCloseRejected();") == 2 and
            "verify_lzop_close_progress(failures)" in checker_source and
            bounded_timeout_count == 3,
            "Lzop close-progress smoke coverage must execute both scenarios with a bounded timeout",
            failures)
    require("static void requireInputAfterZeroProgress(Decompressor decompressor)" in lzop_input_source and
            "Decompressor made no progress while reading" in lzop_input_source and
            "requireInputAfterZeroProgress(decompressor);" in lzop_input_source,
            "LzopInputStream normal reads must reject stalled decompression",
            failures)
    require(checker_source.count("assertInputRequestAccepted();") == 2 and
            checker_source.count("assertStalledDecompressorRejected();") == 2 and
            "verify_lzop_read_decompress_progress(failures)" in checker_source and
            bounded_timeout_count == 3,
            "Lzop read-decompress progress coverage must execute both scenarios with a bounded timeout",
            failures)
    require("uncompressedBlockSize > LzoCodec.MAX_BLOCK_SIZE" in split_record_reader_source and "compressedBlockSize > LzoCodec.MAX_BLOCK_SIZE" in split_record_reader_source,
            "LzoSplitRecordReader must reject oversized LZO block sizes before seeking",
            failures)
    require("compressedBlockSize > uncompressedBlockSize" in split_record_reader_source,
            "LzoSplitRecordReader must reject impossible compressed lengths before seeking",
            failures)
    require("import java.io.FileNotFoundException;" in lzo_index_source and "catch (FileNotFoundException fileNotFound)" in lzo_index_source,
            "LzoIndex.readIndex must only fall back when the index file is missing",
            failures)
    require("assertMissingIndexReturnsEmpty" in Path(__file__).read_text(encoding="utf-8") and "assertOpenFailurePropagates" in Path(__file__).read_text(encoding="utf-8"),
            "LzoIndex smoke check must cover missing-index fallback and non-missing open failures",
            failures)
    require("static void commitIndexFile" in lzo_index_source and "if (!fs.rename(tmpOutputFile, outputFile))" in lzo_index_source and "Failed to move temporary LZO index" in lzo_index_source,
            "LzoIndex.createIndex must surface temporary-index rename failures",
            failures)
    require("public static void commitIndexFile" in lzo_index_source,
            "LzoIndex commit helper must be available to distributed index writers",
            failures)
    require("LzoIndex.commitIndexFile(fs, tmpIndexPath, realIndexPath);" in index_record_writer_source,
            "LzoIndexRecordWriter must surface temporary-index rename failures",
            failures)
    require("assertRenameFailurePropagates" in Path(__file__).read_text(encoding="utf-8"),
            "LzoIndex smoke check must cover temporary-index rename failures",
            failures)
    walk_path_source = extract_java_block(
        distributed_indexer_source,
        r"private void walkPath\(Path path, PathFilter pathFilter, List<Path> accumulator\)\s*throws IOException\s*\{",
    )
    require(walk_path_source is not None,
            "DistributedLzoIndexer.walkPath must propagate IOException",
            failures)
    require(walk_path_source is not None and "catch (IOException" not in walk_path_source,
            "DistributedLzoIndexer.walkPath must not swallow filesystem traversal failures",
            failures)
    require("public int run(String[] args) throws Exception" in distributed_indexer_source and
            "public static void main(String[] args) throws Exception" in distributed_indexer_source,
            "DistributedLzoIndexer entry points must preserve traversal failure propagation",
            failures)
    verify_lzo_index_empty_alignment(failures)
    verify_lzop_extra_header_length(failures)
    verify_lzop_read_progress(failures)
    verify_lzop_close_progress(failures)
    verify_lzop_read_decompress_progress(failures)

    require("build/" in gitignore and "target/" in gitignore and "*.class" in gitignore and "*.so" in gitignore and ".DS_Store" in gitignore,
            ".gitignore must exclude generated build products and local machine files",
            failures)
    require("make lint" in readme and "make test" in readme and "make build" in readme and "make check" in readme and "scripts/check-baseline.py" in readme and "Ant" in readme and "Java 8" in readme and "build revision" in readme,
            "README must document static verification and legacy build prerequisites",
            failures)
    require("GitHub Actions" in readme and "docs/plans/2026-06-10-ci-baseline.md" in readme,
            "README must document the hosted CI baseline",
            failures)
    require("malformed index byte counts" in readme,
            "README must document the malformed LZO index byte-count guard",
            failures)
    require("malformed index positions" in readme,
            "README must document the malformed LZO index position guard",
            failures)
    require("oversized LZO block sizes" in readme,
            "README must document the oversized LZO block-size guard",
            failures)
    require("lengths larger than their declared uncompressed lengths" in readme,
            "README must document compressed-length consistency validation",
            failures)
    require("extra-header fields are bounded" in readme,
            "README must document lzop extra-header length validation",
            failures)
    require("index open failures" in readme,
            "README must document the LZO index open-failure guard",
            failures)
    require("index rename failures" in readme,
            "README must document the LZO index rename-failure guard",
            failures)
    require("distributed input traversal failures" in readme,
            "README must document distributed input traversal failure propagation",
            failures)
    require("absolute Makefile path" in readme and "any working directory" in readme and
            "paths containing spaces" in readme,
            "README must document location-independent Make verification",
            failures)
    require("scripts/check-baseline.py" in vision and "make lint" in vision and "make test" in vision and "make build" in vision and "HTTPS" in vision and "native packaging" in vision and "build revision" in vision and "malformed index byte counts" in vision and "malformed index positions" in vision and "oversized LZO block sizes" in vision and "index open failures" in vision and "index rename failures" in vision,
            "VISION must describe the current static build baseline",
            failures)
    require("GitHub Actions" in vision,
            "VISION must describe the hosted CI baseline",
            failures)
    require("distributed input traversal failures" in vision,
            "VISION must preserve distributed traversal failure propagation",
            failures)
    require("impossible compressed" in vision and "length relations" in vision,
            "VISION must describe compressed-length consistency validation",
            failures)
    require("extra-header streaming" in vision,
            "VISION must describe bounded lzop extra-header streaming",
            failures)
    require("Maven Central" in security and "HTTPS" in security and "oversized block sizes" in security and "malformed index positions" in security,
            "SECURITY must describe build dependency download expectations",
            failures)
    require("GitHub Actions" in security and "make check" in security,
            "SECURITY must describe the hosted CI verification boundary",
            failures)
    require("impossible compressed-length" in security,
            "SECURITY must describe the malformed compressed-length boundary",
            failures)
    require("bounded streaming extra-header fields" in security,
            "SECURITY must describe the lzop extra-header boundary",
            failures)
    require("HTTPS" in changes and "make lint" in changes and "make test" in changes and "make build" in changes and "make check" in changes and "build revision" in changes and "empty-index" in changes and "malformed index byte counts" in changes and "malformed index positions" in changes and "oversized LZO block sizes" in changes and "index open failures" in changes and "index rename failures" in changes,
            "CHANGES must record the legacy build baseline",
            failures)
    require("GitHub Actions" in changes,
            "CHANGES must record the hosted CI baseline",
            failures)
    require("distributed input traversal failures" in changes,
            "CHANGES must record distributed traversal failure propagation",
            failures)
    require("compressed LZO block lengths larger than their declared" in changes,
            "CHANGES must record compressed-length consistency validation",
            failures)
    require("Bounded lzop extra-header field allocation" in changes,
            "CHANGES must record lzop extra-header allocation validation",
            failures)
    require("Make verification target derive the checkout root" in changes and
            "external directories" in changes,
            "CHANGES must record location-independent Make verification",
            failures)
    require("status: completed" in plan,
            "plan must be marked completed",
            failures)
    require("status: completed" in native_plan,
            "native packaging plan must be marked completed",
            failures)
    require("status: completed" in revision_plan,
            "build revision helper plan must be marked completed",
            failures)
    output_construction_pool_plan = OUTPUT_CONSTRUCTION_POOL_PLAN.read_text(
        encoding="utf-8"
    ) if OUTPUT_CONSTRUCTION_POOL_PLAN.exists() else ""
    require("Status: Completed" in output_construction_pool_plan and
            "checked construction failure" in output_construction_pool_plan and
            "configuration/native failure" in output_construction_pool_plan and
            "`Error`" in output_construction_pool_plan,
            "Lzop output construction pool plan must preserve the ownership decision",
            failures)
    require("status: completed" in empty_index_plan,
            "empty-index boundary plan must be marked completed",
            failures)
    require("status: completed" in index_byte_plan,
            "index byte-count plan must be marked completed",
            failures)
    require("status: completed" in index_open_plan,
            "index open-failure plan must be marked completed",
            failures)
    require("status: completed" in block_size_plan,
            "block-size boundary plan must be marked completed",
            failures)
    require("status: completed" in index_rename_plan,
            "index rename-failure plan must be marked completed",
            failures)
    require("status: completed" in index_position_plan,
            "index position-order plan must be marked completed",
            failures)
    require("status: completed" in ci_plan.lower() and "make check" in ci_plan,
            "CI baseline plan must be marked completed and record make check verification",
            failures)
    require("status: completed" in record_writer_rename_plan.lower() and "make check" in record_writer_rename_plan,
            "distributed index rename plan must be marked completed and record verification",
            failures)
    input_traversal_statuses = re.findall(
        r"^status: .+$", input_traversal_plan, flags=re.MULTILINE
    )
    input_traversal_sections = input_traversal_plan.split(
        "## Verification Completed\n", 1
    )
    input_traversal_verification = (
        input_traversal_sections[1] if len(input_traversal_sections) == 2 else ""
    )
    input_traversal_required_evidence = (
        "All four Make gates",
        "push run `27393718908`",
        "pull-request run `27393721234`",
        "push run `27393737055`",
        "CodeQL setup run `27402321777`",
        "mutation restoring the `walkPath` exception-swallowing block",
    )
    require(input_traversal_statuses == ["status: completed"]
            and all(item in input_traversal_verification for item in input_traversal_required_evidence)
            and re.search(r"\b(?:pending|todo|tbd|not run)\b", input_traversal_verification, re.IGNORECASE) is None,
            "distributed input traversal plan must record completed status and actual verification",
            failures)
    compressed_length_statuses = re.findall(
        r"^status: .+$", compressed_length_plan, flags=re.MULTILINE
    )
    compressed_length_sections = compressed_length_plan.split(
        "## Verification Completed\n", 1
    )
    compressed_length_verification = (
        compressed_length_sections[1]
        if len(compressed_length_sections) == 2 else ""
    )
    compressed_length_required_evidence = (
        "All four Make gates",
        "assertCompressedLengthConsistency",
        "python3 -m py_compile scripts/check-baseline.py",
        "git diff --check",
        "Seven isolated hostile mutations",
    )
    require(compressed_length_statuses == ["status: completed"]
            and all(item in compressed_length_verification for item in compressed_length_required_evidence)
            and re.search(r"\b(?:pending|todo|tbd|not run)\b", compressed_length_verification, re.IGNORECASE) is None,
            "compressed-length consistency plan must record completed status and actual verification",
            failures)
    extra_header_length_statuses = re.findall(
        r"^status: .+$", extra_header_length_plan, flags=re.MULTILINE
    )
    extra_header_length_sections = extra_header_length_plan.split(
        "## Verification Completed\n", 1
    )
    extra_header_length_verification = (
        extra_header_length_sections[1]
        if len(extra_header_length_sections) == 2 else ""
    )
    extra_header_length_required_evidence = (
        "focused lzop extra-header smoke harness passed",
        "All four Make gates passed",
        "python3 -m py_compile scripts/check-baseline.py",
        "Validator-call removal failed",
        "Negative-bound removal and upper-bound removal",
        "Harness-invocation removal failed",
        "hosted pull-request and CodeQL snapshot",
    )
    require(extra_header_length_statuses == ["status: completed"]
            and all(item in extra_header_length_verification for item in extra_header_length_required_evidence)
            and re.search(r"\b(?:pending|todo|tbd|not run)\b", extra_header_length_verification, re.IGNORECASE) is None,
            "lzop extra-header plan must record completed status and actual verification",
            failures)
    zero_progress_read_statuses = re.findall(
        r"^status: .+$", zero_progress_read_plan, flags=re.MULTILINE
    )
    zero_progress_read_sections = zero_progress_read_plan.split(
        "## Verification Completed\n", 1
    )
    zero_progress_read_verification = (
        zero_progress_read_sections[1]
        if len(zero_progress_read_sections) == 2 else ""
    )
    zero_progress_read_required_evidence = (
        "focused Lzop read-progress smoke harness passed",
        "All four Make gates passed",
        "python3 -m py_compile scripts/check-baseline.py",
        "zero-progress rejection removal mutation failed",
        "harness-scenario removal mutation failed",
        "subprocess-timeout removal mutation failed",
        "hosted pull-request and CodeQL snapshot",
    )
    require(zero_progress_read_statuses == ["status: completed"]
            and all(item in zero_progress_read_verification for item in zero_progress_read_required_evidence)
            and re.search(r"\b(?:pending|todo|tbd|not run)\b", zero_progress_read_verification, re.IGNORECASE) is None,
            "lzop zero-progress plan must record completed status and actual verification",
            failures)
    location_independent_make_statuses = re.findall(
        r"^status: .+$", location_independent_make_plan, flags=re.MULTILINE
    )
    location_independent_make_sections = location_independent_make_plan.split(
        "## Verification Completed\n", 1
    )
    location_independent_make_verification = (
        location_independent_make_sections[1]
        if len(location_independent_make_sections) == 2 else ""
    )
    location_independent_make_required_evidence = (
        "Root and external-directory Make gates passed",
        "root-derivation mutation failed",
        "checker-invocation mutation failed",
        "plan-status mutation failed",
        "plan-evidence mutation failed",
        "documentation mutation failed",
    )
    require(location_independent_make_statuses == ["status: completed"]
            and all(item in location_independent_make_verification
                    for item in location_independent_make_required_evidence)
            and re.search(r"\b(?:pending|todo|tbd|not run)\b",
                          location_independent_make_verification,
                          re.IGNORECASE) is None,
            "location-independent Make plan must record completed status and actual verification",
            failures)
    require("zero bytes" in read("AGENTS.md") and
            "Positive-length Lzop reads that return zero bytes fail closed" in read("README.md") and
            "zero-byte result must not create an unbounded parsing loop" in read("SECURITY.md") and
            "Reject zero-progress positive-length Lzop reads" in read("VISION.md") and
            "Rejected zero-progress positive-length Lzop reads" in read("CHANGES.md"),
            "Project guidance must document zero-progress Lzop read rejection",
            failures)
    close_progress_guidance = "Close-time Lzop decompression rejects zero progress so malformed streams cannot hang cleanup."
    require(all(close_progress_guidance in read(path) for path in
                ["AGENTS.md", "README.md", "SECURITY.md", "VISION.md", "CHANGES.md"]),
            "Project guidance must document zero-progress Lzop close rejection",
            failures)
    read_decompress_progress_guidance = "Read-time Lzop decompression rejects zero progress without an input request so malformed streams cannot hang normal reads."
    require(all(read_decompress_progress_guidance in read(path) for path in
                ["AGENTS.md", "README.md", "SECURITY.md", "VISION.md", "CHANGES.md"]),
            "Project guidance must document zero-progress Lzop read-decompress rejection",
            failures)
    close_progress_statuses = re.findall(
        r"^status: .+$", close_progress_plan, flags=re.MULTILINE
    )
    close_progress_sections = close_progress_plan.split(
        "## Verification Completed\n", 1
    )
    close_progress_verification = (
        close_progress_sections[1]
        if len(close_progress_sections) == 2 else ""
    )
    close_progress_required_evidence = (
        "pre-fix close hang reproduced",
        "focused Lzop close-progress smoke harness passed",
        "All four Make gates passed",
        "python3 -m py_compile scripts/check-baseline.py",
        "progress-rejection removal mutation failed",
        "successful-drain scenario removal mutation failed",
        "cleanup-preservation mutation failed",
        "subprocess-timeout removal mutation failed",
        "plan-evidence removal mutation failed",
        "hosted pull-request and security-alert snapshot",
    )
    require(close_progress_statuses == ["status: completed"]
            and all(item in close_progress_verification
                    for item in close_progress_required_evidence)
            and re.search(r"\b(?:pending|todo|tbd|not run)\b",
                          close_progress_verification,
                          re.IGNORECASE) is None,
            "lzop close-progress plan must record completed status and actual verification",
            failures)
    read_decompress_progress_statuses = re.findall(
        r"^status: .+$", read_decompress_progress_plan, flags=re.MULTILINE
    )
    read_decompress_progress_sections = read_decompress_progress_plan.split(
        "## Verification Completed\n", 1
    )
    read_decompress_progress_verification = (
        read_decompress_progress_sections[1]
        if len(read_decompress_progress_sections) == 2 else ""
    )
    normalized_read_decompress_progress_verification = " ".join(
        read_decompress_progress_verification.split()
    )
    read_decompress_progress_required_evidence = (
        "pre-fix read hang reproduced",
        "focused Lzop read-decompress progress smoke harness passed",
        "All four Make gates passed separately",
        "absolute Makefile check passed from an external directory",
        "Six isolated mutations were rejected",
        "no actionable findings",
        "Both canonical implementation-head checks passed",
        "push run 27664412273",
        "pull-request run 27664415741",
        "zero open code-scanning, Dependabot, and secret-scanning alerts",
        "Ant, native LZO libraries, a Hadoop cluster, and production compressed corpora were not available or exercised",
    )
    require(read_decompress_progress_statuses == ["status: completed"]
            and all(item in normalized_read_decompress_progress_verification
                    for item in read_decompress_progress_required_evidence)
            and re.search(r"\b(?:pending|todo|tbd|not run|not yet)\b",
                          read_decompress_progress_verification,
                          re.IGNORECASE) is None,
            "lzop read-decompress progress plan must record completed status and actual verification",
            failures)
    output_compression_progress_statuses = re.findall(
        r"^status: .+$", output_compression_progress_plan, flags=re.MULTILINE
    )
    require(output_compression_progress_statuses == ["status: completed"],
            "lzop output-compression progress plan must be marked completed",
            failures)
    make_gates_plan = MAKE_GATES_PLAN.read_text(encoding="utf-8") if MAKE_GATES_PLAN.exists() else ""
    require("status: completed" in make_gates_plan,
            "Make gate alias plan must be marked completed",
            failures)

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("Hadoop-Refactor legacy build baseline checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
