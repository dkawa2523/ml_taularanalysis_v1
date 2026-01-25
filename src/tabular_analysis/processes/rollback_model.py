"""rollback_model process.

- Roll back a registry stage to the previous model
- ClearML enabled: update model registry tags/metadata
- ClearML disabled: update local model_registry_state.json
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from ..ops.clearml_identity import apply_clearml_identity
from ..platform_adapter import (
    add_task_tags,
    hash_config,
    init_task_context,
    is_clearml_enabled,
    resolve_version_props,
    rollback_registry_stage,
    save_config_resolved,
    update_task_properties,
    upload_artifact,
    write_manifest,
    write_out_json,
)
from ..ops.alerting import emit_alert
from ..registry.model_registry_state import (
    load_registry_state,
    rollback_stage_state,
    write_registry_state,
)

_ALLOWED_STAGES = ("staging", "production", "archived")


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


def _normalize_stage(value: Any) -> str:
    stage = _normalize_str(value) or "production"
    key = stage.lower()
    if key == "prod":
        key = "production"
    if key == "archive":
        key = "archived"
    if key not in _ALLOWED_STAGES:
        raise ValueError(f"rollback.stage must be one of {', '.join(_ALLOWED_STAGES)} (got: {stage})")
    return key


def _base_output_dir(cfg: Any) -> Path:
    return Path(getattr(cfg.run, "output_dir", "outputs")).expanduser().resolve()


def _model_ref_id(ref: Mapping[str, Any] | None) -> str | None:
    if not ref:
        return None
    return _normalize_str(ref.get("model_id") or ref.get("registry_model_id"))


def run(cfg: Any) -> None:
    identity = apply_clearml_identity(cfg, stage=cfg.task.stage)
    ctx = init_task_context(
        cfg,
        stage=cfg.task.stage,
        task_name="rollback_model",
        tags=identity.tags,
        properties=identity.user_properties,
    )
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)
    usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id")) or _normalize_str(
        _cfg_value(cfg, "usecase_id")
    ) or "unknown"
    stage = _normalize_stage(
        _cfg_value(cfg, "rollback.stage", _cfg_value(cfg, "rollback_model.stage", "production"))
    )
    reason = _normalize_str(
        _cfg_value(cfg, "rollback.reason", _cfg_value(cfg, "rollback_model.reason"))
    )
    target_model_id = _normalize_str(
        _cfg_value(cfg, "rollback.target_model_id", _cfg_value(cfg, "rollback_model.target_model_id"))
    )

    warnings: list[str] = []
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    registry_state_path: Path | None = None

    if clearml_enabled:
        result = rollback_registry_stage(
            usecase_id=usecase_id,
            stage=stage,
            target_model_id=target_model_id,
            reason=reason,
        )
        before = result.get("before")
        after = result.get("after")
    else:
        registry_state_path = _base_output_dir(cfg) / "model_registry_state.json"
        registry_state = load_registry_state(registry_state_path)
        result = rollback_stage_state(
            registry_state,
            usecase_id=usecase_id,
            stage=stage,
            target_model_id=target_model_id,
        )
        write_registry_state(registry_state_path, registry_state)
        before = result.get("before")
        after = result.get("after")

    if not after:
        raise ValueError("Rollback did not resolve a target model.")
    if not before:
        warnings.append("Previous model reference was missing; rollback used target only.")

    rollback_payload = {
        "stage": stage,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "before": before,
        "after": after,
        "target_model_id": target_model_id,
        "usecase_id": usecase_id,
    }
    if registry_state_path is not None:
        rollback_payload["model_registry_state_path"] = str(registry_state_path)

    rollback_path = ctx.output_dir / "rollback.json"
    rollback_path.write_text(
        json.dumps(rollback_payload, ensure_ascii=True, indent=2), encoding="utf-8"
    )

    emit_alert(
        "rollback",
        "warning",
        "Model rollback executed",
        f"stage={stage}, target_model_id={target_model_id or 'auto'}",
        {
            "_cfg": cfg,
            "_ctx": ctx,
            "stage": stage,
            "target_model_id": target_model_id,
            "before_model_id": _model_ref_id(before),
            "after_model_id": _model_ref_id(after),
            "rollback_json": str(rollback_path),
            "usecase_id": usecase_id,
        },
    )

    if clearml_enabled:
        upload_artifact(ctx, "rollback.json", rollback_path)
        task_tags = [f"stage:{stage}", "rollback:true"]
        if target_model_id:
            task_tags.append("rollback:manual")
        add_task_tags(ctx, task_tags)
        props = {
            "rollback_stage": stage,
            "rollback_reason": reason,
            "rollback_before_model_id": _model_ref_id(before),
            "rollback_after_model_id": _model_ref_id(after),
        }
        props = {key: value for key, value in props.items() if value is not None}
        update_task_properties(ctx, props)

    out = {
        "rollback_json": str(rollback_path),
        "rollback_status": "succeeded",
        "stage": stage,
        "before_model_id": _model_ref_id(before),
        "after_model_id": _model_ref_id(after),
    }
    if registry_state_path is not None:
        out["model_registry_state_path"] = str(registry_state_path)
    if warnings:
        out["warnings"] = warnings
    write_out_json(ctx, out)

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    inputs = {
        "stage": stage,
        "reason": reason,
        "target_model_id": target_model_id,
        "usecase_id": usecase_id,
    }
    outputs = {
        "rollback_json": str(rollback_path),
        "rollback_status": "succeeded",
    }
    split_hash = _normalize_str(
        (after or {}).get("split_hash") or (before or {}).get("split_hash")
    )
    recipe_hash = _normalize_str(
        (after or {}).get("recipe_hash") or (before or {}).get("recipe_hash")
    )
    hashes = {
        "config_hash": hash_config(cfg),
        "split_hash": split_hash or "unknown",
        "recipe_hash": recipe_hash or "unknown",
    }
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "rollback_model",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
        "outputs": outputs,
        "hashes": hashes,
    }
    write_manifest(ctx, manifest)
