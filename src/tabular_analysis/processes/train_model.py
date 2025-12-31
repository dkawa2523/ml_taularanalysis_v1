"""train_model process.

- processed dataset + fixed split を入力
- model_variant を選択して学習
- model_bundle（model + preprocess bundle + schema）を保存
- primary_metric を計算し、properties に best_score を入れる
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from ..io.bundle_io import load_bundle, save_bundle
from ..platform_adapter import (
    get_dataset_local_copy,
    hash_config,
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
from ..registry.metrics import get_metric
from ..registry.models import build_model

_TABULAR_SUFFIXES = (".csv", ".parquet", ".pq")


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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
    return resolve_output_dir(cfg, "02_preprocess")


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


def _write_feature_importance(model: Any, feature_names: list[str], output_dir: Path) -> Path | None:
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
    if len(feature_names) != len(importance_arr):
        return None

    pairs = sorted(zip(feature_names, importance_arr.tolist()), key=lambda x: x[1], reverse=True)
    lines = ["feature,importance"]
    for name, score in pairs:
        lines.append(f"{name},{float(score)}")
    path = output_dir / "feature_importance.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(cfg: Any) -> None:
    _ensure_variant_cfg(cfg)
    ctx = init_task_context(cfg, stage=cfg.task.stage, task_name="train_model")
    save_config_resolved(ctx, cfg)
    clearml_enabled = is_clearml_enabled(cfg)

    processed_ref = _normalize_str(getattr(getattr(cfg, "data", None), "processed_dataset_id", None))
    processed_ref_path: Path | None = None
    if processed_ref:
        candidate = Path(processed_ref).expanduser()
        if candidate.exists():
            processed_ref_path = candidate.resolve()

    preprocess_run_dir = _resolve_preprocess_run_dir(cfg, processed_ref_path)
    if not preprocess_run_dir.exists():
        raise FileNotFoundError(f"preprocess_run_dir not found: {preprocess_run_dir}")

    preprocess_out_path = preprocess_run_dir / "out.json"
    if not preprocess_out_path.exists():
        raise FileNotFoundError(f"preprocess out.json not found: {preprocess_out_path}")

    preprocess_out = _load_json(preprocess_out_path)
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

    split_path = preprocess_run_dir / "split.json"
    if not split_path.exists():
        raise FileNotFoundError(f"split.json not found: {split_path}")
    split_payload = _load_json(split_path)
    train_idx = _normalize_indices(split_payload.get("train_index"), label="train_index")
    val_idx = _normalize_indices(split_payload.get("val_index"), label="val_index")

    bundle_path = preprocess_run_dir / "preprocess_bundle.joblib"
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
    if processed_dataset_path is None:
        out_path_value = _normalize_str(preprocess_out.get("processed_dataset_path"))
        if out_path_value:
            candidate = Path(out_path_value).expanduser()
            if candidate.exists():
                processed_dataset_path = candidate.resolve()
    if processed_dataset_path is None:
        candidate = preprocess_run_dir / "processed_dataset.parquet"
        if candidate.exists():
            processed_dataset_path = candidate
    if processed_dataset_path is None and clearml_enabled and not processed_dataset_id.startswith("local:"):
        local_copy = get_dataset_local_copy(cfg, processed_dataset_id)
        processed_dataset_path = _select_tabular_file(local_copy)
    if processed_dataset_path is None:
        raise FileNotFoundError("processed_dataset.parquet not found; specify preprocess_run_dir.")

    df = _load_dataframe(processed_dataset_path)

    bundle_columns = {}
    if isinstance(preprocess_bundle, dict):
        bundle_columns = preprocess_bundle.get("columns", {}) or {}
    target_column = _normalize_str(bundle_columns.get("target_column")) or _normalize_str(
        getattr(getattr(cfg, "data", None), "target_column", None)
    )
    if not target_column or target_column not in df.columns:
        raise ValueError(f"target_column not found in processed dataset: {target_column}")

    feature_names = None
    if isinstance(preprocess_bundle, dict):
        feature_names = preprocess_bundle.get("feature_names")
    if feature_names and all(name in df.columns for name in feature_names):
        X = df[feature_names]
    else:
        X = df.drop(columns=[target_column])
        feature_names = list(X.columns)
    y = df[target_column].to_numpy()

    if not train_idx or not val_idx:
        raise ValueError("split.json must include non-empty train_index and val_index.")

    X_train = X.iloc[train_idx]
    y_train = y[train_idx]
    X_val = X.iloc[val_idx]
    y_val = y[val_idx]

    model_variant = _merge_model_variant(cfg)
    model_variant_name = _normalize_str(model_variant.get("name")) or "unknown"

    model = build_model(model_variant)
    model.fit(X_train, y_train)

    primary_metric = (
        _normalize_str(getattr(getattr(cfg, "eval", None), "primary_metric", None)) or "rmse"
    ).lower()
    direction = (
        _normalize_str(getattr(getattr(cfg, "eval", None), "direction", None)) or "minimize"
    ).lower()

    metric_names = ["rmse", "mae", "r2"]
    metrics_holdout: dict[str, float] = {}
    y_val_pred = model.predict(X_val)
    for name in metric_names:
        metric_fn = get_metric(name)
        metrics_holdout[name] = float(metric_fn(y_val, y_val_pred))

    if primary_metric not in metrics_holdout:
        metrics_holdout[primary_metric] = float(get_metric(primary_metric)(y_val, y_val_pred))
    best_score = metrics_holdout[primary_metric]

    cv_folds = int(getattr(getattr(cfg, "eval", None), "cv_folds", 0) or 0)
    cv_seed = int(getattr(getattr(cfg, "eval", None), "seed", 42) or 42)
    cv_summary: dict[str, Any] | None = None
    if cv_folds and cv_folds > 1:
        if len(train_idx) < cv_folds:
            raise ValueError("eval.cv_folds is larger than the training split size.")
        try:
            import numpy as np  # type: ignore
            from sklearn.model_selection import KFold  # type: ignore
        except Exception as exc:
            raise RuntimeError("scikit-learn is required for cross-validation.") from exc

        kf = KFold(n_splits=cv_folds, shuffle=True, random_state=cv_seed)
        scores: list[float] = []
        metric_fn = get_metric(primary_metric)
        X_train_full = X.iloc[train_idx]
        y_train_full = y[train_idx]
        for fold_train_idx, fold_val_idx in kf.split(X_train_full):
            fold_model = build_model(model_variant)
            fold_model.fit(X_train_full.iloc[fold_train_idx], y_train_full[fold_train_idx])
            fold_pred = fold_model.predict(X_train_full.iloc[fold_val_idx])
            scores.append(float(metric_fn(y_train_full[fold_val_idx], fold_pred)))
        cv_summary = {
            "folds": cv_folds,
            "seed": cv_seed,
            "scores": scores,
            "mean": float(np.mean(scores)) if scores else None,
            "std": float(np.std(scores)) if scores else None,
        }

    metrics_payload: dict[str, Any] = {
        "primary_metric": primary_metric,
        "direction": direction,
        "holdout": {
            **metrics_holdout,
            "train_rows": int(len(train_idx)),
            "val_rows": int(len(val_idx)),
        },
    }
    if cv_summary is not None:
        metrics_payload["cv"] = cv_summary

    metrics_path = ctx.output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    model_bundle = {
        "model": model,
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
    }
    model_bundle_path = ctx.output_dir / "model_bundle.joblib"
    save_bundle(model_bundle_path, model_bundle)

    feature_importance_path = _write_feature_importance(model, feature_names, ctx.output_dir)

    model_id = str(model_bundle_path)
    train_task_id = _resolve_task_id(ctx)

    if clearml_enabled:
        upload_artifact(ctx, "metrics.json", metrics_path)
        upload_artifact(ctx, "model_bundle.joblib", model_bundle_path)
        if feature_importance_path is not None:
            upload_artifact(ctx, feature_importance_path.name, feature_importance_path)
        update_task_properties(
            ctx,
            {
                "processed_dataset_id": processed_dataset_id,
                "split_hash": split_hash,
                "model_id": model_id,
                "primary_metric": primary_metric,
                "best_score": best_score,
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
    }
    write_out_json(ctx, out)

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
    }
    outputs = {
        "model_id": model_id,
        "best_score": best_score,
        "primary_metric": primary_metric,
    }
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
