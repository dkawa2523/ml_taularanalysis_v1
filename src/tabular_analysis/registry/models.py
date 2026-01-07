"""Model registry.

- conf/group/model/*.yaml の class_path/framework/params を読み、実体を生成する
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from typing import Any, Dict

OPTIONAL_DEPENDENCIES = {
    "lightgbm": "models",
    "xgboost": "models",
    "catboost": "models",
    "tabpfn": "tabpfn",
}


class MissingOptionalDependencyError(RuntimeError):
    def __init__(self, *, module: str, class_path: str, extra: str | None = None):
        install_hint = f'pip install -e ".[{extra}]"' if extra else f"pip install {module}"
        message = (
            f"Optional dependency '{module}' is required for model '{class_path}'. "
            f"Install it with: {install_hint}"
        )
        super().__init__(message)
        self.module = module
        self.class_path = class_path
        self.extra = extra


class ModelWeightsUnavailableError(RuntimeError):
    def __init__(
        self,
        *,
        model_name: str,
        auto_download: bool | None = None,
        detail: str | None = None,
    ):
        base = f"Required weights for model '{model_name}' are not available."
        if detail:
            base = f"{base} {detail}"
        if auto_download is True:
            hint = (
                "Auto-download was enabled but weights could not be retrieved. "
                "Check network access or pre-download the weights."
            )
        elif auto_download is False:
            hint = (
                "Set model_variant.params.auto_download=true to allow download, "
                "or pre-download the weights."
            )
        else:
            hint = "Ensure the required weights are available."
        super().__init__(f"{base} {hint}")
        self.model_name = model_name
        self.auto_download = auto_download
        self.detail = detail


def _to_container(value: Any) -> Any:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(value):
        return OmegaConf.to_container(value, resolve=True)
    return value


def _normalize_task_type(value: Any) -> str:
    key = str(value or "").strip().lower()
    if key in ("classification", "classifier", "class"):
        return "classification"
    if key in ("regression", "regressor", "reg"):
        return "regression"
    return "regression"


def _resolve_class_path(class_path: Any, *, task_type: str | None) -> str:
    class_path = _to_container(class_path)
    if isinstance(class_path, Mapping):
        if not task_type:
            raise ValueError("model_variant.class_path requires eval.task_type for selection.")
        normalized = _normalize_task_type(task_type)
        selected = class_path.get(normalized)
        if not selected:
            raise ValueError(
                f"model_variant.class_path missing entry for task_type '{normalized}'."
            )
        class_path = selected
    if not isinstance(class_path, str) or "." not in class_path:
        raise ValueError(f"Invalid model_variant.class_path: {class_path}")
    return class_path


def build_model(model_variant: Dict[str, Any], *, task_type: str | None = None):
    if not model_variant:
        raise ValueError("model_variant is required to build a model.")

    variant = _to_container(model_variant) or {}
    if not isinstance(variant, dict):
        raise TypeError("model_variant must be a dict-like object.")

    class_path = variant.get("class_path")
    if not class_path:
        raise ValueError("model_variant.class_path is required.")
    class_path = _resolve_class_path(class_path, task_type=task_type)

    module_name, class_name = class_path.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        root_module = module_name.split(".", 1)[0]
        if exc.name in (module_name, root_module) and root_module in OPTIONAL_DEPENDENCIES:
            raise MissingOptionalDependencyError(
                module=root_module,
                class_path=class_path,
                extra=OPTIONAL_DEPENDENCIES[root_module],
            ) from exc
        raise ImportError(f"Failed to import module '{module_name}' for model '{class_path}'.") from exc
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
    except (MissingOptionalDependencyError, ModelWeightsUnavailableError):
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to instantiate model '{class_path}' with params {params}.") from exc
