"""Metrics."""

from __future__ import annotations

from typing import Callable


def get_metric(name: str) -> Callable:
    key = str(name or "").strip().lower()
    if not key:
        raise ValueError("metric name is required.")

    try:
        import numpy as np  # type: ignore
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score  # type: ignore
    except Exception as exc:
        raise RuntimeError("scikit-learn is required for metrics.") from exc

    if key in ("rmse", "root_mean_squared_error"):
        return lambda y_true, y_pred: float(np.sqrt(mean_squared_error(y_true, y_pred)))
    if key in ("mae", "mean_absolute_error"):
        return lambda y_true, y_pred: float(mean_absolute_error(y_true, y_pred))
    if key in ("r2", "r2_score"):
        return lambda y_true, y_pred: float(r2_score(y_true, y_pred))

    raise ValueError(f"Unsupported metric: {name}")
