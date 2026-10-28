"""Repository checks that CI runs on every pull request.

Fails when a notebook is invalid or still holds outputs, or when datasets, training runs
or weights are in the repository.

    python scripts/check_repo.py          # check
    python scripts/check_repo.py --fix    # clear notebook outputs in place, then check
"""

import subprocess
import sys
from pathlib import Path

import nbformat

# Datasets are downloaded by the notebooks and weights go to GitHub Releases.
FORBIDDEN_DIRS = {"data", "runs"}
FORBIDDEN_SUFFIXES = {".pt", ".onnx", ".zip"}


def repo_files():
    # Tracked files plus new ones not yet added, so a check before `git add` sees them too.
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [Path(f) for f in out.splitlines()]


def check_notebook(path, fix):
    nb = nbformat.read(path, as_version=4)
    if fix:
        for cell in nb.cells:
            if cell.cell_type == "code":
                cell.outputs = []
                cell.execution_count = None
        nb.metadata.pop("widgets", None)  # progress-bar widget state Colab leaves behind
        nbformat.write(nb, path)

    problems = []
    try:
        nbformat.validate(nb)
    except nbformat.ValidationError as e:
        problems.append(f"invalid notebook: {e.message}")
    dirty = [i for i, c in enumerate(nb.cells, 1)
             if c.cell_type == "code" and (c.outputs or c.execution_count is not None)]
    if dirty or "widgets" in nb.metadata:
        problems.append(f"outputs not cleared (cells {dirty}); run with --fix")
    return problems


def main():
    fix = "--fix" in sys.argv[1:]
    problems = []
    for f in repo_files():
        if FORBIDDEN_DIRS & set(f.parts[:-1]) or f.suffix in FORBIDDEN_SUFFIXES:
            problems.append(f"{f}: datasets, runs and weights must not be committed")
        elif f.suffix == ".ipynb" and f.exists():
            problems += [f"{f}: {p}" for p in check_notebook(f, fix)]

    for p in problems:
        print(p)
    print(f"{len(problems)} problem(s)" if problems else "All checks passed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
