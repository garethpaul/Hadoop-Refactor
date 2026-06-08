#!/usr/bin/env python3
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/plans/2026-06-08-legacy-build-baseline.md"


def require(condition, message, failures):
    if not condition:
        failures.append(message)


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8", errors="replace")


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


def main():
    failures = []
    required_files = [
        ".gitignore",
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
        "src/test/com/hadoop/compression/lzo/TestLzoCodec.java",
        "docs/plans/2026-06-08-legacy-build-baseline.md",
        "docs/plans/2026-06-08-native-packaging-guard.md",
    ]

    for relative_path in required_files:
        require((ROOT / relative_path).is_file(), f"Required file missing: {relative_path}", failures)

    build_xml = read("build.xml")
    ivysettings = read("ivy/ivysettings.xml")
    package_script = read("src/native/packageNativeHadoop.sh")
    readme = read("README.md")
    vision = read("VISION.md")
    security = read("SECURITY.md")
    changes = read("CHANGES.md")
    gitignore = read(".gitignore")
    plan = PLAN.read_text(encoding="utf-8") if PLAN.exists() else ""
    native_plan = read("docs/plans/2026-06-08-native-packaging-guard.md")

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

    require("build/" in gitignore and "target/" in gitignore and "*.class" in gitignore and "*.so" in gitignore and ".DS_Store" in gitignore,
            ".gitignore must exclude generated build products and local machine files",
            failures)
    require("make check" in readme and "scripts/check-baseline.py" in readme and "Ant" in readme and "Java 8" in readme,
            "README must document static verification and legacy build prerequisites",
            failures)
    require("scripts/check-baseline.py" in vision and "HTTPS" in vision and "native packaging" in vision,
            "VISION must describe the current static build baseline",
            failures)
    require("Maven Central" in security and "HTTPS" in security,
            "SECURITY must describe build dependency download expectations",
            failures)
    require("HTTPS" in changes and "make check" in changes,
            "CHANGES must record the legacy build baseline",
            failures)
    require("status: completed" in plan,
            "plan must be marked completed",
            failures)
    require("status: completed" in native_plan,
            "native packaging plan must be marked completed",
            failures)

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("Hadoop-Refactor legacy build baseline checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
