"""infer process."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import math
import numbers
import re
import time
from pathlib import Path
from typing import Any, Mapping, Sequence
import warnings

from ..clearml.datasets import get_processed_dataset_local_copy
from ..clearml.hparams import connect_infer
from ..clearml.ui_logger import (
    log_debug_table,
    log_debug_text,
    log_plotly,
    report_input_output_table,
)
from ..io.bundle_io import load_bundle
from ..io.schema import extract_schema_dtypes
from ..monitoring.drift import build_drift_report, build_train_profile, render_drift_markdown
from ..ops.alerting import emit_alert
from ..ops.clearml_identity import apply_clearml_identity
from ..ops.data_quality import raise_on_quality_fail, run_data_quality_gate
from .drift_report import append_drift_summary, annotate_profile, resolve_drift_settings, sample_frame
from ..platform_adapter import (
    PlatformAdapterError,
    clone_clearml_task,
    enqueue_clearml_task,
    get_clearml_task_status,
    get_task_artifact_local_copy,
    hash_recipe,
    hash_config,
    init_task_context,
    is_clearml_enabled,
    resolve_version_props,
    resolve_clearml_task_url,
    reset_clearml_task_args,
    save_config_resolved,
    set_clearml_task_parameters,
    update_task_properties,
    upload_artifact,
    write_manifest,
    write_out_json,
)
from ..uncertainty.conformal import apply_split_conformal_interval
from ..viz.infer_plots import (
    build_input_output_table,
    build_label_distribution,
    build_prediction_histogram,
)
from ..viz.optuna_plots import (
    build_contour,
    build_optimization_history,
    build_parallel_coordinate,
    build_param_importance,
)
from ..viz.plots import plot_interval_width_histogram

_TABULAR_SUFFIXES = (".csv", ".parquet", ".pq")
_COERCE_FAILURE_SAMPLE_LIMIT = 200
_INTERVAL_WIDTH_SAMPLE_LIMIT = 10000
_BOOL_TRUTHY = {"true", "1", "yes", "y", "t"}
_BOOL_FALSY = {"false", "0", "no", "n", "f"}


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_bool(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, numbers.Integral):
        return bool(int(value))
    text = str(value).strip().lower()
    if not text:
        return False
    if text in _BOOL_TRUTHY:
        return True
    if text in _BOOL_FALSY:
        return False
    return False


def _normalize_task_type(value: Any) -> str:
    key = _normalize_str(value)
    if key in ("classification", "classifier", "class"):
        return "classification"
    return "regression"


def _has_payload(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return len(value) > 0
    return True


def _validate_infer_input_sources(
    *,
    mode: str,
    has_input_json: bool,
    has_input_path: bool,
    has_batch_inputs_json: bool,
    has_batch_inputs_path: bool,
    has_search_space: bool,
) -> None:
    errors: list[str] = []
    if mode == "single":
        if has_search_space:
            errors.append("infer.optimize.search_space is not supported in infer.mode=single.")
        if has_batch_inputs_json or has_batch_inputs_path:
            errors.append("infer.batch inputs are not supported in infer.mode=single.")
        if has_input_json and has_input_path:
            errors.append("Specify only one of infer.input_json or infer.input_path for infer.mode=single.")
    elif mode == "batch":
        if has_search_space:
            errors.append("infer.optimize.search_space is not supported in infer.mode=batch.")
        if has_batch_inputs_json and has_input_json:
            errors.append("Specify only one of infer.batch.inputs_json or infer.input_json for infer.mode=batch.")
        if has_batch_inputs_path and has_input_path:
            errors.append("Specify only one of infer.batch.inputs_path or infer.input_path for infer.mode=batch.")
        if (has_batch_inputs_json or has_input_json) and (has_batch_inputs_path or has_input_path):
            errors.append("Specify either inputs_json or inputs_path for infer.mode=batch, not both.")
    elif mode == "optimize":
        if has_input_json or has_input_path or has_batch_inputs_json or has_batch_inputs_path:
            errors.append("infer.mode=optimize only supports infer.optimize.search_space.")
        if not has_search_space:
            errors.append("infer.optimize.search_space is required for infer.mode=optimize.")
    if errors:
        raise ValueError(" ".join(errors))


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


def _verify_processed_dataset(
    cfg: Any,
    *,
    processed_dataset_id: str | None,
    recipe_hash: str | None,
    validation_mode: str,
) -> None:
    if not processed_dataset_id or processed_dataset_id.startswith("local:"):
        return
    if not is_clearml_enabled(cfg):
        return
    try:
        dataset_dir = get_processed_dataset_local_copy(cfg, processed_dataset_id)
    except Exception as exc:
        if validation_mode == "strict":
            raise
        warnings.warn(f"Failed to fetch processed dataset {processed_dataset_id}: {exc}")
        return

    dataset_recipe_hash: str | None = None
    meta_path = dataset_dir / "meta.json"
    if meta_path.exists():
        try:
            meta_payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta_payload = {}
        if isinstance(meta_payload, dict):
            dataset_recipe_hash = meta_payload.get("recipe_hash")

    if dataset_recipe_hash is None:
        recipe_path = dataset_dir / "recipe.json"
        if recipe_path.exists():
            try:
                recipe_payload = json.loads(recipe_path.read_text(encoding="utf-8"))
                if isinstance(recipe_payload, dict):
                    dataset_recipe_hash = hash_recipe(recipe_payload)
            except Exception:
                dataset_recipe_hash = None

    if recipe_hash and dataset_recipe_hash and recipe_hash != dataset_recipe_hash:
        message = (
            "processed_dataset recipe_hash mismatch: "
            f"bundle={recipe_hash} dataset={dataset_recipe_hash}"
        )
        if validation_mode == "strict":
            raise ValueError(message)
        warnings.warn(message)


def _drift_counts(summary: Mapping[str, Any]) -> tuple[int, int]:
    warn_count = int(summary.get("warn_count", 0) or 0)
    fail_count = int(summary.get("fail_count", 0) or 0)
    return warn_count, fail_count


def _emit_drift_alert(
    cfg: Any,
    ctx: Any,
    summary: Mapping[str, Any],
    drift_settings: Mapping[str, Any],
    *,
    warn_count: int,
    fail_count: int,
    sample_rows: int | None = None,
) -> None:
    if warn_count <= 0 and fail_count <= 0:
        return
    severity = "error" if fail_count > 0 else "warning"
    psi_max = summary.get("psi_max")
    psi_mean = summary.get("psi_mean")
    title = "Drift threshold exceeded" if fail_count > 0 else "Drift warning threshold exceeded"
    message = f"warn_count={warn_count}, fail_count={fail_count}, psi_max={psi_max}, psi_mean={psi_mean}"
    context = {
        "_cfg": cfg,
        "_ctx": ctx,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "psi_warn_threshold": drift_settings.get("psi_warn_threshold"),
        "psi_fail_threshold": drift_settings.get("psi_fail_threshold"),
        "metrics": drift_settings.get("metrics"),
        "psi_max": psi_max,
        "psi_mean": psi_mean,
    }
    if sample_rows is not None:
        context["sample_rows"] = sample_rows
    emit_alert("drift", severity, title, message, context)


def _to_container(value: Any) -> Any:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(value):
        return OmegaConf.to_container(value, resolve=True)
    return value


def _load_dataframe(path: Path):
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for infer.") from exc
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported dataset format: {path.suffix}")


def _resolve_batch_settings(cfg: Any) -> dict[str, Any]:
    chunk_size = _cfg_value(cfg, "infer.batch.chunk_size", None)
    try:
        chunk_size = int(chunk_size) if chunk_size is not None else None
    except Exception:
        chunk_size = None
    if chunk_size is not None and chunk_size <= 0:
        chunk_size = None

    output_format = _normalize_str(_cfg_value(cfg, "infer.batch.output_format", None)) or "csv"
    output_format = output_format.lower()
    if output_format not in ("csv", "parquet"):
        raise ValueError("infer.batch.output_format must be csv or parquet.")

    write_mode = _normalize_str(_cfg_value(cfg, "infer.batch.write_mode", None)) or "overwrite"
    write_mode = write_mode.lower()
    if write_mode not in ("overwrite", "append"):
        raise ValueError("infer.batch.write_mode must be overwrite or append.")

    max_rows = _cfg_value(cfg, "infer.batch.max_rows", None)
    try:
        max_rows = int(max_rows) if max_rows is not None else None
    except Exception:
        max_rows = None
    if max_rows is not None and max_rows <= 0:
        max_rows = None

    return {
        "chunk_size": chunk_size,
        "output_format": output_format,
        "write_mode": write_mode,
        "max_rows": max_rows,
    }


def _resolve_batch_children_settings(cfg: Any) -> dict[str, Any]:
    max_children = _cfg_value(cfg, "infer.batch.max_children", None)
    try:
        max_children = int(max_children) if max_children is not None else None
    except Exception:
        max_children = None
    if max_children is not None and max_children <= 0:
        max_children = None

    wait_timeout_sec = _cfg_value(cfg, "infer.batch.wait_timeout_sec", None)
    try:
        wait_timeout_sec = float(wait_timeout_sec) if wait_timeout_sec is not None else None
    except Exception:
        wait_timeout_sec = None
    if wait_timeout_sec is None or wait_timeout_sec <= 0:
        wait_timeout_sec = 3600.0

    poll_interval_sec = _cfg_value(cfg, "infer.batch.poll_interval_sec", None)
    try:
        poll_interval_sec = float(poll_interval_sec) if poll_interval_sec is not None else None
    except Exception:
        poll_interval_sec = None
    if poll_interval_sec is None or poll_interval_sec <= 0:
        poll_interval_sec = 10.0

    return {
        "max_children": max_children,
        "wait_timeout_sec": wait_timeout_sec,
        "poll_interval_sec": poll_interval_sec,
    }


def _normalize_optimize_type(value: Any) -> str:
    key = _normalize_str(value) or ""
    key = key.lower()
    if key in ("int", "integer"):
        return "int"
    if key in ("categorical", "category", "choice", "choices", "discrete"):
        return "categorical"
    return "float"


def _normalize_optimize_search_space(space: Any) -> list[dict[str, Any]]:
    space = _to_container(space)
    entries: list[dict[str, Any]] = []
    if not space:
        return entries
    if isinstance(space, str):
        text = space.strip()
        if not text:
            return entries
        try:
            space = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("infer.optimize.search_space must be valid JSON or a mapping/list.") from exc
    if isinstance(space, Mapping):
        for name, payload in space.items():
            entry: dict[str, Any] = {"name": str(name)}
            if isinstance(payload, Mapping):
                entry.update(dict(payload))
            elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
                entry["choices"] = list(payload)
            else:
                entry["choices"] = [payload]
            entries.append(entry)
        return entries
    if isinstance(space, Sequence) and not isinstance(space, (str, bytes)):
        for item in space:
            if not isinstance(item, Mapping):
                continue
            entry = dict(item)
            name = entry.get("name") or entry.get("param")
            if name is None:
                continue
            entry["name"] = str(name)
            entries.append(entry)
    return entries


def _resolve_optimize_objective_keys(cfg: Any) -> list[str]:
    payload = _to_container(_cfg_value(cfg, "infer.optimize.objective"))
    keys_value: Any = None
    if isinstance(payload, Mapping):
        keys_value = payload.get("keys") if "keys" in payload else payload.get("key")
    elif payload is not None:
        keys_value = payload
    if keys_value is None:
        return ["prediction"]
    if isinstance(keys_value, Sequence) and not isinstance(keys_value, (str, bytes)):
        keys = [str(item).strip() for item in keys_value if str(item).strip()]
        return keys or ["prediction"]
    key_text = str(keys_value).strip()
    return [key_text] if key_text else ["prediction"]


def _format_optimize_search_space(space: Sequence[Mapping[str, Any]]) -> str | None:
    if not space:
        return None
    parts: list[str] = []
    for entry in space:
        name = entry.get("name")
        if not name:
            continue
        type_name = _normalize_optimize_type(entry.get("type"))
        if type_name == "categorical":
            choices = entry.get("choices") or entry.get("values")
            if isinstance(choices, Sequence) and not isinstance(choices, (str, bytes)):
                parts.append(f"{name}:cat[{len(choices)}]")
            else:
                parts.append(f"{name}:cat")
            continue
        low = entry.get("low")
        high = entry.get("high")
        step = entry.get("step")
        log_scale = _parse_bool(entry.get("log")) if "log" in entry else False
        suffix = ""
        if step is not None:
            suffix = f",step={step}"
        if log_scale:
            suffix = f"{suffix},log"
        parts.append(f"{name}:{type_name}[{low},{high}{suffix}]")
    return "; ".join(parts) if parts else None


def _resolve_optimize_settings(cfg: Any) -> dict[str, Any]:
    n_trials = _cfg_value(cfg, "infer.optimize.n_trials", None)
    try:
        n_trials = int(n_trials) if n_trials is not None else None
    except Exception:
        n_trials = None
    if n_trials is None or n_trials <= 0:
        n_trials = 20

    direction = _normalize_str(_cfg_value(cfg, "infer.optimize.direction", None)) or "maximize"
    direction = direction.lower()
    if direction not in ("maximize", "minimize"):
        raise ValueError("infer.optimize.direction must be maximize or minimize.")

    sampler_cfg = _to_container(_cfg_value(cfg, "infer.optimize.sampler", None))
    sampler_name = None
    sampler_seed = None
    if isinstance(sampler_cfg, Mapping):
        sampler_name = _normalize_str(sampler_cfg.get("name"))
        sampler_seed = sampler_cfg.get("seed")
    else:
        sampler_name = _normalize_str(sampler_cfg)
    if sampler_name is None:
        sampler_name = _normalize_str(_cfg_value(cfg, "infer.optimize.sampler_name", None))
    sampler_name = sampler_name or "tpe"
    if sampler_seed is None:
        sampler_seed = _cfg_value(cfg, "infer.optimize.seed", None)
    try:
        sampler_seed = int(sampler_seed) if sampler_seed is not None else None
    except Exception:
        sampler_seed = None

    search_space = _normalize_optimize_search_space(_cfg_value(cfg, "infer.optimize.search_space"))
    objective_keys = _resolve_optimize_objective_keys(cfg)

    top_k = _cfg_value(cfg, "infer.optimize.top_k", None)
    try:
        top_k = int(top_k) if top_k is not None else None
    except Exception:
        top_k = None
    if top_k is None or top_k <= 0:
        top_k = 5

    wait_timeout_sec = _cfg_value(cfg, "infer.optimize.wait_timeout_sec", None)
    if wait_timeout_sec is None:
        wait_timeout_sec = _cfg_value(cfg, "infer.batch.wait_timeout_sec", None)
    try:
        wait_timeout_sec = float(wait_timeout_sec) if wait_timeout_sec is not None else None
    except Exception:
        wait_timeout_sec = None
    if wait_timeout_sec is None or wait_timeout_sec <= 0:
        wait_timeout_sec = 3600.0

    poll_interval_sec = _cfg_value(cfg, "infer.optimize.poll_interval_sec", None)
    if poll_interval_sec is None:
        poll_interval_sec = _cfg_value(cfg, "infer.batch.poll_interval_sec", None)
    try:
        poll_interval_sec = float(poll_interval_sec) if poll_interval_sec is not None else None
    except Exception:
        poll_interval_sec = None
    if poll_interval_sec is None or poll_interval_sec <= 0:
        poll_interval_sec = 10.0

    history_log_scale = _parse_bool(_cfg_value(cfg, "infer.optimize.plots.history_log_scale", False))
    contour_params = _to_container(_cfg_value(cfg, "infer.optimize.plots.contour_params", None))
    if isinstance(contour_params, str):
        contour_params = [contour_params]
    if isinstance(contour_params, Sequence) and not isinstance(contour_params, (str, bytes)):
        contour_params = [str(item) for item in contour_params if str(item).strip()]
    else:
        contour_params = None

    return {
        "n_trials": n_trials,
        "direction": direction,
        "sampler_name": sampler_name,
        "sampler_seed": sampler_seed,
        "search_space": search_space,
        "objective_keys": objective_keys,
        "top_k": top_k,
        "wait_timeout_sec": wait_timeout_sec,
        "poll_interval_sec": poll_interval_sec,
        "history_log_scale": history_log_scale,
        "contour_params": contour_params,
    }


def _build_optuna_sampler(name: str, seed: int | None) -> Any:
    try:
        import optuna  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Optuna is required for infer.mode=optimize. Install with: "
            "uv sync --extra optuna (or pip install optuna)"
        ) from exc
    key = (name or "").strip().lower()
    if key in ("tpe", "tp"):
        return optuna.samplers.TPESampler(seed=seed)
    if key in ("random", "rand"):
        return optuna.samplers.RandomSampler(seed=seed)
    if key in ("cmaes", "cma"):
        try:
            return optuna.samplers.CmaEsSampler(seed=seed)
        except Exception as exc:
            raise ValueError("infer.optimize.sampler=cmaes requires cmaes dependency.") from exc
    raise ValueError("infer.optimize.sampler must be tpe, random, or cmaes.")


def _suggest_optuna_params(trial: Any, search_space: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for entry in search_space:
        name = entry.get("name")
        if not name:
            continue
        type_name = entry.get("type")
        if not type_name:
            if "choices" in entry or "values" in entry:
                type_name = "categorical"
            else:
                type_name = "float"
        type_name = _normalize_optimize_type(type_name)

        if type_name == "categorical":
            choices = entry.get("choices") or entry.get("values")
            if not isinstance(choices, Sequence) or isinstance(choices, (str, bytes)):
                raise ValueError(f"infer.optimize.search_space {name} missing choices.")
            params[str(name)] = trial.suggest_categorical(str(name), list(choices))
            continue

        low = entry.get("low")
        high = entry.get("high")
        if low is None or high is None:
            raise ValueError(f"infer.optimize.search_space {name} requires low/high.")
        step = entry.get("step")
        log_scale = _parse_bool(entry.get("log")) if "log" in entry else False
        if step is not None and log_scale:
            raise ValueError(f"infer.optimize.search_space {name} cannot set log and step together.")

        if type_name == "int":
            try:
                low_int = int(low)
                high_int = int(high)
            except Exception as exc:
                raise ValueError(f"infer.optimize.search_space {name} requires int low/high.") from exc
            step_int = None
            if step is not None:
                try:
                    step_int = int(step)
                except Exception as exc:
                    raise ValueError(
                        f"infer.optimize.search_space {name} step must be int."
                    ) from exc
            params[str(name)] = trial.suggest_int(
                str(name),
                low_int,
                high_int,
                step=step_int,
                log=log_scale,
            )
            continue

        try:
            low_float = float(low)
            high_float = float(high)
        except Exception as exc:
            raise ValueError(f"infer.optimize.search_space {name} requires float low/high.") from exc
        step_float = None
        if step is not None:
            try:
                step_float = float(step)
            except Exception as exc:
                raise ValueError(
                    f"infer.optimize.search_space {name} step must be float."
                ) from exc
        params[str(name)] = trial.suggest_float(
            str(name),
            low_float,
            high_float,
            step=step_float,
            log=log_scale,
        )
    return params


def _coerce_objective_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, numbers.Real):
        num = float(value)
        return num if math.isfinite(num) else None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            num = float(text)
        except Exception:
            return None
        return num if math.isfinite(num) else None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if len(value) == 1:
            return _coerce_objective_value(value[0])
    return None


def _resolve_objective_value(payload: Mapping[str, Any], keys: Sequence[str]) -> float | None:
    for key in keys:
        if key in payload:
            numeric = _coerce_objective_value(payload.get(key))
            if numeric is not None:
                return numeric
    return None


def _build_optimize_hparams(optimize_settings: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not optimize_settings:
        return None
    objective_keys = optimize_settings.get("objective_keys") or []
    if isinstance(objective_keys, Sequence) and not isinstance(objective_keys, (str, bytes)):
        objective_label = ",".join([str(item) for item in objective_keys if str(item).strip()])
    else:
        objective_label = str(objective_keys) if objective_keys else None
    search_space = optimize_settings.get("search_space") or []
    search_space_summary = _format_optimize_search_space(search_space)
    return {
        "infer.optimize.n_trials": optimize_settings.get("n_trials"),
        "infer.optimize.direction": optimize_settings.get("direction"),
        "infer.optimize.sampler": optimize_settings.get("sampler_name"),
        "infer.optimize.objective": objective_label,
        "infer.optimize.search_space": search_space_summary,
        "infer.optimize.top_k": optimize_settings.get("top_k"),
    }


def _resolve_child_queue(cfg: Any) -> str | None:
    queue = _normalize_str(_cfg_value(cfg, "exec_policy.queues.infer"))
    if not queue:
        queue = _normalize_str(_cfg_value(cfg, "run.clearml.queue_name"))
    return queue


def _wait_for_child_tasks(
    task_ids: Sequence[str],
    *,
    timeout_sec: float,
    poll_interval_sec: float,
) -> dict[str, str]:
    statuses: dict[str, str] = {}
    remaining = set(task_ids)
    deadline = time.monotonic() + timeout_sec
    terminal = {"completed", "failed", "stopped", "closed", "aborted"}
    while remaining and time.monotonic() < deadline:
        for task_id in list(remaining):
            status = get_clearml_task_status(task_id)
            if status:
                status_value = str(status).lower()
                if status_value in terminal:
                    statuses[task_id] = status_value
                    remaining.remove(task_id)
        if remaining:
            time.sleep(poll_interval_sec)
    for task_id in remaining:
        statuses[task_id] = "timeout"
    return statuses


def _resolve_batch_input_path(cfg: Any, *, mode: str | None = None) -> str | None:
    infer_cfg = getattr(cfg, "infer", None)
    dataset_path = None
    if mode == "batch":
        batch_cfg = getattr(infer_cfg, "batch", None)
        dataset_path = _normalize_str(getattr(batch_cfg, "inputs_path", None))
    if not dataset_path:
        dataset_path = _normalize_str(getattr(infer_cfg, "input_path", None))
    if not dataset_path:
        dataset_path = _normalize_str(getattr(getattr(cfg, "data", None), "dataset_path", None))
    return dataset_path


def _iter_csv_chunks(path: Path, *, chunk_size: int):
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for infer.") from exc
    return pd.read_csv(path, chunksize=chunk_size)


def _iter_parquet_chunks(path: Path, *, chunk_size: int):
    try:
        import pyarrow.parquet as pq  # type: ignore
    except Exception as exc:
        raise RuntimeError("pyarrow is required for parquet chunked infer.") from exc
    parquet_file = pq.ParquetFile(path)
    for batch in parquet_file.iter_batches(batch_size=chunk_size):
        yield batch.to_pandas()


def _iter_tabular_chunks(path: Path, *, chunk_size: int, max_rows: int | None = None):
    suffix = path.suffix.lower()
    if suffix == ".csv":
        iterator = _iter_csv_chunks(path, chunk_size=chunk_size)
    elif suffix in (".parquet", ".pq"):
        iterator = _iter_parquet_chunks(path, chunk_size=chunk_size)
    else:
        raise ValueError(f"Unsupported dataset format: {path.suffix}")

    row_offset = 0
    for chunk in iterator:
        if max_rows is not None and row_offset >= max_rows:
            break
        if max_rows is not None:
            remaining = max_rows - row_offset
            if remaining <= 0:
                break
            if len(chunk) > remaining:
                chunk = chunk.iloc[:remaining]
        if len(chunk) == 0:
            break
        yield chunk, row_offset
        row_offset += len(chunk)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_batch_inputs(
    payload: Any | None,
    path: str | None,
    *,
    max_rows: int | None = None,
) -> tuple[Any | None, str | None]:
    if payload is not None:
        df = _frame_from_payload(payload)
        if max_rows is not None and max_rows > 0:
            df = df.head(max_rows)
        return df, None
    if not path:
        return None, None
    resolved = Path(path).expanduser().resolve()
    if resolved.suffix.lower() == ".json":
        payload = _load_json(resolved)
        df = _frame_from_payload(payload)
        if max_rows is not None and max_rows > 0:
            df = df.head(max_rows)
        return df, str(resolved)
    data_path = _select_tabular_file(resolved)
    if data_path.suffix.lower() == ".csv" and max_rows is not None and max_rows > 0:
        try:
            import pandas as pd  # type: ignore
        except Exception as exc:
            raise RuntimeError("pandas is required for infer.") from exc
        df = pd.read_csv(data_path, nrows=max_rows)
        return df, str(data_path)
    df = _load_dataframe(data_path)
    if max_rows is not None and max_rows > 0:
        df = df.head(max_rows)
    return df, str(data_path)


def _select_tabular_file(path: Path) -> Path:
    if path.is_file():
        return path
    if path.is_dir():
        candidates = sorted([p for p in path.rglob("*") if p.suffix.lower() in _TABULAR_SUFFIXES])
        if candidates:
            return candidates[0]
        raise ValueError(f"No CSV/Parquet files found under: {path}")
    raise FileNotFoundError(str(path))


def _resolve_preprocess_columns(
    preprocess_bundle: Mapping[str, Any],
) -> tuple[list[str], list[str], list[str], str | None]:
    columns = preprocess_bundle.get("columns") or {}
    feature_columns = list(columns.get("feature_columns") or [])
    if not feature_columns:
        schema = preprocess_bundle.get("schema") or {}
        fields = schema.get("fields")
        if isinstance(fields, Mapping):
            feature_columns = [str(name) for name in fields.keys()]
    numeric_features = [str(name) for name in (columns.get("numeric_features") or [])]
    categorical_features = [str(name) for name in (columns.get("categorical_features") or [])]
    target_column = _normalize_str(columns.get("target_column")) or _normalize_str(
        preprocess_bundle.get("target_column")
    )
    return feature_columns, numeric_features, categorical_features, target_column


def _resolve_validation_mode(cfg: Any) -> str:
    infer_cfg = getattr(cfg, "infer", None)
    validation_cfg = getattr(infer_cfg, "validation", None)
    mode = _normalize_str(getattr(validation_cfg, "mode", None)) or "warn"
    return mode.lower()


def _resolve_viz_enabled(cfg: Any) -> bool:
    return bool(_cfg_value(cfg, "viz.enabled", True))


def _resolve_uncertainty_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    payload = bundle.get("uncertainty")
    if not isinstance(payload, Mapping):
        payload = {}
    method = _normalize_str(payload.get("method")) or "conformal_split"
    alpha = payload.get("alpha")
    try:
        alpha = float(alpha) if alpha is not None else None
    except Exception:
        alpha = None
    q = payload.get("q")
    try:
        q = float(q) if q is not None else None
    except Exception:
        q = None
    return {
        "enabled": bool(payload.get("enabled")),
        "method": method,
        "alpha": alpha,
        "q": q,
        "use_abs_residual": payload.get("use_abs_residual"),
    }


def _resolve_uncertainty_settings(
    cfg: Any,
    bundle: Mapping[str, Any],
    *,
    task_type: str,
) -> dict[str, Any]:
    cfg_enabled = bool(_cfg_value(cfg, "eval.uncertainty.enabled", False))
    info = _resolve_uncertainty_bundle(bundle)
    enabled = bool(info.get("enabled"))
    if cfg_enabled and not enabled:
        raise ValueError(
            "eval.uncertainty.enabled is true but model_bundle is missing uncertainty data; "
            "retrain with eval.uncertainty.enabled=true."
        )
    if enabled and task_type != "regression":
        raise ValueError("uncertainty is supported for regression only.")
    if enabled:
        method = _normalize_str(info.get("method")) or "conformal_split"
        if method != "conformal_split":
            raise ValueError("Only conformal_split uncertainty is supported.")
        q = info.get("q")
        if q is None or not math.isfinite(float(q)):
            raise ValueError("uncertainty.q is missing or invalid in model_bundle.")
    return info


def _dtype_kind(expected: str) -> str:
    try:
        from pandas.api.types import (  # type: ignore
            is_bool_dtype,
            is_categorical_dtype,
            is_datetime64_any_dtype,
            is_numeric_dtype,
            is_string_dtype,
            pandas_dtype,
        )
    except Exception:
        return "object"
    try:
        dtype = pandas_dtype(expected)
    except Exception:
        return "object"
    if is_bool_dtype(dtype):
        return "bool"
    if is_numeric_dtype(dtype):
        return "numeric"
    if is_datetime64_any_dtype(dtype):
        return "datetime"
    if is_categorical_dtype(dtype):
        return "category"
    if is_string_dtype(dtype):
        return "string"
    return "object"


def _format_index_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, numbers.Integral):
        return int(value)
    return str(value)


def _collect_coerce_failures(series, coerced, *, column: str, reason: str) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    try:
        missing_before = series.isna()
        missing_after = coerced.isna()
    except Exception:
        return failures
    failed = (~missing_before) & missing_after
    if hasattr(series, "index"):
        for idx in series.index[failed]:
            failures.append({"row_index": _format_index_value(idx), "column": column, "reason": reason})
    return failures


def _coerce_bool_series(series):
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for infer.") from exc

    def _coerce(value: Any) -> Any:
        if pd.isna(value):
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, numbers.Integral):
            if int(value) == 1:
                return True
            if int(value) == 0:
                return False
            return None
        text = str(value).strip().lower()
        if text in _BOOL_TRUTHY:
            return True
        if text in _BOOL_FALSY:
            return False
        return None

    return series.map(_coerce)


def _parse_input_payload(value: Any) -> Any | None:
    payload = _to_container(value)
    if payload is None:
        return None
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("infer.input_json must be valid JSON.") from exc
    return payload


def _parse_batch_inputs_payload(value: Any) -> Any | None:
    payload = _to_container(value)
    if payload is None:
        return None
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("infer.batch.inputs_json must be valid JSON.") from exc
    return payload


def _frame_from_payload(payload: Any):
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for infer.") from exc

    if isinstance(payload, Mapping):
        return pd.DataFrame([dict(payload)])
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        if not payload:
            return pd.DataFrame()
        if all(isinstance(item, Mapping) for item in payload):
            return pd.DataFrame([dict(item) for item in payload])
    raise ValueError("infer.input_json must be a JSON object or list of objects.")


def _frame_to_records(df: Any) -> list[dict[str, Any]]:
    try:
        records = df.to_dict(orient="records")
    except Exception:
        return []
    sanitized: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            continue
        sanitized.append({str(k): _sanitize_json_value(v) for k, v in record.items()})
    return sanitized


def _sanitize_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        num = float(value)
        if not math.isfinite(num):
            return None
        return num
    if isinstance(value, str):
        return value
    return str(value)


def _flatten_prediction_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    flattened: dict[str, Any] = {}
    for key, value in payload.items():
        if key == "predicted_proba":
            if isinstance(value, Mapping):
                labels = list(value.keys())
                safe_labels = _build_proba_column_labels(labels)
                for label, safe in zip(labels, safe_labels):
                    flattened[f"pred_proba_{safe}"] = _sanitize_json_value(value.get(label))
                continue
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                for idx, item in enumerate(value):
                    flattened[f"pred_proba_{idx}"] = _sanitize_json_value(item)
                continue
        if key == "top_k" and isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for idx, entry in enumerate(value, start=1):
                if isinstance(entry, Mapping):
                    flattened[f"top{idx}_label"] = _sanitize_json_value(entry.get("label"))
                    flattened[f"top{idx}_proba"] = _sanitize_json_value(entry.get("proba"))
                else:
                    flattened[f"top{idx}"] = _sanitize_json_value(entry)
            continue
        if key == "prediction" and isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            if len(value) == 1:
                flattened["prediction"] = _sanitize_json_value(value[0])
            else:
                for idx, item in enumerate(value):
                    flattened[f"prediction_{idx}"] = _sanitize_json_value(item)
            continue
        flattened[str(key)] = _sanitize_json_value(value)
    return flattened


def _load_prediction_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if isinstance(payload, Mapping):
            return dict(payload)
        if isinstance(payload, list):
            for entry in payload:
                if isinstance(entry, Mapping):
                    return dict(entry)
        return None
    if suffix == ".csv":
        try:
            with path.open("r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    if row:
                        return dict(row)
        except Exception:
            return None
    return None


def _select_distribution_samples(output_df: Any) -> tuple[list[float] | None, list[Any] | None]:
    if output_df is None:
        return None, None
    try:
        import pandas as pd  # type: ignore
        from pandas.api.types import is_numeric_dtype  # type: ignore
    except Exception:
        return None, None
    if getattr(output_df, "empty", True):
        return None, None
    if "prediction" in output_df.columns and is_numeric_dtype(output_df["prediction"]):
        values = [
            float(value)
            for value in output_df["prediction"].dropna().tolist()
            if isinstance(value, numbers.Real) and math.isfinite(float(value))
        ]
        return values, None
    proba_cols = [
        col
        for col in output_df.columns
        if isinstance(col, str) and (col.startswith("pred_proba_") or col.startswith("proba_"))
    ]
    if proba_cols:
        try:
            series = output_df[proba_cols].max(axis=1, skipna=True)
            values = [
                float(value)
                for value in series.dropna().tolist()
                if isinstance(value, numbers.Real) and math.isfinite(float(value))
            ]
            return values, None
        except Exception:
            pass
    if "pred_label" in output_df.columns:
        labels = output_df["pred_label"].tolist()
        return None, labels
    return None, None


def _coerce_threshold(value: Any) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except Exception:
        return None
    if not math.isfinite(num):
        return None
    if num < 0.0 or num > 1.0:
        return None
    return num


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except Exception:
        return None
    if not math.isfinite(num):
        return None
    return num


def _resolve_top_k(cfg: Any, *, n_classes: int | None) -> int | None:
    value = _cfg_value(cfg, "eval.classification.top_k", None)
    if value is None:
        return None
    try:
        top_k = int(value)
    except Exception:
        return None
    if top_k <= 1:
        return None
    if n_classes is not None and top_k > n_classes:
        top_k = n_classes
    return top_k if top_k > 1 else None


def _load_train_profile(
    cfg: Any,
    bundle: Mapping[str, Any],
    model_bundle_path: Path,
    *,
    train_task_id: str | None,
    clearml_enabled: bool,
) -> tuple[dict[str, Any] | None, Path | None]:
    profile = None
    if isinstance(bundle, Mapping):
        candidate = bundle.get("train_profile")
        if isinstance(candidate, Mapping):
            profile = dict(candidate)
    if profile is not None:
        return profile, None
    profile_path = model_bundle_path.parent / "train_profile.json"
    if profile_path.exists():
        return _load_json(profile_path), profile_path
    if clearml_enabled and train_task_id:
        try:
            profile_path = get_task_artifact_local_copy(cfg, train_task_id, "train_profile.json")
            return _load_json(profile_path), profile_path
        except PlatformAdapterError:
            return None, None
    return None, None


def _ensure_drift_frame(data, feature_names: Sequence[str] | None):
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for drift reporting.") from exc

    if isinstance(data, pd.DataFrame):
        return data
    values = data
    if hasattr(values, "toarray"):
        values = values.toarray()
    shape = getattr(values, "shape", None)
    if shape is None or len(shape) < 2:
        return pd.DataFrame(values)
    n_cols = int(shape[1])
    if feature_names and len(feature_names) == n_cols:
        columns = list(feature_names)
    else:
        columns = [f"f{i}" for i in range(n_cols)]
    return pd.DataFrame(values, columns=columns)


def _maybe_attach_feature_names(data: Any, feature_names: Sequence[str] | None):
    if not feature_names:
        return data
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return data
    try:
        n_cols = int(getattr(data, "shape", [0, 0])[1])
    except Exception:
        return data
    if len(feature_names) != n_cols:
        return data
    return pd.DataFrame(data, columns=list(feature_names))


def _resolve_threshold_used(bundle: Mapping[str, Any], *, n_classes: int | None) -> float | None:
    if n_classes != 2:
        return None
    candidates: list[Any] = []
    postprocess = bundle.get("postprocess")
    if isinstance(postprocess, Mapping):
        candidates.append(postprocess.get("threshold"))
        candidates.append(postprocess.get("best_threshold"))
    candidates.append(bundle.get("best_threshold"))
    for value in candidates:
        threshold = _coerce_threshold(value)
        if threshold is not None:
            return threshold
    return None


def _resolve_calibration_info(bundle: Mapping[str, Any]) -> dict[str, Any] | None:
    postprocess = bundle.get("postprocess")
    if isinstance(postprocess, Mapping):
        calibration = postprocess.get("calibration")
        if isinstance(calibration, Mapping):
            return dict(calibration)
    calibration = bundle.get("calibration")
    if isinstance(calibration, Mapping):
        return dict(calibration)
    metrics = bundle.get("metrics")
    if isinstance(metrics, Mapping):
        calibration = metrics.get("calibration")
        if isinstance(calibration, Mapping):
            return dict(calibration)
    return None


def _extract_positive_proba(y_proba: Any) -> Any:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for classification probabilities.") from exc
    arr = np.asarray(y_proba)
    if arr.ndim == 1:
        return arr
    if arr.ndim == 2 and arr.shape[1] >= 2:
        return arr[:, 1]
    raise ValueError("predict_proba output must include positive-class probabilities.")


def _resolve_mode(cfg: Any) -> str:
    mode = _normalize_str(getattr(getattr(cfg, "infer", None), "mode", None))
    if not mode:
        group_mode = getattr(getattr(cfg, "group", None), "infer_mode", None)
        mode = _normalize_str(getattr(getattr(group_mode, "infer_mode", None), "name", None))
    mode = mode or "single"
    return mode.lower()


def _resolve_model_bundle_path(cfg: Any, *, clearml_enabled: bool) -> tuple[Path, dict[str, Any]]:
    infer_cfg = getattr(cfg, "infer", None)
    model_id = _normalize_str(getattr(infer_cfg, "model_id", None))
    model_bundle_path = _normalize_str(getattr(infer_cfg, "model_bundle_path", None))
    train_task_id = _normalize_str(getattr(infer_cfg, "train_task_id", None))

    meta = {"model_id": model_id, "train_task_id": train_task_id}

    if clearml_enabled and train_task_id:
        try:
            path = get_task_artifact_local_copy(cfg, train_task_id, "model_bundle.joblib")
            return path, meta
        except PlatformAdapterError as exc:
            raise RuntimeError(f"Failed to fetch model_bundle.joblib from task {train_task_id}: {exc}") from exc

    for candidate in (model_bundle_path, model_id):
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path.resolve(), meta

    if train_task_id:
        run_dir = Path(train_task_id).expanduser()
        if run_dir.is_dir():
            candidate = run_dir / "model_bundle.joblib"
            if candidate.exists():
                return candidate.resolve(), meta

    raise FileNotFoundError("model_bundle.joblib not found; set infer.model_id or infer.train_task_id.")


def _build_dummy_input(preprocess_bundle: dict[str, Any]):
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for infer.") from exc

    feature_columns, numeric_features, categorical_features, _ = _resolve_preprocess_columns(
        preprocess_bundle
    )
    numeric_set = set(numeric_features)
    categorical_set = set(categorical_features)
    if not feature_columns:
        raise ValueError("preprocess bundle does not define feature_columns.")

    row: dict[str, Any] = {}
    for col in feature_columns:
        if col in categorical_set:
            row[col] = "unknown"
        elif col in numeric_set:
            row[col] = 0.0
        else:
            row[col] = None
    return pd.DataFrame([row])


def _align_input_frame(
    df,
    preprocess_bundle: Mapping[str, Any],
    *,
    allow_missing: bool,
):
    feature_columns, numeric_features, categorical_features, target_column = _resolve_preprocess_columns(
        preprocess_bundle
    )
    if feature_columns:
        missing = [col for col in feature_columns if col not in df.columns]
        if missing and not allow_missing:
            raise ValueError(f"Input is missing required columns: {missing}")
        if missing:
            df = df.copy()
            numeric_set = set(numeric_features)
            categorical_set = set(categorical_features)
            for col in missing:
                if col in numeric_set:
                    df[col] = float("nan")
                elif col in categorical_set:
                    df[col] = None
                else:
                    df[col] = None
        df = df[feature_columns]
    else:
        if target_column and target_column in df.columns:
            df = df.drop(columns=[target_column])
        feature_columns = list(df.columns)
    return df, feature_columns


def _collect_schema_issues(df, preprocess_bundle: Mapping[str, Any]) -> dict[str, Any]:
    (
        feature_columns,
        _numeric_features,
        _categorical_features,
        target_column,
    ) = _resolve_preprocess_columns(preprocess_bundle)
    expected_dtypes = extract_schema_dtypes(preprocess_bundle.get("schema") or {})
    if feature_columns:
        missing_columns = [col for col in feature_columns if col not in df.columns]
        extra_columns = [col for col in df.columns if col not in feature_columns]
        if target_column and target_column in extra_columns:
            extra_columns.remove(target_column)
    else:
        missing_columns = []
        extra_columns = []

    dtype_mismatch: list[dict[str, Any]] = []
    for col, expected in expected_dtypes.items():
        if feature_columns and col not in feature_columns:
            continue
        if col not in df.columns:
            continue
        actual = str(df[col].dtype)
        if str(expected) != actual:
            dtype_mismatch.append({"column": col, "expected": str(expected), "actual": actual})

    return {
        "feature_columns": feature_columns,
        "expected_dtypes": expected_dtypes,
        "missing_columns": missing_columns,
        "extra_columns": extra_columns,
        "dtype_mismatch": dtype_mismatch,
    }


def _coerce_frame_to_schema(
    df,
    *,
    expected_dtypes: Mapping[str, str],
    feature_columns: Sequence[str],
) -> tuple[Any, list[dict[str, Any]]]:
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for infer.") from exc

    coerce_failures: list[dict[str, Any]] = []
    for col, expected in expected_dtypes.items():
        if feature_columns and col not in feature_columns:
            continue
        if col not in df.columns:
            continue
        kind = _dtype_kind(expected)
        if kind == "numeric":
            coerced = pd.to_numeric(df[col], errors="coerce")
            coerce_failures.extend(
                _collect_coerce_failures(df[col], coerced, column=col, reason="numeric_coerce_failed")
            )
            df[col] = coerced
        elif kind == "datetime":
            coerced = pd.to_datetime(df[col], errors="coerce")
            coerce_failures.extend(
                _collect_coerce_failures(df[col], coerced, column=col, reason="datetime_coerce_failed")
            )
            df[col] = coerced
        elif kind == "bool":
            coerced = _coerce_bool_series(df[col])
            coerce_failures.extend(
                _collect_coerce_failures(df[col], coerced, column=col, reason="bool_coerce_failed")
            )
            df[col] = coerced
    return df, coerce_failures


def _count_schema_issues(issues: Mapping[str, Any]) -> int:
    total = 0
    for key in ("missing_columns", "extra_columns", "dtype_mismatch", "coerce_failures"):
        value = issues.get(key) or []
        try:
            total += len(value)
        except Exception:
            continue
    return total


def _init_validation_accumulator() -> dict[str, Any]:
    return {
        "issues": {
            "missing_columns": set(),
            "extra_columns": set(),
            "dtype_mismatch": {},
            "coerce_failures": [],
        },
        "warnings_count": 0,
        "errors_count": 0,
        "ok": True,
        "total_issues": 0,
    }


def _update_validation_accumulator(
    acc: dict[str, Any],
    issues: Mapping[str, Any],
    *,
    validation_mode: str,
) -> None:
    issue_count = _count_schema_issues(issues)
    acc["total_issues"] += issue_count
    if issue_count > 0:
        acc["ok"] = False
    if validation_mode == "strict":
        acc["errors_count"] += issue_count
    else:
        acc["warnings_count"] += issue_count

    missing = issues.get("missing_columns") or []
    extra = issues.get("extra_columns") or []
    dtype_mismatch = issues.get("dtype_mismatch") or []
    coerce_failures = issues.get("coerce_failures") or []

    acc["issues"]["missing_columns"].update(missing)
    acc["issues"]["extra_columns"].update(extra)
    for entry in dtype_mismatch:
        key = (entry.get("column"), entry.get("expected"), entry.get("actual"))
        acc["issues"]["dtype_mismatch"][key] = dict(entry)
    if coerce_failures and len(acc["issues"]["coerce_failures"]) < _COERCE_FAILURE_SAMPLE_LIMIT:
        remaining = _COERCE_FAILURE_SAMPLE_LIMIT - len(acc["issues"]["coerce_failures"])
        acc["issues"]["coerce_failures"].extend(list(coerce_failures)[:remaining])


def _finalize_validation_accumulator(acc: dict[str, Any]) -> dict[str, Any]:
    issues = acc["issues"]
    return {
        "issues": {
            "missing_columns": sorted(issues.get("missing_columns", [])),
            "extra_columns": sorted(issues.get("extra_columns", [])),
            "dtype_mismatch": list(issues.get("dtype_mismatch", {}).values()),
            "coerce_failures": list(issues.get("coerce_failures", [])),
        },
        "warnings_count": int(acc.get("warnings_count") or 0),
        "errors_count": int(acc.get("errors_count") or 0),
        "ok": bool(acc.get("ok")),
    }


def _format_list_preview(values: Sequence[str], *, limit: int = 10) -> str:
    if not values:
        return ""
    preview = ", ".join(values[:limit])
    if len(values) > limit:
        preview = f"{preview}, ...(+{len(values) - limit})"
    return preview


def _write_schema_errors(output_dir: Path, issues: Mapping[str, Any]) -> tuple[Path, Path]:
    errors_json_path = output_dir / "errors.json"
    errors_csv_path = output_dir / "errors.csv"

    payload = {
        "missing_columns": list(issues.get("missing_columns") or []),
        "extra_columns": list(issues.get("extra_columns") or []),
        "dtype_mismatch": list(issues.get("dtype_mismatch") or []),
        "coerce_failures": list(issues.get("coerce_failures") or []),
    }
    errors_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = ["issue_type", "column", "row_index", "expected_dtype", "actual_dtype", "reason"]
    with errors_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for col in payload["missing_columns"]:
            writer.writerow({"issue_type": "missing_columns", "column": col})
        for col in payload["extra_columns"]:
            writer.writerow({"issue_type": "extra_columns", "column": col})
        for entry in payload["dtype_mismatch"]:
            writer.writerow(
                {
                    "issue_type": "dtype_mismatch",
                    "column": entry.get("column"),
                    "expected_dtype": entry.get("expected"),
                    "actual_dtype": entry.get("actual"),
                }
            )
        for entry in payload["coerce_failures"]:
            writer.writerow(
                {
                    "issue_type": "coerce_failures",
                    "column": entry.get("column"),
                    "row_index": entry.get("row_index"),
                    "reason": entry.get("reason"),
                }
            )
    return errors_json_path, errors_csv_path


def _write_infer_summary(
    output_dir: Path,
    *,
    mode: str,
    validation_mode: str,
    validation: Mapping[str, Any],
    errors_path: Path | None,
    uncertainty: Mapping[str, Any] | None = None,
) -> Path:
    issues = validation.get("issues") or {}
    missing_columns = list(issues.get("missing_columns") or [])
    extra_columns = list(issues.get("extra_columns") or [])
    dtype_mismatch = list(issues.get("dtype_mismatch") or [])
    coerce_failures = list(issues.get("coerce_failures") or [])

    lines = [
        "# Infer Summary",
        "",
        f"- mode: {mode}",
        f"- schema_validation_mode: {validation_mode}",
        f"- schema_validation_ok: {bool(validation.get('ok'))}",
        f"- warnings_count: {validation.get('warnings_count')}",
        f"- errors_count: {validation.get('errors_count')}",
    ]
    if errors_path is not None:
        lines.append(f"- errors_path: {errors_path}")

    if uncertainty and uncertainty.get("enabled"):
        alpha = uncertainty.get("alpha")
        method = uncertainty.get("method")
        q_value = uncertainty.get("q")
        lines.extend(["", "## Prediction Interval"])
        lines.append(f"- method: {method}")
        if alpha is not None:
            coverage = (1.0 - float(alpha)) * 100.0
            lines.append(f"- alpha: {alpha} ({coverage:.1f}% interval)")
        else:
            lines.append("- alpha: unknown")
        if q_value is not None:
            lines.append(f"- interval: pred ± {q_value}")

    if _count_schema_issues(issues) > 0:
        lines.extend(["", "## Schema Validation Issues"])
        if missing_columns:
            lines.append(f"- missing_columns: {_format_list_preview(missing_columns)}")
        if extra_columns:
            lines.append(f"- extra_columns: {_format_list_preview(extra_columns)}")
        if dtype_mismatch:
            mismatch_cols = [entry.get("column", "") for entry in dtype_mismatch if entry.get("column")]
            lines.append(f"- dtype_mismatch: {_format_list_preview(mismatch_cols)}")
        if coerce_failures:
            lines.append(f"- coerce_failures: {len(coerce_failures)} rows")

    summary_path = output_dir / "summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def _write_input_preview(df, mode: str, output_dir: Path) -> Path:
    if mode == "single":
        path = output_dir / "input_preview.json"
        payload: dict[str, Any] = {}
        if not df.empty:
            row = df.iloc[0].to_dict()
            payload = {str(k): _sanitize_json_value(v) for k, v in row.items()}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    path = output_dir / "input_preview.csv"
    df.head(5).to_csv(path, index=False)
    return path


def _load_preview_sample(path: Path | None, *, max_rows: int = 5) -> list[dict[str, Any]] | None:
    if path is None or not path.exists():
        return None
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if isinstance(payload, list):
            return [dict(row) for row in payload[:max_rows] if isinstance(row, Mapping)]
        if isinstance(payload, Mapping):
            return [dict(payload)]
        return None
    if suffix == ".csv":
        rows: list[dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for idx, row in enumerate(reader):
                    if idx >= max_rows:
                        break
                    rows.append(dict(row))
        except Exception:
            return None
        return rows
    return None


def _log_debug_samples(
    ctx: Any,
    *,
    input_sample: Any | None,
    output_sample: Any | None,
    input_preview_path: Path | None,
    predictions_path: Path | None,
) -> None:
    if ctx is None or getattr(ctx, "task", None) is None:
        return
    if input_sample is None:
        input_sample = _load_preview_sample(input_preview_path)
    if output_sample is None:
        output_sample = _load_preview_sample(predictions_path)
    if input_sample is not None:
        log_debug_table(ctx.task, "infer", "input_sample", input_sample, step=0)
    elif input_preview_path is not None:
        log_debug_text(ctx.task, "infer", "input_sample", f"input preview: {input_preview_path}", step=0)
    if output_sample is not None:
        log_debug_table(ctx.task, "infer", "output_sample", output_sample, step=0)
    elif predictions_path is not None:
        log_debug_text(ctx.task, "infer", "output_sample", f"predictions path: {predictions_path}", step=0)


def _resolve_table_samples(
    input_sample: Any | None,
    output_sample: Any | None,
    *,
    input_preview_path: Path | None,
    predictions_path: Path | None,
) -> tuple[Any | None, Any | None]:
    if input_sample is None:
        input_sample = _load_preview_sample(input_preview_path)
    if output_sample is None:
        output_sample = _load_preview_sample(predictions_path)
    return input_sample, output_sample


def _resolve_input_output_table_settings(cfg: Any) -> dict[str, int]:
    def _as_int(value: Any, default: int) -> int:
        try:
            num = int(value)
        except Exception:
            return default
        return num if num > 0 else default

    return {
        "max_rows": _as_int(_cfg_value(cfg, "infer.plots.max_rows", 5), 5),
        "max_input_columns": _as_int(_cfg_value(cfg, "infer.plots.max_input_columns", 20), 20),
        "max_output_columns": _as_int(_cfg_value(cfg, "infer.plots.max_output_columns", 12), 12),
    }


def _resolve_model_abbr(bundle: Mapping[str, Any], meta: Mapping[str, Any]) -> str | None:
    model_variant = _normalize_str(bundle.get("model_variant"))
    if model_variant:
        return model_variant
    model_id = _normalize_str(meta.get("model_id"))
    if model_id:
        try:
            return Path(model_id).stem or model_id
        except Exception:
            return model_id
    return None


def _resolve_model_provenance(
    bundle: Mapping[str, Any],
    *,
    preprocess_bundle: Mapping[str, Any],
    meta: Mapping[str, Any],
    model_bundle_path: Path,
) -> dict[str, Any]:
    provenance: dict[str, Any] = {}
    raw = bundle.get("provenance")
    if isinstance(raw, Mapping):
        provenance.update(dict(raw))

    if provenance.get("train_task_id") is None:
        provenance["train_task_id"] = _normalize_str(meta.get("train_task_id"))

    if provenance.get("processed_dataset_id") is None:
        provenance["processed_dataset_id"] = _normalize_str(bundle.get("processed_dataset_id"))

    if provenance.get("split_hash") is None:
        provenance["split_hash"] = _normalize_str(bundle.get("split_hash"))

    if provenance.get("recipe_hash") is None:
        provenance["recipe_hash"] = _normalize_str(bundle.get("recipe_hash"))

    if provenance.get("preprocess_variant") is None:
        provenance["preprocess_variant"] = _normalize_str(preprocess_bundle.get("preprocess_variant"))

    if provenance.get("raw_dataset_id") is None:
        provenance["raw_dataset_id"] = _normalize_str(bundle.get("raw_dataset_id"))

    if provenance.get("raw_dataset_id") is None:
        manifest_path = model_bundle_path.parent / "manifest.json"
        if manifest_path.exists():
            try:
                manifest_payload = _load_json(manifest_path)
            except Exception:
                manifest_payload = {}
            inputs = manifest_payload.get("inputs") or {}
            provenance["raw_dataset_id"] = _normalize_str(inputs.get("raw_dataset_id"))

    return {key: value for key, value in provenance.items() if value is not None}


def _preds_to_rows(preds: Any) -> list[list[Any]]:
    if preds is None:
        return []
    if hasattr(preds, "tolist"):
        data = preds.tolist()
    else:
        try:
            data = list(preds)
        except Exception:
            data = preds
    if isinstance(data, list):
        if not data:
            return []
        first = data[0]
        if isinstance(first, (list, tuple)):
            return [list(row) for row in data]
        return [[item] for item in data]
    return [[data]]


def _build_classification_predictions_frame(
    transformed: Any,
    *,
    predictor: Any,
    model: Any,
    threshold_used: float | None,
    class_labels: list[Any] | None,
    label_encoder: Any,
    top_k: int | None,
    proba_prefix: str,
) -> tuple[Any, list[Any]]:
    if not hasattr(predictor, "predict_proba"):
        raise ValueError("classification infer requires predict_proba on the model.")
    proba = predictor.predict_proba(transformed)
    if threshold_used is not None:
        positive_proba = _extract_positive_proba(proba)
        preds = (positive_proba >= threshold_used).astype(int)
    else:
        preds = predictor.predict(transformed)

    if label_encoder is not None and hasattr(label_encoder, "inverse_transform"):
        pred_labels = label_encoder.inverse_transform(preds)
    else:
        pred_labels = preds
        if class_labels:
            try:
                pred_labels = [class_labels[int(idx)] for idx in preds]
            except Exception:
                pred_labels = preds

    if hasattr(pred_labels, "tolist"):
        pred_labels = pred_labels.tolist()
    if not isinstance(pred_labels, list):
        pred_labels = list(pred_labels)

    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for classification probabilities.") from exc

    proba_arr = np.asarray(proba)
    if proba_arr.ndim == 1:
        proba_arr = np.stack([1.0 - proba_arr, proba_arr], axis=1)

    if class_labels is None or len(class_labels) != int(proba_arr.shape[1]):
        class_labels = [str(i) for i in range(int(proba_arr.shape[1]))]

    top_indices = None
    if top_k is not None:
        order = np.argsort(proba_arr, axis=1)[:, ::-1]
        top_indices = order[:, :top_k]

    data: dict[str, list[Any]] = {
        "pred_label": [_sanitize_json_value(label) for label in pred_labels],
    }
    if threshold_used is not None:
        data["threshold_used"] = [_sanitize_json_value(threshold_used)] * len(pred_labels)

    proba_columns = _format_proba_columns(class_labels, prefix=proba_prefix)
    for idx, col_name in enumerate(proba_columns):
        data[col_name] = [_sanitize_json_value(v) for v in proba_arr[:, idx]]

    if top_indices is not None:
        for rank in range(1, top_k + 1):
            labels: list[Any] = []
            probs: list[Any] = []
            for row_idx, col_idx in enumerate(top_indices[:, rank - 1]):
                label = class_labels[col_idx] if class_labels else str(col_idx)
                labels.append(_sanitize_json_value(label))
                probs.append(_sanitize_json_value(proba_arr[row_idx][col_idx]))
            data[f"top{rank}_label"] = labels
            data[f"top{rank}_proba"] = probs

    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for infer.") from exc
    return pd.DataFrame(data), class_labels


def _build_regression_predictions_frame(
    transformed: Any,
    *,
    model: Any,
    uncertainty_enabled: bool,
    uncertainty_q: float | None,
) -> tuple[Any, list[float] | None]:
    preds = model.predict(transformed)
    rows = _preds_to_rows(preds)
    lower = None
    upper = None
    if uncertainty_enabled and uncertainty_q is not None:
        try:
            lower, upper = apply_split_conformal_interval(preds, float(uncertainty_q))
        except ValueError as exc:
            raise ValueError("uncertainty intervals require 1D regression predictions.") from exc

    if rows:
        n_cols = len(rows[0])
    else:
        n_cols = 1

    data: dict[str, list[Any]] = {}
    if n_cols == 1:
        data["prediction"] = [_sanitize_json_value(row[0]) for row in rows] if rows else [None]
        if lower is not None and upper is not None:
            data["pred_lower"] = [_sanitize_json_value(v) for v in lower]
            data["pred_upper"] = [_sanitize_json_value(v) for v in upper]
    else:
        for idx in range(n_cols):
            data[f"prediction_{idx}"] = [
                _sanitize_json_value(row[idx]) if idx < len(row) else None for row in rows
            ]

    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for infer.") from exc
    interval_widths = None
    if lower is not None and upper is not None and n_cols == 1:
        interval_widths = [float(upper[idx] - lower[idx]) for idx in range(len(lower))]
    return pd.DataFrame(data), interval_widths


def _write_predictions_csv_chunk(
    path: Path,
    df: Any,
    *,
    write_mode: str,
    header_written: bool,
) -> bool:
    if write_mode == "append":
        mode = "a"
        header = not path.exists() and not header_written
    else:
        mode = "a" if header_written else "w"
        header = not header_written
    df.to_csv(path, mode=mode, header=header, index=False)
    return True


def _write_predictions_parquet_chunk(path: Path, df: Any, writer: Any | None):
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore
    except Exception as exc:
        raise RuntimeError("pyarrow is required for parquet output.") from exc
    table = pa.Table.from_pandas(df, preserve_index=False)
    if writer is None:
        writer = pq.ParquetWriter(path, table.schema)
    writer.write_table(table)
    return writer


def _update_drift_sample(sample_df: Any, new_df: Any, *, sample_n: int | None, rng: Any):
    if sample_n is None:
        return new_df if sample_df is None else sample_df
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return new_df if sample_df is None else sample_df
    if sample_df is None:
        if len(new_df) <= sample_n:
            return new_df
        if rng is not None:
            return new_df.sample(n=sample_n, random_state=int(rng.integers(0, 1_000_000_000)))
        return new_df.head(sample_n)
    combined = pd.concat([sample_df, new_df], ignore_index=True)
    if len(combined) <= sample_n:
        return combined
    if rng is not None:
        return combined.sample(n=sample_n, random_state=int(rng.integers(0, 1_000_000_000)))
    return combined.head(sample_n)


def _update_interval_width_sample(
    sample: list[float],
    widths: list[float],
    *,
    rng: Any,
) -> list[float]:
    if not widths:
        return sample
    sample.extend([float(value) for value in widths])
    if len(sample) <= _INTERVAL_WIDTH_SAMPLE_LIMIT:
        return sample
    if rng is not None:
        try:
            import numpy as np  # type: ignore
        except Exception:
            return sample[:_INTERVAL_WIDTH_SAMPLE_LIMIT]
        sample = list(np.asarray(sample)[
            rng.choice(len(sample), size=_INTERVAL_WIDTH_SAMPLE_LIMIT, replace=False)
        ])
        return sample
    return sample[:_INTERVAL_WIDTH_SAMPLE_LIMIT]


def _resolve_class_labels(bundle: Mapping[str, Any], model: Any) -> list[Any] | None:
    labels = bundle.get("class_labels")
    if isinstance(labels, (list, tuple)):
        return list(labels)
    label_encoder = bundle.get("label_encoder")
    classes = getattr(label_encoder, "classes_", None)
    if classes is not None:
        return list(classes)
    model_classes = getattr(model, "classes_", None)
    if model_classes is not None:
        return list(model_classes)
    return None


def _build_proba_column_labels(labels: Sequence[Any]) -> list[str]:
    seen: set[str] = set()
    safe_labels: list[str] = []
    for idx, label in enumerate(labels):
        safe = re.sub(r"[^0-9A-Za-z_]+", "_", str(label)).strip("_")
        if not safe:
            safe = str(idx)
        if safe in seen:
            safe = f"{safe}_{idx}"
        seen.add(safe)
        safe_labels.append(safe)
    return safe_labels


def _format_proba_columns(labels: Sequence[Any], *, prefix: str = "proba_") -> list[str]:
    return [f"{prefix}{safe}" for safe in _build_proba_column_labels(labels)]


def _build_proba_payload(values: Sequence[Any], labels: Sequence[Any] | None) -> Any:
    if labels:
        return {
            str(label): _sanitize_json_value(value)
            for label, value in zip(labels, values)
        }
    return [_sanitize_json_value(value) for value in values]


def _prepare_inputs(cfg: Any, preprocess_bundle: dict[str, Any], mode: str):
    infer_cfg = getattr(cfg, "infer", None)
    dataset_path = _normalize_str(getattr(infer_cfg, "input_path", None))
    if not dataset_path:
        dataset_path = _normalize_str(getattr(getattr(cfg, "data", None), "dataset_path", None))

    input_payload = _parse_input_payload(getattr(infer_cfg, "input_json", None))

    df = None
    resolved_path = None

    if input_payload is not None:
        df = _frame_from_payload(input_payload)
    elif dataset_path:
        path = Path(dataset_path).expanduser().resolve()
        if path.suffix.lower() == ".json":
            input_payload = _load_json(path)
            df = _frame_from_payload(input_payload)
        else:
            data_path = _select_tabular_file(path)
            df = _load_dataframe(data_path)
            resolved_path = str(data_path)
    else:
        df = _build_dummy_input(preprocess_bundle)

    if df is None:
        raise RuntimeError("infer failed to resolve input data.")

    if mode == "single":
        return df.head(1), resolved_path or dataset_path
    if mode == "batch":
        if input_payload is not None and resolved_path is None and not dataset_path:
            return df, None
        if not (resolved_path or dataset_path):
            raise ValueError("infer.input_path or data.dataset_path is required for batch mode.")
    return df, resolved_path or dataset_path


def _validate_inputs(
    df,
    preprocess_bundle: Mapping[str, Any],
    *,
    validation_mode: str,
) -> tuple[Any, dict[str, Any]]:
    issue_info = _collect_schema_issues(df, preprocess_bundle)
    feature_columns = issue_info.get("feature_columns") or []
    expected_dtypes = issue_info.get("expected_dtypes") or {}
    dtype_mismatch = list(issue_info.get("dtype_mismatch") or [])

    coerce_failures: list[dict[str, Any]] = []
    if validation_mode == "coerce":
        df = df.copy()
        df, coerce_failures = _coerce_frame_to_schema(
            df,
            expected_dtypes=expected_dtypes,
            feature_columns=feature_columns,
        )
        for entry in dtype_mismatch:
            col = entry.get("column")
            if col in df.columns:
                entry["actual_after"] = str(df[col].dtype)
                entry["coerced"] = True

    issues = {
        "missing_columns": list(issue_info.get("missing_columns") or []),
        "extra_columns": list(issue_info.get("extra_columns") or []),
        "dtype_mismatch": dtype_mismatch,
        "coerce_failures": coerce_failures,
    }
    total_issues = _count_schema_issues(issues)
    ok = total_issues == 0

    if validation_mode == "strict":
        warnings_count = 0
        errors_count = total_issues
    else:
        warnings_count = total_issues
        errors_count = 0

    if not (validation_mode == "strict" and total_issues > 0):
        df, _ = _align_input_frame(df, preprocess_bundle, allow_missing=(validation_mode != "strict"))

    return df, {
        "issues": issues,
        "warnings_count": warnings_count,
        "errors_count": errors_count,
        "ok": ok,
    }


def run(cfg: Any) -> None:
    identity = apply_clearml_identity(cfg, stage=cfg.task.stage)
    ctx = init_task_context(
        cfg,
        stage=cfg.task.stage,
        task_name="infer",
        tags=identity.tags,
        properties=identity.user_properties,
    )
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)
    mode = _resolve_mode(cfg)
    if mode not in ("single", "batch", "optimize"):
        raise ValueError(f"Unsupported infer mode: {mode}")
    validation_mode = _resolve_validation_mode(cfg)
    if validation_mode not in ("warn", "strict", "coerce"):
        raise ValueError(f"Unsupported infer.validation.mode: {validation_mode}")
    optimize_settings = _resolve_optimize_settings(cfg) if mode == "optimize" else None
    drift_settings = resolve_drift_settings(cfg)
    debug_input_sample: Any | None = None
    debug_output_sample: Any | None = None
    infer_cfg = getattr(cfg, "infer", None)
    batch_cfg = getattr(infer_cfg, "batch", None)
    optimize_cfg = getattr(infer_cfg, "optimize", None)
    has_input_json = _has_payload(getattr(infer_cfg, "input_json", None))
    has_input_path = _normalize_str(getattr(infer_cfg, "input_path", None)) is not None
    has_batch_inputs_json = _has_payload(getattr(batch_cfg, "inputs_json", None))
    has_batch_inputs_path = _normalize_str(getattr(batch_cfg, "inputs_path", None)) is not None
    has_search_space = _has_payload(getattr(optimize_cfg, "search_space", None))
    _validate_infer_input_sources(
        mode=mode,
        has_input_json=has_input_json,
        has_input_path=has_input_path,
        has_batch_inputs_json=has_batch_inputs_json,
        has_batch_inputs_path=has_batch_inputs_path,
        has_search_space=has_search_space,
    )
    model_id_value = _normalize_str(getattr(infer_cfg, "model_id", None))
    model_bundle_path_value = _normalize_str(getattr(infer_cfg, "model_bundle_path", None))
    train_task_id_value = _normalize_str(getattr(infer_cfg, "train_task_id", None))
    input_payload = _parse_input_payload(getattr(infer_cfg, "input_json", None))
    batch_inputs_payload = _parse_batch_inputs_payload(getattr(batch_cfg, "inputs_json", None))
    if mode == "batch" and batch_inputs_payload is None:
        batch_inputs_payload = input_payload
    batch_inputs_path_value = _normalize_str(getattr(batch_cfg, "inputs_path", None))
    input_path_value = _resolve_batch_input_path(cfg, mode=mode)
    use_batch_children = (
        mode == "batch"
        and clearml_enabled
        and (batch_inputs_payload is not None or batch_inputs_path_value)
    )
    use_optimize_children = mode == "optimize" and clearml_enabled
    is_child_task = _parse_bool(_cfg_value(cfg, "infer.batch.child_task")) or _parse_bool(
        _cfg_value(cfg, "infer.optimize.child_task")
    )
    connect_payload = batch_inputs_payload if mode == "batch" and batch_inputs_payload is not None else input_payload
    input_source = None
    input_json_label = None
    if connect_payload is not None:
        input_source = "json"
        input_json_label = "inline"
    elif input_path_value:
        input_source = "path"
    else:
        input_source = "generated"
    if mode == "optimize":
        input_source = "search_space"
    table_settings = _resolve_input_output_table_settings(cfg)
    include_dataset = not (
        (mode == "batch" and use_batch_children and not is_child_task)
        or (mode == "optimize" and use_optimize_children and not is_child_task)
    )
    include_execution = not is_child_task
    optimize_hparams = None
    if mode == "optimize" and not is_child_task:
        optimize_hparams = _build_optimize_hparams(optimize_settings)
    dry_run = bool(getattr(infer_cfg, "dry_run", False))
    if not dry_run and not (model_id_value or train_task_id_value or model_bundle_path_value):
        raise ValueError("infer.model_id or infer.train_task_id (or infer.model_bundle_path) is required.")
    if clearml_enabled:
        summary_lines = [
            f"mode: {mode}",
            f"input_source: {input_source}",
            f"model_id: {model_id_value or 'n/a'}",
            f"train_task_id: {train_task_id_value or 'n/a'}",
            f"search_space: {'set' if has_search_space else 'none'}",
        ]
        log_debug_text(ctx.task, "infer", "settings", "\n".join(summary_lines), step=0)

    if dry_run:
        model_id = _normalize_str(getattr(infer_cfg, "model_id", None)) or _normalize_str(
            getattr(infer_cfg, "model_bundle_path", None)
        )
        train_task_id = _normalize_str(getattr(infer_cfg, "train_task_id", None))
        connect_infer(
            ctx,
            cfg,
            model_id=model_id or "dry_run",
            model_abbr=None,
            infer_mode=mode,
            schema_policy=validation_mode,
            input_source=input_source,
            input_path=input_path_value,
            input_json=input_json_label,
            provenance={
                "train_task_id": train_task_id,
            },
            optimize_payload=optimize_hparams,
            include_dataset=include_dataset,
            include_execution=include_execution,
        )

        if mode == "optimize":
            trials_path = ctx.output_dir / "optimize_trials.csv"
            trials_path.write_text("", encoding="utf-8")
            summary_path = ctx.output_dir / "optimize_summary.json"
            summary_payload = {
                "n_trials": optimize_settings.get("n_trials") if optimize_settings else None,
                "direction": optimize_settings.get("direction") if optimize_settings else None,
                "objective_keys": optimize_settings.get("objective_keys") if optimize_settings else None,
                "search_space": optimize_settings.get("search_space") if optimize_settings else None,
            }
            summary_path.write_text(
                json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            if clearml_enabled:
                upload_artifact(ctx, trials_path.name, trials_path)
                upload_artifact(ctx, summary_path.name, summary_path)

            out = {
                "mode": mode,
                "model_id": model_id or "dry_run",
                "train_task_id": train_task_id,
                "schema_validation": {
                    "mode": validation_mode,
                    "ok": True,
                    "warnings_count": 0,
                    "errors_count": 0,
                },
                "optimize": {
                    "n_trials": optimize_settings.get("n_trials") if optimize_settings else None,
                    "direction": optimize_settings.get("direction") if optimize_settings else None,
                    "objective_keys": optimize_settings.get("objective_keys") if optimize_settings else None,
                },
                "optimize_trials_path": str(trials_path),
                "optimize_summary_path": str(summary_path),
                "dry_run": True,
            }
            write_out_json(ctx, out)

            versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
            inputs = {
                "model_id": model_id,
                "train_task_id": train_task_id,
                "mode": mode,
                "input_path": input_path_value,
                "dry_run": True,
            }
            outputs = {
                "optimize_trials_path": str(trials_path),
                "optimize_summary_path": str(summary_path),
            }
            manifest = {
                "schema_version": versions.get("schema_version", "unknown"),
                "code_version": versions.get("code_version", "unknown"),
                "platform_version": versions.get("platform_version", "unknown"),
                "process": "infer",
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "inputs": inputs,
                "outputs": outputs,
                "hashes": {
                    "config_hash": hash_config(cfg),
                    "split_hash": "dry_run",
                    "recipe_hash": "dry_run",
                },
            }
            write_manifest(ctx, manifest)
            return

        if mode == "single":
            predictions_path = ctx.output_dir / "prediction.json"
            predictions_path.write_text(
                json.dumps({"prediction": None}, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            input_preview_path = ctx.output_dir / "input_preview.json"
            input_preview_path.write_text("{}", encoding="utf-8")
        else:
            predictions_path = ctx.output_dir / "predictions.csv"
            predictions_path.write_text("", encoding="utf-8")
            input_preview_path = ctx.output_dir / "input_preview.csv"
            input_preview_path.write_text("", encoding="utf-8")

        if clearml_enabled:
            upload_artifact(ctx, predictions_path.name, predictions_path)
            upload_artifact(ctx, input_preview_path.name, input_preview_path)

        out = {
            "predictions_path": str(predictions_path),
            "input_preview_path": str(input_preview_path),
            "mode": mode,
            "model_id": model_id or "dry_run",
            "train_task_id": train_task_id,
            "schema_validation": {
                "mode": validation_mode,
                "ok": True,
                "warnings_count": 0,
                "errors_count": 0,
            },
            "dry_run": True,
        }
        write_out_json(ctx, out)

        versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
        inputs = {
            "model_id": model_id,
            "train_task_id": train_task_id,
            "mode": mode,
            "input_path": input_path_value,
            "dry_run": True,
        }
        outputs = {
            "predictions_path": str(predictions_path),
            "input_preview_path": str(input_preview_path),
        }
        manifest = {
            "schema_version": versions.get("schema_version", "unknown"),
            "code_version": versions.get("code_version", "unknown"),
            "platform_version": versions.get("platform_version", "unknown"),
            "process": "infer",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "inputs": inputs,
            "outputs": outputs,
            "hashes": {
                "config_hash": hash_config(cfg),
                "split_hash": "dry_run",
                "recipe_hash": "dry_run",
            },
        }
        write_manifest(ctx, manifest)
        return

    model_bundle_path, meta = _resolve_model_bundle_path(cfg, clearml_enabled=clearml_enabled)
    bundle = load_bundle(model_bundle_path)
    if not isinstance(bundle, dict):
        raise ValueError("model_bundle.joblib is invalid.")

    model = bundle.get("model")
    calibrated_model = bundle.get("calibrated_model")
    preprocess_bundle = bundle.get("preprocess_bundle") or {}
    processed_dataset_id = _normalize_str(bundle.get("processed_dataset_id"))
    split_hash = _normalize_str(bundle.get("split_hash"))
    recipe_hash = _normalize_str(bundle.get("recipe_hash"))
    task_type = _normalize_task_type(bundle.get("task_type"))
    n_classes = bundle.get("n_classes")
    try:
        n_classes = int(n_classes) if n_classes is not None else None
    except Exception:
        n_classes = None
    if model is None or not isinstance(preprocess_bundle, dict):
        raise ValueError("model_bundle is missing model or preprocess_bundle.")
    if not split_hash or not recipe_hash:
        raise ValueError("model_bundle is missing split_hash or recipe_hash.")

    config_processed_dataset_id = _normalize_str(_cfg_value(cfg, "data.processed_dataset_id"))
    if config_processed_dataset_id and processed_dataset_id:
        if config_processed_dataset_id != processed_dataset_id:
            message = (
                "data.processed_dataset_id does not match model_bundle processed_dataset_id "
                f"({config_processed_dataset_id} != {processed_dataset_id})."
            )
            if validation_mode == "strict":
                raise ValueError(message)
            warnings.warn(message)
    dataset_id_for_check = config_processed_dataset_id or processed_dataset_id
    _verify_processed_dataset(
        cfg,
        processed_dataset_id=dataset_id_for_check,
        recipe_hash=recipe_hash,
        validation_mode=validation_mode,
    )
    model_abbr = _resolve_model_abbr(bundle, meta)
    provenance = _resolve_model_provenance(
        bundle,
        preprocess_bundle=preprocess_bundle,
        meta=meta,
        model_bundle_path=model_bundle_path,
    )
    connect_infer(
        ctx,
        cfg,
        model_id=_normalize_str(meta.get("model_id")) or str(model_bundle_path),
        model_abbr=model_abbr,
        infer_mode=mode,
        schema_policy=validation_mode,
        input_source=input_source,
        input_path=input_path_value,
        input_json=input_json_label,
        provenance=provenance,
        optimize_payload=optimize_hparams,
        include_dataset=include_dataset,
        include_execution=include_execution,
    )

    columns_info = preprocess_bundle.get("columns") or {}
    quality_target = _normalize_str(
        columns_info.get("target_column") or _cfg_value(cfg, "data.target_column")
    )
    quality_id_columns = columns_info.get("id_columns") or _cfg_value(cfg, "data.id_columns") or []

    calibration_info = _resolve_calibration_info(bundle)
    predictor = calibrated_model if calibrated_model is not None else model
    uncertainty_info = _resolve_uncertainty_settings(cfg, bundle, task_type=task_type)

    batch_settings = _resolve_batch_settings(cfg)
    chunk_size = batch_settings["chunk_size"]
    output_format = batch_settings["output_format"]
    write_mode = batch_settings["write_mode"]
    max_rows = batch_settings["max_rows"]

    batch_children_settings = _resolve_batch_children_settings(cfg)
    batch_inputs_df = None
    batch_inputs_path = None
    if mode == "batch" and (batch_inputs_payload is not None or batch_inputs_path_value):
        batch_inputs_df, batch_inputs_path = _load_batch_inputs(
            batch_inputs_payload,
            batch_inputs_path_value or input_path_value,
            max_rows=batch_children_settings["max_children"],
        )

    if mode == "optimize":
        if not clearml_enabled:
            raise ValueError("infer.mode=optimize requires ClearML; set run.clearml.enabled=true.")
        if not optimize_settings:
            raise ValueError("infer.optimize settings are required for optimize mode.")
        search_space = optimize_settings.get("search_space") or []
        if not search_space:
            raise ValueError("infer.optimize.search_space is required for optimize mode.")

        base_df, base_input_path = _prepare_inputs(cfg, preprocess_bundle, "single")
        base_df, validation = _validate_inputs(
            base_df,
            preprocess_bundle,
            validation_mode=validation_mode,
        )
        issues = validation.get("issues") or {}
        errors_json_path: Path | None = None
        errors_csv_path: Path | None = None
        if _count_schema_issues(issues) > 0:
            errors_json_path, errors_csv_path = _write_schema_errors(ctx.output_dir, issues)
        summary_path = _write_infer_summary(
            ctx.output_dir,
            mode=mode,
            validation_mode=validation_mode,
            validation=validation,
            errors_path=errors_json_path,
            uncertainty=uncertainty_info,
        )
        if clearml_enabled:
            upload_artifact(ctx, summary_path.name, summary_path)
            if errors_json_path is not None:
                upload_artifact(ctx, errors_json_path.name, errors_json_path)
                upload_artifact(ctx, errors_csv_path.name, errors_csv_path)
        if validation_mode == "strict" and not validation.get("ok"):
            raise ValueError("Input schema validation failed; see errors.json for details.")

        input_preview_path = _write_input_preview(base_df, "single", ctx.output_dir)
        if clearml_enabled:
            upload_artifact(ctx, input_preview_path.name, input_preview_path)

        base_records = _frame_to_records(base_df)
        base_record = base_records[0] if base_records else {}
        feature_columns, _, _, _ = _resolve_preprocess_columns(preprocess_bundle)
        if feature_columns:
            search_names = [entry.get("name") for entry in search_space if entry.get("name")]
            missing = [name for name in search_names if name not in feature_columns]
            if missing:
                log_debug_text(
                    ctx.task,
                    "infer",
                    "optimize_search_space_warning",
                    f"search_space columns not in feature_columns: {missing}",
                    step=0,
                )

        queue_name = _resolve_child_queue(cfg)
        if not queue_name:
            raise ValueError("run.clearml.queue_name is required to enqueue optimize child tasks.")

        source_task_id = _normalize_str(_cfg_value(cfg, "run.clearml.clone_from_task_id"))
        if not source_task_id:
            source_task_id = str(getattr(ctx.task, "id", ""))
        if not source_task_id:
            raise PlatformAdapterError("ClearML task id is required to clone optimize child tasks.")

        child_model_id = _normalize_str(getattr(infer_cfg, "model_id", None)) or _normalize_str(
            meta.get("model_id")
        )
        child_train_task_id = _normalize_str(getattr(infer_cfg, "train_task_id", None)) or _normalize_str(
            meta.get("train_task_id")
        )
        if not child_model_id and not child_train_task_id:
            raise ValueError("infer.model_id or infer.train_task_id is required for optimize child tasks.")

        try:
            import optuna  # type: ignore
            from optuna.trial import TrialState  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "Optuna is required for infer.mode=optimize. Install with: "
                "uv sync --extra optuna (or pip install optuna)"
            ) from exc

        sampler = _build_optuna_sampler(
            optimize_settings.get("sampler_name"),
            optimize_settings.get("sampler_seed"),
        )
        study = optuna.create_study(direction=optimize_settings.get("direction"), sampler=sampler)

        completed = {"completed", "closed"}
        trial_rows: list[dict[str, Any]] = []
        child_rows: list[dict[str, Any]] = []
        objective_keys = optimize_settings.get("objective_keys") or ["prediction"]

        for _ in range(int(optimize_settings.get("n_trials") or 0)):
            trial = study.ask()
            params = _suggest_optuna_params(trial, search_space)
            trial_number = int(trial.number) + 1
            record = dict(base_record)
            for key, value in params.items():
                record[str(key)] = _sanitize_json_value(value)

            payload = json.dumps(record, ensure_ascii=True, separators=(",", ":"))
            child_name = f"infer__single__trial={trial_number}"
            if model_abbr:
                child_name = f"infer__single__model={model_abbr}__trial={trial_number}"
            overrides: dict[str, Any] = {
                "infer.mode": "single",
                "infer.input_json": payload,
                "infer.dry_run": False,
                "infer.validation.mode": validation_mode,
                "infer.optimize.child_task": True,
                "run.clearml.execution": "logging",
                "run.clearml.queue_name": queue_name,
                "run.clearml.enabled": True,
                "+run.clearml.task_name": child_name,
            }
            if child_train_task_id:
                overrides["infer.train_task_id"] = child_train_task_id
            else:
                overrides["infer.model_id"] = child_model_id

            child_task_id = clone_clearml_task(
                source_task_id=source_task_id,
                task_name=child_name,
            )
            # Clear inherited Args (e.g., optimize settings) so child tasks only use overrides.
            reset_clearml_task_args(child_task_id, [])
            set_clearml_task_parameters(child_task_id, overrides)
            enqueue_clearml_task(child_task_id, queue_name)

            statuses = _wait_for_child_tasks(
                [child_task_id],
                timeout_sec=optimize_settings.get("wait_timeout_sec"),
                poll_interval_sec=optimize_settings.get("poll_interval_sec"),
            )
            status = statuses.get(child_task_id, "unknown")
            child_url = resolve_clearml_task_url(cfg, child_task_id)
            child_rows.append(
                {
                    "trial_number": trial_number,
                    "task_id": child_task_id,
                    "status": status,
                    "url": child_url,
                }
            )

            payload_out = None
            error = None
            if status in completed:
                try:
                    pred_path = get_task_artifact_local_copy(cfg, child_task_id, "prediction.json")
                    payload_out = _load_prediction_payload(pred_path)
                except Exception as exc:
                    error = str(exc)
            else:
                error = f"child_status={status}"

            output_flat = _flatten_prediction_payload(payload_out or {})
            objective_value = _resolve_objective_value(output_flat, objective_keys)
            if objective_value is None:
                study.tell(trial, state=TrialState.FAIL)
            else:
                study.tell(trial, objective_value)

            row: dict[str, Any] = {
                "trial_number": trial_number,
                "objective": objective_value,
                "state": "complete" if objective_value is not None else "fail",
                "child_task_id": child_task_id,
                "child_status": status,
                "child_url": child_url,
            }
            if error:
                row["error"] = error
            elif objective_value is None:
                row["error"] = "objective_value_missing"
            for key, value in params.items():
                row[f"in.{key}"] = _sanitize_json_value(value)
            for key, value in output_flat.items():
                row[f"out.{key}"] = value
            trial_rows.append(row)

        try:
            import pandas as pd  # type: ignore
        except Exception as exc:
            raise RuntimeError("pandas is required for infer.") from exc

        trials_path = ctx.output_dir / "optimize_trials.csv"
        pd.DataFrame(trial_rows).to_csv(trials_path, index=False)
        if clearml_enabled:
            upload_artifact(ctx, trials_path.name, trials_path)

        completed_trials = [row for row in trial_rows if isinstance(row.get("objective"), numbers.Real)]
        direction = optimize_settings.get("direction") or "maximize"
        reverse = direction == "maximize"
        ranked = sorted(completed_trials, key=lambda r: float(r.get("objective", 0.0)), reverse=reverse)
        top_k = int(optimize_settings.get("top_k") or 0)
        top_trials = ranked[:top_k] if top_k > 0 else ranked

        top_inputs: list[dict[str, Any]] = []
        top_outputs: list[dict[str, Any]] = []
        for row in top_trials:
            input_row = {key[3:]: row[key] for key in row if isinstance(key, str) and key.startswith("in.")}
            output_row = {key[4:]: row[key] for key in row if isinstance(key, str) and key.startswith("out.")}
            top_inputs.append(input_row)
            top_outputs.append(output_row)

        best_value = None
        best_params = None
        if ranked:
            best_value = ranked[0].get("objective")
            best_params = {
                key[3:]: ranked[0][key]
                for key in ranked[0]
                if isinstance(key, str) and key.startswith("in.")
            }

        if clearml_enabled:
            history_fig = build_optimization_history(
                study,
                log_scale=bool(optimize_settings.get("history_log_scale")),
                output_path=ctx.output_dir / "optuna_history.png",
            )
            log_plotly(ctx.task, "infer", "optuna_history", history_fig, step=0)
            parallel_fig = build_parallel_coordinate(
                study,
                output_path=ctx.output_dir / "optuna_parallel.png",
            )
            log_plotly(ctx.task, "infer", "optuna_parallel", parallel_fig, step=0)
            importance_fig = build_param_importance(
                study,
                output_path=ctx.output_dir / "optuna_importance.png",
            )
            log_plotly(ctx.task, "infer", "optuna_importance", importance_fig, step=0)
            contour_params = optimize_settings.get("contour_params")
            if not contour_params:
                contour_params = [
                    entry.get("name") for entry in search_space if entry.get("name")
                ][:2]
            if contour_params and len(contour_params) >= 2:
                contour_fig = build_contour(
                    study,
                    params=contour_params,
                    output_path=ctx.output_dir / "optuna_contour.png",
                )
                log_plotly(ctx.task, "infer", "optuna_contour", contour_fig, step=0)
            report_input_output_table(
                ctx.task,
                "infer",
                "input_output_table",
                top_inputs,
                top_outputs,
                max_rows=table_settings["max_rows"],
                max_input_columns=table_settings["max_input_columns"],
                max_output_columns=table_settings["max_output_columns"],
                output_path=ctx.output_dir / "optimize_input_output_table.png",
                step=0,
            )
            log_debug_table(ctx.task, "infer", "optimize_trials", trial_rows, step=0)
            log_debug_table(ctx.task, "infer", "optimize_child_tasks", child_rows, step=0)

        out = {
            "optimize_trials_path": str(trials_path),
            "input_preview_path": str(input_preview_path),
            "mode": mode,
            "model_id": meta.get("model_id") or str(model_bundle_path),
            "train_task_id": meta.get("train_task_id"),
            "schema_validation": {
                "mode": validation_mode,
                "ok": bool(validation.get("ok")),
                "warnings_count": int(validation.get("warnings_count") or 0),
                "errors_count": int(validation.get("errors_count") or 0),
            },
            "optimize": {
                "n_trials": optimize_settings.get("n_trials"),
                "direction": optimize_settings.get("direction"),
                "objective_keys": objective_keys,
                "completed": len(completed_trials),
                "failed": len(trial_rows) - len(completed_trials),
                "best_value": best_value,
                "best_params": best_params,
                "top_k": top_k,
            },
            "child_tasks": child_rows,
        }
        if errors_json_path is not None:
            out["errors_path"] = str(errors_json_path)
        write_out_json(ctx, out)

        versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
        inputs = {
            "model_id": meta.get("model_id") or str(model_bundle_path),
            "train_task_id": meta.get("train_task_id"),
            "mode": mode,
            "input_path": base_input_path,
            "processed_dataset_id": processed_dataset_id,
            "split_hash": split_hash,
            "recipe_hash": recipe_hash,
        }
        outputs = {
            "optimize_trials_path": str(trials_path),
            "input_preview_path": str(input_preview_path),
            "summary_path": str(summary_path),
        }
        if errors_json_path is not None:
            outputs["errors_path"] = str(errors_json_path)
        manifest = {
            "schema_version": versions.get("schema_version", "unknown"),
            "code_version": versions.get("code_version", "unknown"),
            "platform_version": versions.get("platform_version", "unknown"),
            "process": "infer",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "inputs": inputs,
            "outputs": outputs,
            "hashes": {
                "config_hash": hash_config(cfg),
                "split_hash": split_hash,
                "recipe_hash": recipe_hash,
            },
        }
        write_manifest(ctx, manifest)
        return

    if use_batch_children and batch_inputs_df is not None:
        validation_df, validation = _validate_inputs(
            batch_inputs_df.copy(),
            preprocess_bundle,
            validation_mode=validation_mode,
        )
        issues = validation.get("issues") or {}
        errors_json_path: Path | None = None
        errors_csv_path: Path | None = None
        if _count_schema_issues(issues) > 0:
            errors_json_path, errors_csv_path = _write_schema_errors(ctx.output_dir, issues)
        summary_path = _write_infer_summary(
            ctx.output_dir,
            mode=mode,
            validation_mode=validation_mode,
            validation=validation,
            errors_path=errors_json_path,
            uncertainty=uncertainty_info,
        )
        if clearml_enabled:
            upload_artifact(ctx, summary_path.name, summary_path)
            if errors_json_path is not None:
                upload_artifact(ctx, errors_json_path.name, errors_json_path)
                upload_artifact(ctx, errors_csv_path.name, errors_csv_path)
        if validation_mode == "strict" and not validation.get("ok"):
            raise ValueError("Input schema validation failed; see errors.json for details.")

        input_preview_path = _write_input_preview(validation_df, mode, ctx.output_dir)
        input_records = _frame_to_records(validation_df)
        condition_ids = list(range(1, len(input_records) + 1))

        child_task_ids: list[str] = []
        child_rows: list[dict[str, Any]] = []
        completed = {"completed", "closed"}
        statuses: dict[str, str] = {}
        if input_records:
            queue_name = _resolve_child_queue(cfg)
            if not queue_name:
                raise ValueError("run.clearml.queue_name is required to enqueue batch child tasks.")

            source_task_id = _normalize_str(_cfg_value(cfg, "run.clearml.clone_from_task_id"))
            if not source_task_id:
                source_task_id = str(getattr(ctx.task, "id", ""))
            if not source_task_id:
                raise PlatformAdapterError("ClearML task id is required to clone batch child tasks.")

            child_model_id = _normalize_str(getattr(infer_cfg, "model_id", None)) or _normalize_str(
                meta.get("model_id")
            )
            child_train_task_id = _normalize_str(getattr(infer_cfg, "train_task_id", None)) or _normalize_str(
                meta.get("train_task_id")
            )
            if not child_model_id and not child_train_task_id:
                raise ValueError("infer.model_id or infer.train_task_id is required for batch child tasks.")

            for idx, record in enumerate(input_records, start=1):
                payload = json.dumps(record, ensure_ascii=True, separators=(",", ":"))
                child_name = f"infer__single__case={idx}"
                if model_abbr:
                    child_name = f"infer__single__model={model_abbr}__case={idx}"
                overrides: dict[str, Any] = {
                    "infer.mode": "single",
                    "infer.input_json": payload,
                    "infer.dry_run": False,
                    "infer.validation.mode": validation_mode,
                    "infer.batch.child_task": True,
                    "run.clearml.execution": "logging",
                    "run.clearml.queue_name": queue_name,
                    "run.clearml.enabled": True,
                    "run.clearml.task_name": child_name,
                }
                if child_train_task_id:
                    overrides["infer.train_task_id"] = child_train_task_id
                else:
                    overrides["infer.model_id"] = child_model_id

                child_task_id = clone_clearml_task(
                    source_task_id=source_task_id,
                    task_name=child_name,
                )
                set_clearml_task_parameters(child_task_id, overrides)
                enqueue_clearml_task(child_task_id, queue_name)
                child_task_ids.append(child_task_id)
                child_rows.append(
                    {
                        "condition_id": idx,
                        "task_id": child_task_id,
                        "status": "queued",
                        "url": resolve_clearml_task_url(cfg, child_task_id),
                    }
                )

            statuses = _wait_for_child_tasks(
                child_task_ids,
                timeout_sec=batch_children_settings["wait_timeout_sec"],
                poll_interval_sec=batch_children_settings["poll_interval_sec"],
            )

        output_rows: list[dict[str, Any]] = []
        for row in child_rows:
            task_id = row["task_id"]
            status = statuses.get(task_id, "unknown")
            row["status"] = status
            payload = None
            error = None
            if status in completed:
                try:
                    pred_path = get_task_artifact_local_copy(cfg, task_id, "prediction.json")
                    payload = _load_prediction_payload(pred_path)
                except Exception as exc:
                    error = str(exc)
            output_row = {
                "condition_id": row["condition_id"],
                "child_task_id": task_id,
                "child_status": status,
            }
            if payload is not None:
                output_row.update(_flatten_prediction_payload(payload))
            if error:
                output_row["child_error"] = error
            output_rows.append(output_row)

        try:
            import pandas as pd  # type: ignore
        except Exception as exc:
            raise RuntimeError("pandas is required for infer.") from exc
        input_df = pd.DataFrame(input_records)
        if condition_ids:
            input_df.insert(0, "condition_id", condition_ids)
        output_df = pd.DataFrame(output_rows)

        predictions_path = ctx.output_dir / "predictions.csv"
        output_df.to_csv(predictions_path, index=False)

        if clearml_enabled:
            upload_artifact(ctx, predictions_path.name, predictions_path)
            upload_artifact(ctx, input_preview_path.name, input_preview_path)
            table_rows = batch_children_settings["max_children"] or len(input_df)
            table_fig = build_input_output_table(
                input_df,
                output_df,
                max_rows=table_rows,
                max_input_columns=table_settings["max_input_columns"],
                max_output_columns=table_settings["max_output_columns"],
                title="Batch Inputs -> Predictions",
                output_path=ctx.output_dir / "batch_input_output_table.png",
            )
            log_plotly(ctx.task, "infer", "batch_input_output_table", table_fig, step=0)
            dist_values, dist_labels = _select_distribution_samples(output_df)
            if dist_values:
                dist_fig = build_prediction_histogram(
                    dist_values,
                    title="Prediction Distribution",
                    output_path=ctx.output_dir / "prediction_distribution.png",
                )
                log_plotly(ctx.task, "infer", "prediction_distribution", dist_fig, step=0)
            elif dist_labels:
                label_fig = build_label_distribution(
                    dist_labels,
                    title="Prediction Labels",
                    output_path=ctx.output_dir / "prediction_labels.png",
                )
                log_plotly(ctx.task, "infer", "prediction_labels", label_fig, step=0)
            log_debug_table(ctx.task, "infer", "batch_child_tasks", child_rows, step=0)

        out = {
            "predictions_path": str(predictions_path),
            "input_preview_path": str(input_preview_path),
            "mode": mode,
            "model_id": meta.get("model_id") or str(model_bundle_path),
            "train_task_id": meta.get("train_task_id"),
            "schema_validation": {
                "mode": validation_mode,
                "ok": bool(validation.get("ok")),
                "warnings_count": int(validation.get("warnings_count") or 0),
                "errors_count": int(validation.get("errors_count") or 0),
            },
            "batch_children": {
                "inputs_path": batch_inputs_path,
                "inputs_count": len(input_records),
                "child_tasks": len(child_task_ids),
                "completed": sum(1 for status in statuses.values() if status in completed),
                "failed": sum(1 for status in statuses.values() if status == "failed"),
                "timeouts": sum(1 for status in statuses.values() if status == "timeout"),
                "max_children": batch_children_settings["max_children"],
            },
            "child_tasks": child_rows,
        }
        if errors_json_path is not None:
            out["errors_path"] = str(errors_json_path)
        write_out_json(ctx, out)

        versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
        inputs = {
            "model_id": meta.get("model_id") or str(model_bundle_path),
            "train_task_id": meta.get("train_task_id"),
            "mode": mode,
            "input_path": batch_inputs_path,
            "processed_dataset_id": processed_dataset_id,
            "split_hash": split_hash,
            "recipe_hash": recipe_hash,
        }
        outputs = {
            "predictions_path": str(predictions_path),
            "input_preview_path": str(input_preview_path),
        }
        if errors_json_path is not None:
            outputs["errors_path"] = str(errors_json_path)
        manifest = {
            "schema_version": versions.get("schema_version", "unknown"),
            "code_version": versions.get("code_version", "unknown"),
            "platform_version": versions.get("platform_version", "unknown"),
            "process": "infer",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "inputs": inputs,
            "outputs": outputs,
            "hashes": {
                "config_hash": hash_config(cfg),
                "split_hash": split_hash,
                "recipe_hash": recipe_hash,
            },
        }
        write_manifest(ctx, manifest)
        return

    dataset_path = input_path_value
    chunked_input_path: Path | None = None
    if mode == "batch" and chunk_size is not None and input_payload is None and dataset_path:
        candidate = Path(dataset_path).expanduser().resolve()
        if candidate.suffix.lower() != ".json":
            chunked_input_path = _select_tabular_file(candidate)

    if mode == "batch" and chunk_size is not None and input_payload is None and chunked_input_path is not None:
        if output_format == "parquet" and write_mode == "append":
            raise ValueError("infer.batch.write_mode=append is not supported for parquet output.")

        predictions_path = (
            ctx.output_dir / "predictions.parquet"
            if output_format == "parquet"
            else ctx.output_dir / "predictions.csv"
        )
        if write_mode == "overwrite" and predictions_path.exists():
            predictions_path.unlink()

        pipeline = preprocess_bundle.get("pipeline")
        if pipeline is None:
            raise ValueError("preprocess_bundle.pipeline is missing.")

        feature_names = preprocess_bundle.get("feature_names")
        uncertainty_enabled = bool(uncertainty_info.get("enabled"))
        uncertainty_q = uncertainty_info.get("q") if uncertainty_enabled else None
        viz_enabled = _resolve_viz_enabled(cfg)

        validation_acc = _init_validation_accumulator()
        errors_log_path: Path | None = None
        errors_log_handle = None

        drift_sample = None
        drift_sample_n = drift_settings["sample_n"]
        if drift_settings["enabled"] and drift_sample_n is None:
            drift_sample_n = max_rows or chunk_size
        rng = None
        if drift_settings["enabled"] or (uncertainty_enabled and viz_enabled):
            try:
                import numpy as np  # type: ignore

                rng = np.random.default_rng(drift_settings["sample_seed"])
            except Exception:
                rng = None

        threshold_used = None
        class_labels = None
        label_encoder = None
        proba_prefix = "pred_proba_"
        top_k = None
        if task_type == "classification":
            threshold_used = _resolve_threshold_used(bundle, n_classes=n_classes)
            class_labels = _resolve_class_labels(bundle, model)
            label_encoder = bundle.get("label_encoder")
            is_multiclass = n_classes is not None and n_classes > 2
            proba_prefix = "proba_" if is_multiclass else "pred_proba_"
            top_k = _resolve_top_k(cfg, n_classes=n_classes)

        input_preview_path = None
        total_rows = 0
        total_chunks = 0
        header_written = False
        parquet_writer = None
        interval_widths_sample: list[float] = []
        quality_checked = False

        def _log_chunk_issues(
            *,
            chunk_index: int,
            row_offset: int,
            rows: int,
            issues_payload: Mapping[str, Any],
        ) -> None:
            nonlocal errors_log_handle, errors_log_path
            if errors_log_handle is None:
                errors_log_path = ctx.output_dir / "errors.jsonl"
                errors_log_handle = errors_log_path.open("w", encoding="utf-8")
            payload = {
                "chunk_index": chunk_index,
                "row_start": row_offset,
                "row_end": row_offset + rows - 1,
                "rows": rows,
                "issues_count": _count_schema_issues(issues_payload),
                "issues": issues_payload,
            }
            errors_log_handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

        def _finalize_preview() -> Path:
            nonlocal input_preview_path
            if input_preview_path is not None:
                return input_preview_path
            try:
                import pandas as pd  # type: ignore

                empty_df = pd.DataFrame()
            except Exception as exc:
                raise RuntimeError("pandas is required for infer.") from exc
            input_preview_path = _write_input_preview(empty_df, mode, ctx.output_dir)
            return input_preview_path

        if validation_mode == "strict":
            for chunk_index, (chunk, row_offset) in enumerate(
                _iter_tabular_chunks(chunked_input_path, chunk_size=chunk_size, max_rows=max_rows),
                start=1,
            ):
                total_rows += len(chunk)
                total_chunks += 1
                if not quality_checked:
                    quality_result = run_data_quality_gate(
                        cfg=cfg,
                        ctx=ctx,
                        df=chunk,
                        target_column=quality_target,
                        task_type=task_type,
                        id_columns=quality_id_columns,
                        output_dir=ctx.output_dir,
                    )
                    raise_on_quality_fail(
                        cfg=cfg,
                        ctx=ctx,
                        gate=quality_result["gate"],
                        payload=quality_result["payload"],
                        json_path=quality_result["paths"]["json"],
                    )
                    quality_checked = True
                _, chunk_validation = _validate_inputs(
                    chunk,
                    preprocess_bundle,
                    validation_mode=validation_mode,
                )
                issues = chunk_validation.get("issues") or {}
                if _count_schema_issues(issues) > 0:
                    _log_chunk_issues(
                        chunk_index=chunk_index,
                        row_offset=row_offset,
                        rows=len(chunk),
                        issues_payload=issues,
                    )
                _update_validation_accumulator(
                    validation_acc,
                    issues,
                    validation_mode=validation_mode,
                )

            if errors_log_handle is not None:
                errors_log_handle.close()
            validation = _finalize_validation_accumulator(validation_acc)
            summary_path = _write_infer_summary(
                ctx.output_dir,
                mode=mode,
                validation_mode=validation_mode,
                validation=validation,
                errors_path=errors_log_path,
                uncertainty=uncertainty_info,
            )
            if clearml_enabled:
                upload_artifact(ctx, summary_path.name, summary_path)
                if errors_log_path is not None:
                    upload_artifact(ctx, errors_log_path.name, errors_log_path)
            if not validation.get("ok"):
                raise ValueError("Input schema validation failed; see errors.jsonl for details.")
        else:
            for chunk_index, (chunk, row_offset) in enumerate(
                _iter_tabular_chunks(chunked_input_path, chunk_size=chunk_size, max_rows=max_rows),
                start=1,
            ):
                total_rows += len(chunk)
                total_chunks += 1
                if not quality_checked:
                    quality_result = run_data_quality_gate(
                        cfg=cfg,
                        ctx=ctx,
                        df=chunk,
                        target_column=quality_target,
                        task_type=task_type,
                        id_columns=quality_id_columns,
                        output_dir=ctx.output_dir,
                    )
                    raise_on_quality_fail(
                        cfg=cfg,
                        ctx=ctx,
                        gate=quality_result["gate"],
                        payload=quality_result["payload"],
                        json_path=quality_result["paths"]["json"],
                    )
                    quality_checked = True
                chunk_df, chunk_validation = _validate_inputs(
                    chunk,
                    preprocess_bundle,
                    validation_mode=validation_mode,
                )
                issues = chunk_validation.get("issues") or {}
                if _count_schema_issues(issues) > 0:
                    _log_chunk_issues(
                        chunk_index=chunk_index,
                        row_offset=row_offset,
                        rows=len(chunk),
                        issues_payload=issues,
                    )
                _update_validation_accumulator(
                    validation_acc,
                    issues,
                    validation_mode=validation_mode,
                )

                if input_preview_path is None:
                    input_preview_path = _write_input_preview(chunk_df, mode, ctx.output_dir)
                    if debug_input_sample is None:
                        debug_input_sample = chunk_df.head(5).copy()
                    if debug_input_sample is None:
                        debug_input_sample = chunk_df.head(5).copy()

                transformed = pipeline.transform(chunk_df)
                if hasattr(transformed, "toarray"):
                    transformed = transformed.toarray()
                transformed = _maybe_attach_feature_names(transformed, feature_names)

                if drift_settings["enabled"]:
                    drift_chunk = _ensure_drift_frame(transformed, feature_names)
                    drift_sample = _update_drift_sample(
                        drift_sample,
                        drift_chunk,
                        sample_n=drift_sample_n,
                        rng=rng,
                    )

                if task_type == "classification":
                    pred_df, class_labels = _build_classification_predictions_frame(
                        transformed,
                        predictor=predictor,
                        model=model,
                        threshold_used=threshold_used,
                        class_labels=class_labels,
                        label_encoder=label_encoder,
                        top_k=top_k,
                        proba_prefix=proba_prefix,
                    )
                else:
                    pred_df, interval_widths = _build_regression_predictions_frame(
                        transformed,
                        model=model,
                        uncertainty_enabled=uncertainty_enabled,
                        uncertainty_q=uncertainty_q,
                    )
                    if interval_widths:
                        interval_widths_sample = _update_interval_width_sample(
                            interval_widths_sample,
                            interval_widths,
                            rng=rng,
                        )
                if debug_output_sample is None:
                    debug_output_sample = pred_df.head(5).copy()
                if debug_output_sample is None:
                    debug_output_sample = pred_df.head(5).copy()

                if output_format == "parquet":
                    parquet_writer = _write_predictions_parquet_chunk(
                        predictions_path,
                        pred_df,
                        parquet_writer,
                    )
                else:
                    header_written = _write_predictions_csv_chunk(
                        predictions_path,
                        pred_df,
                        write_mode=write_mode,
                        header_written=header_written,
                    )

            if errors_log_handle is not None:
                errors_log_handle.close()
            validation = _finalize_validation_accumulator(validation_acc)
            summary_path = _write_infer_summary(
                ctx.output_dir,
                mode=mode,
                validation_mode=validation_mode,
                validation=validation,
                errors_path=errors_log_path,
                uncertainty=uncertainty_info,
            )
            if clearml_enabled:
                upload_artifact(ctx, summary_path.name, summary_path)
                if errors_log_path is not None:
                    upload_artifact(ctx, errors_log_path.name, errors_log_path)

        if validation_mode == "strict":
            total_rows = 0
            total_chunks = 0
            for chunk_index, (chunk, row_offset) in enumerate(
                _iter_tabular_chunks(chunked_input_path, chunk_size=chunk_size, max_rows=max_rows),
                start=1,
            ):
                total_rows += len(chunk)
                total_chunks += 1
                chunk_df, _ = _validate_inputs(
                    chunk,
                    preprocess_bundle,
                    validation_mode=validation_mode,
                )
                if input_preview_path is None:
                    input_preview_path = _write_input_preview(chunk_df, mode, ctx.output_dir)
                    if debug_input_sample is None:
                        debug_input_sample = chunk_df.head(5).copy()

                transformed = pipeline.transform(chunk_df)
                if hasattr(transformed, "toarray"):
                    transformed = transformed.toarray()
                transformed = _maybe_attach_feature_names(transformed, feature_names)

                if drift_settings["enabled"]:
                    drift_chunk = _ensure_drift_frame(transformed, feature_names)
                    drift_sample = _update_drift_sample(
                        drift_sample,
                        drift_chunk,
                        sample_n=drift_sample_n,
                        rng=rng,
                    )

                if task_type == "classification":
                    pred_df, class_labels = _build_classification_predictions_frame(
                        transformed,
                        predictor=predictor,
                        model=model,
                        threshold_used=threshold_used,
                        class_labels=class_labels,
                        label_encoder=label_encoder,
                        top_k=top_k,
                        proba_prefix=proba_prefix,
                    )
                else:
                    pred_df, interval_widths = _build_regression_predictions_frame(
                        transformed,
                        model=model,
                        uncertainty_enabled=uncertainty_enabled,
                        uncertainty_q=uncertainty_q,
                    )
                    if interval_widths:
                        interval_widths_sample = _update_interval_width_sample(
                            interval_widths_sample,
                            interval_widths,
                            rng=rng,
                        )
                if debug_output_sample is None:
                    debug_output_sample = pred_df.head(5).copy()

                if output_format == "parquet":
                    parquet_writer = _write_predictions_parquet_chunk(
                        predictions_path,
                        pred_df,
                        parquet_writer,
                    )
                else:
                    header_written = _write_predictions_csv_chunk(
                        predictions_path,
                        pred_df,
                        write_mode=write_mode,
                        header_written=header_written,
                    )

        if parquet_writer is not None:
            parquet_writer.close()

        input_preview_path = _finalize_preview()

        drift_report_path: Path | None = None
        drift_report_md_path: Path | None = None
        drift_report: dict[str, Any] | None = None
        drift_alert: bool | None = None
        if drift_settings["enabled"]:
            train_task_id = _normalize_str(meta.get("train_task_id"))
            train_profile, train_profile_path = _load_train_profile(
                cfg,
                bundle,
                model_bundle_path,
                train_task_id=train_task_id,
                clearml_enabled=clearml_enabled,
            )
            if train_profile is None:
                raise ValueError(
                    "train_profile.json not found; run train_model with monitor.drift.enabled=true."
                )
            if drift_sample is None:
                try:
                    import pandas as pd  # type: ignore

                    if feature_names:
                        drift_sample = pd.DataFrame(columns=list(feature_names))
                    else:
                        drift_sample = pd.DataFrame()
                except Exception:
                    drift_sample = _ensure_drift_frame([], feature_names)
            drift_sample, sample_info = sample_frame(
                drift_sample,
                sample_n=drift_sample_n,
                seed=drift_settings["sample_seed"],
            )
            sample_info["rows"] = total_rows
            drift_report = build_drift_report(
                train_profile,
                drift_sample,
                psi_warn_threshold=drift_settings["psi_warn_threshold"],
                psi_fail_threshold=drift_settings["psi_fail_threshold"],
                strict=(validation_mode == "strict"),
                metrics=drift_settings["metrics"],
                train_profile_path=str(train_profile_path) if train_profile_path else None,
            )
            train_settings = train_profile.get("settings") or {}
            max_bins = train_settings.get("max_bins")
            max_categories = train_settings.get("max_categories")
            quantiles = train_settings.get("quantiles")
            try:
                max_bins = int(max_bins) if max_bins is not None else None
            except Exception:
                max_bins = None
            try:
                max_categories = int(max_categories) if max_categories is not None else None
            except Exception:
                max_categories = None
            feature_types = train_profile.get("feature_types") or {}
            infer_profile = build_train_profile(
                drift_sample,
                feature_columns=list(getattr(drift_sample, "columns", [])),
                numeric_features=feature_types.get("numeric"),
                categorical_features=feature_types.get("categorical"),
                max_bins=max_bins or 10,
                quantiles=quantiles,
                max_categories=max_categories or 10,
            )
            infer_profile = annotate_profile(
                infer_profile,
                role="infer",
                sample_info=sample_info,
                metrics=drift_settings["metrics"],
            )
            drift_report["infer_profile"] = infer_profile
            drift_report["sampling"] = dict(sample_info)
            drift_report["train_profile_summary"] = {
                "rows": train_profile.get("rows"),
                "sampling": train_profile.get("sampling"),
                "settings": train_profile.get("settings"),
            }

            drift_summary = drift_report.get("summary", {})
            warn_count, fail_count = _drift_counts(drift_summary)
            drift_alert = bool(warn_count > 0)
            _emit_drift_alert(
                cfg,
                ctx,
                drift_summary,
                drift_settings,
                warn_count=warn_count,
                fail_count=fail_count,
                sample_rows=sample_info.get("rows"),
            )
            drift_report_path = ctx.output_dir / "drift_report.json"
            drift_report_path.write_text(
                json.dumps(drift_report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            drift_report_md_path = ctx.output_dir / "drift_report.md"
            drift_report_md_path.write_text(render_drift_markdown(drift_report), encoding="utf-8")
            append_drift_summary(summary_path, drift_report, drift_alert=drift_alert)
            if clearml_enabled:
                upload_artifact(ctx, summary_path.name, summary_path)
                upload_artifact(ctx, drift_report_path.name, drift_report_path)
                upload_artifact(ctx, drift_report_md_path.name, drift_report_md_path)
            if validation_mode == "strict" and fail_count > 0:
                raise ValueError(
                    "Drift PSI exceeded fail threshold; see drift_report.json for details."
                )

        interval_plot_path: Path | None = None
        if uncertainty_enabled and interval_widths_sample and viz_enabled:
            interval_plot_path = plot_interval_width_histogram(
                interval_widths_sample,
                ctx.output_dir / "interval_widths.png",
                title="Prediction Interval Widths",
            )

        if clearml_enabled:
            upload_artifact(ctx, predictions_path.name, predictions_path)
            upload_artifact(ctx, input_preview_path.name, input_preview_path)
            if interval_plot_path is not None:
                log_plotly(ctx.task, "infer", "interval_widths", interval_plot_path, step=0)
            table_input, table_output = _resolve_table_samples(
                debug_input_sample,
                debug_output_sample,
                input_preview_path=input_preview_path,
                predictions_path=predictions_path,
            )
            report_input_output_table(
                ctx.task,
                "infer",
                "input_output_table",
                table_input,
                table_output,
                max_rows=table_settings["max_rows"],
                max_input_columns=table_settings["max_input_columns"],
                max_output_columns=table_settings["max_output_columns"],
                output_path=ctx.output_dir / "input_output_table.png",
                step=0,
            )
            _log_debug_samples(
                ctx,
                input_sample=debug_input_sample,
                output_sample=debug_output_sample,
                input_preview_path=input_preview_path,
                predictions_path=predictions_path,
            )

        out = {
            "predictions_path": str(predictions_path),
            "input_preview_path": str(input_preview_path),
            "mode": mode,
            "model_id": meta.get("model_id") or str(model_bundle_path),
            "train_task_id": meta.get("train_task_id"),
        }
        if task_type == "classification":
            if calibration_info is None and calibrated_model is not None:
                calibration_info = {"enabled": True}
            if calibration_info is not None:
                calibration_payload = dict(calibration_info)
                calibration_payload["calibrated_proba"] = calibrated_model is not None
                out["calibration"] = calibration_payload
        out["schema_validation"] = {
            "mode": validation_mode,
            "ok": bool(validation.get("ok")),
            "warnings_count": int(validation.get("warnings_count") or 0),
            "errors_count": int(validation.get("errors_count") or 0),
        }
        if errors_log_path is not None:
            out["errors_path"] = str(errors_log_path)
        if drift_report_path is not None:
            out["drift_report_path"] = str(drift_report_path)
        if drift_alert is not None:
            out["drift_alert"] = bool(drift_alert)
        out["chunked"] = {
            "chunk_size": chunk_size,
            "rows": total_rows,
            "chunks": total_chunks,
            "errors_count": int(validation_acc.get("total_issues") or 0),
            "output_format": output_format,
            "write_mode": write_mode,
            "max_rows": max_rows,
        }
        write_out_json(ctx, out)
        if clearml_enabled and drift_alert is not None:
            update_task_properties(ctx, {"drift_alert": bool(drift_alert)})

        versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
        inputs = {
            "model_id": meta.get("model_id") or str(model_bundle_path),
            "train_task_id": meta.get("train_task_id"),
            "mode": mode,
            "input_path": str(chunked_input_path),
            "processed_dataset_id": processed_dataset_id,
            "split_hash": split_hash,
            "recipe_hash": recipe_hash,
        }
        outputs = {
            "predictions_path": str(predictions_path),
            "input_preview_path": str(input_preview_path),
        }
        if errors_log_path is not None:
            outputs["errors_path"] = str(errors_log_path)
        if drift_report_path is not None:
            outputs["drift_report_path"] = str(drift_report_path)
        if drift_alert is not None:
            outputs["drift_alert"] = bool(drift_alert)
        manifest = {
            "schema_version": versions.get("schema_version", "unknown"),
            "code_version": versions.get("code_version", "unknown"),
            "platform_version": versions.get("platform_version", "unknown"),
            "process": "infer",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "inputs": inputs,
            "outputs": outputs,
            "hashes": {
                "config_hash": hash_config(cfg),
                "split_hash": split_hash,
                "recipe_hash": recipe_hash,
            },
        }
        write_manifest(ctx, manifest)
        return

    inputs_df, input_path = _prepare_inputs(cfg, preprocess_bundle, mode)
    quality_result = run_data_quality_gate(
        cfg=cfg,
        ctx=ctx,
        df=inputs_df,
        target_column=quality_target,
        task_type=task_type,
        id_columns=quality_id_columns,
        output_dir=ctx.output_dir,
    )
    raise_on_quality_fail(
        cfg=cfg,
        ctx=ctx,
        gate=quality_result["gate"],
        payload=quality_result["payload"],
        json_path=quality_result["paths"]["json"],
    )
    inputs_df, validation = _validate_inputs(
        inputs_df,
        preprocess_bundle,
        validation_mode=validation_mode,
    )
    issues = validation.get("issues") or {}
    errors_json_path: Path | None = None
    errors_csv_path: Path | None = None
    if _count_schema_issues(issues) > 0:
        errors_json_path, errors_csv_path = _write_schema_errors(ctx.output_dir, issues)
        if clearml_enabled:
            upload_artifact(ctx, errors_json_path.name, errors_json_path)
            upload_artifact(ctx, errors_csv_path.name, errors_csv_path)

    summary_path = _write_infer_summary(
        ctx.output_dir,
        mode=mode,
        validation_mode=validation_mode,
        validation=validation,
        errors_path=errors_json_path,
        uncertainty=uncertainty_info,
    )
    if clearml_enabled:
        upload_artifact(ctx, summary_path.name, summary_path)

    if validation_mode == "strict" and not validation.get("ok"):
        raise ValueError("Input schema validation failed; see errors.json for details.")

    input_preview_path = _write_input_preview(inputs_df, mode, ctx.output_dir)
    if debug_input_sample is None:
        try:
            debug_input_sample = inputs_df.head(5).copy()
        except Exception:
            debug_input_sample = None
    pipeline = preprocess_bundle.get("pipeline")
    if pipeline is None:
        raise ValueError("preprocess_bundle.pipeline is missing.")
    transformed = pipeline.transform(inputs_df)
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()
    feature_names = preprocess_bundle.get("feature_names")
    if feature_names:
        try:
            import pandas as pd  # type: ignore

            if hasattr(transformed, "shape") and len(feature_names) == int(transformed.shape[1]):
                transformed = pd.DataFrame(transformed, columns=list(feature_names))
        except Exception:
            pass

    drift_report_path: Path | None = None
    drift_report_md_path: Path | None = None
    drift_report: dict[str, Any] | None = None
    drift_alert: bool | None = None
    if drift_settings["enabled"]:
        train_task_id = _normalize_str(meta.get("train_task_id"))
        train_profile, train_profile_path = _load_train_profile(
            cfg,
            bundle,
            model_bundle_path,
            train_task_id=train_task_id,
            clearml_enabled=clearml_enabled,
        )
        if train_profile is None:
            raise ValueError(
                "train_profile.json not found; run train_model with monitor.drift.enabled=true."
            )
        drift_df = _ensure_drift_frame(transformed, feature_names)
        drift_sample, sample_info = sample_frame(
            drift_df,
            sample_n=drift_settings["sample_n"],
            seed=drift_settings["sample_seed"],
        )
        drift_report = build_drift_report(
            train_profile,
            drift_sample,
            psi_warn_threshold=drift_settings["psi_warn_threshold"],
            psi_fail_threshold=drift_settings["psi_fail_threshold"],
            strict=(validation_mode == "strict"),
            metrics=drift_settings["metrics"],
            train_profile_path=str(train_profile_path) if train_profile_path else None,
        )
        train_settings = train_profile.get("settings") or {}
        max_bins = train_settings.get("max_bins")
        max_categories = train_settings.get("max_categories")
        quantiles = train_settings.get("quantiles")
        try:
            max_bins = int(max_bins) if max_bins is not None else None
        except Exception:
            max_bins = None
        try:
            max_categories = int(max_categories) if max_categories is not None else None
        except Exception:
            max_categories = None
        feature_types = train_profile.get("feature_types") or {}
        infer_profile = build_train_profile(
            drift_sample,
            feature_columns=list(getattr(drift_df, "columns", [])),
            numeric_features=feature_types.get("numeric"),
            categorical_features=feature_types.get("categorical"),
            max_bins=max_bins or 10,
            quantiles=quantiles,
            max_categories=max_categories or 10,
        )
        infer_profile = annotate_profile(
            infer_profile,
            role="infer",
            sample_info=sample_info,
            metrics=drift_settings["metrics"],
        )
        drift_report["infer_profile"] = infer_profile
        drift_report["sampling"] = dict(sample_info)
        drift_report["train_profile_summary"] = {
            "rows": train_profile.get("rows"),
            "sampling": train_profile.get("sampling"),
            "settings": train_profile.get("settings"),
        }

        drift_summary = drift_report.get("summary", {})
        warn_count, fail_count = _drift_counts(drift_summary)
        drift_alert = bool(warn_count > 0)
        _emit_drift_alert(
            cfg,
            ctx,
            drift_summary,
            drift_settings,
            warn_count=warn_count,
            fail_count=fail_count,
            sample_rows=sample_info.get("rows"),
        )
        drift_report_path = ctx.output_dir / "drift_report.json"
        drift_report_path.write_text(
            json.dumps(drift_report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        drift_report_md_path = ctx.output_dir / "drift_report.md"
        drift_report_md_path.write_text(render_drift_markdown(drift_report), encoding="utf-8")
        append_drift_summary(summary_path, drift_report, drift_alert=drift_alert)
        if clearml_enabled:
            upload_artifact(ctx, summary_path.name, summary_path)
            upload_artifact(ctx, drift_report_path.name, drift_report_path)
            upload_artifact(ctx, drift_report_md_path.name, drift_report_md_path)
        if validation_mode == "strict" and fail_count > 0:
            raise ValueError("Drift PSI exceeded fail threshold; see drift_report.json for details.")

    uncertainty_enabled = bool(uncertainty_info.get("enabled"))
    uncertainty_q = uncertainty_info.get("q") if uncertainty_enabled else None
    viz_enabled = _resolve_viz_enabled(cfg)

    predictions_path: Path
    interval_plot_path: Path | None = None
    if task_type == "classification":
        if not hasattr(predictor, "predict_proba"):
            raise ValueError("classification infer requires predict_proba on the model.")
        proba = predictor.predict_proba(transformed)
        threshold_used = _resolve_threshold_used(bundle, n_classes=n_classes)
        if threshold_used is not None:
            positive_proba = _extract_positive_proba(proba)
            preds = (positive_proba >= threshold_used).astype(int)
        else:
            preds = predictor.predict(transformed)
        class_labels = _resolve_class_labels(bundle, model)
        label_encoder = bundle.get("label_encoder")
        if label_encoder is not None and hasattr(label_encoder, "inverse_transform"):
            pred_labels = label_encoder.inverse_transform(preds)
        else:
            pred_labels = preds
            if class_labels:
                try:
                    pred_labels = [class_labels[int(idx)] for idx in preds]
                except Exception:
                    pred_labels = preds
        if hasattr(pred_labels, "tolist"):
            pred_labels = pred_labels.tolist()
        if not isinstance(pred_labels, list):
            pred_labels = list(pred_labels)
        try:
            import numpy as np  # type: ignore
        except Exception as exc:
            raise RuntimeError("numpy is required for classification probabilities.") from exc
        proba_arr = np.asarray(proba)
        if proba_arr.ndim == 1:
            proba_arr = np.stack([1.0 - proba_arr, proba_arr], axis=1)
        if class_labels is None or len(class_labels) != int(proba_arr.shape[1]):
            class_labels = [str(i) for i in range(int(proba_arr.shape[1]))]

        is_multiclass = n_classes is not None and n_classes > 2
        proba_prefix = "proba_" if is_multiclass else "pred_proba_"

        top_k = _resolve_top_k(cfg, n_classes=n_classes)
        top_indices = None
        if top_k is not None:
            order = np.argsort(proba_arr, axis=1)[:, ::-1]
            top_indices = order[:, :top_k]

        if mode == "single":
            predictions_path = ctx.output_dir / "prediction.json"
            payload: dict[str, Any] = {"predicted_label": None, "pred_label": None}
            if pred_labels:
                label_value = _sanitize_json_value(pred_labels[0])
                payload["predicted_label"] = label_value
                payload["pred_label"] = label_value
                payload["prediction"] = label_value
            if threshold_used is not None:
                payload["threshold_used"] = _sanitize_json_value(threshold_used)
            if hasattr(proba_arr, "__len__") and len(proba_arr) > 0:
                payload["predicted_proba"] = _build_proba_payload(proba_arr[0], class_labels)
                if class_labels and is_multiclass:
                    safe_labels = _build_proba_column_labels(class_labels)
                    for safe, value in zip(safe_labels, proba_arr[0]):
                        payload[f"proba_{safe}"] = _sanitize_json_value(value)
            if top_indices is not None:
                top_payload = []
                for idx in top_indices[0]:
                    label = class_labels[idx] if class_labels else str(idx)
                    top_payload.append(
                        {
                            "label": _sanitize_json_value(label),
                            "proba": _sanitize_json_value(proba_arr[0][idx]),
                        }
                    )
                payload["top_k"] = top_payload
            predictions_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            if debug_output_sample is None:
                debug_output_sample = payload
        else:
            if proba is None:
                raise ValueError("classification infer requires predicted probabilities.")
            if not class_labels:
                class_labels = [str(i) for i in range(int(proba_arr.shape[1]))]
            if output_format == "parquet":
                predictions_path = ctx.output_dir / "predictions.parquet"
                data: dict[str, list[Any]] = {
                    "pred_label": [_sanitize_json_value(label) for label in pred_labels],
                }
                if threshold_used is not None:
                    data["threshold_used"] = [_sanitize_json_value(threshold_used)] * len(pred_labels)
                proba_columns = _format_proba_columns(class_labels, prefix=proba_prefix)
                for idx, col_name in enumerate(proba_columns):
                    data[col_name] = [_sanitize_json_value(v) for v in proba_arr[:, idx]]
                if top_indices is not None:
                    for rank in range(1, top_k + 1):
                        labels: list[Any] = []
                        probs: list[Any] = []
                        for row_idx, col_idx in enumerate(top_indices[:, rank - 1]):
                            label = class_labels[col_idx] if class_labels else str(col_idx)
                            labels.append(_sanitize_json_value(label))
                            probs.append(_sanitize_json_value(proba_arr[row_idx][col_idx]))
                        data[f"top{rank}_label"] = labels
                        data[f"top{rank}_proba"] = probs
                try:
                    import pandas as pd  # type: ignore
                except Exception as exc:
                    raise RuntimeError("pandas is required for infer.") from exc
                pd.DataFrame(data).to_parquet(predictions_path, index=False)
            else:
                predictions_path = ctx.output_dir / "predictions.csv"
                columns = ["pred_label"]
                if threshold_used is not None:
                    columns.append("threshold_used")
                columns.extend(_format_proba_columns(class_labels, prefix=proba_prefix))
                if top_k is not None:
                    for rank in range(1, top_k + 1):
                        columns.append(f"top{rank}_label")
                        columns.append(f"top{rank}_proba")
                with predictions_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(columns)
                    for idx, label in enumerate(pred_labels):
                        row = [_sanitize_json_value(label)]
                        if threshold_used is not None:
                            row.append(_sanitize_json_value(threshold_used))
                        row.extend([_sanitize_json_value(v) for v in proba_arr[idx]])
                        if top_indices is not None:
                            for rank_idx in top_indices[idx]:
                                top_label = class_labels[rank_idx] if class_labels else str(rank_idx)
                                row.append(_sanitize_json_value(top_label))
                                row.append(_sanitize_json_value(proba_arr[idx][rank_idx]))
                        writer.writerow(row)
            if debug_output_sample is None and pred_labels:
                sample_rows: list[dict[str, Any]] = []
                max_rows = min(5, len(pred_labels))
                proba_columns = _format_proba_columns(class_labels, prefix=proba_prefix)
                for idx in range(max_rows):
                    row: dict[str, Any] = {"pred_label": _sanitize_json_value(pred_labels[idx])}
                    if threshold_used is not None:
                        row["threshold_used"] = _sanitize_json_value(threshold_used)
                    for col_idx, col_name in enumerate(proba_columns):
                        if col_idx >= proba_arr.shape[1]:
                            break
                        row[col_name] = _sanitize_json_value(proba_arr[idx][col_idx])
                    if top_indices is not None:
                        for rank, class_idx in enumerate(top_indices[idx], start=1):
                            label = class_labels[class_idx] if class_labels else str(class_idx)
                            row[f"top{rank}_label"] = _sanitize_json_value(label)
                            row[f"top{rank}_proba"] = _sanitize_json_value(proba_arr[idx][class_idx])
                    sample_rows.append(row)
                debug_output_sample = sample_rows
    else:
        preds = model.predict(transformed)
        rows = _preds_to_rows(preds)
        lower = None
        upper = None
        if uncertainty_enabled and uncertainty_q is not None:
            try:
                lower, upper = apply_split_conformal_interval(preds, float(uncertainty_q))
            except ValueError as exc:
                raise ValueError(
                    "uncertainty intervals require 1D regression predictions."
                ) from exc
        if mode == "single":
            predictions_path = ctx.output_dir / "prediction.json"
            if rows:
                row = rows[0]
                if len(row) == 1:
                    payload = {"prediction": _sanitize_json_value(row[0])}
                    if lower is not None and upper is not None:
                        payload["pred_lower"] = _sanitize_json_value(lower[0])
                        payload["pred_upper"] = _sanitize_json_value(upper[0])
                else:
                    payload = {"prediction": [_sanitize_json_value(v) for v in row]}
            else:
                payload = {"prediction": None}
            predictions_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            if debug_output_sample is None:
                debug_output_sample = payload
        else:
            n_cols = len(rows[0]) if rows else 1
            if output_format == "parquet":
                predictions_path = ctx.output_dir / "predictions.parquet"
                data: dict[str, list[Any]] = {}
                if n_cols == 1:
                    data["prediction"] = [_sanitize_json_value(row[0]) for row in rows] if rows else [None]
                    if lower is not None and upper is not None:
                        data["pred_lower"] = [_sanitize_json_value(v) for v in lower]
                        data["pred_upper"] = [_sanitize_json_value(v) for v in upper]
                else:
                    for idx in range(n_cols):
                        data[f"prediction_{idx}"] = [
                            _sanitize_json_value(row[idx]) if idx < len(row) else None for row in rows
                        ]
                try:
                    import pandas as pd  # type: ignore
                except Exception as exc:
                    raise RuntimeError("pandas is required for infer.") from exc
                pd.DataFrame(data).to_parquet(predictions_path, index=False)
            else:
                predictions_path = ctx.output_dir / "predictions.csv"
                with predictions_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    if n_cols == 1:
                        header = ["prediction"]
                        if lower is not None and upper is not None:
                            header.extend(["pred_lower", "pred_upper"])
                    else:
                        header = [f"prediction_{idx}" for idx in range(n_cols)]
                    writer.writerow(header)
                    for idx, row in enumerate(rows):
                        values = list(row)
                        if len(values) < n_cols:
                            values.extend([None] * (n_cols - len(values)))
                        row_values = [_sanitize_json_value(v) for v in values]
                        if lower is not None and upper is not None and n_cols == 1:
                            row_values.append(_sanitize_json_value(lower[idx]))
                            row_values.append(_sanitize_json_value(upper[idx]))
                        writer.writerow(row_values)
            if debug_output_sample is None:
                sample_rows: list[dict[str, Any]] = []
                max_rows = min(5, len(rows))
                for idx in range(max_rows):
                    row_values = list(rows[idx]) if rows else []
                    if n_cols == 1:
                        payload = {"prediction": _sanitize_json_value(row_values[0]) if row_values else None}
                        if lower is not None and upper is not None and idx < len(lower):
                            payload["pred_lower"] = _sanitize_json_value(lower[idx])
                            payload["pred_upper"] = _sanitize_json_value(upper[idx])
                        sample_rows.append(payload)
                    else:
                        payload = {}
                        for col_idx in range(n_cols):
                            key = f"prediction_{col_idx}"
                            value = row_values[col_idx] if col_idx < len(row_values) else None
                            payload[key] = _sanitize_json_value(value)
                        sample_rows.append(payload)
                if sample_rows:
                    debug_output_sample = sample_rows

        if lower is not None and upper is not None and viz_enabled:
            try:
                widths = (upper - lower).tolist()
            except Exception:
                widths = [float(upper[idx] - lower[idx]) for idx in range(len(lower))]
            interval_plot_path = plot_interval_width_histogram(
                widths,
                ctx.output_dir / "interval_widths.png",
                title="Prediction Interval Widths",
            )

    if clearml_enabled:
        upload_artifact(ctx, predictions_path.name, predictions_path)
        upload_artifact(ctx, input_preview_path.name, input_preview_path)
        if interval_plot_path is not None:
            log_plotly(ctx.task, "infer", "interval_widths", interval_plot_path, step=0)
        table_input, table_output = _resolve_table_samples(
            debug_input_sample,
            debug_output_sample,
            input_preview_path=input_preview_path,
            predictions_path=predictions_path,
        )
        report_input_output_table(
            ctx.task,
            "infer",
            "input_output_table",
            table_input,
            table_output,
            max_rows=table_settings["max_rows"],
            max_input_columns=table_settings["max_input_columns"],
            max_output_columns=table_settings["max_output_columns"],
            output_path=ctx.output_dir / "input_output_table.png",
            step=0,
        )
        _log_debug_samples(
            ctx,
            input_sample=debug_input_sample,
            output_sample=debug_output_sample,
            input_preview_path=input_preview_path,
            predictions_path=predictions_path,
        )

    out = {
        "predictions_path": str(predictions_path),
        "input_preview_path": str(input_preview_path),
        "mode": mode,
        "model_id": meta.get("model_id") or str(model_bundle_path),
        "train_task_id": meta.get("train_task_id"),
    }
    if task_type == "classification":
        if calibration_info is None and calibrated_model is not None:
            calibration_info = {"enabled": True}
        if calibration_info is not None:
            calibration_payload = dict(calibration_info)
            calibration_payload["calibrated_proba"] = calibrated_model is not None
            out["calibration"] = calibration_payload
    out["schema_validation"] = {
        "mode": validation_mode,
        "ok": bool(validation.get("ok")),
        "warnings_count": int(validation.get("warnings_count") or 0),
        "errors_count": int(validation.get("errors_count") or 0),
    }
    if errors_json_path is not None:
        out["errors_path"] = str(errors_json_path)
    if drift_report_path is not None:
        out["drift_report_path"] = str(drift_report_path)
    if drift_alert is not None:
        out["drift_alert"] = bool(drift_alert)
    write_out_json(ctx, out)
    if clearml_enabled and drift_alert is not None:
        update_task_properties(ctx, {"drift_alert": bool(drift_alert)})

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    inputs = {
        "model_id": meta.get("model_id") or str(model_bundle_path),
        "train_task_id": meta.get("train_task_id"),
        "mode": mode,
        "input_path": input_path,
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
    }
    outputs = {
        "predictions_path": str(predictions_path),
        "input_preview_path": str(input_preview_path),
    }
    if errors_json_path is not None:
        outputs["errors_path"] = str(errors_json_path)
    if drift_report_path is not None:
        outputs["drift_report_path"] = str(drift_report_path)
    if drift_alert is not None:
        outputs["drift_alert"] = bool(drift_alert)
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "infer",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
        "outputs": outputs,
        "hashes": {
            "config_hash": hash_config(cfg),
            "split_hash": split_hash,
            "recipe_hash": recipe_hash,
        },
    }
    write_manifest(ctx, manifest)
