"""Serving settings parsed from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

_ALLOWED_SCHEMA_MODES = ("strict", "warn", "coerce")
_ALLOWED_STAGES = ("production", "staging", "archived")


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_schema_mode(value: str | None) -> str:
    if not value:
        return "coerce"
    mode = str(value).strip().lower()
    if mode == "warning":
        mode = "warn"
    if mode not in _ALLOWED_SCHEMA_MODES:
        raise ValueError(
            f"SCHEMA_MODE must be one of {', '.join(_ALLOWED_SCHEMA_MODES)} (got: {value})"
        )
    return mode


def _normalize_stage(value: str | None) -> str | None:
    if value is None:
        return None
    stage = str(value).strip().lower()
    if not stage:
        return None
    if stage == "prod":
        stage = "production"
    if stage == "stage":
        stage = "staging"
    if stage == "archive":
        stage = "archived"
    if stage not in _ALLOWED_STAGES:
        raise ValueError(
            f"MODEL_STAGE must be one of {', '.join(_ALLOWED_STAGES)} (got: {value})"
        )
    return stage


def _parse_api_keys(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    parts = [item.strip() for item in value.split(",")]
    return tuple(part for part in parts if part)


def _path_from_env(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser()


@dataclass(frozen=True)
class ServingSettings:
    api_keys: tuple[str, ...]
    model_stage: str | None
    model_ref: str | None
    audit_log_path: Path | None
    schema_mode: str

    @property
    def auth_required(self) -> bool:
        return bool(self.api_keys)

    def with_overrides(self, **kwargs: object) -> "ServingSettings":
        return replace(self, **kwargs)

    @classmethod
    def from_env(cls) -> "ServingSettings":
        api_keys = _parse_api_keys(os.getenv("API_KEY"))
        model_stage = _normalize_stage(os.getenv("MODEL_STAGE"))
        model_ref = _normalize_text(os.getenv("MODEL_REF"))
        audit_log_path = _path_from_env(os.getenv("AUDIT_LOG_PATH"))
        schema_mode = _normalize_schema_mode(os.getenv("SCHEMA_MODE"))
        return cls(
            api_keys=api_keys,
            model_stage=model_stage,
            model_ref=model_ref,
            audit_log_path=audit_log_path,
            schema_mode=schema_mode,
        )


__all__ = ["ServingSettings"]
