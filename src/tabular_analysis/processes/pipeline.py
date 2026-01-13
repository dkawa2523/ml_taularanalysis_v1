"""pipeline process.

T009: grid execution + task_id handoff.
- preprocess/train/leaderboard/infer を独立タスクとして実行する接着剤
- grid_run_id を生成し、各タスクへ伝播させる
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Mapping
import uuid
from ..clearml.reporting import report_scalar, scalars_enabled
from ..platform_adapter import (
    build_clearml_code_ref,
    clearml_task_type_controller,
    create_pipeline_controller_from_template,
    get_task_artifact_local_copy,
    hash_config,
    hash_recipe,
    hash_split,
    init_task_context,
    is_clearml_enabled,
    report_markdown,
    resolve_clearml_task_url,
    resolve_clearml_code_ref_mode,
    resolve_version_props,
    save_config_resolved,
    upload_artifact,
    write_manifest,
    write_out_json,
)
from ..ops.clearml_identity import apply_clearml_identity
from ..reporting.pipeline_report import build_pipeline_report_bundle

_STAGE_BY_TASK = {
    "dataset_register": "01_dataset_register",
    "preprocess": "02_preprocess",
    "train_model": "03_train_model",
    "train_ensemble": "04_train_ensemble",
    "infer": "04_infer",
    "leaderboard": "05_leaderboard",
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
    return current


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


def _to_list(values: Any) -> list[str]:
    if values is None:
        return []
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_list(values):
        return [str(v) for v in values if v is not None]
    if isinstance(values, (list, tuple, set)):
        return [str(v) for v in values if v is not None]
    return [str(values)]


def _to_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(value):
        try:
            container = OmegaConf.to_container(value, resolve=True)
        except Exception:
            container = None
        if isinstance(container, Mapping):
            return dict(container)
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    return {}


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


def _to_value_list(value: Any) -> list[Any]:
    if value is None:
        return []
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_list(value):
        return [v for v in value]
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except Exception:
        return default


def _resolve_exec_policy_limits(cfg: Any) -> dict[str, int]:
    limits_cfg = _to_mapping(_cfg_value(cfg, "exec_policy.limits"))
    if "max_jobs" in limits_cfg:
        max_jobs = _to_int(limits_cfg.get("max_jobs"), 0)
    else:
        max_jobs = _to_int(_cfg_value(cfg, "pipeline.grid.max_jobs"), 0)
    if "max_models" in limits_cfg:
        max_models = _to_int(limits_cfg.get("max_models"), 0)
    else:
        max_models = _to_int(_cfg_value(cfg, "leaderboard.top_k"), 0)
    max_hpo_trials = _to_int(limits_cfg.get("max_hpo_trials"), 0)
    if max_jobs < 0:
        max_jobs = 0
    if max_models < 0:
        max_models = 0
    if max_hpo_trials < 0:
        max_hpo_trials = 0
    return {
        "max_jobs": max_jobs,
        "max_models": max_models,
        "max_hpo_trials": max_hpo_trials,
    }


def _resolve_pipeline_limits(cfg: Any) -> dict[str, int]:
    limits_cfg = _to_mapping(_cfg_value(cfg, "pipeline.limits"))
    max_preprocess = _to_int(limits_cfg.get("max_preprocess_variants"), 0)
    max_train = _to_int(limits_cfg.get("max_train_tasks"), 0)
    max_ensemble = _to_int(limits_cfg.get("max_ensemble_tasks"), 0)
    if max_preprocess < 0:
        max_preprocess = 0
    if max_train < 0:
        max_train = 0
    if max_ensemble < 0:
        max_ensemble = 0
    return {
        "max_preprocess_variants": max_preprocess,
        "max_train_tasks": max_train,
        "max_ensemble_tasks": max_ensemble,
    }


def _resolve_pipeline_parallelism(cfg: Any) -> dict[str, int]:
    parallelism_cfg = _to_mapping(_cfg_value(cfg, "pipeline.parallelism"))
    max_steps = _to_int(parallelism_cfg.get("max_concurrent_steps"), 0)
    max_train = _to_int(parallelism_cfg.get("max_concurrent_train"), 0)
    if max_steps < 0:
        max_steps = 0
    if max_train < 0:
        max_train = 0
    return {
        "max_concurrent_steps": max_steps,
        "max_concurrent_train": max_train,
    }


def _resolve_exec_policy_selection(cfg: Any) -> dict[str, bool]:
    selection_cfg = _to_mapping(_cfg_value(cfg, "exec_policy.selection"))
    selection: dict[str, bool] = {}
    for key in ("calibration", "uncertainty", "ci"):
        if key in selection_cfg:
            selection[key] = bool(selection_cfg.get(key))
    return selection


def _resolve_fail_policy(cfg: Any) -> dict[str, Any]:
    policy_cfg = _to_mapping(_cfg_value(cfg, "pipeline.fail_policy"))
    allow_skipped = bool(policy_cfg.get("allow_skipped", True))
    allowed_failures = _to_int(policy_cfg.get("allowed_failures"), 0)
    fail_fast = bool(policy_cfg.get("fail_fast", False))
    min_successful = _to_int(policy_cfg.get("min_successful_train_tasks"), 1)
    if allowed_failures < 0:
        allowed_failures = 0
    if min_successful < 0:
        min_successful = 0
    return {
        "allow_skipped": allow_skipped,
        "allowed_failures": allowed_failures,
        "fail_fast": fail_fast,
        "min_successful_train_tasks": min_successful,
    }


def _apply_exec_policy_selection(overrides: dict[str, Any], selection: Mapping[str, bool]) -> None:
    for key, path in (
        ("calibration", "eval.calibration.enabled"),
        ("uncertainty", "eval.uncertainty.enabled"),
        ("ci", "eval.ci.enabled"),
    ):
        if key in selection and not selection[key]:
            overrides[path] = False


def _resolve_exec_policy_queues(cfg: Any) -> dict[str, Any]:
    queues_cfg = _to_mapping(_cfg_value(cfg, "exec_policy.queues"))

    def _queue(key: str) -> str | None:
        return _normalize_str(queues_cfg.get(key))

    model_variants_cfg = _to_mapping(queues_cfg.get("model_variants"))
    model_variants = {
        str(key): _normalize_str(value)
        for key, value in model_variants_cfg.items()
        if _normalize_str(value)
    }
    heavy_variants = {
        str(name)
        for name in _to_list(queues_cfg.get("heavy_model_variants"))
        if _normalize_str(name)
    }

    default_queue = _queue("default") or _normalize_str(_cfg_value(cfg, "run.clearml.queue_name"))
    return {
        "default": default_queue,
        "pipeline": _queue("pipeline"),
        "dataset_register": _queue("dataset_register"),
        "preprocess": _queue("preprocess"),
        "train_model": _queue("train_model"),
        "train_ensemble": _queue("train_ensemble"),
        "train_model_heavy": _queue("train_model_heavy"),
        "leaderboard": _queue("leaderboard"),
        "infer": _queue("infer"),
        "model_variants": model_variants,
        "heavy_model_variants": heavy_variants,
    }


def _select_queue(
    queues: Mapping[str, Any],
    process: str,
    *,
    model_variant: str | None = None,
) -> str | None:
    default_queue = _normalize_str(queues.get("default"))
    if process == "train_model":
        model_variants = queues.get("model_variants") or {}
        if model_variant:
            variant_queue = _normalize_str(model_variants.get(model_variant))
            if variant_queue:
                return variant_queue
            heavy_variants = queues.get("heavy_model_variants") or set()
            if model_variant in heavy_variants:
                heavy_queue = _normalize_str(queues.get("train_model_heavy"))
                if heavy_queue:
                    return heavy_queue
        train_queue = _normalize_str(queues.get("train_model"))
        return train_queue or default_queue
    return _normalize_str(queues.get(process)) or default_queue


def _resolve_plan_only(cfg: Any) -> bool:
    return bool(_cfg_value(cfg, "pipeline.plan_only")) or bool(
        _cfg_value(cfg, "pipeline.dry_run")
    ) or bool(_cfg_value(cfg, "pipeline.plan"))


def _expand_param_grid(param_grid: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not param_grid:
        return [{}]
    combos: list[dict[str, Any]] = [{}]
    for key, raw_values in param_grid.items():
        values = _to_value_list(raw_values)
        if not values:
            return []
        next_combos: list[dict[str, Any]] = []
        for combo in combos:
            for value in values:
                next_combo = dict(combo)
                next_combo[str(key)] = value
                next_combos.append(next_combo)
        combos = next_combos
    return combos


def _format_param_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _format_hpo_signature(params: Mapping[str, Any]) -> str:
    if not params:
        return ""
    parts = []
    for key in sorted(params):
        parts.append(f"{key}={_format_param_value(params[key])}")
    return "__".join(parts)


def _build_hpo_trials(
    model_variant: str, param_sets: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    trials: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for params in param_sets:
        if not params:
            trials.append({"params": {}, "hpo_run_id": None, "suffix": None})
            continue
        signature = _format_hpo_signature(params)
        base_id = _sanitize_component(
            f"{model_variant}__{signature}" if signature else str(model_variant)
        )
        count = seen.get(base_id, 0) + 1
        seen[base_id] = count
        hpo_run_id = base_id if count == 1 else _sanitize_component(f"{base_id}__{count}")
        suffix = _sanitize_component(signature or "trial")
        if count > 1:
            suffix = _sanitize_component(f"{suffix}__{count}")
        trials.append({"params": params, "hpo_run_id": hpo_run_id, "suffix": suffix})
    return trials


def _limit_hpo_trials(
    trials_by_model: Mapping[str, list[dict[str, Any]]],
    max_hpo_trials: int,
) -> tuple[dict[str, list[dict[str, Any]]], int]:
    if max_hpo_trials <= 0:
        return {str(k): list(v) for k, v in trials_by_model.items()}, 0
    limited: dict[str, list[dict[str, Any]]] = {}
    skipped = 0
    for model_variant, trials in trials_by_model.items():
        if len(trials) > max_hpo_trials:
            limited[model_variant] = list(trials[:max_hpo_trials])
            skipped += len(trials) - max_hpo_trials
        else:
            limited[model_variant] = list(trials)
    return limited, skipped


def _build_train_plan(
    preprocess_variants: list[str],
    model_variants: list[str],
    trials_by_model: Mapping[str, list[dict[str, Any]]],
    *,
    max_jobs: int,
    max_hpo_trials: int,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, list[dict[str, Any]]]]:
    raw_trial_count = sum(len(trials_by_model.get(model, [])) for model in model_variants)
    raw_jobs = len(preprocess_variants) * raw_trial_count if preprocess_variants else 0
    limited_trials, _ = _limit_hpo_trials(trials_by_model, max_hpo_trials)

    jobs: list[dict[str, Any]] = []
    for preprocess_variant in preprocess_variants:
        for model_variant in model_variants:
            for trial in limited_trials.get(model_variant, [{"params": {}, "hpo_run_id": None, "suffix": None}]):
                jobs.append(
                    {
                        "preprocess_variant": preprocess_variant,
                        "model_variant": model_variant,
                        "trial": trial,
                    }
                )

    planned_jobs = len(jobs)
    if max_jobs > 0 and planned_jobs > max_jobs:
        jobs = jobs[:max_jobs]
    planned_jobs = len(jobs)
    skipped_due_to_policy = raw_jobs - planned_jobs
    if skipped_due_to_policy < 0:
        skipped_due_to_policy = 0
    info = {
        "raw_jobs": raw_jobs,
        "planned_jobs": planned_jobs,
        "skipped_due_to_policy": skipped_due_to_policy,
    }
    return jobs, info, limited_trials


def _resolve_hpo_trials(
    cfg: Any, model_variants: list[str]
) -> tuple[bool, dict[str, list[dict[str, Any]]], dict[str, Any]]:
    enabled = bool(_cfg_value(cfg, "pipeline.hpo.enabled"))
    params_cfg = _to_mapping(_cfg_value(cfg, "pipeline.hpo.params"))
    trials_by_model: dict[str, list[dict[str, Any]]] = {}
    for model_variant in model_variants:
        model_params = _to_mapping(params_cfg.get(model_variant)) if enabled else {}
        if enabled and model_params:
            param_sets = _expand_param_grid(model_params)
            if not param_sets:
                raise ValueError(f"pipeline.hpo.params.{model_variant} is empty.")
        else:
            param_sets = [{}]
        trials_by_model[model_variant] = _build_hpo_trials(model_variant, param_sets)
    return enabled, trials_by_model, params_cfg


def _build_hpo_param_overrides(params: Mapping[str, Any]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for key, value in params.items():
        overrides[f"group.model.model_variant.params.{key}"] = value
    return overrides


def _merge_extra_tags(base_tags: list[str], tag: str | None) -> list[str]:
    if not tag:
        return list(base_tags)
    combined = list(base_tags)
    if tag not in combined:
        combined.append(tag)
    return combined


def _ensure_grid_run_id(cfg: Any) -> str:
    grid_run_id = _normalize_str(_cfg_value(cfg, "run.grid_run_id"))
    if grid_run_id:
        return grid_run_id
    new_id = uuid.uuid4().hex
    _set_cfg_value(cfg, "run.grid_run_id", new_id)
    return new_id


def _sanitize_component(value: str) -> str:
    cleaned = []
    for ch in value:
        if ch.isalnum() or ch in ("-", "_"):
            cleaned.append(ch)
        else:
            cleaned.append("_")
    result = "".join(cleaned).strip("_")
    return result or "item"


def _needs_quote(text: str) -> bool:
    if not text:
        return True
    for ch in text:
        if ch.isspace() or ch in "[]{}(),=":
            return True
    return False


def _quote_string(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _format_list(values: Iterable[Any]) -> str:
    items = []
    for item in values:
        if item is None:
            continue
        if isinstance(item, bool):
            items.append("true" if item else "false")
        elif isinstance(item, (int, float)):
            items.append(str(item))
        else:
            items.append(_quote_string(str(item)))
    return "[" + ",".join(items) + "]"


def _format_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        return _format_list(value)
    text = str(value)
    if _needs_quote(text):
        return _quote_string(text)
    return text


def _overrides_to_args(overrides: Mapping[str, Any]) -> list[str]:
    args: list[str] = []
    for key, value in overrides.items():
        formatted = _format_value(value)
        if formatted is None:
            continue
        args.append(f"{key}={formatted}")
    return args


def _overrides_to_params(overrides: Mapping[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for key, value in overrides.items():
        formatted = _format_value(value)
        if formatted is None:
            continue
        params[key] = formatted
    return params


def _normalize_override_key(text: str) -> str:
    key = str(text).strip().split("=", 1)[0].strip()
    return key.lstrip("+~")


def _ensure_override(overrides: list[str], key: str, value: Any) -> None:
    if value is None:
        return
    normalized = {_normalize_override_key(item) for item in overrides}
    if key in normalized:
        return
    formatted = _format_value(value)
    if formatted is None:
        return
    overrides.append(f"{key}={formatted}")


def _hydra_task_overrides() -> list[str]:
    try:
        from hydra.core.hydra_config import HydraConfig  # type: ignore

        hydra_cfg = HydraConfig.get()
        overrides = getattr(getattr(hydra_cfg, "overrides", None), "task", None)
        if overrides:
            return [str(item) for item in overrides if item]
    except Exception:
        return []
    return []


def _merge_overrides(*items: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for item in items:
        merged.update(dict(item))
    return merged


def _collect_run_overrides(
    cfg: Any,
    grid_run_id: str,
    *,
    child_execution: str | None = None,
) -> dict[str, Any]:
    run_cfg = getattr(cfg, "run", None)
    overrides: dict[str, Any] = {
        "run.grid_run_id": grid_run_id,
    }
    if run_cfg is None:
        return overrides
    overrides["run.usecase_id"] = getattr(run_cfg, "usecase_id", None)
    overrides["run.schema_version"] = getattr(run_cfg, "schema_version", None)
    overrides["run.retrain_run_id"] = getattr(run_cfg, "retrain_run_id", None)
    policy_cfg = getattr(run_cfg, "usecase_id_policy", None)
    if getattr(policy_cfg, "name", None):
        overrides["ops/usecase_id_policy"] = getattr(policy_cfg, "name")
    clearml_cfg = getattr(run_cfg, "clearml", None)
    if clearml_cfg is not None:
        overrides["run.clearml.enabled"] = bool(getattr(clearml_cfg, "enabled", False))
        execution = child_execution if child_execution is not None else getattr(clearml_cfg, "execution", None)
        overrides["run.clearml.execution"] = execution
        overrides["run.clearml.project_root"] = getattr(clearml_cfg, "project_root", None)
        overrides["run.clearml.queue_name"] = getattr(clearml_cfg, "queue_name", None)
        overrides["run.clearml.clone_from_task_id"] = getattr(clearml_cfg, "clone_from_task_id", None)
        parent_task_id = _normalize_str(_cfg_value(cfg, "run.clearml.parent_task_id"))
        if parent_task_id:
            overrides["run.clearml.parent_task_id"] = parent_task_id
        extra_tags = getattr(clearml_cfg, "extra_tags", None)
        if extra_tags:
            overrides["run.clearml.extra_tags"] = list(extra_tags)
        clearml_policy = getattr(clearml_cfg, "policy", None)
        if getattr(clearml_policy, "name", None):
            overrides["ops/clearml_policy"] = getattr(clearml_policy, "name")
    return overrides


def _collect_data_overrides(cfg: Any) -> dict[str, Any]:
    data_cfg = getattr(cfg, "data", None)
    overrides: dict[str, Any] = {}
    if data_cfg is None:
        return overrides
    for key in ("dataset_path", "raw_dataset_id", "processed_dataset_id", "target_column"):
        value = getattr(data_cfg, key, None)
        if value is not None:
            overrides[f"data.{key}"] = value
    id_columns = getattr(data_cfg, "id_columns", None)
    if id_columns:
        overrides["data.id_columns"] = list(id_columns)
    drop_columns = getattr(data_cfg, "drop_columns", None)
    if drop_columns:
        overrides["data.drop_columns"] = list(drop_columns)
    split_cfg = getattr(data_cfg, "split", None)
    if split_cfg is not None:
        for key in ("strategy", "test_size", "seed", "group_column", "time_column"):
            value = getattr(split_cfg, key, None)
            if value is not None:
                overrides[f"data.split.{key}"] = value
    return overrides


def _build_downstream_data_overrides(
    data_overrides: Mapping[str, Any],
    *,
    raw_dataset_id: str | None,
) -> dict[str, Any]:
    overrides = dict(data_overrides)
    if not raw_dataset_id:
        return overrides
    overrides["data.raw_dataset_id"] = raw_dataset_id
    dataset_path_value = _normalize_str(overrides.get("data.dataset_path"))
    if raw_dataset_id.startswith("local:"):
        if not dataset_path_value:
            raise ValueError("data.dataset_path is required when data.raw_dataset_id is local.")
    else:
        overrides.pop("data.dataset_path", None)
    return overrides


_ENSEMBLE_OVERRIDE_KEYS = (
    "ensemble.method",
    "ensemble.top_k",
    "ensemble.selection_metric",
    "ensemble.exclude_variants",
    "ensemble.fallback_rerun_predict",
    "ensemble.weighted.search",
    "ensemble.weighted.n_samples",
    "ensemble.weighted.seed",
    "ensemble.weighted.top_k_max",
    "ensemble.stacking.meta_model",
    "ensemble.stacking.cv_folds",
    "ensemble.stacking.seed",
    "ensemble.stacking.require_test_split",
)


def _collect_ensemble_overrides(cfg: Any) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for key in _ENSEMBLE_OVERRIDE_KEYS:
        value = _cfg_value(cfg, key)
        if value is None:
            continue
        overrides[key] = _to_container(value)
    return overrides


def _collect_eval_overrides(cfg: Any) -> dict[str, Any]:
    eval_cfg = getattr(cfg, "eval", None)
    overrides: dict[str, Any] = {}
    if eval_cfg is None:
        return overrides
    for key in ("primary_metric", "direction", "cv_folds", "seed", "task_type"):
        value = getattr(eval_cfg, key, None)
        if value is not None:
            overrides[f"eval.{key}"] = value
    classification_cfg = getattr(eval_cfg, "classification", None)
    if classification_cfg is not None:
        for key in ("mode", "top_k"):
            value = getattr(classification_cfg, key, None)
            if value is not None:
                overrides[f"eval.classification.{key}"] = value
    metrics_cfg = getattr(eval_cfg, "metrics", None)
    if metrics_cfg is not None:
        value = getattr(metrics_cfg, "classification_multiclass", None)
        if value is not None:
            overrides["eval.metrics.classification_multiclass"] = list(value)
    selection = _resolve_exec_policy_selection(cfg)
    if selection:
        _apply_exec_policy_selection(overrides, selection)
    return overrides


def _build_run_root(base_output_dir: Path, grid_run_id: str, name: str) -> Path:
    safe_name = _sanitize_component(name)
    return base_output_dir / "grid" / str(grid_run_id) / safe_name


def _stage_dir(run_root: Path, task_name: str) -> Path:
    stage = _STAGE_BY_TASK[task_name]
    return run_root / stage


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_repo_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for base in candidates:
        for parent in [base, *base.parents]:
            if (parent / "conf").exists():
                return parent
    return Path.cwd()


def _run_cli_task(args: list[str], *, cwd: Path, config_dir: Path | None) -> None:
    cmd = [sys.executable, "-m", "tabular_analysis.cli", *args]
    env = os.environ.copy()
    if config_dir is not None and "TABULAR_ANALYSIS_CONFIG_DIR" not in env:
        env["TABULAR_ANALYSIS_CONFIG_DIR"] = str(config_dir)
    # Ensure child tasks create their own ClearML Task instead of reusing the pipeline task.
    for key in (
        "CLEARML_TASK_ID",
        "TRAINS_TASK_ID",
        "CLEARML_AGENT_TASK_ID",
        "CLEARML_TASK",
        "TASK_ID",
        "CLEARML_PROC_MASTER_ID",
        "TRAINS_PROC_MASTER_ID",
    ):
        env.pop(key, None)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit={proc.returncode})\n$ {' '.join(cmd)}\n\n{proc.stdout}"
        )


def _load_model_set_payload(path: Path) -> Any:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception as exc:  # pragma: no cover - omegaconf is expected in runtime
        raise RuntimeError("OmegaConf is required to load model_set configs.") from exc
    try:
        cfg = OmegaConf.load(path)
    except Exception as exc:
        raise ValueError(f"Failed to load model_set config: {path}") from exc
    try:
        return OmegaConf.to_container(cfg, resolve=False)
    except Exception:
        return cfg


def _normalize_model_set_name(value: str) -> str:
    name = value.strip()
    if not name:
        return ""
    if Path(name).name != name:
        raise ValueError(f"Invalid pipeline.model_set name: {value}")
    return name


def _resolve_model_set_variants(model_set: str) -> list[str]:
    name = _normalize_model_set_name(model_set)
    if not name:
        return []
    repo_root = _resolve_repo_root()
    path = repo_root / "conf" / "pipeline" / "model_sets" / f"{name}.yaml"
    if not path.exists():
        raise ValueError(f"pipeline.model_set '{name}' not found: {path}")
    payload = _load_model_set_payload(path)
    variants: list[str] = []
    if isinstance(payload, Mapping):
        variants = _to_list(payload.get("variants"))
        auto = bool(payload.get("auto"))
        task_type = _normalize_str(payload.get("task_type"))
        if auto and not task_type:
            raise ValueError(f"model_set '{name}' requires task_type when auto=true.")
        if auto or (task_type and not variants):
            from ..registry.models import list_model_variants

            variants = list_model_variants(task_type=task_type)
        exclude = set(_to_list(payload.get("exclude")))
        if exclude:
            variants = [item for item in variants if item not in exclude]
    elif isinstance(payload, list):
        variants = _to_list(payload)
    else:
        raise ValueError(f"model_set config must be mapping or list: {path}")
    deduped: list[str] = []
    seen: set[str] = set()
    for item in variants:
        name = _normalize_str(item)
        if not name or name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return deduped


def _normalize_option(value: Any) -> str:
    text = _normalize_str(value)
    return text.lower() if text else ""


def _dedupe_variants(values: Iterable[Any]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        name = _normalize_str(item)
        if not name or name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return deduped


def _resolve_pipeline_profile(cfg: Any) -> str:
    profile = _normalize_option(_cfg_value(cfg, "pipeline.profile"))
    return profile or "default"


def _resolve_group_mode(cfg: Any, group: str) -> str:
    mode = _normalize_option(_cfg_value(cfg, f"pipeline.groups.{group}.mode"))
    return mode or "default"


def _resolve_group_custom(cfg: Any, group: str) -> tuple[str, list[str], list[str]]:
    base = _normalize_option(_cfg_value(cfg, f"pipeline.groups.{group}.custom.base")) or "default"
    include = _dedupe_variants(_to_list(_cfg_value(cfg, f"pipeline.groups.{group}.custom.include")))
    exclude = _dedupe_variants(_to_list(_cfg_value(cfg, f"pipeline.groups.{group}.custom.exclude")))
    return base, include, exclude


def _resolve_group_variants(
    *,
    group: str,
    mode: str,
    base: str,
    include: list[str],
    exclude: list[str],
    all_specs: Iterable[Any],
    default_specs: Iterable[Any],
    on_missing_dependency: str | None = None,
    on_inapplicable: str | None = None,
    schema: Any | None = None,
) -> tuple[list[str], dict[str, Any]]:
    mode_key = mode or "default"
    if mode_key not in ("none", "default", "custom"):
        raise ValueError(f"Invalid pipeline.groups.{group}.mode: {mode}")
    base_key = base or "default"
    if mode_key == "custom" and base_key not in ("default", "none"):
        raise ValueError(f"Invalid pipeline.groups.{group}.custom.base: {base}")

    spec_list = list(all_specs)
    spec_by_id = {spec.id: spec for spec in spec_list}
    all_ids = set(spec_by_id.keys())

    if mode_key == "custom":
        for name in [*include, *exclude]:
            if name not in all_ids:
                raise ValueError(f"Unknown {group} variant: {name}")

    default_ids = [spec.id for spec in default_specs]
    selected: list[str]
    if mode_key == "none":
        selected = []
    elif mode_key == "default":
        selected = list(default_ids)
    else:
        selected = list(default_ids) if base_key == "default" else []
        selected.extend(include)
    selected = _dedupe_variants(selected)
    if exclude:
        excluded = set(exclude)
        selected = [name for name in selected if name not in excluded]

    skipped_missing: list[str] = []
    skipped_inapplicable: list[str] = []
    final: list[str] = []
    on_missing = _normalize_option(on_missing_dependency) or "skip"
    on_inapplicable = _normalize_option(on_inapplicable) or "skip"
    for name in selected:
        spec = spec_by_id.get(name)
        if spec is None:
            continue
        missing = list(getattr(spec, "missing_dependencies")() or [])
        if missing:
            if on_missing == "error":
                raise ValueError(
                    f"{group} variant '{name}' requires missing dependencies: {', '.join(missing)}"
                )
            if on_missing != "include":
                skipped_missing.append(name)
                continue
        applicability = getattr(spec, "check_applicability", None)
        if callable(applicability):
            result = applicability(schema)
            if not getattr(result, "ok", True):
                if on_inapplicable == "error":
                    raise ValueError(
                        f"{group} variant '{name}' is not applicable: {getattr(result, 'reason', None)}"
                    )
                if on_inapplicable != "include":
                    skipped_inapplicable.append(name)
                    continue
        final.append(name)

    info = {
        "mode": mode_key,
        "base": base_key if mode_key == "custom" else None,
        "include": list(include),
        "exclude": list(exclude),
        "candidates": list(selected),
        "variants": list(final),
        "skipped_missing_dependencies": skipped_missing,
        "skipped_inapplicable": skipped_inapplicable,
    }
    return final, info


def _resolve_variants_v2(cfg: Any, *, group_modes: Mapping[str, str]) -> tuple[list[str], list[str], dict[str, Any]]:
    from ..registry import (
        list_default_model_variants,
        list_default_preprocess_variants,
        list_model_variants,
        list_preprocess_variants,
    )

    task_type = _normalize_str(_cfg_value(cfg, "eval.task_type"))
    schema = _cfg_value(cfg, "data.schema")

    preprocess_mode = group_modes.get("preprocess") or "default"
    preprocess_base, preprocess_include, preprocess_exclude = _resolve_group_custom(cfg, "preprocess")
    preprocess_specs = list_preprocess_variants(
        task_type=task_type,
        schema=schema,
        defaults_only=False,
        filter_inapplicable=False,
    )
    preprocess_defaults = list_default_preprocess_variants(
        task_type=task_type,
        schema=schema,
        filter_inapplicable=False,
    )
    preprocess_variants, preprocess_info = _resolve_group_variants(
        group="preprocess",
        mode=preprocess_mode,
        base=preprocess_base,
        include=preprocess_include,
        exclude=preprocess_exclude,
        all_specs=preprocess_specs,
        default_specs=preprocess_defaults,
        on_missing_dependency="skip",
        on_inapplicable=_cfg_value(cfg, "pipeline.groups.preprocess.custom.on_inapplicable"),
        schema=schema,
    )

    train_mode = group_modes.get("train") or "default"
    train_base, train_include, train_exclude = _resolve_group_custom(cfg, "train")
    model_specs = list_model_variants(task_type=task_type, defaults_only=False)
    model_defaults = list_default_model_variants(task_type=task_type)
    model_variants, train_info = _resolve_group_variants(
        group="train",
        mode=train_mode,
        base=train_base,
        include=train_include,
        exclude=train_exclude,
        all_specs=model_specs,
        default_specs=model_defaults,
        on_missing_dependency=_cfg_value(cfg, "pipeline.groups.train.custom.on_missing_dependency"),
        on_inapplicable=None,
        schema=None,
    )

    group_info = {
        "preprocess": preprocess_info,
        "train": train_info,
        "ensemble": {"mode": group_modes.get("ensemble") or "default"},
        "leaderboard": {"mode": group_modes.get("leaderboard") or "default"},
    }
    return preprocess_variants, model_variants, group_info


def _resolve_variants(cfg: Any) -> tuple[list[str], list[str]]:
    preprocess_variants = _to_list(_cfg_value(cfg, "pipeline.preprocess_variants"))
    if not preprocess_variants:
        single = _normalize_str(_cfg_value(cfg, "pipeline.preprocess_variant"))
        if single:
            preprocess_variants = [single]
    if not preprocess_variants:
        preprocess_variants = _to_list(_cfg_value(cfg, "pipeline.grid.preprocess_variants"))
    if not preprocess_variants:
        fallback = _normalize_str(_cfg_value(cfg, "preprocess_variant.name")) or _normalize_str(
            _cfg_value(cfg, "group.preprocess.preprocess_variant.name")
        )
        if fallback:
            preprocess_variants = [fallback]
    model_set = _normalize_str(_cfg_value(cfg, "pipeline.model_set"))
    if model_set:
        model_variants = _resolve_model_set_variants(model_set)
    else:
        model_variants = _to_list(_cfg_value(cfg, "pipeline.model_variants"))
        if not model_variants:
            model_variants = _to_list(_cfg_value(cfg, "pipeline.grid.model_variants"))
    if not model_variants:
        fallback = _normalize_str(_cfg_value(cfg, "model_variant.name")) or _normalize_str(
            _cfg_value(cfg, "group.model.model_variant.name")
        )
        if fallback:
            model_variants = [fallback]
    return preprocess_variants, model_variants


def _grid_cell_tag(preprocess_variant: str, model_variant: str) -> str:
    return f"grid_cell:{preprocess_variant}__{model_variant}"


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


def _join_project_path(base: str, tail: str, sep: str) -> str:
    if not base:
        return tail
    if not tail:
        return base
    return f"{_strip_separator(base, sep)}{sep}{_strip_separator(tail, sep)}"


def _resolve_step_project_name(
    cfg: Any,
    *,
    process_name: str,
    preprocess_variant: str | None = None,
    train_project_per_preprocess: bool = True,
) -> str:
    from ..clearml.project_layout import build_project_path

    usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id")) or "unknown"
    base = build_project_path(cfg, process_name=process_name, usecase_id=usecase_id)
    if process_name == "train_model" and preprocess_variant and train_project_per_preprocess:
        sep = _normalize_separator(_cfg_value(cfg, "run.clearml.project_layout.separator"))
        return _join_project_path(base, _sanitize_component(preprocess_variant), sep)
    return base


def _build_train_project_group_override(
    cfg: Any,
    *,
    preprocess_variant: str | None,
    train_project_per_preprocess: bool,
) -> dict[str, Any]:
    if not train_project_per_preprocess:
        return {}
    if not preprocess_variant:
        return {}
    base_group = _normalize_str(_cfg_value(cfg, "run.clearml.project_layout.group_map.train_model"))
    if not base_group:
        return {}
    sep = _normalize_separator(_cfg_value(cfg, "run.clearml.project_layout.separator"))
    group_value = _join_project_path(base_group, _sanitize_component(preprocess_variant), sep)
    return {"run.clearml.project_layout.group_map.train_model": group_value}


def _build_plan_steps(
    cfg: Any,
    *,
    base_output_dir: Path,
    grid_run_id: str,
    run_preprocess: bool,
    run_train: bool,
    run_ensemble: bool,
    run_leaderboard: bool,
    run_infer: bool,
    preprocess_targets: list[str],
    train_jobs: list[dict[str, Any]],
    base_extra_tags: list[str],
    max_models: int,
    queues: Mapping[str, Any],
) -> dict[str, Any]:
    preprocess_steps: list[dict[str, Any]] = []
    preprocess_by_variant: dict[str, dict[str, Any]] = {}
    train_steps: list[dict[str, Any]] = []
    ensemble_steps: list[dict[str, Any]] = []
    leaderboard_step = None
    infer_step = None
    builder_cfg = _to_mapping(_cfg_value(cfg, "pipeline.builder"))
    train_project_per_preprocess = bool(builder_cfg.get("train_project_per_preprocess", True))

    if run_preprocess:
        if not preprocess_targets:
            raise ValueError("preprocess variants are empty.")
        for preprocess_variant in preprocess_targets:
            step_name = f"preprocess__{_sanitize_component(preprocess_variant)}"
            run_root = _build_run_root(base_output_dir, grid_run_id, f"preprocess__{preprocess_variant}")
            overrides = {
                "group/preprocess": preprocess_variant,
                "run.output_dir": str(run_root),
            }
            step_queue = _select_queue(queues, "preprocess")
            if step_queue:
                overrides["run.clearml.queue_name"] = step_queue
            project_name = _resolve_step_project_name(
                cfg,
                process_name="preprocess",
                preprocess_variant=preprocess_variant,
                train_project_per_preprocess=train_project_per_preprocess,
            )
            overrides["run.clearml.project_name"] = project_name
            step = {
                "step_name": step_name,
                "task_name": "preprocess",
                "run_root": run_root,
                "run_dir": _stage_dir(run_root, "preprocess"),
                "parents": [],
                "queue": step_queue,
                "overrides": overrides,
                "preprocess_variant": preprocess_variant,
                "project_name": project_name,
            }
            preprocess_steps.append(step)
            preprocess_by_variant[preprocess_variant] = step

    if run_train:
        if not preprocess_by_variant:
            raise ValueError("preprocess outputs are required before train.")
        for job in train_jobs:
            preprocess_variant = str(job.get("preprocess_variant") or "")
            payload = preprocess_by_variant.get(preprocess_variant)
            if payload is None:
                raise ValueError(f"preprocess step missing for {preprocess_variant}.")
            preprocess_run_dir = payload["run_dir"]
            model_variant = str(job.get("model_variant") or "")
            trial = job.get("trial") or {}
            hpo_params = trial.get("params") or {}
            hpo_run_id = trial.get("hpo_run_id")
            suffix = trial.get("suffix")
            step_name = (
                f"train__{_sanitize_component(preprocess_variant)}__{_sanitize_component(model_variant)}"
            )
            run_name = f"train__{preprocess_variant}__{model_variant}"
            if suffix:
                step_name = f"{step_name}__{_sanitize_component(suffix)}"
                run_name = f"{run_name}__{suffix}"
            run_root = _build_run_root(base_output_dir, grid_run_id, run_name)
            overrides = {
                "group/model": model_variant,
                "train.inputs.preprocess_run_dir": str(preprocess_run_dir),
                "run.output_dir": str(run_root),
            }
            overrides.update(
                _build_train_project_group_override(
                    cfg,
                    preprocess_variant=preprocess_variant,
                    train_project_per_preprocess=train_project_per_preprocess,
                )
            )
            overrides.update(_build_hpo_param_overrides(hpo_params))
            grid_tag = _grid_cell_tag(preprocess_variant, model_variant)
            extra_tags = _merge_extra_tags(base_extra_tags, grid_tag)
            if hpo_run_id:
                extra_tags = _merge_extra_tags(extra_tags, f"hpo:{hpo_run_id}")
            if extra_tags:
                overrides["run.clearml.extra_tags"] = extra_tags
            step_queue = _select_queue(queues, "train_model", model_variant=model_variant)
            if step_queue:
                overrides["run.clearml.queue_name"] = step_queue
            project_name = _resolve_step_project_name(
                cfg,
                process_name="train_model",
                preprocess_variant=preprocess_variant,
                train_project_per_preprocess=train_project_per_preprocess,
            )
            overrides["run.clearml.project_name"] = project_name
            train_steps.append(
                {
                    "step_name": step_name,
                    "task_name": "train_model",
                    "run_root": run_root,
                    "run_dir": _stage_dir(run_root, "train_model"),
                    "parents": [payload["step_name"]],
                    "queue": step_queue,
                    "overrides": overrides,
                    "preprocess_variant": preprocess_variant,
                    "model_variant": model_variant,
                    "hpo_run_id": hpo_run_id,
                    "hpo_params": hpo_params or None,
                    "inputs": {
                        "processed_dataset_id": {
                            "from_step": payload["step_name"],
                            "source": "preprocess",
                        }
                    },
                    "project_name": project_name,
                }
            )

    if run_ensemble:
        if not train_steps:
            raise ValueError("train outputs are required before ensemble.")
        ensemble_by_variant: dict[str, list[str]] = {}
        for step in train_steps:
            variant = str(step.get("preprocess_variant") or "unknown")
            ensemble_by_variant.setdefault(variant, []).append(step["step_name"])
        for preprocess_variant, parents in ensemble_by_variant.items():
            step_name = f"ensemble__{_sanitize_component(preprocess_variant)}"
            run_root = _build_run_root(
                base_output_dir, grid_run_id, f"ensemble__{preprocess_variant}"
            )
            overrides = {
                "run.output_dir": str(run_root),
                "preprocess.variant": preprocess_variant,
            }
            overrides.update(_collect_ensemble_overrides(cfg))
            step_queue = _select_queue(queues, "train_ensemble")
            if step_queue:
                overrides["run.clearml.queue_name"] = step_queue
            project_name = _resolve_step_project_name(
                cfg,
                process_name="train_ensemble",
                preprocess_variant=preprocess_variant,
                train_project_per_preprocess=train_project_per_preprocess,
            )
            overrides["run.clearml.project_name"] = project_name
            ensemble_steps.append(
                {
                    "step_name": step_name,
                    "task_name": "train_ensemble",
                    "run_root": run_root,
                    "run_dir": _stage_dir(run_root, "train_ensemble"),
                    "parents": parents,
                    "queue": step_queue,
                    "overrides": overrides,
                    "preprocess_variant": preprocess_variant,
                    "project_name": project_name,
                }
            )

    if run_leaderboard:
        run_root = _build_run_root(base_output_dir, grid_run_id, "leaderboard")
        overrides = {"run.output_dir": str(run_root)}
        if max_models > 0:
            overrides["leaderboard.top_k"] = max_models
        step_queue = _select_queue(queues, "leaderboard")
        if step_queue:
            overrides["run.clearml.queue_name"] = step_queue
        project_name = _resolve_step_project_name(
            cfg,
            process_name="leaderboard",
            train_project_per_preprocess=train_project_per_preprocess,
        )
        overrides["run.clearml.project_name"] = project_name
        leaderboard_step = {
            "step_name": "leaderboard",
            "task_name": "leaderboard",
            "run_root": run_root,
            "run_dir": _stage_dir(run_root, "leaderboard"),
            "parents": [step["step_name"] for step in [*train_steps, *ensemble_steps]],
            "queue": step_queue,
            "overrides": overrides,
            "project_name": project_name,
        }

    if run_infer:
        infer_cfg = getattr(cfg, "infer", None)
        infer_mode = _normalize_str(getattr(infer_cfg, "mode", None)) or "single"
        run_root = _build_run_root(base_output_dir, grid_run_id, "infer")
        overrides = {
            "infer.mode": infer_mode,
            "run.output_dir": str(run_root),
        }
        step_queue = _select_queue(queues, "infer")
        if step_queue:
            overrides["run.clearml.queue_name"] = step_queue
        parents = [leaderboard_step["step_name"]] if leaderboard_step else []
        project_name = _resolve_step_project_name(
            cfg,
            process_name="infer",
            train_project_per_preprocess=train_project_per_preprocess,
        )
        overrides["run.clearml.project_name"] = project_name
        infer_step = {
            "step_name": "infer",
            "task_name": "infer",
            "run_root": run_root,
            "run_dir": _stage_dir(run_root, "infer"),
            "parents": parents,
            "queue": step_queue,
            "overrides": overrides,
            "project_name": project_name,
        }

    return {
        "preprocess": preprocess_steps,
        "train": train_steps,
        "ensemble": ensemble_steps,
        "leaderboard": leaderboard_step,
        "infer": infer_step,
    }


def _count_plan_tasks(steps: Mapping[str, Any]) -> dict[str, int]:
    preprocess_steps = steps.get("preprocess") if isinstance(steps, Mapping) else None
    train_steps = steps.get("train") if isinstance(steps, Mapping) else None
    ensemble_steps = steps.get("ensemble") if isinstance(steps, Mapping) else None
    leaderboard_step = steps.get("leaderboard") if isinstance(steps, Mapping) else None
    infer_step = steps.get("infer") if isinstance(steps, Mapping) else None
    counts = {
        "preprocess": len(preprocess_steps or []),
        "train": len(train_steps or []),
        "ensemble": len(ensemble_steps or []),
        "leaderboard": 1 if leaderboard_step else 0,
        "infer": 1 if infer_step else 0,
    }
    counts["total"] = sum(counts.values())
    return counts


def _format_limit_value(value: int) -> str:
    return "unlimited" if value <= 0 else str(value)


def _collect_project_examples(cfg: Any, plan: Mapping[str, Any]) -> dict[str, str]:
    examples: dict[str, str] = {}
    pipeline_project = _normalize_str(_cfg_value(cfg, "task.project_name"))
    if pipeline_project:
        examples["pipeline"] = pipeline_project
    steps = plan.get("steps") if isinstance(plan, Mapping) else None
    if not isinstance(steps, Mapping):
        return examples
    step_groups = [
        ("preprocess", "preprocess"),
        ("train", "train_model"),
        ("ensemble", "train_ensemble"),
        ("leaderboard", "leaderboard"),
        ("infer", "infer"),
    ]
    for step_key, label in step_groups:
        payload = steps.get(step_key)
        project_name = None
        if isinstance(payload, list) and payload:
            project_name = _normalize_str(payload[0].get("project_name"))
        elif isinstance(payload, Mapping):
            project_name = _normalize_str(payload.get("project_name"))
        if project_name:
            examples[label] = project_name
    return examples


def _format_plan_summary(cfg: Any, plan: Mapping[str, Any]) -> str:
    steps = plan.get("steps") if isinstance(plan, Mapping) else {}
    counts = plan.get("task_counts") if isinstance(plan, Mapping) else None
    if not isinstance(counts, Mapping):
        counts = _count_plan_tasks(steps if isinstance(steps, Mapping) else {})
    plan_info = plan.get("plan_info") if isinstance(plan, Mapping) else {}
    pipeline_limits = plan.get("pipeline_limits") if isinstance(plan, Mapping) else None
    if not isinstance(pipeline_limits, Mapping):
        pipeline_limits = _resolve_pipeline_limits(cfg)
    exec_limits = plan.get("limits") if isinstance(plan, Mapping) else None
    if not isinstance(exec_limits, Mapping):
        exec_limits = _resolve_exec_policy_limits(cfg)
    parallelism = plan.get("parallelism") if isinstance(plan, Mapping) else None
    if not isinstance(parallelism, Mapping):
        parallelism = _resolve_pipeline_parallelism(cfg)
    fail_policy = _resolve_fail_policy(cfg)
    project_examples = _collect_project_examples(cfg, plan)

    lines = [
        "Pipeline plan (dry-run)",
        (
            "tasks: preprocess={preprocess} train={train} ensemble={ensemble} "
            "leaderboard={leaderboard} infer={infer} total={total}"
        ).format(**counts),
        (
            "train jobs: planned={planned} raw={raw} skipped_due_to_policy={skipped}"
        ).format(
            planned=_to_int(plan_info.get("planned_jobs"), 0),
            raw=_to_int(plan_info.get("raw_jobs"), 0),
            skipped=_to_int(plan_info.get("skipped_due_to_policy"), 0),
        ),
        (
            "fail_policy: allow_skipped={allow_skipped} allowed_failures={allowed_failures} "
            "fail_fast={fail_fast} min_successful_train_tasks={min_success}"
        ).format(
            allow_skipped=str(bool(fail_policy.get("allow_skipped"))).lower(),
            allowed_failures=_to_int(fail_policy.get("allowed_failures"), 0),
            fail_fast=str(bool(fail_policy.get("fail_fast"))).lower(),
            min_success=_to_int(fail_policy.get("min_successful_train_tasks"), 0),
        ),
        (
            "pipeline limits: max_preprocess_variants={pre} max_train_tasks={train} "
            "max_ensemble_tasks={ensemble}"
        ).format(
            pre=_format_limit_value(_to_int(pipeline_limits.get("max_preprocess_variants"), 0)),
            train=_format_limit_value(_to_int(pipeline_limits.get("max_train_tasks"), 0)),
            ensemble=_format_limit_value(_to_int(pipeline_limits.get("max_ensemble_tasks"), 0)),
        ),
        (
            "exec_policy limits: max_jobs={jobs} max_models={models} max_hpo_trials={hpo_trials}"
        ).format(
            jobs=_format_limit_value(_to_int(exec_limits.get("max_jobs"), 0)),
            models=_format_limit_value(_to_int(exec_limits.get("max_models"), 0)),
            hpo_trials=_format_limit_value(_to_int(exec_limits.get("max_hpo_trials"), 0)),
        ),
        (
            "parallelism: max_concurrent_steps={steps} max_concurrent_train={train}"
        ).format(
            steps=_format_limit_value(_to_int(parallelism.get("max_concurrent_steps"), 0)),
            train=_format_limit_value(_to_int(parallelism.get("max_concurrent_train"), 0)),
        ),
    ]

    if project_examples:
        lines.append("project layout examples:")
        for key in ("pipeline", "preprocess", "train_model", "train_ensemble", "leaderboard", "infer"):
            if key in project_examples:
                lines.append(f"- {key}: {project_examples[key]}")
    return "\n".join(lines)


def _collect_limit_violations(cfg: Any, plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    steps = plan.get("steps") if isinstance(plan, Mapping) else {}
    counts = plan.get("task_counts") if isinstance(plan, Mapping) else None
    if not isinstance(counts, Mapping):
        counts = _count_plan_tasks(steps if isinstance(steps, Mapping) else {})
    limits = _resolve_pipeline_limits(cfg)
    violations: list[dict[str, Any]] = []

    preprocess_limit = _to_int(limits.get("max_preprocess_variants"), 0)
    preprocess_count = _to_int(counts.get("preprocess"), 0)
    if preprocess_limit > 0 and preprocess_count > preprocess_limit:
        violations.append(
            {
                "key": "pipeline.limits.max_preprocess_variants",
                "count": preprocess_count,
                "limit": preprocess_limit,
                "suggestions": [
                    "Reduce pipeline.grid.preprocess_variants or pipeline.groups.preprocess.custom.include/exclude",
                    "Set pipeline.groups.preprocess.mode=none or pipeline.run_preprocess=false for testing",
                    "Raise pipeline.limits.max_preprocess_variants temporarily (test only)",
                ],
            }
        )

    train_limit = _to_int(limits.get("max_train_tasks"), 0)
    train_count = _to_int(counts.get("train"), 0)
    if train_limit > 0 and train_count > train_limit:
        violations.append(
            {
                "key": "pipeline.limits.max_train_tasks",
                "count": train_count,
                "limit": train_limit,
                "suggestions": [
                    "Reduce pipeline.grid.model_variants / pipeline.model_set or pipeline.groups.train.custom.include/exclude",
                    "Reduce HPO grid (pipeline.hpo.enabled/params) or exec_policy.limits.max_jobs",
                    "Set pipeline.groups.train.mode=none or pipeline.run_train=false for testing",
                    "Raise pipeline.limits.max_train_tasks temporarily (test only)",
                ],
            }
        )

    ensemble_limit = _to_int(limits.get("max_ensemble_tasks"), 0)
    ensemble_count = _to_int(counts.get("ensemble"), 0)
    if ensemble_limit > 0 and ensemble_count > ensemble_limit:
        violations.append(
            {
                "key": "pipeline.limits.max_ensemble_tasks",
                "count": ensemble_count,
                "limit": ensemble_limit,
                "suggestions": [
                    "Disable ensemble.enabled or pipeline.groups.ensemble.mode=none",
                    "Reduce preprocess variants (pipeline.grid.preprocess_variants)",
                    "Raise pipeline.limits.max_ensemble_tasks temporarily (test only)",
                ],
            }
        )

    return violations


def _format_limit_violation_report(violations: list[dict[str, Any]]) -> str:
    if not violations:
        return ""
    sections: list[str] = ["Pipeline limits exceeded:"]
    for violation in violations:
        key = violation.get("key", "pipeline.limits")
        count = _to_int(violation.get("count"), 0)
        limit = _to_int(violation.get("limit"), 0)
        sections.append(f"- {key}: {count} > {limit}")
        for suggestion in violation.get("suggestions") or []:
            sections.append(f"  - {suggestion}")
    return "\n".join(sections)


def _apply_concurrency_limit(steps: list[dict[str, Any]], max_concurrent: int) -> None:
    if max_concurrent <= 0 or len(steps) <= max_concurrent:
        return
    for idx in range(max_concurrent, len(steps)):
        parent_step = steps[idx - max_concurrent]
        parent_name = _normalize_str(parent_step.get("step_name"))
        if not parent_name:
            continue
        current = steps[idx]
        parents = list(current.get("parents") or [])
        if parent_name not in parents:
            parents.append(parent_name)
            current["parents"] = parents


def _apply_parallelism_dependencies(
    plan: Mapping[str, Any],
    *,
    max_concurrent_steps: int,
    max_concurrent_train: int,
) -> None:
    steps = plan.get("steps") if isinstance(plan, Mapping) else None
    if not isinstance(steps, Mapping):
        return
    if max_concurrent_steps > 0:
        ordered: list[dict[str, Any]] = []
        ordered.extend(list(steps.get("preprocess") or []))
        ordered.extend(list(steps.get("train") or []))
        ordered.extend(list(steps.get("ensemble") or []))
        leaderboard_step = steps.get("leaderboard")
        if isinstance(leaderboard_step, Mapping):
            ordered.append(leaderboard_step)  # type: ignore[arg-type]
        infer_step = steps.get("infer")
        if isinstance(infer_step, Mapping):
            ordered.append(infer_step)  # type: ignore[arg-type]
        _apply_concurrency_limit(ordered, max_concurrent_steps)
    if max_concurrent_train > 0:
        _apply_concurrency_limit(list(steps.get("train") or []), max_concurrent_train)


def _serialize_pipeline_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    def _convert(value: Any) -> Any:
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Mapping):
            return {str(k): _convert(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_convert(v) for v in value]
        if isinstance(value, set):
            return [_convert(v) for v in sorted(value)]
        return value

    return _convert(plan) if isinstance(plan, Mapping) else {}


def _build_pipeline_plan(
    cfg: Any,
    grid_run_id: str,
    *,
    child_execution: str | None = None,
) -> dict[str, Any]:
    base_output_dir = Path(getattr(cfg.run, "output_dir", "outputs")).expanduser().resolve()
    pipeline_cfg = getattr(cfg, "pipeline", None)
    profile = _resolve_pipeline_profile(cfg)
    group_modes = {}
    if profile == "custom":
        group_modes = {
            "preprocess": _resolve_group_mode(cfg, "preprocess"),
            "train": _resolve_group_mode(cfg, "train"),
            "ensemble": _resolve_group_mode(cfg, "ensemble"),
            "leaderboard": _resolve_group_mode(cfg, "leaderboard"),
        }
    run_preprocess = bool(getattr(pipeline_cfg, "run_preprocess", True))
    run_train = bool(getattr(pipeline_cfg, "run_train", True))
    ensemble_cfg = getattr(cfg, "ensemble", None)
    run_ensemble = bool(getattr(ensemble_cfg, "enabled", False))
    run_leaderboard = bool(getattr(pipeline_cfg, "run_leaderboard", True))
    run_infer = bool(getattr(pipeline_cfg, "run_infer", False))
    if profile == "custom":
        run_preprocess = run_preprocess and group_modes.get("preprocess") != "none"
        run_train = run_train and group_modes.get("train") != "none"
        run_ensemble = run_ensemble and group_modes.get("ensemble") != "none"
        run_leaderboard = run_leaderboard and group_modes.get("leaderboard") != "none"

    raw_dataset_id = _normalize_str(_cfg_value(cfg, "data.raw_dataset_id"))
    dataset_path_value = _normalize_str(_cfg_value(cfg, "data.dataset_path"))
    run_dataset_register = bool(getattr(pipeline_cfg, "run_dataset_register", False))
    if run_dataset_register:
        raise ValueError("pipeline.run_dataset_register is not supported. Run dataset_register before pipeline.")
    if not raw_dataset_id:
        raise ValueError("data.raw_dataset_id is required for pipeline. Run dataset_register first.")
    if run_preprocess and raw_dataset_id and raw_dataset_id.startswith("local:") and not dataset_path_value:
        raise ValueError("data.dataset_path is required when data.raw_dataset_id is local.")

    group_info: dict[str, Any] = {}
    if profile == "custom":
        preprocess_variants, model_variants, group_info = _resolve_variants_v2(
            cfg, group_modes=group_modes
        )
    else:
        preprocess_variants, model_variants = _resolve_variants(cfg)
    hpo_enabled, hpo_trials_by_model, hpo_params_cfg = _resolve_hpo_trials(cfg, model_variants)
    base_extra_tags = _to_list(_cfg_value(cfg, "run.clearml.extra_tags"))
    limits = _resolve_exec_policy_limits(cfg)
    pipeline_limits = _resolve_pipeline_limits(cfg)
    parallelism = _resolve_pipeline_parallelism(cfg)
    max_jobs = limits["max_jobs"]
    max_models = limits["max_models"]
    max_hpo_trials = limits["max_hpo_trials"]
    plan_only = _resolve_plan_only(cfg)

    train_jobs: list[dict[str, Any]] = []
    plan_info = {"raw_jobs": 0, "planned_jobs": 0, "skipped_due_to_policy": 0}

    if run_train:
        if not preprocess_variants:
            raise ValueError("preprocess variants are empty.")
        if not model_variants:
            raise ValueError("model variants are empty.")
        train_jobs, plan_info, _ = _build_train_plan(
            preprocess_variants,
            model_variants,
            hpo_trials_by_model,
            max_jobs=max_jobs,
            max_hpo_trials=max_hpo_trials,
        )

    if run_preprocess and not preprocess_variants:
        raise ValueError("preprocess variants are empty.")

    if run_train and not run_preprocess:
        raise ValueError("pipeline.run_preprocess=false cannot be combined with run_train=true.")
    if run_ensemble and not run_train:
        raise ValueError("ensemble.enabled=true requires pipeline.run_train=true.")

    run_overrides = _collect_run_overrides(cfg, grid_run_id, child_execution=child_execution)
    data_overrides = _collect_data_overrides(cfg)
    if run_preprocess:
        downstream_data_overrides = _build_downstream_data_overrides(
            data_overrides, raw_dataset_id=raw_dataset_id
        )
    else:
        downstream_data_overrides = dict(data_overrides)
    eval_overrides = _collect_eval_overrides(cfg)

    preprocess_targets = preprocess_variants
    if run_train:
        preprocess_targets = []
        seen_preprocess: set[str] = set()
        for job in train_jobs:
            variant = str(job.get("preprocess_variant") or "")
            if not variant or variant in seen_preprocess:
                continue
            preprocess_targets.append(variant)
            seen_preprocess.add(variant)

    queues = _resolve_exec_policy_queues(cfg)
    steps = _build_plan_steps(
        cfg,
        base_output_dir=base_output_dir,
        grid_run_id=grid_run_id,
        run_preprocess=run_preprocess,
        run_train=run_train,
        run_ensemble=run_ensemble,
        run_leaderboard=run_leaderboard,
        run_infer=run_infer,
        preprocess_targets=preprocess_targets,
        train_jobs=train_jobs,
        base_extra_tags=base_extra_tags,
        max_models=max_models,
        queues=queues,
    )
    task_counts = _count_plan_tasks(steps)

    return {
        "base_output_dir": base_output_dir,
        "profile": profile,
        "groups": group_info,
        "run_dataset_register": False,
        "run_preprocess": run_preprocess,
        "run_train": run_train,
        "run_ensemble": run_ensemble,
        "run_leaderboard": run_leaderboard,
        "run_infer": run_infer,
        "preprocess_variants": preprocess_variants,
        "model_variants": model_variants,
        "hpo_enabled": hpo_enabled,
        "hpo_params_cfg": hpo_params_cfg,
        "limits": limits,
        "pipeline_limits": pipeline_limits,
        "parallelism": parallelism,
        "max_jobs": max_jobs,
        "max_models": max_models,
        "max_hpo_trials": max_hpo_trials,
        "plan_only": plan_only,
        "plan_info": plan_info,
        "train_jobs": train_jobs,
        "preprocess_targets": preprocess_targets,
        "run_overrides": run_overrides,
        "data_overrides": data_overrides,
        "downstream_data_overrides": downstream_data_overrides,
        "eval_overrides": eval_overrides,
        "base_extra_tags": base_extra_tags,
        "queues": queues,
        "steps": steps,
        "task_counts": task_counts,
    }


def _build_ref(*, run_dir: Path | None = None, task_id: str | None = None, **extras: Any) -> dict[str, Any]:
    ref: dict[str, Any] = {}
    if task_id:
        ref["task_id"] = str(task_id)
    if run_dir is not None:
        ref["run_dir"] = str(run_dir)
    for key, value in extras.items():
        if value is not None:
            ref[key] = value
    return ref


def _run_local_pipeline(
    cfg: Any,
    grid_run_id: str,
    *,
    clearml_enabled: bool,
    plan: Mapping[str, Any] | None = None,
    parent_task_id: str | None = None,
) -> dict[str, Any]:
    from ..pipeline.driver_local import run_local_sequential

    return run_local_sequential(
        cfg,
        grid_run_id,
        clearml_enabled=clearml_enabled,
        plan=plan,
        parent_task_id=parent_task_id,
    )


def _run_clearml_pipeline(
    cfg: Any,
    grid_run_id: str,
    *,
    controller_execution: str | None = None,
    plan: Mapping[str, Any] | None = None,
    controller: Any | None = None,
    parent_task_id: str | None = None,
) -> dict[str, Any]:
    from ..pipeline.driver_controller import run_pipeline_controller

    return run_pipeline_controller(
        cfg,
        grid_run_id,
        controller_execution=controller_execution,
        plan=plan,
        controller=controller,
        parent_task_id=parent_task_id,
    )


def _safe_load_json_optional(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _resolve_artifact_path(cfg: Any, ref: Mapping[str, Any] | None, name: str) -> Path | None:
    if not ref:
        return None
    run_dir = _normalize_str(ref.get("run_dir"))
    if run_dir:
        path = Path(run_dir) / name
        if path.exists():
            return path
    if is_clearml_enabled(cfg):
        task_id = _normalize_str(ref.get("task_id") or ref.get("train_task_id"))
        if task_id:
            try:
                return get_task_artifact_local_copy(cfg, task_id, name)
            except Exception:
                return None
    return None


def _resolve_entry_status(out: Mapping[str, Any] | None, ref: Mapping[str, Any] | None) -> str:
    if out:
        status = _normalize_str(out.get("status"))
        if status in ("skipped", "failed"):
            return status
        return "success"
    if ref:
        ref_status = _normalize_str(ref.get("status"))
        if ref_status in ("skipped", "failed", "success"):
            return ref_status
    return "failed"


def _artifact_ref(cfg: Any, ref: Mapping[str, Any] | None, artifact: str) -> dict[str, Any] | None:
    if not ref:
        return None
    run_dir = _normalize_str(ref.get("run_dir"))
    if run_dir:
        path = Path(run_dir) / artifact
        if path.exists():
            return {"run_dir": run_dir, "path": str(path)}
    task_id = _normalize_str(ref.get("task_id") or ref.get("train_task_id"))
    if task_id:
        return {"task_id": task_id, "artifact": artifact}
    return None


def _build_link_entry(
    cfg: Any | None,
    run_dir: str | None,
    task_id: str | None,
    *,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    entry: dict[str, Any] = {}
    if run_dir:
        entry["run_dir"] = str(run_dir)
    if task_id:
        entry["task_id"] = str(task_id)
        clearml_url = resolve_clearml_task_url(cfg, str(task_id)) if cfg is not None else None
        if clearml_url:
            entry["clearml_url"] = clearml_url
    if extra:
        entry.update(dict(extra))
    return entry or None


def _resolve_code_identity(cfg: Any) -> dict[str, Any]:
    repo_root = _resolve_repo_root()
    repo = None
    branch = None
    commit = None
    try:
        code_ref = build_clearml_code_ref(cfg, repo_root, mode_override="commit")
        repo = _normalize_str(code_ref.get("repository"))
        branch = _normalize_str(code_ref.get("branch"))
        commit = _normalize_str(code_ref.get("version_num"))
    except Exception:
        try:
            code_ref = build_clearml_code_ref(cfg, repo_root)
            repo = repo or _normalize_str(code_ref.get("repository"))
            branch = branch or _normalize_str(code_ref.get("branch"))
        except Exception:
            pass
    return {"repository": repo, "branch": branch, "commit": commit}


def _count_statuses(entries: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = {"total": len(entries), "success": 0, "failed": 0, "skipped": 0}
    for entry in entries:
        status = _normalize_str(entry.get("status"))
        if status == "success":
            counts["success"] += 1
        elif status == "skipped":
            counts["skipped"] += 1
        else:
            counts["failed"] += 1
    return counts


def _build_run_summary(
    pipeline_run: Mapping[str, Any],
    *,
    cfg: Any,
    report_bundle: Any | None,
    pipeline_run_dir: Path,
    pipeline_task_id: str | None,
) -> dict[str, Any]:
    fail_policy = _resolve_fail_policy(cfg)

    preprocess_entries: list[dict[str, Any]] = []
    for ref in pipeline_run.get("preprocess_ref") or []:
        if not isinstance(ref, Mapping):
            continue
        out = _safe_load_json_optional(_resolve_artifact_path(cfg, ref, "out.json"))
        status = _resolve_entry_status(out, ref)
        preprocess_entries.append(
            {
                "preprocess_variant": _normalize_str(ref.get("preprocess_variant")),
                "status": status,
                "processed_dataset_id": _normalize_str(
                    (out or {}).get("processed_dataset_id") or ref.get("processed_dataset_id")
                ),
                "split_hash": _normalize_str((out or {}).get("split_hash") or ref.get("split_hash")),
                "recipe_hash": _normalize_str((out or {}).get("recipe_hash") or ref.get("recipe_hash")),
                "task_id": _normalize_str(ref.get("task_id")),
                "run_dir": _normalize_str(ref.get("run_dir")),
                "reason": (out or {}).get("reason") or ref.get("reason"),
                "error": (out or {}).get("error") or ref.get("error"),
            }
        )

    train_entries: list[dict[str, Any]] = []
    for ref in pipeline_run.get("train_refs") or []:
        if not isinstance(ref, Mapping):
            continue
        out = _safe_load_json_optional(_resolve_artifact_path(cfg, ref, "out.json"))
        status = _resolve_entry_status(out, ref)
        train_task_id = _normalize_str(
            (out or {}).get("train_task_id") or ref.get("train_task_id") or ref.get("task_id")
        )
        train_entries.append(
            {
                "preprocess_variant": _normalize_str(ref.get("preprocess_variant")),
                "model_variant": _normalize_str(ref.get("model_variant")),
                "status": status,
                "train_task_id": train_task_id,
                "task_id": _normalize_str(ref.get("task_id")),
                "run_dir": _normalize_str(ref.get("run_dir")),
                "model_id": _normalize_str((out or {}).get("model_id") or ref.get("model_id")),
                "primary_metric": _normalize_str(
                    (out or {}).get("primary_metric") or ref.get("primary_metric")
                ),
                "best_score": (out or {}).get("best_score") or ref.get("best_score"),
                "metrics_ref": _artifact_ref(cfg, ref, "metrics.json"),
                "reason": (out or {}).get("reason") or ref.get("reason"),
                "error": (out or {}).get("error") or ref.get("error"),
                "hpo_run_id": ref.get("hpo_run_id"),
                "hpo_params": ref.get("hpo_params"),
            }
        )

    ensemble_entries: list[dict[str, Any]] = []
    for ref in pipeline_run.get("ensemble_refs") or []:
        if not isinstance(ref, Mapping):
            continue
        out = _safe_load_json_optional(_resolve_artifact_path(cfg, ref, "out.json"))
        status = _resolve_entry_status(out, ref)
        ensemble_entries.append(
            {
                "preprocess_variant": _normalize_str(
                    (out or {}).get("preprocess_variant") or ref.get("preprocess_variant")
                ),
                "method": _normalize_str((out or {}).get("ensemble_method") or ref.get("model_variant")),
                "status": status,
                "train_task_id": _normalize_str(
                    (out or {}).get("train_task_id") or ref.get("train_task_id") or ref.get("task_id")
                ),
                "task_id": _normalize_str(ref.get("task_id")),
                "run_dir": _normalize_str(ref.get("run_dir")),
                "model_id": _normalize_str((out or {}).get("model_id") or ref.get("model_id")),
                "primary_metric": _normalize_str(
                    (out or {}).get("primary_metric") or ref.get("primary_metric")
                ),
                "best_score": (out or {}).get("best_score") or ref.get("best_score"),
                "reason": (out or {}).get("reason") or ref.get("reason"),
                "error": (out or {}).get("error") or ref.get("error"),
            }
        )

    leaderboard_ref = pipeline_run.get("leaderboard_ref") if isinstance(pipeline_run, Mapping) else None
    leaderboard_entry: dict[str, Any] | None = None
    if isinstance(leaderboard_ref, Mapping):
        out = _safe_load_json_optional(_resolve_artifact_path(cfg, leaderboard_ref, "out.json")) or {}
        status = _resolve_entry_status(out, leaderboard_ref)
        leaderboard_entry = {
            "status": status,
            "task_id": _normalize_str(leaderboard_ref.get("task_id")),
            "run_dir": _normalize_str(leaderboard_ref.get("run_dir")),
            "leaderboard_ref": _artifact_ref(cfg, leaderboard_ref, "leaderboard.csv"),
            "recommendation_ref": _artifact_ref(cfg, leaderboard_ref, "recommendation.json"),
            "recommended_model_id": _normalize_str(out.get("recommended_model_id")),
            "recommended_primary_metric": _normalize_str(out.get("recommended_primary_metric")),
            "recommended_best_score": out.get("recommended_best_score"),
            "reason": out.get("reason") or leaderboard_ref.get("reason"),
            "error": out.get("error") or leaderboard_ref.get("error"),
        }

    infer_ref = pipeline_run.get("infer_ref") if isinstance(pipeline_run, Mapping) else None
    infer_entry: dict[str, Any] | None = None
    if isinstance(infer_ref, Mapping):
        out = _safe_load_json_optional(_resolve_artifact_path(cfg, infer_ref, "out.json"))
        status = _resolve_entry_status(out, infer_ref)
        infer_entry = {
            "status": status,
            "task_id": _normalize_str(infer_ref.get("task_id")),
            "run_dir": _normalize_str(infer_ref.get("run_dir")),
            "predictions_ref": _artifact_ref(cfg, infer_ref, "predictions.csv"),
            "reason": (out or {}).get("reason") or infer_ref.get("reason"),
            "error": (out or {}).get("error") or infer_ref.get("error"),
        }

    train_counts = _count_statuses(train_entries)
    preprocess_counts = _count_statuses(preprocess_entries)
    ensemble_counts = _count_statuses(ensemble_entries)

    planned_jobs = _to_int(pipeline_run.get("planned_jobs"), 0)
    effective_failures = train_counts["failed"]
    if not fail_policy.get("allow_skipped"):
        effective_failures += train_counts["skipped"]
    meets_min_success = train_counts["success"] >= int(fail_policy.get("min_successful_train_tasks", 0))
    if planned_jobs == 0:
        meets_min_success = True
    within_allowed = effective_failures <= int(fail_policy.get("allowed_failures", 0))
    limit_exceeded = bool(pipeline_run.get("limit_exceeded"))
    status = "success" if meets_min_success and within_allowed else "failed"
    if pipeline_run.get("plan_only"):
        status = "success"
    if limit_exceeded:
        status = "failed"

    degraded = False
    for counts in (preprocess_counts, train_counts, ensemble_counts):
        if counts["failed"] or counts["skipped"]:
            degraded = True
            break
    if limit_exceeded:
        degraded = True
    if leaderboard_entry and _normalize_str(leaderboard_entry.get("status")) in ("failed", "skipped"):
        degraded = True
    if infer_entry and _normalize_str(infer_entry.get("status")) in ("failed", "skipped"):
        degraded = True

    links = dict(getattr(report_bundle, "links", {}) or {}) if report_bundle is not None else {}
    ensemble_links: list[dict[str, Any]] = []
    for ref in pipeline_run.get("ensemble_refs") or []:
        if not isinstance(ref, Mapping):
            continue
        entry = _build_link_entry(
            cfg,
            _normalize_str(ref.get("run_dir")),
            _normalize_str(ref.get("task_id")),
            extra={"preprocess_variant": _normalize_str(ref.get("preprocess_variant"))},
        )
        if entry:
            ensemble_links.append(entry)
    if ensemble_links:
        links["ensemble"] = ensemble_links

    recommendation: dict[str, Any] = {}
    if report_bundle is not None and getattr(report_bundle, "payload", None):
        rec = report_bundle.payload.get("recommendation") or {}
        summary = report_bundle.payload.get("summary") or {}
        recommendation = {
            "best_model_id": _normalize_str(rec.get("model_id") or summary.get("recommended_model_id")),
            "train_task_ref": _normalize_str(rec.get("train_task_ref") or summary.get("train_task_ref")),
            "primary_metric": _normalize_str(rec.get("primary_metric") or summary.get("primary_metric")),
            "best_score": rec.get("best_score") or summary.get("best_score"),
            "reason": summary.get("recommendation_rationale"),
        }

    plan_ref = {"run_dir": str(pipeline_run_dir), "artifact": "plan.json"}
    pipeline_task_entry = _build_link_entry(
        cfg, str(pipeline_run_dir) if pipeline_run_dir else None, pipeline_task_id
    )

    execution = {
        "plan_only": bool(pipeline_run.get("plan_only")),
        "planned_jobs": pipeline_run.get("planned_jobs"),
        "executed_jobs": pipeline_run.get("executed_jobs"),
        "skipped_due_to_policy": pipeline_run.get("skipped_due_to_policy"),
        "limit_exceeded": limit_exceeded,
    }

    return {
        "schema_version": 1,
        "status": status,
        "degraded": degraded,
        "policy": {
            "fail_policy": dict(fail_policy),
            "result": {
                "successful_train_tasks": train_counts["success"],
                "failed_train_tasks": train_counts["failed"],
                "skipped_train_tasks": train_counts["skipped"],
                "effective_failures": effective_failures,
                "meets_min_successful_train_tasks": meets_min_success,
                "within_allowed_failures": within_allowed,
            },
        },
        "context": {
            "usecase_id": _normalize_str(_cfg_value(cfg, "run.usecase_id")),
            "project_root": _normalize_str(_cfg_value(cfg, "run.clearml.project_root")),
            "code_identity": _resolve_code_identity(cfg),
            "grid_run_id": pipeline_run.get("grid_run_id"),
            "pipeline_task": pipeline_task_entry,
        },
        "execution": execution,
        "plan_ref": plan_ref,
        "preprocess_variants": preprocess_entries,
        "train_tasks": train_entries,
        "ensemble_tasks": ensemble_entries,
        "leaderboard": leaderboard_entry,
        "infer": infer_entry,
        "recommendation": recommendation,
        "links": links,
    }


def run(cfg: Any) -> None:
    grid_run_id = _ensure_grid_run_id(cfg)
    identity = apply_clearml_identity(cfg, stage=cfg.task.stage)
    execution = _normalize_str(_cfg_value(cfg, "run.clearml.execution")) or "local"
    controller_execution = execution in ("pipeline_controller", "pipeline_controller_local")
    clearml_enabled = is_clearml_enabled(cfg)
    child_clearml_enabled = bool(_cfg_value(cfg, "run.clearml.enabled"))
    child_execution = "logging" if child_clearml_enabled else None
    plan = _build_pipeline_plan(cfg, grid_run_id, child_execution=child_execution)
    limit_violations = _collect_limit_violations(cfg, plan)
    limit_exceeded = bool(limit_violations and not plan.get("plan_only"))
    controller = None
    if controller_execution and clearml_enabled and not plan.get("plan_only") and not limit_exceeded:
        from ..clearml.templates import resolve_template_task_id

        pipeline_template_id = resolve_template_task_id(cfg, "pipeline")
        pipeline_name = _normalize_str(_cfg_value(cfg, "run.clearml.task_name")) or "pipeline"
        pipeline_project = _resolve_step_project_name(
            cfg, process_name="pipeline", train_project_per_preprocess=True
        )
        pipeline_queue = _select_queue(plan.get("queues") or {}, "pipeline")
        controller = create_pipeline_controller_from_template(
            cfg,
            base_task_id=pipeline_template_id,
            name=pipeline_name,
            project=pipeline_project,
            default_queue=pipeline_queue,
        )
    task_type = clearml_task_type_controller() if controller_execution else None
    system_tags = ["pipeline"] if controller_execution else None
    code_ref_override = None
    if controller_execution and resolve_clearml_code_ref_mode(cfg) == "commit":
        code_ref_override = "branch"
    ctx = init_task_context(
        cfg,
        stage=cfg.task.stage,
        task_name="pipeline",
        tags=identity.tags,
        properties=identity.user_properties,
        task_type=task_type,
        system_tags=system_tags,
        task_override=getattr(controller, "task", None) if controller is not None else None,
        code_ref_mode_override=code_ref_override,
    )
    save_config_resolved(ctx, cfg)
    parent_task_id = None
    if ctx.task is not None:
        task_id_value = getattr(ctx.task, "id", None)
        if task_id_value:
            parent_task_id = str(task_id_value)

    if execution in ("pipeline_controller", "pipeline_controller_local"):
        if not clearml_enabled:
            raise ValueError("pipeline_controller requires run.clearml.enabled=true.")
        pipeline_run = _run_clearml_pipeline(
            cfg,
            grid_run_id,
            controller_execution=execution,
            plan=plan,
            controller=controller,
            parent_task_id=parent_task_id,
        )
    elif execution in ("agent", "clone"):
        raise ValueError("pipeline does not support run.clearml.execution=agent/clone; use pipeline_controller.")
    else:
        pipeline_run = _run_local_pipeline(
            cfg,
            grid_run_id,
            clearml_enabled=child_clearml_enabled,
            plan=plan,
            parent_task_id=parent_task_id,
        )

    pipeline_run_path = ctx.output_dir / "pipeline_run.json"
    pipeline_run_path.write_text(
        json.dumps(pipeline_run, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    plan_path = None
    plan_payload = pipeline_run.get("plan") if isinstance(pipeline_run, Mapping) else None
    if isinstance(plan_payload, Mapping):
        plan_path = ctx.output_dir / "plan.json"
        plan_path.write_text(
            json.dumps(plan_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if clearml_enabled:
        upload_artifact(ctx, "pipeline_run.json", pipeline_run_path)
        if plan_path is not None:
            upload_artifact(ctx, "plan.json", plan_path)
        num_models = int(pipeline_run.get("planned_jobs") or 0)
        num_succeeded = int(pipeline_run.get("executed_jobs") or 0)
        num_failed = max(0, num_models - num_succeeded)
        if scalars_enabled(cfg):
            report_scalar(ctx.task, "pipeline", "num_models", num_models, iteration=0, cfg=cfg)
            report_scalar(
                ctx.task,
                "pipeline",
                "num_succeeded",
                num_succeeded,
                iteration=0,
                cfg=cfg,
            )
            report_scalar(ctx.task, "pipeline", "num_failed", num_failed, iteration=0, cfg=cfg)

    report_path = ctx.output_dir / "report.md"
    limits = _resolve_exec_policy_limits(cfg)
    report_max_models = limits["max_models"] if limits["max_models"] > 0 else 5
    pipeline_task_id = None
    if ctx.task is not None:
        task_id_value = getattr(ctx.task, "id", None)
        if task_id_value:
            pipeline_task_id = str(task_id_value)
    report_bundle = build_pipeline_report_bundle(
        pipeline_run,
        cfg=cfg,
        max_models=report_max_models,
        pipeline_run_dir=ctx.output_dir,
        pipeline_task_id=pipeline_task_id,
    )
    report_path.write_text(report_bundle.markdown, encoding="utf-8")
    report_json_path = ctx.output_dir / "report.json"
    report_json_path.write_text(
        json.dumps(report_bundle.payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report_links_path = ctx.output_dir / "report_links.json"
    report_links_path.write_text(
        json.dumps(report_bundle.links, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if clearml_enabled:
        upload_artifact(ctx, "report.md", report_path)
        upload_artifact(ctx, "report.json", report_json_path)
        upload_artifact(ctx, "report_links.json", report_links_path)
        report_markdown(ctx, title="Pipeline Report", markdown=report_bundle.markdown)

    run_summary = _build_run_summary(
        pipeline_run,
        cfg=cfg,
        report_bundle=report_bundle,
        pipeline_run_dir=ctx.output_dir,
        pipeline_task_id=pipeline_task_id,
    )
    run_summary_path = ctx.output_dir / "run_summary.json"
    run_summary_path.write_text(
        json.dumps(run_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if clearml_enabled:
        upload_artifact(ctx, "run_summary.json", run_summary_path)

    out = {"pipeline_run": pipeline_run}
    write_out_json(ctx, out)

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "pipeline",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "run_dataset_register": bool(getattr(getattr(cfg, "pipeline", None), "run_dataset_register", False)),
            "run_preprocess": bool(getattr(getattr(cfg, "pipeline", None), "run_preprocess", True)),
            "run_train": bool(getattr(getattr(cfg, "pipeline", None), "run_train", True)),
            "run_ensemble": bool(getattr(getattr(cfg, "ensemble", None), "enabled", False)),
            "run_leaderboard": bool(getattr(getattr(cfg, "pipeline", None), "run_leaderboard", True)),
            "run_infer": bool(getattr(getattr(cfg, "pipeline", None), "run_infer", False)),
            "plan_only": _resolve_plan_only(cfg),
        },
        "outputs": {
            "grid_run_id": grid_run_id,
            "pipeline_run_path": str(pipeline_run_path),
            "plan_path": str(plan_path) if plan_path is not None else None,
            "run_summary_path": str(run_summary_path),
        },
        "hashes": {
            "config_hash": hash_config(cfg),
            "split_hash": hash_split({}),
            "recipe_hash": hash_recipe({}),
        },
    }
    write_manifest(ctx, manifest)

    if run_summary.get("status") == "failed":
        raise RuntimeError("pipeline failed under fail_policy")
