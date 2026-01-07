"""leaderboard process.

- 複数 train_task を集計して leaderboard.csv を作る
- split_hash / processed_dataset_id が一致しないものは除外（require_comparable=true の場合）
- recommendation.json を出力（推奨モデル）
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import math
import shutil
from pathlib import Path
from typing import Any, Iterable

from ..clearml.hparams import connect_leaderboard_hparams
from ..clearml.ui_logger import log_debug_table, log_plotly, log_scalar
from ..io.bundle_io import load_bundle
from ..ops.clearml_identity import apply_clearml_identity
from ..platform_adapter import (
    PlatformAdapterError,
    get_task_artifact_local_copy,
    hash_config,
    init_task_context,
    is_clearml_enabled,
    resolve_version_props,
    save_config_resolved,
    update_task_properties,
    upload_artifact,
    write_manifest,
    write_out_json,
)


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_direction(value: Any) -> str | None:
    direction = _normalize_str(value)
    if direction == "auto":
        return None
    return direction


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


def _ensure_list(values: Any) -> list[str]:
    if values is None:
        return []
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(values):
        if OmegaConf.is_list(values):
            return [str(v) for v in values if v is not None]
    if isinstance(values, (list, tuple, set)):
        return [str(v) for v in values if v is not None]
    return [str(values)]


def _normalize_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


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


def _format_float(value: Any) -> str:
    num = _to_float(value)
    if num is None:
        return "n/a"
    return f"{num:.6g}"


def _format_ci_interval(interval: dict[str, Any] | None) -> str | None:
    if not isinstance(interval, dict):
        return None
    low = interval.get("low")
    mid = interval.get("mid")
    high = interval.get("high")
    if low is None and mid is None and high is None:
        return None
    return f"[{_format_float(low)}, {_format_float(mid)}, {_format_float(high)}]"


def _stringify_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _stringify_payload(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_stringify_payload(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _resolve_task_id(ctx) -> str | None:
    if getattr(ctx, "task", None) is None:
        return None
    task_obj = ctx.task
    for attr in ("id", "task_id"):
        value = getattr(task_obj, attr, None)
        if value:
            return str(value)
    return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_run_dir(ref: str) -> Path:
    path = Path(ref).expanduser()
    if path.is_file():
        return path.parent
    return path


def _resolve_model_bundle_path(run_dir: Path, model_id: str | None) -> Path | None:
    if model_id:
        candidate = Path(model_id).expanduser()
        if candidate.exists():
            return candidate.resolve()
    candidate = run_dir / "model_bundle.joblib"
    if candidate.exists():
        return candidate.resolve()
    return None


def _extract_variants(bundle: Any) -> tuple[str | None, str | None]:
    model_variant = None
    preprocess_variant = None
    if isinstance(bundle, dict):
        model_variant = _normalize_str(bundle.get("model_variant"))
        preprocess_bundle = bundle.get("preprocess_bundle")
        if isinstance(preprocess_bundle, dict):
            preprocess_variant = _normalize_str(preprocess_bundle.get("preprocess_variant"))
    return model_variant, preprocess_variant


def _extract_metric_ci(out: dict[str, Any]) -> dict[str, float | None] | None:
    if not isinstance(out, dict):
        return None
    for candidate in (
        out.get("primary_metric_ci"),
        out.get("metric_ci"),
        out.get("metrics_ci"),
    ):
        if isinstance(candidate, dict):
            low = _to_float(candidate.get("low"))
            mid = _to_float(candidate.get("mid"))
            high = _to_float(candidate.get("high"))
            if low is None and mid is None and high is None:
                continue
            return {"low": low, "mid": mid, "high": high}
    return None


def _build_entry(
    *,
    out: dict[str, Any],
    manifest: dict[str, Any] | None,
    train_task_ref: str,
    model_bundle_path: Path | None,
    expected_primary_metric: str | None,
    expected_direction: str | None,
    expected_seed: int | None,
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []

    processed_dataset_id = _normalize_str(out.get("processed_dataset_id"))
    split_hash = _normalize_str(out.get("split_hash"))
    recipe_hash = _normalize_str(out.get("recipe_hash"))
    model_id = _normalize_str(out.get("model_id"))
    best_score = _to_float(out.get("best_score"))
    task_type = _normalize_str(out.get("task_type"))

    primary_metric = _normalize_str(out.get("primary_metric")) or expected_primary_metric
    if primary_metric is None:
        errors.append("primary_metric is missing.")

    inputs = {}
    if isinstance(manifest, dict):
        inputs = manifest.get("inputs") or {}
    direction = _normalize_direction(inputs.get("direction")) or expected_direction
    task_type = task_type or _normalize_str(inputs.get("task_type"))
    if task_type is None:
        task_type = "regression"
    seed = _normalize_int(inputs.get("seed"))
    if seed is None:
        seed = expected_seed

    if direction is None:
        errors.append("direction is missing.")
    if processed_dataset_id is None:
        errors.append("processed_dataset_id is missing.")
    if split_hash is None:
        errors.append("split_hash is missing.")
    if recipe_hash is None:
        errors.append("recipe_hash is missing.")
    if model_id is None:
        errors.append("model_id is missing.")
    if best_score is None:
        errors.append("best_score is missing or invalid.")

    model_variant = _normalize_str(inputs.get("model_variant"))
    preprocess_variant = None

    if model_bundle_path is not None:
        try:
            bundle = load_bundle(model_bundle_path)
            bundle_model_variant, bundle_preprocess_variant = _extract_variants(bundle)
            if model_variant is None:
                model_variant = bundle_model_variant
            preprocess_variant = bundle_preprocess_variant
        except Exception as exc:
            warnings.append(f"Failed to load model_bundle.joblib: {exc}")

    if model_variant is None:
        model_variant = "unknown"
    if preprocess_variant is None:
        preprocess_variant = "unknown"

    metric_ci = _extract_metric_ci(out)
    if errors:
        return None, warnings, errors

    threshold_payload = None
    threshold_value = _to_float(out.get("best_threshold"))
    threshold_metric = _normalize_str(out.get("threshold_metric"))
    threshold_score = _to_float(out.get("threshold_score"))
    if threshold_value is not None or threshold_metric or threshold_score is not None:
        threshold_payload = {
            "best_threshold": threshold_value,
            "metric": threshold_metric,
            "score": threshold_score,
        }
    calibration_payload = out.get("calibration") if isinstance(out.get("calibration"), dict) else None
    imbalance_payload = out.get("imbalance") if isinstance(out.get("imbalance"), dict) else None
    uncertainty_payload = out.get("uncertainty") if isinstance(out.get("uncertainty"), dict) else None

    entry = {
        "train_task_ref": train_task_ref,
        "train_task_id": _normalize_str(out.get("train_task_id")) or None,
        "model_id": model_id,
        "best_score": best_score,
        "primary_metric": primary_metric,
        "direction": direction,
        "seed": seed,
        "task_type": task_type,
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "preprocess_variant": preprocess_variant,
        "model_variant": model_variant,
        "primary_metric_ci_low": metric_ci.get("low") if metric_ci else None,
        "primary_metric_ci_mid": metric_ci.get("mid") if metric_ci else None,
        "primary_metric_ci_high": metric_ci.get("high") if metric_ci else None,
        "primary_metric_ci": metric_ci,
        "thresholding": threshold_payload,
        "calibration": calibration_payload,
        "imbalance": imbalance_payload,
        "uncertainty": uncertainty_payload,
        "n_classes": _normalize_int(out.get("n_classes")),
        "class_labels": out.get("class_labels"),
    }
    return entry, warnings, []


def _compare_comparability(entry: dict[str, Any], ref: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    if ref.get("processed_dataset_id") and entry.get("processed_dataset_id") != ref.get(
        "processed_dataset_id"
    ):
        mismatches.append("processed_dataset_id mismatch")
    if ref.get("split_hash") and entry.get("split_hash") != ref.get("split_hash"):
        mismatches.append("split_hash mismatch")
    if ref.get("primary_metric") and entry.get("primary_metric") != ref.get("primary_metric"):
        mismatches.append("primary_metric mismatch")
    if ref.get("direction") and entry.get("direction") != ref.get("direction"):
        mismatches.append("direction mismatch")
    if ref.get("task_type") and entry.get("task_type") != ref.get("task_type"):
        mismatches.append("task_type mismatch")
    if ref.get("seed") is not None:
        if entry.get("seed") is None:
            mismatches.append("seed missing")
        elif entry.get("seed") != ref.get("seed"):
            mismatches.append("seed mismatch")
    return mismatches


def _write_leaderboard_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    fieldnames = [
        "rank",
        "best_score",
        "primary_metric_ci_low",
        "primary_metric_ci_mid",
        "primary_metric_ci_high",
        "primary_metric",
        "task_type",
        "model_id",
        "preprocess_variant",
        "model_variant",
        "train_task_ref",
        "processed_dataset_id",
        "split_hash",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _build_top_k_plotly(rows: list[dict[str, Any]], *, metric_name: str | None) -> Any | None:
    try:
        import plotly.graph_objects as go  # type: ignore
    except Exception:
        return None
    labels: list[str] = []
    scores: list[float] = []
    for row in rows:
        label = (
            row.get("model_variant")
            or row.get("model_id")
            or row.get("train_task_ref")
            or row.get("rank")
        )
        label_text = str(label) if label is not None else "unknown"
        if len(label_text) > 30:
            label_text = label_text[:27] + "..."
        labels.append(f"{row.get('rank')}:{label_text}")
        scores.append(float(row.get("best_score")))
    title = f"Top-K {metric_name}" if metric_name else "Top-K Scores"
    fig = go.Figure(go.Bar(x=labels, y=scores, marker_color="#4C78A8"))
    fig.update_layout(
        title=title,
        xaxis_title="rank/model",
        yaxis_title=metric_name or "score",
        margin=dict(l=40, r=20, t=40, b=80),
    )
    return fig


def _write_top_k_bar_png(
    rows: list[dict[str, Any]],
    output_path: Path,
    *,
    metric_name: str | None,
) -> Path | None:
    try:
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None
    labels: list[str] = []
    scores: list[float] = []
    for row in rows:
        label = (
            row.get("model_variant")
            or row.get("model_id")
            or row.get("train_task_ref")
            or row.get("rank")
        )
        label_text = str(label) if label is not None else "unknown"
        if len(label_text) > 30:
            label_text = label_text[:27] + "..."
        labels.append(f"{row.get('rank')}:{label_text}")
        scores.append(float(row.get("best_score")))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(range(len(scores)), scores, color="#4C78A8")
    ax.set_ylabel(metric_name or "score")
    ax.set_title(f"Top-K {metric_name}" if metric_name else "Top-K Scores")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def _copy_recommended_plot(
    cfg: Any,
    recommended: dict[str, Any],
    output_dir: Path,
    *,
    clearml_enabled: bool,
) -> Path | None:
    candidates = [
        "confusion_matrix.png",
        "residuals.png",
        "feature_importance.png",
        "roc_curve.png",
    ]
    if clearml_enabled:
        task_id = _normalize_str(
            recommended.get("train_task_id") or recommended.get("train_task_ref")
        )
        if not task_id:
            return None
        for name in candidates:
            try:
                src = get_task_artifact_local_copy(cfg, task_id, name)
            except PlatformAdapterError:
                continue
            if not src.exists():
                continue
            dest = output_dir / "recommended_plot.png"
            shutil.copy2(src, dest)
            return dest
    else:
        ref = _normalize_str(recommended.get("train_task_ref"))
        if not ref:
            return None
        run_dir = _resolve_run_dir(ref)
        for name in candidates:
            src = run_dir / name
            if not src.exists():
                continue
            dest = output_dir / "recommended_plot.png"
            shutil.copy2(src, dest)
            return dest
    return None


def run(cfg: Any) -> None:
    identity = apply_clearml_identity(cfg, stage=cfg.task.stage)
    ctx = init_task_context(
        cfg,
        stage=cfg.task.stage,
        task_name="leaderboard",
        tags=identity.tags,
        properties=identity.user_properties,
    )
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)
    lb_cfg = getattr(cfg, "leaderboard", None)
    train_task_ids = _ensure_list(getattr(lb_cfg, "train_task_ids", None))
    train_run_dirs = _ensure_list(getattr(lb_cfg, "train_run_dirs", None))
    require_comparable = bool(getattr(lb_cfg, "require_comparable", True))
    top_k = int(getattr(lb_cfg, "top_k", 10) or 0)

    if clearml_enabled:
        refs = train_task_ids
        if not refs:
            raise ValueError("leaderboard.train_task_ids is required when ClearML is enabled.")
    else:
        refs = train_run_dirs or train_task_ids
        if not refs:
            raise ValueError(
                "leaderboard.train_run_dirs (or train_task_ids) is required when ClearML is disabled."
            )

    expected_primary_metric = _normalize_str(getattr(getattr(cfg, "eval", None), "primary_metric", None))
    expected_direction = _normalize_direction(getattr(getattr(cfg, "eval", None), "direction", None))
    expected_seed = _normalize_int(getattr(getattr(cfg, "eval", None), "seed", None))
    expected_task_type = _normalize_str(getattr(getattr(cfg, "eval", None), "task_type", None)) or "regression"

    connect_leaderboard_hparams(
        ctx,
        cfg,
        primary_metric=expected_primary_metric,
        direction=expected_direction,
        require_comparable=require_comparable,
        top_k=top_k,
    )

    ref_values: dict[str, Any] = {
        "processed_dataset_id": None,
        "split_hash": None,
        "recipe_hash": None,
        "primary_metric": expected_primary_metric,
        "direction": expected_direction,
        "seed": expected_seed,
        "task_type": expected_task_type,
    }

    entries: list[dict[str, Any]] = []
    excluded: list[str] = []
    warnings: list[str] = []
    non_comparable: list[str] = []

    for ref in refs:
        entry: dict[str, Any] | None = None
        entry_warnings: list[str] = []
        entry_errors: list[str] = []
        if clearml_enabled:
            try:
                out_path = get_task_artifact_local_copy(cfg, ref, "out.json")
                manifest_path = get_task_artifact_local_copy(cfg, ref, "manifest.json")
            except PlatformAdapterError as exc:
                entry_errors.append(str(exc))
                out_path = None
                manifest_path = None
            if out_path is not None and manifest_path is not None:
                out = _load_json(out_path)
                manifest = _load_json(manifest_path)
                model_bundle_path = None
                try:
                    model_bundle_path = get_task_artifact_local_copy(cfg, ref, "model_bundle.joblib")
                except PlatformAdapterError as exc:
                    entry_warnings.append(str(exc))
                entry, build_warnings, entry_errors = _build_entry(
                    out=out,
                    manifest=manifest,
                    train_task_ref=str(ref),
                    model_bundle_path=model_bundle_path,
                    expected_primary_metric=expected_primary_metric,
                    expected_direction=expected_direction,
                    expected_seed=expected_seed,
                )
                entry_warnings.extend(build_warnings)
        else:
            run_dir = _resolve_run_dir(str(ref))
            if not run_dir.exists():
                entry_errors.append(f"train run dir not found: {run_dir}")
            else:
                out_path = run_dir / "out.json"
                manifest_path = run_dir / "manifest.json"
                if not out_path.exists() or not manifest_path.exists():
                    entry_errors.append(f"out.json/manifest.json missing under {run_dir}")
                else:
                    out = _load_json(out_path)
                    manifest = _load_json(manifest_path)
                    model_bundle_path = _resolve_model_bundle_path(run_dir, _normalize_str(out.get("model_id")))
                    if model_bundle_path is None:
                        entry_warnings.append(f"model_bundle.joblib not found under {run_dir}")
                    entry, build_warnings, entry_errors = _build_entry(
                        out=out,
                        manifest=manifest,
                        train_task_ref=str(run_dir),
                        model_bundle_path=model_bundle_path,
                        expected_primary_metric=expected_primary_metric,
                        expected_direction=expected_direction,
                        expected_seed=expected_seed,
                    )
                    entry_warnings.extend(build_warnings)

        for warning in entry_warnings:
            warnings.append(f"{ref}: {warning}")
        if entry_errors:
            excluded.append(str(ref))
            for error in entry_errors:
                warnings.append(f"{ref}: {error}")
            continue
        if entry is None:
            excluded.append(str(ref))
            warnings.append(f"{ref}: entry build failed")
            continue

        if clearml_enabled and entry.get("train_task_id") is None:
            entry["train_task_id"] = entry.get("train_task_ref")

        for key in (
            "processed_dataset_id",
            "split_hash",
            "recipe_hash",
            "primary_metric",
            "direction",
            "seed",
            "task_type",
        ):
            if ref_values.get(key) is None and entry.get(key) is not None:
                ref_values[key] = entry.get(key)

        mismatches = _compare_comparability(entry, ref_values)
        if mismatches:
            if require_comparable:
                excluded.append(str(ref))
                warnings.append(f"{ref}: excluded ({', '.join(mismatches)})")
                continue
            non_comparable.append(str(ref))
            warnings.append(f"{ref}: non-comparable ({', '.join(mismatches)})")

        entries.append(entry)

    if not entries:
        raise ValueError("No comparable train runs found for leaderboard.")

    direction = _normalize_direction(ref_values.get("direction")) or "minimize"
    if direction not in ("minimize", "maximize"):
        warnings.append(f"Invalid direction {direction}; defaulting to minimize.")
        direction = "minimize"

    entries_sorted = sorted(
        entries,
        key=lambda item: item["best_score"],
        reverse=direction == "maximize",
    )

    if top_k <= 0:
        top_k = len(entries_sorted)
    rows = []
    for idx, entry in enumerate(entries_sorted[:top_k], start=1):
        rows.append(
            {
                "rank": idx,
                "best_score": entry["best_score"],
                "primary_metric_ci_low": entry.get("primary_metric_ci_low"),
                "primary_metric_ci_mid": entry.get("primary_metric_ci_mid"),
                "primary_metric_ci_high": entry.get("primary_metric_ci_high"),
                "primary_metric": entry["primary_metric"],
                "task_type": entry.get("task_type"),
                "model_id": entry["model_id"],
                "preprocess_variant": entry["preprocess_variant"],
                "model_variant": entry["model_variant"],
                "train_task_ref": entry["train_task_ref"],
                "processed_dataset_id": entry["processed_dataset_id"],
                "split_hash": entry["split_hash"],
            }
        )

    leaderboard_path = ctx.output_dir / "leaderboard.csv"
    _write_leaderboard_csv(leaderboard_path, rows)

    recommended = entries_sorted[0]
    recommendation = {
        "recommended_train_task_ref": recommended["train_task_ref"],
        "recommended_model_id": recommended["model_id"],
        "recommended_best_score": recommended["best_score"],
        "recommended_primary_metric": recommended["primary_metric"],
    }
    recommendation_path = ctx.output_dir / "recommendation.json"
    recommendation_path.write_text(
        json.dumps(recommendation, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary_lines = [
        "# Leaderboard Summary",
        "",
        f"- total_runs: {len(refs)}",
        f"- included: {len(entries_sorted)}",
        f"- excluded: {len(excluded)}",
        f"- require_comparable: {require_comparable}",
        f"- primary_metric: {ref_values.get('primary_metric') or 'unknown'}",
        f"- direction: {direction}",
        f"- task_type: {ref_values.get('task_type') or 'unknown'}",
        f"- seed: {ref_values.get('seed') if ref_values.get('seed') is not None else 'unknown'}",
        f"- processed_dataset_id: {ref_values.get('processed_dataset_id') or 'unknown'}",
        f"- split_hash: {ref_values.get('split_hash') or 'unknown'}",
        "",
        "## Top Results",
    ]
    for row in rows:
        line = (
            f"- rank {row['rank']}: best_score={row['best_score']} model_id={row['model_id']} "
            f"train_task_ref={row['train_task_ref']}"
        )
        if row["rank"] == 1:
            ci_low = row.get("primary_metric_ci_low")
            ci_high = row.get("primary_metric_ci_high")
            if ci_low is not None and ci_high is not None:
                line += f" ci=[{ci_low:.4g}, {ci_high:.4g}]"
        summary_lines.append(line)
    if warnings:
        summary_lines.extend(["", "## Warnings"])
        summary_lines.extend([f"- {line}" for line in warnings])
    summary_path = ctx.output_dir / "summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    if clearml_enabled and rows:
        best_score = recommended.get("best_score")
        if best_score is not None:
            log_scalar(ctx.task, "leaderboard", "best_score", best_score, step=0)
        metric_name = ref_values.get("primary_metric") or recommended.get("primary_metric")
        top_k_fig = _build_top_k_plotly(rows, metric_name=metric_name)
        fallback_path = None
        if top_k_fig is None:
            fallback_path = _write_top_k_bar_png(
                rows,
                ctx.output_dir / "top_k_scores.png",
                metric_name=metric_name,
            )
        log_plotly(ctx.task, "leaderboard", "top_k_scores", top_k_fig or fallback_path, step=0)
        log_debug_table(ctx.task, "leaderboard", "top_k_table", rows[: min(10, len(rows))], step=0)

    max_models = min(5, len(rows))
    decision_rows = rows[:max_models]
    recommended_ci = _format_ci_interval(recommended.get("primary_metric_ci"))
    decision_lines = [
        "# Decision Summary",
        "",
        "## Recommendation",
        f"- recommended_model_id: {recommended.get('model_id')}",
        f"- train_task_ref: {recommended.get('train_task_ref')}",
        f"- primary_metric: {recommended.get('primary_metric')} ({direction})",
        f"- best_score: {_format_float(recommended.get('best_score'))}",
    ]
    if recommended_ci:
        decision_lines.append(f"- primary_metric_ci: {recommended_ci}")
    if recommended.get("task_type"):
        decision_lines.append(f"- task_type: {recommended.get('task_type')}")
    if recommended.get("n_classes") is not None:
        decision_lines.append(f"- n_classes: {recommended.get('n_classes')}")
    decision_lines.extend(
        [
            "",
            "## Comparability",
            f"- require_comparable: {require_comparable}",
            f"- processed_dataset_id: {ref_values.get('processed_dataset_id') or 'unknown'}",
            f"- split_hash: {ref_values.get('split_hash') or 'unknown'}",
            f"- recipe_hash: {ref_values.get('recipe_hash') or 'unknown'}",
            f"- primary_metric: {ref_values.get('primary_metric') or 'unknown'}",
            f"- direction: {direction}",
            f"- task_type: {ref_values.get('task_type') or 'unknown'}",
            f"- seed: {ref_values.get('seed') if ref_values.get('seed') is not None else 'unknown'}",
            f"- excluded_count: {len(excluded)}",
        ]
    )
    if warnings:
        decision_lines.append(f"- warning_count: {len(warnings)} (see summary.md)")
    decision_lines.extend(
        [
            "",
            "## Top Models",
            f"- source: {leaderboard_path.name}",
            "",
            "| rank | model_variant | preprocess_variant | best_score | primary_metric | ci |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in decision_rows:
        ci = _format_ci_interval(
            {
                "low": row.get("primary_metric_ci_low"),
                "mid": row.get("primary_metric_ci_mid"),
                "high": row.get("primary_metric_ci_high"),
            }
        ) or "n/a"
        decision_lines.append(
            "| {rank} | {model_variant} | {preprocess_variant} | {best_score} | {metric} | {ci} |".format(
                rank=row.get("rank"),
                model_variant=row.get("model_variant") or "unknown",
                preprocess_variant=row.get("preprocess_variant") or "unknown",
                best_score=_format_float(row.get("best_score")),
                metric=row.get("primary_metric") or "unknown",
                ci=ci,
            )
        )
    decision_lines.extend(["", "## Extra Capabilities"])
    thresholding = recommended.get("thresholding") or {}
    if thresholding.get("best_threshold") is not None:
        decision_lines.append(
            "- thresholding: enabled metric={metric} best_threshold={thr} score={score}".format(
                metric=thresholding.get("metric") or "unknown",
                thr=_format_float(thresholding.get("best_threshold")),
                score=_format_float(thresholding.get("score")),
            )
        )
    else:
        decision_lines.append("- thresholding: disabled")
    calibration = recommended.get("calibration") or {}
    if calibration.get("enabled"):
        decision_lines.append(
            "- calibration: enabled method={method} mode={mode}".format(
                method=calibration.get("method") or "unknown",
                mode=calibration.get("mode") or "unknown",
            )
        )
    else:
        decision_lines.append("- calibration: disabled")
    uncertainty = recommended.get("uncertainty") or {}
    if uncertainty.get("enabled"):
        decision_lines.append(
            "- uncertainty: enabled method={method} alpha={alpha} q={q}".format(
                method=uncertainty.get("method") or "unknown",
                alpha=_format_float(uncertainty.get("alpha")),
                q=_format_float(uncertainty.get("q")),
            )
        )
    else:
        decision_lines.append("- uncertainty: disabled")
    imbalance = recommended.get("imbalance") or {}
    if imbalance.get("enabled"):
        decision_lines.append(
            "- imbalance_handling: enabled strategy={strategy} applied={applied}".format(
                strategy=imbalance.get("strategy") or "unknown",
                applied=imbalance.get("applied"),
            )
        )
    else:
        decision_lines.append("- imbalance_handling: disabled")
    decision_lines.extend(["", "## Promote Command", "```bash"])
    decision_lines.append(
        f"python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir={ctx.output_dir}"
    )
    task_id = _resolve_task_id(ctx)
    if task_id:
        decision_lines.append(f"# ClearML task id (optional): {task_id}")
    decision_lines.append("```")
    decision_summary_path = ctx.output_dir / "decision_summary.md"
    decision_summary_path.write_text("\n".join(decision_lines) + "\n", encoding="utf-8")

    decision_payload = {
        "recommended": {
            "model_id": recommended.get("model_id"),
            "train_task_ref": recommended.get("train_task_ref"),
            "train_task_id": recommended.get("train_task_id"),
            "best_score": recommended.get("best_score"),
            "primary_metric": recommended.get("primary_metric"),
            "primary_metric_ci": recommended.get("primary_metric_ci"),
            "task_type": recommended.get("task_type"),
            "n_classes": recommended.get("n_classes"),
            "class_labels": recommended.get("class_labels"),
            "thresholding": recommended.get("thresholding"),
            "calibration": recommended.get("calibration"),
            "imbalance": recommended.get("imbalance"),
            "uncertainty": recommended.get("uncertainty"),
        },
        "comparability": {
            "require_comparable": require_comparable,
            "processed_dataset_id": ref_values.get("processed_dataset_id"),
            "split_hash": ref_values.get("split_hash"),
            "recipe_hash": ref_values.get("recipe_hash"),
            "primary_metric": ref_values.get("primary_metric"),
            "direction": direction,
            "task_type": ref_values.get("task_type"),
            "seed": ref_values.get("seed"),
        },
        "leaderboard_csv": str(leaderboard_path),
        "top_models": rows[: min(10, len(rows))],
        "excluded_count": len(excluded),
        "warning_count": len(warnings),
    }
    decision_summary_json_path = ctx.output_dir / "decision_summary.json"
    decision_summary_json_path.write_text(
        json.dumps(_stringify_payload(decision_payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    viz_enabled = bool(_cfg_value(cfg, "viz.enabled", True))
    recommended_plot_path: Path | None = None
    if viz_enabled and not clearml_enabled:
        recommended_plot_path = _copy_recommended_plot(
            cfg,
            recommended,
            ctx.output_dir,
            clearml_enabled=False,
        )

    if clearml_enabled:
        for name, path in [
            ("leaderboard.csv", leaderboard_path),
            ("recommendation.json", recommendation_path),
            ("summary.md", summary_path),
            ("decision_summary.md", decision_summary_path),
            ("decision_summary.json", decision_summary_json_path),
        ]:
            upload_artifact(ctx, name, path)
        update_task_properties(
            ctx,
            {
                "recommended_train_task_id": recommended.get("train_task_id") or None,
                "recommended_model_id": recommended.get("model_id"),
                "excluded_count": len(excluded),
            },
        )

    out = {
        "leaderboard_csv": str(leaderboard_path),
        "recommended_train_task_id": recommended.get("train_task_id") or None,
        "recommended_train_task_ref": recommended.get("train_task_ref"),
        "recommended_model_id": recommended.get("model_id"),
        "recommended_best_score": recommended.get("best_score"),
        "recommended_primary_metric": recommended.get("primary_metric"),
        "excluded_count": len(excluded),
    }
    if non_comparable:
        out["non_comparable_count"] = len(non_comparable)
    if warnings:
        out["warnings"] = warnings
    write_out_json(ctx, out)

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    inputs = {
        "train_task_refs": [str(ref) for ref in refs],
        "require_comparable": require_comparable,
        "top_k": top_k,
        "primary_metric": ref_values.get("primary_metric"),
        "direction": direction,
        "seed": ref_values.get("seed"),
        "task_type": ref_values.get("task_type"),
        "processed_dataset_id": ref_values.get("processed_dataset_id"),
        "split_hash": ref_values.get("split_hash"),
        "recipe_hash": ref_values.get("recipe_hash"),
    }
    outputs = {
        "leaderboard_csv": str(leaderboard_path),
        "recommended_train_task_id": recommended.get("train_task_id") or None,
        "recommended_model_id": recommended.get("model_id"),
        "excluded_count": len(excluded),
    }
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "leaderboard",
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
