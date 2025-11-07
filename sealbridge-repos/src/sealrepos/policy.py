# src/sealrepos/policy.py: Evaluates repository policies.
# This module is responsible for interpreting the configured policies for each
# repository, such as branch protections, push/pull directions, and path
# include/exclude globs. It provides a clear interface for other modules to
# check whether an action is permitted.

from typing import List
import pathspec

def is_protected_branch(branch: str, protected_branches: List[str]) -> bool:
    """Check if a branch is protected."""
    return branch in protected_branches

def build_pathspec(include: List[str], exclude: List[str]) -> pathspec.PathSpec:
    """Builds a pathspec object from include and exclude patterns."""
    spec = []
    # Add excludes first, with a negation
    for pattern in exclude:
        spec.append(f"!{pattern}")
    # Add includes
    for pattern in include:
        spec.append(pattern)
    return pathspec.PathSpec.from_lines('gitwildmatch', spec)

def get_matching_files(pathspec: pathspec.PathSpec, root: str) -> List[str]:
    """Gets a list of files matching the pathspec."""
    return list(pathspec.match_tree(root))
