#!/usr/bin/env python3
"""Convert staged .ipynb files to .py using marimo convert.

This script is used as a pre-commit hook to automatically convert
Jupyter notebooks to Python files using marimo.
"""

import subprocess
import sys
from pathlib import Path


def get_staged_notebooks() -> list[Path]:
    """Get list of staged .ipynb files."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        check=True,
    )
    files = result.stdout.strip().split("\n")
    return [Path(f) for f in files if f.endswith(".ipynb") and Path(f).exists()]


def convert_notebook(notebook_path: Path) -> Path | None:
    """Convert a notebook to .py using marimo convert.

    Returns the path if file was changed, None if unchanged.
    """
    py_path = notebook_path.with_suffix(".py")
    result = subprocess.run(
        ["uv", "run", "marimo", "convert", str(notebook_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"Error converting {notebook_path}: {result.stderr}", file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, "marimo convert")

    new_content = result.stdout

    # Auto-fix with ruff (write to temp, then format)
    py_path.write_text(new_content)
    subprocess.run(
        ["uv", "run", "ruff", "check", "--fix", "--unsafe-fixes", str(py_path)],
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["uv", "run", "ruff", "format", str(py_path)],
        capture_output=True,
        check=False,
    )

    # Check if the converted file is already staged with same content
    staged_result = subprocess.run(
        ["git", "show", f":{py_path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if staged_result.returncode == 0:
        staged_content = staged_result.stdout
        current_content = py_path.read_text()
        if staged_content == current_content:
            return None  # No change needed

    return py_path


def main() -> int:
    """Main function."""
    notebooks = get_staged_notebooks()

    if not notebooks:
        return 0

    converted_files: list[Path] = []
    errors = False

    for notebook in notebooks:
        try:
            py_file = convert_notebook(notebook)
            if py_file is not None:
                converted_files.append(py_file)
                print(f"Converted: {notebook} -> {py_file}")
            else:
                print(f"Up-to-date: {notebook}")
        except subprocess.CalledProcessError:
            errors = True

    if errors:
        return 1

    # Stage the converted files only if there are changes
    if converted_files:
        subprocess.run(
            ["git", "add", *[str(f) for f in converted_files]],
            check=True,
        )
        print(f"\nStaged {len(converted_files)} converted file(s).")
        print("Please commit again to include the converted files.")
        return 1  # Fail to prompt re-commit

    return 0


if __name__ == "__main__":
    sys.exit(main())
