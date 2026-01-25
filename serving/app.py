"""Serving API entrypoint (FastAPI optional)."""

from __future__ import annotations

from tabular_analysis.serve.app import app, create_app

__all__ = ["app", "create_app"]
