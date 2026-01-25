"""champion_challenger process.

- Compare current production (champion) vs a challenger model
- Emit decision artifacts for operational review
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from ..ops.clearml_identity import apply_clearml_identity
from ..platform_adapter import (
    hash_config,
    init_task_context,
    is_clearml_enabled,
    get_task_artifact_local_copy,
    resolve_version_props,
    save_config_resolved,
    update_task_properties,
    upload_artifact,
    write_manifest,
    write_out_json,
)
from ..ops.alerting import emit_alert
from ..registry.metrics import metric_direction
from ..registry.model_registry_state import get_current_entry, load_registry_state


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except Exception:
        return None
    if num != num:  # NaN
        return None
    return num


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


def _base_output_dir(cfg: Any) -> Path:
    return Path(getattr(cfg.run, "output_dir", "outputs")).expanduser().resolve()


def _resolve_run_dir(ref: str) -> Path | None:
    path = Path(ref).expanduser()
    if path.exists():
        return path if path.is_dir() else path.parent
    return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return _load_json(path)
    except Exception:
        return None


def _resolve_model_entry(
    cfg: Any,
    ref: str,
    *,
    clearml_enabled: bool,
    role: str,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    run_dir = _resolve_run_dir(ref)
    out_path = None
    manifest_path = None
    task_id = None
    if run_dir is not None:
        out_path = run_dir / "out.json"
        manifest_path = run_dir / "manifest.json"
    elif clearml_enabled:
        task_id = ref
        out_path = get_task_artifact_local_copy(cfg, task_id, "out.json")
        manifest_path = get_task_artifact_local_copy(cfg, task_id, "manifest.json")
        run_dir = out_path.parent
    else:
        raise FileNotFoundError(f"{role} model reference not found: {ref}")

    if out_path is None or not out_path.exists():
        raise FileNotFoundError(f"{role} out.json not found for ref: {ref}")
    out = _load_json(out_path)
    manifest = _load_optional_json(manifest_path) if manifest_path is not None else None
    inputs = manifest.get("inputs") if isinstance(manifest, dict) else None
    if not isinstance(inputs, Mapping):
        inputs = {}

    model_id = _normalize_str(out.get("model_id"))
    primary_metric = _normalize_str(out.get("primary_metric"))
    best_score = _to_float(out.get("best_score"))
    processed_dataset_id = _normalize_str(out.get("processed_dataset_id"))
    split_hash = _normalize_str(out.get("split_hash"))
    recipe_hash = _normalize_str(out.get("recipe_hash"))
    task_type = _normalize_str(out.get("task_type")) or _normalize_str(inputs.get("task_type"))
    direction = _normalize_str(inputs.get("direction"))

    if primary_metric is None:
        raise ValueError(f"{role} primary_metric is missing.")
    if best_score is None:
        raise ValueError(f"{role} best_score is missing or invalid.")
    if task_type is None:
        task_type = "regression"
        warnings.append(f"{role} task_type missing; defaulted to regression.")
    if direction is None:
        direction = metric_direction(primary_metric, task_type)
        warnings.append(f"{role} direction missing; inferred from metric.")

    entry = {
        "role": role,
        "model_id": model_id,
        "best_score": best_score,
        "primary_metric": primary_metric,
        "direction": direction,
        "task_type": task_type,
        "processed_dataset_id": processed_dataset_id,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "train_task_ref": str(run_dir) if run_dir else None,
        "train_task_id": _normalize_str(out.get("train_task_id")) or task_id,
    }
    return entry, warnings


def _resolve_eval_ref(
    cfg: Any,
    ref: str,
    *,
    clearml_enabled: bool,
) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    run_dir = _resolve_run_dir(ref)
    out_path = None
    if run_dir is not None:
        out_path = run_dir / "out.json"
    elif clearml_enabled:
        try:
            out_path = get_task_artifact_local_copy(cfg, ref, "out.json")
            run_dir = out_path.parent
        except Exception:
            out_path = None
    if out_path is None or not out_path.exists():
        warnings.append(f"eval_dataset_ref out.json not found: {ref}")
        return None, warnings
    try:
        out = _load_json(out_path)
    except Exception:
        warnings.append(f"eval_dataset_ref out.json invalid: {ref}")
        return None, warnings
    payload = {
        "processed_dataset_id": _normalize_str(out.get("processed_dataset_id")),
        "split_hash": _normalize_str(out.get("split_hash")),
        "run_dir": str(run_dir) if run_dir else None,
    }
    return payload, warnings


def _compare_comparability(
    champion: Mapping[str, Any],
    challenger: Mapping[str, Any],
    eval_ref: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    champ_processed = _normalize_str(champion.get("processed_dataset_id"))
    chal_processed = _normalize_str(challenger.get("processed_dataset_id"))
    champ_split = _normalize_str(champion.get("split_hash"))
    chal_split = _normalize_str(challenger.get("split_hash"))

    processed_match = None
    split_match = None

    if champ_processed and chal_processed:
        processed_match = champ_processed == chal_processed
        if not processed_match:
            warnings.append("processed_dataset_id mismatch between champion and challenger.")
    else:
        warnings.append("processed_dataset_id missing for comparability check.")

    if champ_split and chal_split:
        split_match = champ_split == chal_split
        if not split_match:
            warnings.append("split_hash mismatch between champion and challenger.")
    else:
        warnings.append("split_hash missing for comparability check.")

    if eval_ref:
        eval_processed = _normalize_str(eval_ref.get("processed_dataset_id"))
        eval_split = _normalize_str(eval_ref.get("split_hash"))
        if eval_processed and champ_processed and eval_processed != champ_processed:
            warnings.append("eval_dataset_ref processed_dataset_id differs from champion.")
        if eval_processed and chal_processed and eval_processed != chal_processed:
            warnings.append("eval_dataset_ref processed_dataset_id differs from challenger.")
        if eval_split and champ_split and eval_split != champ_split:
            warnings.append("eval_dataset_ref split_hash differs from champion.")
        if eval_split and chal_split and eval_split != chal_split:
            warnings.append("eval_dataset_ref split_hash differs from challenger.")

    return {
        "processed_dataset_id_match": processed_match,
        "split_hash_match": split_match,
    }, warnings


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def run(cfg: Any) -> None:
    identity = apply_clearml_identity(cfg, stage=cfg.task.stage)
    ctx = init_task_context(
        cfg,
        stage=cfg.task.stage,
        task_name="champion_challenger",
        tags=identity.tags,
        properties=identity.user_properties,
    )
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)
    usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id")) or _normalize_str(
        _cfg_value(cfg, "usecase_id")
    ) or "unknown"

    cc_cfg = _cfg_value(cfg, "champion_challenger", {})
    champion_ref = _normalize_str(_cfg_value(cc_cfg, "champion_model_ref"))
    challenger_ref = _normalize_str(_cfg_value(cc_cfg, "challenger_model_ref"))
    eval_ref = _normalize_str(_cfg_value(cc_cfg, "eval_dataset_ref"))
    threshold = _to_float(_cfg_value(cc_cfg, "decision_threshold", 0.0)) or 0.0

    if not challenger_ref:
        raise ValueError("champion_challenger.challenger_model_ref is required.")

    warnings: list[str] = []
    if not champion_ref:
        if clearml_enabled:
            raise ValueError("champion_model_ref is required when ClearML is enabled.")
        registry_path = _base_output_dir(cfg) / "model_registry_state.json"
        registry_state = load_registry_state(registry_path)
        entry = get_current_entry(registry_state, usecase_id=usecase_id, stage="production")
        if not entry:
            raise ValueError("No production model found in model_registry_state.json.")
        champion_ref = _normalize_str(entry.get("train_task_ref") or entry.get("train_task_id"))
        if not champion_ref:
            champion_ref = _normalize_str(entry.get("model_id"))
        if not champion_ref:
            raise ValueError("Production model entry missing train_task_ref/model_id.")

    champion, champ_warnings = _resolve_model_entry(
        cfg, champion_ref, clearml_enabled=clearml_enabled, role="champion"
    )
    challenger, chal_warnings = _resolve_model_entry(
        cfg, challenger_ref, clearml_enabled=clearml_enabled, role="challenger"
    )
    warnings.extend(champ_warnings)
    warnings.extend(chal_warnings)

    eval_payload = None
    if eval_ref:
        eval_payload, eval_warnings = _resolve_eval_ref(cfg, eval_ref, clearml_enabled=clearml_enabled)
        warnings.extend(eval_warnings)

    comparability, comp_warnings = _compare_comparability(champion, challenger, eval_payload)
    warnings.extend(comp_warnings)

    primary_metric = champion.get("primary_metric") or challenger.get("primary_metric")
    direction = champion.get("direction") or challenger.get("direction") or "maximize"
    champion_score = float(champion["best_score"])
    challenger_score = float(challenger["best_score"])

    raw_delta = challenger_score - champion_score
    improvement = raw_delta if direction == "maximize" else champion_score - challenger_score
    if abs(improvement) <= threshold:
        winner = "tie"
    elif improvement > 0:
        winner = "challenger"
    else:
        winner = "champion"

    rationale = (
        f"{winner} selected: delta={improvement:.6g} ({primary_metric}, {direction}), "
        f"threshold={threshold:.6g}"
    )

    csv_rows = [
        {
            "role": "champion",
            "model_id": champion.get("model_id"),
            "best_score": champion_score,
            "primary_metric": primary_metric,
            "direction": direction,
            "processed_dataset_id": champion.get("processed_dataset_id"),
            "split_hash": champion.get("split_hash"),
            "score_delta": 0.0,
            "directional_delta": improvement,
        },
        {
            "role": "challenger",
            "model_id": challenger.get("model_id"),
            "best_score": challenger_score,
            "primary_metric": primary_metric,
            "direction": direction,
            "processed_dataset_id": challenger.get("processed_dataset_id"),
            "split_hash": challenger.get("split_hash"),
            "score_delta": raw_delta,
            "directional_delta": improvement,
        },
    ]

    csv_path = ctx.output_dir / "champion_challenger.csv"
    _write_csv(csv_path, csv_rows)

    decision_payload = {
        "winner": winner,
        "primary_metric": primary_metric,
        "direction": direction,
        "champion_score": champion_score,
        "challenger_score": challenger_score,
        "raw_delta": raw_delta,
        "directional_delta": improvement,
        "decision_threshold": threshold,
        "rationale": rationale,
        "comparability": comparability,
        "champion": champion,
        "challenger": challenger,
        "eval_dataset_ref": eval_ref,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if warnings:
        decision_payload["warnings"] = warnings

    if winner == "champion":
        emit_alert(
            "champion_challenger",
            "warning",
            "Challenger underperformed",
            f"Challenger score did not beat champion: delta={improvement:.6g}, "
            f"threshold={threshold:.6g}",
            {
                "_cfg": cfg,
                "_ctx": ctx,
                "primary_metric": primary_metric,
                "direction": direction,
                "champion_score": champion_score,
                "challenger_score": challenger_score,
                "directional_delta": improvement,
                "decision_threshold": threshold,
                "comparability": comparability,
            },
        )

    decision_path = ctx.output_dir / "decision.json"
    decision_path.write_text(
        json.dumps(decision_payload, ensure_ascii=True, indent=2), encoding="utf-8"
    )

    summary_lines = [
        "# Champion-Challenger Decision",
        "",
        f"- winner: {winner}",
        f"- primary_metric: {primary_metric} ({direction})",
        f"- champion_score: {champion_score:.6g}",
        f"- challenger_score: {challenger_score:.6g}",
        f"- directional_delta: {improvement:.6g}",
        f"- decision_threshold: {threshold:.6g}",
    ]
    if eval_ref:
        summary_lines.append(f"- eval_dataset_ref: {eval_ref}")
    if warnings:
        summary_lines.extend(["", "## Warnings"])
        summary_lines.extend([f"- {line}" for line in warnings])
    summary_path = ctx.output_dir / "summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    if clearml_enabled:
        upload_artifact(ctx, "champion_challenger.csv", csv_path)
        upload_artifact(ctx, "decision.json", decision_path)
        upload_artifact(ctx, "summary.md", summary_path)
        props = {
            "winner": winner,
            "primary_metric": primary_metric,
            "champion_score": champion_score,
            "challenger_score": challenger_score,
            "directional_delta": improvement,
        }
        update_task_properties(ctx, props)

    out = {
        "champion_challenger_csv": str(csv_path),
        "decision_json": str(decision_path),
        "summary_md": str(summary_path),
        "winner": winner,
        "primary_metric": primary_metric,
        "champion_score": champion_score,
        "challenger_score": challenger_score,
        "directional_delta": improvement,
        "champion_model_ref": champion_ref,
        "challenger_model_ref": challenger_ref,
        "eval_dataset_ref": eval_ref,
    }
    if warnings:
        out["warnings"] = warnings
    write_out_json(ctx, out)

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    inputs = {
        "champion_model_ref": champion_ref,
        "challenger_model_ref": challenger_ref,
        "eval_dataset_ref": eval_ref,
        "decision_threshold": threshold,
        "usecase_id": usecase_id,
    }
    outputs = {
        "champion_challenger_csv": str(csv_path),
        "decision_json": str(decision_path),
        "summary_md": str(summary_path),
        "winner": winner,
    }
    hashes = {
        "config_hash": hash_config(cfg),
        "split_hash": champion.get("split_hash") or challenger.get("split_hash") or "unknown",
        "recipe_hash": champion.get("recipe_hash") or challenger.get("recipe_hash") or "unknown",
    }
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "champion_challenger",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
        "outputs": outputs,
        "hashes": hashes,
    }
    write_manifest(ctx, manifest)
