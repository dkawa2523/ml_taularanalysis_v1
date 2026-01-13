"""dataset_register process."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..clearml.datasets import create_raw_dataset, get_raw_dataset_local_copy
from ..clearml.reporting import plots_enabled, report_plotly, report_scalar
from ..platform_adapter import (
    hash_config,
    hash_recipe,
    hash_split,
    init_task_context,
    is_clearml_enabled,
    resolve_version_props,
    save_config_resolved,
    write_manifest,
    write_out_json,
)
from ..ops.clearml_identity import apply_clearml_identity
from ..ops.data_quality import raise_on_quality_fail, run_data_quality_gate
from ..registry.preprocessors import infer_feature_types
from ..viz.data_profile import (
    build_categorical_topk_bars,
    build_head_table,
    build_missingness_bar,
    build_numeric_histograms,
    build_target_distribution,
    summarize_dataframe,
)

_TABULAR_SUFFIXES = (".csv", ".parquet", ".pq")
_PROFILE_SETTINGS = {
    "max_numeric": 4,
    "max_categorical": 4,
    "max_categories": 10,
    "max_columns": 30,
    "sample_rows": 5000,
    "table_rows": 5,
    "table_columns": 20,
}


def _series_name(prefix: str, name: Any, max_len: int = 48) -> str:
    text = str(name).replace("/", "_").replace(" ", "_")
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return f"{prefix}_{text}"


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


def _infer_schema(path: Path, output_dir: Path):
    df = _load_dataframe(path)
    schema = _build_schema(df)
    preview_path = output_dir / "preview.csv"
    df.head(5).to_csv(preview_path, index=False)
    schema_path = output_dir / "schema.json"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    return df, schema


def _log_data_profile(
    ctx: Any,
    df,
    *,
    cfg: Any,
    target_column: str | None,
    id_columns: list[Any],
) -> None:
    summary = summarize_dataframe(df)
    report_scalar(ctx.task, "dataset_register", "rows", summary.get("rows"), iteration=0, cfg=cfg)
    report_scalar(
        ctx.task,
        "dataset_register",
        "columns",
        summary.get("columns"),
        iteration=0,
        cfg=cfg,
    )
    report_scalar(
        ctx.task,
        "dataset_register",
        "missing_rate",
        summary.get("missing_rate"),
        iteration=0,
        cfg=cfg,
    )

    if not plots_enabled(cfg):
        return

    exclude = {str(value) for value in id_columns if value is not None}
    if target_column:
        exclude.add(str(target_column))
    columns = list(getattr(df, "columns", []))
    feature_columns = [col for col in columns if str(col) not in exclude]
    if not feature_columns:
        feature_columns = columns

    numeric_features, categorical_features = infer_feature_types(df, feature_columns)

    head_fig = build_head_table(
        df,
        max_rows=_PROFILE_SETTINGS["table_rows"],
        max_columns=_PROFILE_SETTINGS["table_columns"],
        output_dir=ctx.output_dir,
    )
    report_plotly(ctx.task, "dataset_register", "head_table", head_fig, iteration=0, cfg=cfg)

    missing_fig = build_missingness_bar(
        df,
        columns=columns,
        max_columns=_PROFILE_SETTINGS["max_columns"],
        output_dir=ctx.output_dir,
    )
    report_plotly(ctx.task, "dataset_register", "missingness", missing_fig, iteration=0, cfg=cfg)

    for col, fig in build_numeric_histograms(
        df,
        numeric_features,
        max_columns=_PROFILE_SETTINGS["max_numeric"],
        sample_rows=_PROFILE_SETTINGS["sample_rows"],
        output_dir=ctx.output_dir,
        title_prefix="Numeric Histogram",
    ):
        report_plotly(
            ctx.task,
            "dataset_register",
            _series_name("numeric_hist", col),
            fig,
            iteration=0,
            cfg=cfg,
        )

    for col, fig in build_categorical_topk_bars(
        df,
        categorical_features,
        max_columns=_PROFILE_SETTINGS["max_categorical"],
        top_k=_PROFILE_SETTINGS["max_categories"],
        sample_rows=_PROFILE_SETTINGS["sample_rows"],
        output_dir=ctx.output_dir,
        title_prefix="Top Categories",
    ):
        report_plotly(
            ctx.task,
            "dataset_register",
            _series_name("categorical_topk", col),
            fig,
            iteration=0,
            cfg=cfg,
        )

    target_fig = build_target_distribution(
        df,
        str(target_column) if target_column else "",
        bins=30,
        top_k=_PROFILE_SETTINGS["max_categories"],
        sample_rows=_PROFILE_SETTINGS["sample_rows"],
        output_dir=ctx.output_dir,
    )
    report_plotly(
        ctx.task,
        "dataset_register",
        "target_distribution",
        target_fig,
        iteration=0,
        cfg=cfg,
    )


def run(cfg: Any) -> None:
    identity = apply_clearml_identity(cfg, stage=cfg.task.stage)
    ctx = init_task_context(
        cfg,
        stage=cfg.task.stage,
        task_name="dataset_register",
        tags=identity.tags,
        properties=identity.user_properties,
    )
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)
    dataset_path_value = _normalize_str(getattr(cfg.data, "dataset_path", None))
    raw_dataset_id_input = _normalize_str(getattr(cfg.data, "raw_dataset_id", None))
    target_column = _normalize_str(getattr(getattr(cfg, "data", None), "target_column", None))

    raw_dataset_id: str | None = None
    raw_dataset_hash: str | None = None
    raw_schema: dict[str, Any] | None = None
    raw_df = None

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
        raw_df, raw_schema = _infer_schema(dataset_file, ctx.output_dir)
        if clearml_enabled:
            usecase_id = _normalize_str(getattr(getattr(cfg, "run", None), "usecase_id", None)) or "unknown"
            schema_version = _normalize_str(getattr(getattr(cfg, "run", None), "schema_version", None)) or "unknown"
            dataset_name = f"{usecase_id}__raw__{dataset_file.stem}"
            clearml_cfg = getattr(getattr(cfg, "run", None), "clearml", None)
            dataset_project = _normalize_str(getattr(clearml_cfg, "project_name", None))
            if not dataset_project:
                dataset_project = _normalize_str(getattr(getattr(cfg, "task", None), "project_name", None))
            dataset_tags = [f"usecase:{usecase_id}", "process:dataset_register", f"schema:{schema_version}"]
            raw_dataset_id = create_raw_dataset(
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
            local_copy = get_raw_dataset_local_copy(cfg, raw_dataset_id_input)
            dataset_file = _select_tabular_file(local_copy)
            raw_dataset_hash = _hash_file(dataset_file)
            raw_df, raw_schema = _infer_schema(dataset_file, ctx.output_dir)
            raw_dataset_id = raw_dataset_id_input
        else:
            raise ValueError("data.dataset_path is required when ClearML is disabled and raw_dataset_id is not local.")
    else:
        raise ValueError("Either data.dataset_path or data.raw_dataset_id is required.")

    if raw_dataset_id is None or raw_dataset_hash is None or raw_schema is None:
        raise RuntimeError("dataset_register failed to resolve raw_dataset outputs.")

    task_type = _normalize_task_type(getattr(getattr(cfg, "eval", None), "task_type", None))
    target_column = _normalize_str(getattr(getattr(cfg, "data", None), "target_column", None))
    id_columns = getattr(getattr(cfg, "data", None), "id_columns", []) or []
    quality_result = run_data_quality_gate(
        cfg=cfg,
        ctx=ctx,
        df=raw_df,
        target_column=target_column,
        task_type=task_type,
        id_columns=id_columns,
        output_dir=ctx.output_dir,
        schema=raw_schema if isinstance(raw_schema, dict) else None,
    )
    data_quality = quality_result["payload"]
    quality_summary = quality_result["summary"]
    gate = quality_result["gate"]
    data_quality_path = quality_result["paths"]["json"]

    if clearml_enabled and raw_df is not None:
        _log_data_profile(
            ctx,
            raw_df,
            cfg=cfg,
            target_column=target_column,
            id_columns=id_columns,
        )

    out = {
        "raw_dataset_id": raw_dataset_id,
        "raw_dataset_hash": raw_dataset_hash,
        "raw_schema": raw_schema,
        "data_quality_summary": quality_summary,
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

    raise_on_quality_fail(
        cfg=cfg,
        ctx=ctx,
        gate=gate,
        payload=data_quality,
        json_path=data_quality_path,
    )
