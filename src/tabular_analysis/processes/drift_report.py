"""Drift report helpers for monitoring workflows."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping, Sequence


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


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except Exception:
        return None
    if not math.isfinite(num):
        return None
    return num


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _normalize_metrics(value: Any) -> list[str]:
    if value is None:
        return ["psi", "ks"]
    items: list[str] = []
    if isinstance(value, str):
        parts = [part.strip() for part in value.replace(",", " ").split()]
        items = [part for part in parts if part]
    elif isinstance(value, Mapping):
        items = [str(key) for key in value.keys()]
    elif isinstance(value, (list, tuple, set)):
        items = [str(item) for item in value if item is not None]
    else:
        try:
            items = [str(item) for item in list(value) if item is not None]
        except Exception:
            items = [str(value)]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.strip().lower()
        if key in ("psi", "ks") and key not in seen:
            normalized.append(key)
            seen.add(key)
    if not normalized:
        normalized.append("psi")
    return normalized


def resolve_drift_settings(cfg: Any) -> dict[str, Any]:
    monitor_enabled = bool(_cfg_value(cfg, "monitor.drift.enabled", False))
    infer_enabled = bool(_cfg_value(cfg, "infer.drift.enabled", False))
    enabled = monitor_enabled or infer_enabled

    sample_n = _coerce_int(_cfg_value(cfg, "monitor.drift.sample_n", 5000))
    if sample_n is not None and sample_n <= 0:
        sample_n = None

    metrics = _normalize_metrics(_cfg_value(cfg, "monitor.drift.metrics", None))

    psi_alert = _coerce_float(_cfg_value(cfg, "monitor.drift.alert_thresholds.psi", None))
    warn_threshold = psi_alert
    if warn_threshold is None:
        warn_threshold = _coerce_float(_cfg_value(cfg, "infer.drift.psi_warn_threshold", None))
    if warn_threshold is None:
        warn_threshold = 0.2
    fail_threshold = _coerce_float(_cfg_value(cfg, "infer.drift.psi_fail_threshold", None))

    sample_seed = _coerce_int(_cfg_value(cfg, "eval.seed", 42))
    if sample_seed is None:
        sample_seed = 42

    return {
        "enabled": enabled,
        "sample_n": sample_n,
        "sample_seed": sample_seed,
        "metrics": metrics,
        "psi_warn_threshold": warn_threshold,
        "psi_fail_threshold": fail_threshold,
        "alert_thresholds": {"psi": warn_threshold},
    }


def sample_frame(
    df: Any, *, sample_n: int | None, seed: int | None = None
) -> tuple[Any, dict[str, Any]]:
    rows = int(getattr(df, "shape", [0, 0])[0] or 0)
    info = {
        "rows": rows,
        "sample_n": sample_n,
        "sampled": False,
        "sampled_rows": rows,
        "seed": seed,
    }
    if sample_n is None or sample_n <= 0 or rows <= sample_n:
        return df, info
    if hasattr(df, "sample"):
        try:
            sampled = df.sample(n=int(sample_n), random_state=seed)
            info["sampled"] = True
            info["sampled_rows"] = int(sample_n)
            return sampled, info
        except Exception:
            pass
    try:
        import numpy as np  # type: ignore
    except Exception:
        return df, info
    rng = np.random.default_rng(seed)
    indices = rng.choice(rows, size=int(sample_n), replace=False)
    try:
        sampled = df.iloc[indices]
    except Exception:
        sampled = df[indices]
    info["sampled"] = True
    info["sampled_rows"] = int(sample_n)
    return sampled, info


def annotate_profile(
    profile: dict[str, Any],
    *,
    role: str | None = None,
    sample_info: Mapping[str, Any] | None = None,
    metrics: Sequence[str] | None = None,
) -> dict[str, Any]:
    if role:
        profile["role"] = str(role)
    if sample_info:
        profile["sampling"] = dict(sample_info)
    if metrics:
        settings = profile.get("settings")
        if isinstance(settings, dict):
            settings["metrics"] = [str(item) for item in metrics]
    return profile


def _select_metric(report: Mapping[str, Any]) -> str:
    metrics = report.get("metrics") or []
    normalized = [str(item).lower() for item in metrics if item is not None]
    if "psi" in normalized:
        return "psi"
    if "ks" in normalized:
        return "ks"
    return "psi"


def _collect_top_features(
    report: Mapping[str, Any], *, metric: str, limit: int = 5
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for kind in ("numeric", "categorical"):
        section = report.get(kind) or {}
        if not isinstance(section, Mapping):
            continue
        for name, entry in section.items():
            value = entry.get(metric)
            if value is None:
                continue
            candidates.append(
                {
                    "feature": str(name),
                    "value": float(value),
                    "status": entry.get("status"),
                    "kind": kind,
                }
            )
    candidates.sort(key=lambda item: item["value"], reverse=True)
    return candidates[: int(max(limit, 0))]


def build_drift_summary_lines(
    report: Mapping[str, Any],
    *,
    limit: int = 5,
    drift_alert: bool | None = None,
) -> list[str]:
    if not report:
        return []
    summary = report.get("summary") or {}
    lines = ["## Drift Summary"]
    lines.append(f"- rows: {report.get('rows')}")
    metrics = report.get("metrics") or []
    if metrics:
        lines.append(f"- metrics: {', '.join([str(item) for item in metrics])}")
    if "psi_max" in summary:
        lines.append(f"- psi_max: {summary.get('psi_max')}")
    if "psi_mean" in summary:
        lines.append(f"- psi_mean: {summary.get('psi_mean')}")
    if "ks_max" in summary:
        lines.append(f"- ks_max: {summary.get('ks_max')}")
    if "ks_mean" in summary:
        lines.append(f"- ks_mean: {summary.get('ks_mean')}")
    if "warn_count" in summary:
        lines.append(f"- warn_count: {summary.get('warn_count')}")
    if "fail_count" in summary:
        lines.append(f"- fail_count: {summary.get('fail_count')}")
    if drift_alert is not None:
        lines.append(f"- drift_alert: {bool(drift_alert)}")

    metric = _select_metric(report)
    top_features = _collect_top_features(report, metric=metric, limit=limit)
    if top_features:
        lines.append("")
        lines.append("### Top Drift Features")
        for item in top_features:
            value = item["value"]
            status = item.get("status")
            lines.append(
                f"- {item['feature']} ({item['kind']}): {metric}={value:.4f} [{status}]"
            )
    return lines


def append_drift_summary(
    summary_path: Path,
    report: Mapping[str, Any],
    *,
    limit: int = 5,
    drift_alert: bool | None = None,
) -> None:
    lines = build_drift_summary_lines(report, limit=limit, drift_alert=drift_alert)
    if not lines:
        return
    content = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
    if content and not content.endswith("\n"):
        content += "\n"
    if content:
        content += "\n"
    content += "\n".join(lines) + "\n"
    summary_path.write_text(content, encoding="utf-8")
