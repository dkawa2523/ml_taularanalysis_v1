#!/usr/bin/env python3
"""Backward-compatible wrapper for run_pipeline_v2."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Run rehearsal scenarios (wrapper).")
    ap.add_argument("--repo", default=".", help="Repository root (default: current directory)")
    ap.add_argument("--mode", default="local", choices=["local", "logging"], help="Execution mode")
    ap.add_argument("--dry-run", action="store_true", help="Only print commands, do not execute")
    ap.add_argument(
        "--usecase-id",
        default=None,
        help="Optional usecase_id override (default: test_<dataset>_<timestamp>)",
    )
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    runner = repo / "tools" / "rehearsal" / "run_pipeline_v2.py"
    cmd = [sys.executable, str(runner), "--repo", str(repo), "--execution", args.mode]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.usecase_id:
        cmd.extend(["--usecase-id", args.usecase_id])
    proc = subprocess.run(cmd, cwd=str(repo))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
