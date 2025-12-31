"""dataset_register process."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    write_manifest,
    write_out_json,
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
        raise RuntimeError("pandas is required for dataset_register.") from exc
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported dataset format: {path.suffix}")


def _build_schema(df) -> dict[str, Any]:
    rows = int(df.shape[0])
    cols = int(df.shape[1])
    null_count = df.isna().sum()
    fields: dict[str, Any] = {}
    for col in df.columns:
        key = str(col)
        count = int(null_count[col])
        rate = float(count / rows) if rows else 0.0
        fields[key] = {
            "dtype": str(df[col].dtype),
            "null_count": count,
            "null_rate": rate,
        }
    return {"rows": rows, "columns": cols, "fields": fields}


def _infer_schema(path: Path, output_dir: Path) -> dict[str, Any]:
    df = _load_dataframe(path)
    schema = _build_schema(df)
    preview_path = output_dir / "preview.csv"
    df.head(5).to_csv(preview_path, index=False)
    schema_path = output_dir / "schema.json"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    return schema


def run(cfg: Any) -> None:
    ctx = init_task_context(cfg, stage=cfg.task.stage, task_name="dataset_register")
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)
    dataset_path_value = _normalize_str(getattr(cfg.data, "dataset_path", None))
    raw_dataset_id_input = _normalize_str(getattr(cfg.data, "raw_dataset_id", None))

    raw_dataset_id: str | None = None
    raw_dataset_hash: str | None = None
    raw_schema: dict[str, Any] | None = None

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

    if dataset_path is not None:
        dataset_file = _select_tabular_file(dataset_path)
        raw_dataset_hash = _hash_file(dataset_file)
        raw_schema = _infer_schema(dataset_file, ctx.output_dir)
        if clearml_enabled:
            usecase_id = _normalize_str(getattr(getattr(cfg, "run", None), "usecase_id", None)) or "unknown"
            schema_version = _normalize_str(getattr(getattr(cfg, "run", None), "schema_version", None)) or "unknown"
            dataset_name = f"{usecase_id}__raw__{dataset_file.stem}"
            dataset_project = _normalize_str(getattr(getattr(cfg, "task", None), "project_name", None))
            dataset_tags = [f"usecase:{usecase_id}", "process:dataset_register", f"schema:{schema_version}"]
            raw_dataset_id = register_dataset(
                cfg,
                dataset_path=dataset_file,
                dataset_name=dataset_name,
                dataset_project=dataset_project,
                dataset_tags=dataset_tags,
                description=f"raw_dataset_hash={raw_dataset_hash}",
            )
        else:
            raw_dataset_id = f"local:{raw_dataset_hash}"
    elif raw_dataset_id_input:
        if raw_dataset_id_input.startswith("local:"):
            raw_dataset_id = raw_dataset_id_input
            raw_dataset_hash = raw_dataset_id_input.split(":", 1)[1]
            if not raw_dataset_hash:
                raise ValueError("raw_dataset_id local:<hash> must include a hash.")
            raw_schema = {"rows": None, "columns": None, "fields": {}}
        elif clearml_enabled:
            local_copy = get_dataset_local_copy(cfg, raw_dataset_id_input)
            dataset_file = _select_tabular_file(local_copy)
            raw_dataset_hash = _hash_file(dataset_file)
            raw_schema = _infer_schema(dataset_file, ctx.output_dir)
            raw_dataset_id = raw_dataset_id_input
        else:
            raise ValueError("data.dataset_path is required when ClearML is disabled and raw_dataset_id is not local.")
    else:
        raise ValueError("Either data.dataset_path or data.raw_dataset_id is required.")

    if raw_dataset_id is None or raw_dataset_hash is None or raw_schema is None:
        raise RuntimeError("dataset_register failed to resolve raw_dataset outputs.")

    out = {
        "raw_dataset_id": raw_dataset_id,
        "raw_dataset_hash": raw_dataset_hash,
        "raw_schema": raw_schema,
    }
    write_out_json(ctx, out)

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    hashes = {
        "config_hash": hash_config(cfg),
        "split_hash": hash_split({}),
        "recipe_hash": hash_recipe({}),
    }
    inputs: dict[str, Any] = {}
    if dataset_path_value:
        inputs["dataset_path"] = dataset_path_value
    if raw_dataset_id_input:
        inputs["raw_dataset_id"] = raw_dataset_id_input
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "dataset_register",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
        "outputs": {"raw_dataset_id": raw_dataset_id, "raw_dataset_hash": raw_dataset_hash},
        "hashes": hashes,
    }
    write_manifest(ctx, manifest)
