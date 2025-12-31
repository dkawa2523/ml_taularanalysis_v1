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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional


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


_CLEARML_TASK_CACHE: dict[str, Any] = {}


def _cfg_value(cfg: Any, dotted_path: str, default: Any | None = None) -> Any:
    if cfg is None:
        return default
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None:
        try:
            value = OmegaConf.select(cfg, dotted_path)
        except Exception:
            value = None
        if value is not None:
            return value
    current = cfg
    for key in dotted_path.split("."):
        if isinstance(current, Mapping):
            if key not in current:
                return default
            current = current[key]
            continue
        if not hasattr(current, key):
            return default
        current = getattr(current, key)
    return current


def _set_cfg_value(cfg: Any, dotted_path: str, value: Any) -> bool:
    if cfg is None:
        return False
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(cfg):
        try:
            was_struct = OmegaConf.is_struct(cfg)
        except Exception:
            was_struct = False
        if was_struct:
            try:
                OmegaConf.set_struct(cfg, False)
            except Exception:
                pass
        try:
            OmegaConf.update(cfg, dotted_path, value, merge=False)
            return True
        except Exception:
            return False
        finally:
            if was_struct:
                try:
                    OmegaConf.set_struct(cfg, True)
                except Exception:
                    pass
    current = cfg
    keys = dotted_path.split(".")
    for key in keys[:-1]:
        if isinstance(current, Mapping):
            if key not in current or not isinstance(current[key], Mapping):
                current[key] = {}
            current = current[key]
            continue
        if not hasattr(current, key) or getattr(current, key) is None:
            setattr(current, key, type("CfgNode", (), {})())
        current = getattr(current, key)
    last = keys[-1]
    if isinstance(current, Mapping):
        current[last] = value
        return True
    try:
        setattr(current, last, value)
        return True
    except Exception:
        return False


def _dedupe_tags(tags: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags:
        if tag is None:
            continue
        tag_str = str(tag).strip()
        if not tag_str or tag_str in seen:
            continue
        seen.add(tag_str)
        result.append(tag_str)
    return result


def _resolve_version_props(cfg: Any, *, clearml_enabled: bool) -> dict[str, str]:
    try:
        from ml_platform.versioning import (  # type: ignore
            get_code_version,
            get_platform_version,
            get_schema_version,
        )
    except Exception as exc:
        if clearml_enabled:
            raise PlatformAdapterError(
                "ml_platform.versioning is required for ClearML runs. "
                "Install/update ml_platform."
            ) from exc
        return {"code_version": "unknown", "platform_version": "unknown", "schema_version": "unknown"}
    schema_version = _cfg_value(cfg, "run.schema_version") or get_schema_version(cfg, default="unknown")
    return {
        "code_version": get_code_version(repo_root=Path.cwd()),
        "platform_version": get_platform_version(),
        "schema_version": str(schema_version),
    }


def _build_properties(
    cfg: Any,
    *,
    stage: str,
    task_name: str,
    extra: Optional[Mapping[str, Any]],
    clearml_enabled: bool,
) -> dict[str, Any]:
    usecase_id = _cfg_value(cfg, "run.usecase_id") or _cfg_value(cfg, "usecase_id") or "unknown"
    process = _cfg_value(cfg, "task.name") or task_name or stage or "unknown"
    versions = _resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    grid_run_id = _cfg_value(cfg, "run.grid_run_id")
    base: dict[str, Any] = {
        "usecase_id": usecase_id,
        "process": process,
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "grid_run_id": grid_run_id,
    }
    merged = dict(base)
    if extra:
        merged.update(dict(extra))
    for key, value in base.items():
        merged.setdefault(key, value)
    return merged


def _build_tags(
    cfg: Any,
    *,
    process: str,
    schema_version: str,
    grid_run_id: Any,
    extra_tags: Optional[Iterable[str]],
    tags: Optional[Iterable[str]],
) -> list[str]:
    usecase_id = _cfg_value(cfg, "run.usecase_id") or _cfg_value(cfg, "usecase_id") or "unknown"
    base = [
        f"usecase:{usecase_id}",
        f"process:{process}",
        f"schema:{schema_version}",
    ]
    if grid_run_id:
        base.append(f"grid:{grid_run_id}")
    return _dedupe_tags([*base, *(extra_tags or []), *(tags or [])])


def _ensure_clearml_names(cfg: Any, *, project_name: str, task_name: str, clearml_enabled: bool) -> None:
    if _cfg_value(cfg, "run.clearml.project_name") != project_name:
        _set_cfg_value(cfg, "run.clearml.project_name", project_name)
    if _cfg_value(cfg, "run.clearml.task_name") != task_name:
        _set_cfg_value(cfg, "run.clearml.task_name", task_name)
    if clearml_enabled:
        if _cfg_value(cfg, "run.clearml.project_name") != project_name:
            raise PlatformAdapterError("Failed to set run.clearml.project_name for ClearML init.")
        if _cfg_value(cfg, "run.clearml.task_name") != task_name:
            raise PlatformAdapterError("Failed to set run.clearml.task_name for ClearML init.")


def _load_clearml_module(clearml_enabled: bool):
    try:
        from ml_platform.integrations import clearml as platform_clearml  # type: ignore
    except Exception as exc:
        if clearml_enabled:
            raise PlatformAdapterError(
                "ml_platform.integrations.clearml is required for ClearML runs. "
                "Install/update ml_platform."
            ) from exc
        return None
    return platform_clearml


def _load_clearml_dataset(clearml_enabled: bool):
    try:
        from clearml import Dataset as ClearMLDataset  # type: ignore
    except Exception as exc:
        if clearml_enabled:
            raise PlatformAdapterError(
                "clearml.Dataset is required for ClearML dataset registration. "
                "Install/update clearml."
            ) from exc
        return None
    return ClearMLDataset


def _existing_user_properties(task: Any) -> dict[str, Any]:
    getter = getattr(task, "get_user_properties", None)
    if callable(getter):
        try:
            existing = getter()
        except Exception:
            existing = None
        if isinstance(existing, Mapping):
            return dict(existing)
    return {}


def hash_config(payload: Any) -> str:
    try:
        from ml_platform.artifacts import hash_config as platform_hash_config  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("ml_platform.artifacts.hash_config not available.") from exc
    return platform_hash_config(payload)


def hash_split(payload: Any) -> str:
    try:
        from ml_platform.artifacts import hash_split as platform_hash_split  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("ml_platform.artifacts.hash_split not available.") from exc
    return platform_hash_split(payload)


def hash_recipe(payload: Any) -> str:
    try:
        from ml_platform.artifacts import hash_recipe as platform_hash_recipe  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("ml_platform.artifacts.hash_recipe not available.") from exc
    return platform_hash_recipe(payload)


def is_clearml_enabled(cfg) -> bool:
    return bool(getattr(cfg.run.clearml, "enabled", False)) and str(
        getattr(cfg.run.clearml, "execution", "local")
    ) != "local"


def resolve_version_props(cfg: Any, *, clearml_enabled: Optional[bool] = None) -> dict[str, str]:
    if clearml_enabled is None:
        clearml_enabled = is_clearml_enabled(cfg)
    return _resolve_version_props(cfg, clearml_enabled=bool(clearml_enabled))


def resolve_output_dir(cfg, stage: str) -> Path:
    base = Path(getattr(cfg.run, "output_dir", "outputs"))
    return base / stage


def init_task_context(
    cfg,
    *,
    stage: str,
    task_name: str,
    tags: Optional[list[str]] = None,
    properties: Optional[dict] = None,
) -> TaskContext:
    """platform の task_factory を呼び出して Task を作る。

    - ClearML 無効の場合: task=None の TaskContext を返す
    - ClearML 有効の場合: platform の task_factory を呼び出す

    NOTE: platform 側 API パスが変わってもこの関数の中だけを直せばよい。
    """

    project_name = (
        _cfg_value(cfg, "run.clearml.project_name")
        or _cfg_value(cfg, "task.project_name")
        or f"MFG/{cfg.run.usecase_id}/{stage}"
    )
    task_name_value = _cfg_value(cfg, "run.clearml.task_name") or task_name
    output_dir = resolve_output_dir(cfg, stage)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not is_clearml_enabled(cfg):
        return TaskContext(
            task=None,
            project_name=str(project_name),
            task_name=str(task_name_value),
            output_dir=output_dir,
        )

    try:
        _ensure_clearml_names(
            cfg,
            project_name=str(project_name),
            task_name=str(task_name_value),
            clearml_enabled=True,
        )
        platform_clearml = _load_clearml_module(clearml_enabled=True)
        task_factory = getattr(platform_clearml, "task_factory", None)
        if task_factory is None:
            raise PlatformAdapterError("ml_platform.integrations.clearml.task_factory not found.")
        merged_props = _build_properties(
            cfg,
            stage=stage,
            task_name=str(task_name_value),
            extra=properties,
            clearml_enabled=True,
        )
        process = str(merged_props.get("process") or task_name_value or stage)
        merged_tags = _build_tags(
            cfg,
            process=process,
            schema_version=str(merged_props.get("schema_version") or "unknown"),
            grid_run_id=merged_props.get("grid_run_id"),
            extra_tags=_cfg_value(cfg, "run.clearml.extra_tags") or [],
            tags=tags,
        )
        task = task_factory(cfg, tags=merged_tags)
        setter = getattr(platform_clearml, "set_user_properties", None)
        if setter is None:
            raise PlatformAdapterError("ml_platform.integrations.clearml.set_user_properties not found.")
        existing = _existing_user_properties(task)
        merged_props = {**existing, **merged_props}
        setter(task, merged_props)
        return TaskContext(
            task=task,
            project_name=str(project_name),
            task_name=str(task_name_value),
            output_dir=output_dir,
        )
    except Exception as e:
        raise PlatformAdapterError(f"Failed to init ClearML task via ml-platform: {e}") from e


def save_config_resolved(ctx: TaskContext, cfg) -> Path:
    """Hydra の解決済み config を保存（platform に委譲できる場合は委譲）。"""
    if ctx.task is not None:
        try:
            from ml_platform.config import export_config_artifact  # type: ignore
        except Exception as exc:
            raise PlatformAdapterError(
                "ml_platform.config.export_config_artifact not available for ClearML runs."
            ) from exc
        try:
            return export_config_artifact(
                cfg,
                output_dir=ctx.output_dir,
                task=ctx.task,
                artifact_name="config_resolved.yaml",
            )
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to write config_resolved.yaml via ml_platform: {exc}") from exc
    path = ctx.output_dir / "config_resolved.yaml"
    try:
        from omegaconf import OmegaConf

        path.write_text(OmegaConf.to_yaml(cfg), encoding="utf-8")
    except Exception:
        path.write_text(str(cfg), encoding="utf-8")
    return path


def write_out_json(ctx: TaskContext, out: dict[str, Any]) -> Path:
    path = ctx.output_dir / "out.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if ctx.task is not None:
        platform_clearml = _load_clearml_module(clearml_enabled=True)
        uploader = getattr(platform_clearml, "upload_artifact", None)
        if uploader is None:
            raise PlatformAdapterError("ml_platform.integrations.clearml.upload_artifact not found.")
        try:
            uploader(ctx.task, "out.json", path)
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to upload out.json via ml_platform: {exc}") from exc
    return path


def upload_artifact(ctx: TaskContext, name: str, path: Path) -> None:
    """Upload an artifact to ClearML when enabled."""
    if ctx.task is None:
        return
    platform_clearml = _load_clearml_module(clearml_enabled=True)
    uploader = getattr(platform_clearml, "upload_artifact", None)
    if uploader is None:
        raise PlatformAdapterError("ml_platform.integrations.clearml.upload_artifact not found.")
    try:
        uploader(ctx.task, name, path)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to upload artifact {name} via ml_platform: {exc}") from exc


def update_task_properties(ctx: TaskContext, props: Mapping[str, Any]) -> None:
    """Merge and update task user properties (ClearML only)."""
    if ctx.task is None:
        return
    platform_clearml = _load_clearml_module(clearml_enabled=True)
    setter = getattr(platform_clearml, "set_user_properties", None)
    if setter is None:
        raise PlatformAdapterError("ml_platform.integrations.clearml.set_user_properties not found.")
    existing = _existing_user_properties(ctx.task)
    merged = {**existing, **dict(props)}
    try:
        setter(ctx.task, merged)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to update user properties via ml_platform: {exc}") from exc


def _get_clearml_task(task_id: str) -> Any:
    cached = _CLEARML_TASK_CACHE.get(task_id)
    if cached is not None:
        return cached
    try:
        from clearml import Task as ClearMLTask  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml is required for task artifact retrieval.") from exc
    try:
        task = ClearMLTask.get_task(task_id=str(task_id))
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to load ClearML task: {task_id}") from exc
    _CLEARML_TASK_CACHE[task_id] = task
    return task


def _resolve_task_artifact(task: Any, artifact_name: str) -> Any | None:
    artifacts = getattr(task, "artifacts", None)
    if isinstance(artifacts, Mapping):
        if artifact_name in artifacts:
            return artifacts[artifact_name]
    elif artifacts is not None and not isinstance(artifacts, (str, bytes)):
        try:
            for item in artifacts:
                if isinstance(item, Mapping):
                    key = item.get("key") or item.get("name")
                    if key == artifact_name:
                        return item
                else:
                    key = getattr(item, "key", None) or getattr(item, "name", None)
                    if key == artifact_name:
                        return item
        except Exception:
            pass
    getter = getattr(task, "get_artifact", None)
    if callable(getter):
        try:
            return getter(artifact_name)
        except Exception:
            return None
    return None


def _artifact_local_copy(artifact: Any) -> str | None:
    if artifact is None:
        return None
    if isinstance(artifact, Path):
        return str(artifact)
    if isinstance(artifact, str):
        return artifact
    getter = getattr(artifact, "get_local_copy", None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            return None
    if isinstance(artifact, Mapping):
        for key in ("local_copy", "local_path", "path", "artifact_local_path"):
            value = artifact.get(key)
            if value:
                return str(value)
    return None


def get_task_artifact_local_copy(cfg: Any, task_id: str, artifact_name: str) -> Path:
    if not is_clearml_enabled(cfg):
        raise PlatformAdapterError("ClearML is disabled; cannot fetch task artifacts.")
    task = _get_clearml_task(task_id)
    artifact = _resolve_task_artifact(task, artifact_name)
    local_path = _artifact_local_copy(artifact)
    if not local_path:
        raise PlatformAdapterError(
            f"Artifact {artifact_name} not found on ClearML task {task_id}."
        )
    path = Path(local_path)
    if not path.exists():
        raise PlatformAdapterError(
            f"Artifact {artifact_name} local copy does not exist: {path}"
        )
    return path


def write_manifest(ctx: TaskContext, manifest: dict[str, Any]) -> Path:
    """manifest.json を保存。

    本来は platform の manifest builder（P201〜P204）を使うべき。
    ここは Codex が platform 実装に合わせて置き換える。
    """
    try:
        from ml_platform.artifacts import write_manifest as platform_write_manifest  # type: ignore
    except Exception as exc:
        if ctx.task is not None:
            raise PlatformAdapterError("ml_platform.artifacts.write_manifest not available.") from exc
        platform_write_manifest = None
    if platform_write_manifest is not None:
        try:
            return platform_write_manifest(
                manifest,
                output_dir=ctx.output_dir,
                task=ctx.task,
                filename="manifest.json",
            )
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to write manifest via ml_platform: {exc}") from exc
    path = ctx.output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def register_dataset(
    cfg: Any,
    *,
    dataset_path: Path,
    dataset_name: str,
    dataset_project: str | None = None,
    dataset_tags: Optional[Iterable[str]] = None,
    dataset_version: str | None = None,
    description: str | None = None,
) -> str:
    if not is_clearml_enabled(cfg):
        raise PlatformAdapterError("ClearML is disabled; cannot register dataset.")
    ClearMLDataset = _load_clearml_dataset(clearml_enabled=True)
    try:
        dataset = ClearMLDataset.create(
            dataset_name=dataset_name,
            dataset_project=dataset_project,
            dataset_tags=list(dataset_tags) if dataset_tags else None,
            dataset_version=dataset_version,
            description=description,
        )
        dataset.add_files(path=str(dataset_path))
        dataset.upload()
        dataset.finalize()
        return str(dataset.id)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to register dataset via ClearML: {exc}") from exc


def get_dataset_local_copy(cfg: Any, dataset_id: str) -> Path:
    if not is_clearml_enabled(cfg):
        raise PlatformAdapterError("ClearML is disabled; cannot fetch dataset.")
    ClearMLDataset = _load_clearml_dataset(clearml_enabled=True)
    try:
        dataset = ClearMLDataset.get(dataset_id=str(dataset_id))
        local_path = dataset.get_local_copy()
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to fetch dataset via ClearML: {exc}") from exc
    if not local_path:
        raise PlatformAdapterError("ClearML Dataset.get_local_copy returned an empty path.")
    return Path(local_path)


def _load_clearml_pipeline_utils(clearml_enabled: bool):
    try:
        from ml_platform.integrations.clearml import pipeline_utils as platform_pipeline_utils  # type: ignore
    except Exception as exc:
        if clearml_enabled:
            raise PlatformAdapterError(
                "ml_platform.integrations.clearml.pipeline_utils not available for ClearML runs."
            ) from exc
        return None
    return platform_pipeline_utils


def create_pipeline_controller(
    cfg: Any,
    *,
    name: str | None = None,
    tags: Iterable[str] | None = None,
    default_queue: str | None = None,
) -> Any:
    pipeline_utils = _load_clearml_pipeline_utils(clearml_enabled=True)
    if pipeline_utils is None:
        raise PlatformAdapterError("pipeline_utils is not available.")
    return pipeline_utils.create_controller(
        cfg,
        name=name,
        tags=tags,
        default_queue=default_queue,
    )


def pipeline_require_clearml_agent(queue_name: str | None = None) -> None:
    pipeline_utils = _load_clearml_pipeline_utils(clearml_enabled=True)
    if pipeline_utils is None:
        raise PlatformAdapterError("pipeline_utils is not available.")
    pipeline_utils.require_clearml_agent(queue_name)


def pipeline_step_task_id_ref(step_name: str) -> str:
    pipeline_utils = _load_clearml_pipeline_utils(clearml_enabled=True)
    if pipeline_utils is None:
        raise PlatformAdapterError("pipeline_utils is not available.")
    return pipeline_utils.step_task_id_ref(step_name)
