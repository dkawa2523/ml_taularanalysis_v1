"""preprocess process.

T005 で実装予定。
- raw dataset から processed dataset を作る
- split を生成して固定（split_hash）
- preprocess bundle（transformers + schema）を保存

重要：train は split を再生成しない（比較可能性のため）。
"""

from __future__ import annotations

from typing import Any

from ..platform_adapter import init_task_context, save_config_resolved


def run(cfg: Any) -> None:
    ctx = init_task_context(cfg, stage=cfg.task.stage, task_name="preprocess")
    save_config_resolved(ctx, cfg)

    raise NotImplementedError(
        "preprocess is not implemented yet. Run Codex task T005 to implement it."
    )
