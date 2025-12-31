"""leaderboard process.

T007 で実装予定。
- 複数 train_task を集計して leaderboard.csv を作る
- split_hash / processed_dataset_id が一致しないものは除外（require_comparable=true の場合）
- recommendation.json を出力（推奨モデル）
"""

from __future__ import annotations

from typing import Any

from ..platform_adapter import init_task_context, save_config_resolved


def run(cfg: Any) -> None:
    ctx = init_task_context(cfg, stage=cfg.task.stage, task_name="leaderboard")
    save_config_resolved(ctx, cfg)

    raise NotImplementedError(
        "leaderboard is not implemented yet. Run Codex task T007 to implement it." 
    )
