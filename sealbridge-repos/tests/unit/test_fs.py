# tests/unit/test_fs.py: Unit tests for filesystem utilities.

import pytest
from pathlib import Path
from sealrepos.util.fs import safe_copy_tree, atomic_write

def test_atomic_write(tmp_path: Path):
    """Tests that atomic_write writes content correctly to a file."""
    file_path = tmp_path / "test.txt"
    content = "hello world"

    atomic_write(file_path, content)

    assert file_path.is_file()
    assert file_path.read_text() == content

def test_safe_copy_tree_with_filtering(tmp_path: Path):
    """Tests that safe_copy_tree correctly applies include and exclude filters."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()

    # Create a directory structure to test against
    (src / "a.py").write_text("python file")
    (src / "b.txt").write_text("text file")
    (src / "docs").mkdir()
    (src / "docs" / "c.md").write_text("markdown file")
    (src / "build").mkdir()
    (src / "build" / "artifact.bin").write_text("binary")

    # Define the filter rules
    include_patterns = ["*.py", "*.md"]
    exclude_patterns = ["build/"]

    # Execute the copy
    safe_copy_tree(str(src), str(dst), include_patterns, exclude_patterns)

    # Assert that the correct files were copied
    assert (dst / "a.py").is_file()
    assert (dst / "docs" / "c.md").is_file()

    # Assert that the incorrect files were NOT copied
    assert not (dst / "b.txt").exists()
    assert not (dst / "build").exists()

def test_safe_copy_tree_no_filter(tmp_path: Path):
    """Tests that safe_copy_tree copies everything when no filters are provided."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "file1.txt").write_text("file1")
    (src / "subdir").mkdir()
    (src / "subdir" / "file2.txt").write_text("file2")

    safe_copy_tree(str(src), str(dst), [], [])

    assert (dst / "file1.txt").is_file()
    assert (dst / "subdir" / "file2.txt").is_file()
