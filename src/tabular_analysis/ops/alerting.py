"""Alerting utilities for operational notifications."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping
import urllib.request

from ..platform_adapter import TaskContext, add_task_tags, resolve_output_dir, update_task_properties


_CONTEXT_CFG_KEY = "_cfg"
_CONTEXT_CTX_KEY = "_ctx"
_CONTEXT_OUTPUT_DIR_KEY = "_output_dir"


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


def _normalize_text(value: Any, fallback: str | None = None) -> str | None:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _normalize_kind(value: Any) -> str:
    key = _normalize_text(value, "unknown") or "unknown"
    return key.replace(" ", "_").lower()


def _normalize_severity(value: Any) -> str:
    key = _normalize_text(value, "info") or "info"
    lowered = key.lower()
    if lowered in ("warn", "warning"):
        return "warning"
    if lowered in ("err", "error", "failure", "failed"):
        return "error"
    if lowered in ("critical", "fatal"):
        return "critical"
    return lowered


def _coerce_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _coerce_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_coerce_json(item) for item in value]
    return str(value)


def _resolve_alert_settings(cfg: Any) -> dict[str, Any]:
    enabled = _cfg_value(cfg, "run.alerts.enabled", None)
    if enabled is None:
        enabled = _cfg_value(cfg, "alerts.enabled", None)
    enabled = bool(enabled) if enabled is not None else False

    file_enabled = _cfg_value(cfg, "run.alerts.sinks.file.enabled", None)
    if file_enabled is None:
        file_enabled = _cfg_value(cfg, "alerts.sinks.file.enabled", None)
    file_enabled = bool(file_enabled) if file_enabled is not None else True
    file_path = _cfg_value(cfg, "run.alerts.sinks.file.path", None)
    if file_path is None:
        file_path = _cfg_value(cfg, "alerts.sinks.file.path", None)

    stdout_enabled = _cfg_value(cfg, "run.alerts.sinks.stdout.enabled", None)
    if stdout_enabled is None:
        stdout_enabled = _cfg_value(cfg, "alerts.sinks.stdout.enabled", None)
    stdout_enabled = bool(stdout_enabled) if stdout_enabled is not None else False

    webhook_url = _normalize_text(
        _cfg_value(cfg, "run.alerts.sinks.webhook.url", None)
        or _cfg_value(cfg, "alerts.sinks.webhook.url", None)
    )
    webhook_enabled = _cfg_value(cfg, "run.alerts.sinks.webhook.enabled", None)
    if webhook_enabled is None:
        webhook_enabled = _cfg_value(cfg, "alerts.sinks.webhook.enabled", None)
    webhook_enabled = bool(webhook_enabled) if webhook_enabled is not None else bool(webhook_url)
    if not webhook_url:
        webhook_enabled = False

    timeout_value = (
        _cfg_value(cfg, "run.alerts.sinks.webhook.timeout_sec", None)
        or _cfg_value(cfg, "alerts.sinks.webhook.timeout_sec", None)
        or 5.0
    )
    try:
        timeout_sec = float(timeout_value)
    except Exception:
        timeout_sec = 5.0

    return {
        "enabled": enabled,
        "file": {"enabled": file_enabled, "path": file_path},
        "stdout": {"enabled": stdout_enabled},
        "webhook": {"enabled": webhook_enabled, "url": webhook_url, "timeout_sec": timeout_sec},
    }


def _extract_context(context_dict: Mapping[str, Any] | None) -> tuple[Any, Any, Any, dict[str, Any]]:
    cfg = None
    ctx = None
    output_dir = None
    context: dict[str, Any] = {}
    if not context_dict:
        return cfg, ctx, output_dir, context
    for key, value in context_dict.items():
        if key == _CONTEXT_CFG_KEY:
            cfg = value
            continue
        if key == _CONTEXT_CTX_KEY:
            ctx = value
            continue
        if key == _CONTEXT_OUTPUT_DIR_KEY:
            output_dir = value
            continue
        context[key] = value
    return cfg, ctx, output_dir, context


def _resolve_output_dir(cfg: Any, ctx: Any, output_dir: Any) -> Path | None:
    if output_dir is not None:
        return Path(str(output_dir)).expanduser().resolve()
    if isinstance(ctx, TaskContext):
        return ctx.output_dir
    stage = _cfg_value(cfg, "task.stage")
    if stage is not None:
        try:
            return resolve_output_dir(cfg, str(stage))
        except Exception:
            return None
    run_output = _cfg_value(cfg, "run.output_dir")
    if run_output is not None:
        return Path(str(run_output)).expanduser().resolve()
    return None


def _resolve_log_path(path_value: Any, output_dir: Path | None) -> Path | None:
    if path_value:
        candidate = Path(str(path_value)).expanduser()
        if candidate.exists() and candidate.is_dir():
            return candidate / "alerts.jsonl"
        if candidate.suffix:
            return candidate
        return candidate / "alerts.jsonl"
    if output_dir is None:
        return None
    return output_dir / "alerts.jsonl"


def _post_webhook(url: str, payload: Mapping[str, Any], timeout_sec: float) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        response.read()


def emit_alert(
    kind: Any,
    severity: Any,
    title: Any,
    message: Any,
    context_dict: Mapping[str, Any] | None = None,
) -> bool:
    """Emit an alert to configured sinks.

    Reserved keys in context_dict:
    - _cfg: Hydra/OmegaConf config
    - _ctx: TaskContext
    - _output_dir: override output directory for file sink
    """

    cfg, ctx, output_dir_value, context = _extract_context(context_dict)
    settings = _resolve_alert_settings(cfg)
    if not settings["enabled"]:
        return False

    kind_value = _normalize_kind(kind)
    severity_value = _normalize_severity(severity)
    title_value = _normalize_text(title, "") or ""
    message_value = _normalize_text(message, "") or ""

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload: dict[str, Any] = {
        "timestamp": timestamp,
        "kind": kind_value,
        "severity": severity_value,
        "title": title_value,
        "message": message_value,
    }

    usecase_id = _normalize_text(
        _cfg_value(cfg, "run.usecase_id") or _cfg_value(cfg, "usecase_id")
    )
    stage = _normalize_text(_cfg_value(cfg, "task.stage"))
    process = _normalize_text(_cfg_value(cfg, "task.name"))
    task_name = _normalize_text(getattr(ctx, "task_name", None)) if ctx is not None else None
    project_name = _normalize_text(getattr(ctx, "project_name", None)) if ctx is not None else None

    if usecase_id:
        payload["usecase_id"] = usecase_id
    if stage:
        payload["stage"] = stage
    if process:
        payload["process"] = process
    if task_name:
        payload["task_name"] = task_name
    if project_name:
        payload["project_name"] = project_name
    if context:
        payload["context"] = _coerce_json(context)

    errors: list[Exception] = []
    any_success = False

    output_dir = _resolve_output_dir(cfg, ctx, output_dir_value)
    if settings["file"]["enabled"]:
        log_path = _resolve_log_path(settings["file"]["path"], output_dir)
        if log_path is None:
            errors.append(ValueError("alert file sink enabled but path could not be resolved."))
        else:
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with log_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
                any_success = True
            except Exception as exc:
                errors.append(exc)

    if settings["stdout"]["enabled"]:
        try:
            print(json.dumps(payload, ensure_ascii=False))
            any_success = True
        except Exception as exc:
            errors.append(exc)

    if settings["webhook"]["enabled"] and settings["webhook"]["url"]:
        try:
            _post_webhook(settings["webhook"]["url"], payload, settings["webhook"]["timeout_sec"])
            any_success = True
        except Exception as exc:
            errors.append(exc)

    if isinstance(ctx, TaskContext) and ctx.task is not None:
        add_task_tags(ctx, [f"alert:{kind_value}", f"severity:{severity_value}"])
        props = {
            "last_alert_kind": kind_value,
            "last_alert_severity": severity_value,
            "last_alert_title": title_value,
            "last_alert_at": timestamp,
        }
        update_task_properties(ctx, props)
        any_success = True

    if not any_success and errors:
        raise RuntimeError(f"All alert sinks failed: {errors[0]}")

    return any_success
