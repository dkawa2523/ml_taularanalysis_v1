"""Hydra CLI entrypoint.

この CLI は *開発途中* のスケルトンです。
Codex タスク（work/tasks/T00x）を進めることで、各タスクが実装されます。

実行例（実装が進んだ後）:
  python -m tabular_analysis.cli task=preprocess data.dataset_path=... data.target_column=...

ポイント:
- `task.name` でプロセスを切り替える
- ClearML 連携・manifest/out.json/hashes 等は `platform_adapter.py` 経由で ml-platform を利用する
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List, Optional

from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf


def _resolve_config_dir() -> Path:
    """conf/ ディレクトリを解決する。

    - 環境変数 TABULAR_ANALYSIS_CONFIG_DIR があればそれを優先
    - なければカレントの conf/ を探索
    - 最後に、パッケージ位置から 2 階層上の conf/ を探索

    NOTE: 本リポジトリは editable install + repo root 実行を想定。
    """

    env = os.getenv("TABULAR_ANALYSIS_CONFIG_DIR")
    if env:
        p = Path(env).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"TABULAR_ANALYSIS_CONFIG_DIR does not exist: {p}")
        return p

    candidates = [
        Path.cwd() / "conf",
        Path(__file__).resolve().parents[2] / "conf",
    ]
    for c in candidates:
        if c.exists():
            return c

    raise FileNotFoundError(
        "conf/ directory was not found. Run from repository root or set TABULAR_ANALYSIS_CONFIG_DIR."
    )


def _select_runner(task_name: str):
    if task_name == "dataset_register":
        from .processes.dataset_register import run

        return run
    if task_name == "preprocess":
        from .processes.preprocess import run

        return run
    if task_name == "train_model":
        from .processes.train_model import run

        return run
    if task_name == "leaderboard":
        from .processes.leaderboard import run

        return run
    if task_name == "infer":
        from .processes.infer import run

        return run
    if task_name == "pipeline":
        from .processes.pipeline import run

        return run

    raise ValueError(f"Unknown task.name: {task_name}")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Compose config and print it, then exit.",
    )
    args, overrides = parser.parse_known_args(argv)

    config_dir = _resolve_config_dir()
    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = compose(config_name="config", overrides=overrides)

    if args.print_config:
        print(OmegaConf.to_yaml(cfg))
        return

    task_name = getattr(cfg.task, "name", None)
    if not task_name:
        raise ValueError("cfg.task.name is required (e.g. task=preprocess).")

    runner = _select_runner(task_name)
    runner(cfg)


if __name__ == "__main__":
    main()
