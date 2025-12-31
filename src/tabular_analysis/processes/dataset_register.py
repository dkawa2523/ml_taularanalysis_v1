"""dataset_register process.

T004 で実装予定。
"""

from __future__ import annotations

from typing import Any

from ..platform_adapter import init_task_context, save_config_resolved, write_manifest, write_out_json


def run(cfg: Any) -> None:
    ctx = init_task_context(cfg, stage=cfg.task.stage, task_name="dataset_register")
    save_config_resolved(ctx, cfg)

    raise NotImplementedError(
        "dataset_register is not implemented yet. Run Codex task T004 to implement it."
    )
