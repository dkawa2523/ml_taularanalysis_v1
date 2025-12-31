"""ml-platform との接続面（Adapter）。

この Solution Repo は dkawa2523/ml_platform_v1（P201〜P204 反映済み）を前提とします。

ただし、platform 側の実装詳細（モジュールパスや関数名）は将来変わり得るため、
Solution 側は **この adapter を唯一の依存点**にしておくことで影響範囲を最小化します。

Codex タスクでは、まずこの adapter を platform 実装に合わせて完成させ、
以降の各プロセス（dataset_register/preprocess/train/...）は adapter だけを呼ぶようにします。

期待する platform 能力（P201〜P204 相当）:
- ClearML Task 初期化（project/name/tags/properties の統一）
- config_resolved.yaml の保存
- out.json / manifest.json の生成（hashes: config_hash/split_hash/recipe_hash など）
- （できれば）contract lint / doctor
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class TaskContext:
    """実行コンテキスト（ClearML Task など）。

    clearml が無効（local 実行）の場合は task=None になります。
    """

    task: Any | None
    project_name: str
    task_name: str
    output_dir: Path


class PlatformAdapterError(RuntimeError):
    pass


def is_clearml_enabled(cfg) -> bool:
    return bool(getattr(cfg.run.clearml, "enabled", False)) and str(
        getattr(cfg.run.clearml, "execution", "local")
    ) != "local"


def resolve_output_dir(cfg, stage: str) -> Path:
    base = Path(getattr(cfg.run, "output_dir", "outputs"))
    return base / stage


def init_task_context(cfg, *, stage: str, task_name: str, tags: Optional[list[str]] = None, properties: Optional[dict] = None) -> TaskContext:
    """platform の init_task を呼び出して Task を作る。

    - ClearML 無効の場合: task=None の TaskContext を返す
    - ClearML 有効の場合: platform の init_task を探して呼び出す

    NOTE: platform 側 API パスが変わってもこの関数の中だけを直せばよい。
    """

    project_name = str(getattr(cfg.task, "project_name", "")) or f"MFG/{cfg.run.usecase_id}/{stage}"
    output_dir = resolve_output_dir(cfg, stage)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not is_clearml_enabled(cfg):
        return TaskContext(task=None, project_name=project_name, task_name=task_name, output_dir=output_dir)

    # --- platform API を探索して呼ぶ（P201〜P204 の実装に合わせて Codex が調整する）
    try:
        from importlib import import_module

        candidates = [
            ("ml_platform.utils", "init_task"),
            ("ml_platform.clearml.task_factory", "init_task"),
            ("ml_platform.integrations.clearml.task_factory", "init_task"),
        ]
        init_fn = None
        for mod_name, fn_name in candidates:
            try:
                mod = import_module(mod_name)
                if hasattr(mod, fn_name):
                    init_fn = getattr(mod, fn_name)
                    break
            except Exception:
                continue
        if init_fn is None:
            raise PlatformAdapterError(
                "ml-platform の init_task が見つかりません。platform_adapter.py の candidates を更新してください。"
            )

        task = init_fn(
            project_name=project_name,
            task_name=task_name,
            tags=tags or [],
            properties=properties or {},
            cfg=cfg,
            output_dir=str(output_dir),
        )
        return TaskContext(task=task, project_name=project_name, task_name=task_name, output_dir=output_dir)
    except Exception as e:
        raise PlatformAdapterError(f"Failed to init ClearML task via ml-platform: {e}") from e


def save_config_resolved(ctx: TaskContext, cfg) -> Path:
    """Hydra の解決済み config を保存（platform に委譲できる場合は委譲）。"""
    path = ctx.output_dir / "config_resolved.yaml"
    try:
        from omegaconf import OmegaConf

        path.write_text(OmegaConf.to_yaml(cfg), encoding="utf-8")
    except Exception:
        # 最低限の保険
        path.write_text(str(cfg), encoding="utf-8")
    if ctx.task is not None:
        try:
            ctx.task.upload_artifact("config_resolved.yaml", artifact_object=str(path))
        except Exception:
            pass
    return path


def write_out_json(ctx: TaskContext, out: Dict[str, Any]) -> Path:
    path = ctx.output_dir / "out.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if ctx.task is not None:
        try:
            ctx.task.upload_artifact("out.json", artifact_object=str(path))
        except Exception:
            pass
    return path


def write_manifest(ctx: TaskContext, manifest: Dict[str, Any]) -> Path:
    """manifest.json を保存。

    本来は platform の manifest builder（P201〜P204）を使うべき。
    ここは Codex が platform 実装に合わせて置き換える。
    """

    path = ctx.output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if ctx.task is not None:
        try:
            ctx.task.upload_artifact("manifest.json", artifact_object=str(path))
        except Exception:
            pass
    return path
