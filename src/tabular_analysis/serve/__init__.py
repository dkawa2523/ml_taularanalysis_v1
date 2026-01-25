"""Optional serving helpers (FastAPI)."""

from __future__ import annotations

from typing import Any


def create_app(model_bundle_path: str | None = None, *, strict_schema: bool | None = None) -> Any:
    """Create a FastAPI app with the loaded model bundle."""
    from .app import create_app as _create_app

    return _create_app(model_bundle_path=model_bundle_path, strict_schema=strict_schema)


__all__ = ["create_app"]
