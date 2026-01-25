#!/usr/bin/env python3
"""Local test for rollback_model and champion_challenger."""

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


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _make_train_run(
    run_dir: Path,
    *,
    model_id: str,
    best_score: float,
    primary_metric: str,
    processed_dataset_id: str,
    split_hash: str,
    task_type: str = "classification",
    direction: str = "maximize",
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    out = {
        "model_id": model_id,
        "best_score": best_score,
        "primary_metric": primary_metric,
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "task_type": task_type,
    }
    manifest = {
        "schema_version": "v1",
        "code_version": "test",
        "platform_version": "test",
        "process": "train_model",
        "created_at": "2026-01-01T00:00:00Z",
        "inputs": {"direction": direction, "task_type": task_type},
        "outputs": {"model_id": model_id, "best_score": best_score, "primary_metric": primary_metric},
        "hashes": {"config_hash": "test"},
    }
    _write_json(run_dir / "out.json", out)
    _write_json(run_dir / "manifest.json", manifest)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    work_root = repo / "work" / "_test_model_lifecycle"
    out_root = work_root / "out"
    ref_root = work_root / "refs"
    out_root.mkdir(parents=True, exist_ok=True)
    ref_root.mkdir(parents=True, exist_ok=True)

    usecase_id = "LifecycleLocal"
    processed_dataset_id = "ds_local"
    split_hash = "split_local"

    current_run = ref_root / "current"
    previous_run = ref_root / "previous"
    challenger_run = ref_root / "challenger"

    _make_train_run(
        current_run,
        model_id="model_current",
        best_score=0.70,
        primary_metric="accuracy",
        processed_dataset_id=processed_dataset_id,
        split_hash=split_hash,
    )
    _make_train_run(
        previous_run,
        model_id="model_previous",
        best_score=0.65,
        primary_metric="accuracy",
        processed_dataset_id=processed_dataset_id,
        split_hash=split_hash,
    )
    _make_train_run(
        challenger_run,
        model_id="model_challenger",
        best_score=0.80,
        primary_metric="accuracy",
        processed_dataset_id=processed_dataset_id,
        split_hash=split_hash,
    )

    registry_state = {
        "schema_version": 1,
        "updated_at": "2026-01-01T00:00:00Z",
        "usecases": {
            usecase_id: {
                "stages": {
                    "production": {
                        "current": {
                            "model_id": "model_current",
                            "train_task_ref": str(current_run),
                            "processed_dataset_id": processed_dataset_id,
                            "split_hash": split_hash,
                        },
                        "history": [
                            {
                                "model_id": "model_previous",
                                "train_task_ref": str(previous_run),
                                "processed_dataset_id": processed_dataset_id,
                                "split_hash": split_hash,
                            }
                        ],
                    }
                }
            }
        },
    }
    _write_json(out_root / "model_registry_state.json", registry_state)

    py = sys.executable

    _run(
        [
            py,
            "-m",
            "tabular_analysis.cli",
            "task=rollback_model",
            "run.clearml.enabled=false",
            f"run.output_dir={out_root}",
            f"run.usecase_id={usecase_id}",
            "rollback.stage=production",
            "rollback.reason=unit_test",
        ],
        cwd=repo,
    )
    rollback_dir = out_root / "07_rollback_model"
    _must_exist(rollback_dir / "config_resolved.yaml")
    _must_exist(rollback_dir / "out.json")
    _must_exist(rollback_dir / "manifest.json")
    _must_exist(rollback_dir / "rollback.json")

    rollback_payload = _load_json(rollback_dir / "rollback.json")
    before = rollback_payload.get("before", {})
    after = rollback_payload.get("after", {})
    if before.get("model_id") != "model_current":
        raise AssertionError("rollback before model_id mismatch")
    if after.get("model_id") != "model_previous":
        raise AssertionError("rollback after model_id mismatch")

    registry_after = _load_json(out_root / "model_registry_state.json")
    current_after = (
        registry_after.get("usecases", {})
        .get(usecase_id, {})
        .get("stages", {})
        .get("production", {})
        .get("current", {})
    )
    if current_after.get("model_id") != "model_previous":
        raise AssertionError("registry state did not rollback to previous model")

    _run(
        [
            py,
            "-m",
            "tabular_analysis.cli",
            "task=champion_challenger",
            "run.clearml.enabled=false",
            f"run.output_dir={out_root}",
            f"run.usecase_id={usecase_id}",
            f"champion_challenger.challenger_model_ref={challenger_run}",
            f"champion_challenger.eval_dataset_ref={previous_run}",
        ],
        cwd=repo,
    )
    cc_dir = out_root / "07_champion_challenger"
    _must_exist(cc_dir / "config_resolved.yaml")
    _must_exist(cc_dir / "out.json")
    _must_exist(cc_dir / "manifest.json")
    _must_exist(cc_dir / "champion_challenger.csv")
    _must_exist(cc_dir / "decision.json")
    _must_exist(cc_dir / "summary.md")

    decision = _load_json(cc_dir / "decision.json")
    if decision.get("winner") != "challenger":
        raise AssertionError("expected challenger to win")

    print("OK: model lifecycle local")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
