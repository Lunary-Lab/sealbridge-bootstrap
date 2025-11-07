# src/sealrepos/util/fs.py: Filesystem utilities.
# This module provides safe and robust filesystem operations, such as atomically
# writing files and copying directory trees. The copy operation is designed to
# respect the include/exclude path policies defined in the configuration,
# preventing unwanted files from being mirrored.

import os
import shutil
from typing import List
import pathspec

def safe_copy_tree(src: str, dst: str, include: List[str], exclude: List[str]):
    """
    Copy a directory tree, filtering by include/exclude globs.
    """
    # 1. Get all files recursively from src, as relative paths
    all_files_rel = []
    for root, _, files in os.walk(src):
        for name in files:
            full_path = os.path.join(root, name)
            all_files_rel.append(os.path.relpath(full_path, src))

    # 2. Start with the full set of files
    files_to_process = set(all_files_rel)

    # 3. If include patterns are given, filter the set down
    if include:
        include_spec = pathspec.PathSpec.from_lines('gitwildmatch', include)
        files_to_process = set(include_spec.match_files(all_files_rel))

    # 4. Remove any files that match the exclude patterns
    if exclude:
        exclude_spec = pathspec.PathSpec.from_lines('gitwildmatch', exclude)
        excluded_files = set(exclude_spec.match_files(files_to_process))
        files_to_process -= excluded_files

    # 5. Copy the final set of files
    if os.path.exists(dst):
        shutil.rmtree(dst)

    for rel_path in files_to_process:
        # Prevent path traversal issues, although rel_path from os.walk should be safe
        if ".." in rel_path.split(os.path.sep):
            continue

        src_path = os.path.join(src, rel_path)
        dst_path = os.path.join(dst, rel_path)

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copy2(src_path, dst_path)


def atomic_write(path: str, content: str):
    """Write content to a file atomically."""
    temp_path = f"{path}.tmp"
    with open(temp_path, "w") as f:
        f.write(content)
    os.rename(temp_path, path)
