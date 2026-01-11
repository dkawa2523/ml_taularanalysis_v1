#!/usr/bin/env python3
"""Minimal ClearML pipeline probe (script repo/branch/entry_point/version_num check)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from datetime import datetime, timezone

from omegaconf import OmegaConf

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from tabular_analysis import platform_adapter


def _repo_root() -> Path:
    return REPO_ROOT


def _resolve_output_dir(base: str | None) -> Path:
    if base:
        root = Path(base).expanduser()
        return root if root.is_absolute() else _repo_root() / root
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return _repo_root() / "outputs" / f"clearml_probe_{stamp}"


def _git_head() -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(_repo_root()), "rev-parse", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _needs_quote(text: str) -> bool:
    if not text:
        return True
    for ch in text:
        if ch.isspace() or ch in "[]{}(),=":
            return True
    return False


def _quote(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _format_value(value: str) -> str:
    text = str(value)
    return _quote(text) if _needs_quote(text) else text


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Missing config: {path}")
    return OmegaConf.load(path)


def _print_script_check(script: dict[str, Any], cfg: Any) -> int:
    repo = platform_adapter.normalize_clearml_repository(script.get("repository"))
    branch = str(script.get("branch") or "")
    entry_point = platform_adapter.normalize_clearml_entry_point(script.get("entry_point"))
    version_num = str(script.get("version_num") or "")

    expected_repo = platform_adapter.normalize_clearml_repository(
        platform_adapter.detect_git_repository_url(_repo_root())
    )
    expected_branch = platform_adapter.detect_git_branch(_repo_root()) or ""
    expected_entry = "tools/clearml_entrypoint.py"
    clearml_cfg = getattr(getattr(cfg, "run", None), "clearml", None)
    version_mode = str(getattr(clearml_cfg, "code_version_mode", None) or "branch_head")

    print("pipeline script:")
    print(f"  repository: {repo or 'none'}")
    print(f"  branch: {branch or 'none'}")
    print(f"  entry_point: {entry_point or 'none'}")
    print(f"  version_num: {version_num or 'branch_head'}")
    print(f"  expected repo: {expected_repo or 'none'}")
    print(f"  expected branch: {expected_branch or 'none'}")
    print(f"  expected entry_point: {expected_entry}")
    print(f"  code_version_mode: {version_mode}")

    exit_code = 0
    if expected_repo and repo != expected_repo:
        print("[warn] repository mismatch")
        exit_code = 1
    if expected_branch and branch != expected_branch:
        print("[warn] branch mismatch")
        exit_code = 1
    if entry_point != expected_entry:
        print("[warn] entry_point mismatch")
        exit_code = 1
    if version_mode == "branch_head" and version_num:
        print("[warn] version_num should be empty for branch_head")
        exit_code = 1
    if version_mode == "pin_commit" and expected_repo:
        commit = _git_head()
        if not version_num or not commit or not commit.startswith(version_num):
            print("[warn] version_num does not match HEAD")
            exit_code = 1
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Minimal ClearML pipeline probe.")
    parser.add_argument("--dataset-path", required=True, help="Dataset path for dataset_register.")
    parser.add_argument("--target-column", default="target", help="Target column name.")
    parser.add_argument("--queue", default=None, help="ClearML queue name for pipeline steps.")
    parser.add_argument("--config-dir", default=None, help="Path to conf/ directory.")
    parser.add_argument("--output-dir", default=None, help="Base output dir for the run.")
    parser.add_argument("--usecase-id", default=None, help="Override run.usecase_id.")
    args = parser.parse_args(argv)

    output_root = _resolve_output_dir(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / "99_pipeline"
    log_path = output_root / "clearml_probe.log"

    overrides = [
        "task=pipeline",
        "run.clearml.enabled=true",
        "run.clearml.execution=pipeline_controller_local",
        "pipeline.run_dataset_register=true",
        "pipeline.run_preprocess=false",
        "pipeline.run_train=false",
        "pipeline.run_leaderboard=false",
        "pipeline.run_infer=false",
        f"data.dataset_path={_format_value(args.dataset_path)}",
        f"data.target_column={_format_value(args.target_column)}",
        f"run.output_dir={str(output_root)}",
    ]
    if args.queue:
        overrides.append(f"run.clearml.queue_name={args.queue}")
    if args.usecase_id:
        overrides.append(f"run.usecase_id={args.usecase_id}")

    cmd = [sys.executable, "-m", "tabular_analysis.cli", *overrides]
    env = os.environ.copy()
    if args.config_dir:
        env["TABULAR_ANALYSIS_CONFIG_DIR"] = str(Path(args.config_dir).expanduser())
    proc = subprocess.run(
        cmd,
        cwd=str(_repo_root()),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log_path.write_text(proc.stdout or "", encoding="utf-8")
    if proc.returncode != 0:
        print(f"pipeline run failed (exit={proc.returncode})")
        print(f"log: {log_path}")
        return proc.returncode

    config_path = run_dir / "config_resolved.yaml"
    report_links_path = run_dir / "report_links.json"
    if not config_path.exists() or not report_links_path.exists():
        print("pipeline outputs not found; check the log.")
        print(f"log: {log_path}")
        return 1

    cfg = _load_yaml(config_path)
    usecase_id = getattr(getattr(cfg, "run", None), "usecase_id", None)
    print(f"usecase_id: {usecase_id}")

    links = json.loads(report_links_path.read_text(encoding="utf-8"))
    pipeline_entry = links.get("pipeline") if isinstance(links, dict) else None
    pipeline_task_id = None
    if isinstance(pipeline_entry, dict):
        pipeline_task_id = pipeline_entry.get("task_id")
    if not pipeline_task_id:
        print("pipeline task id not found in report_links.json")
        print(f"log: {log_path}")
        return 1
    print(f"pipeline_task_id: {pipeline_task_id}")

    script = platform_adapter.get_clearml_task_script(str(pipeline_task_id))
    return _print_script_check(script, cfg)


if __name__ == "__main__":
    raise SystemExit(main())
