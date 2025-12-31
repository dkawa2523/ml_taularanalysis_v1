"""pipeline process.

T009 で実装予定。
- dataset_register/preprocess/train/leaderboard/infer を独立タスクとして実行するための接着剤
- grid_run_id を生成し、各タスクへ伝播させる
- agent/clone 実行モードに対応（platform の execute_remotely/clone を利用）

重要：pipeline は実処理を実装しない（各独立タスクに委譲）。
"""

from __future__ import annotations

from typing import Any

from ..platform_adapter import init_task_context, save_config_resolved


def run(cfg: Any) -> None:
    ctx = init_task_context(cfg, stage=cfg.task.stage, task_name="pipeline")
    save_config_resolved(ctx, cfg)

    raise NotImplementedError(
        "pipeline is not implemented yet. Run Codex task T009 to implement it." 
    )
