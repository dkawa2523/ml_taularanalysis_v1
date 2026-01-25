#!/usr/bin/env python3
"""Unified verification runner for local development and CI."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence, Tuple

Step = Tuple[str, List[str]]


def _repo_root(repo_arg: str | None) -> Path:
    if repo_arg:
        return Path(repo_arg).resolve()
    return Path(__file__).resolve().parents[2]


def _run(cmd: Sequence[str], *, cwd: Path) -> int:
    print(f"$ {' '.join(cmd)}")
    proc = subprocess.run(
        list(cmd), cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    output = (proc.stdout or "").rstrip()
    if output:
        print(output)
    if proc.returncode != 0:
        print(f"FAILED (exit={proc.returncode})")
    return proc.returncode


def _quick_steps(repo: Path, py: str) -> List[Step]:
    tests_dir = repo / "tools" / "tests"
    return [
        ("compileall", [py, "-m", "compileall", "-q", "src"]),
        ("serving_app", [py, str(tests_dir / "test_serving_app.py")]),
        (
            "smoke_ci_config",
            [
                py,
                str(tests_dir / "smoke_ci_config.py"),
                "--repo",
                str(repo),
            ],
        ),
        (
            "smoke_local",
            [
                py,
                str(tests_dir / "smoke_local.py"),
                "--repo",
                str(repo),
                "--until",
                "pipeline",
            ],
        ),
        (
            "smoke_doctor_lint",
            [
                py,
                str(tests_dir / "smoke_doctor_lint.py"),
                "--repo",
                str(repo),
            ],
        ),
        (
            "ui_contract_lint",
            [
                py,
                str(tests_dir / "test_ui_contract_lint.py"),
                "--repo",
                str(repo),
            ],
        ),
        (
            "smoke_classification",
            [
                py,
                str(tests_dir / "smoke_classification.py"),
                "--repo",
                str(repo),
                "--until",
                "leaderboard",
            ],
        ),
        (
            "smoke_multiclass",
            [
                py,
                str(tests_dir / "smoke_multiclass.py"),
                "--repo",
                str(repo),
            ],
        ),
        ("smoke_high_card_cat", [py, str(tests_dir / "smoke_high_card_cat.py")]),
        (
            "check_optional_models",
            [
                py,
                str(tests_dir / "check_optional_models.py"),
                "--repo",
                str(repo),
                "--models",
                "lgbm,xgboost,catboost,tabpfn",
            ],
        ),
        ("smoke_hpo", [py, str(tests_dir / "smoke_hpo.py"), "--repo", str(repo)]),
        ("smoke_report", [py, str(tests_dir / "smoke_report.py"), "--repo", str(repo)]),
        ("smoke_plots", [py, str(tests_dir / "smoke_plots.py"), "--repo", str(repo)]),
    ]


def _full_steps(repo: Path, py: str) -> List[Step]:
    steps = _quick_steps(repo, py)
    tests_dir = repo / "tools" / "tests"
    regression_script = tests_dir / "smoke_train_regression_model.py"
    if not regression_script.exists():
        print(f"SKIP: {regression_script} not found")
        return steps
    steps.extend(
        [
            (
                "smoke_train_regression_model (ridge)",
                [
                    py,
                    str(regression_script),
                    "--repo",
                    str(repo),
                    "--model",
                    "ridge",
                ],
            ),
            (
                "smoke_train_regression_model (random_forest)",
                [
                    py,
                    str(regression_script),
                    "--repo",
                    str(repo),
                    "--model",
                    "random_forest",
                    "--expect-feature-importance",
                ],
            ),
        ]
    )
    steps.extend(
        [
            (
                "smoke_imbalance",
                [py, str(tests_dir / "smoke_imbalance.py"), "--repo", str(repo)],
            ),
            (
                "smoke_uncertainty",
                [py, str(tests_dir / "smoke_uncertainty.py"), "--repo", str(repo)],
            ),
            (
                "smoke_calibration",
                [py, str(tests_dir / "smoke_calibration.py"), "--repo", str(repo)],
            ),
            (
                "smoke_metric_ci",
                [py, str(tests_dir / "smoke_metric_ci.py"), "--repo", str(repo)],
            ),
            (
                "smoke_decision_summary",
                [py, str(tests_dir / "smoke_decision_summary.py"), "--repo", str(repo)],
            ),
            (
                "smoke_champion_registry",
                [py, str(tests_dir / "smoke_champion_registry.py"), "--repo", str(repo)],
            ),
            (
                "smoke_drift_enhanced",
                [py, str(tests_dir / "smoke_drift_enhanced.py"), "--repo", str(repo)],
            ),
            (
                "smoke_batch_chunked",
                [py, str(tests_dir / "smoke_batch_chunked.py"), "--repo", str(repo)],
            ),
            ("smoke_serve_import", [py, str(tests_dir / "smoke_serve_import.py")]),
        ]
    )
    return steps


def _run_steps(steps: List[Step], *, cwd: Path) -> int:
    for name, cmd in steps:
        print(f"\n==> {name}")
        rc = _run(cmd, cwd=cwd)
        if rc != 0:
            return rc
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=None)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help="Run short verification suite.")
    mode.add_argument("--full", action="store_true", help="Run extended verification suite.")
    args = ap.parse_args()

    repo = _repo_root(args.repo)
    py = sys.executable

    if not args.quick and not args.full:
        args.quick = True

    steps = _full_steps(repo, py) if args.full else _quick_steps(repo, py)
    return _run_steps(steps, cwd=repo)


if __name__ == "__main__":
    raise SystemExit(main())
