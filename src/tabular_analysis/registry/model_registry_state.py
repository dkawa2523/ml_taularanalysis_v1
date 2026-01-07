"""Local model registry state helpers.

These helpers keep a lightweight stage history for offline runs so that
rollback/champion-challenger can work without ClearML.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

_SCHEMA_VERSION = 1


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_entry(entry: Mapping[str, Any], stage: str) -> dict[str, Any]:
    payload = {str(key): value for key, value in entry.items() if value is not None}
    payload.setdefault("stage", stage)
    return payload


def load_registry_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": _SCHEMA_VERSION, "updated_at": None, "usecases": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"model_registry_state.json is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("model_registry_state.json must contain a JSON object.")
    payload.setdefault("schema_version", _SCHEMA_VERSION)
    usecases = payload.get("usecases")
    if not isinstance(usecases, dict):
        payload["usecases"] = {}
    return payload


def write_registry_state(path: Path, registry: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(registry, ensure_ascii=True, indent=2)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    tmp_path.replace(path)


def ensure_usecase_entry(registry: dict[str, Any], usecase_id: str) -> dict[str, Any]:
    usecases = registry.get("usecases")
    if not isinstance(usecases, dict):
        usecases = {}
        registry["usecases"] = usecases
    entry = usecases.get(usecase_id)
    if not isinstance(entry, dict):
        entry = {}
        usecases[usecase_id] = entry
    stages = entry.get("stages")
    if not isinstance(stages, dict):
        stages = {}
        entry["stages"] = stages
    return entry


def ensure_stage_entry(usecase_entry: dict[str, Any], stage: str) -> dict[str, Any]:
    stages = usecase_entry.get("stages")
    if not isinstance(stages, dict):
        stages = {}
        usecase_entry["stages"] = stages
    entry = stages.get(stage)
    if not isinstance(entry, dict):
        entry = {}
        stages[stage] = entry
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


def get_current_entry(
    registry: dict[str, Any],
    *,
    usecase_id: str,
    stage: str,
) -> dict[str, Any] | None:
    usecase = ensure_usecase_entry(registry, usecase_id)
    stage_entry = ensure_stage_entry(usecase, stage)
    current = stage_entry.get("current")
    if isinstance(current, Mapping):
        return dict(current)
    return None


def update_stage_state(
    registry: dict[str, Any],
    *,
    usecase_id: str,
    stage: str,
    entry: Mapping[str, Any],
) -> dict[str, Any]:
    usecase = ensure_usecase_entry(registry, usecase_id)
    stage_entry = ensure_stage_entry(usecase, stage)
    current = stage_entry.get("current") if isinstance(stage_entry.get("current"), Mapping) else None
    history = stage_entry.get("history")
    if not isinstance(history, list):
        history = []
        stage_entry["history"] = history
    if current is not None:
        history.insert(0, dict(current))
    normalized = _normalize_entry(entry, stage)
    stage_entry["current"] = normalized
    stage_entry["updated_at"] = _timestamp()
    registry["updated_at"] = _timestamp()
    return {"current": normalized, "previous": current}


def rollback_stage_state(
    registry: dict[str, Any],
    *,
    usecase_id: str,
    stage: str,
    target_model_id: str | None = None,
) -> dict[str, Any]:
    usecase = ensure_usecase_entry(registry, usecase_id)
    stage_entry = ensure_stage_entry(usecase, stage)
    current = stage_entry.get("current") if isinstance(stage_entry.get("current"), Mapping) else None
    history = stage_entry.get("history")
    if not isinstance(history, list):
        history = []
        stage_entry["history"] = history
    target = None
    if target_model_id:
        for idx, item in enumerate(list(history)):
            if not isinstance(item, Mapping):
                continue
            if str(item.get("model_id")) == str(target_model_id):
                target = dict(history.pop(idx))
                break
        if target is None:
            target = {"model_id": target_model_id, "source": "manual", "stage": stage}
    else:
        if not history:
            raise ValueError("rollback requested but no previous model is available in registry state.")
        target = dict(history.pop(0))
    if current is not None and target_model_id != str(current.get("model_id")):
        history.insert(0, dict(current))
    target = _normalize_entry(target, stage)
    stage_entry["current"] = target
    stage_entry["updated_at"] = _timestamp()
    registry["updated_at"] = _timestamp()
    return {"before": current, "after": target, "target": target}
