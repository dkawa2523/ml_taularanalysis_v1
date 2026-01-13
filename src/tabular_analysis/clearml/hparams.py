"""ClearML HyperParameters helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_SECTION_ORDER = ("inputs", "dataset", "preprocess", "model", "eval", "pipeline", "clearml")


def _select_cfg(cfg: Any, dotted_path: str) -> Any:
    if cfg is None:
        return None
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None:
        try:
            return OmegaConf.select(cfg, dotted_path)
        except Exception:
            return None
    current = cfg
    for key in dotted_path.split("."):
        if isinstance(current, Mapping):
            if key not in current:
                return None
            current = current[key]
            continue
        if not hasattr(current, key):
            return None
        current = getattr(current, key)
    return current


def _to_container(value: Any) -> Any:
    if value is None:
        return None
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(value):
        try:
            return OmegaConf.to_container(value, resolve=True)
        except Exception:
            return value
    return value


def _strip_none(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            cleaned_item = _strip_none(item)
            if cleaned_item is None:
                continue
            cleaned[str(key)] = cleaned_item
        return cleaned or None
    if isinstance(value, (list, tuple)):
        cleaned_list = []
        for item in value:
            cleaned_item = _strip_none(item)
            if cleaned_item is None:
                continue
            cleaned_list.append(cleaned_item)
        return cleaned_list or None
    return value


def _normalize_dotpaths(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Sequence):
        normalized: list[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if not text:
                continue
            normalized.append(text)
        return normalized
    return []


def extract_by_dotpaths(cfg: Any, dotpaths: Sequence[str]) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    if not dotpaths:
        return extracted
    for raw_path in dotpaths:
        if not raw_path:
            continue
        if not isinstance(raw_path, str):
            continue
        path = raw_path.strip()
        if not path:
            continue
        if path.endswith(".*"):
            base = path[:-2]
            if not base:
                continue
            value = _to_container(_select_cfg(cfg, base))
            if not isinstance(value, Mapping):
                continue
            cleaned = _strip_none(value)
            if cleaned is None:
                continue
            extracted[base] = cleaned
            continue
        value = _to_container(_select_cfg(cfg, path))
        if value is None:
            continue
        cleaned = _strip_none(value)
        if cleaned is None:
            continue
        extracted[path] = cleaned
    return extracted


def resolve_hyperparams_sections(cfg: Any) -> dict[str, list[str]]:
    raw_sections = _to_container(_select_cfg(cfg, "run.clearml.hyperparams.sections"))
    if not isinstance(raw_sections, Mapping):
        return {}
    resolved: dict[str, list[str]] = {}
    for name, dotpaths in raw_sections.items():
        section_name = str(name).strip()
        if not section_name:
            continue
        resolved[section_name] = _normalize_dotpaths(dotpaths)
    return resolved


def build_hyperparams_sections(cfg: Any) -> dict[str, dict[str, Any]]:
    sections = resolve_hyperparams_sections(cfg)
    if not sections:
        return {}
    payloads: dict[str, dict[str, Any]] = {}
    for name in _SECTION_ORDER:
        dotpaths = sections.get(name)
        if not dotpaths:
            continue
        payload = extract_by_dotpaths(cfg, dotpaths)
        cleaned = _strip_none(payload)
        if not cleaned:
            continue
        payloads[name] = cleaned
    for name, dotpaths in sections.items():
        if name in _SECTION_ORDER:
            continue
        if not dotpaths:
            continue
        payload = extract_by_dotpaths(cfg, dotpaths)
        cleaned = _strip_none(payload)
        if not cleaned:
            continue
        payloads[name] = cleaned
    return payloads
