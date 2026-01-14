"""retrain process.

- Orchestrate monitoring -> retrain -> compare -> optional promote.
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
from ..registry.model_registry_state import get_current_entry, load_registry_state
from . import champion_challenger as champion_challenger_process
from . import pipeline as pipeline_process
from . import promote_model as promote_model_process

_ALLOWED_STAGES = ("staging", "production", "archived")


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "y", "on"):
        return True
    if text in ("0", "false", "no", "n", "off"):
        return False
    return default


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except Exception:
        return None
    if num != num:
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


def _normalize_stage(value: Any) -> str:
    stage = _normalize_str(value) or "production"
    key = stage.lower()
    if key == "prod":
        key = "production"
    if key == "archive":
        key = "archived"
    if key not in _ALLOWED_STAGES:
        raise ValueError(f"retrain.baseline_stage must be one of {', '.join(_ALLOWED_STAGES)}.")
    return key


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


def _resolve_champion_ref(
    cfg: Any,
    *,
    baseline_stage: str,
    usecase_id: str,
    explicit_ref: str | None,
) -> tuple[str | None, list[str]]:
    if explicit_ref:
        return explicit_ref, []
    warnings: list[str] = []
    registry_path = _base_output_dir(cfg) / "model_registry_state.json"
    if registry_path.exists():
        registry_state = load_registry_state(registry_path)
        entry = get_current_entry(registry_state, usecase_id=usecase_id, stage=baseline_stage)
        if entry:
            ref = _normalize_str(entry.get("train_task_ref") or entry.get("train_task_id"))
            if not ref:
                ref = _normalize_str(entry.get("model_id"))
            if ref:
                return ref, []
    warnings.append(
        "Champion model reference was not found. Provide retrain.champion_model_ref or "
        "promote a baseline model to populate model_registry_state.json."
    )
    return None, warnings


def _evaluate_promote_criteria(
    criteria: Mapping[str, Any],
    comparison: Mapping[str, Any] | None,
) -> tuple[bool, list[str], dict[str, Any]]:
    reasons: list[str] = []
    checks: dict[str, Any] = {}

    if comparison is None:
        return False, ["comparison not available"], checks

    require_comparable = _normalize_bool(criteria.get("require_comparable"), True)
    allow_tie = _normalize_bool(criteria.get("allow_tie"), False)
    min_improvement = _to_float(criteria.get("min_improvement"))
    if min_improvement is None:
        min_improvement = 0.0

    comparability = comparison.get("comparability") if isinstance(comparison, Mapping) else None
    comparability_ok = True
    if isinstance(comparability, Mapping):
        for key in ("processed_dataset_id_match", "split_hash_match"):
            value = comparability.get(key)
            if value is False or value is None:
                comparability_ok = False
    else:
        comparability_ok = False

    winner = _normalize_str(comparison.get("winner")) if isinstance(comparison, Mapping) else None
    directional_delta = _to_float(comparison.get("directional_delta")) if isinstance(comparison, Mapping) else None

    checks.update(
        {
            "require_comparable": require_comparable,
            "comparability_ok": comparability_ok,
            "allow_tie": allow_tie,
            "min_improvement": min_improvement,
            "directional_delta": directional_delta,
            "winner": winner,
        }
    )

    if require_comparable and not comparability_ok:
        reasons.append("comparability check failed")
    if winner is None:
        reasons.append("winner is missing")
    elif winner != "challenger" and not (allow_tie and winner == "tie"):
        reasons.append(f"winner is {winner}")
    if directional_delta is None:
        reasons.append("directional_delta is missing")
    elif directional_delta < min_improvement:
        reasons.append("directional_delta below min_improvement")

    return len(reasons) == 0, reasons, checks


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

    baseline_stage = _normalize_stage(_cfg_value(cfg, "retrain.baseline_stage"))
    champion_ref = _normalize_str(_cfg_value(cfg, "retrain.champion_model_ref"))
    eval_ref = _normalize_str(_cfg_value(cfg, "retrain.eval_dataset_ref"))
    champion_ref, champion_warnings = _resolve_champion_ref(
        cfg,
        baseline_stage=baseline_stage,
        usecase_id=usecase_id,
        explicit_ref=champion_ref,
    )

    decision_threshold = _to_float(_cfg_value(cfg, "retrain.decision_threshold"))
    if decision_threshold is None:
        decision_threshold = 0.0

    comparison: dict[str, Any] | None = None
    comparison_dir: Path | None = None
    comparison_path: Path | None = None
    comparison_summary_path: Path | None = None
    if champion_ref:
        cc_cfg = copy.deepcopy(cfg)
        _set_cfg_value(cc_cfg, "task.name", "champion_challenger")
        _set_cfg_value(cc_cfg, "task.stage", "07_champion_challenger")
        _set_cfg_value(cc_cfg, "task.project_name", _project_name(cfg, "07_champion_challenger"))
        _set_cfg_value(cc_cfg, "champion_challenger.champion_model_ref", champion_ref)
        _set_cfg_value(cc_cfg, "champion_challenger.challenger_model_ref", challenger_ref)
        if eval_ref:
            _set_cfg_value(cc_cfg, "champion_challenger.eval_dataset_ref", eval_ref)
        _set_cfg_value(cc_cfg, "champion_challenger.decision_threshold", decision_threshold)
        _set_cfg_value(cc_cfg, "run.grid_run_id", grid_run_id)
        _set_cfg_value(cc_cfg, "run.retrain_run_id", retrain_run_id)
        champion_challenger_process.run(cc_cfg)
        comparison_dir = resolve_output_dir(cc_cfg, getattr(cc_cfg.task, "stage", "07_champion_challenger"))
        comparison_path = comparison_dir / "decision.json"
        comparison_summary_path = comparison_dir / "summary.md"
        comparison = _load_optional_json(comparison_path) if comparison_path else None

    promote_criteria = _to_mapping(_cfg_value(cfg, "retrain.promote_criteria"))
    auto_promote = _normalize_bool(_cfg_value(cfg, "retrain.auto_promote"), False)
    promote_stage = _normalize_stage(
        _cfg_value(cfg, "retrain.promote_stage", None) or baseline_stage
    )
    promote_set_champion = _normalize_bool(_cfg_value(cfg, "retrain.promote_set_champion"), True)

    promote_status = {
        "status": "skipped",
        "reason": "auto_promote is false",
        "stage": promote_stage,
        "set_champion": promote_set_champion,
    }
    promote_dir: Path | None = None
    promotion_path: Path | None = None
    promote_checks: dict[str, Any] | None = None
    if auto_promote:
        should_promote, promote_reasons, promote_checks = _evaluate_promote_criteria(
            promote_criteria, comparison
        )
        if not should_promote:
            promote_status = {
                "status": "skipped",
                "reason": "; ".join(promote_reasons) if promote_reasons else "criteria not met",
                "stage": promote_stage,
                "set_champion": promote_set_champion,
                "checks": promote_checks,
            }
        else:
            promote_cfg = copy.deepcopy(cfg)
            _set_cfg_value(promote_cfg, "task.name", "promote_model")
            _set_cfg_value(promote_cfg, "task.stage", "06_promote_model")
            _set_cfg_value(promote_cfg, "task.project_name", _project_name(cfg, "06_promote_model"))
            source_ref = _normalize_str(leaderboard_ref.get("task_id")) or _normalize_str(
                leaderboard_ref.get("run_dir")
            )
            if not source_ref:
                raise ValueError("leaderboard_ref missing task_id/run_dir for promote_model.")
            _set_cfg_value(promote_cfg, "promotion.source_leaderboard_dir", source_ref)
            _set_cfg_value(promote_cfg, "promotion.stage", promote_stage)
            _set_cfg_value(promote_cfg, "promotion.set_champion", promote_set_champion)
            _set_cfg_value(
                promote_cfg,
                "promotion.note",
                f"auto_promote retrain_run_id={retrain_run_id}",
            )
            _set_cfg_value(promote_cfg, "run.grid_run_id", grid_run_id)
            _set_cfg_value(promote_cfg, "run.retrain_run_id", retrain_run_id)
            promote_model_process.run(promote_cfg)
            promote_dir = resolve_output_dir(promote_cfg, getattr(promote_cfg.task, "stage", "06_promote_model"))
            promotion_path = promote_dir / "promotion.json"
            promote_status = {
                "status": "success",
                "stage": promote_stage,
                "set_champion": promote_set_champion,
                "promotion_json": str(promotion_path) if promotion_path else None,
                "checks": promote_checks,
            }

    warnings = list(champion_warnings)
    decision_payload: dict[str, Any] = {
        "retrain_run_id": retrain_run_id,
        "grid_run_id": grid_run_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_path": dataset_path,
        "dataset_id": dataset_id,
        "baseline_stage": baseline_stage,
        "champion_model_ref": champion_ref,
        "challenger_model_ref": challenger_ref,
        "leaderboard_out": {
            "recommended_model_id": leaderboard_out.get("recommended_model_id"),
            "recommended_train_task_ref": leaderboard_out.get("recommended_train_task_ref"),
            "recommended_train_task_id": leaderboard_out.get("recommended_train_task_id"),
            "recommended_best_score": leaderboard_out.get("recommended_best_score"),
            "recommended_primary_metric": leaderboard_out.get("recommended_primary_metric"),
        },
        "comparison": comparison,
        "auto_promote": auto_promote,
        "promote_status": promote_status,
        "promote_criteria": promote_criteria,
    }
    if warnings:
        decision_payload["warnings"] = warnings

    action = "review"
    if promote_status.get("status") == "success":
        action = "promote"
    decision_payload["decision"] = {"action": action, "reason": promote_status.get("reason")}

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
        "champion_challenger_run_dir": str(comparison_dir) if comparison_dir else None,
        "champion_challenger_decision": str(comparison_path) if comparison_path else None,
        "champion_challenger_summary": str(comparison_summary_path) if comparison_summary_path else None,
        "promote_run_dir": str(promote_dir) if promote_dir else None,
        "promote_json": str(promotion_path) if promotion_path else None,
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
        f"- baseline_stage: {baseline_stage}",
        f"- champion_model_ref: {champion_ref or 'n/a'}",
        f"- challenger_model_ref: {challenger_ref}",
    ]
    if comparison:
        summary_lines.extend(
            [
                "",
                "## Champion vs Challenger",
                f"- winner: {comparison.get('winner')}",
                f"- primary_metric: {comparison.get('primary_metric')}",
                f"- champion_score: {comparison.get('champion_score')}",
                f"- challenger_score: {comparison.get('challenger_score')}",
                f"- directional_delta: {comparison.get('directional_delta')}",
            ]
        )
    else:
        summary_lines.extend(["", "## Champion vs Challenger", "- comparison: skipped"])
    summary_lines.extend(
        [
            "",
            "## Auto Promote",
            f"- auto_promote: {auto_promote}",
            f"- status: {promote_status.get('status')}",
            f"- reason: {promote_status.get('reason') or 'n/a'}",
        ]
    )
    if warnings:
        summary_lines.extend(["", "## Warnings"])
        summary_lines.extend([f"- {line}" for line in warnings])

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
                "auto_promote": auto_promote,
                "promote_status": promote_status.get("status"),
                "winner": comparison.get("winner") if comparison else None,
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
        "auto_promote": auto_promote,
        "promote_status": promote_status.get("status"),
    }
    if comparison_dir:
        out["champion_challenger_dir"] = str(comparison_dir)
    if promote_dir:
        out["promote_dir"] = str(promote_dir)
    if warnings:
        out["warnings"] = warnings
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
            "baseline_stage": baseline_stage,
            "champion_model_ref": champion_ref,
            "challenger_model_ref": challenger_ref,
            "auto_promote": auto_promote,
            "promote_stage": promote_stage,
            "promote_set_champion": promote_set_champion,
            "decision_threshold": decision_threshold,
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
