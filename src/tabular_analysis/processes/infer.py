"""infer process."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import math
import numbers
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..io.bundle_io import load_bundle
from ..platform_adapter import (
    PlatformAdapterError,
    get_task_artifact_local_copy,
    hash_config,
    init_task_context,
    is_clearml_enabled,
    resolve_version_props,
    save_config_resolved,
    upload_artifact,
    write_manifest,
    write_out_json,
)

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


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _prepare_inputs(cfg: Any, preprocess_bundle: dict[str, Any], mode: str):
    infer_cfg = getattr(cfg, "infer", None)
    dataset_path = _normalize_str(getattr(infer_cfg, "input_path", None))
    if not dataset_path:
        dataset_path = _normalize_str(getattr(getattr(cfg, "data", None), "dataset_path", None))

    input_payload = _parse_input_payload(getattr(infer_cfg, "input_json", None))
    allow_missing = bool(getattr(infer_cfg, "allow_missing_columns", False))

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

    df, _ = _align_input_frame(df, preprocess_bundle, allow_missing=allow_missing)
    if mode == "single":
        return df.head(1), resolved_path or dataset_path
    if mode == "batch":
        if input_payload is not None and resolved_path is None and not dataset_path:
            return df, None
        if not (resolved_path or dataset_path):
            raise ValueError("infer.input_path or data.dataset_path is required for batch mode.")
    return df, resolved_path or dataset_path


def run(cfg: Any) -> None:
    ctx = init_task_context(cfg, stage=cfg.task.stage, task_name="infer")
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)
    mode = _resolve_mode(cfg)
    if mode not in ("single", "batch"):
        raise ValueError(f"Unsupported infer mode: {mode}")

    model_bundle_path, meta = _resolve_model_bundle_path(cfg, clearml_enabled=clearml_enabled)
    bundle = load_bundle(model_bundle_path)
    if not isinstance(bundle, dict):
        raise ValueError("model_bundle.joblib is invalid.")

    model = bundle.get("model")
    preprocess_bundle = bundle.get("preprocess_bundle") or {}
    processed_dataset_id = _normalize_str(bundle.get("processed_dataset_id"))
    split_hash = _normalize_str(bundle.get("split_hash"))
    recipe_hash = _normalize_str(bundle.get("recipe_hash"))
    if model is None or not isinstance(preprocess_bundle, dict):
        raise ValueError("model_bundle is missing model or preprocess_bundle.")
    if not split_hash or not recipe_hash:
        raise ValueError("model_bundle is missing split_hash or recipe_hash.")

    inputs_df, input_path = _prepare_inputs(cfg, preprocess_bundle, mode)
    input_preview_path = _write_input_preview(inputs_df, mode, ctx.output_dir)
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

    preds = model.predict(transformed)
    rows = _preds_to_rows(preds)
    predictions_path: Path
    if mode == "single":
        predictions_path = ctx.output_dir / "prediction.json"
        if rows:
            row = rows[0]
            if len(row) == 1:
                payload = {"prediction": _sanitize_json_value(row[0])}
            else:
                payload = {"prediction": [_sanitize_json_value(v) for v in row]}
        else:
            payload = {"prediction": None}
        predictions_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        predictions_path = ctx.output_dir / "predictions.csv"
        with predictions_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            n_cols = len(rows[0]) if rows else 1
            if n_cols == 1:
                header = ["prediction"]
            else:
                header = [f"prediction_{idx}" for idx in range(n_cols)]
            writer.writerow(header)
            for row in rows:
                values = list(row)
                if len(values) < n_cols:
                    values.extend([None] * (n_cols - len(values)))
                writer.writerow([_sanitize_json_value(v) for v in values])

    if clearml_enabled:
        upload_artifact(ctx, predictions_path.name, predictions_path)
        upload_artifact(ctx, input_preview_path.name, input_preview_path)

    out = {
        "predictions_path": str(predictions_path),
        "input_preview_path": str(input_preview_path),
        "mode": mode,
        "model_id": meta.get("model_id") or str(model_bundle_path),
        "train_task_id": meta.get("train_task_id"),
    }
    write_out_json(ctx, out)

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
