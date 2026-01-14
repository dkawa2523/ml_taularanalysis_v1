"""preprocess process.

T005 で実装予定。
- raw dataset から processed dataset を作る
- split を生成して固定（split_hash）
- preprocess bundle（transformers + schema）を保存

重要：train は split を再生成しない（比較可能性のため）。
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Iterable

from ..clearml.datasets import (
    create_processed_dataset,
    get_raw_dataset_local_copy,
    resolve_dataset_version,
)
from ..clearml.hparams import build_preprocess_sections, connect_preprocess
from ..clearml.ui_logger import report_plotly
from ..io.bundle_io import save_bundle
from ..io.schema import infer_schema
from ..ops.clearml_identity import apply_clearml_identity
from ..ops.data_quality import raise_on_quality_fail, run_data_quality_gate
from ..platform_adapter import (
    hash_config,
    hash_recipe,
    hash_split,
    init_task_context,
    is_clearml_enabled,
    resolve_version_props,
    save_config_resolved,
    update_task_properties,
    upload_artifact,
    write_manifest,
    write_out_json,
)
from ..feature_engineering.categorical import (
    build_categorical_encoding_report,
    build_tabular_preprocessor,
    encode_target_for_mean,
    normalize_encoding,
)
from ..registry.preprocessors import infer_feature_types
from ..viz.data_profile import (
    build_missing_rate_comparison_bar,
    build_profile_comparison_table,
    build_profile_summary,
)

_TABULAR_SUFFIXES = (".csv", ".parquet", ".pq")


def _hash_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


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


def _normalize_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "y", "on"):
        return True
    if text in ("0", "false", "no", "n", "off"):
        return False
    return bool(value)


def _select_tabular_file(path: Path) -> Path:
    if path.is_file():
        return path
    if path.is_dir():
        candidates = sorted([p for p in path.rglob("*") if p.suffix.lower() in _TABULAR_SUFFIXES])
        if candidates:
            return candidates[0]
        raise ValueError(f"No CSV/Parquet files found under: {path}")
    raise FileNotFoundError(str(path))


def _load_dataframe(path: Path):
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for preprocess.") from exc
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported dataset format: {path.suffix}")


def _to_container(value: Any) -> Any:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(value):
        return OmegaConf.to_container(value, resolve=True)
    return value


def _hash_payload(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _ensure_variant_cfg(cfg: Any, source_path: str, target_path: str) -> None:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        return
    if not OmegaConf.is_config(cfg):
        return
    if OmegaConf.select(cfg, target_path) is not None:
        return
    source = OmegaConf.select(cfg, source_path)
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
        OmegaConf.update(cfg, target_path, source, merge=False)
    finally:
        if was_struct:
            try:
                OmegaConf.set_struct(cfg, True)
            except Exception:
                pass


def _ensure_columns(df, columns: Iterable[str], *, label: str) -> list[str]:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing {label} columns in dataset: {missing}")
    return list(columns)


def _missing_stats(df, columns: Iterable[str]) -> dict[str, Any]:
    cols = list(columns)
    rows = int(df.shape[0])
    if not cols or rows <= 0:
        return {"missing_total": 0, "missing_rate": 0.0, "missing_columns": 0}
    subset = df[cols]
    missing_counts = subset.isna().sum()
    missing_total = int(missing_counts.sum())
    missing_columns = int((missing_counts > 0).sum())
    denom = rows * len(cols)
    missing_rate = float(missing_total / denom) if denom else 0.0
    return {
        "missing_total": missing_total,
        "missing_rate": missing_rate,
        "missing_columns": missing_columns,
    }


def _log_preprocess_profile(
    ctx: Any,
    *,
    df,
    processed_df,
    feature_columns: list[str],
    numeric_features: list[str],
    categorical_features: list[str],
    processed_feature_columns: list[str],
) -> None:
    processed_numeric, processed_categorical = infer_feature_types(
        processed_df, processed_feature_columns
    )
    raw_summary = build_profile_summary(
        df,
        feature_columns=feature_columns,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
    )
    processed_summary = build_profile_summary(
        processed_df,
        feature_columns=processed_feature_columns,
        numeric_features=processed_numeric,
        categorical_features=processed_categorical,
    )

    table_fig = build_profile_comparison_table(
        raw_summary,
        processed_summary,
        output_dir=ctx.output_dir,
        title="Raw vs Processed Summary",
    )
    report_plotly(ctx.task, "preprocess", "raw_vs_processed_summary", table_fig, step=0)

    missing_fig = build_missing_rate_comparison_bar(
        float(raw_summary.get("missing_rate", 0.0)),
        float(processed_summary.get("missing_rate", 0.0)),
        output_dir=ctx.output_dir,
        title="Missing Rate (raw vs processed)",
    )
    report_plotly(ctx.task, "preprocess", "missing_rate", missing_fig, step=0)


def _split_indices(
    df,
    *,
    strategy: str,
    test_size: float,
    seed: int,
    group_column: str | None,
    time_column: str | None,
    stratify_labels: Any | None = None,
) -> tuple[list[int], list[int]]:
    import math

    import numpy as np  # type: ignore

    n_samples = int(df.shape[0])
    if n_samples < 2:
        raise ValueError("Dataset must contain at least 2 rows for splitting.")
    if not (0.0 < test_size < 1.0):
        raise ValueError(f"data.split.test_size must be between 0 and 1. Got {test_size}.")

    indices = np.arange(n_samples)
    strategy_lower = str(strategy).strip().lower()
    if strategy_lower == "random":
        from sklearn.model_selection import train_test_split  # type: ignore

        train_idx, val_idx = train_test_split(
            indices,
            test_size=test_size,
            random_state=seed,
            shuffle=True,
        )
    elif strategy_lower == "group":
        if not group_column:
            raise ValueError("data.split.group_column is required for group strategy.")
        if group_column not in df.columns:
            raise ValueError(f"group_column not found in dataset: {group_column}")
        from sklearn.model_selection import GroupShuffleSplit  # type: ignore

        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
        train_idx, val_idx = next(splitter.split(indices, groups=df[group_column]))
    elif strategy_lower == "stratified":
        if stratify_labels is None:
            raise ValueError("stratified split requires target labels for stratification.")
        labels = np.asarray(stratify_labels).reshape(-1)
        if labels.shape[0] != n_samples:
            raise ValueError("stratified split labels size does not match dataset rows.")
        if len(np.unique(labels)) < 2:
            raise ValueError("stratified split requires at least 2 classes in target.")
        from sklearn.model_selection import StratifiedShuffleSplit  # type: ignore

        splitter = StratifiedShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
        train_idx, val_idx = next(splitter.split(indices, labels))
    elif strategy_lower == "time":
        if not time_column:
            raise ValueError("data.split.time_column is required for time strategy.")
        if time_column not in df.columns:
            raise ValueError(f"time_column not found in dataset: {time_column}")
        order = np.argsort(df[time_column].to_numpy(), kind="mergesort")
        n_val = int(math.ceil(n_samples * test_size))
        if n_val <= 0 or n_val >= n_samples:
            raise ValueError("data.split.test_size produces an invalid split size for time strategy.")
        val_idx = order[-n_val:]
        train_idx = order[:-n_val]
    else:
        raise ValueError(f"Unsupported split strategy: {strategy}")

    return sorted(train_idx.tolist()), sorted(val_idx.tolist())


def run(cfg: Any) -> None:
    _ensure_variant_cfg(cfg, "group.preprocess.preprocess_variant", "preprocess_variant")
    identity = apply_clearml_identity(cfg, stage=cfg.task.stage)
    ctx = init_task_context(
        cfg,
        stage=cfg.task.stage,
        task_name="preprocess",
        tags=identity.tags,
        properties=identity.user_properties,
    )
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)

    dataset_path_value = _normalize_str(getattr(cfg.data, "dataset_path", None))
    raw_dataset_id_input = _normalize_str(getattr(cfg.data, "raw_dataset_id", None))

    dataset_path: Path | None = None
    if dataset_path_value:
        dataset_path = Path(dataset_path_value).expanduser().resolve()
    elif raw_dataset_id_input and not clearml_enabled:
        if raw_dataset_id_input.startswith("local:"):
            dataset_path = None
        else:
            candidate = Path(raw_dataset_id_input).expanduser()
            if candidate.exists():
                dataset_path = candidate.resolve()

    dataset_file: Path | None = None
    if dataset_path is not None:
        dataset_file = _select_tabular_file(dataset_path)
    elif raw_dataset_id_input:
        if raw_dataset_id_input.startswith("local:"):
            if not dataset_path_value:
                raise ValueError(
                    "data.dataset_path is required when raw_dataset_id is local in local mode."
                )
        elif clearml_enabled:
            local_copy = get_raw_dataset_local_copy(cfg, raw_dataset_id_input)
            dataset_file = _select_tabular_file(local_copy)
        else:
            raise ValueError(
                "data.dataset_path is required when ClearML is disabled and raw_dataset_id is not local."
            )
    else:
        raise ValueError("Either data.dataset_path or data.raw_dataset_id is required.")

    if dataset_file is None:
        raise RuntimeError("preprocess failed to resolve dataset file.")

    df = _load_dataframe(dataset_file)
    raw_dataset_hash = _hash_file(dataset_file)

    target_column = _normalize_str(getattr(cfg.data, "target_column", None))
    if not target_column or target_column not in df.columns:
        raise ValueError(f"target_column not found in dataset: {target_column}")

    id_columns = _ensure_columns(
        df, getattr(cfg.data, "id_columns", []) or [], label="id"
    )
    drop_columns = _ensure_columns(
        df, getattr(cfg.data, "drop_columns", []) or [], label="drop"
    )

    feature_columns = [
        col for col in df.columns if col not in set([target_column, *id_columns, *drop_columns])
    ]
    if not feature_columns:
        raise ValueError("No feature columns remain after applying target/id/drop exclusions.")

    split_cfg = getattr(cfg.data, "split", None)
    split_strategy = _normalize_str(getattr(split_cfg, "strategy", None)) or "random"
    split_test_size = float(getattr(split_cfg, "test_size", 0.2))
    split_seed = int(getattr(split_cfg, "seed", 42))
    split_group_column = _normalize_str(getattr(split_cfg, "group_column", None))
    split_time_column = _normalize_str(getattr(split_cfg, "time_column", None))
    task_type = _normalize_task_type(getattr(getattr(cfg, "eval", None), "task_type", None))
    if split_strategy.lower() == "stratified" and task_type != "classification":
        raise ValueError("data.split.strategy=stratified requires eval.task_type=classification.")

    quality_result = run_data_quality_gate(
        cfg=cfg,
        ctx=ctx,
        df=df,
        target_column=target_column,
        task_type=task_type,
        id_columns=id_columns,
        output_dir=ctx.output_dir,
    )
    raise_on_quality_fail(
        cfg=cfg,
        ctx=ctx,
        gate=quality_result["gate"],
        payload=quality_result["payload"],
        json_path=quality_result["paths"]["json"],
    )

    train_idx, val_idx = _split_indices(
        df,
        strategy=split_strategy,
        test_size=split_test_size,
        seed=split_seed,
        group_column=split_group_column,
        time_column=split_time_column,
        stratify_labels=df[target_column] if split_strategy.lower() == "stratified" else None,
    )

    split_payload = {"train_index": train_idx, "val_index": val_idx}
    split_hash = hash_split(split_payload)
    store_features = _normalize_bool(
        _cfg_value(cfg, "ops.processed_dataset.store_features", True), default=True
    )

    preprocess_variant = _to_container(getattr(cfg, "preprocess_variant", {})) or {}
    preprocess_variant_name = _normalize_str(preprocess_variant.get("name")) or _normalize_str(
        getattr(getattr(cfg, "preprocess", None), "variant", None)
    ) or "unknown"
    connect_preprocess(
        ctx,
        cfg,
        raw_dataset_id=raw_dataset_id_input,
        dataset_path=dataset_path_value if not raw_dataset_id_input else None,
        preprocess_variant=preprocess_variant_name,
        split_strategy=split_strategy,
        split_seed=split_seed,
        store_features=store_features,
    )

    numeric_impute = _normalize_str(getattr(getattr(cfg, "preprocess", None), "numeric_impute", None))
    categorical_impute = _normalize_str(
        getattr(getattr(cfg, "preprocess", None), "categorical_impute", None)
    )
    numeric_impute = numeric_impute or "mean"
    categorical_impute = categorical_impute or "most_frequent"

    numeric_features, categorical_features = infer_feature_types(df, feature_columns)
    categorical_cfg = getattr(getattr(cfg, "preprocess", None), "categorical", None)
    categorical_encoding_raw = _normalize_str(getattr(categorical_cfg, "encoding", None))
    if not categorical_encoding_raw:
        categorical_encoding_raw = preprocess_variant.get("categorical_encoder", None)
    categorical_encoding = normalize_encoding(categorical_encoding_raw or "onehot") or "onehot"
    auto_onehot_max_categories = int(
        getattr(categorical_cfg, "auto_onehot_max_categories", 50) or 50
    )
    hashing_cfg = getattr(categorical_cfg, "hashing", None)
    hashing_n_features = int(getattr(hashing_cfg, "n_features", 128) or 128)
    target_mean_cfg = getattr(categorical_cfg, "target_mean_oof", None)
    target_mean_folds = int(getattr(target_mean_cfg, "folds", 5) or 5)
    target_mean_smoothing = getattr(target_mean_cfg, "smoothing", 10.0)
    if target_mean_smoothing is None:
        target_mean_smoothing = 0.0
    target_mean_smoothing = float(target_mean_smoothing)

    train_df = df.iloc[train_idx]
    cat_unique_counts = {
        col: int(train_df[col].nunique(dropna=True)) for col in categorical_features
    }
    preprocessor, encoding_by_column, categorical_encoding = build_tabular_preprocessor(
        preprocess_variant,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        numeric_impute=numeric_impute,
        categorical_impute=categorical_impute,
        categorical_encoding=categorical_encoding,
        auto_onehot_max_categories=auto_onehot_max_categories,
        hashing_n_features=hashing_n_features,
        target_mean_smoothing=target_mean_smoothing,
        unique_counts=cat_unique_counts,
    )

    if categorical_encoding == "target_mean_oof" and categorical_features:
        y_encoded, _ = encode_target_for_mean(
            train_values=train_df[target_column],
            all_values=df[target_column],
            task_type=task_type,
        )
        preprocessor.fit(train_df[feature_columns], y_encoded[train_idx])
        transformed = preprocessor.transform_with_oof(
            df[feature_columns],
            y_encoded,
            train_idx=train_idx,
            folds=target_mean_folds,
            seed=split_seed,
            task_type=task_type,
        )
    else:
        preprocessor.fit(train_df[feature_columns])
        transformed = preprocessor.transform(df[feature_columns])
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()

    try:
        feature_names = list(preprocessor.get_feature_names_out())
    except Exception:
        feature_names = [f"f{i}" for i in range(int(getattr(transformed, "shape", [0, 0])[1]))]

    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("pandas is required for preprocess output.") from exc

    unique_counts_imputed: dict[str, int] = {}
    if categorical_features and getattr(preprocessor, "categorical_imputer", None) is not None:
        cat_imputed = preprocessor.categorical_imputer.transform(train_df[categorical_features])
        cat_imputed_df = pd.DataFrame(cat_imputed, columns=categorical_features)
        unique_counts_imputed = {
            col: int(cat_imputed_df[col].nunique(dropna=True)) for col in categorical_features
        }
    encoding_report = build_categorical_encoding_report(
        categorical_features,
        encoding=categorical_encoding,
        encoding_by_column=encoding_by_column,
        unique_counts=unique_counts_imputed,
        hashing_n_features=hashing_n_features,
    )
    encoding_report_path = ctx.output_dir / "categorical_encoding_report.json"
    encoding_report_path.write_text(
        json.dumps(encoding_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    processed_df = pd.DataFrame(transformed, columns=feature_names)
    processed_df[target_column] = df[target_column].to_numpy()

    missing_before = _missing_stats(df, feature_columns)
    processed_feature_columns = [col for col in processed_df.columns if col != target_column]
    n_rows = int(df.shape[0])
    n_features = len(processed_feature_columns)
    missing_after = _missing_stats(processed_df, processed_feature_columns)
    dropped_columns = [str(col) for col in dict.fromkeys([*id_columns, *drop_columns])]
    quality_after = {
        "rows": n_rows,
        "columns_before": len(feature_columns),
        "columns_after": len(processed_feature_columns),
        "dropped_columns": {"count": len(dropped_columns), "columns": dropped_columns},
        "missing": {
            "before": missing_before,
            "after": missing_after,
            "reduced_total": missing_before["missing_total"] - missing_after["missing_total"],
        },
    }
    quality_after_path = ctx.output_dir / "quality_after_preprocess.json"
    quality_after_path.write_text(
        json.dumps(quality_after, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if clearml_enabled:
        _log_preprocess_profile(
            ctx,
            df=df,
            processed_df=processed_df,
            feature_columns=feature_columns,
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            processed_feature_columns=processed_feature_columns,
        )

    processed_path = ctx.output_dir / "processed_dataset.parquet"
    processed_df.to_parquet(processed_path, index=False)

    categorical_encoding_config = {
        "encoding": categorical_encoding,
        "auto_onehot_max_categories": auto_onehot_max_categories,
        "hashing": {"n_features": hashing_n_features},
        "target_mean_oof": {"folds": target_mean_folds, "smoothing": target_mean_smoothing},
    }
    recipe_payload = {
        "variant": preprocess_variant,
        "impute": {"numeric": numeric_impute, "categorical": categorical_impute},
        "categorical_encoding": categorical_encoding_config,
        "columns": {
            "feature_columns": feature_columns,
            "numeric_features": numeric_features,
            "categorical_features": categorical_features,
            "target_column": target_column,
            "id_columns": id_columns,
            "drop_columns": drop_columns,
        },
    }
    recipe_hash = hash_recipe(recipe_payload)

    processed_id_payload = {
        "raw_dataset_hash": raw_dataset_hash,
        "recipe_hash": recipe_hash,
        "split_hash": split_hash,
    }
    processed_dataset_hash = _hash_payload(processed_id_payload)

    schema = infer_schema(df[feature_columns])
    schema["target_column"] = target_column
    schema["id_columns"] = id_columns
    schema["drop_columns"] = drop_columns
    schema_hash = _hash_payload(schema)

    schema_path = ctx.output_dir / "schema.json"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    split_artifact = {
        "strategy": split_strategy,
        "seed": split_seed,
        "test_size": split_test_size,
        "group_column": split_group_column,
        "time_column": split_time_column,
        **split_payload,
    }
    split_path = ctx.output_dir / "split.json"
    split_path.write_text(json.dumps(split_artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    splits_path = ctx.output_dir / "splits.json"
    splits_path.write_text(json.dumps(split_artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    recipe_path = ctx.output_dir / "recipe.json"
    recipe_path.write_text(json.dumps(recipe_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    feature_names_path = ctx.output_dir / "feature_names.json"
    feature_names_path.write_text(
        json.dumps(feature_names, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    bundle = {
        "preprocess_variant": preprocess_variant_name,
        "pipeline": preprocessor,
        "feature_names": feature_names,
        "columns": {
            "feature_columns": feature_columns,
            "numeric_features": numeric_features,
            "categorical_features": categorical_features,
            "target_column": target_column,
            "id_columns": id_columns,
            "drop_columns": drop_columns,
        },
        "schema": schema,
        "impute": {"numeric": numeric_impute, "categorical": categorical_impute},
    }
    bundle_path = ctx.output_dir / "preprocess_bundle.joblib"
    save_bundle(bundle_path, bundle)
    bundle_hash = _hash_file(bundle_path)

    usecase_id = _normalize_str(getattr(getattr(cfg, "run", None), "usecase_id", None)) or "unknown"
    schema_version = _normalize_str(getattr(getattr(cfg, "run", None), "schema_version", None)) or "unknown"

    meta_payload = {
        "processed_dataset_hash": processed_dataset_hash,
        "raw_dataset_hash": raw_dataset_hash,
        "raw_dataset_id": raw_dataset_id_input,
        "recipe_hash": recipe_hash,
        "split_hash": split_hash,
        "schema_hash": schema_hash,
        "bundle_hash": bundle_hash,
        "preprocess_variant": preprocess_variant_name,
        "task_type": task_type,
        "target_column": target_column,
        "n_rows": n_rows,
        "n_features": n_features,
        "store_features": store_features,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": schema_version,
        "usecase_id": usecase_id,
    }
    meta_path = ctx.output_dir / "meta.json"
    meta_path.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    dataset_dir = ctx.output_dir / "processed_dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(schema_path, dataset_dir / "schema.json")
    shutil.copy2(splits_path, dataset_dir / "splits.json")
    shutil.copy2(recipe_path, dataset_dir / "recipe.json")
    shutil.copy2(bundle_path, dataset_dir / "preprocess_bundle.joblib")
    shutil.copy2(meta_path, dataset_dir / "meta.json")
    shutil.copy2(feature_names_path, dataset_dir / "feature_names.json")
    if store_features:
        x_path = dataset_dir / "X.parquet"
        y_path = dataset_dir / "y.parquet"
        processed_df[processed_feature_columns].to_parquet(x_path, index=False)
        processed_df[[target_column]].to_parquet(y_path, index=False)
    else:
        for name in ("X.parquet", "y.parquet"):
            candidate = dataset_dir / name
            if candidate.exists():
                candidate.unlink()

    processed_dataset_version: str | None = None
    if clearml_enabled:
        dataset_name = (
            f"processed__{usecase_id}__{preprocess_variant_name}__{split_hash}__v{schema_version}"
        )
        dataset_project = _normalize_str(getattr(getattr(cfg, "task", None), "project_name", None))
        dataset_tags = [
            f"usecase:{usecase_id}",
            "process:preprocess",
            "type:processed",
            f"schema:v{schema_version}",
        ]
        parent_ids = None
        if raw_dataset_id_input and not raw_dataset_id_input.startswith("local:"):
            parent_ids = [raw_dataset_id_input]
        dataset_sections, dataset_order = build_preprocess_sections(
            cfg,
            raw_dataset_id=raw_dataset_id_input,
            dataset_path=dataset_path_value if not raw_dataset_id_input else None,
            preprocess_variant=preprocess_variant_name,
            split_strategy=split_strategy,
            split_seed=split_seed,
            store_features=store_features,
        )
        processed_dataset_id = create_processed_dataset(
            cfg,
            dataset_dir=dataset_dir,
            dataset_name=dataset_name,
            dataset_project=dataset_project,
            dataset_tags=dataset_tags,
            description=(
                "raw_hash="
                f"{raw_dataset_hash} recipe_hash={recipe_hash} split_hash={split_hash} "
                f"schema_hash={schema_hash} store_features={store_features}"
            ),
            parent_dataset_ids=parent_ids,
            task_sections=dataset_sections,
            task_section_order=dataset_order,
        )
        processed_dataset_version = resolve_dataset_version(cfg, processed_dataset_id)
    else:
        processed_dataset_id = f"local:{processed_dataset_hash}"

    encoding_note = categorical_encoding
    if categorical_encoding == "auto":
        encoding_note = (
            f"auto(onehot_max={auto_onehot_max_categories}, hash_n_features={hashing_n_features})"
        )
    elif categorical_encoding == "hashing":
        encoding_note = f"hashing(n_features={hashing_n_features})"
    elif categorical_encoding == "target_mean_oof":
        encoding_note = f"target_mean_oof(folds={target_mean_folds}, smoothing={target_mean_smoothing})"

    summary_lines = [
        "# Preprocess Summary",
        "",
        f"- variant: {preprocess_variant_name}",
        f"- categorical_encoding: {encoding_note} (high-card handling)",
        f"- rows: {n_rows}",
        f"- features: {len(feature_columns)} (numeric={len(numeric_features)}, categorical={len(categorical_features)})",
        f"- split: train={len(train_idx)} val={len(val_idx)} strategy={split_strategy}",
        f"- processed_dataset_id: {processed_dataset_id}",
        f"- store_features: {store_features}",
        f"- split_hash: {split_hash}",
        f"- recipe_hash: {recipe_hash}",
        f"- schema_hash: {schema_hash}",
    ]
    summary_path = ctx.output_dir / "summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    if clearml_enabled:
        for name, path in [
            ("schema.json", schema_path),
            ("split.json", split_path),
            ("splits.json", splits_path),
            ("recipe.json", recipe_path),
            ("feature_names.json", feature_names_path),
            ("meta.json", meta_path),
            ("categorical_encoding_report.json", encoding_report_path),
            ("summary.md", summary_path),
            ("quality_after_preprocess.json", quality_after_path),
            ("preprocess_bundle.joblib", bundle_path),
            ("processed_dataset.parquet", processed_path),
        ]:
            upload_artifact(ctx, name, path)
        update_task_properties(
            ctx,
            {
                "processed_dataset_id": processed_dataset_id,
                "split_hash": split_hash,
                "recipe_hash": recipe_hash,
                "schema_hash": schema_hash,
                "processed_dataset_version": processed_dataset_version,
            },
        )

    out = {
        "processed_dataset_id": processed_dataset_id,
        "processed_dataset_version": processed_dataset_version,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "schema_hash": schema_hash,
        "processed_dataset_hash": processed_dataset_hash,
        "n_rows": n_rows,
        "n_features": n_features,
        "preprocess_variant": preprocess_variant_name,
    }
    if not clearml_enabled:
        out["processed_dataset_path"] = str(processed_path)
    write_out_json(ctx, out)

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    hashes = {
        "config_hash": hash_config(cfg),
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "schema_hash": schema_hash,
    }
    raw_dataset_id_value = raw_dataset_id_input
    if not raw_dataset_id_value and dataset_path_value:
        raw_dataset_id_value = f"local:{raw_dataset_hash}"
    inputs: dict[str, Any] = {
        "raw_dataset_id": raw_dataset_id_value,
        "upstream_task_ids": [],
        "preprocess_variant": preprocess_variant_name,
        "target_column": target_column,
        "categorical_encoding": categorical_encoding_config,
        "store_features": store_features,
    }
    if dataset_path_value:
        inputs["dataset_path"] = dataset_path_value
    outputs = {
        "processed_dataset_id": processed_dataset_id,
        "processed_dataset_version": processed_dataset_version,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "schema_hash": schema_hash,
        "n_rows": n_rows,
        "n_features": n_features,
    }
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "preprocess",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
        "outputs": outputs,
        "hashes": hashes,
    }
    write_manifest(ctx, manifest)
