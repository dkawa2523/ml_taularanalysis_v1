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

from datetime import datetime, timezone
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


def _normalize_requirement_lines(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        items: Iterable[Any] = values.splitlines()
    elif isinstance(values, Iterable) and not isinstance(values, Mapping):
        items = values
    else:
        items = [values]
    normalized: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        if text.lstrip().startswith("#"):
            continue
        normalized.append(text)
    return normalized


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
    retrain_run_id = _cfg_value(cfg, "run.retrain_run_id")
    base: dict[str, Any] = {
        "usecase_id": usecase_id,
        "process": process,
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "grid_run_id": grid_run_id,
    }
    if retrain_run_id:
        base["retrain_run_id"] = retrain_run_id
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
    retrain_run_id: Any,
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
    if retrain_run_id:
        base.append(f"retrain:{retrain_run_id}")
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


def _capture_env_snapshot(ctx: TaskContext) -> None:
    try:
        from .ops.env_snapshot import capture_env_snapshot
    except Exception as exc:
        raise PlatformAdapterError("tabular_analysis.ops.env_snapshot is not available.") from exc
    try:
        env_path, freeze_path = capture_env_snapshot(ctx.output_dir)
        upload_artifact(ctx, env_path.name, env_path)
        upload_artifact(ctx, freeze_path.name, freeze_path)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to capture env snapshot: {exc}") from exc


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

    project_root = _cfg_value(cfg, "run.clearml.project_root") or "MFG"
    usecase_id = _cfg_value(cfg, "run.usecase_id") or "unknown"
    project_name = (
        _cfg_value(cfg, "run.clearml.project_name")
        or _cfg_value(cfg, "task.project_name")
        or f"{project_root}/TabularAnalysis/{usecase_id}/{stage}"
    )
    task_name_value = _cfg_value(cfg, "run.clearml.task_name") or task_name
    output_dir = resolve_output_dir(cfg, stage)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not is_clearml_enabled(cfg):
        ctx = TaskContext(
            task=None,
            project_name=str(project_name),
            task_name=str(task_name_value),
            output_dir=output_dir,
        )
        _capture_env_snapshot(ctx)
        return ctx

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
            retrain_run_id=merged_props.get("retrain_run_id"),
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
        ctx = TaskContext(
            task=task,
            project_name=str(project_name),
            task_name=str(task_name_value),
            output_dir=output_dir,
        )
    except Exception as e:
        raise PlatformAdapterError(f"Failed to init ClearML task via ml-platform: {e}") from e
    _capture_env_snapshot(ctx)
    return ctx


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


def connect_hyperparameters(ctx: TaskContext, hparams: Mapping[str, Any]) -> None:
    """Connect minimal HyperParameters to ClearML task."""
    if ctx.task is None:
        return
    connector = getattr(ctx.task, "connect", None)
    if not callable(connector):
        raise PlatformAdapterError("ClearML Task.connect is not available.")
    try:
        connector(dict(hparams))
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to connect HyperParameters via ClearML: {exc}") from exc


def connect_configuration(ctx: TaskContext, config: Mapping[str, Any], *, name: str = "effective") -> None:
    """Attach a minimal configuration snapshot to ClearML task."""
    if ctx.task is None:
        return
    connector = getattr(ctx.task, "connect_configuration", None)
    if not callable(connector):
        raise PlatformAdapterError("ClearML Task.connect_configuration is not available.")
    try:
        connector(dict(config), name=name)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to connect configuration via ClearML: {exc}") from exc


def report_markdown(ctx: TaskContext, *, title: str, markdown: str) -> bool:
    """Publish markdown text to ClearML when reporting is available."""
    if ctx.task is None:
        return False
    if not markdown:
        return False
    getter = getattr(ctx.task, "get_logger", None)
    if not callable(getter):
        return False
    try:
        logger = getter()
    except Exception:
        return False
    if logger is None:
        return False
    reporter = getattr(logger, "report_text", None)
    if not callable(reporter):
        return False
    try:
        payload = markdown.strip()
        if title:
            payload = f"# {title}\n\n{payload}"
        reporter(payload, print_console=False)
        return True
    except Exception:
        return False


def add_task_tags(ctx: TaskContext, tags: Iterable[str]) -> None:
    """Add tags to a ClearML task when enabled."""
    if ctx.task is None:
        return
    tag_list = _dedupe_tags(tags)
    if not tag_list:
        return
    task = ctx.task
    adder = getattr(task, "add_tags", None)
    if callable(adder):
        try:
            adder(tag_list)
            return
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to add task tags via ClearML: {exc}") from exc
    getter = getattr(task, "get_tags", None)
    setter = getattr(task, "set_tags", None)
    if callable(setter):
        existing: list[str] = []
        if callable(getter):
            try:
                current = getter() or []
                if isinstance(current, (str, bytes)):
                    existing = [str(current)]
                elif isinstance(current, Iterable):
                    existing = [str(item) for item in current]
            except Exception:
                existing = []
        merged = _dedupe_tags([*existing, *tag_list])
        try:
            setter(merged)
            return
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to set task tags via ClearML: {exc}") from exc
    raise PlatformAdapterError("ClearML task does not support tag updates.")


def register_promoted_model(
    ctx: TaskContext,
    *,
    model_path: Path,
    model_name: str,
    tags: Iterable[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    comment: str | None = None,
    framework: str | None = None,
) -> str:
    """Register a model artifact in ClearML model registry and tag it."""
    if ctx.task is None:
        raise PlatformAdapterError("ClearML is disabled; cannot register model.")
    try:
        from clearml import OutputModel  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml.OutputModel is required for model promotion.") from exc

    model_path = Path(model_path).expanduser().resolve()
    if not model_path.exists():
        raise PlatformAdapterError(f"Model file does not exist: {model_path}")

    try:
        output_model = OutputModel(
            task=ctx.task,
            name=str(model_name),
            tags=_dedupe_tags(tags or []),
            comment=comment,
            framework=framework,
        )
        output_model.update_weights(
            weights_filename=str(model_path),
            auto_delete_file=False,
            async_enable=False,
        )
        if metadata:
            for key, value in metadata.items():
                if value is None:
                    continue
                if isinstance(value, (dict, list, tuple)):
                    text = json.dumps(value, ensure_ascii=True)
                else:
                    text = str(value)
                if not text:
                    continue
                output_model.set_metadata(str(key), text)
        return str(output_model.id)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to register model via ClearML: {exc}") from exc


def get_clearml_model_local_copy(model_id: str) -> Path:
    """Download a ClearML registry model artifact and return the local path."""
    try:
        from clearml import Model  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml.Model is required for registry model downloads.") from exc
    try:
        model = Model(model_id=str(model_id))
        local_path = model.get_local_copy(raise_on_error=True)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to download ClearML model {model_id}: {exc}") from exc
    if not local_path:
        raise PlatformAdapterError(f"ClearML model {model_id} did not return a local copy path.")
    path = Path(local_path)
    if not path.exists():
        raise PlatformAdapterError(f"ClearML model local copy does not exist: {path}")
    return path.resolve()


def resolve_registry_model_bundle_by_stage(
    *,
    stage: str,
    usecase_id: str | None = None,
) -> tuple[str, Path]:
    """Resolve a ClearML registry model bundle by stage tags."""
    try:
        from clearml import Model  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml.Model is required for registry queries.") from exc
    tags = ["__$all", f"stage:{stage}"]
    if usecase_id:
        tags.append(f"usecase:{usecase_id}")
    try:
        models = Model.query_models(
            tags=tags,
            only_published=False,
            include_archived=True,
            max_results=1,
        )
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to query ClearML registry for stage {stage}: {exc}") from exc
    if not models:
        suffix = f" usecase={usecase_id}" if usecase_id else ""
        raise PlatformAdapterError(
            f"No ClearML registry model found for stage={stage}.{suffix}"
        )
    model = models[0]
    model_id = getattr(model, "id", None) or getattr(model, "model_id", None)
    model_id_str = str(model_id) if model_id is not None else "unknown"
    try:
        local_path = model.get_local_copy(raise_on_error=True)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to download ClearML model {model_id_str}: {exc}") from exc
    if not local_path:
        raise PlatformAdapterError(
            f"ClearML model {model_id_str} did not return a local copy path."
        )
    path = Path(local_path)
    if not path.exists():
        raise PlatformAdapterError(f"ClearML model local copy does not exist: {path}")
    return model_id_str, path.resolve()


def _model_tags(model: Any) -> list[str]:
    tags = getattr(model, "tags", None)
    if tags is None:
        return []
    if isinstance(tags, (str, bytes)):
        return [str(tags)]
    try:
        return [str(item) for item in tags]
    except Exception:
        return []


def _set_model_tags(model: Any, tags: Iterable[str]) -> None:
    try:
        model.tags = list(tags)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to update model tags via ClearML: {exc}") from exc


def _update_model_metadata(model: Any, metadata: Mapping[str, Any]) -> None:
    setter = getattr(model, "set_metadata", None)
    if not callable(setter):
        return
    for key, value in metadata.items():
        if value is None:
            continue
        try:
            setter(str(key), str(value))
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to update model metadata via ClearML: {exc}") from exc


def _model_snapshot(model: Any | None) -> dict[str, Any] | None:
    if model is None:
        return None
    return {
        "registry_model_id": getattr(model, "id", None),
        "name": getattr(model, "name", None),
        "tags": _model_tags(model),
    }


def rollback_registry_stage(
    *,
    usecase_id: str,
    stage: str,
    target_model_id: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Rollback ClearML model registry stage to previous production (best-effort)."""
    try:
        from clearml import Model  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml.Model is required for model registry rollback.") from exc

    tags = ["__$all", f"usecase:{usecase_id}", f"stage:{stage}"]
    models = Model.query_models(
        tags=tags,
        only_published=False,
        include_archived=True,
        max_results=20,
    )
    current = models[0] if models else None
    target = None
    if target_model_id:
        target = Model(model_id=str(target_model_id))
    elif len(models) > 1:
        target = models[1]

    if target is None:
        raise PlatformAdapterError("No previous model found for rollback.")

    target_tags = _dedupe_tags(
        [*_model_tags(target), f"usecase:{usecase_id}", f"stage:{stage}", "rollback:true"]
    )
    _set_model_tags(target, target_tags)
    _update_model_metadata(
        target,
        {
            "promotion_stage": stage,
            "rollback_reason": reason,
            "rollback_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )

    if current is not None and getattr(current, "id", None) != getattr(target, "id", None):
        current_tags = [tag for tag in _model_tags(current) if tag != f"stage:{stage}"]
        _set_model_tags(current, _dedupe_tags(current_tags))

    return {"before": _model_snapshot(current), "after": _model_snapshot(target)}


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


def clearml_task_exists(task_id: str) -> bool:
    _get_clearml_task(task_id)
    return True


def create_clearml_task(
    *,
    project_name: str,
    task_name: str,
    module: str | None = None,
    script: str | None = None,
    args: Iterable[str] | None = None,
    repo: str | None = None,
    branch: str | None = None,
    working_dir: str | None = None,
    task_type: str | None = None,
    tags: Iterable[str] | None = None,
    properties: Mapping[str, Any] | None = None,
    requirements: Iterable[str] | None = None,
) -> str:
    if module and script:
        raise PlatformAdapterError("Specify either module or script for ClearML task creation.")
    try:
        from clearml import Task as ClearMLTask  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml is required to create ClearML tasks.") from exc
    try:
        task = ClearMLTask.create(
            project_name=str(project_name),
            task_name=str(task_name),
            task_type=task_type,
            repo=repo,
            branch=branch,
            script=script,
            working_directory=working_dir,
            module=module,
            argparse_args=list(args) if args else None,
        )
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to create ClearML task: {exc}") from exc
    if tags:
        tag_list = _dedupe_tags(tags)
        if tag_list:
            try:
                task.add_tags(tag_list)
            except Exception as exc:
                raise PlatformAdapterError(f"Failed to set task tags via ClearML: {exc}") from exc
    if properties:
        setter = getattr(task, "set_user_properties", None)
        if callable(setter):
            normalized = {str(key): "" if value is None else str(value) for key, value in properties.items()}
            try:
                setter(*normalized.items())
            except Exception as exc:
                raise PlatformAdapterError(f"Failed to set task properties via ClearML: {exc}") from exc
    if requirements:
        setter = getattr(task, "set_packages", None)
        if not callable(setter):
            raise PlatformAdapterError("ClearML Task.set_packages is not available.")
        normalized = _normalize_requirement_lines(requirements)
        if normalized:
            try:
                setter(normalized)
            except Exception as exc:
                raise PlatformAdapterError(f"Failed to set task requirements via ClearML: {exc}") from exc
    task_id = getattr(task, "id", None)
    if not task_id:
        raise PlatformAdapterError("ClearML task id is missing after creation.")
    return str(task_id)


def find_clearml_task_id_by_tags(
    tags: Iterable[str],
    *,
    project_name: str | None = None,
    task_name: str | None = None,
    allow_archived: bool = True,
) -> str | None:
    """Resolve the most recently updated ClearML task id matching tags."""
    try:
        from clearml import Task as ClearMLTask  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml is required for ClearML task queries.") from exc
    tag_list = _dedupe_tags(tags)
    if not tag_list:
        raise PlatformAdapterError("tags are required to query ClearML tasks.")
    try:
        tasks = ClearMLTask.get_tasks(
            project_name=project_name,
            task_name=task_name,
            tags=tag_list,
            allow_archived=allow_archived,
            task_filter={"order_by": ["-last_update"]},
        )
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to query ClearML tasks by tags: {exc}") from exc
    if not tasks:
        return None
    task = tasks[0]
    task_id = getattr(task, "id", None) or getattr(task, "task_id", None)
    return str(task_id) if task_id else None


def _task_tags(task: Any) -> list[str]:
    getter = getattr(task, "get_tags", None)
    if callable(getter):
        try:
            tags = getter()
        except Exception:
            tags = None
        if tags is not None:
            if isinstance(tags, (list, tuple, set)):
                return [str(tag) for tag in tags if tag is not None]
            return [str(tags)]
    tags = getattr(task, "tags", None)
    if tags is not None:
        if isinstance(tags, (list, tuple, set)):
            return [str(tag) for tag in tags if tag is not None]
        return [str(tags)]
    data = getattr(task, "data", None)
    if isinstance(data, Mapping):
        tags = data.get("tags")
        if isinstance(tags, (list, tuple, set)):
            return [str(tag) for tag in tags if tag is not None]
    if data is not None:
        tags = getattr(data, "tags", None)
        if isinstance(tags, (list, tuple, set)):
            return [str(tag) for tag in tags if tag is not None]
    return []


def _task_script(task: Any) -> dict[str, Any]:
    getter = getattr(task, "get_script", None)
    if callable(getter):
        try:
            script = getter()
        except Exception:
            script = None
        if isinstance(script, Mapping):
            return dict(script)
    data = getattr(task, "data", None)
    script_obj = getattr(data, "script", None) if data is not None else None
    if script_obj is not None:
        return {
            "repository": getattr(script_obj, "repository", None),
            "branch": getattr(script_obj, "branch", None),
            "entry_point": getattr(script_obj, "entry_point", None),
            "working_dir": getattr(script_obj, "working_dir", None),
        }
    return {}


def _task_parameters(task: Any) -> dict[str, Any]:
    getter = getattr(task, "get_parameters", None)
    if callable(getter):
        try:
            params = getter()
        except Exception:
            params = None
        if isinstance(params, Mapping):
            return dict(params)
    getter = getattr(task, "get_parameters_as_dict", None)
    if callable(getter):
        try:
            params = getter()
        except Exception:
            params = None
        if isinstance(params, Mapping):
            flat: dict[str, Any] = {}
            for section, values in params.items():
                if not isinstance(values, Mapping):
                    continue
                for key, value in values.items():
                    flat[f"{section}/{key}"] = value
            return flat
    return {}


def _property_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        if "value" in value:
            return value.get("value")
    return value


def _parse_task_args(args: Iterable[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in args:
        text = str(item).strip()
        if not text:
            continue
        if "=" not in text:
            raise PlatformAdapterError(f"override must be key=value: {text}")
        key, value = text.split("=", 1)
        parsed[str(key)] = str(value)
    return parsed


def get_clearml_task_tags(task_id: str) -> list[str]:
    task = _get_clearml_task(task_id)
    return _dedupe_tags(_task_tags(task))


def get_clearml_task_script(task_id: str) -> dict[str, Any]:
    task = _get_clearml_task(task_id)
    script = _task_script(task)
    return {
        "repository": script.get("repository"),
        "branch": script.get("branch"),
        "entry_point": script.get("entry_point"),
        "working_dir": script.get("working_dir"),
    }


def get_clearml_task_args(task_id: str) -> dict[str, str]:
    task = _get_clearml_task(task_id)
    params = _task_parameters(task)
    args: dict[str, str] = {}
    for key, value in params.items():
        if not isinstance(key, str) or not key.startswith("Args/"):
            continue
        args[key[5:]] = "" if value is None else str(value)
    return args


def ensure_clearml_task_tags(task_id: str, tags: Iterable[str]) -> bool:
    desired = _dedupe_tags(tags)
    if not desired:
        return False
    task = _get_clearml_task(task_id)
    existing = set(_task_tags(task))
    missing = [tag for tag in desired if tag not in existing]
    if not missing:
        return False
    adder = getattr(task, "add_tags", None)
    if not callable(adder):
        raise PlatformAdapterError("ClearML Task.add_tags is not available.")
    adder(missing)
    return True


def ensure_clearml_task_requirements(task_id: str, requirements: Iterable[str]) -> bool:
    desired = _normalize_requirement_lines(requirements)
    if not desired:
        return False
    task = _get_clearml_task(task_id)
    getter = getattr(task, "get_requirements", None)
    if not callable(getter):
        raise PlatformAdapterError("ClearML Task.get_requirements is not available.")
    try:
        existing = getter()
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to read task requirements via ClearML: {exc}") from exc
    existing_pip = existing.get("pip") if isinstance(existing, Mapping) else None
    if _normalize_requirement_lines(existing_pip) == desired:
        return False
    setter = getattr(task, "set_packages", None)
    if not callable(setter):
        raise PlatformAdapterError("ClearML Task.set_packages is not available.")
    try:
        setter(desired)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to set task requirements via ClearML: {exc}") from exc
    return True


def ensure_clearml_task_properties(task_id: str, properties: Mapping[str, Any]) -> bool:
    if not properties:
        return False
    task = _get_clearml_task(task_id)
    existing = _existing_user_properties(task)
    updates: dict[str, Any] = {}
    for key, value in properties.items():
        expected = "" if value is None else str(value)
        current = _property_value(existing.get(str(key)))
        if current is None or str(current) != expected:
            updates[str(key)] = expected
    if not updates:
        return False
    setter = getattr(task, "set_user_properties", None)
    if not callable(setter):
        raise PlatformAdapterError("ClearML Task.set_user_properties is not available.")
    setter(*updates.items())
    return True


def ensure_clearml_task_args(task_id: str, args: Iterable[str]) -> bool:
    desired = _parse_task_args(args)
    if not desired:
        return False
    task = _get_clearml_task(task_id)
    params = _task_parameters(task)
    existing_args: dict[str, str] = {}
    for key, value in params.items():
        if isinstance(key, str) and key.startswith("Args/"):
            existing_args[key[5:]] = "" if value is None else str(value)
    updates: dict[str, str] = {}
    for key, value in desired.items():
        if existing_args.get(key) != value:
            updates[key] = value
    if not updates:
        return False
    updated_params = dict(params)
    for key, value in updates.items():
        updated_params[f"Args/{key}"] = value
    setter = getattr(task, "set_parameters", None)
    if callable(setter):
        setter(updated_params)
        return True
    setter = getattr(task, "set_parameters_as_dict", None)
    if callable(setter):
        merged = {**existing_args, **updates}
        setter({"Args": merged})
        return True
    raise PlatformAdapterError("ClearML Task.set_parameters is not available.")


def ensure_clearml_task_script(
    task_id: str,
    *,
    repo: str | None,
    branch: str | None,
    entry_point: str | None,
    working_dir: str | None,
) -> bool:
    if repo is None and branch is None and entry_point is None and working_dir is None:
        return False
    task = _get_clearml_task(task_id)
    current = _task_script(task)
    changed = False
    if repo is not None and str(current.get("repository") or "") != str(repo):
        changed = True
    if branch is not None and str(current.get("branch") or "") != str(branch):
        changed = True
    if entry_point is not None and str(current.get("entry_point") or "") != str(entry_point):
        changed = True
    if working_dir is not None and str(current.get("working_dir") or "") != str(working_dir):
        changed = True
    if not changed:
        return False
    setter = getattr(task, "set_script", None)
    if not callable(setter):
        raise PlatformAdapterError("ClearML Task.set_script is not available.")
    setter(
        repository=repo,
        branch=branch,
        working_dir=working_dir,
        entry_point=entry_point,
    )
    return True


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


def resolve_clearml_task_url(cfg: Any, task_id: str) -> str | None:
    """Resolve a ClearML task URL when possible; returns None when unavailable."""
    if not is_clearml_enabled(cfg) or not task_id:
        return None
    try:
        task = _get_clearml_task(task_id)
    except Exception:
        return None
    for getter_name in ("get_output_log_web_page", "get_task_output_log_web_page"):
        getter = getattr(task, getter_name, None)
        if callable(getter):
            try:
                url = getter()
            except Exception:
                url = None
            if url:
                return str(url)
    url = getattr(task, "output_log_web_page", None)
    if url:
        return str(url)
    return None


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
    parent_dataset_ids: Optional[Iterable[str]] = None,
) -> str:
    if not is_clearml_enabled(cfg):
        raise PlatformAdapterError("ClearML is disabled; cannot register dataset.")
    ClearMLDataset = _load_clearml_dataset(clearml_enabled=True)
    try:
        parents = [str(parent) for parent in (parent_dataset_ids or []) if parent]
        dataset = ClearMLDataset.create(
            dataset_name=dataset_name,
            dataset_project=dataset_project,
            dataset_tags=list(dataset_tags) if dataset_tags else None,
            dataset_version=dataset_version,
            description=description,
            parent_datasets=parents or None,
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


def get_dataset_info(cfg: Any, dataset_id: str) -> dict[str, Any]:
    if not is_clearml_enabled(cfg):
        raise PlatformAdapterError("ClearML is disabled; cannot fetch dataset info.")
    ClearMLDataset = _load_clearml_dataset(clearml_enabled=True)
    try:
        dataset = ClearMLDataset.get(dataset_id=str(dataset_id))
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to fetch dataset info via ClearML: {exc}") from exc
    info: dict[str, Any] = {"dataset_id": str(getattr(dataset, "id", dataset_id))}
    version = getattr(dataset, "version", None)
    if version is None:
        version = getattr(dataset, "dataset_version", None)
    if version is not None:
        info["dataset_version"] = str(version)
    name = getattr(dataset, "name", None)
    if name:
        info["dataset_name"] = str(name)
    project = getattr(dataset, "project", None)
    if project:
        info["dataset_project"] = str(project)
    return info


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
