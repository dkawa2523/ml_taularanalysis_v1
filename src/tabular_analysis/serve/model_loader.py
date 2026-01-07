"""Model loading helpers for serving."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..platform_adapter import (
    PlatformAdapterError,
    get_clearml_model_local_copy,
    resolve_registry_model_bundle_by_stage,
)
from ..registry.model_registry_state import get_current_entry, load_registry_state
from .settings import ServingSettings

_ENV_MODEL_BUNDLE = ("TABULAR_MODEL_BUNDLE", "TABULAR_MODEL_BUNDLE_PATH", "MODEL_BUNDLE_PATH")


@dataclass(frozen=True)
class ModelResolution:
    model_bundle_path: Path | None
    model_ref: str | None
    stage: str | None
    source: str | None
    error: str | None


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _clearml_configured() -> bool:
    if _truthy(os.getenv("CLEARML_USE_REGISTRY")):
        return True
    for key in (
        "CLEARML_API_ACCESS_KEY",
        "CLEARML_API_HOST",
        "CLEARML_WEB_HOST",
        "CLEARML_FILES_HOST",
        "CLEARML_CONFIG_FILE",
        "CLEARML_TASK_ID",
    ):
        if os.getenv(key):
            return True
    return False


def _resolve_legacy_bundle_ref() -> str | None:
    for key in _ENV_MODEL_BUNDLE:
        value = _normalize_text(os.getenv(key))
        if value:
            return value
    return None


def _resolve_model_ref_path(model_ref: str) -> Path | None:
    candidate = Path(model_ref).expanduser()
    if candidate.exists():
        if candidate.is_dir():
            bundle = candidate / "model_bundle.joblib"
            if bundle.exists():
                return bundle.resolve()
            return candidate.resolve()
        return candidate.resolve()
    return None


def _resolve_registry_state_path() -> Path | None:
    env_path = _normalize_text(os.getenv("MODEL_REGISTRY_STATE_PATH"))
    if env_path:
        return Path(env_path).expanduser().resolve()
    cwd_path = Path.cwd() / "model_registry_state.json"
    if cwd_path.exists():
        return cwd_path
    outputs_path = Path.cwd() / "outputs" / "model_registry_state.json"
    if outputs_path.exists():
        return outputs_path
    return None


def _resolve_usecase_id(registry: Mapping[str, Any]) -> str | None:
    env_usecase = _normalize_text(os.getenv("USECASE_ID") or os.getenv("TABULAR_USECASE_ID"))
    if env_usecase:
        return env_usecase
    usecases = registry.get("usecases")
    if isinstance(usecases, Mapping) and len(usecases) == 1:
        try:
            return next(iter(usecases.keys()))
        except Exception:
            return None
    return None


def _resolve_local_registry_stage(stage: str) -> ModelResolution:
    registry_path = _resolve_registry_state_path()
    if registry_path is None or not registry_path.exists():
        return ModelResolution(
            None,
            None,
            stage,
            "local_registry",
            "model_registry_state.json not found; set MODEL_REF or place registry state in CWD.",
        )
    registry = load_registry_state(registry_path)
    usecase_id = _resolve_usecase_id(registry)
    if not usecase_id:
        usecases = registry.get("usecases")
        if isinstance(usecases, Mapping) and len(usecases) > 1:
            return ModelResolution(
                None,
                None,
                stage,
                "local_registry",
                "Multiple usecases found in model_registry_state.json; set USECASE_ID or MODEL_REF.",
            )
        return ModelResolution(
            None,
            None,
            stage,
            "local_registry",
            "usecase_id not found in model_registry_state.json; set MODEL_REF.",
        )
    entry = get_current_entry(registry, usecase_id=usecase_id, stage=stage)
    if not entry:
        return ModelResolution(
            None,
            None,
            stage,
            "local_registry",
            f"No model found for stage={stage} in model_registry_state.json.",
        )
    model_ref = _normalize_text(entry.get("model_id") or entry.get("train_task_ref"))
    model_path = None
    if model_ref:
        model_path = _resolve_model_ref_path(model_ref)
    if model_path is None:
        train_task_ref = _normalize_text(entry.get("train_task_ref"))
        if train_task_ref:
            model_path = _resolve_model_ref_path(train_task_ref)
            if model_path is not None:
                model_ref = train_task_ref
    if model_path is None:
        registry_model_id = _normalize_text(entry.get("registry_model_id"))
        if registry_model_id and _clearml_configured():
            try:
                model_path = get_clearml_model_local_copy(registry_model_id)
                model_ref = registry_model_id
            except PlatformAdapterError:
                model_path = None
    if model_path is None:
        return ModelResolution(
            None,
            model_ref,
            stage,
            "local_registry",
            "model_bundle.joblib could not be resolved from model_registry_state.json.",
        )
    return ModelResolution(model_path, model_ref, stage, "local_registry", None)


def _resolve_clearml_stage(stage: str) -> ModelResolution:
    try:
        usecase_id = _normalize_text(os.getenv("USECASE_ID") or os.getenv("TABULAR_USECASE_ID"))
        model_id, model_path = resolve_registry_model_bundle_by_stage(
            stage=stage,
            usecase_id=usecase_id,
        )
        return ModelResolution(model_path, model_id, stage, "clearml_registry", None)
    except PlatformAdapterError as exc:
        return ModelResolution(
            None,
            None,
            stage,
            "clearml_registry",
            str(exc),
        )


def resolve_model_bundle(settings: ServingSettings) -> ModelResolution:
    model_ref = settings.model_ref or _resolve_legacy_bundle_ref()
    if model_ref:
        model_path = _resolve_model_ref_path(model_ref)
        if model_path is not None:
            return ModelResolution(model_path, model_ref, None, "model_ref", None)
        if _clearml_configured():
            try:
                model_path = get_clearml_model_local_copy(model_ref)
                return ModelResolution(model_path, model_ref, None, "clearml_model", None)
            except PlatformAdapterError as exc:
                return ModelResolution(None, model_ref, None, "clearml_model", str(exc))
        return ModelResolution(
            None,
            model_ref,
            None,
            "model_ref",
            "MODEL_REF did not resolve to a model_bundle.joblib path.",
        )

    if settings.model_stage:
        stage = settings.model_stage
        if _clearml_configured():
            clearml_result = _resolve_clearml_stage(stage)
            if clearml_result.model_bundle_path is not None:
                return clearml_result
            local_result = _resolve_local_registry_stage(stage)
            if local_result.model_bundle_path is not None:
                return local_result
            return clearml_result
        return _resolve_local_registry_stage(stage)

    return ModelResolution(
        None,
        None,
        None,
        None,
        "model_ref or model_stage is required; set MODEL_REF, MODEL_STAGE, or TABULAR_MODEL_BUNDLE.",
    )


__all__ = ["ModelResolution", "resolve_model_bundle"]
