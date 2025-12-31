"""train_model process.

T006 で実装予定。
- processed dataset + fixed split を入力
- model_variant を選択して学習
- model_bundle（model + preprocess bundle + schema）を保存
- primary_metric を計算し、properties に best_score を入れる
"""

from __future__ import annotations

from typing import Any

from ..platform_adapter import init_task_context, save_config_resolved


def run(cfg: Any) -> None:
    ctx = init_task_context(cfg, stage=cfg.task.stage, task_name="train_model")
    save_config_resolved(ctx, cfg)

    raise NotImplementedError(
        "train_model is not implemented yet. Run Codex task T006 to implement it."
    )
