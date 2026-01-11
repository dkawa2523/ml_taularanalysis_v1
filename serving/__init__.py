"""Serving entrypoints (wrapper for tabular_analysis.serve)."""

from __future__ import annotations

from tabular_analysis.serve.app import app, create_app

__all__ = ["app", "create_app"]
