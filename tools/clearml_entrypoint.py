#!/usr/bin/env python3
"""ClearML entrypoint wrapper for src/ layout."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _find_repo_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for base in candidates:
        for parent in [base, *base.parents]:
            if (parent / "conf").exists():
                return parent
    raise RuntimeError("Could not locate repo root containing conf/ directory.")


def main(argv: list[str] | None = None) -> None:
    repo_root = _find_repo_root()
    src_path = repo_root / "src"
    src_str = str(src_path)
    if src_path.exists() and src_str not in sys.path:
        sys.path.insert(0, src_str)

    if not os.getenv("TABULAR_ANALYSIS_CONFIG_DIR"):
        os.environ["TABULAR_ANALYSIS_CONFIG_DIR"] = str(repo_root / "conf")

    from tabular_analysis import cli

    cli.main(argv)


if __name__ == "__main__":
    main(sys.argv[1:])
