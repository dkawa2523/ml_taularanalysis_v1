"""infer process.

T008 で実装予定。
- model_bundle を読み込み、single/batch/optimize のいずれかのモードで推論
- target transform がある場合は逆変換して出力
"""

from __future__ import annotations

from typing import Any

from ..platform_adapter import init_task_context, save_config_resolved


def run(cfg: Any) -> None:
    ctx = init_task_context(cfg, stage=cfg.task.stage, task_name="infer")
    save_config_resolved(ctx, cfg)

    raise NotImplementedError(
        "infer is not implemented yet. Run Codex task T008 to implement it."
    )
