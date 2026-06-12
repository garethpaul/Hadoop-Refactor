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
    ]

    for relative_path in required_files:
        require((ROOT / relative_path).is_file(), f"Required file missing: {relative_path}", failures)

    build_xml = read("build.xml")
    ivysettings = read("ivy/ivysettings.xml")
    lzo_index_source = read("src/java/com/hadoop/compression/lzo/LzoIndex.java")
    lzop_input_source = read("src/java/com/hadoop/compression/lzo/LzopInputStream.java")
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
    require("uncompressedBlockSize > LzoCodec.MAX_BLOCK_SIZE" in lzop_input_source and "compressedLen <= 0" in lzop_input_source and "compressedLen > LzoCodec.MAX_BLOCK_SIZE" in lzop_input_source,
            "LzopInputStream must reject invalid compressed and uncompressed block sizes",
            failures)
    require("uncompressedBlockSize > LzoCodec.MAX_BLOCK_SIZE" in split_record_reader_source and "compressedBlockSize > LzoCodec.MAX_BLOCK_SIZE" in split_record_reader_source,
            "LzoSplitRecordReader must reject oversized LZO block sizes before seeking",
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
    require("index open failures" in readme,
            "README must document the LZO index open-failure guard",
            failures)
    require("index rename failures" in readme,
            "README must document the LZO index rename-failure guard",
            failures)
    require("distributed input traversal failures" in readme,
            "README must document distributed input traversal failure propagation",
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
    require("Maven Central" in security and "HTTPS" in security and "oversized block sizes" in security and "malformed index positions" in security,
            "SECURITY must describe build dependency download expectations",
            failures)
    require("GitHub Actions" in security and "make check" in security,
            "SECURITY must describe the hosted CI verification boundary",
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
    require("status: completed" in plan,
            "plan must be marked completed",
            failures)
    require("status: completed" in native_plan,
            "native packaging plan must be marked completed",
            failures)
    require("status: completed" in revision_plan,
            "build revision helper plan must be marked completed",
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
    require("status: completed" in input_traversal_plan.lower() and "make check" in input_traversal_plan,
            "distributed input traversal plan must be marked completed and record verification",
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
