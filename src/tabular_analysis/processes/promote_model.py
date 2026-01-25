"""promote_model process.

- Promote recommended model to a stage (staging/production/archived)
- Track champion history for rollback
- Optionally register the model in ClearML model registry
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from ..io.bundle_io import load_bundle
from ..ops.clearml_identity import apply_clearml_identity
from ..platform_adapter import (
    PlatformAdapterError,
    add_task_tags,
    get_task_artifact_local_copy,
    hash_config,
    init_task_context,
    is_clearml_enabled,
    register_promoted_model,
    resolve_version_props,
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
    update_stage_state,
    write_registry_state,
)

_ALLOWED_STAGES = ("staging", "production", "archived")
_CHAMPION_REGISTRY_SCHEMA_VERSION = 1


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
    if num != num:  # NaN check
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
        else:
            if not hasattr(current, key):
                return default
            current = getattr(current, key)
    return default if current is None else current


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


def _select_cfg_value(cfg: Any, primary_path: str, fallback_path: str, default: Any | None = None) -> Any:
    value = _cfg_value(cfg, primary_path, None)
    if value is not None:
        return value
    return _cfg_value(cfg, fallback_path, default)


def _normalize_stage(value: Any) -> str:
    stage = _normalize_str(value)
    if stage is None:
        raise ValueError("promote.stage or promotion.stage is required.")
    key = stage.lower()
    if key == "prod":
        key = "production"
    if key == "archive":
        key = "archived"
    if key not in _ALLOWED_STAGES:
        raise ValueError(
            f"promote.stage must be one of {', '.join(_ALLOWED_STAGES)} (got: {stage})"
        )
    return key


def _resolve_repo_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for base in candidates:
        for parent in [base, *base.parents]:
            if (parent / "work").exists() and (parent / "pyproject.toml").exists():
                return parent
    return Path.cwd()


def _champion_registry_path() -> Path:
    return _resolve_repo_root() / "work" / "registry" / "champions.json"


def _model_registry_state_path(cfg: Any) -> Path:
    base_output_dir = Path(getattr(cfg.run, "output_dir", "outputs")).expanduser().resolve()
    return base_output_dir / "model_registry_state.json"


def _load_champion_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": _CHAMPION_REGISTRY_SCHEMA_VERSION,
            "updated_at": None,
            "usecases": {},
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"champions.json is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("champions.json must contain a JSON object.")
    payload.setdefault("schema_version", _CHAMPION_REGISTRY_SCHEMA_VERSION)
    usecases = payload.get("usecases")
    if not isinstance(usecases, dict):
        payload["usecases"] = {}
    return payload


def _ensure_usecase_registry(registry: dict[str, Any], usecase_id: str) -> dict[str, Any]:
    usecases = registry.get("usecases")
    if not isinstance(usecases, dict):
        usecases = {}
        registry["usecases"] = usecases
    entry = usecases.get(usecase_id)
    if not isinstance(entry, dict):
        entry = {}
        usecases[usecase_id] = entry
    history = entry.get("history")
    if not isinstance(history, list):
        history = []
    history = [item for item in history if isinstance(item, Mapping)]
    entry["history"] = history
    current = entry.get("current")
    if current is not None and not isinstance(current, Mapping):
        entry["current"] = None
    entry.setdefault("current", None)
    return entry


def _write_champion_registry(path: Path, registry: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(registry, ensure_ascii=True, indent=2)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    tmp_path.replace(path)


def _build_champion_entry(
    *,
    model_id: str,
    stage: str,
    source: str,
    metric: str | None,
    score: float | None,
    task_type: str | None,
    split_hash: str | None,
    recipe_hash: str | None,
    processed_dataset_id: str | None,
    train_task_ref: str | None,
    train_task_id: str | None,
    model_variant: str | None,
    preprocess_variant: str | None,
    note: str | None,
    registry_model_id: str | None,
    registry_status: str | None,
) -> dict[str, Any]:
    entry = {
        "model_id": model_id,
        "stage": stage,
        "source": source,
        "metric": metric,
        "score": score,
        "task_type": task_type,
        "split_hash": split_hash,
        "recipe_hash": recipe_hash,
        "processed_dataset_id": processed_dataset_id,
        "train_task_ref": train_task_ref,
        "train_task_id": train_task_id,
        "model_variant": model_variant,
        "preprocess_variant": preprocess_variant,
        "note": note,
        "registry_model_id": registry_model_id,
        "registry_status": registry_status,
        "promoted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return {key: value for key, value in entry.items() if value is not None}


def _compact_champion_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    keep = (
        "model_id",
        "stage",
        "metric",
        "score",
        "train_task_id",
        "train_task_ref",
        "promoted_at",
    )
    compact: dict[str, Any] = {}
    for key in keep:
        value = entry.get(key)
        if value is not None:
            compact[key] = value
    return compact


def _update_champion_registry(
    registry_path: Path,
    registry: dict[str, Any],
    *,
    usecase_id: str,
    new_entry: dict[str, Any],
    rollback: bool,
) -> dict[str, Any]:
    entry = _ensure_usecase_registry(registry, usecase_id)
    history = entry.get("history")
    if not isinstance(history, list):
        history = []
        entry["history"] = history
    current = entry.get("current") if isinstance(entry.get("current"), Mapping) else None
    result: dict[str, Any] = {"current": new_entry, "previous": current}
    if rollback:
        if current is None or not history:
            raise ValueError("rollback requested but champion history is missing.")
        target = history.pop(0)
        result["target"] = target
        if current is not None:
            history.insert(0, current)
        entry["current"] = new_entry
    else:
        if current is not None:
            history.insert(0, current)
        entry["current"] = new_entry
    registry["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_champion_registry(registry_path, registry)
    return result


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_run_dir(ref: Path) -> Path:
    if ref.is_file():
        return ref.parent
    return ref


def _resolve_leaderboard_info(
    cfg: Any,
    ref: str,
    *,
    clearml_enabled: bool,
) -> dict[str, Any]:
    ref_path = Path(ref).expanduser()
    source_kind = "leaderboard_dir"
    if ref_path.exists():
        run_dir = _resolve_run_dir(ref_path)
        rec_path = run_dir / "recommendation.json"
        out_path = run_dir / "out.json"
    else:
        if not clearml_enabled:
            raise FileNotFoundError(f"leaderboard output not found: {ref_path}")
        rec_path = get_task_artifact_local_copy(cfg, ref, "recommendation.json")
        out_path = get_task_artifact_local_copy(cfg, ref, "out.json")
        source_kind = "leaderboard_task"

    if not rec_path.exists():
        raise FileNotFoundError(f"recommendation.json not found: {rec_path}")

    rec = _load_json(rec_path)
    info: dict[str, Any] = {
        "source_kind": source_kind,
        "source_ref": ref,
        "recommended_model_id": _normalize_str(rec.get("recommended_model_id")),
        "recommended_primary_metric": _normalize_str(rec.get("recommended_primary_metric")),
        "recommended_best_score": _to_float(rec.get("recommended_best_score")),
        "recommended_train_task_ref": _normalize_str(rec.get("recommended_train_task_ref")),
        "recommended_train_task_id": None,
    }

    if out_path.exists():
        out = _load_json(out_path)
        info["recommended_train_task_id"] = _normalize_str(out.get("recommended_train_task_id"))
        if info.get("recommended_train_task_ref") is None:
            info["recommended_train_task_ref"] = _normalize_str(out.get("recommended_train_task_ref"))
        if info.get("recommended_model_id") is None:
            info["recommended_model_id"] = _normalize_str(out.get("recommended_model_id"))
    return info


def _resolve_model_bundle_path(
    cfg: Any,
    *,
    recommended_model_id: str | None,
    train_task_ref: str | None,
    train_task_id: str | None,
    clearml_enabled: bool,
) -> Path | None:
    if recommended_model_id:
        candidate = Path(recommended_model_id).expanduser()
        if candidate.exists():
            return candidate.resolve()
    if clearml_enabled and train_task_id:
        try:
            return get_task_artifact_local_copy(cfg, train_task_id, "model_bundle.joblib")
        except PlatformAdapterError:
            return None
    if train_task_ref:
        ref_path = Path(train_task_ref).expanduser()
        if ref_path.exists():
            run_dir = _resolve_run_dir(ref_path)
            candidate = run_dir / "model_bundle.joblib"
            if candidate.exists():
                return candidate.resolve()
            if ref_path.is_file():
                return ref_path.resolve()
        if clearml_enabled:
            try:
                return get_task_artifact_local_copy(cfg, train_task_ref, "model_bundle.joblib")
            except PlatformAdapterError:
                return None
    return None


def _load_train_out(
    cfg: Any,
    *,
    train_task_ref: str | None,
    train_task_id: str | None,
    clearml_enabled: bool,
) -> dict[str, Any] | None:
    if clearml_enabled:
        task_ref = train_task_id or train_task_ref
        if task_ref:
            try:
                out_path = get_task_artifact_local_copy(cfg, task_ref, "out.json")
                return _load_json(out_path)
            except PlatformAdapterError:
                return None
    if train_task_ref:
        ref_path = Path(train_task_ref).expanduser()
        if ref_path.exists():
            run_dir = _resolve_run_dir(ref_path)
            out_path = run_dir / "out.json"
            if out_path.exists():
                return _load_json(out_path)
    return None


def _extract_bundle_meta(bundle: Mapping[str, Any]) -> dict[str, Any]:
    preprocess_bundle = bundle.get("preprocess_bundle") or {}
    preprocess_variant = None
    if isinstance(preprocess_bundle, Mapping):
        preprocess_variant = _normalize_str(preprocess_bundle.get("preprocess_variant"))
    return {
        "model_variant": _normalize_str(bundle.get("model_variant")),
        "preprocess_variant": preprocess_variant,
        "primary_metric": _normalize_str(bundle.get("primary_metric")),
        "best_score": _to_float(bundle.get("best_score")),
        "task_type": _normalize_str(bundle.get("task_type")),
        "split_hash": _normalize_str(bundle.get("split_hash")),
        "recipe_hash": _normalize_str(bundle.get("recipe_hash")),
        "processed_dataset_id": _normalize_str(bundle.get("processed_dataset_id")),
        "n_classes": bundle.get("n_classes"),
    }


def _merge_meta(base: dict[str, Any], extra: Mapping[str, Any] | None) -> dict[str, Any]:
    if not extra:
        return base
    merged = dict(base)
    for key, value in extra.items():
        if merged.get(key) is None and value is not None:
            merged[key] = value
    return merged


def _write_failure(
    ctx: Any,
    cfg: Any,
    *,
    stage: str,
    model_id: str | None,
    source: str,
    error: Exception,
    promotion_path: Path | None,
) -> None:
    error_payload = {"type": error.__class__.__name__, "message": str(error)}
    out: dict[str, Any] = {
        "model_id": model_id,
        "stage": stage,
        "source": source,
        "promotion_status": "failed",
        "error": error_payload,
    }
    if promotion_path is not None:
        out["promotion_json"] = str(promotion_path)
    write_out_json(ctx, out)

    clearml_enabled = is_clearml_enabled(cfg)
    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    inputs = {"model_id": model_id, "stage": stage, "source": source}
    outputs = {"promotion_status": "failed"}
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "promote_model",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
        "outputs": outputs,
        "hashes": {"config_hash": hash_config(cfg)},
        "error": error_payload,
    }
    write_manifest(ctx, manifest)


def run(cfg: Any) -> None:
    identity = apply_clearml_identity(cfg, stage=cfg.task.stage)
    ctx = init_task_context(
        cfg,
        stage=cfg.task.stage,
        task_name="promote_model",
        tags=identity.tags,
        properties=identity.user_properties,
    )
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)
    usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id")) or _normalize_str(
        _cfg_value(cfg, "usecase_id")
    ) or "unknown"

    source_leaderboard = _normalize_str(
        _select_cfg_value(
            cfg, "promote.source_leaderboard_dir", "promotion.source_leaderboard_dir"
        )
    )
    recommended_model_id = _normalize_str(
        _select_cfg_value(cfg, "promote.recommended_model_id", "promotion.recommended_model_id")
    )
    note = _normalize_str(_select_cfg_value(cfg, "promote.note", "promotion.note"))
    stage = _normalize_stage(
        _select_cfg_value(cfg, "promote.stage", "promotion.stage", "production")
    )
    set_champion = _normalize_bool(
        _select_cfg_value(cfg, "promote.set_champion", "promotion.set_champion"),
        default=True,
    )
    rollback = _normalize_bool(
        _select_cfg_value(cfg, "promote.rollback", "promotion.rollback"),
        default=False,
    )

    if rollback and not set_champion:
        raise ValueError("promote.rollback requires promote.set_champion=true.")

    warnings: list[str] = []
    leaderboard_info: dict[str, Any] | None = None
    rollback_info: dict[str, Any] | None = None
    rollback_meta: dict[str, Any] = {}
    registry_path: Path | None = None
    registry_state: dict[str, Any] | None = None
    train_task_ref = None
    train_task_id = None

    if rollback:
        if source_leaderboard or recommended_model_id:
            warnings.append(
                "rollback ignores promotion.source_leaderboard_dir/recommended_model_id; "
                "using champion registry."
            )
        registry_path = _champion_registry_path()
        registry_state = _load_champion_registry(registry_path)
        usecase_entry = _ensure_usecase_registry(registry_state, usecase_id)
        current_entry = usecase_entry.get("current")
        history = usecase_entry.get("history") or []
        if current_entry is None or not history:
            raise ValueError("champion registry does not contain a previous champion for rollback.")
        target_entry = history[0]
        rollback_info = {"from": current_entry, "to": target_entry}
        recommended_model_id = _normalize_str(target_entry.get("model_id"))
        if not recommended_model_id:
            raise ValueError("champion registry entry missing model_id for rollback.")
        train_task_ref = _normalize_str(target_entry.get("train_task_ref"))
        train_task_id = _normalize_str(target_entry.get("train_task_id"))
        rollback_meta = {
            "metric": _normalize_str(target_entry.get("metric")),
            "score": _to_float(target_entry.get("score")),
        }
    else:
        if not source_leaderboard and not recommended_model_id:
            raise ValueError(
                "promote.source_leaderboard_dir or promote.recommended_model_id is required."
            )

    if source_leaderboard and not rollback:
        leaderboard_info = _resolve_leaderboard_info(
            cfg, source_leaderboard, clearml_enabled=clearml_enabled
        )
        lb_model_id = _normalize_str(leaderboard_info.get("recommended_model_id"))
        if recommended_model_id and lb_model_id and recommended_model_id != lb_model_id:
            warnings.append(
                "recommended_model_id differs from leaderboard recommendation; using override."
            )
        if recommended_model_id is None:
            recommended_model_id = lb_model_id

    if not recommended_model_id:
        raise ValueError("recommended_model_id could not be resolved.")

    if leaderboard_info and not rollback:
        train_task_ref = _normalize_str(leaderboard_info.get("recommended_train_task_ref"))
        train_task_id = _normalize_str(leaderboard_info.get("recommended_train_task_id"))

    model_bundle_path = _resolve_model_bundle_path(
        cfg,
        recommended_model_id=recommended_model_id,
        train_task_ref=train_task_ref,
        train_task_id=train_task_id,
        clearml_enabled=clearml_enabled,
    )
    if model_bundle_path is None:
        raise FileNotFoundError("model_bundle.joblib could not be located for promotion.")

    bundle_meta: dict[str, Any] = {}
    try:
        bundle = load_bundle(model_bundle_path)
        if isinstance(bundle, Mapping):
            bundle_meta = _extract_bundle_meta(bundle)
    except Exception as exc:
        warnings.append(f"Failed to load model bundle metadata: {exc}")

    train_out = _load_train_out(
        cfg,
        train_task_ref=train_task_ref,
        train_task_id=train_task_id,
        clearml_enabled=clearml_enabled,
    )
    train_meta: dict[str, Any] = {}
    if isinstance(train_out, Mapping):
        train_meta = {
            "primary_metric": _normalize_str(train_out.get("primary_metric")),
            "best_score": _to_float(train_out.get("best_score")),
            "task_type": _normalize_str(train_out.get("task_type")),
            "split_hash": _normalize_str(train_out.get("split_hash")),
            "recipe_hash": _normalize_str(train_out.get("recipe_hash")),
            "processed_dataset_id": _normalize_str(train_out.get("processed_dataset_id")),
            "model_id": _normalize_str(train_out.get("model_id")),
            "n_classes": train_out.get("n_classes"),
        }

    meta = _merge_meta(bundle_meta, train_meta)
    primary_metric = meta.get("primary_metric") or (
        leaderboard_info.get("recommended_primary_metric") if leaderboard_info else None
    )
    if primary_metric is None and rollback_meta.get("metric") is not None:
        primary_metric = rollback_meta.get("metric")
    best_score = meta.get("best_score")
    if best_score is None and leaderboard_info:
        best_score = leaderboard_info.get("recommended_best_score")
    if best_score is None and rollback_meta.get("score") is not None:
        best_score = rollback_meta.get("score")

    if rollback:
        source = f"rollback:champion_registry:{usecase_id}"
    elif leaderboard_info:
        source = f"{leaderboard_info.get('source_kind')}:{leaderboard_info.get('source_ref')}"
    else:
        source = "direct"

    promotion_payload: dict[str, Any] = {
        "model_id": recommended_model_id,
        "stage": stage,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "metric": primary_metric,
        "score": best_score,
        "task_type": meta.get("task_type"),
        "split_hash": meta.get("split_hash"),
        "recipe_hash": meta.get("recipe_hash"),
        "processed_dataset_id": meta.get("processed_dataset_id"),
        "train_task_ref": train_task_ref,
        "train_task_id": train_task_id,
        "model_variant": meta.get("model_variant"),
        "preprocess_variant": meta.get("preprocess_variant"),
        "note": note,
        "set_champion": set_champion,
        "rollback": rollback,
    }
    if meta.get("n_classes") is not None:
        promotion_payload["n_classes"] = meta.get("n_classes")
    if set_champion or rollback:
        registry_path = registry_path or _champion_registry_path()
        promotion_payload["champion_registry_path"] = str(registry_path)
        promotion_payload["champion_usecase_id"] = usecase_id
    if rollback_info and isinstance(rollback_info.get("from"), Mapping):
        promotion_payload["rollback_from"] = _compact_champion_entry(rollback_info["from"])

    registry_model_id: str | None = None
    registry_status: str | None = None
    registry_error: dict[str, Any] | None = None
    if clearml_enabled:
        model_name_parts = [usecase_id or "usecase", stage]
        model_name_source = train_task_id or train_task_ref or recommended_model_id
        if model_name_source:
            model_name_parts.append(Path(str(model_name_source)).stem)
        model_name = "__".join([part for part in model_name_parts if part])
        model_tags = [
            f"stage:{stage}",
            f"usecase:{usecase_id or 'unknown'}",
            "process:promote_model",
        ]
        if set_champion:
            model_tags.append("champion:current")
        if rollback:
            model_tags.append("rollback:true")
        model_props = {
            "usecase_id": usecase_id or "unknown",
            "task_type": meta.get("task_type"),
            "metric": primary_metric,
            "score": best_score,
            "split_hash": meta.get("split_hash"),
            "recipe_hash": meta.get("recipe_hash"),
            "processed_dataset_id": meta.get("processed_dataset_id"),
            "model_id": recommended_model_id,
            "train_task_id": train_task_id,
            "promotion_stage": stage,
            "set_champion": set_champion,
            "rollback": rollback,
        }
        if note:
            model_props["note"] = note
        try:
            registry_model_id = register_promoted_model(
                ctx,
                model_path=model_bundle_path,
                model_name=model_name,
                tags=model_tags,
                metadata=model_props,
                comment=note,
            )
            registry_status = "registered"
        except Exception as exc:
            registry_status = "failed"
            registry_error = {"type": exc.__class__.__name__, "message": str(exc)}
            warnings.append(f"ClearML registry registration failed: {exc}")

    if registry_model_id:
        promotion_payload["registry_model_id"] = registry_model_id
    if registry_status:
        promotion_payload["registry_status"] = registry_status
    if registry_error:
        promotion_payload["registry_error"] = registry_error

    champion_update: dict[str, Any] | None = None
    if set_champion or rollback:
        registry_path = registry_path or _champion_registry_path()
        registry_state = registry_state or _load_champion_registry(registry_path)
        champion_entry = _build_champion_entry(
            model_id=recommended_model_id,
            stage=stage,
            source=source,
            metric=primary_metric,
            score=best_score,
            task_type=meta.get("task_type"),
            split_hash=meta.get("split_hash"),
            recipe_hash=meta.get("recipe_hash"),
            processed_dataset_id=meta.get("processed_dataset_id"),
            train_task_ref=train_task_ref,
            train_task_id=train_task_id,
            model_variant=meta.get("model_variant"),
            preprocess_variant=meta.get("preprocess_variant"),
            note=note,
            registry_model_id=registry_model_id,
            registry_status=registry_status,
        )
        champion_update = _update_champion_registry(
            registry_path,
            registry_state,
            usecase_id=usecase_id,
            new_entry=champion_entry,
            rollback=rollback,
        )
        champion_payload = {
            "registry_path": str(registry_path),
            "usecase_id": usecase_id,
            "set_champion": set_champion,
            "rollback": rollback,
        }
        previous = champion_update.get("previous")
        if isinstance(previous, Mapping):
            previous_model_id = _normalize_str(previous.get("model_id"))
            if previous_model_id:
                champion_payload["previous_model_id"] = previous_model_id
        if rollback:
            target = champion_update.get("target")
            if isinstance(target, Mapping):
                target_model_id = _normalize_str(target.get("model_id"))
                if target_model_id:
                    champion_payload["rollback_target_model_id"] = target_model_id
        promotion_payload["champion"] = champion_payload

    local_registry_state_path: Path | None = None
    if not clearml_enabled:
        local_registry_state_path = _model_registry_state_path(cfg)
        local_state = load_registry_state(local_registry_state_path)
        local_entry = {
            "model_id": recommended_model_id,
            "stage": stage,
            "source": source,
            "metric": primary_metric,
            "score": best_score,
            "task_type": meta.get("task_type"),
            "split_hash": meta.get("split_hash"),
            "recipe_hash": meta.get("recipe_hash"),
            "processed_dataset_id": meta.get("processed_dataset_id"),
            "train_task_ref": train_task_ref,
            "train_task_id": train_task_id,
            "model_variant": meta.get("model_variant"),
            "preprocess_variant": meta.get("preprocess_variant"),
            "note": note,
            "registry_model_id": registry_model_id,
            "registry_status": registry_status,
            "promoted_at": promotion_payload.get("timestamp"),
        }
        if rollback:
            rollback_stage_state(
                local_state,
                usecase_id=usecase_id,
                stage=stage,
                target_model_id=recommended_model_id,
            )
        else:
            update_stage_state(
                local_state,
                usecase_id=usecase_id,
                stage=stage,
                entry=local_entry,
            )
        write_registry_state(local_registry_state_path, local_state)
        promotion_payload["model_registry_state_path"] = str(local_registry_state_path)

    promotion_path = ctx.output_dir / "promotion.json"
    promotion_path.write_text(
        json.dumps(promotion_payload, ensure_ascii=True, indent=2), encoding="utf-8"
    )

    alert_kind = "rollback" if rollback else "promotion"
    alert_severity = "warning" if rollback else "info"
    alert_title = "Model rollback executed" if rollback else "Model promotion executed"
    emit_alert(
        alert_kind,
        alert_severity,
        alert_title,
        f"stage={stage}, model_id={recommended_model_id}, source={source}",
        {
            "_cfg": cfg,
            "_ctx": ctx,
            "stage": stage,
            "model_id": recommended_model_id,
            "source": source,
            "set_champion": set_champion,
            "rollback": rollback,
            "registry_status": registry_status,
            "registry_model_id": registry_model_id,
            "promotion_json": str(promotion_path),
        },
    )

    if clearml_enabled:
        upload_artifact(ctx, "promotion.json", promotion_path)
        task_tags = [f"stage:{stage}"]
        if set_champion:
            task_tags.append("champion:current")
        if rollback:
            task_tags.append("rollback:true")
        try:
            add_task_tags(ctx, task_tags)
        except Exception as exc:
            warnings.append(f"Failed to update ClearML task tags: {exc}")
        props = {
            "promotion_stage": stage,
            "promoted_model_id": recommended_model_id,
            "promotion_source": source,
            "primary_metric": primary_metric,
            "best_score": best_score,
            "registry_model_id": registry_model_id,
            "registry_status": registry_status,
            "champion_usecase_id": usecase_id if registry_path else None,
            "champion_registry_path": str(registry_path) if registry_path else None,
            "set_champion": set_champion,
            "rollback": rollback,
        }
        if rollback_info and isinstance(rollback_info.get("from"), Mapping):
            rollback_from = rollback_info["from"]
            rollback_from_id = _normalize_str(rollback_from.get("model_id"))
            if rollback_from_id:
                props["rollback_from_model_id"] = rollback_from_id
        props = {key: value for key, value in props.items() if value is not None}
        try:
            update_task_properties(ctx, props)
        except Exception as exc:
            warnings.append(f"Failed to update ClearML task properties: {exc}")

    summary_lines = [
        "# Promotion Summary",
        "",
        f"- stage: {stage}",
        f"- model_id: {recommended_model_id}",
        f"- metric: {primary_metric if primary_metric is not None else 'unknown'}",
        f"- score: {best_score if best_score is not None else 'unknown'}",
        f"- source: {source}",
        f"- set_champion: {set_champion}",
        f"- rollback: {rollback}",
    ]
    if train_task_id:
        summary_lines.append(f"- train_task_id: {train_task_id}")
    if train_task_ref and train_task_ref != train_task_id:
        summary_lines.append(f"- train_task_ref: {train_task_ref}")
    if registry_path:
        summary_lines.append(f"- champion_registry: {registry_path}")
        summary_lines.append(f"- champion_usecase_id: {usecase_id}")
    if local_registry_state_path is not None:
        summary_lines.append(f"- model_registry_state: {local_registry_state_path}")
    if rollback_info and isinstance(rollback_info.get("from"), Mapping):
        rollback_from = rollback_info["from"]
        rollback_from_id = _normalize_str(rollback_from.get("model_id"))
        if rollback_from_id:
            summary_lines.append(f"- rollback_from_model_id: {rollback_from_id}")
    if note:
        summary_lines.append(f"- note: {note}")
    if warnings:
        summary_lines.extend(["", "## Warnings"])
        summary_lines.extend([f"- {line}" for line in warnings])
    summary_path = ctx.output_dir / "summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    if clearml_enabled:
        upload_artifact(ctx, "summary.md", summary_path)

    out: dict[str, Any] = {
        "promotion_json": str(promotion_path),
        "model_id": recommended_model_id,
        "stage": stage,
        "source": source,
        "promotion_status": "succeeded",
        "set_champion": set_champion,
        "rollback": rollback,
    }
    if primary_metric is not None:
        out["primary_metric"] = primary_metric
    if best_score is not None:
        out["best_score"] = best_score
    if registry_model_id:
        out["registry_model_id"] = registry_model_id
    if registry_status:
        out["registry_status"] = registry_status
    if registry_path:
        out["champion_registry_path"] = str(registry_path)
        out["champion_usecase_id"] = usecase_id
    if local_registry_state_path is not None:
        out["model_registry_state_path"] = str(local_registry_state_path)
    if warnings:
        out["warnings"] = warnings
    write_out_json(ctx, out)

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    inputs = {
        "model_id": recommended_model_id,
        "stage": stage,
        "source": source,
        "train_task_id": train_task_id,
        "train_task_ref": train_task_ref,
        "primary_metric": primary_metric,
        "set_champion": set_champion,
        "rollback": rollback,
    }
    if registry_path:
        inputs["champion_registry_path"] = str(registry_path)
    outputs: dict[str, Any] = {
        "promotion_json": str(promotion_path),
        "registry_model_id": registry_model_id,
        "registry_status": registry_status,
        "promotion_status": "succeeded",
    }
    if registry_path:
        outputs["champion_registry_path"] = str(registry_path)
    if local_registry_state_path is not None:
        outputs["model_registry_state_path"] = str(local_registry_state_path)
    hashes = {"config_hash": hash_config(cfg)}
    if meta.get("split_hash"):
        hashes["split_hash"] = meta.get("split_hash")
    if meta.get("recipe_hash"):
        hashes["recipe_hash"] = meta.get("recipe_hash")
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "promote_model",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
        "outputs": outputs,
        "hashes": hashes,
    }
    write_manifest(ctx, manifest)
