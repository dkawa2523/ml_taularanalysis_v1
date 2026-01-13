"""train_ensemble process (mean_topk/weighted)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..clearml.naming import apply_train_ensemble_naming
from ..clearml.reporting import report_scalar, report_table, scalars_enabled, tables_enabled
from ..io.bundle_io import load_bundle, save_bundle
from ..metrics.regression import REGRESSION_METRIC_ORDER, compute_regression_metrics
from ..ops.clearml_identity import apply_clearml_identity
from ..platform_adapter import (
    clearml_task_id,
    clearml_task_status_from_obj,
    emit_skip,
    get_task_artifact_local_copy,
    hash_config,
    init_task_context,
    is_clearml_enabled,
    list_clearml_tasks_by_tags,
    resolve_version_props,
    save_config_resolved,
    update_task_properties,
    upload_artifact,
    write_manifest,
    write_out_json,
)
from ..registry import list_ensemble_methods
from ..registry.metrics import get_metric, metric_direction, metric_requires_proba


@dataclass
class _Candidate:
    train_task_id: str | None
    run_dir: Path | None
    model_variant: str
    preprocess_variant: str
    task_type: str
    metric_value: float
    preds_path: Path | None
    classes: list[str] | None
    model_bundle_path: Path | None
    model_id: str | None
    processed_dataset_id: str | None
    split_hash: str | None
    recipe_hash: str | None


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_key(value: Any) -> str | None:
    text = _normalize_str(value)
    if text is None:
        return None
    return text.lower().replace("-", "_")


def _normalize_task_type(value: Any) -> str:
    key = _normalize_str(value)
    if key in ("classification", "classifier", "class"):
        return "classification"
    return "regression"


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


def _to_container(value: Any) -> Any:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(value):
        return OmegaConf.to_container(value, resolve=True)
    return value


def _ensure_str_list(values: Any) -> list[str]:
    container = _to_container(values)
    if container is None:
        return []
    if isinstance(container, (list, tuple, set)):
        return [str(v) for v in container if v is not None]
    return [str(container)]


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except Exception:
        return None
    if not math.isfinite(num):
        return None
    return num


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_usecase_id(config_path: Path) -> str | None:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        return None
    try:
        cfg = OmegaConf.load(config_path)
        value = OmegaConf.select(cfg, "run.usecase_id")
    except Exception:
        value = None
    return _normalize_str(value)


def _resolve_preprocess_variant(cfg: Any) -> str | None:
    return _normalize_str(_cfg_value(cfg, "preprocess.variant")) or _normalize_str(
        _cfg_value(cfg, "preprocess_variant.name")
    )


def _resolve_primary_metric(cfg: Any) -> str:
    primary_metric = _normalize_str(_cfg_value(cfg, "eval.primary_metric")) or "rmse"
    return primary_metric.lower()


def _resolve_selection_metric(cfg: Any) -> str:
    selection_metric = _normalize_str(_cfg_value(cfg, "ensemble.selection_metric")) or _resolve_primary_metric(cfg)
    return selection_metric.lower()


def _find_ensemble_spec(method: str, *, task_type: str | None) -> Any | None:
    try:
        specs = list_ensemble_methods(task_type=task_type, defaults_only=False)
    except Exception:
        return None
    for spec in specs:
        if spec.id == method:
            return spec
    return None


def _required_candidate_count(method: str, top_k: int) -> int:
    required = top_k if top_k > 0 else 1
    if method == "stacking" and required < 2:
        required = 2
    return required


def _resolve_direction(cfg: Any, metric_name: str, task_type: str) -> str:
    direction = _normalize_str(_cfg_value(cfg, "eval.direction"))
    if not direction or direction == "auto":
        direction = metric_direction(metric_name, task_type)
    return direction.lower()


def _resolve_classification_metrics(cfg: Any, *, n_classes: int | None) -> list[str]:
    metrics = _ensure_str_list(_cfg_value(cfg, "eval.metrics.classification_binary"))
    if n_classes is not None and n_classes > 2:
        metrics = _ensure_str_list(_cfg_value(cfg, "eval.metrics.classification_multiclass", metrics))
        if not metrics:
            metrics = ["accuracy", "f1_macro", "logloss"]
    elif not metrics:
        metrics = ["accuracy", "f1", "log_loss", "roc_auc"]
    seen: set[str] = set()
    ordered: list[str] = []
    for name in metrics:
        key = _normalize_str(name)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def _resolve_regression_metrics(cfg: Any) -> list[str]:
    metrics = list(REGRESSION_METRIC_ORDER)
    extras = _ensure_str_list(_cfg_value(cfg, "eval.metrics.regression"))
    if extras:
        metrics.extend(extras)
    seen: set[str] = set()
    ordered: list[str] = []
    for name in metrics:
        key = _normalize_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def _metric_value_from_payload(metrics_payload: dict[str, Any], metric_name: str) -> float | None:
    if not isinstance(metrics_payload, dict):
        return None
    holdout = metrics_payload.get("holdout")
    if not isinstance(holdout, dict):
        return None
    candidates = [metric_name, _normalize_key(metric_name)]
    for key in candidates:
        if not key:
            continue
        if key in holdout:
            return _to_float(holdout.get(key))
    return None


def _load_preds_frame(path: Path):
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for ensemble predictions.") from exc
    return pd.read_parquet(path)


def _read_classes(path: Path) -> list[str] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(payload, (list, tuple)):
        return [str(item) for item in payload]
    return None


def _extract_preds_payload(
    preds_path: Path,
    *,
    task_type: str,
    classes: list[str] | None,
) -> tuple[Any, Any, Any | None]:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for ensemble predictions.") from exc
    df = _load_preds_frame(preds_path)
    if "y_true" not in df.columns:
        raise ValueError("preds_valid.parquet is missing y_true.")
    y_true = df["y_true"].to_numpy()
    y_pred = None
    y_proba = None
    if task_type == "classification":
        if not classes:
            raise ValueError("classes.json is missing for classification ensemble.")
        proba_columns = [f"proba__{label}" for label in classes]
        missing = [col for col in proba_columns if col not in df.columns]
        if missing:
            raise ValueError(f"preds_valid.parquet missing proba columns: {missing}")
        y_proba = df[proba_columns].to_numpy()
        if y_proba.ndim == 1:
            y_proba = np.stack([1.0 - y_proba, y_proba], axis=1)
        if y_proba.shape[1] != len(classes):
            raise ValueError("preds_valid probability columns do not match classes.")
        if "y_pred" in df.columns:
            y_pred = df["y_pred"].to_numpy()
        else:
            y_pred = np.asarray(y_proba).argmax(axis=1)
    else:
        if "y_pred" not in df.columns:
            raise ValueError("preds_valid.parquet is missing y_pred.")
        y_pred = df["y_pred"].to_numpy()
    return y_true, y_pred, y_proba


def _summarize_skips(skipped: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in skipped:
        reason = _normalize_str(item.get("reason")) or "unknown"
        counts[reason] = counts.get(reason, 0) + 1
    summary = [{"reason": reason, "count": count} for reason, count in counts.items()]
    summary.sort(key=lambda row: (-row["count"], row["reason"]))
    return summary


def _resolve_search_root(run_root: Path) -> Path:
    for parent in run_root.parents:
        if parent.parent.name == "grid":
            return parent
    return run_root


def _find_preprocess_run_dir(search_root: Path, processed_dataset_id: str | None) -> Path | None:
    if not processed_dataset_id or not search_root.exists():
        return None
    for out_path in search_root.glob("*/02_preprocess/out.json"):
        try:
            payload = _load_json(out_path)
        except Exception:
            continue
        if _normalize_str(payload.get("processed_dataset_id")) == processed_dataset_id:
            return out_path.parent
    return None


def _collect_candidates_local(
    cfg: Any,
    *,
    desired_usecase: str | None,
    desired_preprocess: str | None,
    selection_metric: str,
    exclude_variants: set[str],
    allow_missing_preds: bool,
    skipped: list[dict[str, Any]],
) -> list[_Candidate]:
    run_root = Path(_cfg_value(cfg, "run.output_dir", "outputs")).expanduser().resolve()
    search_root = _resolve_search_root(run_root)
    candidates: list[_Candidate] = []
    for out_path in search_root.glob("**/03_train_model/out.json"):
        run_dir = out_path.parent
        try:
            out_payload = _load_json(out_path)
        except Exception as exc:
            skipped.append(
                {
                    "train_task_id": None,
                    "model_variant": "unknown",
                    "reason": "out_json_invalid",
                    "details": str(exc),
                }
            )
            continue
        if _normalize_str(out_payload.get("status")) == "failed":
            skipped.append(
                {
                    "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                    "model_variant": _normalize_str(out_payload.get("model_variant")) or "unknown",
                    "reason": "train_failed",
                }
            )
            continue

        config_path = run_dir / "config_resolved.yaml"
        if desired_usecase:
            usecase_id = _load_usecase_id(config_path) if config_path.exists() else None
            if usecase_id != desired_usecase:
                skipped.append(
                    {
                        "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                        "model_variant": _normalize_str(out_payload.get("model_variant")) or "unknown",
                        "reason": "usecase_mismatch",
                        "details": usecase_id,
                    }
                )
                continue

        manifest_path = run_dir / "manifest.json"
        if manifest_path.exists():
            try:
                manifest_payload = _load_json(manifest_path)
            except Exception:
                manifest_payload = {}
            if _normalize_str(manifest_payload.get("process")) not in (None, "train_model"):
                skipped.append(
                    {
                        "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                        "model_variant": _normalize_str(out_payload.get("model_variant")) or "unknown",
                        "reason": "process_mismatch",
                    }
                )
                continue

        model_bundle_path = run_dir / "model_bundle.joblib"
        if not model_bundle_path.exists():
            skipped.append(
                {
                    "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                    "model_variant": _normalize_str(out_payload.get("model_variant")) or "unknown",
                    "reason": "missing_model_bundle",
                }
            )
            continue

        try:
            bundle = load_bundle(model_bundle_path)
        except Exception as exc:
            skipped.append(
                {
                    "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                    "model_variant": _normalize_str(out_payload.get("model_variant")) or "unknown",
                    "reason": "model_bundle_invalid",
                    "details": str(exc),
                }
            )
            continue
        if not isinstance(bundle, dict):
            skipped.append(
                {
                    "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                    "model_variant": "unknown",
                    "reason": "model_bundle_invalid",
                }
            )
            continue

        model_variant = _normalize_str(bundle.get("model_variant"))
        if not model_variant:
            model_variant = _normalize_str(out_payload.get("model_variant")) or "unknown"
        if model_variant.lower() in exclude_variants:
            skipped.append(
                {
                    "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                    "model_variant": model_variant,
                    "reason": "excluded_variant",
                }
            )
            continue

        preprocess_bundle = bundle.get("preprocess_bundle") or {}
        preprocess_variant = _normalize_str(preprocess_bundle.get("preprocess_variant")) or "unknown"
        if desired_preprocess and preprocess_variant != desired_preprocess:
            skipped.append(
                {
                    "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                    "model_variant": model_variant,
                    "reason": "preprocess_mismatch",
                    "details": preprocess_variant,
                }
            )
            continue

        task_type = _normalize_task_type(bundle.get("task_type") or out_payload.get("task_type"))

        metrics_path = run_dir / "metrics.json"
        if not metrics_path.exists():
            skipped.append(
                {
                    "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                    "model_variant": model_variant,
                    "reason": "missing_metrics",
                }
            )
            continue
        try:
            metrics_payload = _load_json(metrics_path)
        except Exception as exc:
            skipped.append(
                {
                    "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                    "model_variant": model_variant,
                    "reason": "metrics_invalid",
                    "details": str(exc),
                }
            )
            continue
        metric_value = _metric_value_from_payload(metrics_payload, selection_metric)
        if metric_value is None:
            skipped.append(
                {
                    "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                    "model_variant": model_variant,
                    "reason": "metric_missing",
                    "details": selection_metric,
                }
            )
            continue

        preds_path = None
        preds_path_value = _normalize_str(out_payload.get("preds_valid_path"))
        if preds_path_value:
            candidate = Path(preds_path_value).expanduser()
            if not candidate.is_absolute():
                candidate = run_dir / candidate
            if candidate.exists():
                preds_path = candidate
        if preds_path is None:
            candidate = run_dir / "artifacts" / "preds_valid.parquet"
            if candidate.exists():
                preds_path = candidate
        if preds_path is None:
            if not allow_missing_preds:
                skipped.append(
                    {
                        "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                        "model_variant": model_variant,
                        "reason": "missing_preds_valid",
                    }
                )
                continue

        classes = None
        if task_type == "classification":
            classes_path = run_dir / "artifacts" / "classes.json"
            if classes_path.exists():
                classes = _read_classes(classes_path)
            if not classes:
                skipped.append(
                    {
                        "train_task_id": _normalize_str(out_payload.get("train_task_id")),
                        "model_variant": model_variant,
                        "reason": "missing_classes",
                    }
                )
                continue
        else:
            classes_path = None

        candidates.append(
            _Candidate(
                train_task_id=_normalize_str(out_payload.get("train_task_id")),
                run_dir=run_dir,
                model_variant=model_variant,
                preprocess_variant=preprocess_variant,
                task_type=task_type,
                metric_value=float(metric_value),
                preds_path=preds_path,
                classes=classes,
                model_bundle_path=model_bundle_path,
                model_id=_normalize_str(out_payload.get("model_id")),
                processed_dataset_id=_normalize_str(out_payload.get("processed_dataset_id")),
                split_hash=_normalize_str(out_payload.get("split_hash")),
                recipe_hash=_normalize_str(out_payload.get("recipe_hash")),
            )
        )
    return candidates


def _collect_candidates_clearml(
    cfg: Any,
    *,
    desired_usecase: str | None,
    desired_preprocess: str | None,
    selection_metric: str,
    exclude_variants: set[str],
    allow_missing_preds: bool,
    skipped: list[dict[str, Any]],
) -> list[_Candidate]:
    tags = ["process:train_model"]
    if desired_usecase:
        tags.append(f"usecase:{desired_usecase}")
    if desired_preprocess:
        tags.append(f"preprocess:{desired_preprocess}")
    tasks = list_clearml_tasks_by_tags(tags)
    candidates: list[_Candidate] = []
    for task in tasks:
        task_id = clearml_task_id(task)
        status = _normalize_str(clearml_task_status_from_obj(task)) or ""
        if status.lower() != "completed":
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": "unknown",
                    "reason": "status_incomplete",
                    "details": status,
                }
            )
            continue
        try:
            out_path = get_task_artifact_local_copy(cfg, task_id, "out.json")
            out_payload = _load_json(out_path)
        except Exception as exc:
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": "unknown",
                    "reason": "missing_out_json",
                    "details": str(exc),
                }
            )
            continue
        if _normalize_str(out_payload.get("status")) == "failed":
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": _normalize_str(out_payload.get("model_variant")) or "unknown",
                    "reason": "train_failed",
                }
            )
            continue

        try:
            model_bundle_path = get_task_artifact_local_copy(cfg, task_id, "model_bundle.joblib")
            bundle = load_bundle(model_bundle_path)
        except Exception as exc:
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": _normalize_str(out_payload.get("model_variant")) or "unknown",
                    "reason": "missing_model_bundle",
                    "details": str(exc),
                }
            )
            continue
        if not isinstance(bundle, dict):
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": "unknown",
                    "reason": "model_bundle_invalid",
                }
            )
            continue

        model_variant = _normalize_str(bundle.get("model_variant")) or _normalize_str(
            out_payload.get("model_variant")
        ) or "unknown"
        if model_variant.lower() in exclude_variants:
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": model_variant,
                    "reason": "excluded_variant",
                }
            )
            continue

        preprocess_bundle = bundle.get("preprocess_bundle") or {}
        preprocess_variant = _normalize_str(preprocess_bundle.get("preprocess_variant")) or "unknown"
        if desired_preprocess and preprocess_variant != desired_preprocess:
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": model_variant,
                    "reason": "preprocess_mismatch",
                    "details": preprocess_variant,
                }
            )
            continue

        task_type = _normalize_task_type(bundle.get("task_type") or out_payload.get("task_type"))

        try:
            metrics_path = get_task_artifact_local_copy(cfg, task_id, "metrics.json")
            metrics_payload = _load_json(metrics_path)
        except Exception as exc:
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": model_variant,
                    "reason": "missing_metrics",
                    "details": str(exc),
                }
            )
            continue
        metric_value = _metric_value_from_payload(metrics_payload, selection_metric)
        if metric_value is None:
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": model_variant,
                    "reason": "metric_missing",
                    "details": selection_metric,
                }
            )
            continue

        preds_path = None
        try:
            preds_path = get_task_artifact_local_copy(cfg, task_id, "preds_valid.parquet")
        except Exception as exc:
            if not allow_missing_preds:
                skipped.append(
                    {
                        "train_task_id": task_id,
                        "model_variant": model_variant,
                        "reason": "missing_preds_valid",
                        "details": str(exc),
                    }
                )
                continue

        classes = None
        if task_type == "classification":
            try:
                classes_path = get_task_artifact_local_copy(cfg, task_id, "classes.json")
                classes = _read_classes(classes_path)
            except Exception as exc:
                skipped.append(
                    {
                        "train_task_id": task_id,
                        "model_variant": model_variant,
                        "reason": "missing_classes",
                        "details": str(exc),
                    }
                )
                continue
            if not classes:
                skipped.append(
                    {
                        "train_task_id": task_id,
                        "model_variant": model_variant,
                        "reason": "missing_classes",
                    }
                )
                continue

        candidates.append(
            _Candidate(
                train_task_id=task_id,
                run_dir=None,
                model_variant=model_variant,
                preprocess_variant=preprocess_variant,
                task_type=task_type,
                metric_value=float(metric_value),
                preds_path=preds_path,
                classes=classes,
                model_bundle_path=model_bundle_path,
                model_id=_normalize_str(out_payload.get("model_id")),
                processed_dataset_id=_normalize_str(out_payload.get("processed_dataset_id")),
                split_hash=_normalize_str(out_payload.get("split_hash")),
                recipe_hash=_normalize_str(out_payload.get("recipe_hash")),
            )
        )
    return candidates


def _compute_metrics(
    cfg: Any,
    *,
    task_type: str,
    y_true: Any,
    y_pred: Any,
    y_proba: Any | None,
    n_classes: int | None,
    primary_metric: str,
) -> dict[str, float]:
    metrics_holdout: dict[str, float] = {}
    if task_type == "classification":
        metric_names = _resolve_classification_metrics(cfg, n_classes=n_classes)
        fbeta_beta = _cfg_value(cfg, "eval.metrics.fbeta_beta", 1.0)
        try:
            fbeta_beta = float(fbeta_beta)
        except Exception:
            fbeta_beta = 1.0
        for name in metric_names:
            if n_classes is not None and n_classes != 2 and name in ("roc_auc", "auc", "pr_auc"):
                continue
            if metric_requires_proba(name, task_type) and y_proba is None:
                continue
            metric_fn = get_metric(name, task_type, n_classes=n_classes, beta=fbeta_beta)
            metrics_holdout[name] = float(metric_fn(y_true, y_pred, y_proba))
        if primary_metric not in metrics_holdout:
            metric_fn = get_metric(primary_metric, task_type, n_classes=n_classes, beta=fbeta_beta)
            metrics_holdout[primary_metric] = float(metric_fn(y_true, y_pred, y_proba))
    else:
        metric_names = _resolve_regression_metrics(cfg)
        regression_metrics = compute_regression_metrics(y_true, y_pred, metrics=metric_names)
        metrics_holdout.update(regression_metrics)
        if primary_metric not in metrics_holdout:
            metrics_holdout[primary_metric] = float(
                get_metric(primary_metric, task_type)(y_true, y_pred)
            )
    return metrics_holdout


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _resolve_weighted_settings(cfg: Any) -> dict[str, Any]:
    search = _normalize_str(_cfg_value(cfg, "ensemble.weighted.search")) or "linear"
    if search not in ("linear", "random_simplex"):
        search = "linear"
    n_samples = _coerce_int(_cfg_value(cfg, "ensemble.weighted.n_samples", 1500), 1500)
    seed = _coerce_int(_cfg_value(cfg, "ensemble.weighted.seed", 42), 42)
    top_k_max = _coerce_int(_cfg_value(cfg, "ensemble.weighted.top_k_max", 5), 5)
    return {
        "search": search,
        "n_samples": n_samples,
        "seed": seed,
        "top_k_max": top_k_max,
    }


def _resolve_weighted_top_k(top_k: int, top_k_max: int) -> int:
    if top_k_max <= 0:
        return top_k
    if top_k <= 0:
        return top_k_max
    return min(top_k, top_k_max)


def _resolve_stacking_settings(cfg: Any) -> dict[str, Any]:
    meta_model = _normalize_str(_cfg_value(cfg, "ensemble.stacking.meta_model")) or "ridge"
    cv_folds = _coerce_int(_cfg_value(cfg, "ensemble.stacking.cv_folds", 5), 5)
    seed = _coerce_int(_cfg_value(cfg, "ensemble.stacking.seed", 42), 42)
    require_test_split = bool(_cfg_value(cfg, "ensemble.stacking.require_test_split", False))
    return {
        "meta_model": meta_model.lower(),
        "cv_folds": cv_folds,
        "seed": seed,
        "require_test_split": require_test_split,
    }


def _build_meta_features(
    included_preds: Sequence[tuple[Any, Any, Any | None]],
    base_models: Sequence[Mapping[str, Any]],
    *,
    task_type: str,
    classes: list[str] | None,
) -> tuple[Any, list[str]]:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for stacking meta features.") from exc
    feature_names: list[str] = []
    if task_type == "classification":
        proba_list = []
        if not classes:
            raise ValueError("classes are required for classification stacking.")
        for idx, (preds, base) in enumerate(zip(included_preds, base_models)):
            proba = preds[2]
            if proba is None:
                raise ValueError("stacking requires predicted probabilities for classification.")
            proba_arr = np.asarray(proba)
            if proba_arr.ndim == 1:
                proba_arr = np.stack([1.0 - proba_arr, proba_arr], axis=1)
            if proba_arr.shape[1] != len(classes):
                raise ValueError("stacking probability columns do not match classes.")
            proba_list.append(proba_arr)
            model_label = _normalize_str(base.get("model_variant")) or f"model_{idx}"
            for label in classes:
                feature_names.append(f"{model_label}__proba__{label}")
        X_meta = np.concatenate(proba_list, axis=1)
        return X_meta, feature_names
    pred_list = []
    for idx, (preds, base) in enumerate(zip(included_preds, base_models)):
        pred_list.append(np.asarray(preds[1]))
        model_label = _normalize_str(base.get("model_variant")) or f"model_{idx}"
        feature_names.append(model_label)
    X_meta = np.column_stack(pred_list)
    return X_meta, feature_names


def _build_meta_model(task_type: str, meta_model: str, seed: int):
    meta_key = meta_model.lower().strip()
    if task_type == "classification":
        if meta_key not in ("logreg", "logistic_regression"):
            raise ValueError("classification stacking requires meta_model=logreg.")
        try:
            from sklearn.linear_model import LogisticRegression  # type: ignore
        except Exception as exc:
            raise RuntimeError("scikit-learn is required for stacking logistic regression.") from exc
        model = LogisticRegression(max_iter=1000, solver="lbfgs", multi_class="auto", random_state=seed)
        return model, "logreg"
    if meta_key in ("elasticnet", "elastic_net"):
        try:
            from sklearn.linear_model import ElasticNet  # type: ignore
        except Exception as exc:
            raise RuntimeError("scikit-learn is required for stacking ElasticNet.") from exc
        model = ElasticNet(random_state=seed)
        return model, "elasticnet"
    try:
        from sklearn.linear_model import Ridge  # type: ignore
    except Exception as exc:
        raise RuntimeError("scikit-learn is required for stacking Ridge.") from exc
    model = Ridge(random_state=seed)
    return model, "ridge"


def _describe_meta_model(model: Any, meta_type: str) -> dict[str, Any]:
    try:
        params = model.get_params()
    except Exception:
        params = {}
    return {"type": meta_type, "params": params}


def _compute_meta_cv_score(
    cfg: Any,
    *,
    X_meta: Any,
    y_true: Any,
    task_type: str,
    primary_metric: str,
    cv_folds: int,
    seed: int,
    n_classes: int | None,
    meta_model: str,
) -> tuple[float, list[float]]:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for stacking CV.") from exc
    try:
        from sklearn.model_selection import KFold, StratifiedKFold  # type: ignore
    except Exception as exc:
        raise RuntimeError("scikit-learn is required for stacking CV.") from exc
    X_arr = np.asarray(X_meta)
    y_arr = np.asarray(y_true)
    if cv_folds < 2:
        raise ValueError("stacking cv_folds must be >= 2.")
    if len(y_arr) < cv_folds:
        raise ValueError("stacking cv_folds is larger than available samples.")
    if task_type == "classification":
        splitter = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
    else:
        splitter = KFold(n_splits=cv_folds, shuffle=True, random_state=seed)
    fbeta_beta = _cfg_value(cfg, "eval.metrics.fbeta_beta", 1.0)
    try:
        fbeta_beta = float(fbeta_beta)
    except Exception:
        fbeta_beta = 1.0
    metric_fn = get_metric(primary_metric, task_type, n_classes=n_classes, beta=fbeta_beta)
    requires_proba = metric_requires_proba(primary_metric, task_type)
    scores: list[float] = []
    for fold_train_idx, fold_val_idx in splitter.split(X_arr, y_arr):
        model, _ = _build_meta_model(task_type, meta_model, seed)
        model.fit(X_arr[fold_train_idx], y_arr[fold_train_idx])
        y_pred = model.predict(X_arr[fold_val_idx])
        y_proba = None
        if task_type == "classification" and requires_proba:
            if not hasattr(model, "predict_proba"):
                raise ValueError("stacking meta_model missing predict_proba.")
            y_proba = model.predict_proba(X_arr[fold_val_idx])
        score = float(metric_fn(y_arr[fold_val_idx], y_pred, y_proba))
        if math.isfinite(score):
            scores.append(score)
    if not scores:
        raise ValueError("stacking CV produced no valid scores.")
    return float(np.mean(scores)), scores


def _summarize_meta_coefficients(
    meta_model: Any,
    feature_names: Sequence[str],
    *,
    max_rows: int = 20,
) -> list[dict[str, Any]] | None:
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None
    coef = getattr(meta_model, "coef_", None)
    if coef is None:
        return None
    coef_arr = np.asarray(coef)
    if coef_arr.ndim == 2 and coef_arr.shape[0] > 1:
        weights = np.mean(np.abs(coef_arr), axis=0)
        label = "coef_abs"
    else:
        weights = coef_arr.reshape(-1)
        label = "coef"
    if weights.size == 0:
        return None
    pairs = list(zip(feature_names, weights))
    pairs.sort(key=lambda item: abs(item[1]), reverse=True)
    rows = [{"feature": name, label: float(weight)} for name, weight in pairs[:max_rows]]
    return rows


def _resolve_artifact_path(base_dir: Path, name: str) -> Path | None:
    for candidate in (base_dir / name, base_dir / "processed_dataset" / name):
        if candidate.exists():
            return candidate
    return None


def _resolve_split_path(base_dir: Path) -> Path:
    for name in ("splits.json", "split.json"):
        candidate = _resolve_artifact_path(base_dir, name)
        if candidate is not None:
            return candidate
    raise FileNotFoundError(f"split file not found under: {base_dir}")


def _extract_split_indices(split_payload: dict[str, Any], split_key: str) -> list[int] | None:
    if split_key == "test":
        keys = ("test_index", "test_indices")
    else:
        keys = ("val_index", "val_indices")
    for key in keys:
        values = split_payload.get(key)
        if values:
            try:
                return list(values)
            except Exception:
                return None
    return None


def _resolve_processed_dataset_dir(
    cfg: Any,
    processed_dataset_id: str | None,
    candidate_run_dir: Path | None,
) -> Path:
    if is_clearml_enabled(cfg) and processed_dataset_id and not processed_dataset_id.startswith("local:"):
        from ..clearml.datasets import get_processed_dataset_local_copy

        return get_processed_dataset_local_copy(cfg, processed_dataset_id)
    run_root = Path(_cfg_value(cfg, "run.output_dir", "outputs")).expanduser().resolve()
    search_root = _resolve_search_root(run_root)
    preprocess_run_dir = _find_preprocess_run_dir(search_root, processed_dataset_id)
    if preprocess_run_dir is None:
        raise ValueError("preprocess run dir not found for fallback predictions.")
    return preprocess_run_dir


def _primary_metric_source_code(source: str) -> float:
    mapping = {
        "valid": 0.0,
        "meta_cv_on_valid": 1.0,
        "test": 2.0,
        "fallback_mean_topk_on_valid": -1.0,
        "fallback_top1_on_valid": -2.0,
    }
    return float(mapping.get(source, -99.0))


def _normalize_weights(weights: Any) -> Any | None:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for ensemble weights.") from exc
    arr = np.asarray(weights, dtype=float)
    if arr.ndim > 1:
        arr = arr.reshape(-1)
    arr = np.where(np.isfinite(arr), arr, 0.0)
    arr = np.maximum(arr, 0.0)
    total = float(arr.sum())
    if not math.isfinite(total) or total <= 0:
        return None
    return arr / total


def _estimate_linear_weights(pred_stack: Any, y_true: Any) -> Any | None:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for ensemble weights.") from exc
    X = np.asarray(pred_stack).T
    try:
        from sklearn.linear_model import LinearRegression  # type: ignore

        model = LinearRegression(positive=True, fit_intercept=False)
        model.fit(X, y_true)
        weights = model.coef_
    except TypeError:
        try:
            from sklearn.linear_model import Ridge  # type: ignore

            model = Ridge(fit_intercept=False)
            model.fit(X, y_true)
            weights = model.coef_
        except Exception:
            return None
    except Exception:
        return None
    return _normalize_weights(weights)


def _random_simplex_search(
    *,
    pred_stack: Any | None,
    proba_stack: Any | None,
    y_true: Any,
    metric_fn: Any,
    direction: str,
    n_samples: int,
    seed: int,
) -> tuple[Any | None, float | None]:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for ensemble weights.") from exc
    stack = proba_stack if proba_stack is not None else pred_stack
    if stack is None:
        return None, None
    n_models = int(np.asarray(stack).shape[0])
    if n_models <= 0:
        return None, None
    if n_models == 1:
        weights = np.array([1.0])
        return weights, None
    n_samples = int(n_samples)
    if n_samples <= 0:
        return None, None
    rng = np.random.default_rng(seed)
    best_weights = None
    best_score = None
    for _ in range(n_samples):
        weights = rng.dirichlet(np.ones(n_models))
        try:
            if proba_stack is not None:
                y_proba = np.tensordot(weights, proba_stack, axes=(0, 0))
                y_pred = np.asarray(y_proba).argmax(axis=1)
                score = float(metric_fn(y_true, y_pred, y_proba))
            else:
                y_pred = np.tensordot(weights, pred_stack, axes=(0, 0))
                score = float(metric_fn(y_true, y_pred, None))
        except Exception:
            continue
        if not math.isfinite(score):
            continue
        if best_score is None:
            best_score = score
            best_weights = weights
        elif direction == "maximize":
            if score > best_score:
                best_score = score
                best_weights = weights
        else:
            if score < best_score:
                best_score = score
                best_weights = weights
    return best_weights, best_score


def _estimate_weighted_weights(
    cfg: Any,
    *,
    task_type: str,
    y_true: Any,
    pred_stack: Any | None,
    proba_stack: Any | None,
    primary_metric: str,
    direction: str,
    search: str,
    n_samples: int,
    seed: int,
) -> tuple[Any | None, str | None]:
    fbeta_beta = _cfg_value(cfg, "eval.metrics.fbeta_beta", 1.0)
    try:
        fbeta_beta = float(fbeta_beta)
    except Exception:
        fbeta_beta = 1.0
    n_classes = None
    if proba_stack is not None:
        try:
            n_classes = int(proba_stack.shape[2])
        except Exception:
            n_classes = None
    metric_fn = get_metric(primary_metric, task_type, n_classes=n_classes, beta=fbeta_beta)
    direction = direction.lower()

    if task_type == "regression":
        if search == "random_simplex":
            weights, _ = _random_simplex_search(
                pred_stack=pred_stack,
                proba_stack=None,
                y_true=y_true,
                metric_fn=metric_fn,
                direction=direction,
                n_samples=n_samples,
                seed=seed,
            )
            if weights is not None:
                return weights, "random_simplex"
            weights = _estimate_linear_weights(pred_stack, y_true)
            if weights is not None:
                return weights, "linear"
        else:
            weights = _estimate_linear_weights(pred_stack, y_true)
            if weights is not None:
                return weights, "linear"
            weights, _ = _random_simplex_search(
                pred_stack=pred_stack,
                proba_stack=None,
                y_true=y_true,
                metric_fn=metric_fn,
                direction=direction,
                n_samples=n_samples,
                seed=seed,
            )
            if weights is not None:
                return weights, "random_simplex"
        return None, None

    weights, _ = _random_simplex_search(
        pred_stack=None,
        proba_stack=proba_stack,
        y_true=y_true,
        metric_fn=metric_fn,
        direction=direction,
        n_samples=n_samples,
        seed=seed,
    )
    if weights is not None:
        return weights, "random_simplex"
    return None, None


def _record_failure(
    *,
    ctx: Any,
    cfg: Any,
    reason: str,
    details: str | None = None,
    primary_metric: str,
    task_type: str,
) -> None:
    out = {
        "model_id": None,
        "train_task_id": _normalize_str(getattr(ctx.task, "id", None)),
        "best_score": None,
        "primary_metric": primary_metric,
        "task_type": task_type,
        "status": "failed",
        "reason": reason,
    }
    if details:
        out["error"] = {"message": details}
    write_out_json(ctx, out)

    versions = resolve_version_props(cfg, clearml_enabled=is_clearml_enabled(cfg))
    hashes = _resolve_manifest_hashes(cfg, split_hash=None, recipe_hash=None)
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "train_ensemble",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {},
        "outputs": {"status": "failed", "reason": reason},
        "hashes": hashes,
        "error": {"reason": reason, "details": details},
    }
    write_manifest(ctx, manifest)


def _resolve_manifest_hashes(
    cfg: Any,
    *,
    split_hash: str | None,
    recipe_hash: str | None,
) -> dict[str, str]:
    resolved_split = _normalize_str(split_hash)
    resolved_recipe = _normalize_str(recipe_hash)
    if not resolved_split or not resolved_recipe:
        processed_dataset_id = _normalize_str(_cfg_value(cfg, "data.processed_dataset_id"))
        if processed_dataset_id:
            try:
                base_dir = _resolve_processed_dataset_dir(cfg, processed_dataset_id, None)
                meta_path = _resolve_artifact_path(base_dir, "meta.json")
                if meta_path is not None and meta_path.exists():
                    payload = json.loads(meta_path.read_text(encoding="utf-8"))
                    if not resolved_split:
                        resolved_split = _normalize_str(payload.get("split_hash"))
                    if not resolved_recipe:
                        resolved_recipe = _normalize_str(payload.get("recipe_hash"))
            except Exception:
                pass
    return {
        "config_hash": hash_config(cfg),
        "split_hash": resolved_split or "unknown",
        "recipe_hash": resolved_recipe or "unknown",
    }


def _record_skip(
    *,
    ctx: Any,
    cfg: Any,
    reason: str,
    detail: Any | None,
    primary_metric: str,
    task_type: str,
    preprocess_variant: str,
    method: str,
) -> None:
    out = {
        "model_id": None,
        "train_task_id": _normalize_str(getattr(ctx.task, "id", None)),
        "best_score": None,
        "primary_metric": primary_metric,
        "task_type": task_type,
        "preprocess_variant": preprocess_variant,
        "ensemble_method": method,
    }
    emit_skip(ctx, reason=reason, detail=detail, out=out)

    versions = resolve_version_props(cfg, clearml_enabled=is_clearml_enabled(cfg))
    hashes = _resolve_manifest_hashes(cfg, split_hash=None, recipe_hash=None)
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "train_ensemble",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "preprocess_variant": preprocess_variant,
            "method": method,
        },
        "outputs": {
            "model_id": None,
            "best_score": None,
            "primary_metric": primary_metric,
            "task_type": task_type,
            "status": "skipped",
            "reason": reason,
        },
        "hashes": hashes,
    }
    write_manifest(ctx, manifest)


def run(cfg: Any) -> None:
    identity = apply_clearml_identity(cfg, stage=cfg.task.stage)
    apply_train_ensemble_naming(cfg)
    ctx = init_task_context(
        cfg,
        stage=cfg.task.stage,
        task_name="train_ensemble",
        tags=identity.tags,
        properties=identity.user_properties,
    )
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)
    preprocess_variant = _resolve_preprocess_variant(cfg)
    desired_preprocess = preprocess_variant
    if preprocess_variant is None:
        preprocess_variant = "unknown"
        desired_preprocess = None

    ensemble_cfg = getattr(cfg, "ensemble", None)
    method = _normalize_str(getattr(ensemble_cfg, "method", None)) or "mean_topk"
    weighted_settings = None
    stacking_settings = None
    if method == "weighted":
        weighted_settings = _resolve_weighted_settings(cfg)
    elif method == "stacking":
        stacking_settings = _resolve_stacking_settings(cfg)
    elif method != "mean_topk":
        raise ValueError(f"Unsupported ensemble.method: {method}")
    top_k = int(getattr(ensemble_cfg, "top_k", 3) or 0)
    if weighted_settings is not None:
        top_k = _resolve_weighted_top_k(top_k, int(weighted_settings["top_k_max"]))
    required_candidates = _required_candidate_count(method, top_k)
    task_type_hint = _normalize_task_type(_cfg_value(cfg, "eval.task_type"))
    ensemble_spec = _find_ensemble_spec(method, task_type=task_type_hint)
    if ensemble_spec is not None:
        missing = list(ensemble_spec.missing_dependencies() or [])
        if missing:
            _record_skip(
                ctx=ctx,
                cfg=cfg,
                reason="missing_dependency",
                detail={"missing": missing, "method": method},
                primary_metric=_resolve_primary_metric(cfg),
                task_type=task_type_hint,
                preprocess_variant=preprocess_variant,
                method=method,
            )
            return
    selection_metric = _resolve_selection_metric(cfg)
    exclude_variants = {
        v.lower()
        for v in _ensure_str_list(getattr(ensemble_cfg, "exclude_variants", None))
        if _normalize_str(v)
    }
    fallback_rerun = bool(getattr(ensemble_cfg, "fallback_rerun_predict", False))

    desired_usecase = _normalize_str(_cfg_value(cfg, "run.usecase_id"))

    skipped: list[dict[str, Any]] = []
    if clearml_enabled:
        candidates = _collect_candidates_clearml(
            cfg,
            desired_usecase=desired_usecase,
            desired_preprocess=desired_preprocess,
            selection_metric=selection_metric,
            exclude_variants=exclude_variants,
            allow_missing_preds=fallback_rerun,
            skipped=skipped,
        )
    else:
        candidates = _collect_candidates_local(
            cfg,
            desired_usecase=desired_usecase,
            desired_preprocess=desired_preprocess,
            selection_metric=selection_metric,
            exclude_variants=exclude_variants,
            allow_missing_preds=fallback_rerun,
            skipped=skipped,
        )

    if not candidates:
        _record_skip(
            ctx=ctx,
            cfg=cfg,
            reason="insufficient_candidates",
            detail={
                "available": 0,
                "required": required_candidates,
                "skipped_reasons": _summarize_skips(skipped),
            },
            primary_metric=_resolve_primary_metric(cfg),
            task_type=task_type_hint,
            preprocess_variant=preprocess_variant,
            method=method,
        )
        return

    task_type = _normalize_task_type(_cfg_value(cfg, "eval.task_type") or candidates[0].task_type)
    selection_direction = metric_direction(selection_metric, task_type)
    def _sort_key(candidate: _Candidate) -> tuple[float, str, str]:
        metric_value = candidate.metric_value
        if selection_direction == "maximize":
            metric_value = -metric_value
        tie_task = candidate.train_task_id or ""
        tie_path = str(candidate.run_dir) if candidate.run_dir is not None else ""
        return (metric_value, candidate.model_variant, tie_task or tie_path)
    candidates_sorted = sorted(candidates, key=_sort_key)

    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for ensemble aggregation.") from exc

    included: list[dict[str, Any]] = []
    included_preds: list[tuple[Any, Any, Any | None]] = []
    included_candidates: list[_Candidate] = []
    base_models: list[dict[str, Any]] = []
    ref_processed_dataset_id = None
    ref_split_hash = None
    ref_recipe_hash = None
    ref_classes = None
    ref_y_true = None
    for candidate in candidates_sorted:
        if top_k > 0 and len(included) >= top_k:
            break
        if candidate.task_type != task_type:
            skipped.append(
                {
                    "train_task_id": candidate.train_task_id,
                    "model_variant": candidate.model_variant,
                    "reason": "task_type_mismatch",
                    "details": candidate.task_type,
                }
            )
            continue
        if candidate.processed_dataset_id and ref_processed_dataset_id:
            if candidate.processed_dataset_id != ref_processed_dataset_id:
                skipped.append(
                    {
                        "train_task_id": candidate.train_task_id,
                        "model_variant": candidate.model_variant,
                        "reason": "processed_dataset_mismatch",
                    }
                )
                continue
        if candidate.split_hash and ref_split_hash:
            if candidate.split_hash != ref_split_hash:
                skipped.append(
                    {
                        "train_task_id": candidate.train_task_id,
                        "model_variant": candidate.model_variant,
                        "reason": "split_mismatch",
                    }
                )
                continue
        if candidate.recipe_hash and ref_recipe_hash:
            if candidate.recipe_hash != ref_recipe_hash:
                skipped.append(
                    {
                        "train_task_id": candidate.train_task_id,
                        "model_variant": candidate.model_variant,
                        "reason": "recipe_mismatch",
                    }
                )
                continue
        preds_ref = str(candidate.preds_path) if candidate.preds_path is not None else "fallback_rerun"
        if candidate.preds_path is None:
            if fallback_rerun and candidate.model_bundle_path is not None:
                try:
                    y_true, y_pred, y_proba = _rerun_predictions(
                        cfg,
                        candidate,
                        preprocess_variant=preprocess_variant,
                    )
                except Exception as rerun_exc:
                    skipped.append(
                        {
                            "train_task_id": candidate.train_task_id,
                            "model_variant": candidate.model_variant,
                            "reason": "fallback_rerun_failed",
                            "details": str(rerun_exc),
                        }
                    )
                    continue
            else:
                skipped.append(
                    {
                        "train_task_id": candidate.train_task_id,
                        "model_variant": candidate.model_variant,
                        "reason": "missing_preds_valid",
                    }
                )
                continue
        else:
            try:
                y_true, y_pred, y_proba = _extract_preds_payload(
                    candidate.preds_path,
                    task_type=task_type,
                    classes=candidate.classes,
                )
            except Exception as exc:
                if fallback_rerun and candidate.model_bundle_path is not None:
                    try:
                        y_true, y_pred, y_proba = _rerun_predictions(
                            cfg,
                            candidate,
                            preprocess_variant=preprocess_variant,
                        )
                        preds_ref = "fallback_rerun"
                    except Exception as rerun_exc:
                        skipped.append(
                            {
                                "train_task_id": candidate.train_task_id,
                                "model_variant": candidate.model_variant,
                                "reason": "preds_invalid",
                                "details": str(rerun_exc),
                            }
                        )
                        continue
                else:
                    skipped.append(
                        {
                            "train_task_id": candidate.train_task_id,
                            "model_variant": candidate.model_variant,
                            "reason": "preds_invalid",
                            "details": str(exc),
                        }
                    )
                    continue
        if ref_y_true is None:
            ref_y_true = y_true
        else:
            if len(ref_y_true) != len(y_true) or not np.array_equal(ref_y_true, y_true):
                skipped.append(
                    {
                        "train_task_id": candidate.train_task_id,
                        "model_variant": candidate.model_variant,
                        "reason": "y_true_mismatch",
                    }
                )
                continue
        if ref_classes is None and task_type == "classification":
            ref_classes = candidate.classes
        if task_type == "classification" and candidate.classes != ref_classes:
            skipped.append(
                {
                    "train_task_id": candidate.train_task_id,
                    "model_variant": candidate.model_variant,
                    "reason": "classes_mismatch",
                }
            )
            continue
        if ref_processed_dataset_id is None:
            ref_processed_dataset_id = candidate.processed_dataset_id
        if ref_split_hash is None:
            ref_split_hash = candidate.split_hash
        if ref_recipe_hash is None:
            ref_recipe_hash = candidate.recipe_hash
        included_preds.append((y_true, y_pred, y_proba))
        included.append(
            {
                "train_task_id": candidate.train_task_id,
                "model_variant": candidate.model_variant,
                "metric_value": candidate.metric_value,
                "preds_ref": preds_ref,
            }
        )
        included_candidates.append(candidate)
        base_models.append(
            {
                "train_task_id": candidate.train_task_id,
                "model_id": candidate.model_id,
                "model_variant": candidate.model_variant,
                "preprocess_variant": candidate.preprocess_variant,
            }
        )

    if not included_preds:
        _record_skip(
            ctx=ctx,
            cfg=cfg,
            reason="insufficient_candidates",
            detail={
                "available": len(candidates),
                "included": len(included_candidates),
                "required": required_candidates,
                "skipped_reasons": _summarize_skips(skipped),
            },
            primary_metric=_resolve_primary_metric(cfg),
            task_type=task_type,
            preprocess_variant=preprocess_variant,
            method=method,
        )
        return

    y_true = included_preds[0][0]
    primary_metric = _resolve_primary_metric(cfg)
    direction = _resolve_direction(cfg, primary_metric, task_type)

    weights = None
    weights_map = None
    weight_rows = None
    degraded_to = None
    degraded_reason = None
    search_used = None
    search_requested = None
    objective_metric = primary_metric
    objective_direction = direction
    n_samples = None
    seed = None
    top_k_max = None
    primary_metric_source = "valid"
    meta_model = None
    meta_model_info = None
    meta_model_path = None
    meta_training_protocol: dict[str, Any] | None = None
    fit_score_on_valid = None
    meta_coeff_rows = None
    fallback_weights = None
    eval_y_true = y_true
    train_rows = len(y_true)
    eval_rows = len(y_true)

    metrics_holdout = None
    best_score = None

    if method == "mean_topk":
        if task_type == "classification":
            proba_stack = np.stack([preds[2] for preds in included_preds if preds[2] is not None], axis=0)
            if proba_stack.size == 0:
                raise ValueError("classification ensemble requires predicted probabilities.")
            y_proba = proba_stack.mean(axis=0)
            if y_proba.ndim != 2:
                raise ValueError("ensemble probabilities are invalid.")
            y_pred = y_proba.argmax(axis=1)
            n_classes = int(y_proba.shape[1])
        else:
            pred_stack = np.stack([preds[1] for preds in included_preds], axis=0)
            y_pred = pred_stack.mean(axis=0)
            y_proba = None
            n_classes = None
    elif method == "weighted":
        if weighted_settings is None:
            weighted_settings = _resolve_weighted_settings(cfg)
        search_requested = str(weighted_settings.get("search") or "linear")
        n_samples = int(weighted_settings.get("n_samples") or 0)
        seed = int(weighted_settings.get("seed") or 0)
        top_k_max = int(weighted_settings.get("top_k_max") or 0)
        if task_type == "classification":
            proba_list = [preds[2] for preds in included_preds]
            if any(item is None for item in proba_list):
                raise ValueError("classification ensemble requires predicted probabilities.")
            proba_stack = np.stack(proba_list, axis=0)
            weights, search_used = _estimate_weighted_weights(
                cfg,
                task_type=task_type,
                y_true=y_true,
                pred_stack=None,
                proba_stack=proba_stack,
                primary_metric=primary_metric,
                direction=direction,
                search=search_requested,
                n_samples=n_samples,
                seed=seed,
            )
            if weights is None or len(weights) != len(included_preds):
                weights = np.zeros(len(included_preds))
                weights[0] = 1.0
                degraded_to = "top1"
            y_proba = np.tensordot(weights, proba_stack, axes=(0, 0))
            if y_proba.ndim != 2:
                raise ValueError("ensemble probabilities are invalid.")
            y_pred = y_proba.argmax(axis=1)
            n_classes = int(y_proba.shape[1])
        else:
            pred_stack = np.stack([preds[1] for preds in included_preds], axis=0)
            weights, search_used = _estimate_weighted_weights(
                cfg,
                task_type=task_type,
                y_true=y_true,
                pred_stack=pred_stack,
                proba_stack=None,
                primary_metric=primary_metric,
                direction=direction,
                search=search_requested,
                n_samples=n_samples,
                seed=seed,
            )
            if weights is None or len(weights) != len(included_preds):
                weights = np.zeros(len(included_preds))
                weights[0] = 1.0
                degraded_to = "top1"
            y_pred = np.tensordot(weights, pred_stack, axes=(0, 0))
            y_proba = None
            n_classes = None

        weights_map = {}
        weight_rows = []
        weights_arr = np.asarray(weights).reshape(-1)
        for idx, (entry, weight) in enumerate(zip(included, weights_arr)):
            key = _normalize_str(entry.get("train_task_id"))
            if not key:
                model_variant = _normalize_str(entry.get("model_variant")) or "unknown"
                key = f"local:{model_variant}:{idx}"
            weights_map[key] = float(weight)
            weight_rows.append(
                {
                    "train_task_id": entry.get("train_task_id"),
                    "model_variant": entry.get("model_variant"),
                    "weight": float(weight),
                }
            )
        if search_used is None:
            search_used = search_requested
        if degraded_to:
            search_used = search_used or "random_simplex"
    else:
        if stacking_settings is None:
            stacking_settings = _resolve_stacking_settings(cfg)
        seed = int(stacking_settings.get("seed") or 0)
        cv_folds = int(stacking_settings.get("cv_folds") or 0)
        meta_model_key = str(stacking_settings.get("meta_model") or "ridge")
        meta_model_requested = meta_model_key
        if task_type == "classification":
            meta_model_key = "logreg"
        elif meta_model_key in ("logreg", "logistic_regression"):
            meta_model_key = "ridge"
        require_test_split = bool(stacking_settings.get("require_test_split"))
        meta_training_protocol = {
            "cv_folds": cv_folds,
            "seed": seed,
            "require_test_split": require_test_split,
            "meta_model_requested": meta_model_requested,
            "meta_model_used": meta_model_key,
        }
        try:
            X_meta, meta_feature_names = _build_meta_features(
                included_preds,
                base_models,
                task_type=task_type,
                classes=ref_classes,
            )
            has_test_split = False
            test_split_error = None
            try:
                base_dir = _resolve_processed_dataset_dir(
                    cfg,
                    ref_processed_dataset_id,
                    included_candidates[0].run_dir if included_candidates else None,
                )
                split_path = _resolve_split_path(base_dir)
                split_payload = _load_json(split_path)
                test_indices = _extract_split_indices(split_payload, "test")
                has_test_split = bool(test_indices)
            except Exception as exc:
                test_split_error = str(exc)
            meta_training_protocol["has_test_split"] = has_test_split
            if test_split_error:
                meta_training_protocol["test_split_error"] = test_split_error

            use_test = False
            test_preds: list[tuple[Any, Any, Any | None]] | None = None
            if has_test_split:
                try:
                    test_preds = []
                    ref_test_y = None
                    for candidate in included_candidates:
                        y_true_test, y_pred_test, y_proba_test = _rerun_predictions(
                            cfg,
                            candidate,
                            preprocess_variant=preprocess_variant,
                            split_key="test",
                        )
                        if ref_test_y is None:
                            ref_test_y = y_true_test
                        else:
                            if len(ref_test_y) != len(y_true_test) or not np.array_equal(
                                ref_test_y, y_true_test
                            ):
                                raise ValueError("test y_true mismatch across base models.")
                        test_preds.append((y_true_test, y_pred_test, y_proba_test))
                    use_test = bool(test_preds)
                except Exception as exc:
                    if require_test_split:
                        raise
                    meta_training_protocol["test_eval_error"] = str(exc)
                    use_test = False

            meta_model, meta_type = _build_meta_model(task_type, meta_model_key, seed)
            meta_model_info = _describe_meta_model(meta_model, meta_type)
            meta_model.fit(X_meta, y_true)
            meta_coeff_rows = _summarize_meta_coefficients(meta_model, meta_feature_names)

            y_pred_fit = meta_model.predict(X_meta)
            y_proba_fit = None
            if task_type == "classification" and hasattr(meta_model, "predict_proba"):
                y_proba_fit = meta_model.predict_proba(X_meta)
            fit_metrics = _compute_metrics(
                cfg,
                task_type=task_type,
                y_true=y_true,
                y_pred=y_pred_fit,
                y_proba=y_proba_fit,
                n_classes=int(y_proba_fit.shape[1]) if y_proba_fit is not None else None,
                primary_metric=primary_metric,
            )
            fit_score_on_valid = fit_metrics.get(primary_metric)

            if use_test and test_preds:
                X_meta_test, _ = _build_meta_features(
                    test_preds,
                    base_models,
                    task_type=task_type,
                    classes=ref_classes,
                )
                eval_y_true = test_preds[0][0]
                train_rows = len(y_true)
                eval_rows = len(eval_y_true)
                y_pred = meta_model.predict(X_meta_test)
                y_proba = None
                if task_type == "classification" and hasattr(meta_model, "predict_proba"):
                    y_proba = meta_model.predict_proba(X_meta_test)
                n_classes = int(y_proba.shape[1]) if y_proba is not None else None
                metrics_holdout = _compute_metrics(
                    cfg,
                    task_type=task_type,
                    y_true=eval_y_true,
                    y_pred=y_pred,
                    y_proba=y_proba,
                    n_classes=n_classes,
                    primary_metric=primary_metric,
                )
                best_score = metrics_holdout.get(primary_metric)
                primary_metric_source = "test"
                meta_training_protocol["used_test_split"] = True
            else:
                cv_score, cv_scores = _compute_meta_cv_score(
                    cfg,
                    X_meta=X_meta,
                    y_true=y_true,
                    task_type=task_type,
                    primary_metric=primary_metric,
                    cv_folds=cv_folds,
                    seed=seed,
                    n_classes=int(y_proba_fit.shape[1]) if y_proba_fit is not None else None,
                    meta_model=meta_model_key,
                )
                metrics_holdout = {primary_metric: cv_score}
                best_score = cv_score
                primary_metric_source = "meta_cv_on_valid"
                meta_training_protocol["used_test_split"] = False
                meta_training_protocol["cv_scores"] = cv_scores
                n_classes = int(y_proba_fit.shape[1]) if y_proba_fit is not None else None
                y_pred = y_pred_fit
                y_proba = y_proba_fit
            if best_score is None:
                raise ValueError("primary_metric missing for stacking.")
        except Exception as exc:
            degraded_reason = str(exc)
            if len(included_preds) <= 1:
                degraded_to = "top1"
                y_pred = included_preds[0][1]
                y_proba = included_preds[0][2]
                if task_type == "classification" and y_proba is not None:
                    n_classes = int(np.asarray(y_proba).shape[1])
                else:
                    n_classes = None
                fallback_weights = np.zeros(len(included_preds))
                fallback_weights[0] = 1.0
            else:
                degraded_to = "mean_topk"
                if task_type == "classification":
                    proba_stack = np.stack(
                        [preds[2] for preds in included_preds if preds[2] is not None], axis=0
                    )
                    if proba_stack.size == 0:
                        raise ValueError("classification ensemble requires predicted probabilities.")
                    y_proba = proba_stack.mean(axis=0)
                    if y_proba.ndim != 2:
                        raise ValueError("ensemble probabilities are invalid.")
                    y_pred = y_proba.argmax(axis=1)
                    n_classes = int(y_proba.shape[1])
                else:
                    pred_stack = np.stack([preds[1] for preds in included_preds], axis=0)
                    y_pred = pred_stack.mean(axis=0)
                    y_proba = None
                    n_classes = None
            primary_metric_source = f"fallback_{degraded_to}_on_valid"
            meta_training_protocol = meta_training_protocol or {}
            meta_training_protocol["degraded_reason"] = degraded_reason
            metrics_holdout = _compute_metrics(
                cfg,
                task_type=task_type,
                y_true=y_true,
                y_pred=y_pred,
                y_proba=y_proba,
                n_classes=n_classes,
                primary_metric=primary_metric,
            )
            best_score = metrics_holdout.get(primary_metric)

    if metrics_holdout is None:
        metrics_holdout = _compute_metrics(
            cfg,
            task_type=task_type,
            y_true=y_true,
            y_pred=y_pred,
            y_proba=y_proba,
            n_classes=n_classes,
            primary_metric=primary_metric,
        )
        best_score = metrics_holdout.get(primary_metric)
    if best_score is None:
        raise ValueError(f"primary_metric '{primary_metric}' is missing from ensemble metrics.")

    metrics_payload: dict[str, Any] = {
        "primary_metric": primary_metric,
        "direction": direction,
        "task_type": task_type,
        "holdout": {
            **metrics_holdout,
            "train_rows": int(train_rows),
            "val_rows": int(eval_rows),
        },
    }
    if method == "stacking":
        metrics_payload["primary_metric_source"] = primary_metric_source
        if fit_score_on_valid is not None:
            metrics_payload["fit_score_on_valid"] = fit_score_on_valid
    if n_classes is not None:
        metrics_payload["n_classes"] = n_classes
    metrics_path = ctx.output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    ensemble_spec = {
        "method": method,
        "selection_metric": selection_metric,
        "direction": selection_direction,
        "top_k": len(included),
        "preprocess_variant": preprocess_variant,
        "included": included,
        "skipped": skipped,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_version": versions.get("code_version", "unknown"),
        "schema_version": versions.get("schema_version", "unknown"),
    }
    if method == "weighted":
        ensemble_spec.update(
            {
                "weights": weights_map,
                "search": search_used,
                "n_samples": n_samples,
                "seed": seed,
                "objective_metric": objective_metric,
                "objective_direction": objective_direction,
                "top_k_max": top_k_max,
            }
        )
        if degraded_to:
            ensemble_spec["degraded_to"] = degraded_to
        if search_requested and search_requested != search_used:
            ensemble_spec["search_requested"] = search_requested
    if method == "stacking":
        if meta_model_info is not None:
            ensemble_spec["meta_model"] = meta_model_info
        ensemble_spec["primary_metric"] = primary_metric
        ensemble_spec["primary_metric_source"] = primary_metric_source
        if meta_training_protocol is not None:
            ensemble_spec["meta_training_protocol"] = meta_training_protocol
        if fit_score_on_valid is not None:
            ensemble_spec["fit_score_on_valid"] = fit_score_on_valid
        if degraded_to:
            ensemble_spec["degraded_to"] = degraded_to
        if degraded_reason:
            ensemble_spec["degraded_reason"] = degraded_reason
    ensemble_spec_path = ctx.output_dir / "ensemble_spec.json"
    ensemble_spec_path.write_text(
        json.dumps(ensemble_spec, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if method == "stacking" and meta_model is not None:
        meta_model_path = ctx.output_dir / "meta_model.joblib"
        save_bundle(meta_model_path, meta_model)

    preprocess_bundle = None
    label_encoder = None
    if candidates_sorted and candidates_sorted[0].model_bundle_path is not None:
        try:
            bundle = load_bundle(candidates_sorted[0].model_bundle_path)
        except Exception:
            bundle = {}
        if isinstance(bundle, dict):
            preprocess_bundle = bundle.get("preprocess_bundle")
            label_encoder = bundle.get("label_encoder")
    if not isinstance(preprocess_bundle, dict):
        preprocess_bundle = {}
    class_labels = ref_classes if task_type == "classification" else None

    ensemble_payload = {
        "method": method,
        "top_k": len(included),
        "selection_metric": selection_metric,
        "direction": selection_direction,
        "base_models": base_models,
    }
    if method == "weighted" and weights is not None:
        ensemble_payload["weights"] = [float(w) for w in np.asarray(weights).reshape(-1)]
        ensemble_payload["objective_metric"] = objective_metric
        ensemble_payload["objective_direction"] = objective_direction
    if method == "stacking":
        if meta_model_info is not None:
            ensemble_payload["meta_model"] = meta_model_info
        ensemble_payload["primary_metric_source"] = primary_metric_source
        if degraded_to:
            ensemble_payload["fallback_method"] = degraded_to
        if fallback_weights is not None:
            ensemble_payload["weights"] = [float(w) for w in np.asarray(fallback_weights).reshape(-1)]
    model_bundle = {
        "model": meta_model if method == "stacking" and meta_model is not None else None,
        "model_variant": f"ensemble_{method}",
        "primary_metric": primary_metric,
        "best_score": best_score,
        "metrics": metrics_payload,
        "preprocess_bundle": preprocess_bundle,
        "processed_dataset_id": ref_processed_dataset_id,
        "split_hash": ref_split_hash,
        "recipe_hash": ref_recipe_hash,
        "task_type": task_type,
        "class_labels": class_labels,
        "n_classes": n_classes,
        "label_encoder": label_encoder,
        "ensemble": ensemble_payload,
        "uncertainty": {"enabled": False, "method": None, "alpha": None, "q": None},
        "provenance": {
            "train_task_id": _normalize_str(getattr(ctx.task, "id", None)),
            "processed_dataset_id": ref_processed_dataset_id,
            "split_hash": ref_split_hash,
            "recipe_hash": ref_recipe_hash,
            "preprocess_variant": preprocess_variant,
        },
    }
    model_bundle_path = ctx.output_dir / "model_bundle.joblib"
    save_bundle(model_bundle_path, model_bundle)

    if clearml_enabled:
        upload_artifact(ctx, "metrics.json", metrics_path)
        upload_artifact(ctx, "ensemble_spec.json", ensemble_spec_path)
        upload_artifact(ctx, "model_bundle.joblib", model_bundle_path)
        if meta_model_path is not None:
            upload_artifact(ctx, "meta_model.joblib", meta_model_path)
        if scalars_enabled(cfg):
            for name, value in metrics_holdout.items():
                series_name = name
                if method == "stacking" and name == primary_metric:
                    series_name = f"{name} ({primary_metric_source})"
                report_scalar(ctx.task, "metrics", series_name, value, iteration=0, cfg=cfg)
            if best_score is not None:
                report_scalar(ctx.task, "ensemble", "best_score", best_score, iteration=0, cfg=cfg)
            if method == "stacking":
                report_scalar(
                    ctx.task,
                    "ensemble",
                    "primary_metric_source",
                    _primary_metric_source_code(primary_metric_source),
                    iteration=0,
                    cfg=cfg,
                )
            report_scalar(
                ctx.task,
                "ensemble",
                "n_included",
                len(included),
                iteration=0,
                cfg=cfg,
            )
            report_scalar(
                ctx.task,
                "ensemble",
                "n_skipped",
                len(skipped),
                iteration=0,
                cfg=cfg,
            )
        if tables_enabled(cfg):
            report_table(
                ctx.task,
                "ensemble",
                "included_models",
                included,
                iteration=0,
                cfg=cfg,
                output_path=ctx.output_dir / "included_models.png",
            )
            if method == "weighted" and weight_rows:
                report_table(
                    ctx.task,
                    "ensemble",
                    "weights",
                    weight_rows,
                    iteration=0,
                    cfg=cfg,
                    output_path=ctx.output_dir / "weights.png",
                )
            if method == "stacking" and meta_coeff_rows:
                report_table(
                    ctx.task,
                    "ensemble",
                    "meta_coefficients",
                    meta_coeff_rows,
                    iteration=0,
                    cfg=cfg,
                    output_path=ctx.output_dir / "meta_coefficients.png",
                )
            report_table(
                ctx.task,
                "ensemble",
                "skipped_reasons",
                _summarize_skips(skipped),
                iteration=0,
                cfg=cfg,
                output_path=ctx.output_dir / "skipped_reasons.png",
            )
        update_task_properties(
            ctx,
            {
                "processed_dataset_id": ref_processed_dataset_id,
                "split_hash": ref_split_hash,
                "model_id": str(model_bundle_path),
                "primary_metric": primary_metric,
                "best_score": best_score,
                "task_type": task_type,
                "n_classes": n_classes,
            },
        )

    out = {
        "model_id": str(model_bundle_path),
        "train_task_id": _normalize_str(getattr(ctx.task, "id", None)),
        "best_score": best_score,
        "primary_metric": primary_metric,
        "processed_dataset_id": ref_processed_dataset_id,
        "split_hash": ref_split_hash,
        "recipe_hash": ref_recipe_hash,
        "task_type": task_type,
    }
    if n_classes is not None:
        out["n_classes"] = n_classes
    if class_labels is not None:
        out["class_labels"] = class_labels
    write_out_json(ctx, out)

    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "train_ensemble",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "preprocess_variant": preprocess_variant,
            "method": method,
            "top_k": len(included),
            "selection_metric": selection_metric,
            "primary_metric": primary_metric,
            "direction": direction,
        },
        "outputs": {
            "model_id": str(model_bundle_path),
            "best_score": best_score,
            "primary_metric": primary_metric,
            "task_type": task_type,
        },
        "hashes": _resolve_manifest_hashes(
            cfg, split_hash=ref_split_hash, recipe_hash=ref_recipe_hash
        ),
    }
    write_manifest(ctx, manifest)


def _rerun_predictions(
    cfg: Any,
    candidate: _Candidate,
    *,
    preprocess_variant: str,
    split_key: str = "val",
) -> tuple[Any, Any, Any | None]:
    if candidate.model_bundle_path is None:
        raise ValueError("model_bundle is required for fallback predictions.")
    bundle = load_bundle(candidate.model_bundle_path)
    if not isinstance(bundle, dict):
        raise ValueError("model_bundle is invalid.")
    model = bundle.get("calibrated_model") or bundle.get("model")
    preprocess_bundle = bundle.get("preprocess_bundle") or {}
    label_encoder = bundle.get("label_encoder")
    task_type = _normalize_task_type(bundle.get("task_type"))
    if model is None or not isinstance(preprocess_bundle, dict):
        raise ValueError("model_bundle missing model or preprocess_bundle.")

    processed_dataset_id = _normalize_str(bundle.get("processed_dataset_id")) or candidate.processed_dataset_id
    base_dir = _resolve_processed_dataset_dir(cfg, processed_dataset_id, candidate.run_dir)
    split_path = _resolve_split_path(base_dir)
    split_payload = _load_json(split_path)
    split_idx = _extract_split_indices(split_payload, split_key)
    if not split_idx:
        raise ValueError(f"{split_key}_index missing in split.json.")
    try:
        split_idx = list(split_idx)
    except Exception as exc:
        raise ValueError(f"{split_key}_index is invalid.") from exc

    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for fallback predictions.") from exc

    columns_info = preprocess_bundle.get("columns") or {}
    target_column = _normalize_str(columns_info.get("target_column")) or _normalize_str(
        bundle.get("target_column")
    )
    processed_path = _resolve_artifact_path(base_dir, "processed_dataset.parquet")
    x_path = _resolve_artifact_path(base_dir, "X.parquet")
    y_path = _resolve_artifact_path(base_dir, "y.parquet")
    if processed_path is None and (x_path is None or y_path is None):
        raise ValueError("processed dataset is missing for fallback predictions.")
    feature_names = preprocess_bundle.get("feature_names")
    if processed_path is not None:
        df = pd.read_parquet(processed_path)
        if not target_column or target_column not in df.columns:
            raise ValueError("target_column missing in processed dataset.")
        if not feature_names:
            feature_names = [col for col in df.columns if col != target_column]
        X_val = df.iloc[split_idx][feature_names]
        y_val = df.iloc[split_idx][target_column].to_numpy()
    else:
        X_df = pd.read_parquet(x_path)
        y_df = pd.read_parquet(y_path)
        if feature_names and all(name in X_df.columns for name in feature_names):
            X_df = X_df[feature_names]
        X_val = X_df.iloc[split_idx]
        y_val = y_df.iloc[split_idx].to_numpy().reshape(-1)
    if task_type == "classification" and label_encoder is not None:
        try:
            y_val = label_encoder.transform(y_val)
        except Exception as exc:
            raise ValueError("label encoding failed for fallback predictions.") from exc
    y_pred = model.predict(X_val)
    y_proba = None
    if task_type == "classification":
        if not hasattr(model, "predict_proba"):
            raise ValueError("predict_proba is required for classification fallback.")
        y_proba = model.predict_proba(X_val)
    return y_val, y_pred, y_proba
