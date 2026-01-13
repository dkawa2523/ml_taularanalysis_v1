"""ClearML naming/tagging helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Mapping


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


def _shorten_token(token: str, max_len: int = 12) -> str:
    if max_len <= 0:
        return token
    if len(token) <= max_len:
        return token
    if max_len < 6:
        return token[:max_len]
    tail = 3
    head = max_len - tail - 1
    return f"{token[:head]}~{token[-tail:]}"


def _resolve_model_abbr(cfg: Any) -> str:
    value = _normalize_str(_cfg_value(cfg, "model_variant.name"))
    if value is None:
        value = _normalize_str(_cfg_value(cfg, "train.model"))
    return _sanitize_identifier(value or "unknown")


def _resolve_preprocess_variant(cfg: Any) -> str:
    value = _normalize_str(_cfg_value(cfg, "preprocess_variant.name"))
    if value is None:
        value = _normalize_str(_cfg_value(cfg, "preprocess.variant"))
    return _sanitize_identifier(value or "unknown")


def _resolve_raw_dataset_id(cfg: Any) -> str:
    for path in ("data.raw_dataset_id", "data.dataset_path", "data.processed_dataset_id"):
        token = _extract_dataset_token(_cfg_value(cfg, path))
        if token:
            return token
    return "unknown"


def _merge_extra_tags(cfg: Any, tags: Iterable[str]) -> None:
    existing = _cfg_value(cfg, "run.clearml.extra_tags") or []
    if isinstance(existing, str):
        existing_list = [existing]
    elif isinstance(existing, Iterable):
        existing_list = [str(item) for item in existing if item is not None]
    else:
        existing_list = []
    merged = existing_list[:]
    for tag in tags:
        if tag and tag not in merged:
            merged.append(tag)
    _set_cfg_value(cfg, "run.clearml.extra_tags", merged)


def apply_train_model_naming(cfg: Any) -> dict[str, Any]:
    """Apply train_model naming/tagging policy to config."""
    model_abbr = _resolve_model_abbr(cfg)
    preprocess_variant = _resolve_preprocess_variant(cfg)
    raw_dataset_id = _resolve_raw_dataset_id(cfg)
    raw_short = _shorten_token(raw_dataset_id)
    task_name = f"train__{model_abbr}__pp={preprocess_variant}__ds={raw_short}"
    tags = [
        f"model:{model_abbr}",
        f"preprocess:{preprocess_variant}",
        f"dataset:{raw_dataset_id}",
    ]
    _set_cfg_value(cfg, "run.clearml.task_name", task_name)
    _merge_extra_tags(cfg, tags)
    return {"task_name": task_name, "tags": tags}


def apply_preprocess_naming(cfg: Any) -> dict[str, Any]:
    """Apply preprocess naming/tagging policy to config."""
    preprocess_variant = _resolve_preprocess_variant(cfg)
    task_name = f"preprocess__pp={preprocess_variant}"
    tags = [f"preprocess:{preprocess_variant}"]
    _set_cfg_value(cfg, "run.clearml.task_name", task_name)
    _merge_extra_tags(cfg, tags)
    return {"task_name": task_name, "tags": tags}


def apply_train_ensemble_naming(cfg: Any) -> dict[str, Any]:
    """Apply train_ensemble naming/tagging policy to config."""
    preprocess_variant = _resolve_preprocess_variant(cfg)
    method = _normalize_str(_cfg_value(cfg, "ensemble.method")) or "mean_topk"
    top_k = _cfg_value(cfg, "ensemble.top_k")
    try:
        top_k = int(top_k) if top_k is not None else None
    except Exception:
        top_k = None
    if method == "weighted":
        top_k_max = _cfg_value(cfg, "ensemble.weighted.top_k_max")
        try:
            top_k_max = int(top_k_max) if top_k_max is not None else None
        except Exception:
            top_k_max = None
        if top_k_max is not None and top_k_max > 0:
            if top_k is None or top_k <= 0:
                top_k = top_k_max
            else:
                top_k = min(top_k, top_k_max)
    top_k_label = f"{top_k}" if top_k is not None else "na"
    task_name = f"train_ensemble/{method}(k={top_k_label})"
    model_tag = f"ensemble_{method}"
    tags = [
        f"model:{model_tag}",
        f"ensemble:{method}",
        f"topk:{top_k_label}",
        f"preprocess:{preprocess_variant}",
    ]
    _set_cfg_value(cfg, "run.clearml.task_name", task_name)
    _merge_extra_tags(cfg, tags)
    return {"task_name": task_name, "tags": tags}
