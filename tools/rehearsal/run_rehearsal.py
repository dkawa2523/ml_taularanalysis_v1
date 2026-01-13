#!/usr/bin/env python3
"""Run local rehearsal scenarios for ClearML integration."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import platform as platform_mod
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence


def _format_cmd(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in cmd)


def _run(cmd: Sequence[str], *, cwd: Path, dry_run: bool) -> str:
    line = f"$ {_format_cmd(cmd)}"
    print(line)
    if dry_run:
        return ""
    proc = subprocess.run(
        list(cmd),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed (exit={proc.returncode})\n{line}\n\n{proc.stdout}")
    return proc.stdout


def _sanitize_identifier(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "-", value)
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    return sanitized.strip("-_") or "unknown"


def _dataset_token(path: Path) -> str:
    stem = Path(path.name).stem or path.name
    return _sanitize_identifier(stem)


def _make_toy_csv(path: Path) -> None:
    try:
        import numpy as np
        import pandas as pd
    except Exception as exc:
        raise RuntimeError(
            "pandas/numpy are required for rehearsal runs. Install requirements/base.txt first.\n"
            + str(exc)
        )

    rng = np.random.default_rng(0)
    n = 200
    df = pd.DataFrame(
        {
            "num1": rng.normal(0, 1, size=n),
            "num2": rng.normal(5, 2, size=n),
            "cat": rng.choice(["a", "b", "c"], size=n),
        }
    )
    df["target"] = 0.3 * df["num1"] - 0.1 * df["num2"] + (df["cat"] == "b").astype(float)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _utc_stamp(now: dt.datetime | None = None) -> tuple[str, str]:
    now_value = now or dt.datetime.now(dt.timezone.utc)
    stamp = now_value.strftime("%Y%m%d_%H%M%S")
    iso = now_value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return stamp, iso


def _render_log(
    *,
    timestamp_iso: str,
    mode: str,
    dry_run: bool,
    repo: Path,
    dataset_path: Path,
    output_dir: Path,
    usecase_id: str,
    commands: Iterable[Sequence[str]],
    result: str,
    error: str | None,
) -> str:
    lines: list[str] = [
        f"## {timestamp_iso}",
        f"- mode: {mode}",
        f"- dry_run: {str(dry_run).lower()}",
        f"- usecase_id: {usecase_id}",
        f"- repo: {repo}",
        f"- dataset_path: {dataset_path}",
        f"- output_dir: {output_dir}",
        f"- python: {sys.version.split()[0]} ({sys.executable})",
        f"- platform: {platform_mod.platform()}",
        "- commands:",
        "```bash",
    ]
    for cmd in commands:
        lines.append(f"$ {_format_cmd(cmd)}")
    lines.extend(["```", f"- result: {result}"])
    if error:
        lines.append(f"- error: {error}")
    lines.append("")
    return "\n".join(lines)


def _summarize_error(exc: Exception) -> str:
    text = str(exc).strip().replace("\r\n", "\n")
    if len(text) > 1200:
        return text[:1200] + "..."
    return text


def _build_pipeline_command(
    *,
    mode: str,
    py: str,
    output_dir: Path,
    dataset_path: Path,
    raw_dataset_id: str,
    usecase_id: str,
) -> list[str]:
    cmd = [
        py,
        "-m",
        "tabular_analysis.cli",
        "task=pipeline",
        f"run.output_dir={output_dir}",
        f"run.usecase_id={usecase_id}",
        f"data.raw_dataset_id={raw_dataset_id}",
        "data.target_column=target",
    ]
    if raw_dataset_id.startswith("local:"):
        cmd.append(f"data.dataset_path={dataset_path}")
    if mode == "local":
        cmd.append("run.clearml.enabled=false")
    elif mode == "logging":
        cmd.append("run.clearml.enabled=true")
        cmd.append("run.clearml.execution=logging")
    else:
        raise ValueError(f"Unsupported mode: {mode}")
    return cmd


def _build_dataset_register_command(
    *,
    mode: str,
    py: str,
    output_dir: Path,
    dataset_path: Path,
    usecase_id: str,
) -> list[str]:
    cmd = [
        py,
        "-m",
        "tabular_analysis.cli",
        "task=dataset_register",
        f"run.output_dir={output_dir}",
        f"run.usecase_id={usecase_id}",
        f"data.dataset_path={dataset_path}",
        "data.target_column=target",
    ]
    if mode == "local":
        cmd.append("run.clearml.enabled=false")
    elif mode == "logging":
        cmd.append("run.clearml.enabled=true")
        cmd.append("run.clearml.execution=logging")
    else:
        raise ValueError(f"Unsupported mode: {mode}")
    return cmd


def main() -> int:
    ap = argparse.ArgumentParser(description="Run rehearsal scenarios for local ClearML testing.")
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
    rehearsal_root = repo / "work" / "rehearsal"
    tmp_dir = rehearsal_root / "tmp"
    out_root = rehearsal_root / "out"

    dataset_path = tmp_dir / "toy.csv"
    stamp, timestamp_iso = _utc_stamp()
    dataset_token = _dataset_token(dataset_path)
    usecase_id = args.usecase_id or f"test_{dataset_token}_{stamp}"
    output_dir = out_root / args.mode / usecase_id

    py = sys.executable
    dataset_cmd = _build_dataset_register_command(
        mode=args.mode,
        py=py,
        output_dir=output_dir,
        dataset_path=dataset_path,
        usecase_id=usecase_id,
    )
    result = "dry-run (not executed)" if args.dry_run else "success"
    error: str | None = None
    raw_dataset_id = "<RAW_DATASET_ID>"
    if args.dry_run and args.mode == "local":
        raw_dataset_id = "local:<RAW_DATASET_ID>"
    if not args.dry_run:
        try:
            _make_toy_csv(dataset_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            _run(dataset_cmd, cwd=repo, dry_run=False)
            dataset_out = json.loads(
                (output_dir / "01_dataset_register" / "out.json").read_text(encoding="utf-8")
            )
            raw_dataset_id = str(dataset_out.get("raw_dataset_id") or "").strip()
        except Exception as exc:
            result = "failure"
            error = _summarize_error(exc)
            raw_dataset_id = ""
    if not raw_dataset_id:
        result = "failure"
        error = error or "dataset_register did not return raw_dataset_id."

    cmd = _build_pipeline_command(
        mode=args.mode,
        py=py,
        output_dir=output_dir,
        dataset_path=dataset_path,
        raw_dataset_id=raw_dataset_id,
        usecase_id=usecase_id,
    )

    commands = [dataset_cmd, cmd]
    error = error if result == "failure" else None

    try:
        if not args.dry_run and result != "failure":
            _run(cmd, cwd=repo, dry_run=False)
    except Exception as exc:
        result = "failure"
        error = _summarize_error(exc)
    finally:
        log_path = rehearsal_root / "rehearsal_log.md"
        entry = _render_log(
            timestamp_iso=timestamp_iso,
            mode=args.mode,
            dry_run=args.dry_run,
            repo=repo,
            dataset_path=dataset_path,
            output_dir=output_dir,
            usecase_id=usecase_id,
            commands=commands,
            result=result,
            error=error,
        )
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(entry)

    if result == "failure":
        return 1
    if args.dry_run:
        _run(cmd, cwd=repo, dry_run=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
