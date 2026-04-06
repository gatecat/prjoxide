#!/usr/bin/env bash

set -e

new_dir=${1:-db}
mkdir ./${new_dir}
pushd ${new_dir}

set -euo pipefail

root=`git rev-parse --show-toplevel`
SRC=$root/database
DST=$(pwd)

find "$SRC" -type d | while read -r dir; do
    rel="${dir#$SRC/}"
    [[ "$rel" == "$dir" ]] && continue  # skip root itself
    mkdir -p "$DST/$rel"
done

# Find all json files and recreate directory structure with symlinks
find "$SRC" -type f -name '*.json' ! -path "*/overlays.d/*" | while read -r file; do
    # Path relative to source root
    rel="${file#$SRC/}"

    # Destination path
    dest="$DST/$rel"

    # Create destination directory
    mkdir -p "$(dirname "$dest")"

    # Create symlink (overwrite if exists)
    ln -sf "$file" "$dest"
done
