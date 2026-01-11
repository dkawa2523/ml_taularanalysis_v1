"""Pipeline reporting utilities."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping

from ..platform_adapter import get_task_artifact_local_copy, is_clearml_enabled


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _format_value(value: Any, *, fallback: str = "n/a") -> str:
    if value is None:
        return fallback
    if isinstance(value, float):
        return f"{value:.6g}"
    text = str(value).strip()
    return text if text else fallback


def _format_rate(value: Any, *, fallback: str = "n/a") -> str:
    try:
        return f"{float(value):.1%}"
    except Exception:
        return fallback


def _shorten_path(value: str, *, keep: int = 2) -> str:
    if "/" not in value and "\\" not in value:
        return value
    path = Path(value)
    parts = path.parts
    if len(parts) <= keep:
        return value
    return ".../" + "/".join(parts[-keep:])


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _safe_load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_load_csv(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row:
                    continue
                rows.append(dict(row))
    except Exception:
        return []
    return rows


class _ArtifactResolver:
    def __init__(self, cfg: Any | None):
        self._cfg = cfg
        self._clearml_enabled = bool(cfg) and is_clearml_enabled(cfg)

    def resolve(self, ref: Mapping[str, Any] | None, name: str) -> Path | None:
        if not ref:
            return None
        run_dir = _normalize_str(ref.get("run_dir"))
        if run_dir:
            path = Path(run_dir) / name
            if path.exists():
                return path
        if self._clearml_enabled:
            task_id = _normalize_str(ref.get("task_id") or ref.get("train_task_id"))
            if task_id:
                try:
                    return get_task_artifact_local_copy(self._cfg, task_id, name)
                except Exception:
                    return None
        return None


def _build_model_rows_from_train_refs(train_refs: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, ref in enumerate(train_refs, start=1):
        rows.append(
            {
                "rank": idx,
                "model_variant": ref.get("model_variant"),
                "preprocess_variant": ref.get("preprocess_variant"),
                "primary_metric": ref.get("primary_metric"),
                "best_score": ref.get("best_score"),
                "model_id": ref.get("model_id"),
                "train_task_ref": ref.get("train_task_id") or ref.get("task_id"),
            }
        )
    return rows


def _append_models_table(lines: list[str], rows: list[Mapping[str, Any]], max_models: int) -> None:
    if not rows:
        lines.append("- No leaderboard or train results available.")
        return
    lines.extend(
        [
            "",
            "| Rank | Model | Preprocess | Metric | Score | Model ID |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows[:max_models]:
        model_id = _normalize_str(row.get("model_id"))
        model_id_display = _shorten_path(model_id) if model_id else "n/a"
        items = [
            _format_value(row.get("rank")),
            _format_value(row.get("model_variant")),
            _format_value(row.get("preprocess_variant")),
            _format_value(row.get("primary_metric")),
            _format_value(row.get("best_score")),
            model_id_display,
        ]
        lines.append("| " + " | ".join(_md_escape(str(item)) for item in items) + " |")


def build_pipeline_report(
    pipeline_run: Mapping[str, Any], *, cfg: Any | None = None, max_models: int = 5
) -> str:
    """Build a human-readable markdown report for pipeline runs."""

    resolver = _ArtifactResolver(cfg)

    grid = pipeline_run.get("grid", {}) if isinstance(pipeline_run, Mapping) else {}
    preprocess_variants = list(grid.get("preprocess_variants") or [])
    model_variants = list(grid.get("model_variants") or [])
    hpo_cfg = grid.get("hpo", {}) if isinstance(grid, Mapping) else {}
    hpo_enabled = bool(hpo_cfg.get("enabled"))

    preprocess_refs = list(pipeline_run.get("preprocess_ref") or [])
    preprocess_ref = preprocess_refs[0] if preprocess_refs else None
    preprocess_out = _safe_load_json(resolver.resolve(preprocess_ref, "out.json")) or {}
    preprocess_schema = _safe_load_json(resolver.resolve(preprocess_ref, "schema.json")) or {}
    split_payload = _safe_load_json(resolver.resolve(preprocess_ref, "split.json")) or {}
    recipe_payload = _safe_load_json(resolver.resolve(preprocess_ref, "recipe.json")) or {}

    dataset_register_ref = pipeline_run.get("dataset_register_ref")
    dataset_out = _safe_load_json(resolver.resolve(dataset_register_ref, "out.json")) or {}
    data_quality = _safe_load_json(resolver.resolve(dataset_register_ref, "data_quality.json")) or {}

    rows = preprocess_schema.get("rows")
    feature_cols = preprocess_schema.get("columns")
    target_column = preprocess_schema.get("target_column")
    id_columns = preprocess_schema.get("id_columns") or []
    drop_columns = preprocess_schema.get("drop_columns") or []
    preprocess_variant = (
        _normalize_str(preprocess_ref.get("preprocess_variant")) if preprocess_ref else None
    ) or _normalize_str(recipe_payload.get("variant", {}).get("name"))

    split_hash = _normalize_str(preprocess_out.get("split_hash")) or (
        _normalize_str(preprocess_ref.get("split_hash")) if preprocess_ref else None
    )
    recipe_hash = _normalize_str(preprocess_out.get("recipe_hash")) or (
        _normalize_str(preprocess_ref.get("recipe_hash")) if preprocess_ref else None
    )

    leaderboard_ref = pipeline_run.get("leaderboard_ref")
    leaderboard_csv = resolver.resolve(leaderboard_ref, "leaderboard.csv")
    leaderboard_rows = _safe_load_csv(leaderboard_csv)
    leaderboard_out = _safe_load_json(resolver.resolve(leaderboard_ref, "out.json")) or {}
    recommendation = _safe_load_json(resolver.resolve(leaderboard_ref, "recommendation.json")) or {}

    recommended_model_id = _normalize_str(
        recommendation.get("recommended_model_id") or leaderboard_out.get("recommended_model_id")
    )
    recommended_metric = _normalize_str(
        recommendation.get("recommended_primary_metric")
        or leaderboard_out.get("recommended_primary_metric")
    )
    recommended_score = recommendation.get("recommended_best_score")
    if recommended_score is None:
        recommended_score = leaderboard_out.get("recommended_best_score")
    recommended_train_ref = _normalize_str(
        leaderboard_out.get("recommended_train_task_ref")
        or leaderboard_out.get("recommended_train_task_id")
    )

    recommended_threshold = None
    if recommended_train_ref:
        ref: dict[str, Any]
        if Path(recommended_train_ref).exists():
            ref = {"run_dir": recommended_train_ref}
        else:
            ref = {"task_id": recommended_train_ref}
        train_out = _safe_load_json(resolver.resolve(ref, "out.json")) or {}
        recommended_threshold = train_out.get("best_threshold")

    train_refs = list(pipeline_run.get("train_refs") or [])
    if not leaderboard_rows and train_refs:
        leaderboard_rows = _build_model_rows_from_train_refs(train_refs)

    models_tried = len(leaderboard_rows) if leaderboard_rows else len(train_refs)
    status = "ready" if recommended_model_id else "incomplete"

    lines: list[str] = [
        "# Pipeline Summary",
        "",
        "## Conclusion",
        f"- recommended_model_id: {_format_value(recommended_model_id)}",
        f"- primary_metric: {_format_value(recommended_metric)}",
        f"- best_score: {_format_value(recommended_score)}",
        f"- status: {status}",
        f"- models_tried: {_format_value(models_tried)}",
    ]
    planned_jobs = pipeline_run.get("planned_jobs") if isinstance(pipeline_run, Mapping) else None
    executed_jobs = pipeline_run.get("executed_jobs") if isinstance(pipeline_run, Mapping) else None
    skipped_jobs = pipeline_run.get("skipped_due_to_policy") if isinstance(pipeline_run, Mapping) else None
    plan_only = pipeline_run.get("plan_only") if isinstance(pipeline_run, Mapping) else None
    if planned_jobs is not None:
        lines.append(f"- planned_jobs: {_format_value(planned_jobs)}")
    if executed_jobs is not None:
        lines.append(f"- executed_jobs: {_format_value(executed_jobs)}")
    if skipped_jobs is not None:
        lines.append(f"- skipped_due_to_policy: {_format_value(skipped_jobs)}")
    if plan_only:
        lines.append("- plan_only: true")
    if recommended_train_ref:
        lines.append(f"- train_task_ref: {_format_value(recommended_train_ref)}")

    lines.extend(
        [
            "",
            "## Data Overview",
            f"- rows: {_format_value(rows)}",
            f"- feature_columns: {_format_value(feature_cols)}",
            f"- target_column: {_format_value(target_column)}",
        ]
    )
    if id_columns:
        lines.append(f"- id_columns: {_format_value(id_columns)}")
    if drop_columns:
        lines.append(f"- drop_columns: {_format_value(drop_columns)}")

    lines.extend(["", "## Data Quality"])
    if data_quality:
        rows_scanned = data_quality.get("rows_scanned")
        rows_total = data_quality.get("rows_total")
        sampled = data_quality.get("scan_sampled")
        if sampled and rows_total:
            lines.append(f"- sampled: true ({_format_value(rows_scanned)}/{_format_value(rows_total)})")
        else:
            lines.append(f"- rows_scanned: {_format_value(rows_scanned)}")
        duplicates_count = data_quality.get("duplicates_count")
        duplicates_rate = data_quality.get("duplicates_rate")
        lines.append(
            f"- duplicates: {_format_value(duplicates_count)} ({_format_rate(duplicates_rate)})"
        )
        missing_top = data_quality.get("missing_top") or []
        if missing_top:
            items = []
            for item in missing_top[:5]:
                col = _normalize_str(item.get("column"))
                rate = item.get("missing_rate")
                if not col:
                    continue
                items.append(f"{_md_escape(col)}({_format_rate(rate)})")
            lines.append(f"- missing_top: {', '.join(items) if items else 'n/a'}")
        else:
            lines.append("- missing_top: n/a")
        leak_suspects = data_quality.get("leak_suspects") or []
        if leak_suspects:
            items = []
            for suspect in leak_suspects[:5]:
                col = _normalize_str(suspect.get("column"))
                reason = _normalize_str(suspect.get("reason"))
                severity = _normalize_str(suspect.get("severity"))
                if not col:
                    continue
                label = f"{_md_escape(col)}:{reason or 'suspect'}"
                if severity:
                    label += f"({severity})"
                items.append(label)
            lines.append(f"- leak_suspects: {', '.join(items) if items else 'n/a'}")
        else:
            lines.append("- leak_suspects: none")
    else:
        summary = dataset_out.get("data_quality_summary") or {}
        if summary:
            lines.append(f"- rows_scanned: {_format_value(summary.get('rows'))}")
            lines.append(f"- duplicates: {_format_value(summary.get('duplicates_count'))}")
            lines.append(f"- missing_columns: {_format_value(summary.get('missing_columns'))}")
            lines.append(f"- leak_suspects: {_format_value(summary.get('leak_suspects'))}")
        else:
            lines.append("- data_quality: n/a")

    lines.extend(
        [
            "",
            "## Split / Recipe / Hashes",
            f"- preprocess_variant: {_format_value(preprocess_variant)}",
            f"- split.strategy: {_format_value(split_payload.get('strategy'))}",
            f"- split.test_size: {_format_value(split_payload.get('test_size'))}",
            f"- split.seed: {_format_value(split_payload.get('seed'))}",
            f"- split_hash: {_format_value(split_hash)}",
            f"- recipe_hash: {_format_value(recipe_hash)}",
        ]
    )
    if split_payload.get("group_column"):
        lines.append(f"- split.group_column: {_format_value(split_payload.get('group_column'))}")
    if split_payload.get("time_column"):
        lines.append(f"- split.time_column: {_format_value(split_payload.get('time_column'))}")

    lines.extend(
        [
            "",
            f"## Models Tried (Top {max_models})",
        ]
    )
    _append_models_table(lines, leaderboard_rows, max_models)

    lines.extend(
        [
            "",
            "## Recommendation",
            f"- model_id: {_format_value(recommended_model_id)}",
            f"- primary_metric: {_format_value(recommended_metric)}",
            f"- best_score: {_format_value(recommended_score)}",
        ]
    )
    if recommended_threshold is not None:
        lines.append(f"- threshold: {_format_value(recommended_threshold)}")
    if recommended_train_ref:
        lines.append(f"- train_task_ref: {_format_value(recommended_train_ref)}")

    actions: list[str] = []
    if not recommended_model_id:
        actions.append("Wait for training/leaderboard to finish, then regenerate the report.")
    if not leaderboard_rows and train_refs:
        actions.append("Run leaderboard to select the best model explicitly.")
    if len(model_variants) <= 1:
        actions.append("Try additional model variants for a stronger baseline.")
    if len(preprocess_variants) <= 1:
        actions.append("Try alternative preprocessing variants for robustness.")
    if not hpo_enabled and model_variants:
        actions.append("Enable pipeline.hpo to explore parameter grids on promising models.")
    if not actions:
        actions.append("Validate the recommended model on a fresh holdout set.")
    actions = actions[:3]

    lines.extend(["", "## Next Actions"])
    lines.extend([f"- {action}" for action in actions])

    return "\n".join(lines) + "\n"
