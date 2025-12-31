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
from typing import Any, Iterable

from ..io.bundle_io import save_bundle
from ..io.schema import infer_schema
from ..platform_adapter import (
    get_dataset_local_copy,
    hash_config,
    hash_recipe,
    hash_split,
    init_task_context,
    is_clearml_enabled,
    register_dataset,
    resolve_version_props,
    save_config_resolved,
    update_task_properties,
    upload_artifact,
    write_manifest,
    write_out_json,
)
from ..registry.preprocessors import build_preprocessor, infer_feature_types

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


def _split_indices(
    df,
    *,
    strategy: str,
    test_size: float,
    seed: int,
    group_column: str | None,
    time_column: str | None,
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
    ctx = init_task_context(cfg, stage=cfg.task.stage, task_name="preprocess")
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
            local_copy = get_dataset_local_copy(cfg, raw_dataset_id_input)
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

    train_idx, val_idx = _split_indices(
        df,
        strategy=split_strategy,
        test_size=split_test_size,
        seed=split_seed,
        group_column=split_group_column,
        time_column=split_time_column,
    )

    split_payload = {"train_index": train_idx, "val_index": val_idx}
    split_hash = hash_split(split_payload)

    preprocess_variant = _to_container(getattr(cfg, "preprocess_variant", {})) or {}
    preprocess_variant_name = _normalize_str(preprocess_variant.get("name")) or _normalize_str(
        getattr(getattr(cfg, "preprocess", None), "variant", None)
    ) or "unknown"

    numeric_impute = _normalize_str(getattr(getattr(cfg, "preprocess", None), "numeric_impute", None))
    categorical_impute = _normalize_str(
        getattr(getattr(cfg, "preprocess", None), "categorical_impute", None)
    )
    numeric_impute = numeric_impute or "mean"
    categorical_impute = categorical_impute or "most_frequent"

    numeric_features, categorical_features = infer_feature_types(df, feature_columns)
    preprocessor = build_preprocessor(
        preprocess_variant,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        numeric_impute=numeric_impute,
        categorical_impute=categorical_impute,
    )

    train_df = df.iloc[train_idx]
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
    processed_df = pd.DataFrame(transformed, columns=feature_names)
    processed_df[target_column] = df[target_column].to_numpy()

    processed_path = ctx.output_dir / "processed_dataset.parquet"
    processed_df.to_parquet(processed_path, index=False)

    recipe_payload = {
        "variant": preprocess_variant,
        "impute": {"numeric": numeric_impute, "categorical": categorical_impute},
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

    if clearml_enabled:
        usecase_id = _normalize_str(getattr(getattr(cfg, "run", None), "usecase_id", None)) or "unknown"
        schema_version = _normalize_str(getattr(getattr(cfg, "run", None), "schema_version", None)) or "unknown"
        dataset_name = f"{usecase_id}__processed__{preprocess_variant_name}"
        dataset_project = _normalize_str(getattr(getattr(cfg, "task", None), "project_name", None))
        dataset_tags = [f"usecase:{usecase_id}", "process:preprocess", f"schema:{schema_version}"]
        processed_dataset_id = register_dataset(
            cfg,
            dataset_path=processed_path,
            dataset_name=dataset_name,
            dataset_project=dataset_project,
            dataset_tags=dataset_tags,
            description=f"raw_hash={raw_dataset_hash} recipe_hash={recipe_hash} split_hash={split_hash}",
        )
    else:
        processed_dataset_id = f"local:{processed_dataset_hash}"

    schema = infer_schema(df[feature_columns])
    schema["target_column"] = target_column
    schema["id_columns"] = id_columns
    schema["drop_columns"] = drop_columns

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

    recipe_path = ctx.output_dir / "recipe.json"
    recipe_path.write_text(json.dumps(recipe_payload, ensure_ascii=False, indent=2), encoding="utf-8")

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

    summary_lines = [
        "# Preprocess Summary",
        "",
        f"- variant: {preprocess_variant_name}",
        f"- rows: {int(df.shape[0])}",
        f"- features: {len(feature_columns)} (numeric={len(numeric_features)}, categorical={len(categorical_features)})",
        f"- split: train={len(train_idx)} val={len(val_idx)} strategy={split_strategy}",
        f"- processed_dataset_id: {processed_dataset_id}",
        f"- split_hash: {split_hash}",
        f"- recipe_hash: {recipe_hash}",
    ]
    summary_path = ctx.output_dir / "summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    if clearml_enabled:
        for name, path in [
            ("schema.json", schema_path),
            ("split.json", split_path),
            ("recipe.json", recipe_path),
            ("summary.md", summary_path),
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
            },
        )

    out = {
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
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
    }
    inputs: dict[str, Any] = {
        "preprocess_variant": preprocess_variant_name,
        "target_column": target_column,
    }
    if dataset_path_value:
        inputs["dataset_path"] = dataset_path_value
    if raw_dataset_id_input:
        inputs["raw_dataset_id"] = raw_dataset_id_input
    outputs = {
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
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
