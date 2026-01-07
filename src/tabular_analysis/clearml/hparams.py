"""ClearML HyperParameters helpers."""

from __future__ import annotations

from typing import Any, Mapping

from ..platform_adapter import connect_hyperparameters, resolve_version_props


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
        else:
            if not hasattr(current, key):
                return default
            current = getattr(current, key)
    return default if current is None else current


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _drop_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _flatten(prefix: str, params: Mapping[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        flattened[f"{prefix}.{key}"] = value
    return flattened


def _common_hparams(cfg: Any) -> dict[str, Any]:
    usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id")) or _normalize_str(
        _cfg_value(cfg, "usecase_id")
    )
    execution = _normalize_str(_cfg_value(cfg, "run.clearml.execution"))
    try:
        versions = resolve_version_props(cfg, clearml_enabled=True)
    except Exception:
        versions = {"schema_version": "unknown", "code_version": "unknown"}
    return _drop_none(
        {
            "usecase_id": usecase_id,
            "schema_version": versions.get("schema_version"),
            "code_version": versions.get("code_version"),
            "clearml.execution": execution,
        }
    )


def connect_dataset_register_hparams(
    ctx: Any,
    cfg: Any,
    *,
    dataset_path: str | None,
    target_column: str | None,
) -> None:
    hparams = _common_hparams(cfg)
    hparams.update(
        _drop_none(
            {
                "data.dataset_path": dataset_path,
                "data.target_column": target_column,
            }
        )
    )
    connect_hyperparameters(ctx, hparams)


def connect_preprocess_hparams(
    ctx: Any,
    cfg: Any,
    *,
    raw_dataset_id: str | None,
    dataset_path: str | None,
    preprocess_variant: str | None,
    split_strategy: str | None,
    split_seed: int | None,
    store_features: bool | None,
) -> None:
    hparams = _common_hparams(cfg)
    hparams.update(
        _drop_none(
            {
                "raw_dataset_id": raw_dataset_id,
                "data.dataset_path": dataset_path,
                "preprocess.variant": preprocess_variant,
                "split.strategy": split_strategy,
                "split.seed": split_seed,
                "processed_dataset.store_features": store_features,
            }
        )
    )
    connect_hyperparameters(ctx, hparams)


def connect_train_hparams(
    ctx: Any,
    cfg: Any,
    *,
    processed_dataset_id: str | None,
    task_type: str | None,
    primary_metric: str | None,
    model_variant: str | None,
    model_params: Mapping[str, Any] | None,
) -> None:
    hparams = _common_hparams(cfg)
    hparams.update(
        _drop_none(
            {
                "processed_dataset_id": processed_dataset_id,
                "task_type": task_type,
                "primary_metric": primary_metric,
                "model.variant": model_variant,
            }
        )
    )
    if model_params:
        hparams.update(_flatten("model.params", model_params))
    connect_hyperparameters(ctx, hparams)


def connect_infer_hparams(
    ctx: Any,
    cfg: Any,
    *,
    model_id: str | None,
    infer_mode: str | None,
    schema_policy: str | None,
) -> None:
    hparams = _common_hparams(cfg)
    hparams.update(
        _drop_none(
            {
                "model_id": model_id,
                "infer.mode": infer_mode,
                "schema_policy": schema_policy,
            }
        )
    )
    connect_hyperparameters(ctx, hparams)


def connect_leaderboard_hparams(
    ctx: Any,
    cfg: Any,
    *,
    primary_metric: str | None,
    direction: str | None,
    require_comparable: bool | None,
    top_k: int | None,
) -> None:
    hparams = _common_hparams(cfg)
    hparams.update(
        _drop_none(
            {
                "primary_metric": primary_metric,
                "direction": direction,
                "compare.require_comparable": require_comparable,
                "selection.top_k": top_k,
            }
        )
    )
    connect_hyperparameters(ctx, hparams)
