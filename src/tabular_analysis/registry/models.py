"""Model registry.

- conf/group/model/*.yaml の class_path/framework/params を読み、実体を生成する
"""

from __future__ import annotations

import importlib
from typing import Any, Dict


def _to_container(value: Any) -> Any:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(value):
        return OmegaConf.to_container(value, resolve=True)
    return value


def build_model(model_variant: Dict[str, Any]):
    if not model_variant:
        raise ValueError("model_variant is required to build a model.")

    variant = _to_container(model_variant) or {}
    if not isinstance(variant, dict):
        raise TypeError("model_variant must be a dict-like object.")

    class_path = variant.get("class_path")
    if not class_path:
        raise ValueError("model_variant.class_path is required.")
    if not isinstance(class_path, str) or "." not in class_path:
        raise ValueError(f"Invalid model_variant.class_path: {class_path}")

    module_name, class_name = class_path.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise ImportError(f"Failed to import module '{module_name}' for model '{class_path}'.") from exc

    try:
        model_cls = getattr(module, class_name)
    except AttributeError as exc:
        raise ImportError(f"Model class '{class_name}' not found in '{module_name}'.") from exc

    params = _to_container(variant.get("params") or {}) or {}
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise TypeError("model_variant.params must be a dict.")

    try:
        return model_cls(**params)
    except Exception as exc:
        raise RuntimeError(f"Failed to instantiate model '{class_path}' with params {params}.") from exc
