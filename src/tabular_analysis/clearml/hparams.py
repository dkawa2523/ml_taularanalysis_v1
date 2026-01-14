"""ClearML HyperParameters helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from ..platform_adapter import connect_hyperparameters, resolve_version_props

_DEFAULT_SECTION_ORDER = (
    "inputs",
    "dataset",
    "preprocess",
    "model",
    "eval",
    "optimize",
    "pipeline",
    "clearml",
)

_CODE_REF_ALIASES = {
    "repository": "run.clearml.code_repository",
    "branch": "run.clearml.code_branch",
    "mode": "run.clearml.code_version_mode",
}


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
        if dotted_path.startswith("run.clearml.code_ref."):
            alias_key = dotted_path.split(".")[-1]
            alias_path = _CODE_REF_ALIASES.get(alias_key)
            if alias_path:
                try:
                    value = OmegaConf.select(cfg, alias_path)
                except Exception:
                    value = None
                if value is not None:
                    return value
    current = cfg
    for key in dotted_path.split("."):
        if isinstance(current, Mapping):
            if key not in current:
                if dotted_path.startswith("run.clearml.code_ref."):
                    alias_key = dotted_path.split(".")[-1]
                    alias_path = _CODE_REF_ALIASES.get(alias_key)
                    if alias_path:
                        return _cfg_value(cfg, alias_path, default)
                return default
            current = current[key]
        else:
            if not hasattr(current, key):
                if dotted_path.startswith("run.clearml.code_ref."):
                    alias_key = dotted_path.split(".")[-1]
                    alias_path = _CODE_REF_ALIASES.get(alias_key)
                    if alias_path:
                        return _cfg_value(cfg, alias_path, default)
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


def _resolve_repo_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for base in candidates:
        for parent in [base, *base.parents]:
            if (parent / "conf").exists():
                return parent
    return Path(__file__).resolve().parents[3]


def _load_sections_from_file() -> dict[str, list[str]]:
    path = _resolve_repo_root() / "conf" / "clearml" / "hyperparams_sections.yaml"
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
    if not isinstance(payload, Mapping):
        return {}
    sections = payload.get("sections")
    if isinstance(sections, Mapping):
        return {str(key): list(value or []) for key, value in sections.items()}
    return {}


def _resolve_sections_cfg(cfg: Any) -> dict[str, list[str]]:
    sections = _cfg_value(cfg, "run.clearml.hyperparams.sections")
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(sections):
        sections = OmegaConf.to_container(sections, resolve=True)
    if isinstance(sections, Mapping):
        return {str(key): list(value or []) for key, value in sections.items()}
    return _load_sections_from_file()


def _section_key(sections_cfg: Mapping[str, Any], canonical: str) -> str:
    if not sections_cfg:
        return canonical
    for key in sections_cfg:
        if str(key).lower() == canonical.lower():
            return str(key)
    return canonical


def _flatten_mapping(prefix: str, payload: Any, out: dict[str, Any]) -> None:
    if payload is None:
        return
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if value is None:
                continue
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, Mapping):
                _flatten_mapping(next_prefix, value, out)
            else:
                out[next_prefix] = value
        return
    out[prefix] = payload


def _extract_sections(cfg: Any, sections_cfg: Mapping[str, Iterable[str]]) -> dict[str, dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    for name, paths in sections_cfg.items():
        payload: dict[str, Any] = {}
        for path in list(paths or []):
            text = _normalize_str(path)
            if not text:
                continue
            if text.endswith(".*"):
                base = text[:-2]
                value = _cfg_value(cfg, base)
                if value is None:
                    continue
                _flatten_mapping(base, value, payload)
            else:
                value = _cfg_value(cfg, text)
                if value is not None:
                    payload[text] = value
        if payload:
            sections[str(name)] = payload
    return sections


def _section_order(sections_cfg: Mapping[str, Any]) -> list[str]:
    if sections_cfg:
        return [str(key) for key in sections_cfg.keys()]
    return list(_DEFAULT_SECTION_ORDER)


def _merge_section(
    sections: dict[str, dict[str, Any]],
    name: str,
    payload: Mapping[str, Any],
) -> None:
    cleaned = _drop_none(payload)
    if not cleaned:
        return
    merged = dict(sections.get(name, {}))
    merged.update(cleaned)
    sections[name] = merged


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
            "run.usecase_id": usecase_id,
            "run.schema_version": versions.get("schema_version"),
            "run.code_version": versions.get("code_version"),
            "run.clearml.execution": execution,
        }
    )


def _connect_section(ctx: Any, name: str, payload: Mapping[str, Any]) -> None:
    cleaned = _drop_none(payload)
    if not cleaned:
        return
    connect_hyperparameters(ctx, cleaned, name=name)


def _connect_sections(
    ctx: Any,
    sections: Mapping[str, Mapping[str, Any]],
    order: Iterable[str],
) -> None:
    seen: set[str] = set()
    for name in order:
        payload = sections.get(name)
        if not payload:
            continue
        _connect_section(ctx, name, payload)
        seen.add(name)
    for name, payload in sections.items():
        if name in seen:
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
    sections_cfg = _resolve_sections_cfg(cfg)
    sections = _extract_sections(cfg, sections_cfg)
    inputs_key = _section_key(sections_cfg, "inputs")
    dataset_key = _section_key(sections_cfg, "dataset")
    clearml_key = _section_key(sections_cfg, "clearml")
    _merge_section(
        sections,
        inputs_key,
        {
            "data.dataset_path": dataset_path,
            "data.target_column": target_column,
        },
    )
    _merge_section(
        sections,
        dataset_key,
        {"data.raw_dataset_id": raw_dataset_id},
    )
    _merge_section(sections, clearml_key, _execution_hparams(cfg))
    _connect_sections(ctx, sections, _section_order(sections_cfg))


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
    sections_cfg = _resolve_sections_cfg(cfg)
    sections = _extract_sections(cfg, sections_cfg)
    inputs_key = _section_key(sections_cfg, "inputs")
    dataset_key = _section_key(sections_cfg, "dataset")
    preprocess_key = _section_key(sections_cfg, "preprocess")
    clearml_key = _section_key(sections_cfg, "clearml")
    _merge_section(sections, inputs_key, {"data.dataset_path": dataset_path})
    _merge_section(sections, dataset_key, {"data.raw_dataset_id": raw_dataset_id})
    _merge_section(
        sections,
        preprocess_key,
        {
            "preprocess.variant": preprocess_variant,
            "data.split.strategy": split_strategy,
            "data.split.seed": split_seed,
            "ops.processed_dataset.store_features": store_features,
        },
    )
    _merge_section(sections, clearml_key, _execution_hparams(cfg))
    _connect_sections(ctx, sections, _section_order(sections_cfg))


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
    model_payload: dict[str, Any] = {
        "model_variant.name": model_variant,
        "train.model": model_variant,
    }
    if model_params:
        model_payload.update(_flatten("train.params", model_params))
    sections_cfg = _resolve_sections_cfg(cfg)
    sections = _extract_sections(cfg, sections_cfg)
    dataset_key = _section_key(sections_cfg, "dataset")
    model_key = _section_key(sections_cfg, "model")
    eval_key = _section_key(sections_cfg, "eval")
    clearml_key = _section_key(sections_cfg, "clearml")
    _merge_section(
        sections,
        dataset_key,
        {"data.processed_dataset_id": processed_dataset_id},
    )
    _merge_section(sections, model_key, model_payload)
    _merge_section(
        sections,
        eval_key,
        {
            "eval.task_type": task_type,
            "eval.primary_metric": primary_metric,
        },
    )
    _merge_section(sections, clearml_key, _execution_hparams(cfg))
    _connect_sections(ctx, sections, _section_order(sections_cfg))


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
            "data.raw_dataset_id": provenance.get("raw_dataset_id"),
            "data.processed_dataset_id": provenance.get("processed_dataset_id"),
            "preprocess.variant": provenance.get("preprocess_variant"),
            "split_hash": provenance.get("split_hash"),
            "recipe_hash": provenance.get("recipe_hash"),
        }
    sections_cfg = _resolve_sections_cfg(cfg)
    sections = _extract_sections(cfg, sections_cfg)
    inputs_key = _section_key(sections_cfg, "inputs")
    model_key = _section_key(sections_cfg, "model")
    dataset_key = _section_key(sections_cfg, "dataset")
    optimize_key = _section_key(sections_cfg, "optimize")
    clearml_key = _section_key(sections_cfg, "clearml")
    _merge_section(
        sections,
        inputs_key,
        {
            "infer.mode": infer_mode,
            "infer.validation.mode": schema_policy,
            "infer.input_source": input_source,
            "infer.input_path": input_path,
            "infer.input_json": input_json,
        },
    )
    _merge_section(
        sections,
        model_key,
        {
            "infer.model_id": model_id,
            "model_abbr": model_abbr,
        },
    )
    if optimize_payload:
        _merge_section(sections, optimize_key, dict(optimize_payload))
    if include_dataset:
        _merge_section(sections, dataset_key, dataset_payload)
    if include_execution:
        _merge_section(sections, clearml_key, _execution_hparams(cfg))
    _connect_sections(ctx, sections, _section_order(sections_cfg))


def connect_leaderboard(
    ctx: Any,
    cfg: Any,
    *,
    primary_metric: str | None,
    direction: str | None,
    require_comparable: bool | None,
    top_k: int | None,
) -> None:
    sections_cfg = _resolve_sections_cfg(cfg)
    sections = _extract_sections(cfg, sections_cfg)
    eval_key = _section_key(sections_cfg, "eval")
    clearml_key = _section_key(sections_cfg, "clearml")
    _merge_section(
        sections,
        eval_key,
        {
            "eval.primary_metric": primary_metric,
            "eval.direction": direction,
            "leaderboard.require_comparable": require_comparable,
            "leaderboard.top_k": top_k,
        },
    )
    _merge_section(sections, clearml_key, _execution_hparams(cfg))
    _connect_sections(ctx, sections, _section_order(sections_cfg))


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
