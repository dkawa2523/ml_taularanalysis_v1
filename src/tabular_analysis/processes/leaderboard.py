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
from pathlib import Path
from typing import Any, Iterable

from ..io.bundle_io import load_bundle
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

    primary_metric = _normalize_str(out.get("primary_metric")) or expected_primary_metric
    if primary_metric is None:
        errors.append("primary_metric is missing.")

    inputs = {}
    if isinstance(manifest, dict):
        inputs = manifest.get("inputs") or {}
    direction = _normalize_str(inputs.get("direction")) or expected_direction
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

    if errors:
        return None, warnings, errors

    entry = {
        "train_task_ref": train_task_ref,
        "train_task_id": _normalize_str(out.get("train_task_id")) or None,
        "model_id": model_id,
        "best_score": best_score,
        "primary_metric": primary_metric,
        "direction": direction,
        "seed": seed,
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "preprocess_variant": preprocess_variant,
        "model_variant": model_variant,
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
        "primary_metric",
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


def run(cfg: Any) -> None:
    ctx = init_task_context(cfg, stage=cfg.task.stage, task_name="leaderboard")
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
    expected_direction = _normalize_str(getattr(getattr(cfg, "eval", None), "direction", None))
    expected_seed = _normalize_int(getattr(getattr(cfg, "eval", None), "seed", None))

    ref_values: dict[str, Any] = {
        "processed_dataset_id": None,
        "split_hash": None,
        "recipe_hash": None,
        "primary_metric": expected_primary_metric,
        "direction": expected_direction,
        "seed": expected_seed,
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

    direction = _normalize_str(ref_values.get("direction")) or "minimize"
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
                "primary_metric": entry["primary_metric"],
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
        f"- seed: {ref_values.get('seed') if ref_values.get('seed') is not None else 'unknown'}",
        f"- processed_dataset_id: {ref_values.get('processed_dataset_id') or 'unknown'}",
        f"- split_hash: {ref_values.get('split_hash') or 'unknown'}",
        "",
        "## Top Results",
    ]
    for row in rows:
        summary_lines.append(
            f"- rank {row['rank']}: best_score={row['best_score']} model_id={row['model_id']} "
            f"train_task_ref={row['train_task_ref']}"
        )
    if warnings:
        summary_lines.extend(["", "## Warnings"])
        summary_lines.extend([f"- {line}" for line in warnings])
    summary_path = ctx.output_dir / "summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    if clearml_enabled:
        for name, path in [
            ("leaderboard.csv", leaderboard_path),
            ("recommendation.json", recommendation_path),
            ("summary.md", summary_path),
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
