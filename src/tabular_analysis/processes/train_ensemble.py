"""train_ensemble process.

- collect train_model outputs and build ensemble predictions
- support mean_topk / weighted / stacking
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping
import warnings

from ..clearml.hparams import connect_train_ensemble
from ..clearml.naming import apply_train_ensemble_naming
from ..clearml.ui_logger import log_debug_table, log_plotly, log_scalar
from ..io.bundle_io import load_bundle, save_bundle
from ..metrics.regression import REGRESSION_METRIC_ORDER, compute_regression_metrics
from ..ops.clearml_identity import apply_clearml_identity
from ..platform_adapter import (
    PlatformAdapterError,
    clearml_task_id,
    clearml_task_status_from_obj,
    clearml_task_tags,
    get_task_artifact_local_copy,
    hash_config,
    init_task_context,
    is_clearml_enabled,
    list_clearml_tasks_by_tags,
    register_model_artifact,
    resolve_version_props,
    save_config_resolved,
    update_task_properties,
    upload_artifact,
    write_manifest,
    write_out_json,
)
from ..registry.metrics import get_metric, metric_direction, metric_requires_proba
from ..viz.plots import (
    plot_confusion_matrix,
    plot_regression_residuals,
    plot_roc_curve,
)
from ..viz.regression_plots import (
    build_regression_metrics_table,
    build_residuals_plot,
    build_true_pred_scatter,
)


@dataclass
class PredsPayload:
    y_true: Any
    y_pred: Any
    y_proba: Any | None
    class_labels: list[str] | None
    source: str


@dataclass
class Candidate:
    train_task_ref: str
    train_task_id: str | None
    preprocess_task_id: str | None
    model_id: str | None
    model_variant: str
    task_type: str
    n_classes: int | None
    processed_dataset_id: str | None
    split_hash: str | None
    recipe_hash: str | None
    metric_value: float
    preds: PredsPayload
    model_bundle_path: Path


class EnsemblePredictor:
    def __init__(
        self,
        *,
        task_type: str,
        method: str,
        base_models: list[Any],
        weights: list[float] | None = None,
        meta_model: Any | None = None,
        n_classes: int | None = None,
    ) -> None:
        self.task_type = task_type
        self.method = method
        self.base_models = list(base_models)
        self.weights = list(weights) if weights is not None else None
        self.meta_model = meta_model
        self.n_classes = n_classes

    def _predict_base(self, X, *, proba: bool) -> list[Any]:
        preds: list[Any] = []
        for model in self.base_models:
            if proba:
                pred = model.predict_proba(X)
            else:
                pred = model.predict(X)
            preds.append(pred)
        return preds

    def predict(self, X):
        import numpy as np  # type: ignore

        if self.task_type != "classification":
            if self.method == "stacking":
                if self.meta_model is None:
                    raise ValueError("meta_model is required for stacking.")
                return self.meta_model.predict(self._stack_meta_features(X))
            preds = self._predict_base(X, proba=False)
            arr = np.column_stack([np.asarray(p).reshape(-1) for p in preds])
            weights = self.weights or [1.0 / arr.shape[1]] * arr.shape[1]
            return np.average(arr, axis=1, weights=weights)

        proba = self.predict_proba(X)
        return np.asarray(proba).argmax(axis=1)

    def predict_proba(self, X):
        import numpy as np  # type: ignore

        if self.task_type != "classification":
            raise ValueError("predict_proba is only available for classification.")

        if self.method == "stacking" and self.meta_model is not None:
            meta_features = self._stack_meta_features(X)
            if hasattr(self.meta_model, "predict_proba"):
                return self.meta_model.predict_proba(meta_features)
            raise ValueError("meta_model lacks predict_proba.")

        proba_list = self._predict_base(X, proba=True)
        proba_arr = np.stack([np.asarray(p) for p in proba_list], axis=1)
        weights = self.weights or [1.0 / proba_arr.shape[1]] * proba_arr.shape[1]
        return np.average(proba_arr, axis=1, weights=weights)

    def _stack_meta_features(self, X):
        import numpy as np  # type: ignore

        if self.task_type == "classification":
            proba_list = self._predict_base(X, proba=True)
            arrays = [np.asarray(p) for p in proba_list]
            return np.hstack(arrays)
        preds = self._predict_base(X, proba=False)
        return np.column_stack([np.asarray(p).reshape(-1) for p in preds])


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
    return default if current is None else current


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_task_type(value: Any) -> str:
    key = _normalize_str(value)
    if key in ("classification", "classifier", "class"):
        return "classification"
    return "regression"


def _normalize_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "y", "on"):
        return True
    if text in ("0", "false", "no", "n", "off"):
        return False
    return default


def _dedupe_tags(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags:
        text = str(tag).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _build_registry_tags(
    *,
    usecase_id: str,
    process: str,
    processed_dataset_id: str,
    split_hash: str,
    recipe_hash: str,
    preprocess_variant: str,
    model_variant: str,
    task_type: str | None,
    train_ensemble_task_id: str | None,
    train_task_ids: Iterable[str],
    preprocess_task_ids: Iterable[str],
    pipeline_task_id: str | None,
) -> list[str]:
    tags = [
        f"usecase:{usecase_id}",
        f"process:{process}",
        f"dataset:{processed_dataset_id}",
        f"split:{split_hash}",
        f"recipe:{recipe_hash}",
        f"preprocess:{preprocess_variant}",
        f"model_variant:{model_variant}",
    ]
    if task_type:
        tags.append(f"task_type:{task_type}")
    if train_ensemble_task_id:
        tags.append(f"task:train_ensemble:{train_ensemble_task_id}")
    for task_id in train_task_ids:
        if task_id:
            tags.append(f"task:train_model:{task_id}")
    for task_id in preprocess_task_ids:
        if task_id:
            tags.append(f"task:preprocess:{task_id}")
    if pipeline_task_id:
        tags.append(f"task:pipeline:{pipeline_task_id}")
    return _dedupe_tags(tags)


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


def _plotly_go():
    try:
        import plotly.graph_objects as go  # type: ignore
    except Exception:
        return None
    return go


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


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _resolve_preprocess_variant(cfg: Any) -> str:
    for path in (
        "preprocess.variant",
        "preprocess_variant.name",
        "group.preprocess.preprocess_variant.name",
    ):
        value = _normalize_str(_cfg_value(cfg, path))
        if value:
            return value
    return "unknown"


def _resolve_primary_metric(cfg: Any) -> str:
    return _normalize_str(_cfg_value(cfg, "eval.primary_metric")) or "rmse"


def _resolve_selection_metric(cfg: Any) -> str:
    return _normalize_str(_cfg_value(cfg, "ensemble.selection_metric")) or _resolve_primary_metric(cfg)


def _resolve_top_k(cfg: Any) -> int:
    value = _cfg_value(cfg, "ensemble.top_k")
    try:
        return int(value)
    except Exception:
        return 0


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_metric_list(cfg: Any) -> list[str]:
    metrics = list(REGRESSION_METRIC_ORDER)
    extras = _to_list(_cfg_value(cfg, "eval.metrics.regression"))
    if extras:
        metrics.extend(extras)
    seen: set[str] = set()
    ordered: list[str] = []
    for name in metrics:
        key = _normalize_str(name)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def _resolve_viz_settings(cfg: Any) -> dict[str, Any]:
    enabled = bool(_cfg_value(cfg, "viz.enabled", True))
    try:
        max_points = int(_cfg_value(cfg, "viz.max_points", 1000))
    except Exception:
        max_points = 1000
    confusion_normalize = bool(_cfg_value(cfg, "viz.confusion_normalize", True))
    roc_curve = bool(_cfg_value(cfg, "viz.roc_curve", True))
    return {
        "enabled": enabled,
        "max_points": max_points,
        "confusion_normalize": confusion_normalize,
        "roc_curve": roc_curve,
    }


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
        metrics = _to_list(_cfg_value(cfg, "eval.metrics.classification_multiclass"))
        if not metrics:
            metrics = ["accuracy", "f1_macro", "logloss"]
    else:
        metrics = _to_list(_cfg_value(cfg, "eval.metrics.classification_binary"))
        if not metrics:
            metrics = ["accuracy", "f1", "log_loss"]
            if n_classes == 2:
                metrics.append("roc_auc")
    if imbalance_enabled:
        extra = _to_list(_cfg_value(cfg, "eval.metrics.classification_imbalance"))
        if extra:
            metrics.extend(extra)
    seen: set[str] = set()
    ordered: list[str] = []
    for name in metrics:
        key = _normalize_str(name)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def _load_classes(path: Path | None) -> list[str] | None:
    if path is None or not path.exists():
        return None
    payload = _load_json(path)
    if isinstance(payload, list):
        return [str(item) for item in payload]
    return None


def _load_preds_valid(
    preds_path: Path,
    *,
    task_type: str,
    classes_path: Path | None,
) -> PredsPayload:
    try:
        import numpy as np  # type: ignore
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas/numpy are required to load preds_valid.") from exc
    df = pd.read_parquet(preds_path)
    if "y_true" not in df.columns:
        raise ValueError("preds_valid.parquet missing y_true.")
    y_true = df["y_true"].to_numpy()
    y_pred = df["y_pred"].to_numpy() if "y_pred" in df.columns else None

    if task_type == "regression":
        if y_pred is None:
            raise ValueError("preds_valid.parquet missing y_pred for regression.")
        return PredsPayload(y_true=y_true, y_pred=y_pred, y_proba=None, class_labels=None, source="preds_valid")

    class_labels = _load_classes(classes_path)
    proba_cols = [c for c in df.columns if c.startswith("proba__")]
    if len(proba_cols) < 2:
        raise ValueError("preds_valid.parquet missing proba__* columns for classification.")
    if class_labels:
        ordered_cols = []
        for label in class_labels:
            col = f"proba__{label}"
            if col in df.columns:
                ordered_cols.append(col)
        if len(ordered_cols) == len(class_labels):
            proba_cols = ordered_cols
    else:
        class_labels = [c.split("proba__", 1)[-1] for c in proba_cols]

    proba = df[proba_cols].to_numpy()
    if y_pred is None:
        y_pred = proba.argmax(axis=1)
    return PredsPayload(
        y_true=y_true,
        y_pred=y_pred,
        y_proba=proba,
        class_labels=class_labels,
        source="preds_valid",
    )


def _load_preds_fallback(
    cfg: Any,
    *,
    run_dir: Path,
    task_type: str,
) -> PredsPayload | None:
    preprocess_dir = None
    config_path = run_dir / "config_resolved.yaml"
    if config_path.exists():
        try:
            from omegaconf import OmegaConf  # type: ignore

            train_cfg = OmegaConf.load(config_path)
            preprocess_run_dir = OmegaConf.select(train_cfg, "train.inputs.preprocess_run_dir")
            preprocess_run_dir = _normalize_str(preprocess_run_dir)
            if preprocess_run_dir:
                preprocess_dir = Path(preprocess_run_dir).expanduser()
        except Exception:
            preprocess_dir = None
    if preprocess_dir is None:
        train_root = run_dir.parent
        grid_root = train_root.parent
        parsed_variant = _parse_preprocess_variant_from_run_root(train_root)
        if parsed_variant:
            candidate = grid_root / f"preprocess__{parsed_variant}" / "02_preprocess"
            if candidate.exists():
                preprocess_dir = candidate
    if preprocess_dir is None or not preprocess_dir.exists():
        return None

    split_path = preprocess_dir / "split.json"
    if not split_path.exists():
        return None
    split_payload = _load_json(split_path)
    val_idx = split_payload.get("val_index") or []
    if not val_idx:
        return None

    dataset_dir = preprocess_dir / "processed_dataset"
    x_path = dataset_dir / "X.parquet"
    y_path = dataset_dir / "y.parquet"
    if not x_path.exists() or not y_path.exists():
        return None

    try:
        import numpy as np  # type: ignore
        import pandas as pd  # type: ignore
    except Exception:
        return None

    X = pd.read_parquet(x_path)
    y = pd.read_parquet(y_path)
    if y.shape[1] != 1:
        return None
    y_series = y.iloc[:, 0].to_numpy()
    val_idx = np.asarray(val_idx, dtype=int)
    X_val = X.iloc[val_idx]
    y_val = y_series[val_idx]

    bundle_path = run_dir / "model_bundle.joblib"
    if not bundle_path.exists():
        return None
    try:
        bundle = load_bundle(bundle_path)
    except Exception:
        return None
    if not isinstance(bundle, dict):
        return None
    predictor = bundle.get("calibrated_model") or bundle.get("model")
    if predictor is None:
        return None

    if task_type == "classification":
        label_encoder = bundle.get("label_encoder")
        if label_encoder is not None:
            try:
                y_val = label_encoder.transform(y_val)
            except Exception:
                return None
        else:
            try:
                y_val = y_val.astype(int)
            except Exception:
                return None

    y_pred = predictor.predict(X_val)
    y_proba = None
    class_labels = None
    if task_type == "classification" and hasattr(predictor, "predict_proba"):
        y_proba = predictor.predict_proba(X_val)
        labels = bundle.get("class_labels")
        if isinstance(labels, list):
            class_labels = [str(item) for item in labels]
    if task_type == "classification" and y_proba is None:
        return None
    return PredsPayload(
        y_true=y_val,
        y_pred=y_pred,
        y_proba=y_proba,
        class_labels=class_labels,
        source="fallback_rerun",
    )


def _extract_metric_value(metrics_payload: dict[str, Any] | None, metric_name: str) -> float | None:
    if not isinstance(metrics_payload, dict):
        return None
    holdout = metrics_payload.get("holdout")
    if isinstance(holdout, dict) and metric_name in holdout:
        return _to_float(holdout.get(metric_name))
    if isinstance(holdout, dict):
        key = _normalize_str(metric_name)
        if key:
            key = key.lower().replace("-", "_")
            for candidate_key in holdout:
                cand_norm = _normalize_str(candidate_key)
                if cand_norm and cand_norm.lower().replace("-", "_") == key:
                    return _to_float(holdout.get(candidate_key))
    return None


def _extract_model_variant(manifest: dict[str, Any] | None) -> str:
    if isinstance(manifest, dict):
        inputs = manifest.get("inputs")
        if isinstance(inputs, dict):
            variant = _normalize_str(inputs.get("model_variant"))
            if variant:
                return variant
    return "unknown"


def _status_completed(status: str | None) -> bool:
    if not status:
        return True
    key = status.strip().lower()
    return key in ("completed", "closed", "finished", "success")


def _collect_candidates_clearml(
    cfg: Any,
    *,
    preprocess_variant: str,
    selection_metric: str,
    exclude_variants: set[str],
) -> tuple[list[Candidate], list[dict[str, Any]], dict[str, Any]]:
    usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id")) or "unknown"
    grid_run_id = _normalize_str(_cfg_value(cfg, "run.grid_run_id"))
    tags = [f"usecase:{usecase_id}", "process:train_model", f"preprocess:{preprocess_variant}"]
    if grid_run_id:
        tags.append(f"grid:{grid_run_id}")

    skipped: list[dict[str, Any]] = []
    candidates: list[Candidate] = []
    ref_values: dict[str, Any] = {}

    tasks = list_clearml_tasks_by_tags(tags)
    for task in tasks:
        task_id = clearml_task_id(task)
        if not task_id:
            continue
        task_tags = clearml_task_tags(task)
        if "template:true" in task_tags:
            continue
        status = clearml_task_status_from_obj(task)
        if status and not _status_completed(status):
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
        except PlatformAdapterError as exc:
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": "unknown",
                    "reason": "missing_out_json",
                    "details": str(exc),
                }
            )
            continue
        out = _load_json(out_path)
        out_status = _normalize_str(out.get("status"))
        if out_status and not _status_completed(out_status):
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": "unknown",
                    "reason": "status_incomplete",
                    "details": out_status,
                }
            )
            continue
        processed_dataset_id = _normalize_str(out.get("processed_dataset_id"))
        split_hash = _normalize_str(out.get("split_hash"))
        recipe_hash = _normalize_str(out.get("recipe_hash"))
        preprocess_task_id = _normalize_str(out.get("preprocess_task_id"))
        task_type = _normalize_task_type(out.get("task_type"))
        n_classes = _to_int(out.get("n_classes"))
        model_id = _normalize_str(out.get("model_id"))

        manifest = None
        try:
            manifest_path = get_task_artifact_local_copy(cfg, task_id, "manifest.json")
            manifest = _load_json(manifest_path)
        except PlatformAdapterError:
            manifest = None

        model_variant = _extract_model_variant(manifest)
        if model_variant in exclude_variants:
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": model_variant,
                    "reason": "excluded_variant",
                }
            )
            continue

        try:
            metrics_path = get_task_artifact_local_copy(cfg, task_id, "metrics.json")
            metrics_payload = _load_json(metrics_path)
        except PlatformAdapterError as exc:
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": model_variant,
                    "reason": "missing_metrics",
                    "details": str(exc),
                }
            )
            continue
        metric_value = _extract_metric_value(metrics_payload, selection_metric)
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

        try:
            preds_path = get_task_artifact_local_copy(cfg, task_id, "preds_valid.parquet")
            classes_path = None
            try:
                classes_path = get_task_artifact_local_copy(cfg, task_id, "classes.json")
            except PlatformAdapterError:
                classes_path = None
            preds = _load_preds_valid(preds_path, task_type=task_type, classes_path=classes_path)
        except Exception as exc:
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": model_variant,
                    "reason": "preds_invalid",
                    "details": str(exc),
                }
            )
            continue

        try:
            model_bundle_path = get_task_artifact_local_copy(cfg, task_id, "model_bundle.joblib")
        except PlatformAdapterError as exc:
            skipped.append(
                {
                    "train_task_id": task_id,
                    "model_variant": model_variant,
                    "reason": "missing_model_bundle",
                    "details": str(exc),
                }
            )
            continue

        if not ref_values:
            ref_values = {
                "processed_dataset_id": processed_dataset_id,
                "split_hash": split_hash,
                "recipe_hash": recipe_hash,
                "task_type": task_type,
                "n_classes": n_classes,
                "class_labels": preds.class_labels,
                "y_true": preds.y_true,
            }
        else:
            if ref_values.get("processed_dataset_id") and processed_dataset_id != ref_values.get(
                "processed_dataset_id"
            ):
                skipped.append(
                    {
                        "train_task_id": task_id,
                        "model_variant": model_variant,
                        "reason": "preprocess_mismatch",
                        "details": processed_dataset_id or "unknown",
                    }
                )
                continue
            if ref_values.get("split_hash") and split_hash != ref_values.get("split_hash"):
                skipped.append(
                    {
                        "train_task_id": task_id,
                        "model_variant": model_variant,
                        "reason": "split_mismatch",
                        "details": split_hash or "unknown",
                    }
                )
                continue
            if task_type != ref_values.get("task_type"):
                skipped.append(
                    {
                        "train_task_id": task_id,
                        "model_variant": model_variant,
                        "reason": "task_type_mismatch",
                        "details": task_type,
                    }
                )
                continue
            if n_classes is not None and ref_values.get("n_classes") is not None:
                if n_classes != ref_values.get("n_classes"):
                    skipped.append(
                        {
                            "train_task_id": task_id,
                            "model_variant": model_variant,
                            "reason": "classes_mismatch",
                            "details": n_classes,
                        }
                    )
                    continue
            if preds.class_labels and ref_values.get("class_labels") is not None:
                if preds.class_labels != ref_values.get("class_labels"):
                    skipped.append(
                        {
                            "train_task_id": task_id,
                            "model_variant": model_variant,
                            "reason": "classes_mismatch",
                            "details": "label_order",
                        }
                    )
                    continue
            try:
                import numpy as np  # type: ignore

                if not np.array_equal(preds.y_true, ref_values.get("y_true")):
                    skipped.append(
                        {
                            "train_task_id": task_id,
                            "model_variant": model_variant,
                            "reason": "preds_mismatch",
                            "details": "y_true",
                        }
                    )
                    continue
            except Exception:
                pass

        candidates.append(
            Candidate(
                train_task_ref=task_id,
                train_task_id=task_id,
                preprocess_task_id=preprocess_task_id,
                model_id=model_id,
                model_variant=model_variant,
                task_type=task_type,
                n_classes=n_classes,
                processed_dataset_id=processed_dataset_id,
                split_hash=split_hash,
                recipe_hash=recipe_hash,
                metric_value=float(metric_value),
                preds=preds,
                model_bundle_path=model_bundle_path,
            )
        )
    return candidates, skipped, ref_values


def _parse_preprocess_variant_from_run_root(run_root: Path) -> str | None:
    name = run_root.name
    if not name.startswith("train__"):
        return None
    parts = name.split("__")
    if len(parts) < 2:
        return None
    return parts[1] or None


def _collect_candidates_local(
    cfg: Any,
    *,
    preprocess_variant: str,
    selection_metric: str,
    exclude_variants: set[str],
    fallback_rerun_predict: bool,
) -> tuple[list[Candidate], list[dict[str, Any]], dict[str, Any]]:
    skipped: list[dict[str, Any]] = []
    candidates: list[Candidate] = []
    ref_values: dict[str, Any] = {}

    run_root = Path(_cfg_value(cfg, "run.output_dir") or ".").expanduser()
    search_root = run_root.parent if run_root.name.startswith("ensemble__") else run_root
    for out_path in search_root.glob("train__*/03_train_model/out.json"):
        run_dir = out_path.parent
        train_root = run_dir.parent
        parsed_variant = _parse_preprocess_variant_from_run_root(train_root)
        if parsed_variant and parsed_variant != preprocess_variant:
            continue
        out = _load_json(out_path)
        out_status = _normalize_str(out.get("status"))
        if out_status and not _status_completed(out_status):
            skipped.append(
                {
                    "train_task_id": str(run_dir),
                    "model_variant": "unknown",
                    "reason": "status_incomplete",
                    "details": out_status,
                }
            )
            continue
        processed_dataset_id = _normalize_str(out.get("processed_dataset_id"))
        split_hash = _normalize_str(out.get("split_hash"))
        recipe_hash = _normalize_str(out.get("recipe_hash"))
        preprocess_task_id = _normalize_str(out.get("preprocess_task_id"))
        task_type = _normalize_task_type(out.get("task_type"))
        n_classes = _to_int(out.get("n_classes"))
        model_id = _normalize_str(out.get("model_id"))

        manifest = None
        manifest_path = run_dir / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = _load_json(manifest_path)
            except Exception:
                manifest = None

        model_variant = _extract_model_variant(manifest)
        if model_variant in exclude_variants:
            skipped.append(
                {
                    "train_task_id": str(run_dir),
                    "model_variant": model_variant,
                    "reason": "excluded_variant",
                }
            )
            continue

        metrics_path = run_dir / "metrics.json"
        if not metrics_path.exists():
            skipped.append(
                {
                    "train_task_id": str(run_dir),
                    "model_variant": model_variant,
                    "reason": "missing_metrics",
                }
            )
            continue
        metrics_payload = _load_json(metrics_path)
        metric_value = _extract_metric_value(metrics_payload, selection_metric)
        if metric_value is None:
            skipped.append(
                {
                    "train_task_id": str(run_dir),
                    "model_variant": model_variant,
                    "reason": "metric_missing",
                    "details": selection_metric,
                }
            )
            continue

        preds_path = run_dir / "preds_valid.parquet"
        classes_path = run_dir / "classes.json"
        try:
            preds = _load_preds_valid(preds_path, task_type=task_type, classes_path=classes_path)
        except Exception as exc:
            preds = None
            if fallback_rerun_predict:
                preds = _load_preds_fallback(cfg, run_dir=run_dir, task_type=task_type)
            if preds is None:
                skipped.append(
                    {
                        "train_task_id": str(run_dir),
                        "model_variant": model_variant,
                        "reason": "preds_invalid",
                        "details": str(exc),
                    }
                )
                continue

        model_bundle_path = run_dir / "model_bundle.joblib"
        if not model_bundle_path.exists():
            skipped.append(
                {
                    "train_task_id": str(run_dir),
                    "model_variant": model_variant,
                    "reason": "missing_model_bundle",
                }
            )
            continue

        if not ref_values:
            ref_values = {
                "processed_dataset_id": processed_dataset_id,
                "split_hash": split_hash,
                "recipe_hash": recipe_hash,
                "task_type": task_type,
                "n_classes": n_classes,
                "class_labels": preds.class_labels,
                "y_true": preds.y_true,
            }
        else:
            if ref_values.get("processed_dataset_id") and processed_dataset_id != ref_values.get(
                "processed_dataset_id"
            ):
                skipped.append(
                    {
                        "train_task_id": str(run_dir),
                        "model_variant": model_variant,
                        "reason": "preprocess_mismatch",
                        "details": processed_dataset_id or "unknown",
                    }
                )
                continue
            if ref_values.get("split_hash") and split_hash != ref_values.get("split_hash"):
                skipped.append(
                    {
                        "train_task_id": str(run_dir),
                        "model_variant": model_variant,
                        "reason": "split_mismatch",
                        "details": split_hash or "unknown",
                    }
                )
                continue
            if task_type != ref_values.get("task_type"):
                skipped.append(
                    {
                        "train_task_id": str(run_dir),
                        "model_variant": model_variant,
                        "reason": "task_type_mismatch",
                        "details": task_type,
                    }
                )
                continue
            if n_classes is not None and ref_values.get("n_classes") is not None:
                if n_classes != ref_values.get("n_classes"):
                    skipped.append(
                        {
                            "train_task_id": str(run_dir),
                            "model_variant": model_variant,
                            "reason": "classes_mismatch",
                            "details": n_classes,
                        }
                    )
                    continue
            if preds.class_labels and ref_values.get("class_labels") is not None:
                if preds.class_labels != ref_values.get("class_labels"):
                    skipped.append(
                        {
                            "train_task_id": str(run_dir),
                            "model_variant": model_variant,
                            "reason": "classes_mismatch",
                            "details": "label_order",
                        }
                    )
                    continue
            try:
                import numpy as np  # type: ignore

                if not np.array_equal(preds.y_true, ref_values.get("y_true")):
                    skipped.append(
                        {
                            "train_task_id": str(run_dir),
                            "model_variant": model_variant,
                            "reason": "preds_mismatch",
                            "details": "y_true",
                        }
                    )
                    continue
            except Exception:
                pass

        candidates.append(
            Candidate(
                train_task_ref=str(run_dir),
                train_task_id=_normalize_str(out.get("train_task_id")),
                preprocess_task_id=preprocess_task_id,
                model_id=model_id,
                model_variant=model_variant,
                task_type=task_type,
                n_classes=n_classes,
                processed_dataset_id=processed_dataset_id,
                split_hash=split_hash,
                recipe_hash=recipe_hash,
                metric_value=float(metric_value),
                preds=preds,
                model_bundle_path=model_bundle_path,
            )
        )

    return candidates, skipped, ref_values


def _normalize_weights(weights: Iterable[float]) -> list[float] | None:
    values = [float(w) for w in weights]
    total = sum(max(0.0, w) for w in values)
    if total <= 0.0 or not math.isfinite(total):
        return None
    return [max(0.0, w) / total for w in values]


def _score_metric(
    metric_name: str,
    *,
    task_type: str,
    y_true: Any,
    y_pred: Any,
    y_proba: Any | None,
    n_classes: int | None,
    fbeta_beta: float,
) -> float | None:
    try:
        metric_fn = get_metric(metric_name, task_type, n_classes=n_classes, beta=fbeta_beta)
        return float(metric_fn(y_true, y_pred, y_proba))
    except Exception:
        return None


def _random_simplex_search(
    y_true: Any,
    preds: Any,
    *,
    task_type: str,
    metric_name: str,
    direction: str,
    n_classes: int | None,
    n_samples: int,
    seed: int,
    fbeta_beta: float,
) -> tuple[list[float], float | None]:
    import numpy as np  # type: ignore

    rng = np.random.default_rng(seed)
    best_score: float | None = None
    best_weights: list[float] | None = None
    for _ in range(max(n_samples, 1)):
        weights = rng.dirichlet(np.ones(preds.shape[1]))
        if task_type == "classification":
            proba = np.average(preds, axis=1, weights=weights)
            y_pred = np.asarray(proba).argmax(axis=1)
            score = _score_metric(
                metric_name,
                task_type=task_type,
                y_true=y_true,
                y_pred=y_pred,
                y_proba=proba,
                n_classes=n_classes,
                fbeta_beta=fbeta_beta,
            )
        else:
            y_pred = np.average(preds, axis=1, weights=weights)
            score = _score_metric(
                metric_name,
                task_type=task_type,
                y_true=y_true,
                y_pred=y_pred,
                y_proba=None,
                n_classes=n_classes,
                fbeta_beta=fbeta_beta,
            )
        if score is None:
            continue
        if best_score is None:
            best_score = score
            best_weights = list(weights)
        else:
            if direction == "maximize" and score > best_score:
                best_score = score
                best_weights = list(weights)
            if direction == "minimize" and score < best_score:
                best_score = score
                best_weights = list(weights)
    if best_weights is None:
        return [1.0 / preds.shape[1]] * preds.shape[1], None
    return best_weights, best_score


def _estimate_weights_regression(
    y_true: Any,
    preds: Any,
    *,
    search: str,
    n_samples: int,
    seed: int,
    metric_name: str,
    direction: str,
    fbeta_beta: float,
) -> tuple[list[float], dict[str, Any]]:
    import numpy as np  # type: ignore

    search = search or "random_simplex"
    meta: dict[str, Any] = {"search": search, "n_samples": n_samples, "seed": seed}
    if preds.shape[1] == 1:
        return [1.0], meta
    if search == "linear":
        try:
            from sklearn.linear_model import LinearRegression  # type: ignore

            model = LinearRegression(positive=True, fit_intercept=False)
            model.fit(preds, y_true)
            weights = _normalize_weights(model.coef_)
            if weights:
                meta["search"] = "linear"
                return weights, meta
        except Exception:
            pass
        try:
            from sklearn.linear_model import Ridge  # type: ignore

            model = Ridge(alpha=1.0, fit_intercept=False, random_state=seed)
            model.fit(preds, y_true)
            weights = _normalize_weights(model.coef_)
            if weights:
                meta["search"] = "ridge"
                return weights, meta
        except Exception:
            pass
    weights, _ = _random_simplex_search(
        y_true,
        preds,
        task_type="regression",
        metric_name=metric_name,
        direction=direction,
        n_classes=None,
        n_samples=n_samples,
        seed=seed,
        fbeta_beta=fbeta_beta,
    )
    meta["search"] = "random_simplex"
    return weights, meta


def _estimate_weights_classification(
    y_true: Any,
    preds: Any,
    *,
    search: str,
    n_samples: int,
    seed: int,
    metric_name: str,
    direction: str,
    n_classes: int,
    fbeta_beta: float,
) -> tuple[list[float], dict[str, Any]]:
    if preds.shape[1] == 1:
        return [1.0], {"search": "single", "n_samples": n_samples, "seed": seed}
    weights, _ = _random_simplex_search(
        y_true,
        preds,
        task_type="classification",
        metric_name=metric_name,
        direction=direction,
        n_classes=n_classes,
        n_samples=n_samples,
        seed=seed,
        fbeta_beta=fbeta_beta,
    )
    return weights, {"search": "random_simplex", "n_samples": n_samples, "seed": seed}


def _build_meta_model(
    cfg: Any,
    *,
    task_type: str,
    n_classes: int | None,
) -> Any:
    method = _normalize_str(_cfg_value(cfg, "ensemble.stacking.meta_model")) or "ridge"
    seed = _to_int(_cfg_value(cfg, "ensemble.stacking.seed")) or 42
    if task_type == "classification":
        try:
            from sklearn.linear_model import LogisticRegression  # type: ignore
        except Exception as exc:
            raise RuntimeError("scikit-learn is required for stacking meta models.") from exc
        return LogisticRegression(max_iter=1000, multi_class="auto", random_state=seed)
    if method == "elasticnet":
        try:
            from sklearn.linear_model import ElasticNet  # type: ignore
        except Exception as exc:
            raise RuntimeError("scikit-learn is required for stacking meta models.") from exc
        return ElasticNet(random_state=seed)
    try:
        from sklearn.linear_model import Ridge  # type: ignore
    except Exception as exc:
        raise RuntimeError("scikit-learn is required for stacking meta models.") from exc
    return Ridge(random_state=seed)


def _stacking_fit_and_score(
    cfg: Any,
    *,
    X_meta: Any,
    y_true: Any,
    task_type: str,
    n_classes: int | None,
    primary_metric: str,
    fbeta_beta: float,
) -> tuple[Any, float, float | None, Any, Any | None]:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for stacking.") from exc
    try:
        from sklearn.model_selection import KFold, StratifiedKFold  # type: ignore
    except Exception as exc:
        raise RuntimeError("scikit-learn is required for stacking.") from exc

    cv_folds = _to_int(_cfg_value(cfg, "ensemble.stacking.cv_folds")) or 5
    seed = _to_int(_cfg_value(cfg, "ensemble.stacking.seed")) or 42
    scores: list[float] = []
    if task_type == "classification":
        splitter = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
        split_iter = splitter.split(X_meta, y_true)
    else:
        splitter = KFold(n_splits=cv_folds, shuffle=True, random_state=seed)
        split_iter = splitter.split(X_meta)

    for train_idx, val_idx in split_iter:
        model = _build_meta_model(cfg, task_type=task_type, n_classes=n_classes)
        model.fit(X_meta[train_idx], y_true[train_idx])
        if task_type == "classification":
            if not hasattr(model, "predict_proba"):
                raise ValueError("meta model lacks predict_proba.")
            y_proba = model.predict_proba(X_meta[val_idx])
            y_pred = np.asarray(y_proba).argmax(axis=1)
        else:
            y_pred = model.predict(X_meta[val_idx])
            y_proba = None
        score = _score_metric(
            primary_metric,
            task_type=task_type,
            y_true=y_true[val_idx],
            y_pred=y_pred,
            y_proba=y_proba,
            n_classes=n_classes,
            fbeta_beta=fbeta_beta,
        )
        if score is not None:
            scores.append(score)

    if not scores:
        raise ValueError("stacking CV produced no valid scores.")

    cv_score = float(sum(scores) / len(scores))
    meta_model = _build_meta_model(cfg, task_type=task_type, n_classes=n_classes)
    meta_model.fit(X_meta, y_true)
    if task_type == "classification":
        y_proba_full = meta_model.predict_proba(X_meta)
        y_pred_full = np.asarray(y_proba_full).argmax(axis=1)
    else:
        y_pred_full = meta_model.predict(X_meta)
        y_proba_full = None
    fit_score = _score_metric(
        primary_metric,
        task_type=task_type,
        y_true=y_true,
        y_pred=y_pred_full,
        y_proba=y_proba_full,
        n_classes=n_classes,
        fbeta_beta=fbeta_beta,
    )
    return meta_model, cv_score, fit_score, y_pred_full, y_proba_full


def _load_base_models(
    candidates: list[Candidate],
    *,
    skipped: list[dict[str, Any]],
) -> tuple[list[Any], list[Candidate], dict[str, Any] | None]:
    base_models: list[Any] = []
    loaded_candidates: list[Candidate] = []
    preprocess_bundle: dict[str, Any] | None = None
    for cand in candidates:
        try:
            bundle = load_bundle(cand.model_bundle_path)
        except Exception as exc:
            skipped.append(
                {
                    "train_task_id": cand.train_task_ref,
                    "model_variant": cand.model_variant,
                    "reason": "missing_model_bundle",
                    "details": str(exc),
                }
            )
            continue
        if not isinstance(bundle, dict):
            skipped.append(
                {
                    "train_task_id": cand.train_task_ref,
                    "model_variant": cand.model_variant,
                    "reason": "missing_model_bundle",
                    "details": "bundle_not_dict",
                }
            )
            continue
        predictor = bundle.get("calibrated_model") or bundle.get("model")
        if predictor is None:
            skipped.append(
                {
                    "train_task_id": cand.train_task_ref,
                    "model_variant": cand.model_variant,
                    "reason": "missing_model_bundle",
                    "details": "model_missing",
                }
            )
            continue
        base_models.append(predictor)
        loaded_candidates.append(cand)
        if preprocess_bundle is None:
            preprocess = bundle.get("preprocess_bundle")
            if isinstance(preprocess, dict):
                preprocess_bundle = preprocess
    return base_models, loaded_candidates, preprocess_bundle


def _compute_metrics(
    cfg: Any,
    *,
    y_true: Any,
    y_pred: Any,
    y_proba: Any | None,
    task_type: str,
    n_classes: int | None,
    primary_metric: str,
) -> tuple[dict[str, Any], float]:
    metrics_holdout: dict[str, Any] = {}
    if task_type == "classification":
        mode = _resolve_classification_mode(cfg, n_classes=int(n_classes or 2))
        metric_names = _resolve_classification_metrics(
            cfg,
            classification_mode=mode,
            n_classes=n_classes,
            imbalance_enabled=bool(_cfg_value(cfg, "eval.imbalance.enabled", False)),
        )
        fbeta_beta = float(_cfg_value(cfg, "eval.metrics.fbeta_beta", 1.0) or 1.0)
        for name in metric_names:
            if metric_requires_proba(name, task_type) and y_proba is None:
                continue
            score = _score_metric(
                name,
                task_type=task_type,
                y_true=y_true,
                y_pred=y_pred,
                y_proba=y_proba,
                n_classes=n_classes,
                fbeta_beta=fbeta_beta,
            )
            if score is not None:
                metrics_holdout[name] = score
        if primary_metric not in metrics_holdout:
            score = _score_metric(
                primary_metric,
                task_type=task_type,
                y_true=y_true,
                y_pred=y_pred,
                y_proba=y_proba,
                n_classes=n_classes,
                fbeta_beta=fbeta_beta,
            )
            if score is not None:
                metrics_holdout[primary_metric] = score
    else:
        metric_names = _resolve_metric_list(cfg)
        metrics_holdout = compute_regression_metrics(y_true, y_pred, metrics=metric_names)
        if primary_metric not in metrics_holdout:
            score = _score_metric(
                primary_metric,
                task_type=task_type,
                y_true=y_true,
                y_pred=y_pred,
                y_proba=None,
                n_classes=n_classes,
                fbeta_beta=float(_cfg_value(cfg, "eval.metrics.fbeta_beta", 1.0) or 1.0),
            )
            if score is not None:
                metrics_holdout[primary_metric] = score
    if primary_metric not in metrics_holdout:
        raise ValueError(f"primary_metric '{primary_metric}' missing from metrics.")
    metrics_holdout["val_rows"] = int(len(y_true))
    return metrics_holdout, float(metrics_holdout[primary_metric])


def _record_failure(
    *,
    ctx: Any,
    cfg: Any,
    reason: str,
    ref_values: Mapping[str, Any],
    skipped: list[dict[str, Any]],
) -> None:
    task_id = None
    if getattr(ctx, "task", None) is not None:
        task_id = getattr(ctx.task, "id", None)
        if task_id:
            task_id = str(task_id)
    out = {
        "processed_dataset_id": ref_values.get("processed_dataset_id"),
        "split_hash": ref_values.get("split_hash"),
        "recipe_hash": ref_values.get("recipe_hash"),
        "train_task_id": task_id,
        "model_id": None,
        "best_score": None,
        "primary_metric": _resolve_primary_metric(cfg),
        "task_type": ref_values.get("task_type"),
        "status": "failed",
        "reason": reason,
    }
    if ref_values.get("n_classes") is not None:
        out["n_classes"] = ref_values.get("n_classes")
    write_out_json(ctx, out)

    versions = resolve_version_props(cfg, clearml_enabled=is_clearml_enabled(cfg))
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "train_ensemble",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "preprocess_variant": _resolve_preprocess_variant(cfg),
            "method": _normalize_str(_cfg_value(cfg, "ensemble.method")),
        },
        "outputs": {
            "model_id": None,
            "best_score": None,
            "primary_metric": _resolve_primary_metric(cfg),
            "task_type": ref_values.get("task_type"),
        },
        "hashes": {
            "config_hash": hash_config(cfg),
            "split_hash": ref_values.get("split_hash"),
            "recipe_hash": ref_values.get("recipe_hash"),
        },
        "error": {"type": "no_valid_base_models", "message": reason},
    }
    write_manifest(ctx, manifest)

    if skipped:
        spec_path = ctx.output_dir / "ensemble_spec.json"
        spec = {
            "method": _normalize_str(_cfg_value(cfg, "ensemble.method")) or "unknown",
            "selection_metric": _resolve_selection_metric(cfg),
            "direction": metric_direction(_resolve_selection_metric(cfg), ref_values.get("task_type") or "regression"),
            "top_k": _resolve_top_k(cfg),
            "preprocess_variant": _resolve_preprocess_variant(cfg),
            "included": [],
            "skipped": skipped,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "code_version": versions.get("code_version", "unknown"),
            "schema_version": versions.get("schema_version", "unknown"),
        }
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        if is_clearml_enabled(cfg):
            upload_artifact(ctx, "ensemble_spec.json", spec_path)


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
    selection_metric = _resolve_selection_metric(cfg)
    primary_metric = _resolve_primary_metric(cfg)
    method = _normalize_str(_cfg_value(cfg, "ensemble.method")) or "mean_topk"
    top_k = _resolve_top_k(cfg)
    exclude_variants = set(_to_list(_cfg_value(cfg, "ensemble.exclude_variants")))
    fallback_rerun_predict = bool(_cfg_value(cfg, "ensemble.fallback_rerun_predict", False))

    if clearml_enabled:
        candidates, skipped, ref_values = _collect_candidates_clearml(
            cfg,
            preprocess_variant=preprocess_variant,
            selection_metric=selection_metric,
            exclude_variants=exclude_variants,
        )
    else:
        candidates, skipped, ref_values = _collect_candidates_local(
            cfg,
            preprocess_variant=preprocess_variant,
            selection_metric=selection_metric,
            exclude_variants=exclude_variants,
            fallback_rerun_predict=fallback_rerun_predict,
        )

    if not candidates:
        _record_failure(
            ctx=ctx,
            cfg=cfg,
            reason="no_valid_base_models",
            ref_values=ref_values,
            skipped=skipped,
        )
        return

    task_type = candidates[0].task_type
    n_classes = candidates[0].n_classes
    selection_direction = metric_direction(selection_metric, task_type)
    sorted_candidates = sorted(
        candidates, key=lambda c: c.metric_value, reverse=(selection_direction == "maximize")
    )
    if top_k <= 0:
        top_k = len(sorted_candidates)

    if method == "weighted":
        top_k_max = _to_int(_cfg_value(cfg, "ensemble.weighted.top_k_max")) or top_k
        top_k = min(top_k, top_k_max)

    selected = sorted_candidates[: max(top_k, 1)]
    base_models, loaded_candidates, preprocess_bundle = _load_base_models(selected, skipped=skipped)
    if not base_models:
        _record_failure(
            ctx=ctx,
            cfg=cfg,
            reason="no_valid_base_models",
            ref_values=ref_values,
            skipped=skipped,
        )
        return

    if preprocess_bundle is None:
        raise ValueError("preprocess_bundle is missing from base model bundle.")

    selected = loaded_candidates
    if not selected:
        _record_failure(
            ctx=ctx,
            cfg=cfg,
            reason="no_valid_base_models",
            ref_values=ref_values,
            skipped=skipped,
        )
        return

    try:
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("numpy is required for train_ensemble.") from exc

    y_true = np.asarray(selected[0].preds.y_true)
    primary_direction = metric_direction(primary_metric, task_type)
    fbeta_beta = float(_cfg_value(cfg, "eval.metrics.fbeta_beta", 1.0) or 1.0)
    primary_metric_source = "valid"
    weights: list[float] | None = None
    ensemble_meta: dict[str, Any] = {}
    method_used = method
    y_proba: Any | None = None

    if task_type == "classification":
        proba_stack = np.stack([np.asarray(c.preds.y_proba) for c in selected], axis=1)
        if method == "stacking":
            try:
                if bool(_cfg_value(cfg, "ensemble.stacking.require_test_split")):
                    raise ValueError("stacking require_test_split is enabled but test split is unavailable.")
                meta_model, cv_score, fit_score, y_pred, y_proba = _stacking_fit_and_score(
                    cfg,
                    X_meta=np.hstack([np.asarray(c.preds.y_proba) for c in selected]),
                    y_true=y_true,
                    task_type=task_type,
                    n_classes=n_classes,
                    primary_metric=primary_metric,
                    fbeta_beta=fbeta_beta,
                )
                primary_metric_source = "meta_cv_on_valid"
                ensemble_meta.update(
                    {
                        "meta_model": _normalize_str(_cfg_value(cfg, "ensemble.stacking.meta_model"))
                        or "ridge",
                        "primary_metric_source": primary_metric_source,
                        "meta_training_protocol": {
                            "cv_folds": _to_int(_cfg_value(cfg, "ensemble.stacking.cv_folds")) or 5,
                        },
                        "fit_score_on_valid": fit_score,
                    }
                )
                ensemble_model = EnsemblePredictor(
                    task_type=task_type,
                    method=method,
                    base_models=base_models,
                    meta_model=meta_model,
                    n_classes=n_classes,
                )
                metrics_holdout, fit_score = _compute_metrics(
                    cfg,
                    y_true=y_true,
                    y_pred=y_pred,
                    y_proba=y_proba,
                    task_type=task_type,
                    n_classes=n_classes,
                    primary_metric=primary_metric,
                )
                metrics_holdout[primary_metric] = cv_score
                best_score = cv_score
                ensemble_meta["cv_score"] = cv_score
            except Exception as exc:
                warnings.warn(f"stacking failed; degraded to mean_topk: {exc}")
                method_used = "mean_topk"
                ensemble_meta["degraded_to"] = "mean_topk"
                primary_metric_source = "valid"
                weights = [1.0 / proba_stack.shape[1]] * proba_stack.shape[1]
                y_proba = np.average(proba_stack, axis=1, weights=weights)
                y_pred = np.asarray(y_proba).argmax(axis=1)
                ensemble_model = EnsemblePredictor(
                    task_type=task_type,
                    method=method_used,
                    base_models=base_models,
                    weights=weights,
                    n_classes=n_classes,
                )
                metrics_holdout, best_score = _compute_metrics(
                    cfg,
                    y_true=y_true,
                    y_pred=y_pred,
                    y_proba=y_proba,
                    task_type=task_type,
                    n_classes=n_classes,
                    primary_metric=primary_metric,
                )
        else:
            if method == "weighted":
                search = _normalize_str(_cfg_value(cfg, "ensemble.weighted.search")) or "random_simplex"
                n_samples = _to_int(_cfg_value(cfg, "ensemble.weighted.n_samples")) or 1500
                seed = _to_int(_cfg_value(cfg, "ensemble.weighted.seed")) or 42
                weights, meta = _estimate_weights_classification(
                    y_true,
                    proba_stack,
                    search=search,
                    n_samples=n_samples,
                    seed=seed,
                    metric_name=primary_metric,
                    direction=primary_direction,
                    n_classes=int(n_classes or 2),
                    fbeta_beta=fbeta_beta,
                )
                ensemble_meta.update(meta)
                ensemble_meta["objective_metric"] = primary_metric
                ensemble_meta["objective_direction"] = primary_direction
            else:
                weights = [1.0 / proba_stack.shape[1]] * proba_stack.shape[1]
            y_proba = np.average(proba_stack, axis=1, weights=weights)
            y_pred = np.asarray(y_proba).argmax(axis=1)
            ensemble_model = EnsemblePredictor(
                task_type=task_type,
                method=method_used,
                base_models=base_models,
                weights=weights,
                n_classes=n_classes,
            )
            metrics_holdout, best_score = _compute_metrics(
                cfg,
                y_true=y_true,
                y_pred=y_pred,
                y_proba=y_proba,
                task_type=task_type,
                n_classes=n_classes,
                primary_metric=primary_metric,
            )
    else:
        preds_stack = np.column_stack([np.asarray(c.preds.y_pred).reshape(-1) for c in selected])
        if method == "stacking":
            try:
                if bool(_cfg_value(cfg, "ensemble.stacking.require_test_split")):
                    raise ValueError("stacking require_test_split is enabled but test split is unavailable.")
                meta_model, cv_score, fit_score, y_pred, y_proba = _stacking_fit_and_score(
                    cfg,
                    X_meta=preds_stack,
                    y_true=y_true,
                    task_type=task_type,
                    n_classes=None,
                    primary_metric=primary_metric,
                    fbeta_beta=fbeta_beta,
                )
                primary_metric_source = "meta_cv_on_valid"
                ensemble_meta.update(
                    {
                        "meta_model": _normalize_str(_cfg_value(cfg, "ensemble.stacking.meta_model"))
                        or "ridge",
                        "primary_metric_source": primary_metric_source,
                        "meta_training_protocol": {
                            "cv_folds": _to_int(_cfg_value(cfg, "ensemble.stacking.cv_folds")) or 5,
                        },
                        "fit_score_on_valid": fit_score,
                    }
                )
                ensemble_model = EnsemblePredictor(
                    task_type=task_type,
                    method=method,
                    base_models=base_models,
                    meta_model=meta_model,
                )
                metrics_holdout, fit_score = _compute_metrics(
                    cfg,
                    y_true=y_true,
                    y_pred=y_pred,
                    y_proba=None,
                    task_type=task_type,
                    n_classes=None,
                    primary_metric=primary_metric,
                )
                metrics_holdout[primary_metric] = cv_score
                best_score = cv_score
                ensemble_meta["cv_score"] = cv_score
            except Exception as exc:
                warnings.warn(f"stacking failed; degraded to mean_topk: {exc}")
                method_used = "mean_topk"
                ensemble_meta["degraded_to"] = "mean_topk"
                primary_metric_source = "valid"
                weights = [1.0 / preds_stack.shape[1]] * preds_stack.shape[1]
                y_pred = np.average(preds_stack, axis=1, weights=weights)
                ensemble_model = EnsemblePredictor(
                    task_type=task_type,
                    method=method_used,
                    base_models=base_models,
                    weights=weights,
                )
                metrics_holdout, best_score = _compute_metrics(
                    cfg,
                    y_true=y_true,
                    y_pred=y_pred,
                    y_proba=None,
                    task_type=task_type,
                    n_classes=None,
                    primary_metric=primary_metric,
                )
        else:
            if method == "weighted":
                search = _normalize_str(_cfg_value(cfg, "ensemble.weighted.search")) or "random_simplex"
                n_samples = _to_int(_cfg_value(cfg, "ensemble.weighted.n_samples")) or 1500
                seed = _to_int(_cfg_value(cfg, "ensemble.weighted.seed")) or 42
                weights, meta = _estimate_weights_regression(
                    y_true,
                    preds_stack,
                    search=search,
                    n_samples=n_samples,
                    seed=seed,
                    metric_name=primary_metric,
                    direction=primary_direction,
                    fbeta_beta=fbeta_beta,
                )
                ensemble_meta.update(meta)
                ensemble_meta["objective_metric"] = primary_metric
                ensemble_meta["objective_direction"] = primary_direction
            else:
                weights = [1.0 / preds_stack.shape[1]] * preds_stack.shape[1]
            y_pred = np.average(preds_stack, axis=1, weights=weights)
            ensemble_model = EnsemblePredictor(
                task_type=task_type,
                method=method_used,
                base_models=base_models,
                weights=weights,
            )
            metrics_holdout, best_score = _compute_metrics(
                cfg,
                y_true=y_true,
                y_pred=y_pred,
                y_proba=None,
                task_type=task_type,
                n_classes=None,
                primary_metric=primary_metric,
            )

    viz_settings = _resolve_viz_settings(cfg)
    class_names = (
        selected[0].preds.class_labels if task_type == "classification" else None
    )
    debug_sample = None
    residuals_plot_path: Path | None = None
    confusion_plot_path: Path | None = None
    roc_plot_path: Path | None = None
    if clearml_enabled:
        debug_sample = _build_prediction_sample(y_true, y_pred, y_proba)
        if viz_settings["enabled"]:
            if task_type == "regression":
                residuals_plot_path = plot_regression_residuals(
                    y_true,
                    y_pred,
                    ctx.output_dir / "residuals.png",
                    max_points=viz_settings["max_points"],
                )
            else:
                confusion_plot_path = plot_confusion_matrix(
                    y_true,
                    y_pred,
                    ctx.output_dir / "confusion_matrix.png",
                    class_names=class_names,
                    normalize=viz_settings["confusion_normalize"],
                )
                if viz_settings["roc_curve"] and n_classes == 2 and y_proba is not None:
                    roc_plot_path = plot_roc_curve(
                        y_true,
                        y_proba[:, 1],
                        ctx.output_dir / "roc_curve.png",
                    )

    included = [
        {
            "train_task_id": c.train_task_id or c.train_task_ref,
            "model_variant": c.model_variant,
            "metric_value": c.metric_value,
            "preds_ref": c.preds.source,
        }
        for c in selected
    ]

    task_id = None
    if getattr(ctx, "task", None) is not None:
        task_id = getattr(ctx.task, "id", None)
        if task_id:
            task_id = str(task_id)

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    ensemble_spec = {
        "method": method_used,
        "selection_metric": selection_metric,
        "direction": selection_direction,
        "top_k": top_k,
        "preprocess_variant": preprocess_variant,
        "primary_metric": primary_metric,
        "primary_metric_source": primary_metric_source,
        "n_base_models": len(included),
        "included": included,
        "skipped": skipped,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_version": versions.get("code_version", "unknown"),
        "schema_version": versions.get("schema_version", "unknown"),
    }
    if method_used != method:
        ensemble_spec["configured_method"] = method
    if weights is not None:
        ensemble_spec["weights"] = {
            (c.train_task_id or c.train_task_ref): float(weights[i]) for i, c in enumerate(selected)
        }
    ensemble_spec.update(ensemble_meta)
    spec_path = ctx.output_dir / "ensemble_spec.json"
    spec_path.write_text(json.dumps(ensemble_spec, ensure_ascii=False, indent=2), encoding="utf-8")

    metrics_payload = {
        "primary_metric": primary_metric,
        "direction": primary_direction,
        "task_type": task_type,
        "primary_metric_source": primary_metric_source,
        "holdout": metrics_holdout,
    }
    metrics_path = ctx.output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    ensemble_payload = {
        "method": method_used,
        "base_train_task_ids": [c.train_task_id or c.train_task_ref for c in selected],
        "weights": weights,
        "primary_metric_source": primary_metric_source,
    }
    if method_used != method:
        ensemble_payload["configured_method"] = method
    model_bundle = {
        "model": ensemble_model,
        "model_variant": f"ensemble_{method_used}",
        "primary_metric": primary_metric,
        "best_score": best_score,
        "metrics": metrics_payload,
        "preprocess_bundle": preprocess_bundle,
        "processed_dataset_id": ref_values.get("processed_dataset_id"),
        "split_hash": ref_values.get("split_hash"),
        "recipe_hash": ref_values.get("recipe_hash"),
        "task_type": task_type,
        "n_classes": n_classes,
        "ensemble": ensemble_payload,
        "provenance": {
            "train_task_id": task_id,
            "processed_dataset_id": ref_values.get("processed_dataset_id"),
            "preprocess_variant": preprocess_variant,
        },
    }
    model_bundle_path = ctx.output_dir / "model_bundle.joblib"
    save_bundle(model_bundle_path, model_bundle)
    model_id = str(model_bundle_path)

    pipeline_task_id = _normalize_str(_cfg_value(cfg, "run.clearml.pipeline_task_id"))
    train_task_ids = [
        c.train_task_id or c.train_task_ref for c in selected if c.train_task_id or c.train_task_ref
    ]
    preprocess_task_ids = sorted(
        {
            c.preprocess_task_id
            for c in selected
            if c.preprocess_task_id is not None and str(c.preprocess_task_id).strip()
        }
    )
    train_task_tag_limit = _to_int(_cfg_value(cfg, "train_ensemble.registry.tag_limits.train_task_ids"))
    train_task_ids_tagged = train_task_ids
    train_task_truncated = False
    if train_task_tag_limit and train_task_tag_limit > 0 and len(train_task_ids) > train_task_tag_limit:
        train_task_ids_tagged = train_task_ids[:train_task_tag_limit]
        train_task_truncated = True
    full_ids_to_metadata = _normalize_bool(
        _cfg_value(cfg, "train_ensemble.registry.metadata.full_train_task_ids"), True
    )
    ensemble_variant = f"ensemble_{method_used}"
    registry_model_id: str | None = None
    registry_status: str | None = None
    registry_error: dict[str, Any] | None = None
    if clearml_enabled:
        usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id")) or "unknown"
        model_name = f"{usecase_id}:{ensemble_variant}:{ref_values.get('processed_dataset_id')}"
        metadata: dict[str, Any] | None = None
        if full_ids_to_metadata:
            metadata = {
                "train_task_ids_full": train_task_ids,
                "preprocess_task_ids_full": preprocess_task_ids,
                "pipeline_task_id": pipeline_task_id,
                "train_task_ids_tag_limit": train_task_tag_limit,
                "train_task_ids_truncated": train_task_truncated,
            }
        tags = _build_registry_tags(
            usecase_id=usecase_id,
            process="train_ensemble",
            processed_dataset_id=str(ref_values.get("processed_dataset_id")),
            split_hash=str(ref_values.get("split_hash")),
            recipe_hash=str(ref_values.get("recipe_hash")),
            preprocess_variant=preprocess_variant,
            model_variant=ensemble_variant,
            task_type=task_type,
            train_ensemble_task_id=task_id,
            train_task_ids=train_task_ids_tagged,
            preprocess_task_ids=preprocess_task_ids,
            pipeline_task_id=pipeline_task_id,
        )
        if train_task_ids:
            tags.append(f"task:train_model_count:{len(train_task_ids)}")
        if train_task_truncated:
            tags.append("task:train_model_truncated:true")
        tags = _dedupe_tags(tags)
        try:
            registry_model_id = register_model_artifact(
                ctx,
                model_path=model_bundle_path,
                model_name=model_name,
                tags=tags,
                metadata=metadata,
            )
            registry_status = "registered"
        except Exception as exc:
            registry_status = "failed"
            registry_error = {"type": exc.__class__.__name__, "message": str(exc)}
            warnings.warn(f"Failed to register ensemble model in ClearML registry: {exc}")

    connect_train_ensemble(
        ctx,
        cfg,
        processed_dataset_id=ref_values.get("processed_dataset_id"),
        task_type=task_type,
        primary_metric=primary_metric,
        method=method,
        top_k=top_k,
    )

    if clearml_enabled:
        upload_artifact(ctx, "ensemble_spec.json", spec_path)
        upload_artifact(ctx, "metrics.json", metrics_path)
        upload_artifact(ctx, "model_bundle.joblib", model_bundle_path)
        props = {
            "processed_dataset_id": ref_values.get("processed_dataset_id"),
            "split_hash": ref_values.get("split_hash"),
            "model_id": model_id,
            "primary_metric": primary_metric,
            "best_score": best_score,
            "task_type": task_type,
            "n_classes": n_classes,
        }
        if registry_model_id:
            props["registry_model_id"] = registry_model_id
        if registry_status:
            props["registry_status"] = registry_status
        update_task_properties(ctx, props)
        if task_type == "regression":
            for name in REGRESSION_METRIC_ORDER:
                if name in metrics_holdout:
                    log_scalar(ctx.task, "metrics", name, metrics_holdout[name], step=0)
        log_scalar(ctx.task, "ensemble", "best_score", best_score, step=0)
        log_scalar(ctx.task, "ensemble", "n_included", len(included), step=0)
        log_scalar(ctx.task, "ensemble", "n_skipped", len(skipped), step=0)
        log_scalar(ctx.task, "metrics", primary_metric, best_score, step=0)
        log_debug_table(ctx.task, "ensemble", "included", included, step=0)
        if skipped:
            log_debug_table(ctx.task, "ensemble", "skipped", skipped, step=0)
        if weights is not None:
            weights_table = [
                {
                    "train_task_id": c.train_task_id or c.train_task_ref,
                    "model_variant": c.model_variant,
                    "weight": float(weights[i]),
                }
                for i, c in enumerate(selected)
            ]
            log_debug_table(ctx.task, "ensemble", "weights", weights_table, step=0)
        if debug_sample is not None:
            log_debug_table(ctx.task, "train_ensemble", "prediction_sample", debug_sample, step=0)
        if viz_settings["enabled"]:
            if task_type == "regression":
                numeric_metrics = {
                    key: float(value)
                    for key, value in metrics_holdout.items()
                    if isinstance(value, (int, float)) and math.isfinite(float(value))
                }
                metrics_table = build_regression_metrics_table(numeric_metrics)
                log_plotly(ctx.task, "train_ensemble", "metrics_table", metrics_table, step=0)
                scatter = build_true_pred_scatter(
                    y_true,
                    y_pred,
                    r2=metrics_holdout.get("r2"),
                    max_points=viz_settings["max_points"],
                )
                log_plotly(ctx.task, "train_ensemble", "true_vs_pred", scatter, step=0)
                fig = build_residuals_plot(
                    y_true,
                    y_pred,
                    max_points=viz_settings["max_points"],
                )
                log_plotly(
                    ctx.task,
                    "train_ensemble",
                    "residuals",
                    fig or residuals_plot_path,
                    step=0,
                )
            else:
                fig = _build_plotly_confusion_matrix(
                    y_true,
                    y_pred,
                    class_names=class_names,
                    normalize=viz_settings["confusion_normalize"],
                )
                log_plotly(
                    ctx.task,
                    "train_ensemble",
                    "confusion_matrix",
                    fig or confusion_plot_path,
                    step=0,
                )
                if y_proba is not None and n_classes == 2:
                    fig = _build_plotly_roc_curve(y_true, y_proba[:, 1])
                    log_plotly(
                        ctx.task,
                        "train_ensemble",
                        "roc_curve",
                        fig or roc_plot_path,
                        step=0,
                    )

    out = {
        "processed_dataset_id": ref_values.get("processed_dataset_id"),
        "split_hash": ref_values.get("split_hash"),
        "recipe_hash": ref_values.get("recipe_hash"),
        "train_task_id": task_id,
        "pipeline_task_id": pipeline_task_id,
        "preprocess_task_ids": preprocess_task_ids,
        "base_train_task_ids": train_task_ids,
        "model_id": model_id,
        "best_score": best_score,
        "primary_metric": primary_metric,
        "task_type": task_type,
        "primary_metric_source": primary_metric_source,
    }
    if registry_model_id:
        out["registry_model_id"] = registry_model_id
    if registry_status:
        out["registry_status"] = registry_status
    if registry_error:
        out["registry_error"] = registry_error
    if n_classes is not None:
        out["n_classes"] = n_classes
    write_out_json(ctx, out)

    inputs = {
        "preprocess_variant": preprocess_variant,
        "method": method,
        "top_k": top_k,
        "selection_metric": selection_metric,
        "primary_metric": primary_metric,
        "direction": primary_direction,
    }
    outputs = {
        "model_id": model_id,
        "best_score": best_score,
        "primary_metric": primary_metric,
        "task_type": task_type,
        "primary_metric_source": primary_metric_source,
    }
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "train_ensemble",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
        "outputs": outputs,
        "hashes": {
            "config_hash": hash_config(cfg),
            "split_hash": ref_values.get("split_hash"),
            "recipe_hash": ref_values.get("recipe_hash"),
        },
    }
    write_manifest(ctx, manifest)
