#!/usr/bin/env python3
"""Smoke test for champion registry (local mode)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def _run(cmd: List[str], *, cwd: Path) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed (exit={proc.returncode})\n$ {' '.join(cmd)}\n\n{proc.stdout}")
    return proc.stdout


def _must_exist(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(str(path))


def _load_json(path: Path) -> Dict[str, Any]:
    _must_exist(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _check_common(stage_dir: Path) -> None:
    _must_exist(stage_dir / "config_resolved.yaml")
    _must_exist(stage_dir / "out.json")
    _must_exist(stage_dir / "manifest.json")


def _make_toy_csv(path: Path) -> None:
    try:
        import numpy as np
        import pandas as pd
    except Exception as exc:
        raise RuntimeError(
            "pandas/numpy are required for smoke tests. Install requirements/base.txt first.\n" + str(exc)
        )

    rng = np.random.default_rng(7)
    n = 200
    df = pd.DataFrame(
        {
            "num1": rng.normal(0, 1, size=n),
            "num2": rng.normal(5, 2, size=n),
            "cat": rng.choice(["a", "b", "c"], size=n),
        }
    )
    df["target"] = 0.2 * df["num1"] - 0.15 * df["num2"] + (df["cat"] == "b").astype(float) + rng.normal(
        0, 0.1, size=n
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _reset_registry(registry_path: Path, usecase_id: str) -> None:
    if not registry_path.exists():
        return
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("champions.json must be a JSON object")
    usecases = data.get("usecases")
    if not isinstance(usecases, dict):
        return
    if usecase_id in usecases:
        del usecases[usecase_id]
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    smoke_root = repo / "work" / "_smoke_champion_registry"
    tmp = smoke_root / "tmp"
    out_root = smoke_root / "out"
    tmp.mkdir(parents=True, exist_ok=True)
    out_root.mkdir(parents=True, exist_ok=True)

    usecase_id = "SmokeChampionRegistry"
    registry_path = repo / "work" / "registry" / "champions.json"
    _reset_registry(registry_path, usecase_id)

    csv_path = tmp / "toy.csv"
    _make_toy_csv(csv_path)

    py = sys.executable
    base_out = out_root / "base"

    _run(
        [
            py,
            "-m",
            "tabular_analysis.cli",
            "task=dataset_register",
            "run.clearml.enabled=false",
            f"run.output_dir={base_out}",
            f"run.usecase_id={usecase_id}",
            f"data.dataset_path={csv_path}",
            "data.target_column=target",
        ],
        cwd=repo,
    )
    ds_dir = base_out / "01_dataset_register"
    _check_common(ds_dir)

    _run(
        [
            py,
            "-m",
            "tabular_analysis.cli",
            "task=preprocess",
            "run.clearml.enabled=false",
            f"run.output_dir={base_out}",
            f"run.usecase_id={usecase_id}",
            f"data.dataset_path={csv_path}",
            "data.target_column=target",
            "group/preprocess=stdscaler_ohe",
            "data.split.strategy=random",
            "data.split.seed=42",
        ],
        cwd=repo,
    )
    pp_dir = base_out / "02_preprocess"
    _check_common(pp_dir)

    pp_out = _load_json(pp_dir / "out.json")
    processed_ref = pp_out["processed_dataset_id"]

    train1_out = out_root / "train1"
    train2_out = out_root / "train2"

    _run(
        [
            py,
            "-m",
            "tabular_analysis.cli",
            "task=train_model",
            "run.clearml.enabled=false",
            f"run.output_dir={train1_out}",
            f"run.usecase_id={usecase_id}",
            f"data.processed_dataset_id={processed_ref}",
            f"train.inputs.preprocess_run_dir={pp_dir}",
            "eval.primary_metric=rmse",
            "group/model=ridge",
        ],
        cwd=repo,
    )
    tr1_dir = train1_out / "03_train_model"
    _check_common(tr1_dir)

    _run(
        [
            py,
            "-m",
            "tabular_analysis.cli",
            "task=train_model",
            "run.clearml.enabled=false",
            f"run.output_dir={train2_out}",
            f"run.usecase_id={usecase_id}",
            f"data.processed_dataset_id={processed_ref}",
            f"train.inputs.preprocess_run_dir={pp_dir}",
            "eval.primary_metric=rmse",
            "group/model=lasso",
        ],
        cwd=repo,
    )
    tr2_dir = train2_out / "03_train_model"
    _check_common(tr2_dir)

    model_id_1 = _load_json(tr1_dir / "out.json")["model_id"]
    model_id_2 = _load_json(tr2_dir / "out.json")["model_id"]

    lb1_out = out_root / "lb1"
    lb2_out = out_root / "lb2"

    _run(
        [
            py,
            "-m",
            "tabular_analysis.cli",
            "task=leaderboard",
            "run.clearml.enabled=false",
            f"run.output_dir={lb1_out}",
            f"run.usecase_id={usecase_id}",
            f"leaderboard.train_task_ids=['{tr1_dir}']",
        ],
        cwd=repo,
    )
    lb1_dir = lb1_out / "05_leaderboard"
    _check_common(lb1_dir)

    _run(
        [
            py,
            "-m",
            "tabular_analysis.cli",
            "task=leaderboard",
            "run.clearml.enabled=false",
            f"run.output_dir={lb2_out}",
            f"run.usecase_id={usecase_id}",
            f"leaderboard.train_task_ids=['{tr2_dir}']",
        ],
        cwd=repo,
    )
    lb2_dir = lb2_out / "05_leaderboard"
    _check_common(lb2_dir)

    promo1_out = out_root / "promo1"
    promo2_out = out_root / "promo2"

    _run(
        [
            py,
            "-m",
            "tabular_analysis.cli",
            "task=promote_model",
            "run.clearml.enabled=false",
            f"run.output_dir={promo1_out}",
            f"run.usecase_id={usecase_id}",
            f"promote.source_leaderboard_dir={lb1_dir}",
            "promote.stage=production",
            "promote.set_champion=true",
        ],
        cwd=repo,
    )
    pm1_dir = promo1_out / "06_promote_model"
    _check_common(pm1_dir)

    _run(
        [
            py,
            "-m",
            "tabular_analysis.cli",
            "task=promote_model",
            "run.clearml.enabled=false",
            f"run.output_dir={promo2_out}",
            f"run.usecase_id={usecase_id}",
            f"promote.source_leaderboard_dir={lb2_dir}",
            "promote.stage=production",
            "promote.set_champion=true",
        ],
        cwd=repo,
    )
    pm2_dir = promo2_out / "06_promote_model"
    _check_common(pm2_dir)

    registry = _load_json(registry_path)
    usecases = registry.get("usecases", {})
    if usecase_id not in usecases:
        raise AssertionError("usecase_id not found in champion registry")
    entry = usecases[usecase_id]
    current = entry.get("current")
    history = entry.get("history")
    if not isinstance(current, dict):
        raise AssertionError("champion registry current entry missing")
    if current.get("model_id") != model_id_2:
        raise AssertionError("champion registry did not update to second promotion")
    if not isinstance(history, list) or not history:
        raise AssertionError("champion registry history missing after second promotion")
    if history[0].get("model_id") != model_id_1:
        raise AssertionError("champion registry history does not contain previous champion")

    rollback_out = out_root / "rollback"
    _run(
        [
            py,
            "-m",
            "tabular_analysis.cli",
            "task=promote_model",
            "run.clearml.enabled=false",
            f"run.output_dir={rollback_out}",
            f"run.usecase_id={usecase_id}",
            "promote.rollback=true",
            "promote.stage=production",
            "promote.set_champion=true",
        ],
        cwd=repo,
    )
    rb_dir = rollback_out / "06_promote_model"
    _check_common(rb_dir)

    registry_after = _load_json(registry_path)
    entry_after = registry_after.get("usecases", {}).get(usecase_id)
    if not isinstance(entry_after, dict):
        raise AssertionError("champion registry missing after rollback")
    current_after = entry_after.get("current")
    if not isinstance(current_after, dict):
        raise AssertionError("champion registry current entry missing after rollback")
    if current_after.get("model_id") != model_id_1:
        raise AssertionError("rollback did not restore previous champion")

    print("OK: champion registry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
