"""ClearML identity resolution (project/usecase/tags/properties)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping


@dataclass
class ClearMLIdentity:
    project_root: str
    usecase_id: str
    tags: list[str]
    user_properties: dict[str, Any]


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


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _sanitize_identifier(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "-", value)
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    return sanitized.strip("-_") or "unknown"


def _resolve_repo_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for base in candidates:
        for parent in [base, *base.parents]:
            if (parent / "conf").exists():
                return parent
    return Path(__file__).resolve().parents[3]


def _load_project_layout_from_file() -> dict[str, Any]:
    repo_root = _resolve_repo_root()
    path = repo_root / "conf" / "clearml" / "project_layout.yaml"
    if not path.exists():
        return {}
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        return {}
    try:
        payload = OmegaConf.to_container(OmegaConf.load(path), resolve=True)
    except Exception:
        return {}
    if isinstance(payload, Mapping):
        return dict(payload)
    return {}


def _resolve_project_layout(cfg: Any | None) -> dict[str, Any]:
    if cfg is not None:
        layout = _cfg_value(cfg, "run.clearml.project_layout")
        try:
            from omegaconf import OmegaConf  # type: ignore
        except Exception:
            OmegaConf = None
        if OmegaConf is not None and OmegaConf.is_config(layout):
            layout = OmegaConf.to_container(layout, resolve=True)
        if isinstance(layout, Mapping):
            return dict(layout)
    return _load_project_layout_from_file()


def _ensure_project_layout(cfg: Any | None) -> dict[str, Any]:
    layout = _resolve_project_layout(cfg)
    if cfg is not None and layout:
        _set_cfg_value(cfg, "run.clearml.project_layout", layout)
    return layout


def _infer_process_from_stage(stage: str | None) -> str | None:
    text = _normalize_str(stage)
    if not text:
        return None
    match = re.match(r"^\d+_(.+)$", text)
    if match:
        return match.group(1)
    return text


def _resolve_project_root(cfg: Any) -> str:
    env_value = _normalize_str(os.getenv("TABULAR_ANALYSIS_CLEARML_PROJECT_ROOT"))
    if env_value:
        return env_value
    env_value = _normalize_str(os.getenv("CLEARML_PROJECT_ROOT"))
    if env_value:
        return env_value
    config_value = _normalize_str(_cfg_value(cfg, "run.clearml.project_root"))
    return config_value or "MFG"


def _resolve_policy(cfg: Any, path: str) -> Any:
    return _cfg_value(cfg, path) or {}


def _extract_dataset_token(value: Any) -> str | None:
    text = _normalize_str(value)
    if not text:
        return None
    if text.startswith("local:"):
        text = text.split(":", 1)[1] or "local"
    if "/" in text or "\\" in text:
        name = Path(text).name
        if name:
            text = Path(name).stem or name
    return _sanitize_identifier(text)


def _resolve_dataset_id(cfg: Any, policy: Any) -> str:
    paths = _cfg_value(policy, "dataset_id_paths") or [
        "data.raw_dataset_id",
        "data.processed_dataset_id",
        "data.dataset_path",
    ]
    for path in list(paths) if isinstance(paths, Iterable) and not isinstance(paths, str) else [paths]:
        token = _extract_dataset_token(_cfg_value(cfg, str(path)))
        if token:
            return token
    fallback = _normalize_str(_cfg_value(policy, "fallback"))
    return _sanitize_identifier(fallback or "unknown")


def _generate_usecase_id(cfg: Any, policy: Any, now: datetime | None) -> str:
    strategy = _normalize_str(_cfg_value(policy, "strategy")) or _normalize_str(_cfg_value(policy, "name"))
    if not strategy:
        strategy = "dataset_timestamp"
    if strategy == "explicit":
        raise ValueError("run.usecase_id is required when usecase_id_policy is explicit.")
    if strategy == "dataset_timestamp":
        prefix = _normalize_str(_cfg_value(policy, "prefix")) or "test"
        dataset_id = _resolve_dataset_id(cfg, policy)
        timestamp_format = _normalize_str(_cfg_value(policy, "timestamp_format")) or "%Y%m%d_%H%M%S"
        now_value = now or datetime.now(timezone.utc)
        timestamp = now_value.strftime(timestamp_format)
        prefix = _sanitize_identifier(prefix)
        dataset_id = _sanitize_identifier(dataset_id)
        return f"{prefix}_{dataset_id}_{timestamp}"
    raise ValueError(f"Unsupported usecase_id_policy strategy: {strategy}")


def _filter_tags(values: Iterable[Any]) -> list[str]:
    filtered: list[str] = []
    for item in values:
        if item is None:
            continue
        text = str(item).strip()
        if not text or text.lower() in ("none", "null"):
            continue
        filtered.append(text)
    return filtered


def _filter_properties(values: Mapping[str, Any]) -> dict[str, Any]:
    filtered: dict[str, Any] = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, str) and value.strip().lower() in ("", "none", "null"):
            continue
        filtered[str(key)] = value
    return filtered


def build_project_name(
    project_root: str,
    usecase_id: str,
    stage: str,
    *,
    process: str | None = None,
    layout: Mapping[str, Any] | None = None,
    cfg: Any | None = None,
) -> str:
    layout_cfg = dict(layout or _resolve_project_layout(cfg))
    solution_root = _normalize_str(layout_cfg.get("solution_root")) or "TabularAnalysis"
    separator = _normalize_str(layout_cfg.get("separator")) or "/"
    group_map = layout_cfg.get("group_map") if isinstance(layout_cfg.get("group_map"), Mapping) else {}
    misc_group = _normalize_str(layout_cfg.get("misc_group")) or "99_Misc"

    process_name = _normalize_str(process) or _infer_process_from_stage(stage)
    group = None
    if process_name and isinstance(group_map, Mapping):
        group = _normalize_str(group_map.get(process_name))
    if not group and isinstance(group_map, Mapping):
        group = _normalize_str(group_map.get(stage))
    group = group or misc_group or _normalize_str(stage) or "unknown"

    root = _normalize_str(project_root) or "MFG"
    usecase_value = _normalize_str(usecase_id) or "unknown"
    root = root.rstrip(separator)
    return separator.join([root, solution_root, usecase_value, group])


def resolve_clearml_identity(cfg: Any, *, now: datetime | None = None) -> ClearMLIdentity:
    usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id"))
    policy = _resolve_policy(cfg, "run.usecase_id_policy")
    if not usecase_id:
        usecase_id = _generate_usecase_id(cfg, policy, now)

    project_root = _resolve_project_root(cfg)

    clearml_policy = _resolve_policy(cfg, "run.clearml.policy")
    policy_tags = _filter_tags(_cfg_value(clearml_policy, "tags") or [])
    extra_tags = _filter_tags(_cfg_value(clearml_policy, "extra_tags") or [])
    policy_properties = _filter_properties(_cfg_value(clearml_policy, "properties") or {})
    extra_properties = _filter_properties(_cfg_value(clearml_policy, "extra_properties") or {})
    merged_properties = dict(extra_properties)
    merged_properties.update(policy_properties)
    merged_tags = [*extra_tags, *policy_tags]

    return ClearMLIdentity(
        project_root=project_root,
        usecase_id=usecase_id,
        tags=merged_tags,
        user_properties=merged_properties,
    )


def apply_clearml_identity(cfg: Any, *, stage: str, now: datetime | None = None) -> ClearMLIdentity:
    identity = resolve_clearml_identity(cfg, now=now)
    _set_cfg_value(cfg, "run.usecase_id", identity.usecase_id)
    _set_cfg_value(cfg, "run.clearml.project_root", identity.project_root)
    layout = _ensure_project_layout(cfg)
    process_name = _normalize_str(_cfg_value(cfg, "task.name")) or _infer_process_from_stage(stage)
    project_name = build_project_name(
        identity.project_root,
        identity.usecase_id,
        stage,
        process=process_name,
        layout=layout,
    )
    if stage == "99_pipeline":
        pipeline_project = _normalize_str(_cfg_value(cfg, "run.clearml.pipeline.project_name"))
        if pipeline_project == "default":
            project_name = f"{pipeline_project}/.pipelines/{identity.usecase_id}"
            _set_cfg_value(cfg, "run.clearml.pipeline.project_mode", "visible")
            _set_cfg_value(cfg, "run.clearml.pipeline.project_name", project_name)
    _set_cfg_value(cfg, "run.clearml.project_name", project_name)
    _set_cfg_value(cfg, "task.project_name", project_name)
    return identity


def resolve_clearml_metadata(
    cfg: Any,
    *,
    stage: str,
    task_name: str,
    identity: ClearMLIdentity | None = None,
    clearml_enabled: bool | None = None,
) -> dict[str, Any]:
    if identity is None:
        identity = resolve_clearml_identity(cfg)
    if not _normalize_str(_cfg_value(cfg, "run.usecase_id")):
        _set_cfg_value(cfg, "run.usecase_id", identity.usecase_id)
    from .. import platform_adapter

    if clearml_enabled is None:
        clearml_enabled = platform_adapter.is_clearml_enabled(cfg)
    props = platform_adapter._build_properties(
        cfg,
        stage=stage,
        task_name=task_name,
        extra=identity.user_properties,
        clearml_enabled=clearml_enabled,
    )
    process = str(props.get("process") or task_name or stage)
    tags = platform_adapter._build_tags(
        cfg,
        process=process,
        schema_version=str(props.get("schema_version") or "unknown"),
        grid_run_id=props.get("grid_run_id"),
        retrain_run_id=props.get("retrain_run_id"),
        extra_tags=platform_adapter._cfg_value(cfg, "run.clearml.extra_tags") or [],
        tags=identity.tags,
    )
    layout = _ensure_project_layout(cfg)
    project_name = build_project_name(
        identity.project_root,
        identity.usecase_id,
        stage,
        process=process,
        layout=layout,
    )
    return {
        "project_root": identity.project_root,
        "project_name": project_name,
        "usecase_id": identity.usecase_id,
        "tags": tags,
        "user_properties": props,
    }
