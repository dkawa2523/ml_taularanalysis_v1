"""ClearML HyperParameters helpers."""

from __future__ import annotations

from typing import Any, Mapping

from ..platform_adapter import connect_hyperparameters, resolve_version_props

_SECTION_ORDER = (
    "Inputs",
    "Dataset",
    "Preprocess",
    "Model",
    "Eval",
    "Optimize",
    "Execution",
    "Links",
)


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


def _drop_none(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _flatten(prefix: str, params: Mapping[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        flattened[f"{prefix}.{key}"] = value
    return flattened


def _execution_hparams(cfg: Any) -> dict[str, Any]:
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


def _connect_section(ctx: Any, name: str, payload: Mapping[str, Any]) -> None:
    cleaned = _drop_none(payload)
    if not cleaned:
        return
    connect_hyperparameters(ctx, cleaned, name=name)


def _connect_sections(ctx: Any, sections: Mapping[str, Mapping[str, Any]]) -> None:
    for name in _SECTION_ORDER:
        payload = sections.get(name)
        if not payload:
            continue
        _connect_section(ctx, name, payload)


def connect_dataset_register(
    ctx: Any,
    cfg: Any,
    *,
    dataset_path: str | None,
    target_column: str | None,
    raw_dataset_id: str | None = None,
) -> None:
    sections = {
        "Inputs": {
            "data.dataset_path": dataset_path,
            "data.target_column": target_column,
        },
        "Dataset": {"raw_dataset_id": raw_dataset_id},
        "Execution": _execution_hparams(cfg),
    }
    _connect_sections(ctx, sections)


def connect_preprocess(
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
    sections = {
        "Inputs": {"data.dataset_path": dataset_path},
        "Dataset": {"raw_dataset_id": raw_dataset_id},
        "Preprocess": {
            "preprocess.variant": preprocess_variant,
            "split.strategy": split_strategy,
            "split.seed": split_seed,
            "processed_dataset.store_features": store_features,
        },
        "Execution": _execution_hparams(cfg),
    }
    _connect_sections(ctx, sections)


def connect_train_model(
    ctx: Any,
    cfg: Any,
    *,
    processed_dataset_id: str | None,
    task_type: str | None,
    primary_metric: str | None,
    model_variant: str | None,
    model_params: Mapping[str, Any] | None,
) -> None:
    model_payload: dict[str, Any] = {"model.variant": model_variant}
    if model_params:
        model_payload.update(_flatten("model.params", model_params))
    sections = {
        "Dataset": {"processed_dataset_id": processed_dataset_id},
        "Model": model_payload,
        "Eval": {
            "task_type": task_type,
            "primary_metric": primary_metric,
        },
        "Execution": _execution_hparams(cfg),
    }
    _connect_sections(ctx, sections)


def connect_infer(
    ctx: Any,
    cfg: Any,
    *,
    model_id: str | None,
    model_abbr: str | None = None,
    infer_mode: str | None,
    schema_policy: str | None,
    input_source: str | None = None,
    input_path: str | None = None,
    input_json: str | None = None,
    provenance: Mapping[str, Any] | None = None,
    optimize_payload: Mapping[str, Any] | None = None,
    include_dataset: bool = True,
    include_execution: bool = True,
) -> None:
    dataset_payload: dict[str, Any] = {}
    if provenance:
        dataset_payload = {
            "train_task_id": provenance.get("train_task_id"),
            "raw_dataset_id": provenance.get("raw_dataset_id"),
            "processed_dataset_id": provenance.get("processed_dataset_id"),
            "preprocess_variant": provenance.get("preprocess_variant"),
            "split_hash": provenance.get("split_hash"),
            "recipe_hash": provenance.get("recipe_hash"),
        }
    sections = {
        "Inputs": {
            "infer.mode": infer_mode,
            "schema_policy": schema_policy,
            "input.source": input_source,
            "input.path": input_path,
            "input.json": input_json,
        },
        "Model": {
            "model_id": model_id,
            "model_abbr": model_abbr,
        },
    }
    if optimize_payload:
        sections["Optimize"] = dict(optimize_payload)
    if include_dataset:
        sections["Dataset"] = dataset_payload
    if include_execution:
        sections["Execution"] = _execution_hparams(cfg)
    _connect_sections(ctx, sections)


def connect_leaderboard(
    ctx: Any,
    cfg: Any,
    *,
    primary_metric: str | None,
    direction: str | None,
    require_comparable: bool | None,
    top_k: int | None,
) -> None:
    sections = {
        "Eval": {
            "primary_metric": primary_metric,
            "direction": direction,
            "compare.require_comparable": require_comparable,
            "selection.top_k": top_k,
        },
        "Execution": _execution_hparams(cfg),
    }
    _connect_sections(ctx, sections)


def connect_dataset_register_hparams(
    ctx: Any,
    cfg: Any,
    *,
    dataset_path: str | None,
    target_column: str | None,
) -> None:
    connect_dataset_register(
        ctx,
        cfg,
        dataset_path=dataset_path,
        target_column=target_column,
        raw_dataset_id=None,
    )


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
    connect_preprocess(
        ctx,
        cfg,
        raw_dataset_id=raw_dataset_id,
        dataset_path=dataset_path,
        preprocess_variant=preprocess_variant,
        split_strategy=split_strategy,
        split_seed=split_seed,
        store_features=store_features,
    )


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
    connect_train_model(
        ctx,
        cfg,
        processed_dataset_id=processed_dataset_id,
        task_type=task_type,
        primary_metric=primary_metric,
        model_variant=model_variant,
        model_params=model_params,
    )


def connect_infer_hparams(
    ctx: Any,
    cfg: Any,
    *,
    model_id: str | None,
    model_abbr: str | None = None,
    infer_mode: str | None,
    schema_policy: str | None,
    input_source: str | None = None,
    input_path: str | None = None,
    input_json: str | None = None,
    provenance: Mapping[str, Any] | None = None,
    optimize_payload: Mapping[str, Any] | None = None,
    include_dataset: bool = True,
    include_execution: bool = True,
) -> None:
    connect_infer(
        ctx,
        cfg,
        model_id=model_id,
        model_abbr=model_abbr,
        infer_mode=infer_mode,
        schema_policy=schema_policy,
        input_source=input_source,
        input_path=input_path,
        input_json=input_json,
        provenance=provenance,
        optimize_payload=optimize_payload,
        include_dataset=include_dataset,
        include_execution=include_execution,
    )


def connect_leaderboard_hparams(
    ctx: Any,
    cfg: Any,
    *,
    primary_metric: str | None,
    direction: str | None,
    require_comparable: bool | None,
    top_k: int | None,
) -> None:
    connect_leaderboard(
        ctx,
        cfg,
        primary_metric=primary_metric,
        direction=direction,
        require_comparable=require_comparable,
        top_k=top_k,
    )
