#!/bin/sh
set -eu

# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# packageNativeHadoop.sh - A simple script to help package native-hadoop libraries

#
# Note: 
# This script relies on the following environment variables to function correctly:
#  * BASE_NATIVE_LIB_DIR
#  * BUILD_NATIVE_DIR
#  * DIST_LIB_DIR
# All these are setup by build.xml.
#

: "${BASE_NATIVE_LIB_DIR:?BASE_NATIVE_LIB_DIR must be set}"
: "${BUILD_NATIVE_DIR:?BUILD_NATIVE_DIR must be set}"
: "${DIST_LIB_DIR:?DIST_LIB_DIR must be set}"

copy_libraries() {
  source_root=$1
  source_suffix=$2

  if [ ! -d "$source_root" ]; then
    return
  fi

  for platform_dir in "$source_root"/*; do
    [ -d "$platform_dir" ] || continue

    platform=$(basename "$platform_dir")
    source_dir="$platform_dir/$source_suffix"
    dist_platform_dir="$DIST_LIB_DIR/$platform"

    [ -d "$source_dir" ] || continue

    found_library=false
    for library in "$source_dir"/*gplcompression*; do
      [ -e "$library" ] || continue
      found_library=true
      break
    done
    [ "$found_library" = true ] || continue

    if [ ! -d "$dist_platform_dir" ]; then
      mkdir -p "$dist_platform_dir"
      echo "Created $dist_platform_dir"
    fi

    echo "Copying libraries in $source_dir to $dist_platform_dir/"
    (cd "$source_dir" && tar cf - *gplcompression*) |
      (cd "$dist_platform_dir" && tar xfBp -)
  done
}

# Copy the pre-built libraries in $BASE_NATIVE_LIB_DIR
copy_libraries "$BASE_NATIVE_LIB_DIR" "."

# Copy the custom-built libraries in $BUILD_NATIVE_DIR
copy_libraries "$BUILD_NATIVE_DIR" "lib"

#vim: ts=2: sw=2: et
