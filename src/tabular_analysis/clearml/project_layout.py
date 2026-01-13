"""ClearML project layout helpers."""

from __future__ import annotations

import re
from typing import Any, Mapping


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
    return default if current is None else current


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(value):
        value = OmegaConf.to_container(value, resolve=True)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _normalize_separator(value: Any) -> str:
    text = _normalize_str(value)
    return text if text else "/"


def _strip_separator(text: str, sep: str) -> str:
    if not text:
        return text
    if sep == "/":
        return text.strip("/")
    if len(sep) == 1:
        return text.strip(sep)
    while text.startswith(sep):
        text = text[len(sep) :]
    while text.endswith(sep):
        text = text[: -len(sep)]
    return text


def _join_parts(parts: list[str], sep: str) -> str:
    cleaned: list[str] = []
    for part in parts:
        value = _normalize_str(part)
        if value:
            cleaned.append(_strip_separator(value, sep))
    if not cleaned:
        return ""
    return sep.join(cleaned)


_PROCESS_PREFIX = re.compile(r"^\d+[_-](.+)$")


def normalize_process_name(value: Any) -> str | None:
    text = _normalize_str(value)
    if not text:
        return None
    match = _PROCESS_PREFIX.match(text)
    if match:
        text = match.group(1)
    return text


def resolve_process_name(
    cfg: Any,
    *,
    process_name: Any | None = None,
    task_name: Any | None = None,
    stage: Any | None = None,
) -> str:
    candidates = [
        process_name,
        task_name,
        _cfg_value(cfg, "task.name"),
        stage,
        _cfg_value(cfg, "task.stage"),
    ]
    for item in candidates:
        normalized = normalize_process_name(item)
        if normalized:
            return normalized
    return "unknown"


def resolve_project_group(cfg: Any, process_name: str) -> str:
    group_map = _coerce_mapping(_cfg_value(cfg, "run.clearml.project_layout.group_map"))
    process_key = normalize_process_name(process_name) or ""
    group = _normalize_str(group_map.get(process_key))
    if not group:
        group = _normalize_str(group_map.get(process_name))
    if not group:
        group = _normalize_str(_cfg_value(cfg, "run.clearml.project_layout.misc_group"))
    if not group:
        group = process_key or "unknown"
    return group


def build_project_path(cfg: Any, *, process_name: str, usecase_id: str) -> str:
    project_root = _normalize_str(_cfg_value(cfg, "run.clearml.project_root")) or "MFG"
    solution_root = _normalize_str(_cfg_value(cfg, "run.clearml.project_layout.solution_root"))
    if not solution_root:
        solution_root = _normalize_str(_cfg_value(cfg, "run.clearml.template_usecase_id"))
    usecase_value = _normalize_str(usecase_id) or "unknown"
    group = resolve_project_group(cfg, process_name)
    sep = _normalize_separator(_cfg_value(cfg, "run.clearml.project_layout.separator"))
    return _join_parts([project_root, solution_root, usecase_value, group], sep)
