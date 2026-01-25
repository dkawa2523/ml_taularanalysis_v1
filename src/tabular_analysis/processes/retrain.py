"""retrain process.

- Orchestrate retrain and emit leaderboard-based decision artifacts.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import uuid

from ..ops.clearml_identity import apply_clearml_identity, build_project_name
from ..platform_adapter import (
    get_task_artifact_local_copy,
    hash_config,
    hash_recipe,
    hash_split,
    init_task_context,
    is_clearml_enabled,
    report_markdown,
    resolve_output_dir,
    resolve_version_props,
    save_config_resolved,
    update_task_properties,
    upload_artifact,
    write_manifest,
    write_out_json,
)
from . import pipeline as pipeline_process


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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


def _set_cfg_value(cfg: Any, dotted_path: str, value: Any) -> bool:
    if cfg is None:
        return False
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(cfg):
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
            OmegaConf.update(cfg, dotted_path, value, merge=False)
            return True
        except Exception:
            return False
        finally:
            if was_struct:
                try:
                    OmegaConf.set_struct(cfg, True)
                except Exception:
                    pass
    current = cfg
    keys = dotted_path.split(".")
    for key in keys[:-1]:
        if isinstance(current, Mapping):
            if key not in current or not isinstance(current[key], Mapping):
                current[key] = {}
            current = current[key]
            continue
        if not hasattr(current, key) or getattr(current, key) is None:
            setattr(current, key, type("CfgNode", (), {})())
        current = getattr(current, key)
    last = keys[-1]
    if isinstance(current, Mapping):
        current[last] = value
        return True
    try:
        setattr(current, last, value)
        return True
    except Exception:
        return False


def _to_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(value):
        try:
            container = OmegaConf.to_container(value, resolve=True)
        except Exception:
            container = None
        if isinstance(container, Mapping):
            return dict(container)
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _ensure_run_id(cfg: Any, path: str) -> str:
    existing = _normalize_str(_cfg_value(cfg, path))
    if existing:
        return existing
    new_id = uuid.uuid4().hex
    _set_cfg_value(cfg, path, new_id)
    return new_id


def _project_name(cfg: Any, stage: str) -> str:
    project_root = _normalize_str(_cfg_value(cfg, "run.clearml.project_root")) or "MFG"
    usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id")) or "unknown"
    return build_project_name(project_root, usecase_id, stage, cfg=cfg)


def _base_output_dir(cfg: Any) -> Path:
    return Path(getattr(cfg.run, "output_dir", "outputs")).expanduser().resolve()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return _load_json(path)
    except Exception:
        return None


def _resolve_ref_out(
    cfg: Any,
    ref: Mapping[str, Any],
    *,
    clearml_enabled: bool,
    label: str,
) -> tuple[dict[str, Any], Path]:
    run_dir = _normalize_str(ref.get("run_dir"))
    task_id = _normalize_str(ref.get("task_id"))
    out_path = None
    if run_dir:
        candidate = Path(run_dir).expanduser() / "out.json"
        if candidate.exists():
            out_path = candidate
    if out_path is None and clearml_enabled and task_id:
        out_path = get_task_artifact_local_copy(cfg, task_id, "out.json")
    if out_path is None or not out_path.exists():
        raise FileNotFoundError(f"{label} out.json not found for ref: {ref}")
    payload = _load_json(out_path)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} out.json must contain an object.")
    return payload, out_path


def _resolve_challenger_ref(
    leaderboard_out: Mapping[str, Any],
    *,
    clearml_enabled: bool,
) -> str | None:
    ordered_keys = [
        "recommended_train_task_id",
        "recommended_train_task_ref",
        "recommended_model_id",
    ]
    if not clearml_enabled:
        ordered_keys = [
            "recommended_train_task_ref",
            "recommended_train_task_id",
            "recommended_model_id",
        ]
    for key in ordered_keys:
        value = _normalize_str(leaderboard_out.get(key))
        if value:
            return value
    return None




def run(cfg: Any) -> None:
    retrain_run_id = _ensure_run_id(cfg, "run.retrain_run_id")
    grid_run_id = _ensure_run_id(cfg, "run.grid_run_id")
    identity = apply_clearml_identity(cfg, stage=cfg.task.stage)
    ctx = init_task_context(
        cfg,
        stage=cfg.task.stage,
        task_name="retrain",
        tags=[*identity.tags, f"retrain:{retrain_run_id}"],
        properties={**identity.user_properties, "retrain_run_id": retrain_run_id},
    )
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)
    usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id")) or "unknown"
    dataset_path = _normalize_str(_cfg_value(cfg, "retrain.dataset_path")) or _normalize_str(
        _cfg_value(cfg, "data.dataset_path")
    )
    dataset_id = _normalize_str(_cfg_value(cfg, "retrain.dataset_id")) or _normalize_str(
        _cfg_value(cfg, "data.raw_dataset_id")
    )

    pipeline_cfg = copy.deepcopy(cfg)
    _set_cfg_value(pipeline_cfg, "task.name", "pipeline")
    _set_cfg_value(pipeline_cfg, "task.stage", "99_pipeline")
    _set_cfg_value(pipeline_cfg, "task.project_name", _project_name(cfg, "99_pipeline"))
    _set_cfg_value(pipeline_cfg, "run.grid_run_id", grid_run_id)
    _set_cfg_value(pipeline_cfg, "run.retrain_run_id", retrain_run_id)
    if dataset_path:
        _set_cfg_value(pipeline_cfg, "data.dataset_path", dataset_path)
    if dataset_id:
        _set_cfg_value(pipeline_cfg, "data.raw_dataset_id", dataset_id)

    pipeline_process.run(pipeline_cfg)

    pipeline_output_dir = resolve_output_dir(pipeline_cfg, getattr(pipeline_cfg.task, "stage", "99_pipeline"))
    pipeline_run_path = pipeline_output_dir / "pipeline_run.json"
    if not pipeline_run_path.exists():
        raise FileNotFoundError(f"pipeline_run.json not found: {pipeline_run_path}")
    pipeline_run = _load_json(pipeline_run_path)

    leaderboard_ref = _to_mapping(pipeline_run.get("leaderboard_ref"))
    if not leaderboard_ref:
        raise ValueError("pipeline_run is missing leaderboard_ref.")
    leaderboard_out, leaderboard_out_path = _resolve_ref_out(
        cfg, leaderboard_ref, clearml_enabled=clearml_enabled, label="leaderboard"
    )
    challenger_ref = _resolve_challenger_ref(leaderboard_out, clearml_enabled=clearml_enabled)
    if not challenger_ref:
        raise ValueError("leaderboard did not provide a challenger reference.")

    decision_payload: dict[str, Any] = {
        "retrain_run_id": retrain_run_id,
        "grid_run_id": grid_run_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_path": dataset_path,
        "dataset_id": dataset_id,
        "challenger_model_ref": challenger_ref,
        "leaderboard_out": {
            "recommended_model_id": leaderboard_out.get("recommended_model_id"),
            "recommended_train_task_ref": leaderboard_out.get("recommended_train_task_ref"),
            "recommended_train_task_id": leaderboard_out.get("recommended_train_task_id"),
            "recommended_best_score": leaderboard_out.get("recommended_best_score"),
            "recommended_primary_metric": leaderboard_out.get("recommended_primary_metric"),
            "recommendation_count": leaderboard_out.get("recommendation_count"),
            "recommended_models": leaderboard_out.get("recommended_models"),
        },
    }
    decision_payload["decision"] = {"action": "select_model", "reason": "user_select_at_infer"}

    decision_path = ctx.output_dir / "retrain_decision.json"
    decision_path.write_text(
        json.dumps(decision_payload, ensure_ascii=True, indent=2), encoding="utf-8"
    )

    retrain_run_payload = {
        "retrain_run_id": retrain_run_id,
        "grid_run_id": grid_run_id,
        "pipeline_run_path": str(pipeline_run_path),
        "leaderboard_ref": leaderboard_ref,
        "leaderboard_out_path": str(leaderboard_out_path),
    }
    retrain_run_path = ctx.output_dir / "retrain_run.json"
    retrain_run_path.write_text(
        json.dumps(retrain_run_payload, ensure_ascii=True, indent=2), encoding="utf-8"
    )

    summary_lines = [
        "# Retrain Summary",
        "",
        f"- retrain_run_id: {retrain_run_id}",
        f"- grid_run_id: {grid_run_id}",
        f"- dataset_path: {dataset_path or 'n/a'}",
        f"- dataset_id: {dataset_id or 'n/a'}",
        f"- challenger_model_ref: {challenger_ref}",
    ]
    summary_lines.extend(["", "## Decision", "- action: select_model (choose at infer time)"])

    summary_path = ctx.output_dir / "retrain_summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    if clearml_enabled:
        for name, path in [
            ("retrain_decision.json", decision_path),
            ("retrain_run.json", retrain_run_path),
            ("retrain_summary.md", summary_path),
        ]:
            upload_artifact(ctx, name, path)
        report_markdown(ctx, title="", markdown="\n".join(summary_lines))
        update_task_properties(
            ctx,
            {
                "retrain_run_id": retrain_run_id,
                "grid_run_id": grid_run_id,
                "decision": "select_model",
            },
        )

    out = {
        "retrain_run_id": retrain_run_id,
        "grid_run_id": grid_run_id,
        "pipeline_run_path": str(pipeline_run_path),
        "leaderboard_ref": leaderboard_ref,
        "decision_json": str(decision_path),
        "summary_md": str(summary_path),
        "retrain_run_json": str(retrain_run_path),
    }
    write_out_json(ctx, out)

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "retrain",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "dataset_path": dataset_path,
            "dataset_id": dataset_id,
            "challenger_model_ref": challenger_ref,
        },
        "outputs": {
            "retrain_decision_json": str(decision_path),
            "retrain_run_json": str(retrain_run_path),
            "retrain_summary_md": str(summary_path),
        },
        "hashes": {
            "config_hash": hash_config(cfg),
            "split_hash": hash_split({}),
            "recipe_hash": hash_recipe({}),
        },
    }
    write_manifest(ctx, manifest)
