"""TabPFN wrappers with optional weight handling."""

from __future__ import annotations

import inspect
from typing import Any

from .models import MissingOptionalDependencyError, ModelWeightsUnavailableError

_DOWNLOAD_PARAM_CANDIDATES = (
    "download",
    "download_if_needed",
    "download_if_missing",
    "auto_download",
)
_DOWNLOAD_FUNC_CANDIDATES = (
    ("download_model",),
    ("download",),
    ("download_weights",),
    ("utils", "download_model"),
    ("utils", "download"),
    ("utils", "download_weights"),
)
_WEIGHT_ERROR_HINTS = (
    "weight",
    "weights",
    "checkpoint",
    "model file",
    "download",
    "pretrained",
)


def _import_tabpfn(class_path: str):
    try:
        import tabpfn  # type: ignore
    except ModuleNotFoundError as exc:
        raise MissingOptionalDependencyError(
            module="tabpfn",
            class_path=class_path,
            extra="tabpfn",
        ) from exc
    return tabpfn


def _resolve_tabpfn_class(tabpfn_module: Any, class_name: str):
    model_cls = getattr(tabpfn_module, class_name, None)
    if model_cls is None:
        raise ImportError(
            f"tabpfn.{class_name} not found. Install or upgrade the tabpfn package."
        )
    return model_cls


def _filter_params(model_cls: Any, params: dict[str, Any]) -> dict[str, Any]:
    try:
        signature = inspect.signature(model_cls)
    except (TypeError, ValueError):
        return params
    accepts_kwargs = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()
    )
    if accepts_kwargs:
        return params
    return {key: value for key, value in params.items() if key in signature.parameters}


def _apply_download_param(model_cls: Any, params: dict[str, Any], auto_download: bool) -> None:
    try:
        signature = inspect.signature(model_cls)
    except (TypeError, ValueError):
        return
    for name in _DOWNLOAD_PARAM_CANDIDATES:
        if name in signature.parameters:
            params[name] = bool(auto_download)
            return


def _maybe_download_weights(tabpfn_module: Any, *, model_name: str) -> None:
    last_exc: Exception | None = None
    for path in _DOWNLOAD_FUNC_CANDIDATES:
        target = tabpfn_module
        for attr in path:
            target = getattr(target, attr, None)
            if target is None:
                break
        if callable(target):
            try:
                target()
                return
            except Exception as exc:
                last_exc = exc
                break
    if last_exc is not None:
        raise ModelWeightsUnavailableError(
            model_name=model_name,
            auto_download=True,
            detail=str(last_exc),
        ) from last_exc


def _looks_like_weight_error(exc: Exception) -> bool:
    if isinstance(exc, FileNotFoundError):
        return True
    message = str(exc).lower()
    return any(token in message for token in _WEIGHT_ERROR_HINTS)


class _TabPFNBase:
    _CLASS_NAME = ""

    def __init__(self, *, auto_download: bool = False, **params: Any):
        self._auto_download = bool(auto_download)
        self._params = dict(params)
        self._model = self._init_model()

    def _init_model(self):
        class_path = f"tabpfn.{self._CLASS_NAME}"
        tabpfn_module = _import_tabpfn(class_path)
        model_cls = _resolve_tabpfn_class(tabpfn_module, self._CLASS_NAME)
        params = dict(self._params)
        _apply_download_param(model_cls, params, self._auto_download)
        if self._auto_download:
            _maybe_download_weights(tabpfn_module, model_name=self._CLASS_NAME)
        params = _filter_params(model_cls, params)
        try:
            return model_cls(**params)
        except Exception as exc:
            if _looks_like_weight_error(exc):
                raise ModelWeightsUnavailableError(
                    model_name=self._CLASS_NAME,
                    auto_download=self._auto_download,
                    detail=str(exc),
                ) from exc
            raise

    def fit(self, *args: Any, **kwargs: Any):
        try:
            return self._model.fit(*args, **kwargs)
        except Exception as exc:
            if _looks_like_weight_error(exc):
                raise ModelWeightsUnavailableError(
                    model_name=self._CLASS_NAME,
                    auto_download=self._auto_download,
                    detail=str(exc),
                ) from exc
            raise

    def predict(self, *args: Any, **kwargs: Any):
        try:
            return self._model.predict(*args, **kwargs)
        except Exception as exc:
            if _looks_like_weight_error(exc):
                raise ModelWeightsUnavailableError(
                    model_name=self._CLASS_NAME,
                    auto_download=self._auto_download,
                    detail=str(exc),
                ) from exc
            raise

    def get_params(self, deep: bool = True) -> dict[str, Any]:
        if hasattr(self._model, "get_params"):
            return self._model.get_params(deep=deep)
        return dict(self._params)

    def set_params(self, **params: Any):
        if hasattr(self._model, "set_params"):
            self._model.set_params(**params)
        else:
            self._params.update(params)
        return self

    def __getattr__(self, name: str):
        return getattr(self._model, name)


class TabPFNClassifier(_TabPFNBase):
    _CLASS_NAME = "TabPFNClassifier"

    def predict_proba(self, *args: Any, **kwargs: Any):
        try:
            return self._model.predict_proba(*args, **kwargs)
        except Exception as exc:
            if _looks_like_weight_error(exc):
                raise ModelWeightsUnavailableError(
                    model_name=self._CLASS_NAME,
                    auto_download=self._auto_download,
                    detail=str(exc),
                ) from exc
            raise


class TabPFNRegressor(_TabPFNBase):
    _CLASS_NAME = "TabPFNRegressor"
