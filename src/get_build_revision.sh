#!/bin/bash
set -euo pipefail

# Allow user to specify - this is done by packages
if [ -n "${BUILD_REVISION:-}" ]; then
  printf '%s\n' "$BUILD_REVISION"
  exit 0
fi

# If we're in git, use that
BUILD_REVISION=$(git rev-parse HEAD 2>/dev/null || true)
if [ -n "$BUILD_REVISION" ]; then
  printf '%s\n' "$BUILD_REVISION"
  exit 0
fi

# Otherwise try to use the .archive-version file which
# is filled in by git exports (eg github downloads)
BIN=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ARCHIVE_VERSION_FILE="$BIN/../.archive-version"
if [ -r "$ARCHIVE_VERSION_FILE" ]; then
  BUILD_REVISION=$(cat "$ARCHIVE_VERSION_FILE")
else
  BUILD_REVISION=""
fi

if [ -n "$BUILD_REVISION" ] && [[ "$BUILD_REVISION" != *Format* ]]; then
  printf '%s\n' "$BUILD_REVISION"
  exit 0
fi

# Give up
printf '%s\n' "Unknown build revision"
