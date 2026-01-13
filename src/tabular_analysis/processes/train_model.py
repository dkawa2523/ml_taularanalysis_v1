"""train_model process.

- processed dataset + fixed split を入力
- model_variant を選択して学習
- model_bundle（model + preprocess bundle + schema）を保存
- primary_metric を計算し、properties に best_score を入れる
"""

from __future__ import annotations

from datetime import datetime, timezone
import importlib
import inspect
import json
import math
from pathlib import Path
from typing import Any
import warnings

from ..clearml.datasets import get_processed_dataset_local_copy, get_raw_dataset_local_copy
from ..clearml.naming import apply_train_model_naming
from ..clearml.reporting import (
    plots_enabled,
    report_plotly,
    report_scalar,
    report_table,
    scalars_enabled,
    tables_enabled,
)
from ..clearml.ui_logger import log_debug_table
from ..feature_engineering.categorical import encode_target_for_mean
from ..io.bundle_io import load_bundle, save_bundle
from ..metrics.regression import REGRESSION_METRIC_ORDER, compute_regression_metrics
from ..monitoring.drift import build_train_profile
from .drift_report import annotate_profile, resolve_drift_settings, sample_frame
from ..ops.clearml_identity import apply_clearml_identity
from ..platform_adapter import (
    hash_config,
    emit_skip,
    init_task_context,
    is_clearml_enabled,
    resolve_output_dir,
    resolve_version_props,
    save_config_resolved,
    update_task_properties,
    upload_artifact,
    write_manifest,
    write_out_json,
)
from ..registry.metrics import (
    get_metric,
    metric_direction,
    metric_requires_proba,
    metric_supports_thresholding,
)
from ..registry import list_model_variants
from ..registry.models import MissingOptionalDependencyError, ModelWeightsUnavailableError, build_model
from ..uncertainty.conformal import compute_split_conformal_quantile
from ..viz.plots import (
    plot_confusion_matrix,
    plot_feature_importance,
    plot_interval_width_histogram,
    plot_reliability_curve,
    plot_regression_residuals,
    plot_true_pred_scatter,
    plot_roc_curve,
    write_confusion_matrix_csv,
)
from ..viz.regression_plots import (
    build_regression_metrics_table,
    build_residuals_plot,
    build_true_pred_scatter,
)

_TABULAR_SUFFIXES = (".csv", ".parquet", ".pq")
_DEFAULT_THRESHOLD_GRID = [i / 100 for i in range(5, 100, 5)]


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
        if isinstance(current, dict):
            if key not in current:
                return default
            current = current[key]
        else:
            if not hasattr(current, key):
                return default
            current = getattr(current, key)
    return default if current is None else current


def _ensure_str_list(values: Any) -> list[str]:
    container = _to_container(values)
    if container is None:
        return []
    if isinstance(container, (list, tuple, set)):
        return [str(v) for v in container if v is not None]
    return [str(container)]


def _resolve_classification_mode(cfg: Any, *, n_classes: int) -> str:
    mode = _normalize_str(_cfg_value(cfg, "eval.classification.mode", "auto")) or "auto"
    mode = mode.lower()
    if mode not in ("auto", "binary", "multiclass"):
        raise ValueError("eval.classification.mode must be auto, binary, or multiclass.")
    if mode == "auto":
        return "binary" if n_classes == 2 else "multiclass"
    if mode == "binary" and n_classes != 2:
        raise ValueError("eval.classification.mode=binary requires exactly 2 classes.")
    if mode == "multiclass" and n_classes < 3:
        raise ValueError("eval.classification.mode=multiclass requires at least 3 classes.")
    return mode


def _resolve_classification_metrics(
    cfg: Any,
    *,
    classification_mode: str,
    n_classes: int | None,
    imbalance_enabled: bool,
) -> list[str]:
    metrics: list[str] = []
    if classification_mode == "multiclass":
        metrics = _ensure_str_list(_cfg_value(cfg, "eval.metrics.classification_multiclass", None))
        if not metrics:
            metrics = ["accuracy", "f1_macro", "logloss"]
    else:
        metrics = _ensure_str_list(_cfg_value(cfg, "eval.metrics.classification_binary", None))
        if not metrics:
            metrics = ["accuracy", "f1", "log_loss"]
            if n_classes == 2:
                metrics.append("roc_auc")
    if imbalance_enabled:
        extra = _ensure_str_list(_cfg_value(cfg, "eval.metrics.classification_imbalance", None))
        if extra:
            metrics.extend(extra)
    seen: set[str] = set()
    ordered: list[str] = []
    for name in metrics:
        key = _normalize_str(name)
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def _resolve_regression_metrics(cfg: Any) -> list[str]:
    metrics = list(REGRESSION_METRIC_ORDER)
    extras = _ensure_str_list(_cfg_value(cfg, "eval.metrics.regression", None))
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


def _resolve_eval_context(cfg: Any, *, task_type: str) -> tuple[str, str, int, int]:
    primary_metric = (
        _normalize_str(getattr(getattr(cfg, "eval", None), "primary_metric", None)) or "rmse"
    ).lower()
    direction = _normalize_str(getattr(getattr(cfg, "eval", None), "direction", None))
    if not direction or direction == "auto":
        direction = metric_direction(primary_metric, task_type)
    direction = direction.lower()
    cv_folds = int(getattr(getattr(cfg, "eval", None), "cv_folds", 0) or 0)
    cv_seed = int(getattr(getattr(cfg, "eval", None), "seed", 42) or 42)
    return primary_metric, direction, cv_folds, cv_seed


def _resolve_viz_settings(cfg: Any) -> dict[str, Any]:
    enabled = bool(_cfg_value(cfg, "viz.enabled", True))
    heavy_enabled = bool(_cfg_value(cfg, "viz.heavy.enabled", False))
    try:
        max_features = int(_cfg_value(cfg, "viz.max_features", 20))
    except Exception:
        max_features = 20
    try:
        max_points = int(_cfg_value(cfg, "viz.max_points", 1000))
    except Exception:
        max_points = 1000
    confusion_normalize = bool(_cfg_value(cfg, "viz.confusion_normalize", True))
    roc_curve = bool(_cfg_value(cfg, "viz.roc_curve", True))
    return {
        "enabled": enabled,
        "heavy_enabled": heavy_enabled,
        "max_features": max_features,
        "max_points": max_points,
        "confusion_normalize": confusion_normalize,
        "roc_curve": roc_curve,
    }


def _normalize_threshold_grid(values: Any) -> list[float]:
    container = _to_container(values)
    if container is None:
        return []
    if isinstance(container, (list, tuple, set)):
        raw_values = list(container)
    else:
        raw_values = [container]
    grid: list[float] = []
    for value in raw_values:
        try:
            num = float(value)
        except Exception:
            continue
        if not math.isfinite(num):
            continue
        if num < 0.0 or num > 1.0:
            continue
        grid.append(float(num))
    if not grid:
        return []
    return sorted(set(grid))


def _resolve_thresholding_settings(cfg: Any) -> dict[str, Any]:
    enabled = bool(_cfg_value(cfg, "eval.thresholding.enabled", False))
    metric = _normalize_str(_cfg_value(cfg, "eval.thresholding.metric", "f1")) or "f1"
    grid: list[float] = []
    if enabled:
        raw_grid = _cfg_value(cfg, "eval.thresholding.grid", None)
        grid = _normalize_threshold_grid(raw_grid)
        if not grid and raw_grid is None:
            grid = list(_DEFAULT_THRESHOLD_GRID)
        if not grid:
            raise ValueError("eval.thresholding.grid must include values between 0 and 1.")
    return {"enabled": enabled, "metric": metric, "grid": grid}


def _resolve_calibration_settings(cfg: Any) -> dict[str, Any]:
    enabled = bool(_cfg_value(cfg, "eval.calibration.enabled", False))
    method = _normalize_str(_cfg_value(cfg, "eval.calibration.method", "sigmoid")) or "sigmoid"
    mode = _normalize_str(_cfg_value(cfg, "eval.calibration.mode", "prefit")) or "prefit"
    method = method.lower()
    mode = mode.lower()
    if enabled:
        if method not in ("sigmoid", "isotonic"):
            raise ValueError("eval.calibration.method must be 'sigmoid' or 'isotonic'.")
        if mode not in ("prefit",):
            raise ValueError("eval.calibration.mode must be 'prefit'.")
    return {"enabled": enabled, "method": method, "mode": mode}


def _resolve_uncertainty_settings(cfg: Any) -> dict[str, Any]:
    enabled = bool(_cfg_value(cfg, "eval.uncertainty.enabled", False))
    method = _normalize_str(_cfg_value(cfg, "eval.uncertainty.method", "conformal_split")) or "conformal_split"
    method = method.lower()
    try:
        alpha = float(_cfg_value(cfg, "eval.uncertainty.alpha", 0.1))
    except Exception:
        alpha = 0.1
    use_abs_residual = bool(_cfg_value(cfg, "eval.uncertainty.use_abs_residual", True))
    if enabled:
        if method not in ("conformal_split",):
            raise ValueError("eval.uncertainty.method must be 'conformal_split'.")
        if not (0.0 < alpha < 1.0):
            raise ValueError("eval.uncertainty.alpha must be between 0 and 1.")
    return {
        "enabled": enabled,
        "method": method,
        "alpha": alpha,
        "use_abs_residual": use_abs_residual,
    }


def _resolve_ci_settings(cfg: Any) -> dict[str, Any]:
    enabled = bool(_cfg_value(cfg, "eval.ci.enabled", False))
    try:
        n_boot = int(_cfg_value(cfg, "eval.ci.n_boot", 200))
    except Exception:
        n_boot = 200
    try:
        alpha = float(_cfg_value(cfg, "eval.ci.alpha", 0.05))
    except Exception:
        alpha = 0.05
    try:
        seed = int(_cfg_value(cfg, "eval.ci.seed", 0))
    except Exception:
        seed = 0
    if enabled:
        if n_boot <= 0:
            raise ValueError("eval.ci.n_boot must be > 0.")
        if not (0.0 < alpha < 1.0):
            raise ValueError("eval.ci.alpha must be between 0 and 1.")
    return {
        "enabled": enabled,
        "n_boot": n_boot,
        "alpha": alpha,
        "seed": seed,
    }


def _normalize_class_weight(value: Any) -> Any | None:
    if value is None:
        return None
    if isinstance(value, str):
        key = value.strip().lower()
        if key in ("", "none", "null"):
            return None
        if key == "balanced":
            return "balanced"
    return value


def _resolve_imbalance_settings(cfg: Any) -> dict[str, Any]:
    enabled = bool(_cfg_value(cfg, "eval.imbalance.enabled", False))
    strategy = _normalize_key(_cfg_value(cfg, "eval.imbalance.strategy", "class_weight"))
    class_weight = _normalize_class_weight(_cfg_value(cfg, "eval.imbalance.class_weight", None))
    pos_weight = _cfg_value(cfg, "eval.imbalance.pos_weight", None)
    if enabled and strategy not in ("class_weight", "pos_weight", "oversample", "undersample"):
        raise ValueError(
            "eval.imbalance.strategy must be class_weight, pos_weight, oversample, or undersample."
        )
    return {
        "enabled": enabled,
        "strategy": strategy,
        "class_weight": class_weight,
        "pos_weight": pos_weight,
    }


def _resolve_model_class_path(model_variant: dict[str, Any], *, task_type: str | None) -> str | None:
    class_path = model_variant.get("class_path")
    if isinstance(class_path, dict) and task_type:
        class_path = class_path.get(task_type)
    return class_path if isinstance(class_path, str) else None


def _supports_param(class_path: str, param: str) -> tuple[bool, str | None]:
    try:
        module_name, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
    except Exception:
        return False, "dependency_unavailable"
    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        return False, "signature_unavailable"
    if param in sig.parameters:
        return True, None
    for value in sig.parameters.values():
        if value.kind == inspect.Parameter.VAR_KEYWORD:
            return True, None
    return False, "param_not_supported"


def _compute_balanced_class_weights(y_train: Any, *, n_classes: int) -> list[float]:
    try:
        import numpy as np  # type: ignore
        from sklearn.utils.class_weight import compute_class_weight  # type: ignore
    except Exception as exc:
        raise RuntimeError("scikit-learn is required for class_weight balancing.") from exc
    classes = np.arange(n_classes)
    weights = compute_class_weight(class_weight="balanced", classes=classes, y=y_train)
    return [float(weight) for weight in weights.tolist()]


def _coerce_class_weight_list(value: Any, *, n_classes: int, y_train: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() == "balanced":
        return _compute_balanced_class_weights(y_train, n_classes=n_classes)
    if isinstance(value, (list, tuple)) and len(value) == n_classes:
        return [float(v) for v in value]
    if isinstance(value, dict):
        weights = [1.0 for _ in range(n_classes)]
        for key, weight in value.items():
            try:
                idx = int(key)
            except Exception:
                continue
            if 0 <= idx < n_classes:
                weights[idx] = float(weight)
        return weights
    return None


def _resolve_pos_weight(y_train: Any, value: Any | None = None) -> float | None:
    if value is not None:
        try:
            weight = float(value)
        except Exception:
            return None
        return weight if weight > 0 else None
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None
    counts = np.bincount(np.asarray(y_train, dtype=int), minlength=2)
    if counts.size < 2:
        return None
    neg = counts[0]
    pos = counts[1]
    if pos <= 0 or neg <= 0:
        return None
    return float(neg / pos)


def _bootstrap_metric_ci(
    y_true: Any,
    y_pred: Any,
    y_proba: Any | None,
    *,
    metric_name: str,
    task_type: str,
    n_classes: int | None,
    n_boot: int,
    alpha: float,
    seed: int,
    beta: float | None,
    point_estimate: float | None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for bootstrap confidence intervals.") from exc

    metric_fn = get_metric(metric_name, task_type, n_classes=n_classes, beta=beta)
    needs_proba = metric_requires_proba(metric_name, task_type)
    if needs_proba and y_proba is None:
        raise ValueError("primary_metric requires predicted probabilities for CI.")

    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)
    y_proba_arr = np.asarray(y_proba) if y_proba is not None else None
    n_samples = int(y_true_arr.shape[0])
    if n_samples <= 1:
        raise ValueError("bootstrap CI requires at least 2 validation samples.")

    rng = np.random.default_rng(seed)
    scores: list[float] = []
    attempts = 0
    max_attempts = max(n_boot * 10, n_boot + 50)
    while len(scores) < n_boot and attempts < max_attempts:
        attempts += 1
        sample_idx = rng.integers(0, n_samples, size=n_samples)
        y_true_sample = y_true_arr[sample_idx]
        y_pred_sample = y_pred_arr[sample_idx]
        y_proba_sample = y_proba_arr[sample_idx] if y_proba_arr is not None else None
        try:
            score = float(metric_fn(y_true_sample, y_pred_sample, y_proba_sample))
        except Exception:
            continue
        if not math.isfinite(score):
            continue
        scores.append(score)

    info = {
        "n_boot": int(n_boot),
        "n_boot_effective": int(len(scores)),
        "alpha": float(alpha),
        "seed": int(seed),
        "attempts": int(attempts),
    }
    if not scores:
        return None, info

    values = np.asarray(scores, dtype=float)
    low = float(np.quantile(values, alpha / 2.0))
    high = float(np.quantile(values, 1.0 - alpha / 2.0))
    mid = float(point_estimate) if point_estimate is not None else float(np.quantile(values, 0.5))
    interval = {"low": low, "mid": mid, "high": high}
    return interval, info


def _apply_resampling(
    strategy: str,
    X_train: Any,
    y_train: Any,
    *,
    seed: int,
) -> tuple[Any, Any, dict[str, Any] | None, str | None]:
    try:
        if strategy == "oversample":
            from imblearn.over_sampling import RandomOverSampler  # type: ignore

            sampler_cls = RandomOverSampler
        else:
            from imblearn.under_sampling import RandomUnderSampler  # type: ignore

            sampler_cls = RandomUnderSampler
    except Exception:
        return X_train, y_train, None, "optional_dependency_missing"

    try:
        sampler = sampler_cls(random_state=seed)
    except Exception:
        sampler = sampler_cls()

    X_resampled, y_resampled = sampler.fit_resample(X_train, y_train)
    info = {
        "train_rows_before": int(len(y_train)),
        "train_rows_after": int(len(y_resampled)),
    }
    return X_resampled, y_resampled, info, None


def _apply_weight_strategy(
    *,
    model_variant: dict[str, Any],
    task_type: str,
    y_train: Any,
    n_classes: int | None,
    imbalance_cfg: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    report: dict[str, Any] = {"applied": False}
    strategy = imbalance_cfg.get("strategy")
    class_path = _resolve_model_class_path(model_variant, task_type=task_type)
    if not class_path:
        report["reason"] = "missing_class_path"
        return model_variant, report

    if strategy == "class_weight":
        class_weight = imbalance_cfg.get("class_weight")
        if class_weight is None:
            report["reason"] = "class_weight_null"
            return model_variant, report
        supports, reason = _supports_param(class_path, "class_weight")
        if supports:
            model_variant["params"]["class_weight"] = class_weight
            report["applied"] = True
            report["detail"] = {"class_weight": class_weight}
            return model_variant, report

        supports, reason = _supports_param(class_path, "class_weights")
        if supports:
            if n_classes is None:
                report["reason"] = "n_classes_unknown"
                return model_variant, report
            weights = _coerce_class_weight_list(class_weight, n_classes=n_classes, y_train=y_train)
            if weights is None:
                report["reason"] = "class_weights_unresolved"
                return model_variant, report
            model_variant["params"]["class_weights"] = weights
            report["applied"] = True
            report["detail"] = {"class_weight": class_weight}
            return model_variant, report

        if reason == "dependency_unavailable":
            report["reason"] = "optional_dependency_missing"
        else:
            report["reason"] = "class_weight_not_supported"
        return model_variant, report

    if strategy == "pos_weight":
        if n_classes is not None and n_classes != 2:
            report["reason"] = "pos_weight_binary_only"
            return model_variant, report
        pos_weight = _resolve_pos_weight(y_train, imbalance_cfg.get("pos_weight"))
        if pos_weight is None:
            report["reason"] = "pos_weight_unavailable"
            return model_variant, report
        supports, reason = _supports_param(class_path, "scale_pos_weight")
        if supports:
            model_variant["params"]["scale_pos_weight"] = pos_weight
            report["applied"] = True
            report["detail"] = {"pos_weight": pos_weight}
            return model_variant, report
        if reason == "dependency_unavailable":
            report["reason"] = "optional_dependency_missing"
        else:
            report["reason"] = "pos_weight_not_supported"
        return model_variant, report

    report["reason"] = "unknown_strategy"
    return model_variant, report


def _is_binary_only_metric(name: str) -> bool:
    key = _normalize_key(name) or ""
    return key in ("roc_auc", "auc", "pr_auc", "average_precision", "average_precision_score")


def _extract_positive_proba(y_proba: Any) -> Any:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for threshold optimization.") from exc
    arr = np.asarray(y_proba)
    if arr.ndim == 1:
        return arr
    if arr.ndim == 2 and arr.shape[1] >= 2:
        return arr[:, 1]
    raise ValueError("predict_proba output must include positive-class probabilities.")


def _select_best_threshold(
    y_true: Any,
    y_proba: Any,
    *,
    metric_name: str,
    grid: list[float],
    task_type: str,
    n_classes: int | None,
    beta: float | None = None,
) -> tuple[float, float, str]:
    if not metric_supports_thresholding(metric_name, task_type):
        raise ValueError(
            f"thresholding.metric '{metric_name}' is not supported for threshold optimization."
        )
    direction = metric_direction(metric_name, task_type)
    metric_fn = get_metric(metric_name, task_type, n_classes=n_classes, beta=beta)
    positive_proba = _extract_positive_proba(y_proba)
    best_threshold: float | None = None
    best_score: float | None = None
    for threshold in grid:
        preds = (positive_proba >= threshold).astype(int)
        score = float(metric_fn(y_true, preds, y_proba))
        if best_score is None:
            best_score = score
            best_threshold = float(threshold)
            continue
        if direction == "maximize" and score > best_score:
            best_score = score
            best_threshold = float(threshold)
        elif direction == "minimize" and score < best_score:
            best_score = score
            best_threshold = float(threshold)
    if best_threshold is None or best_score is None:
        raise ValueError("Failed to select a valid threshold from eval.thresholding.grid.")
    return best_threshold, best_score, direction


def _calibrate_classifier(model: Any, X_val: Any, y_val: Any, *, method: str, mode: str) -> Any:
    try:
        from sklearn.calibration import CalibratedClassifierCV  # type: ignore
    except Exception as exc:
        raise RuntimeError("scikit-learn is required for calibration.") from exc
    if mode != "prefit":
        raise ValueError(f"Unsupported calibration mode: {mode}")
    calibrator = CalibratedClassifierCV(model, method=method, cv="prefit")
    calibrator.fit(X_val, y_val)
    return calibrator


def _prepare_calibration_samples(
    y_true: Any,
    y_proba: Any,
    *,
    n_classes: int | None,
) -> tuple[Any, Any, str]:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for calibration reports.") from exc

    y_true_arr = np.asarray(y_true).reshape(-1)
    proba_arr = np.asarray(y_proba)

    if proba_arr.ndim == 1:
        confidence = proba_arr.astype(float)
        correct = (y_true_arr == 1).astype(float)
        return confidence, correct, "binary_positive"

    if proba_arr.ndim != 2:
        raise ValueError("predict_proba output must be a 1D or 2D array.")

    if n_classes is None:
        n_classes = int(proba_arr.shape[1])

    if n_classes <= 2:
        positive = proba_arr[:, 1] if proba_arr.shape[1] >= 2 else proba_arr[:, -1]
        confidence = positive.astype(float)
        correct = (y_true_arr == 1).astype(float)
        return confidence, correct, "binary_positive"

    top_idx = np.argmax(proba_arr, axis=1)
    confidence = proba_arr[np.arange(proba_arr.shape[0]), top_idx].astype(float)
    correct = (top_idx == y_true_arr).astype(float)
    return confidence, correct, "multiclass_top1"


def _build_calibration_report(
    y_true: Any,
    y_proba: Any,
    *,
    n_classes: int | None,
    n_bins: int = 10,
) -> tuple[dict[str, Any], list[float], list[float]]:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for calibration reports.") from exc

    confidence, correct, mode = _prepare_calibration_samples(
        y_true, y_proba, n_classes=n_classes
    )
    confidence = np.clip(np.asarray(confidence, dtype=float).reshape(-1), 0.0, 1.0)
    correct = np.clip(np.asarray(correct, dtype=float).reshape(-1), 0.0, 1.0)

    if n_bins <= 0:
        n_bins = 10

    n_samples = int(confidence.shape[0])
    if n_samples == 0:
        report = {
            "n_samples": 0,
            "n_bins": int(n_bins),
            "mode": mode,
            "ece": None,
            "curve": [],
        }
        return report, [], []

    bin_indices = np.minimum((confidence * n_bins).astype(int), n_bins - 1)
    counts = np.bincount(bin_indices, minlength=n_bins)
    sum_conf = np.bincount(bin_indices, weights=confidence, minlength=n_bins)
    sum_acc = np.bincount(bin_indices, weights=correct, minlength=n_bins)
    mean_conf = np.divide(
        sum_conf, counts, out=np.zeros_like(sum_conf, dtype=float), where=counts > 0
    )
    mean_acc = np.divide(
        sum_acc, counts, out=np.zeros_like(sum_acc, dtype=float), where=counts > 0
    )

    weights = counts / max(n_samples, 1)
    ece = float(np.sum(weights * np.abs(mean_acc - mean_conf)))
    curve = []
    curve_conf: list[float] = []
    curve_acc: list[float] = []
    for idx in range(n_bins):
        if counts[idx] <= 0:
            continue
        curve.append(
            {
                "bin": int(idx),
                "count": int(counts[idx]),
                "mean_confidence": float(mean_conf[idx]),
                "mean_accuracy": float(mean_acc[idx]),
            }
        )
        curve_conf.append(float(mean_conf[idx]))
        curve_acc.append(float(mean_acc[idx]))

    report = {
        "n_samples": n_samples,
        "n_bins": int(n_bins),
        "mode": mode,
        "ece": ece,
        "curve": curve,
    }
    return report, curve_conf, curve_acc


def _to_container(value: Any) -> Any:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(value):
        return OmegaConf.to_container(value, resolve=True)
    return value


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_preprocess_provenance(
    preprocess_run_dir: Path,
    assets_dir: Path | None,
    preprocess_out: dict[str, Any] | None,
    preprocess_bundle: Any,
) -> dict[str, Any]:
    raw_dataset_id = None
    preprocess_variant = None
    if isinstance(preprocess_out, dict):
        preprocess_variant = _normalize_str(preprocess_out.get("preprocess_variant"))
    if preprocess_variant is None and isinstance(preprocess_bundle, dict):
        preprocess_variant = _normalize_str(preprocess_bundle.get("preprocess_variant"))

    for candidate in (assets_dir, preprocess_run_dir):
        if candidate is None:
            continue
        meta_path = candidate / "meta.json"
        if not meta_path.exists():
            continue
        meta_payload = _load_json(meta_path)
        if raw_dataset_id is None:
            raw_dataset_id = _normalize_str(meta_payload.get("raw_dataset_id"))
        if preprocess_variant is None:
            preprocess_variant = _normalize_str(meta_payload.get("preprocess_variant"))
        break

    manifest_path = preprocess_run_dir / "manifest.json"
    if manifest_path.exists():
        manifest_payload = _load_json(manifest_path)
        inputs = manifest_payload.get("inputs") or {}
        if raw_dataset_id is None:
            raw_dataset_id = _normalize_str(inputs.get("raw_dataset_id"))

    return {
        "raw_dataset_id": raw_dataset_id,
        "preprocess_variant": preprocess_variant,
    }


def _stringify_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _stringify_payload(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_stringify_payload(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _format_float(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        num = float(value)
    except Exception:
        return "n/a"
    if not math.isfinite(num):
        return "n/a"
    return f"{num:.6g}"


def _format_ci_interval(ci_payload: dict[str, Any] | None) -> str | None:
    if not isinstance(ci_payload, dict):
        return None
    interval = ci_payload.get("primary_metric")
    if not isinstance(interval, dict):
        return None
    low = interval.get("low")
    mid = interval.get("mid")
    high = interval.get("high")
    if low is None and mid is None and high is None:
        return None
    return f"[{_format_float(low)}, {_format_float(mid)}, {_format_float(high)}]"


def _format_encoding_note(recipe_payload: dict[str, Any]) -> str | None:
    if not isinstance(recipe_payload, dict):
        return None
    enc = recipe_payload.get("categorical_encoding")
    if not isinstance(enc, dict):
        return None
    encoding = _normalize_str(enc.get("encoding"))
    if not encoding:
        return None
    if encoding == "auto":
        max_cats = enc.get("auto_onehot_max_categories")
        hash_cfg = enc.get("hashing") or {}
        hash_n = hash_cfg.get("n_features") if isinstance(hash_cfg, dict) else None
        return f"auto(onehot_max={max_cats}, hash_n_features={hash_n})"
    if encoding == "hashing":
        hash_cfg = enc.get("hashing") or {}
        hash_n = hash_cfg.get("n_features") if isinstance(hash_cfg, dict) else None
        return f"hashing(n_features={hash_n})"
    if encoding == "target_mean_oof":
        oof_cfg = enc.get("target_mean_oof") or {}
        folds = oof_cfg.get("folds") if isinstance(oof_cfg, dict) else None
        smoothing = oof_cfg.get("smoothing") if isinstance(oof_cfg, dict) else None
        return f"target_mean_oof(folds={folds}, smoothing={smoothing})"
    return encoding


def _summarize_metrics(metrics: dict[str, float], primary_metric: str, *, max_items: int = 4) -> str | None:
    if not metrics:
        return None
    items = [(k, v) for k, v in metrics.items() if k != primary_metric]
    if not items:
        return None
    items.sort(key=lambda item: item[0])
    trimmed = items[:max_items]
    summary = ", ".join(f"{name}={_format_float(value)}" for name, value in trimmed)
    if len(items) > max_items:
        summary += f" (+{len(items) - max_items} more)"
    return summary


def _load_dataframe(path: Path):
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for train_model.") from exc
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported dataset format: {path.suffix}")


def _select_tabular_file(path: Path) -> Path:
    if path.is_file():
        return path
    if path.is_dir():
        candidates = sorted([p for p in path.rglob("*") if p.suffix.lower() in _TABULAR_SUFFIXES])
        if candidates:
            return candidates[0]
        raise ValueError(f"No CSV/Parquet files found under: {path}")
    raise FileNotFoundError(str(path))


def _find_latest_preprocess_dir(search_root: Path) -> Path | None:
    if not search_root.exists():
        return None
    candidates: list[Path] = []
    for path in search_root.glob("*/02_preprocess/out.json"):
        candidates.append(path.parent)
    if not candidates:
        return None
    try:
        return max(candidates, key=lambda item: item.stat().st_mtime)
    except Exception:
        return candidates[-1]


def _resolve_preprocess_run_dir(cfg: Any, processed_ref_path: Path | None) -> Path:
    candidate: str | None = None
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None:
        for key in (
            "train.inputs.preprocess_run_dir",
            "train.preprocess_run_dir",
            "inputs.preprocess_run_dir",
        ):
            value = OmegaConf.select(cfg, key)
            if value:
                candidate = str(value)
                break
    if candidate:
        return Path(candidate).expanduser().resolve()
    if processed_ref_path is not None:
        if processed_ref_path.is_dir():
            return processed_ref_path
        if processed_ref_path.is_file():
            return processed_ref_path.parent
    run_cfg = getattr(cfg, "run", None)
    base_output_dir = Path(getattr(run_cfg, "output_dir", "outputs"))
    candidates = [base_output_dir / "02_preprocess"]
    name = base_output_dir.name
    if len(name) >= 3 and name[:2].isdigit() and name[2] == "_":
        parent = base_output_dir.parent
        candidates.append(parent / "02_preprocess")
        candidates.append(parent / "02_preprocess" / "02_preprocess")
    for candidate in candidates:
        if (candidate / "out.json").exists():
            return candidate
    for candidate in candidates:
        if candidate.exists():
            return candidate
    latest = _find_latest_preprocess_dir(base_output_dir.parent)
    if latest is not None:
        return latest
    return resolve_output_dir(cfg, "02_preprocess")


def _resolve_split_path(base_dir: Path) -> Path:
    for name in ("splits.json", "split.json"):
        candidate = base_dir / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"split(s).json not found under: {base_dir}")


def _load_feature_names(base_dir: Path) -> list[str] | None:
    path = base_dir / "feature_names.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [str(value) for value in payload]
    return None


def _load_processed_from_xy(base_dir: Path):
    x_path = base_dir / "X.parquet"
    y_path = base_dir / "y.parquet"
    if not (x_path.exists() and y_path.exists()):
        return None, None
    df_x = _load_dataframe(x_path)
    df_y = _load_dataframe(y_path)
    if getattr(df_y, "shape", (0, 0))[1] != 1:
        raise ValueError("y.parquet must contain exactly one column.")
    target_column = str(df_y.columns[0])
    df = df_x.copy()
    df[target_column] = df_y.iloc[:, 0].to_numpy()
    return df, target_column


def _rebuild_processed_from_raw(
    cfg: Any,
    *,
    base_dir: Path,
    preprocess_bundle: dict[str, Any],
    split_payload: dict[str, Any],
    task_type: str,
) -> tuple[Any, str]:
    meta_path = base_dir / "meta.json"
    meta = _load_json(meta_path) if meta_path.exists() else {}
    raw_dataset_id = _normalize_str(meta.get("raw_dataset_id")) or _normalize_str(
        _cfg_value(cfg, "data.raw_dataset_id")
    )
    dataset_path_value = _normalize_str(_cfg_value(cfg, "data.dataset_path"))
    if raw_dataset_id and not raw_dataset_id.startswith("local:"):
        raw_dir = get_raw_dataset_local_copy(cfg, raw_dataset_id)
        dataset_file = _select_tabular_file(raw_dir)
    elif dataset_path_value:
        dataset_file = _select_tabular_file(Path(dataset_path_value).expanduser().resolve())
    else:
        raise FileNotFoundError(
            "raw dataset not available; set data.dataset_path or provide raw_dataset_id in meta.json."
        )

    raw_df = _load_dataframe(dataset_file)
    columns_info = preprocess_bundle.get("columns") or {}
    feature_columns = columns_info.get("feature_columns") or []
    target_column = _normalize_str(columns_info.get("target_column")) or _normalize_str(
        _cfg_value(cfg, "data.target_column")
    )
    if not target_column or target_column not in raw_df.columns:
        raise ValueError("target_column not found in raw dataset for rebuild.")
    if not feature_columns:
        raise ValueError("feature_columns missing in preprocess_bundle; cannot rebuild features.")

    pipeline = preprocess_bundle.get("pipeline")
    if pipeline is None:
        raise ValueError("preprocess_bundle.pipeline is missing.")

    recipe_path = base_dir / "recipe.json"
    recipe_payload = _load_json(recipe_path) if recipe_path.exists() else {}
    encoding_cfg = recipe_payload.get("categorical_encoding") or {}
    encoding = _normalize_str(encoding_cfg.get("encoding"))
    target_mean_cfg = encoding_cfg.get("target_mean_oof") or {}
    target_mean_folds = int(target_mean_cfg.get("folds") or 5)
    split_seed = int(split_payload.get("seed") or _cfg_value(cfg, "data.split.seed", 42) or 42)
    train_idx = _normalize_indices(split_payload.get("train_index"), label="train_index")

    if encoding == "target_mean_oof":
        y_encoded, _ = encode_target_for_mean(
            train_values=raw_df.iloc[train_idx][target_column],
            all_values=raw_df[target_column],
            task_type=task_type,
        )
        transformed = pipeline.transform_with_oof(
            raw_df[feature_columns],
            y_encoded,
            train_idx=train_idx,
            folds=target_mean_folds,
            seed=split_seed,
            task_type=task_type,
        )
    else:
        transformed = pipeline.transform(raw_df[feature_columns])
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()

    feature_names = preprocess_bundle.get("feature_names")
    if not feature_names:
        try:
            feature_names = list(pipeline.get_feature_names_out())
        except Exception:
            feature_names = [f"f{i}" for i in range(int(getattr(transformed, "shape", [0, 0])[1]))]

    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for rebuild.") from exc
    processed_df = pd.DataFrame(transformed, columns=feature_names)
    processed_df[target_column] = raw_df[target_column].to_numpy()
    return processed_df, target_column


def _ensure_variant_cfg(cfg: Any) -> None:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        return
    if not OmegaConf.is_config(cfg):
        return
    if OmegaConf.select(cfg, "model_variant") is not None:
        return
    source = OmegaConf.select(cfg, "group.model.model_variant")
    if source is None:
        return
    was_struct = False
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
        OmegaConf.update(cfg, "model_variant", source, merge=False)
    finally:
        if was_struct:
            try:
                OmegaConf.set_struct(cfg, True)
            except Exception:
                pass


def _resolve_task_id(ctx) -> str | None:
    if ctx.task is None:
        return None
    for attr in ("id", "task_id"):
        value = getattr(ctx.task, attr, None)
        if value:
            return str(value)
    return None


def _normalize_indices(values: Any, *, label: str) -> list[int]:
    if not isinstance(values, list):
        raise ValueError(f"{label} must be a list of indices.")
    return [int(v) for v in values]


def _merge_model_variant(cfg: Any) -> dict[str, Any]:
    variant = _to_container(getattr(cfg, "model_variant", None))
    if not variant:
        try:
            from omegaconf import OmegaConf  # type: ignore
        except Exception:
            OmegaConf = None
        if OmegaConf is not None:
            variant = OmegaConf.select(cfg, "group.model.model_variant")
        variant = _to_container(variant) or {}
    if not isinstance(variant, dict):
        raise TypeError("model_variant must be a dict-like object.")
    params = _to_container(variant.get("params") or {}) or {}
    train_params = _to_container(getattr(getattr(cfg, "train", None), "params", {}) or {}) or {}
    if not isinstance(params, dict) or not isinstance(train_params, dict):
        raise TypeError("model params must be dicts.")
    merged = {**params, **train_params}
    merged_variant = dict(variant)
    merged_variant["params"] = merged
    if not merged_variant.get("name"):
        merged_variant["name"] = _normalize_str(getattr(getattr(cfg, "train", None), "model", None))
    return merged_variant


def _find_model_spec(variant_id: str, *, task_type: str | None) -> Any | None:
    try:
        specs = list_model_variants(task_type=task_type, defaults_only=False)
    except Exception:
        return None
    for spec in specs:
        if spec.id == variant_id:
            return spec
    return None


def _extract_feature_importance(
    model: Any, feature_names: list[str] | None
) -> tuple[list[str], list[float]] | None:
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None

    importance = None
    if hasattr(model, "feature_importances_"):
        importance = getattr(model, "feature_importances_", None)
    elif hasattr(model, "coef_"):
        coef = getattr(model, "coef_", None)
        if coef is not None:
            coef_arr = np.asarray(coef)
            if coef_arr.ndim > 1:
                coef_arr = np.mean(np.abs(coef_arr), axis=0)
            importance = np.abs(coef_arr)

    if importance is None:
        return None

    importance_arr = np.asarray(importance).reshape(-1)
    names = list(feature_names or [])
    if len(names) != len(importance_arr):
        names = [f"feature_{idx}" for idx in range(len(importance_arr))]
    return names, [float(v) for v in importance_arr.tolist()]


def _write_feature_importance_csv(
    names: list[str],
    scores: list[float],
    output_dir: Path,
) -> Path:
    pairs = sorted(zip(names, scores), key=lambda x: x[1], reverse=True)
    lines = ["feature,importance"]
    for name, score in pairs:
        lines.append(f"{name},{float(score)}")
    path = output_dir / "feature_importance.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _plotly_go():
    try:
        import plotly.graph_objects as go  # type: ignore
    except Exception:
        return None
    return go


def _build_plotly_feature_importance(
    names: list[str],
    scores: list[float],
    *,
    top_n: int,
) -> Any | None:
    go = _plotly_go()
    if go is None:
        return None
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None
    values = np.asarray(scores, dtype=float).reshape(-1)
    order = np.argsort(values)[::-1]
    if top_n <= 0 or top_n > len(order):
        top_n = len(order)
    order = order[:top_n]
    labels = [str(names[idx]) for idx in order]
    values = values[order]
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color="#4C78A8"))
    fig.update_layout(
        title="Feature Importance",
        xaxis_title="importance",
        yaxis_title="feature",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def _build_plotly_residuals(
    y_true: Any,
    y_pred: Any,
    *,
    title: str = "Residuals vs Predicted",
) -> Any | None:
    go = _plotly_go()
    if go is None:
        return None
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None
    y_true_arr = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred_arr = np.asarray(y_pred, dtype=float).reshape(-1)
    if y_true_arr.shape[0] == 0 or y_pred_arr.shape[0] == 0:
        return None
    n = min(y_true_arr.shape[0], y_pred_arr.shape[0])
    residuals = y_true_arr[:n] - y_pred_arr[:n]
    fig = go.Figure(
        go.Scatter(
            x=y_pred_arr[:n],
            y=residuals,
            mode="markers",
            marker=dict(size=6, color="#F58518"),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="predicted",
        yaxis_title="residual (true - pred)",
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def _build_plotly_confusion_matrix(
    y_true: Any,
    y_pred: Any,
    *,
    class_names: list[str] | None,
    normalize: bool,
) -> Any | None:
    go = _plotly_go()
    if go is None:
        return None
    try:
        import numpy as np  # type: ignore
        from sklearn.metrics import confusion_matrix  # type: ignore
    except Exception:
        return None
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)
    if y_true_arr.shape[0] == 0 or y_pred_arr.shape[0] == 0:
        return None
    labels = None
    if class_names is not None:
        labels = list(range(len(class_names)))
    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=labels)
    display_cm = cm.astype(float)
    if normalize:
        row_sums = display_cm.sum(axis=1, keepdims=True)
        with np.errstate(divide="ignore", invalid="ignore"):
            display_cm = np.divide(
                display_cm,
                row_sums,
                out=np.zeros_like(display_cm),
                where=row_sums != 0,
            )
    if class_names is None:
        values = np.unique(np.concatenate([y_true_arr, y_pred_arr]))
        class_names = [str(value) for value in values]
    fig = go.Figure(
        go.Heatmap(
            z=display_cm,
            x=class_names,
            y=class_names,
            colorscale="Blues",
            showscale=True,
        )
    )
    fig.update_layout(
        title="Confusion Matrix (normalized)" if normalize else "Confusion Matrix",
        xaxis_title="predicted",
        yaxis_title="true",
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def _build_plotly_roc_curve(y_true: Any, y_score: Any) -> Any | None:
    go = _plotly_go()
    if go is None:
        return None
    try:
        import numpy as np  # type: ignore
        from sklearn.metrics import auc, roc_curve  # type: ignore
    except Exception:
        return None
    y_true_arr = np.asarray(y_true)
    scores = np.asarray(y_score, dtype=float)
    if scores.ndim > 1:
        scores = scores[:, -1]
    if y_true_arr.shape[0] == 0:
        return None
    fpr, tpr, _ = roc_curve(y_true_arr, scores)
    roc_auc = auc(fpr, tpr)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines", name=f"AUC={roc_auc:.3f}"))
    fig.add_trace(
        go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(dash="dash"), name="chance")
    )
    fig.update_layout(
        title="ROC Curve",
        xaxis_title="false positive rate",
        yaxis_title="true positive rate",
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def _build_prediction_sample(
    y_true: Any,
    y_pred: Any,
    y_proba: Any | None,
    *,
    max_rows: int = 5,
) -> Any | None:
    try:
        import numpy as np  # type: ignore
        import pandas as pd  # type: ignore
    except Exception:
        return None
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)
    n = min(len(y_true_arr), len(y_pred_arr))
    if n <= 0:
        return None
    payload: dict[str, Any] = {
        "y_true": y_true_arr[:n],
        "y_pred": y_pred_arr[:n],
    }
    if y_proba is not None:
        proba_arr = np.asarray(y_proba)
        if proba_arr.ndim == 2:
            col = 1 if proba_arr.shape[1] > 1 else 0
            payload["pred_proba"] = proba_arr[:n, col]
        else:
            payload["pred_proba"] = proba_arr.reshape(-1)[:n]
    df = pd.DataFrame(payload)
    return df.head(max_rows)


def _write_preds_valid(
    output_dir: Path,
    *,
    y_true: Any,
    y_pred: Any,
    y_proba: Any | None,
    task_type: str,
    class_labels: list[str] | None,
) -> tuple[Path | None, Path | None, dict[str, Any] | None]:
    try:
        import numpy as np  # type: ignore
        import pandas as pd  # type: ignore
    except Exception:
        return None, None, None
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)
    n = min(len(y_true_arr), len(y_pred_arr))
    if n <= 0:
        return None, None, None
    payload: dict[str, Any] = {
        "y_true": y_true_arr[:n],
        "y_pred": y_pred_arr[:n],
    }
    preds_schema: dict[str, Any] = {"task_type": task_type}
    classes_path: Path | None = None
    if task_type == "classification":
        if y_proba is not None:
            proba_arr = np.asarray(y_proba)
            if proba_arr.ndim == 1:
                proba_arr = np.stack([1.0 - proba_arr, proba_arr], axis=1)
            if class_labels is None or len(class_labels) != int(proba_arr.shape[1]):
                class_labels = [str(i) for i in range(int(proba_arr.shape[1]))]
            for idx, label in enumerate(class_labels):
                payload[f"proba__{label}"] = proba_arr[:n, idx]
        preds_schema["classes"] = class_labels
        preds_schema["has_proba"] = y_proba is not None
        if class_labels is not None:
            classes_path = output_dir / "artifacts" / "classes.json"
            classes_path.parent.mkdir(parents=True, exist_ok=True)
            classes_path.write_text(
                json.dumps(class_labels, ensure_ascii=True, indent=2), encoding="utf-8"
            )
    artifacts_dir = output_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    preds_path = artifacts_dir / "preds_valid.parquet"
    df = pd.DataFrame(payload)
    df.to_parquet(preds_path, index=False)
    preds_schema["columns"] = list(df.columns)
    return preds_path, classes_path, preds_schema


def _record_model_failure(
    *,
    ctx: Any,
    cfg: Any,
    processed_dataset_id: str,
    split_hash: str,
    recipe_hash: str,
    model_variant_name: str,
    primary_metric: str,
    direction: str,
    cv_folds: int,
    cv_seed: int,
    task_type: str,
    n_classes: int | None,
    error: Exception,
) -> None:
    train_task_id = _resolve_task_id(ctx)
    error_payload = {"type": error.__class__.__name__, "message": str(error)}
    out = {
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "train_task_id": train_task_id,
        "model_id": None,
        "best_score": None,
        "primary_metric": primary_metric,
        "task_type": task_type,
        "status": "failed",
        "error": error_payload,
        "model_variant": model_variant_name,
    }
    if n_classes is not None:
        out["n_classes"] = n_classes
    write_out_json(ctx, out)

    clearml_enabled = is_clearml_enabled(cfg)
    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    inputs = {
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "model_variant": model_variant_name,
        "primary_metric": primary_metric,
        "direction": direction,
        "cv_folds": cv_folds,
        "seed": cv_seed,
        "task_type": task_type,
    }
    outputs = {
        "model_id": None,
        "best_score": None,
        "primary_metric": primary_metric,
        "task_type": task_type,
        "status": "failed",
    }
    if n_classes is not None:
        outputs["n_classes"] = n_classes
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "train_model",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
        "outputs": outputs,
        "hashes": {
            "config_hash": hash_config(cfg),
            "split_hash": split_hash,
            "recipe_hash": recipe_hash,
        },
        "error": error_payload,
    }
    write_manifest(ctx, manifest)


def _record_model_skip(
    *,
    ctx: Any,
    cfg: Any,
    processed_dataset_id: str | None,
    split_hash: str | None,
    recipe_hash: str | None,
    model_variant_name: str,
    primary_metric: str,
    direction: str,
    cv_folds: int,
    cv_seed: int,
    task_type: str,
    n_classes: int | None,
    reason: str,
    detail: Any | None = None,
) -> None:
    train_task_id = _resolve_task_id(ctx)
    out = {
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "train_task_id": train_task_id,
        "model_id": None,
        "best_score": None,
        "primary_metric": primary_metric,
        "task_type": task_type,
        "model_variant": model_variant_name,
    }
    if n_classes is not None:
        out["n_classes"] = n_classes
    emit_skip(ctx, reason=reason, detail=detail, out=out)

    clearml_enabled = is_clearml_enabled(cfg)
    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    inputs = {
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "model_variant": model_variant_name,
        "primary_metric": primary_metric,
        "direction": direction,
        "cv_folds": cv_folds,
        "seed": cv_seed,
        "task_type": task_type,
    }
    outputs = {
        "model_id": None,
        "best_score": None,
        "primary_metric": primary_metric,
        "task_type": task_type,
        "status": "skipped",
        "reason": reason,
    }
    if n_classes is not None:
        outputs["n_classes"] = n_classes
    hashes = {"config_hash": hash_config(cfg)}
    if split_hash:
        hashes["split_hash"] = split_hash
    if recipe_hash:
        hashes["recipe_hash"] = recipe_hash
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "train_model",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
        "outputs": outputs,
        "hashes": hashes,
    }
    write_manifest(ctx, manifest)


def run(cfg: Any) -> None:
    _ensure_variant_cfg(cfg)
    identity = apply_clearml_identity(cfg, stage=cfg.task.stage)
    apply_train_model_naming(cfg)
    ctx = init_task_context(
        cfg,
        stage=cfg.task.stage,
        task_name="train_model",
        tags=identity.tags,
        properties=identity.user_properties,
    )
    save_config_resolved(ctx, cfg)
    clearml_enabled = is_clearml_enabled(cfg)
    task_type = _normalize_task_type(getattr(getattr(cfg, "eval", None), "task_type", None))
    primary_metric, direction, cv_folds, cv_seed = _resolve_eval_context(cfg, task_type=task_type)

    processed_ref = _normalize_str(getattr(getattr(cfg, "data", None), "processed_dataset_id", None))
    processed_ref_path: Path | None = None
    if processed_ref:
        candidate = Path(processed_ref).expanduser()
        if candidate.exists():
            processed_ref_path = candidate.resolve()

    preprocess_run_dir = _resolve_preprocess_run_dir(cfg, processed_ref_path)
    preprocess_out_path = preprocess_run_dir / "out.json"
    preprocess_out: dict[str, Any] | None = None
    assets_dir: Path | None = None

    if preprocess_out_path.exists():
        preprocess_out = _load_json(preprocess_out_path)
        if _normalize_str(preprocess_out.get("status")) == "skipped":
            processed_dataset_id = _normalize_str(preprocess_out.get("processed_dataset_id"))
            split_hash = _normalize_str(preprocess_out.get("split_hash"))
            recipe_hash = _normalize_str(preprocess_out.get("recipe_hash"))
            model_variant = _merge_model_variant(cfg)
            model_variant_name = _normalize_str(model_variant.get("name")) or "unknown"
            skip_reason = _normalize_str(preprocess_out.get("reason")) or "inapplicable"
            skip_detail = {
                "upstream": "preprocess",
                "preprocess_reason": preprocess_out.get("reason"),
                "preprocess_detail": preprocess_out.get("detail"),
                "preprocess_run_dir": str(preprocess_run_dir),
            }
            _record_model_skip(
                ctx=ctx,
                cfg=cfg,
                processed_dataset_id=processed_dataset_id,
                split_hash=split_hash,
                recipe_hash=recipe_hash,
                model_variant_name=model_variant_name,
                primary_metric=primary_metric,
                direction=direction,
                cv_folds=cv_folds,
                cv_seed=cv_seed,
                task_type=task_type,
                n_classes=None,
                reason=skip_reason,
                detail=skip_detail,
            )
            return
        processed_dataset_id = _normalize_str(preprocess_out.get("processed_dataset_id"))
        split_hash = _normalize_str(preprocess_out.get("split_hash"))
        recipe_hash = _normalize_str(preprocess_out.get("recipe_hash"))
        if not processed_dataset_id or not split_hash or not recipe_hash:
            raise ValueError("preprocess out.json is missing required keys.")
        if processed_ref and processed_ref_path is None and processed_ref != processed_dataset_id:
            raise ValueError(
                "data.processed_dataset_id does not match preprocess out.json. "
                "Set train.inputs.preprocess_run_dir to the matching preprocess output."
            )
        assets_dir = preprocess_run_dir
    else:
        if processed_ref_path is not None:
            assets_dir = processed_ref_path if processed_ref_path.is_dir() else processed_ref_path.parent
        elif processed_ref and clearml_enabled and not processed_ref.startswith("local:"):
            assets_dir = get_processed_dataset_local_copy(cfg, processed_ref)
        else:
            raise FileNotFoundError(
                "preprocess out.json not found; specify train.inputs.preprocess_run_dir or data.processed_dataset_id."
            )
        meta_path = assets_dir / "meta.json"
        meta_payload = _load_json(meta_path) if meta_path.exists() else {}
        processed_dataset_id = _normalize_str(processed_ref) or _normalize_str(
            meta_payload.get("processed_dataset_id")
        )
        split_hash = _normalize_str(meta_payload.get("split_hash"))
        recipe_hash = _normalize_str(meta_payload.get("recipe_hash"))
        if not processed_dataset_id or not split_hash or not recipe_hash:
            raise ValueError("processed dataset meta.json is missing required keys.")

    if assets_dir is None or not assets_dir.exists():
        raise FileNotFoundError("processed dataset assets directory not found.")

    split_path = _resolve_split_path(assets_dir)
    split_payload = _load_json(split_path)
    train_idx = _normalize_indices(split_payload.get("train_index"), label="train_index")
    val_idx = _normalize_indices(split_payload.get("val_index"), label="val_index")

    bundle_path = assets_dir / "preprocess_bundle.joblib"
    if not bundle_path.exists():
        raise FileNotFoundError(f"preprocess_bundle.joblib not found: {bundle_path}")
    preprocess_bundle = load_bundle(bundle_path)

    processed_dataset_path: Path | None = None
    if processed_ref_path is not None:
        if processed_ref_path.is_file():
            processed_dataset_path = processed_ref_path
        elif processed_ref_path.is_dir():
            candidate = processed_ref_path / "processed_dataset.parquet"
            if candidate.exists():
                processed_dataset_path = candidate
    if processed_dataset_path is None and preprocess_out is not None:
        out_path_value = _normalize_str(preprocess_out.get("processed_dataset_path"))
        if out_path_value:
            candidate = Path(out_path_value).expanduser()
            if candidate.exists():
                processed_dataset_path = candidate.resolve()
    if processed_dataset_path is None:
        candidate = assets_dir / "processed_dataset.parquet"
        if candidate.exists():
            processed_dataset_path = candidate
    df = None
    dataset_target_column: str | None = None
    if processed_dataset_path is not None:
        df = _load_dataframe(processed_dataset_path)
    else:
        df, dataset_target_column = _load_processed_from_xy(assets_dir)
        if df is None:
            df, dataset_target_column = _rebuild_processed_from_raw(
                cfg,
                base_dir=assets_dir,
                preprocess_bundle=preprocess_bundle if isinstance(preprocess_bundle, dict) else {},
                split_payload=split_payload,
                task_type=task_type,
            )
    if df is None:
        raise FileNotFoundError("processed dataset not found; specify preprocess_run_dir or dataset features.")

    bundle_columns = {}
    if isinstance(preprocess_bundle, dict):
        bundle_columns = preprocess_bundle.get("columns", {}) or {}
    target_column = (
        _normalize_str(bundle_columns.get("target_column"))
        or dataset_target_column
        or _normalize_str(getattr(getattr(cfg, "data", None), "target_column", None))
    )
    if not target_column or target_column not in df.columns:
        raise ValueError(f"target_column not found in processed dataset: {target_column}")

    feature_names = None
    if isinstance(preprocess_bundle, dict):
        feature_names = preprocess_bundle.get("feature_names")
    if not feature_names:
        feature_names = _load_feature_names(assets_dir)
    if feature_names and all(name in df.columns for name in feature_names):
        X = df[feature_names]
    else:
        X = df.drop(columns=[target_column])
        feature_names = list(X.columns)
    y = df[target_column].to_numpy()
    label_encoder = None
    n_classes: int | None = None
    classification_mode: str | None = None
    class_labels: list[str] | None = None
    class_labels_raw: list[Any] | None = None
    if task_type == "classification":
        try:
            from sklearn.preprocessing import LabelEncoder  # type: ignore
        except Exception as exc:
            raise RuntimeError("scikit-learn is required for classification.") from exc
        label_encoder = LabelEncoder()
        y = label_encoder.fit_transform(y)
        n_classes = int(len(label_encoder.classes_))
        if n_classes < 2:
            raise ValueError("classification requires at least 2 classes in target.")
        classification_mode = _resolve_classification_mode(cfg, n_classes=n_classes)
        class_labels_raw = list(label_encoder.classes_)
        class_labels = [str(label) for label in class_labels_raw]

    thresholding_cfg = _resolve_thresholding_settings(cfg)
    calibration_cfg = _resolve_calibration_settings(cfg)
    imbalance_cfg = _resolve_imbalance_settings(cfg)
    uncertainty_cfg = _resolve_uncertainty_settings(cfg)
    ci_cfg = _resolve_ci_settings(cfg)
    if uncertainty_cfg["enabled"] and task_type != "regression":
        raise ValueError("eval.uncertainty.enabled is supported for regression only.")
    if thresholding_cfg["enabled"]:
        if task_type != "classification":
            raise ValueError("threshold optimization is supported for classification only.")
        if n_classes != 2:
            raise ValueError("threshold optimization supports binary classification only.")
    if calibration_cfg["enabled"] and task_type != "classification":
        raise ValueError("probability calibration is supported for classification only.")
    fbeta_beta = _cfg_value(cfg, "eval.metrics.fbeta_beta", 1.0)
    try:
        fbeta_beta = float(fbeta_beta)
    except Exception:
        fbeta_beta = 1.0

    uncertainty_payload: dict[str, Any] = {
        "enabled": bool(uncertainty_cfg.get("enabled")),
        "method": uncertainty_cfg.get("method"),
        "alpha": uncertainty_cfg.get("alpha"),
        "q": None,
    }

    if not train_idx or not val_idx:
        raise ValueError("split.json must include non-empty train_index and val_index.")

    X_train = X.iloc[train_idx]
    y_train = y[train_idx]
    X_val = X.iloc[val_idx]
    y_val = y[val_idx]

    drift_settings = resolve_drift_settings(cfg)
    train_profile: dict[str, Any] | None = None
    train_profile_path: Path | None = None
    if drift_settings["enabled"]:
        drift_sample, sample_info = sample_frame(
            X_train,
            sample_n=drift_settings["sample_n"],
            seed=drift_settings["sample_seed"],
        )
        train_profile = build_train_profile(drift_sample, feature_columns=list(X_train.columns))
        train_profile = annotate_profile(
            train_profile,
            role="train",
            sample_info=sample_info,
            metrics=drift_settings["metrics"],
        )
        settings = train_profile.get("settings")
        if isinstance(settings, dict):
            alert_thresholds = drift_settings.get("alert_thresholds")
            if alert_thresholds:
                settings["alert_thresholds"] = dict(alert_thresholds)
        train_profile_path = ctx.output_dir / "train_profile.json"
        train_profile_path.write_text(
            json.dumps(train_profile, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if clearml_enabled:
            upload_artifact(ctx, train_profile_path.name, train_profile_path)

    model_variant = _merge_model_variant(cfg)
    model_variant_name = _normalize_str(model_variant.get("name")) or "unknown"
    model_variant_fit = dict(model_variant)
    model_variant_fit["params"] = dict(model_variant.get("params") or {})
    model_spec = _find_model_spec(model_variant_name, task_type=task_type)
    if model_spec is not None:
        missing = list(model_spec.missing_dependencies() or [])
        if missing:
            _record_model_skip(
                ctx=ctx,
                cfg=cfg,
                processed_dataset_id=processed_dataset_id,
                split_hash=split_hash,
                recipe_hash=recipe_hash,
                model_variant_name=model_variant_name,
                primary_metric=primary_metric,
                direction=direction,
                cv_folds=cv_folds,
                cv_seed=cv_seed,
                task_type=task_type,
                n_classes=n_classes,
                reason="missing_dependency",
                detail={"missing": missing, "model_variant": model_variant_name},
            )
            return

    imbalance_report: dict[str, Any] = {
        "enabled": bool(imbalance_cfg.get("enabled")),
        "strategy": imbalance_cfg.get("strategy"),
        "applied": False,
    }
    X_train_fit = X_train
    y_train_fit = y_train
    resample_strategy: str | None = None
    if imbalance_cfg.get("enabled"):
        if task_type != "classification":
            imbalance_report["reason"] = "task_type_not_classification"
        elif not imbalance_cfg.get("strategy"):
            imbalance_report["reason"] = "strategy_missing"
        elif imbalance_cfg.get("strategy") in ("oversample", "undersample"):
            imbalance_seed = int(_cfg_value(cfg, "eval.seed", 42) or 42)
            X_train_fit, y_train_fit, resample_info, resample_reason = _apply_resampling(
                imbalance_cfg["strategy"],
                X_train,
                y_train,
                seed=imbalance_seed,
            )
            if resample_reason:
                imbalance_report["reason"] = resample_reason
            else:
                imbalance_report["applied"] = True
                imbalance_report["detail"] = resample_info
                resample_strategy = imbalance_cfg["strategy"]
        else:
            model_variant_fit, weight_report = _apply_weight_strategy(
                model_variant=model_variant_fit,
                task_type=task_type,
                y_train=y_train,
                n_classes=n_classes,
                imbalance_cfg=imbalance_cfg,
            )
            imbalance_report.update(weight_report)
        if not imbalance_report.get("applied"):
            warnings.warn(
                f"Imbalance strategy '{imbalance_cfg.get('strategy')}' was skipped: "
                f"{imbalance_report.get('reason')}"
            )

    calibration_report_path: Path | None = None
    calibration_plot_path: Path | None = None

    try:
        model = build_model(model_variant_fit, task_type=task_type)
        model.fit(X_train_fit, y_train_fit)

        predictor = model
        calibrated_model = None
        calibration_payload: dict[str, Any] | None = None
        if task_type == "classification" and calibration_cfg["enabled"]:
            if not hasattr(model, "predict_proba"):
                raise ValueError("calibration requires predict_proba on the model.")
            calibrated_model = _calibrate_classifier(
                model,
                X_val,
                y_val,
                method=calibration_cfg["method"],
                mode=calibration_cfg["mode"],
            )
            predictor = calibrated_model
            calibration_payload = {
                "enabled": True,
                "method": calibration_cfg["method"],
                "mode": calibration_cfg["mode"],
            }

        metrics_holdout: dict[str, float] = {}
        regression_metrics: dict[str, float] | None = None
        y_val_pred = predictor.predict(X_val)
        y_val_proba = None
        if task_type == "classification" and hasattr(predictor, "predict_proba"):
            y_val_proba = predictor.predict_proba(X_val)

        threshold_payload: dict[str, Any] | None = None
        if thresholding_cfg["enabled"]:
            if y_val_proba is None:
                raise ValueError("threshold optimization requires predict_proba on the model.")
            best_threshold, threshold_score, threshold_direction = _select_best_threshold(
                y_val,
                y_val_proba,
                metric_name=thresholding_cfg["metric"],
                grid=thresholding_cfg["grid"],
                task_type=task_type,
                n_classes=n_classes,
                beta=fbeta_beta,
            )
            positive_proba = _extract_positive_proba(y_val_proba)
            y_val_pred = (positive_proba >= best_threshold).astype(int)
            threshold_payload = {
                "enabled": True,
                "metric": thresholding_cfg["metric"],
                "best_threshold": best_threshold,
                "best_score": threshold_score,
                "direction": threshold_direction,
            }

        if calibration_payload is not None and y_val_proba is not None:
            report, curve_conf, curve_acc = _build_calibration_report(
                y_val,
                y_val_proba,
                n_classes=n_classes,
            )
            calibration_report_path = ctx.output_dir / "calibration_report.json"
            calibration_report_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            calibration_plot_path = plot_reliability_curve(
                curve_conf,
                curve_acc,
                ctx.output_dir / "calibration_reliability.png",
                title="Reliability Diagram",
            )

        if task_type == "classification":
            if y_val_proba is not None and n_classes and n_classes > 2:
                import numpy as np  # type: ignore

                y_val_pred = np.asarray(y_val_proba).argmax(axis=1)
            mode = classification_mode or "binary"
            metric_names = _resolve_classification_metrics(
                cfg,
                classification_mode=mode,
                n_classes=n_classes,
                imbalance_enabled=bool(imbalance_cfg.get("enabled")),
            )
            for name in metric_names:
                if n_classes is not None and n_classes != 2 and _is_binary_only_metric(name):
                    warnings.warn(f"metric '{name}' is binary-only; skipping for multiclass.")
                    continue
                if metric_requires_proba(name, task_type) and y_val_proba is None:
                    continue
                metric_fn = get_metric(name, task_type, n_classes=n_classes, beta=fbeta_beta)
                metrics_holdout[name] = float(metric_fn(y_val, y_val_pred, y_val_proba))
            if primary_metric not in metrics_holdout:
                if metric_requires_proba(primary_metric, task_type) and y_val_proba is None:
                    raise ValueError(
                        f"primary_metric '{primary_metric}' requires predict_proba but model does not support it."
                    )
                metric_fn = get_metric(primary_metric, task_type, n_classes=n_classes, beta=fbeta_beta)
                metrics_holdout[primary_metric] = float(
                    metric_fn(y_val, y_val_pred, y_val_proba)
                )
        else:
            metric_names = _resolve_regression_metrics(cfg)
            regression_metrics = compute_regression_metrics(y_val, y_val_pred, metrics=metric_names)
            metrics_holdout.update(regression_metrics)
            if primary_metric not in metrics_holdout:
                metrics_holdout[primary_metric] = float(
                    get_metric(primary_metric, task_type)(y_val, y_val_pred)
                )

        if uncertainty_cfg.get("enabled"):
            q = compute_split_conformal_quantile(
                y_val,
                y_val_pred,
                alpha=float(uncertainty_cfg.get("alpha") or 0.1),
                use_abs_residual=bool(uncertainty_cfg.get("use_abs_residual", True)),
            )
            uncertainty_payload["q"] = q

        best_score = metrics_holdout[primary_metric]
        debug_sample = None
        if clearml_enabled:
            debug_sample = _build_prediction_sample(y_val, y_val_pred, y_val_proba)

        ci_payload: dict[str, Any] | None = None
        if ci_cfg.get("enabled"):
            ci_interval, ci_info = _bootstrap_metric_ci(
                y_val,
                y_val_pred,
                y_val_proba,
                metric_name=primary_metric,
                task_type=task_type,
                n_classes=n_classes,
                n_boot=int(ci_cfg.get("n_boot") or 0),
                alpha=float(ci_cfg.get("alpha") or 0.05),
                seed=int(ci_cfg.get("seed") or 0),
                beta=fbeta_beta,
                point_estimate=best_score,
            )
            if ci_interval is None:
                warnings.warn("Bootstrap CI skipped: no valid samples.")
                ci_interval = {"low": None, "mid": float(best_score), "high": None}
            if ci_info["n_boot_effective"] < ci_info["n_boot"]:
                warnings.warn(
                    "Bootstrap CI used fewer samples than requested "
                    f"({ci_info['n_boot_effective']}/{ci_info['n_boot']})."
                )
            ci_payload = {
                "primary_metric": ci_interval,
                "n_boot": ci_info["n_boot"],
                "n_boot_effective": ci_info["n_boot_effective"],
                "alpha": ci_info["alpha"],
                "seed": ci_info["seed"],
            }

        cv_summary: dict[str, Any] | None = None
        if cv_folds and cv_folds > 1:
            if len(train_idx) < cv_folds:
                warnings.warn(
                    "eval.cv_folds is larger than the training split size; skipping CV."
                )
            else:
                try:
                    import numpy as np  # type: ignore
                    from sklearn.model_selection import KFold  # type: ignore
                except Exception as exc:
                    raise RuntimeError("scikit-learn is required for cross-validation.") from exc

                kf = KFold(n_splits=cv_folds, shuffle=True, random_state=cv_seed)
                scores: list[float] = []
                metric_fn = get_metric(primary_metric, task_type, n_classes=n_classes, beta=fbeta_beta)
                X_train_full = X.iloc[train_idx]
                y_train_full = y[train_idx]
                needs_proba = metric_requires_proba(primary_metric, task_type)
                for fold_train_idx, fold_val_idx in kf.split(X_train_full):
                    fold_X_train = X_train_full.iloc[fold_train_idx]
                    fold_y_train = y_train_full[fold_train_idx]
                    if resample_strategy:
                        fold_X_train, fold_y_train, _, _ = _apply_resampling(
                            resample_strategy,
                            fold_X_train,
                            fold_y_train,
                            seed=cv_seed,
                        )
                    fold_model = build_model(model_variant_fit, task_type=task_type)
                    fold_model.fit(fold_X_train, fold_y_train)
                    fold_pred = fold_model.predict(X_train_full.iloc[fold_val_idx])
                    fold_proba = None
                    if needs_proba:
                        if not hasattr(fold_model, "predict_proba"):
                            raise ValueError(
                                f"primary_metric '{primary_metric}' requires predict_proba "
                                "but model does not support it."
                            )
                        fold_proba = fold_model.predict_proba(X_train_full.iloc[fold_val_idx])
                    scores.append(float(metric_fn(y_train_full[fold_val_idx], fold_pred, fold_proba)))
                cv_summary = {
                    "folds": cv_folds,
                    "seed": cv_seed,
                    "scores": scores,
                    "mean": float(np.mean(scores)) if scores else None,
                    "std": float(np.std(scores)) if scores else None,
                }
    except MissingOptionalDependencyError as exc:
        _record_model_skip(
            ctx=ctx,
            cfg=cfg,
            processed_dataset_id=processed_dataset_id,
            split_hash=split_hash,
            recipe_hash=recipe_hash,
            model_variant_name=model_variant_name,
            primary_metric=primary_metric,
            direction=direction,
            cv_folds=cv_folds,
            cv_seed=cv_seed,
            task_type=task_type,
            n_classes=n_classes,
            reason="missing_dependency",
            detail={"module": exc.module, "class_path": exc.class_path, "extra": exc.extra},
        )
        return
    except ModelWeightsUnavailableError as exc:
        _record_model_failure(
            ctx=ctx,
            cfg=cfg,
            processed_dataset_id=processed_dataset_id,
            split_hash=split_hash,
            recipe_hash=recipe_hash,
            model_variant_name=model_variant_name,
            primary_metric=primary_metric,
            direction=direction,
            cv_folds=cv_folds,
            cv_seed=cv_seed,
            task_type=task_type,
            n_classes=n_classes,
            error=exc,
        )
        raise

    metrics_payload: dict[str, Any] = {
        "primary_metric": primary_metric,
        "direction": direction,
        "task_type": task_type,
        "holdout": {
            **metrics_holdout,
            "train_rows": int(len(train_idx)),
            "val_rows": int(len(val_idx)),
        },
    }
    if n_classes is not None:
        metrics_payload["n_classes"] = n_classes
    if cv_summary is not None:
        metrics_payload["cv"] = cv_summary
    if threshold_payload is not None:
        metrics_payload["thresholding"] = threshold_payload
    if calibration_payload is not None:
        metrics_payload["calibration"] = calibration_payload
    metrics_payload["uncertainty"] = uncertainty_payload
    if ci_payload is not None:
        metrics_payload["ci"] = ci_payload

    metrics_path = ctx.output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    preds_path, classes_path, preds_schema = _write_preds_valid(
        ctx.output_dir,
        y_true=y_val,
        y_pred=y_val_pred,
        y_proba=y_val_proba,
        task_type=task_type,
        class_labels=class_labels,
    )

    metrics_ci_path: Path | None = None
    if ci_payload is not None:
        metrics_ci_path = ctx.output_dir / "metrics_ci.json"
        metrics_ci_path.write_text(
            json.dumps(ci_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    postprocess_payload: dict[str, Any] = {}
    if threshold_payload is not None:
        postprocess_payload.update(
            {
                "threshold": threshold_payload.get("best_threshold"),
                "metric": threshold_payload.get("metric"),
                "score": threshold_payload.get("best_score"),
                "direction": threshold_payload.get("direction"),
            }
        )
    if calibration_payload is not None:
        postprocess_payload["calibration"] = calibration_payload

    postprocess_path: Path | None = None
    if postprocess_payload:
        postprocess_path = ctx.output_dir / "postprocess.json"
        postprocess_path.write_text(
            json.dumps(postprocess_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    train_task_id = _resolve_task_id(ctx)
    preprocess_provenance = _resolve_preprocess_provenance(
        preprocess_run_dir,
        assets_dir,
        preprocess_out,
        preprocess_bundle,
    )
    provenance_payload = {
        "train_task_id": train_task_id,
        "raw_dataset_id": preprocess_provenance.get("raw_dataset_id"),
        "processed_dataset_id": processed_dataset_id,
        "preprocess_variant": preprocess_provenance.get("preprocess_variant"),
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
    }

    model_bundle = {
        "model": model,
        "calibrated_model": calibrated_model,
        "model_variant": model_variant_name,
        "primary_metric": primary_metric,
        "best_score": best_score,
        "metrics": metrics_payload,
        "preprocess_bundle": preprocess_bundle,
        "feature_names": feature_names,
        "target_column": target_column,
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "task_type": task_type,
        "label_encoder": label_encoder,
        "class_labels": class_labels_raw,
        "n_classes": n_classes,
        "postprocess": postprocess_payload or None,
        "uncertainty": {
            **uncertainty_payload,
            "use_abs_residual": uncertainty_cfg.get("use_abs_residual"),
        },
        "provenance": {key: value for key, value in provenance_payload.items() if value is not None},
    }
    if train_profile is not None:
        model_bundle["train_profile"] = train_profile
    if calibration_payload is not None:
        model_bundle["calibration"] = calibration_payload
    model_bundle_path = ctx.output_dir / "model_bundle.joblib"
    save_bundle(model_bundle_path, model_bundle)
    viz_settings = _resolve_viz_settings(cfg)
    feature_importance_path: Path | None = None
    feature_importance_plot_path: Path | None = None
    residuals_plot_path: Path | None = None
    interval_plot_path: Path | None = None
    confusion_csv_path: Path | None = None
    confusion_plot_path: Path | None = None
    roc_plot_path: Path | None = None

    importance_payload = _extract_feature_importance(model, feature_names)
    importance_names: list[str] | None = None
    importance_scores: list[float] | None = None
    if importance_payload is not None:
        names, scores = importance_payload
        importance_names = names
        importance_scores = scores
        feature_importance_path = _write_feature_importance_csv(names, scores, ctx.output_dir)
        if viz_settings["enabled"]:
            feature_importance_plot_path = plot_feature_importance(
                names,
                scores,
                ctx.output_dir / "feature_importance.png",
                top_n=viz_settings["max_features"],
            )

    class_names = class_labels
    if task_type == "regression":
        if viz_settings["enabled"]:
            residuals_plot_path = plot_regression_residuals(
                y_val,
                y_val_pred,
                ctx.output_dir / "residuals.png",
                max_points=viz_settings["max_points"],
            )
        if (
            viz_settings["enabled"]
            and uncertainty_payload.get("enabled")
            and uncertainty_payload.get("q") is not None
        ):
            width = float(uncertainty_payload["q"]) * 2.0
            interval_widths = [width for _ in range(int(len(y_val_pred) or 1))]
            interval_plot_path = plot_interval_width_histogram(
                interval_widths,
                ctx.output_dir / "interval_widths.png",
                title="Prediction Interval Widths",
            )
    else:
        confusion_csv_path = write_confusion_matrix_csv(
            y_val,
            y_val_pred,
            ctx.output_dir / "confusion_matrix.csv",
            class_names=class_names,
        )
        if viz_settings["enabled"]:
            confusion_plot_path = plot_confusion_matrix(
                y_val,
                y_val_pred,
                ctx.output_dir / "confusion_matrix.png",
                class_names=class_names,
                normalize=viz_settings["confusion_normalize"],
            )
            if (
                viz_settings["roc_curve"]
                and n_classes == 2
                and y_val_proba is not None
            ):
                roc_plot_path = plot_roc_curve(
                    y_val,
                    y_val_proba[:, 1],
                    ctx.output_dir / "roc_curve.png",
                )

    if clearml_enabled:
        plots_on = plots_enabled(cfg)
        scalars_on = scalars_enabled(cfg)
        tables_on = tables_enabled(cfg)
        if scalars_on:
            if task_type == "regression":
                for name in REGRESSION_METRIC_ORDER:
                    if name in metrics_holdout:
                        report_scalar(
                            ctx.task,
                            "metrics",
                            name,
                            metrics_holdout[name],
                            iteration=0,
                            cfg=cfg,
                        )
            if best_score is not None and (
                task_type != "regression" or primary_metric not in REGRESSION_METRIC_ORDER
            ):
                report_scalar(
                    ctx.task,
                    "metrics",
                    primary_metric,
                    best_score,
                    iteration=0,
                    cfg=cfg,
                )
        if tables_on and debug_sample is not None:
            log_debug_table(ctx.task, "train_model", "prediction_sample", debug_sample, step=0)
        if viz_settings["enabled"] and plots_on:
            if importance_names and importance_scores:
                fig = _build_plotly_feature_importance(
                    importance_names,
                    importance_scores,
                    top_n=viz_settings["max_features"],
                )
                report_plotly(
                    ctx.task,
                    "train_model",
                    "feature_importance",
                    fig or feature_importance_plot_path,
                    iteration=0,
                    cfg=cfg,
                )
            if task_type == "regression":
                metrics_payload = regression_metrics or metrics_holdout
                if tables_on:
                    metrics_table = build_regression_metrics_table(metrics_payload)
                    report_table(
                        ctx.task,
                        "train_model",
                        "metrics_table",
                        metrics_table or metrics_payload,
                        iteration=0,
                        cfg=cfg,
                        output_path=ctx.output_dir / "metrics_table.png",
                    )
                scatter = build_true_pred_scatter(
                    y_val,
                    y_val_pred,
                    r2=metrics_holdout.get("r2"),
                    max_points=viz_settings["max_points"],
                )
                scatter_path = None
                if scatter is None:
                    scatter_path = plot_true_pred_scatter(
                        y_val,
                        y_val_pred,
                        ctx.output_dir / "true_vs_pred.png",
                        max_points=viz_settings["max_points"],
                    )
                report_plotly(
                    ctx.task,
                    "train_model",
                    "true_vs_pred",
                    scatter or scatter_path,
                    iteration=0,
                    cfg=cfg,
                )
                fig = build_residuals_plot(
                    y_val,
                    y_val_pred,
                    max_points=viz_settings["max_points"],
                )
                report_plotly(
                    ctx.task,
                    "train_model",
                    "residuals",
                    fig or residuals_plot_path,
                    iteration=0,
                    cfg=cfg,
                )
            else:
                fig = _build_plotly_confusion_matrix(
                    y_val,
                    y_val_pred,
                    class_names=class_names,
                    normalize=viz_settings["confusion_normalize"],
                )
                report_plotly(
                    ctx.task,
                    "train_model",
                    "confusion_matrix",
                    fig or confusion_plot_path,
                    iteration=0,
                    cfg=cfg,
                )
                if y_val_proba is not None and n_classes == 2:
                    fig = _build_plotly_roc_curve(y_val, y_val_proba[:, 1])
                    report_plotly(
                        ctx.task,
                        "train_model",
                        "roc_curve",
                        fig or roc_plot_path,
                        iteration=0,
                        cfg=cfg,
                    )

    model_id = str(model_bundle_path)

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    recipe_payload: dict[str, Any] = {}
    recipe_path = preprocess_run_dir / "recipe.json"
    if recipe_path.exists():
        recipe_payload = _load_json(recipe_path)
    preprocess_variant = _normalize_str(recipe_payload.get("variant")) if recipe_payload else None
    if preprocess_variant is None and isinstance(preprocess_bundle, dict):
        preprocess_variant = _normalize_str(preprocess_bundle.get("preprocess_variant"))
    if preprocess_variant is None:
        preprocess_variant = "unknown"
    encoding_note = _format_encoding_note(recipe_payload) or "unknown"
    model_class_path = None
    if isinstance(model_variant, dict):
        model_class_path = _normalize_str(model_variant.get("class_path"))
    if model_class_path is None and isinstance(model_variant_fit, dict):
        model_class_path = _normalize_str(model_variant_fit.get("class_path"))
    model_params = {}
    if isinstance(model_variant_fit, dict):
        model_params = _stringify_payload(model_variant_fit.get("params") or {})

    model_card_lines = [
        "# Model Card",
        "",
        "## Dataset",
        f"- processed_dataset_id: {processed_dataset_id}",
        f"- split_hash: {split_hash}",
        f"- schema_version: {versions.get('schema_version', 'unknown')}",
        "",
        "## Preprocess",
        f"- preprocess_variant: {preprocess_variant}",
        f"- categorical_encoding: {encoding_note}",
        f"- recipe_hash: {recipe_hash}",
        "",
        "## Model",
        f"- model_variant: {model_variant_name}",
    ]
    if model_class_path:
        model_card_lines.append(f"- model_class: {model_class_path}")
    model_card_lines.extend(
        [
            f"- hyperparams: {json.dumps(model_params, ensure_ascii=True, sort_keys=True)}",
            f"- seed: {cv_seed}",
            f"- task_type: {task_type}",
        ]
    )
    if n_classes is not None:
        model_card_lines.append(f"- n_classes: {n_classes}")
    model_card_lines.extend(
        [
            "",
            "## Metrics",
            f"- primary_metric: {primary_metric} ({direction})",
            f"- best_score: {_format_float(best_score)}",
        ]
    )
    ci_text = _format_ci_interval(ci_payload)
    if ci_text:
        model_card_lines.append(f"- primary_metric_ci: {ci_text}")
    model_card_lines.extend(
        [
            f"- train_rows: {len(train_idx)}",
            f"- val_rows: {len(val_idx)}",
        ]
    )
    extra_metrics = _summarize_metrics(metrics_holdout, primary_metric)
    if extra_metrics:
        model_card_lines.append(f"- other_metrics: {extra_metrics}")
    model_card_lines.extend(["", "## Calibration / Thresholding / Uncertainty"])
    if threshold_payload is not None:
        model_card_lines.append(
            f"- thresholding: enabled metric={threshold_payload.get('metric')} "
            f"best_threshold={_format_float(threshold_payload.get('best_threshold'))} "
            f"score={_format_float(threshold_payload.get('best_score'))}"
        )
    else:
        model_card_lines.append("- thresholding: disabled")
    if calibration_payload is not None:
        model_card_lines.append(
            f"- calibration: enabled method={calibration_payload.get('method')} "
            f"mode={calibration_payload.get('mode')}"
        )
    else:
        model_card_lines.append("- calibration: disabled")
    if uncertainty_payload.get("enabled"):
        model_card_lines.append(
            f"- uncertainty: enabled method={uncertainty_payload.get('method')} "
            f"alpha={_format_float(uncertainty_payload.get('alpha'))} "
            f"q={_format_float(uncertainty_payload.get('q'))}"
        )
    else:
        model_card_lines.append("- uncertainty: disabled")
    imbalance_strategy = imbalance_report.get("strategy")
    imbalance_applied = imbalance_report.get("applied")
    if imbalance_report.get("enabled"):
        model_card_lines.append(
            f"- imbalance_handling: enabled strategy={imbalance_strategy} applied={imbalance_applied}"
        )
    else:
        model_card_lines.append("- imbalance_handling: disabled")
    model_card_lines.extend(
        [
            "",
            "## Limitations",
            "- Evaluated on a single split; performance may vary on new data.",
            "- Confirm leakage checks and target stability before promotion.",
            "- Not validated for out-of-scope inputs or populations.",
        ]
    )
    model_card_path = ctx.output_dir / "model_card.md"
    model_card_path.write_text("\n".join(model_card_lines) + "\n", encoding="utf-8")

    if clearml_enabled:
        upload_artifact(ctx, "metrics.json", metrics_path)
        if metrics_ci_path is not None:
            upload_artifact(ctx, metrics_ci_path.name, metrics_ci_path)
        if preds_path is not None:
            upload_artifact(ctx, preds_path.name, preds_path)
        if classes_path is not None:
            upload_artifact(ctx, classes_path.name, classes_path)
        upload_artifact(ctx, "model_bundle.joblib", model_bundle_path)
        upload_artifact(ctx, "model_card.md", model_card_path)
        if postprocess_path is not None:
            upload_artifact(ctx, postprocess_path.name, postprocess_path)
        if calibration_report_path is not None:
            upload_artifact(ctx, calibration_report_path.name, calibration_report_path)
        if feature_importance_path is not None:
            upload_artifact(ctx, feature_importance_path.name, feature_importance_path)
        if confusion_csv_path is not None:
            upload_artifact(ctx, confusion_csv_path.name, confusion_csv_path)
        extra_props = {"task_type": task_type}
        if n_classes is not None:
            extra_props["n_classes"] = n_classes
        if threshold_payload is not None:
            extra_props["best_threshold"] = threshold_payload.get("best_threshold")
        extra_props["imbalance_enabled"] = bool(imbalance_report.get("enabled"))
        extra_props["imbalance_strategy"] = imbalance_report.get("strategy")
        extra_props["imbalance_applied"] = bool(imbalance_report.get("applied"))
        update_task_properties(
            ctx,
            {
                "processed_dataset_id": processed_dataset_id,
                "split_hash": split_hash,
                "model_id": model_id,
                "primary_metric": primary_metric,
                "best_score": best_score,
                **extra_props,
            },
        )

    out = {
        "model_id": model_id,
        "train_task_id": train_task_id,
        "best_score": best_score,
        "primary_metric": primary_metric,
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "task_type": task_type,
    }
    if preds_path is not None:
        out["preds_valid_path"] = str(preds_path)
    if preds_schema is not None:
        out["preds_schema"] = preds_schema
    if classes_path is not None:
        out["classes_path"] = str(classes_path)
    if n_classes is not None:
        out["n_classes"] = n_classes
    if class_labels is not None:
        out["class_labels"] = class_labels
    if threshold_payload is not None:
        out["best_threshold"] = threshold_payload.get("best_threshold")
        out["threshold_metric"] = threshold_payload.get("metric")
        out["threshold_score"] = threshold_payload.get("best_score")
    if calibration_payload is not None:
        out["calibration"] = calibration_payload
    if ci_payload is not None:
        out["primary_metric_ci"] = ci_payload.get("primary_metric")
    out["imbalance"] = imbalance_report
    out["uncertainty"] = uncertainty_payload
    write_out_json(ctx, out)

    inputs = {
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "model_variant": model_variant_name,
        "primary_metric": primary_metric,
        "direction": direction,
        "cv_folds": cv_folds,
        "seed": cv_seed,
        "task_type": task_type,
    }
    outputs = {
        "model_id": model_id,
        "best_score": best_score,
        "primary_metric": primary_metric,
        "task_type": task_type,
    }
    if n_classes is not None:
        outputs["n_classes"] = n_classes
    if threshold_payload is not None:
        outputs["best_threshold"] = threshold_payload.get("best_threshold")
        outputs["threshold_metric"] = threshold_payload.get("metric")
        outputs["threshold_score"] = threshold_payload.get("best_score")
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "train_model",
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
