"""pipeline process.

T009: grid execution + task_id handoff.
- dataset_register/preprocess/train/leaderboard/infer を独立タスクとして実行する接着剤
- grid_run_id を生成し、各タスクへ伝播させる
"""

from __future__ import annotations

import inspect
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Mapping
import uuid

from ..clearml.templates import resolve_template_task_id
from ..clearml.ui_logger import log_scalar
from ..platform_adapter import (
    apply_clearml_task_overrides,
    clearml_task_type_controller,
    create_pipeline_controller,
    hash_config,
    hash_recipe,
    hash_split,
    init_task_context,
    is_clearml_enabled,
    pipeline_require_clearml_agent,
    pipeline_step_task_id_ref,
    report_markdown,
    resolve_version_props,
    save_config_resolved,
    upload_artifact,
    write_manifest,
    write_out_json,
)
from ..ops.clearml_identity import apply_clearml_identity, build_project_name
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


def _resolve_exec_policy_selection(cfg: Any) -> dict[str, bool]:
    selection_cfg = _to_mapping(_cfg_value(cfg, "exec_policy.selection"))
    selection: dict[str, bool] = {}
    for key in ("calibration", "uncertainty", "ci"):
        if key in selection_cfg:
            selection[key] = bool(selection_cfg.get(key))
    return selection


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


def _resolve_ensemble_methods(cfg: Any) -> list[str]:
    methods = [_normalize_str(item) for item in _to_list(_cfg_value(cfg, "ensemble.methods"))]
    methods = [item for item in methods if item]
    if methods:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in methods:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered
    method = _normalize_str(_cfg_value(cfg, "ensemble.method")) or "mean_topk"
    return [method]


def _collect_ensemble_overrides(cfg: Any) -> dict[str, Any]:
    ensemble_cfg = getattr(cfg, "ensemble", None)
    overrides: dict[str, Any] = {}
    if ensemble_cfg is None:
        return overrides
    for key in ("top_k", "selection_metric", "exclude_variants", "fallback_rerun_predict"):
        value = getattr(ensemble_cfg, key, None)
        if value is not None:
            overrides[f"ensemble.{key}"] = list(value) if key == "exclude_variants" else value
    weighted_cfg = getattr(ensemble_cfg, "weighted", None)
    if weighted_cfg is not None:
        for key in ("search", "n_samples", "seed", "top_k_max"):
            value = getattr(weighted_cfg, key, None)
            if value is not None:
                overrides[f"ensemble.weighted.{key}"] = value
    stacking_cfg = getattr(ensemble_cfg, "stacking", None)
    if stacking_cfg is not None:
        for key in ("meta_model", "cv_folds", "seed", "require_test_split"):
            value = getattr(stacking_cfg, key, None)
            if value is not None:
                overrides[f"ensemble.stacking.{key}"] = value
    return overrides


def _build_run_root(base_output_dir: Path, grid_run_id: str, name: str) -> Path:
    safe_name = _sanitize_component(name)
    return base_output_dir / "grid" / str(grid_run_id) / safe_name


def _stage_dir(run_root: Path, task_name: str) -> Path:
    stage = _STAGE_BY_TASK[task_name]
    return run_root / stage


def _clearml_project(cfg: Any, stage: str) -> str:
    project_root = _normalize_str(_cfg_value(cfg, "run.clearml.project_root")) or "MFG"
    usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id")) or "unknown"
    return build_project_name(project_root, usecase_id, stage, cfg=cfg)


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
    # Avoid child tasks inheriting the parent ClearML task in logging mode.
    env.pop("CLEARML_TASK_ID", None)
    env.pop("TRAINS_TASK_ID", None)
    env.pop("CLEARML_PROC_MASTER_ID", None)
    env.pop("TRAINS_PROC_MASTER_ID", None)
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


def _build_plan_steps(
    cfg: Any,
    *,
    base_output_dir: Path,
    grid_run_id: str,
    run_dataset_register: bool,
    run_preprocess: bool,
    run_train: bool,
    run_train_ensemble: bool,
    run_leaderboard: bool,
    run_infer: bool,
    preprocess_targets: list[str],
    train_jobs: list[dict[str, Any]],
    base_extra_tags: list[str],
    max_models: int,
    queues: Mapping[str, Any],
    ensemble_methods: list[str],
    ensemble_overrides: Mapping[str, Any],
) -> dict[str, Any]:
    dataset_step = None
    preprocess_steps: list[dict[str, Any]] = []
    preprocess_by_variant: dict[str, dict[str, Any]] = {}
    train_steps: list[dict[str, Any]] = []
    train_ensemble_steps: list[dict[str, Any]] = []
    leaderboard_step = None
    infer_step = None

    if run_dataset_register:
        run_root = _build_run_root(base_output_dir, grid_run_id, "dataset_register")
        step_queue = _select_queue(queues, "dataset_register")
        overrides = {"run.output_dir": str(run_root)}
        if step_queue:
            overrides["run.clearml.queue_name"] = step_queue
        dataset_step = {
            "step_name": "dataset_register",
            "task_name": "dataset_register",
            "run_root": run_root,
            "run_dir": _stage_dir(run_root, "dataset_register"),
            "parents": [],
            "queue": step_queue,
            "overrides": overrides,
        }

    if run_preprocess:
        if not preprocess_targets:
            raise ValueError("pipeline.grid.preprocess_variants is empty.")
        for preprocess_variant in preprocess_targets:
            step_name = f"preprocess__{_sanitize_component(preprocess_variant)}"
            run_root = _build_run_root(base_output_dir, grid_run_id, f"preprocess__{preprocess_variant}")
            parents = [dataset_step["step_name"]] if dataset_step else []
            overrides = {
                "group/preprocess": preprocess_variant,
                "run.output_dir": str(run_root),
            }
            step_queue = _select_queue(queues, "preprocess")
            if step_queue:
                overrides["run.clearml.queue_name"] = step_queue
            step = {
                "step_name": step_name,
                "task_name": "preprocess",
                "run_root": run_root,
                "run_dir": _stage_dir(run_root, "preprocess"),
                "parents": parents,
                "queue": step_queue,
                "overrides": overrides,
                "preprocess_variant": preprocess_variant,
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
                "+preprocess.variant": preprocess_variant,
                "train.inputs.preprocess_run_dir": str(preprocess_run_dir),
                "run.output_dir": str(run_root),
            }
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
                }
            )

    if run_train_ensemble:
        if not preprocess_by_variant:
            raise ValueError("preprocess outputs are required before train_ensemble.")
        by_variant: dict[str, list[dict[str, Any]]] = {}
        for step in train_steps:
            variant = str(step.get("preprocess_variant") or "")
            if not variant:
                continue
            by_variant.setdefault(variant, []).append(step)
        methods = ensemble_methods or ["mean_topk"]
        for preprocess_variant, parent_steps in by_variant.items():
            for method in methods:
                method_key = _sanitize_component(method)
                step_name = f"ensemble__{_sanitize_component(preprocess_variant)}__{method_key}"
                run_root = _build_run_root(
                    base_output_dir,
                    grid_run_id,
                    f"ensemble__{preprocess_variant}__{method}",
                )
                overrides = {
                    "run.output_dir": str(run_root),
                    "+preprocess.variant": preprocess_variant,
                    "group/preprocess": preprocess_variant,
                    "ensemble.enabled": True,
                    "ensemble.method": method,
                }
                overrides.update(ensemble_overrides)
                step_queue = _select_queue(queues, "train_ensemble")
                if step_queue:
                    overrides["run.clearml.queue_name"] = step_queue
                train_ensemble_steps.append(
                    {
                        "step_name": step_name,
                        "task_name": "train_ensemble",
                        "run_root": run_root,
                        "run_dir": _stage_dir(run_root, "train_ensemble"),
                        "parents": [step["step_name"] for step in parent_steps],
                        "queue": step_queue,
                        "overrides": overrides,
                        "preprocess_variant": preprocess_variant,
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
        leaderboard_step = {
            "step_name": "leaderboard",
            "task_name": "leaderboard",
            "run_root": run_root,
            "run_dir": _stage_dir(run_root, "leaderboard"),
            "parents": [
                *[step["step_name"] for step in train_steps],
                *[step["step_name"] for step in train_ensemble_steps],
            ],
            "queue": step_queue,
            "overrides": overrides,
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
        infer_step = {
            "step_name": "infer",
            "task_name": "infer",
            "run_root": run_root,
            "run_dir": _stage_dir(run_root, "infer"),
            "parents": parents,
            "queue": step_queue,
            "overrides": overrides,
        }

    return {
        "dataset_register": dataset_step,
        "preprocess": preprocess_steps,
        "train": train_steps,
        "train_ensemble": train_ensemble_steps,
        "leaderboard": leaderboard_step,
        "infer": infer_step,
    }


def _build_pipeline_plan(
    cfg: Any,
    grid_run_id: str,
    *,
    child_execution: str | None = None,
) -> dict[str, Any]:
    base_output_dir = Path(getattr(cfg.run, "output_dir", "outputs")).expanduser().resolve()
    pipeline_cfg = getattr(cfg, "pipeline", None)
    run_dataset_register = bool(getattr(pipeline_cfg, "run_dataset_register", False))
    run_preprocess = bool(getattr(pipeline_cfg, "run_preprocess", True))
    run_train = bool(getattr(pipeline_cfg, "run_train", True))
    run_train_ensemble = bool(
        getattr(pipeline_cfg, "run_train_ensemble", _cfg_value(cfg, "ensemble.enabled", False))
    )
    run_leaderboard = bool(getattr(pipeline_cfg, "run_leaderboard", True))
    run_infer = bool(getattr(pipeline_cfg, "run_infer", False))

    raw_dataset_id = _normalize_str(_cfg_value(cfg, "data.raw_dataset_id"))
    dataset_path_value = _normalize_str(_cfg_value(cfg, "data.dataset_path"))
    if run_preprocess and not run_dataset_register and not raw_dataset_id:
        raise ValueError(
            "data.raw_dataset_id is required when pipeline.run_dataset_register is false."
        )
    if run_preprocess and raw_dataset_id and raw_dataset_id.startswith("local:") and not dataset_path_value:
        raise ValueError("data.dataset_path is required when data.raw_dataset_id is local.")

    preprocess_variants, model_variants = _resolve_variants(cfg)
    hpo_enabled, hpo_trials_by_model, hpo_params_cfg = _resolve_hpo_trials(cfg, model_variants)
    base_extra_tags = _to_list(_cfg_value(cfg, "run.clearml.extra_tags"))
    limits = _resolve_exec_policy_limits(cfg)
    max_jobs = limits["max_jobs"]
    max_models = limits["max_models"]
    max_hpo_trials = limits["max_hpo_trials"]
    plan_only = _resolve_plan_only(cfg)

    train_jobs: list[dict[str, Any]] = []
    plan_info = {"raw_jobs": 0, "planned_jobs": 0, "skipped_due_to_policy": 0}

    if run_train:
        if not preprocess_variants:
            raise ValueError("pipeline.grid.preprocess_variants is empty.")
        if not model_variants:
            raise ValueError("pipeline.grid.model_variants is empty.")
        train_jobs, plan_info, _ = _build_train_plan(
            preprocess_variants,
            model_variants,
            hpo_trials_by_model,
            max_jobs=max_jobs,
            max_hpo_trials=max_hpo_trials,
        )

    if run_preprocess and not preprocess_variants:
        raise ValueError("pipeline.grid.preprocess_variants is empty.")

    if run_train and not run_preprocess:
        raise ValueError("pipeline.run_preprocess=false cannot be combined with run_train=true.")
    if run_train_ensemble and not run_train:
        raise ValueError("pipeline.run_train_ensemble=true requires run_train=true.")

    run_overrides = _collect_run_overrides(cfg, grid_run_id, child_execution=child_execution)
    data_overrides = _collect_data_overrides(cfg)
    if run_preprocess:
        downstream_data_overrides = _build_downstream_data_overrides(
            data_overrides, raw_dataset_id=raw_dataset_id
        )
    else:
        downstream_data_overrides = dict(data_overrides)
    eval_overrides = _collect_eval_overrides(cfg)
    ensemble_methods = _resolve_ensemble_methods(cfg)
    ensemble_overrides = _collect_ensemble_overrides(cfg)

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
        run_dataset_register=run_dataset_register,
        run_preprocess=run_preprocess,
        run_train=run_train,
        run_train_ensemble=run_train_ensemble,
        run_leaderboard=run_leaderboard,
        run_infer=run_infer,
        preprocess_targets=preprocess_targets,
        train_jobs=train_jobs,
        base_extra_tags=base_extra_tags,
        max_models=max_models,
        queues=queues,
        ensemble_methods=ensemble_methods,
        ensemble_overrides=ensemble_overrides,
    )

    return {
        "base_output_dir": base_output_dir,
        "run_dataset_register": run_dataset_register,
        "run_preprocess": run_preprocess,
        "run_train": run_train,
        "run_train_ensemble": run_train_ensemble,
        "run_leaderboard": run_leaderboard,
        "run_infer": run_infer,
        "preprocess_variants": preprocess_variants,
        "model_variants": model_variants,
        "hpo_enabled": hpo_enabled,
        "hpo_params_cfg": hpo_params_cfg,
        "limits": limits,
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
    }


def _collect_step_task_ids(controller: Any) -> dict[str, str]:
    getter = getattr(controller, "get_processed_nodes", None)
    nodes = getter() if callable(getter) else {}
    payload: dict[str, str] = {}
    for name, node in dict(nodes).items():
        task_id = getattr(node, "executed", None)
        if not task_id and getattr(node, "job", None):
            job = node.job
            if hasattr(job, "task_id"):
                task_id = job.task_id() if callable(job.task_id) else job.task_id
        if task_id:
            payload[str(name)] = str(task_id)
    return payload


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


def _add_pipeline_step(
    controller: Any,
    *,
    execution_queue: str | None = None,
    **kwargs: Any,
) -> None:
    add_step = getattr(controller, "add_step", None)
    if not callable(add_step):
        raise AttributeError("Pipeline controller does not support add_step.")
    if execution_queue:
        try:
            signature = inspect.signature(add_step)
        except Exception:
            signature = None
        if signature is not None and "execution_queue" in signature.parameters:
            kwargs["execution_queue"] = execution_queue
    add_step(**kwargs)


def _run_local_pipeline(cfg: Any, grid_run_id: str, *, clearml_enabled: bool) -> dict[str, Any]:
    plan = _build_pipeline_plan(cfg, grid_run_id)
    repo_root = _resolve_repo_root()
    config_dir = repo_root / "conf"
    run_overrides = dict(plan["run_overrides"])
    data_overrides = dict(plan["data_overrides"])
    downstream_data_overrides = dict(plan["downstream_data_overrides"])
    eval_overrides = plan["eval_overrides"]
    steps = plan["steps"]

    dataset_register_ref: dict[str, Any] | None = None
    preprocess_refs: list[dict[str, Any]] = []
    train_refs: list[dict[str, Any]] = []
    train_ensemble_refs: list[dict[str, Any]] = []
    leaderboard_ref: dict[str, Any] | None = None
    infer_ref: dict[str, Any] | None = None

    executed_jobs = 0
    leaderboard_out: dict[str, Any] | None = None
    if not plan["plan_only"]:
        if plan["run_dataset_register"]:
            step = steps["dataset_register"]
            if step is None:
                raise ValueError("dataset_register step is missing.")
            overrides = _merge_overrides(run_overrides, data_overrides, step["overrides"])
            args = ["task=dataset_register", *_overrides_to_args(overrides)]
            _run_cli_task(args, cwd=repo_root, config_dir=config_dir)
            dataset_register_ref = _build_ref(run_dir=step["run_dir"])
            dataset_out = _load_json(step["run_dir"] / "out.json")
            raw_dataset_id = _normalize_str(dataset_out.get("raw_dataset_id"))
            if raw_dataset_id:
                data_overrides["data.raw_dataset_id"] = raw_dataset_id
                if plan["run_preprocess"]:
                    downstream_data_overrides = _build_downstream_data_overrides(
                        data_overrides, raw_dataset_id=raw_dataset_id
                    )

        preprocess_outputs: dict[str, dict[str, Any]] = {}
        if plan["run_preprocess"]:
            for step in steps["preprocess"]:
                preprocess_variant = step.get("preprocess_variant")
                overrides = _merge_overrides(run_overrides, downstream_data_overrides, step["overrides"])
                args = ["task=preprocess", *_overrides_to_args(overrides)]
                _run_cli_task(args, cwd=repo_root, config_dir=config_dir)
                out = _load_json(step["run_dir"] / "out.json")
                preprocess_refs.append(
                    _build_ref(
                        run_dir=step["run_dir"],
                        preprocess_variant=preprocess_variant,
                        processed_dataset_id=out.get("processed_dataset_id"),
                        split_hash=out.get("split_hash"),
                        recipe_hash=out.get("recipe_hash"),
                    )
                )
                preprocess_outputs[str(preprocess_variant)] = {"run_dir": step["run_dir"], "out": out}

        if plan["run_train"]:
            if not preprocess_outputs:
                raise ValueError("preprocess outputs are required before train.")
            for step in steps["train"]:
                preprocess_variant = step.get("preprocess_variant")
                payload = preprocess_outputs.get(str(preprocess_variant))
                if payload is None:
                    raise ValueError(f"preprocess output missing for {preprocess_variant}.")
                preprocess_out = payload["out"]
                processed_dataset_id = _normalize_str(preprocess_out.get("processed_dataset_id"))
                overrides = _merge_overrides(
                    run_overrides,
                    downstream_data_overrides,
                    eval_overrides,
                    step["overrides"],
                )
                if processed_dataset_id:
                    overrides["data.processed_dataset_id"] = processed_dataset_id
                args = ["task=train_model", *_overrides_to_args(overrides)]
                _run_cli_task(args, cwd=repo_root, config_dir=config_dir)
                out = _load_json(step["run_dir"] / "out.json")
                train_refs.append(
                    _build_ref(
                        run_dir=step["run_dir"],
                        preprocess_variant=preprocess_variant,
                        model_variant=step.get("model_variant"),
                        train_task_id=out.get("train_task_id"),
                        model_id=out.get("model_id"),
                        best_score=out.get("best_score"),
                        primary_metric=out.get("primary_metric"),
                        hpo_run_id=step.get("hpo_run_id"),
                        hpo_params=step.get("hpo_params"),
                    )
                )
            executed_jobs = len(train_refs)

        if plan["run_train_ensemble"]:
            if not train_refs:
                raise ValueError("train outputs are required before train_ensemble.")
            for step in steps["train_ensemble"]:
                overrides = _merge_overrides(
                    run_overrides,
                    downstream_data_overrides,
                    eval_overrides,
                    step["overrides"],
                )
                args = ["task=train_ensemble", *_overrides_to_args(overrides)]
                _run_cli_task(args, cwd=repo_root, config_dir=config_dir)
                out = _load_json(step["run_dir"] / "out.json")
                train_ensemble_refs.append(
                    _build_ref(
                        run_dir=step["run_dir"],
                        preprocess_variant=step.get("preprocess_variant"),
                        train_task_id=out.get("train_task_id"),
                        model_id=out.get("model_id"),
                        best_score=out.get("best_score"),
                        primary_metric=out.get("primary_metric"),
                        task_type=out.get("task_type"),
                    )
                )

        if plan["run_leaderboard"]:
            if not train_refs and not train_ensemble_refs:
                raise ValueError("train outputs are required before leaderboard.")
            step = steps["leaderboard"]
            if step is None:
                raise ValueError("leaderboard step is missing.")
            overrides = _merge_overrides(run_overrides, eval_overrides, step["overrides"])
            if clearml_enabled:
                train_task_ids = [
                    ref.get("train_task_id") for ref in train_refs if ref.get("train_task_id")
                ]
                train_task_ids.extend(
                    [ref.get("train_task_id") for ref in train_ensemble_refs if ref.get("train_task_id")]
                )
                if not train_task_ids:
                    raise ValueError("train_task_id is missing in train outputs (ClearML mode).")
                overrides["leaderboard.train_task_ids"] = train_task_ids
            else:
                train_run_dirs = [ref.get("run_dir") for ref in train_refs if ref.get("run_dir")]
                train_run_dirs.extend(
                    [ref.get("run_dir") for ref in train_ensemble_refs if ref.get("run_dir")]
                )
                overrides["leaderboard.train_run_dirs"] = train_run_dirs
            args = ["task=leaderboard", *_overrides_to_args(overrides)]
            _run_cli_task(args, cwd=repo_root, config_dir=config_dir)
            leaderboard_out = _load_json(step["run_dir"] / "out.json")
            leaderboard_ref = _build_ref(run_dir=step["run_dir"])

        if plan["run_infer"]:
            step = steps["infer"]
            if step is None:
                raise ValueError("infer step is missing.")
            infer_cfg = getattr(cfg, "infer", None)
            overrides = _merge_overrides(run_overrides, step["overrides"])
            if clearml_enabled:
                train_task_id = None
                if leaderboard_out is not None:
                    train_task_id = _normalize_str(leaderboard_out.get("recommended_train_task_id"))
                train_task_id = train_task_id or _normalize_str(getattr(infer_cfg, "train_task_id", None))
                model_id = _normalize_str(getattr(infer_cfg, "model_id", None))
                if train_task_id:
                    overrides["infer.train_task_id"] = train_task_id
                elif model_id:
                    overrides["infer.model_id"] = model_id
                else:
                    raise ValueError("infer requires train_task_id or model_id in ClearML mode.")
            else:
                model_id = None
                train_task_ref = None
                if leaderboard_out is not None:
                    model_id = _normalize_str(leaderboard_out.get("recommended_model_id"))
                    train_task_ref = _normalize_str(leaderboard_out.get("recommended_train_task_ref"))
                if model_id:
                    overrides["infer.model_id"] = model_id
                elif train_task_ref:
                    overrides["infer.train_task_id"] = train_task_ref
                else:
                    fallback_model = _normalize_str(getattr(infer_cfg, "model_id", None))
                    fallback_task = _normalize_str(getattr(infer_cfg, "train_task_id", None))
                    if fallback_model:
                        overrides["infer.model_id"] = fallback_model
                    elif fallback_task:
                        overrides["infer.train_task_id"] = fallback_task
                    else:
                        raise ValueError("infer requires model_id or train_task_id.")
            args = ["task=infer", *_overrides_to_args(overrides)]
            _run_cli_task(args, cwd=repo_root, config_dir=config_dir)
            infer_ref = _build_ref(run_dir=step["run_dir"])

    pipeline_run = {
        "grid_run_id": grid_run_id,
        "plan_only": plan["plan_only"],
        "planned_jobs": int(plan["plan_info"].get("planned_jobs", 0)),
        "executed_jobs": int(executed_jobs),
        "skipped_due_to_policy": int(plan["plan_info"].get("skipped_due_to_policy", 0)),
        "dataset_register_ref": dataset_register_ref,
        "preprocess_ref": preprocess_refs,
        "train_refs": train_refs,
        "train_ensemble_refs": train_ensemble_refs,
        "leaderboard_ref": leaderboard_ref,
        "infer_ref": infer_ref,
        "grid": {
            "preprocess_variants": plan["preprocess_variants"],
            "model_variants": plan["model_variants"],
            "max_jobs": plan["max_jobs"],
            "max_hpo_trials": plan["max_hpo_trials"],
            "hpo": {
                "enabled": plan["hpo_enabled"],
                "params": plan["hpo_params_cfg"],
            },
        },
        "policy": {
            "limits": dict(plan["limits"]),
            "selection": _resolve_exec_policy_selection(cfg),
        },
    }
    return pipeline_run


def _run_clearml_pipeline(
    cfg: Any,
    grid_run_id: str,
    *,
    use_templates: bool,
    controller_execution: str | None = None,
    pipeline_task_id: str | None = None,
) -> dict[str, Any]:
    child_execution = "logging" if use_templates else None
    controller_execution = _normalize_str(controller_execution) or ""
    run_controller_locally = controller_execution != "pipeline_controller"
    plan = _build_pipeline_plan(cfg, grid_run_id, child_execution=child_execution)
    run_overrides = plan["run_overrides"]
    if pipeline_task_id:
        run_overrides["run.clearml.pipeline_task_id"] = pipeline_task_id
    data_overrides = plan["data_overrides"]
    downstream_data_overrides = plan["downstream_data_overrides"]
    eval_overrides = plan["eval_overrides"]
    queues = plan["queues"]
    steps = plan["steps"]

    step_task_ids: dict[str, str] = {}
    executed_jobs = 0

    if not plan["plan_only"]:
        pipeline_queue = _select_queue(queues, "pipeline")
        queue_candidates = [
            pipeline_queue,
            _select_queue(queues, "dataset_register"),
            _select_queue(queues, "preprocess"),
            _select_queue(queues, "train_model"),
            _select_queue(queues, "train_ensemble"),
            _normalize_str(queues.get("train_model_heavy")),
            _select_queue(queues, "leaderboard"),
            _select_queue(queues, "infer"),
        ]
        queue_name = next((value for value in queue_candidates if value), None)
        if not queue_name:
            model_variant_queues = queues.get("model_variants") or {}
            for value in model_variant_queues.values():
                value = _normalize_str(value)
                if value:
                    queue_name = value
                    break

        pipeline_name = _normalize_str(_cfg_value(cfg, "run.clearml.task_name")) or "pipeline"
        controller = create_pipeline_controller(cfg, name=pipeline_name, default_queue=pipeline_queue)
        controller_overrides = _hydra_task_overrides()
        if controller_overrides:
            _ensure_override(controller_overrides, "task", "pipeline")
            _ensure_override(controller_overrides, "run.grid_run_id", grid_run_id)
            _ensure_override(controller_overrides, "run.output_dir", _cfg_value(cfg, "run.output_dir"))
            _ensure_override(controller_overrides, "run.clearml.enabled", True)
            _ensure_override(
                controller_overrides,
                "run.clearml.execution",
                controller_execution or _cfg_value(cfg, "run.clearml.execution"),
            )
            _ensure_override(
                controller_overrides,
                "pipeline.run_dataset_register",
                plan.get("run_dataset_register"),
            )
            _ensure_override(controller_overrides, "pipeline.run_preprocess", plan.get("run_preprocess"))
            _ensure_override(controller_overrides, "pipeline.run_train", plan.get("run_train"))
            _ensure_override(
                controller_overrides,
                "pipeline.run_train_ensemble",
                plan.get("run_train_ensemble"),
            )
            _ensure_override(controller_overrides, "pipeline.run_leaderboard", plan.get("run_leaderboard"))
            _ensure_override(controller_overrides, "pipeline.run_infer", plan.get("run_infer"))
            _ensure_override(
                controller_overrides,
                "pipeline.grid.preprocess_variants",
                plan.get("preprocess_variants"),
            )
            _ensure_override(
                controller_overrides,
                "pipeline.grid.model_variants",
                plan.get("model_variants"),
            )
            _ensure_override(controller_overrides, "data.dataset_path", _cfg_value(cfg, "data.dataset_path"))
            _ensure_override(controller_overrides, "data.target_column", _cfg_value(cfg, "data.target_column"))
            _ensure_override(controller_overrides, "data.raw_dataset_id", _cfg_value(cfg, "data.raw_dataset_id"))
            _ensure_override(controller_overrides, "run.usecase_id", _cfg_value(cfg, "run.usecase_id"))
        else:
            controller_overrides_map = _merge_overrides(
                _collect_run_overrides(cfg, grid_run_id, child_execution=None),
                _collect_data_overrides(cfg),
                _collect_eval_overrides(cfg),
                {
                    "task": "pipeline",
                    "run.output_dir": _cfg_value(cfg, "run.output_dir"),
                    "pipeline.run_dataset_register": plan.get("run_dataset_register"),
                    "pipeline.run_preprocess": plan.get("run_preprocess"),
                    "pipeline.run_train": plan.get("run_train"),
                    "pipeline.run_train_ensemble": plan.get("run_train_ensemble"),
                    "pipeline.run_leaderboard": plan.get("run_leaderboard"),
                    "pipeline.run_infer": plan.get("run_infer"),
                    "pipeline.grid.preprocess_variants": plan.get("preprocess_variants"),
                    "pipeline.grid.model_variants": plan.get("model_variants"),
                },
            )
            controller_overrides = _overrides_to_args(controller_overrides_map)
        if controller_overrides:
            apply_clearml_task_overrides(controller, controller_overrides)
        pipeline_require_clearml_agent(queue_name)

        template_task_ids: dict[str, str] = {}

        def _base_task_kwargs(task_name: str) -> dict[str, Any]:
            if not use_templates:
                return {
                    "base_task_project": _clearml_project(cfg, _STAGE_BY_TASK[task_name]),
                    "base_task_name": task_name,
                }
            task_id = template_task_ids.get(task_name)
            if not task_id:
                task_id = resolve_template_task_id(cfg, task_name)
                template_task_ids[task_name] = task_id
            return {"base_task_id": task_id}

        if plan["run_dataset_register"]:
            step = steps["dataset_register"]
            if step is None:
                raise ValueError("dataset_register step is missing.")
            dataset_step_name = step["step_name"]
            overrides = _merge_overrides(run_overrides, data_overrides, step["overrides"])
            _add_pipeline_step(
                controller,
                name=step["step_name"],
                parents=step["parents"],
                parameter_override={f"Args/{k}": v for k, v in _overrides_to_params(overrides).items()},
                clone_base_task=True,
                cache_executed_step=False,
                execution_queue=step["queue"],
                **_base_task_kwargs(step["task_name"]),
            )

        if plan["run_preprocess"]:
            for step in steps["preprocess"]:
                overrides = _merge_overrides(run_overrides, downstream_data_overrides, step["overrides"])
                _add_pipeline_step(
                    controller,
                    name=step["step_name"],
                    parents=step["parents"],
                    parameter_override={f"Args/{k}": v for k, v in _overrides_to_params(overrides).items()},
                    clone_base_task=True,
                    cache_executed_step=False,
                    execution_queue=step["queue"],
                    **_base_task_kwargs(step["task_name"]),
                )

        if plan["run_train"]:
            if not steps["train"]:
                raise ValueError("preprocess outputs are required before train.")
            for step in steps["train"]:
                overrides = _merge_overrides(
                    run_overrides,
                    downstream_data_overrides,
                    eval_overrides,
                    step["overrides"],
                )
                parents = step.get("parents") or []
                if parents:
                    overrides["train.inputs.preprocess_task_id"] = pipeline_step_task_id_ref(
                        str(parents[0])
                    )
                _add_pipeline_step(
                    controller,
                    name=step["step_name"],
                    parents=step["parents"],
                    parameter_override={f"Args/{k}": v for k, v in _overrides_to_params(overrides).items()},
                    clone_base_task=True,
                    cache_executed_step=False,
                    execution_queue=step["queue"],
                    **_base_task_kwargs(step["task_name"]),
                )

        if plan["run_train_ensemble"]:
            if not steps["train"]:
                raise ValueError("train outputs are required before train_ensemble.")
            for step in steps["train_ensemble"]:
                overrides = _merge_overrides(
                    run_overrides,
                    downstream_data_overrides,
                    eval_overrides,
                    step["overrides"],
                )
                _add_pipeline_step(
                    controller,
                    name=step["step_name"],
                    parents=step["parents"],
                    parameter_override={f"Args/{k}": v for k, v in _overrides_to_params(overrides).items()},
                    clone_base_task=True,
                    cache_executed_step=False,
                    execution_queue=step["queue"],
                    **_base_task_kwargs(step["task_name"]),
                )

        if plan["run_leaderboard"]:
            if not steps["train"] and not steps["train_ensemble"]:
                raise ValueError("train outputs are required before leaderboard.")
            step = steps["leaderboard"]
            if step is None:
                raise ValueError("leaderboard step is missing.")
            train_task_refs = [
                pipeline_step_task_id_ref(train_step["step_name"]) for train_step in steps["train"]
            ]
            train_task_refs.extend(
                [pipeline_step_task_id_ref(step["step_name"]) for step in steps["train_ensemble"]]
            )
            overrides = _merge_overrides(
                run_overrides,
                eval_overrides,
                step["overrides"],
                {"leaderboard.train_task_ids": train_task_refs},
            )
            _add_pipeline_step(
                controller,
                name=step["step_name"],
                parents=step["parents"],
                parameter_override={f"Args/{k}": v for k, v in _overrides_to_params(overrides).items()},
                clone_base_task=True,
                cache_executed_step=False,
                execution_queue=step["queue"],
                **_base_task_kwargs(step["task_name"]),
            )

        if plan["run_infer"]:
            step = steps["infer"]
            if step is None:
                raise ValueError("infer step is missing.")
            infer_cfg = getattr(cfg, "infer", None)
            overrides = _merge_overrides(run_overrides, step["overrides"])
            infer_model_id = _normalize_str(getattr(infer_cfg, "model_id", None))
            infer_train_task_id = _normalize_str(getattr(infer_cfg, "train_task_id", None))
            if infer_train_task_id:
                overrides["infer.train_task_id"] = infer_train_task_id
            elif infer_model_id:
                overrides["infer.model_id"] = infer_model_id
            else:
                raise ValueError("infer requires model_id or train_task_id for remote execution.")
            _add_pipeline_step(
                controller,
                name=step["step_name"],
                parents=step["parents"],
                parameter_override={f"Args/{k}": v for k, v in _overrides_to_params(overrides).items()},
                clone_base_task=True,
                cache_executed_step=False,
                execution_queue=step["queue"],
                **_base_task_kwargs(step["task_name"]),
            )

        if run_controller_locally:
            starter = getattr(controller, "start_locally", None)
            if not callable(starter):
                raise AttributeError("Pipeline controller does not support start_locally.")
            starter(run_pipeline_steps_locally=False)
        else:
            starter = getattr(controller, "start", None)
            if not callable(starter):
                raise AttributeError("Pipeline controller does not support start.")
            if queue_name:
                starter(queue=queue_name)
            else:
                starter()
        step_task_ids = _collect_step_task_ids(controller)
        executed_jobs = len(steps["train"])

    dataset_register_ref = None
    preprocess_refs: list[dict[str, Any]] = []
    train_refs: list[dict[str, Any]] = []
    train_ensemble_refs: list[dict[str, Any]] = []
    leaderboard_ref = None
    infer_ref = None
    if not plan["plan_only"]:
        if steps["dataset_register"] is not None:
            dataset_step = steps["dataset_register"]
            dataset_register_ref = _build_ref(
                run_dir=dataset_step["run_dir"],
                task_id=step_task_ids.get(dataset_step["step_name"]),
            )

        for step in steps["preprocess"]:
            preprocess_refs.append(
                _build_ref(
                    run_dir=step["run_dir"],
                    task_id=step_task_ids.get(step["step_name"]),
                    preprocess_variant=step.get("preprocess_variant"),
                )
            )

        for step in steps["train"]:
            train_refs.append(
                _build_ref(
                    run_dir=step["run_dir"],
                    task_id=step_task_ids.get(step["step_name"]),
                    preprocess_variant=step.get("preprocess_variant"),
                    model_variant=step.get("model_variant"),
                    hpo_run_id=step.get("hpo_run_id"),
                    hpo_params=step.get("hpo_params"),
                )
            )

        for step in steps["train_ensemble"]:
            train_ensemble_refs.append(
                _build_ref(
                    run_dir=step["run_dir"],
                    task_id=step_task_ids.get(step["step_name"]),
                    preprocess_variant=step.get("preprocess_variant"),
                )
            )

        if steps["leaderboard"] is not None:
            leaderboard_step = steps["leaderboard"]
            leaderboard_ref = _build_ref(
                run_dir=leaderboard_step["run_dir"],
                task_id=step_task_ids.get(leaderboard_step["step_name"]),
            )

        if steps["infer"] is not None:
            infer_step = steps["infer"]
            infer_ref = _build_ref(
                run_dir=infer_step["run_dir"],
                task_id=step_task_ids.get(infer_step["step_name"]),
            )

    pipeline_run = {
        "grid_run_id": grid_run_id,
        "plan_only": plan["plan_only"],
        "planned_jobs": int(plan["plan_info"].get("planned_jobs", 0)),
        "executed_jobs": int(executed_jobs),
        "skipped_due_to_policy": int(plan["plan_info"].get("skipped_due_to_policy", 0)),
        "dataset_register_ref": dataset_register_ref,
        "preprocess_ref": preprocess_refs,
        "train_refs": train_refs,
        "train_ensemble_refs": train_ensemble_refs,
        "leaderboard_ref": leaderboard_ref,
        "infer_ref": infer_ref,
        "grid": {
            "preprocess_variants": plan["preprocess_variants"],
            "model_variants": plan["model_variants"],
            "max_jobs": plan["max_jobs"],
            "max_hpo_trials": plan["max_hpo_trials"],
            "hpo": {
                "enabled": plan["hpo_enabled"],
                "params": plan["hpo_params_cfg"],
            },
        },
        "policy": {
            "limits": dict(plan["limits"]),
            "selection": _resolve_exec_policy_selection(cfg),
        },
    }
    return pipeline_run


def run(cfg: Any) -> None:
    grid_run_id = _ensure_grid_run_id(cfg)
    identity = apply_clearml_identity(cfg, stage=cfg.task.stage)
    execution = _normalize_str(_cfg_value(cfg, "run.clearml.execution")) or "local"
    controller_execution = execution in ("pipeline_controller", "pipeline_controller_local")
    task_type = clearml_task_type_controller() if controller_execution else None
    system_tags = ["pipeline"] if controller_execution else None
    ctx = init_task_context(
        cfg,
        stage=cfg.task.stage,
        task_name="pipeline",
        tags=identity.tags,
        properties=identity.user_properties,
        task_type=task_type,
        system_tags=system_tags,
    )
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)
    pipeline_task_id = None
    if ctx.task is not None:
        task_id_value = getattr(ctx.task, "id", None)
        if task_id_value:
            pipeline_task_id = str(task_id_value)

    if clearml_enabled and execution in ("pipeline_controller", "pipeline_controller_local"):
        pipeline_run = _run_clearml_pipeline(
            cfg,
            grid_run_id,
            use_templates=True,
            controller_execution=execution,
            pipeline_task_id=pipeline_task_id,
        )
    elif clearml_enabled and execution in ("agent", "clone"):
        pipeline_run = _run_clearml_pipeline(
            cfg,
            grid_run_id,
            use_templates=False,
            controller_execution=execution,
            pipeline_task_id=pipeline_task_id,
        )
    else:
        pipeline_run = _run_local_pipeline(cfg, grid_run_id, clearml_enabled=clearml_enabled)

    pipeline_run_path = ctx.output_dir / "pipeline_run.json"
    pipeline_run_path.write_text(
        json.dumps(pipeline_run, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if clearml_enabled:
        upload_artifact(ctx, "pipeline_run.json", pipeline_run_path)
        num_models = int(pipeline_run.get("planned_jobs") or 0)
        num_succeeded = int(pipeline_run.get("executed_jobs") or 0)
        num_failed = max(0, num_models - num_succeeded)
        log_scalar(ctx.task, "pipeline", "num_models", num_models, step=0)
        log_scalar(ctx.task, "pipeline", "num_succeeded", num_succeeded, step=0)
        log_scalar(ctx.task, "pipeline", "num_failed", num_failed, step=0)

    report_path = ctx.output_dir / "report.md"
    limits = _resolve_exec_policy_limits(cfg)
    report_max_models = limits["max_models"] if limits["max_models"] > 0 else 5
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
            "run_leaderboard": bool(getattr(getattr(cfg, "pipeline", None), "run_leaderboard", True)),
            "run_infer": bool(getattr(getattr(cfg, "pipeline", None), "run_infer", False)),
            "plan_only": _resolve_plan_only(cfg),
        },
        "outputs": {"grid_run_id": grid_run_id, "pipeline_run_path": str(pipeline_run_path)},
        "hashes": {
            "config_hash": hash_config(cfg),
            "split_hash": hash_split({}),
            "recipe_hash": hash_recipe({}),
        },
    }
    write_manifest(ctx, manifest)
