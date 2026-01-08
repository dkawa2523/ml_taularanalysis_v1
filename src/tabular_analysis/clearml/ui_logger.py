"""ClearML UI logging helpers (Scalars / Plots / Debug Samples)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def _get_logger(task: Any) -> Any | None:
    if task is None:
        return None
    getter = getattr(task, "get_logger", None)
    if not callable(getter):
        return None
    try:
        return getter()
    except Exception:
        return None


def _as_path(value: Any) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


def _to_dataframe(value: Any, *, max_rows: int = 20) -> Any | None:
    if value is None:
        return None
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return None
    if isinstance(value, pd.DataFrame):
        return value.head(max_rows)
    if isinstance(value, Mapping):
        return pd.DataFrame([value])
    if isinstance(value, list):
        if not value:
            return pd.DataFrame()
        if isinstance(value[0], Mapping):
            return pd.DataFrame(value).head(max_rows)
        return pd.DataFrame(value).head(max_rows)
    return None


def log_scalar(task: Any, title: str, series: str, value: Any, step: int = 0) -> bool:
    logger = _get_logger(task)
    if logger is None or value is None:
        return False
    reporter = getattr(logger, "report_scalar", None)
    if not callable(reporter):
        return False
    try:
        reporter(title=str(title), series=str(series), iteration=int(step), value=float(value))
        return True
    except Exception:
        try:
            reporter(str(title), str(series), int(step), value)
            return True
        except Exception:
            return False


def log_plotly(task: Any, title: str, series: str, fig: Any, step: int = 0) -> bool:
    if fig is None:
        return False
    logger = _get_logger(task)
    if logger is None:
        return False
    path = _as_path(fig)
    if path is not None:
        reporter = getattr(logger, "report_image", None)
        if not callable(reporter):
            return log_debug_text(task, title, series, f"plot image: {path}", step=step)
        if not path.exists():
            return False
        try:
            reporter(
                title=str(title),
                series=str(series),
                iteration=int(step),
                local_path=str(path),
            )
            return True
        except Exception:
            try:
                reporter(str(title), str(series), int(step), local_path=str(path))
                return True
            except Exception:
                return False
    reporter = getattr(logger, "report_plotly", None)
    if callable(reporter):
        try:
            reporter(title=str(title), series=str(series), iteration=int(step), figure=fig)
            return True
        except Exception:
            try:
                reporter(str(title), str(series), int(step), fig)
                return True
            except Exception:
                pass
    payload = None
    if hasattr(fig, "to_plotly_json"):
        try:
            payload = json.dumps(fig.to_plotly_json(), ensure_ascii=True)
        except Exception:
            payload = None
    if payload is None:
        payload = str(fig)
    return log_debug_text(task, title, series, payload, step=step)


def report_plotly(task: Any, title: str, series: str, fig: Any, step: int = 0) -> bool:
    return log_plotly(task, title, series, fig, step=step)


def report_input_output_table(
    task: Any,
    title: str,
    series: str,
    input_sample: Any,
    output_sample: Any,
    *,
    max_rows: int = 5,
    max_input_columns: int = 20,
    max_output_columns: int = 12,
    output_path: str | Path | None = None,
    step: int = 0,
) -> bool:
    try:
        from ..viz.infer_plots import build_input_output_table
    except Exception:
        return False
    fig = build_input_output_table(
        input_sample,
        output_sample,
        max_rows=max_rows,
        max_input_columns=max_input_columns,
        max_output_columns=max_output_columns,
        output_path=_as_path(output_path) if output_path is not None else None,
    )
    if fig is None:
        return False
    return log_plotly(task, title, series, fig, step=step)


def log_debug_text(task: Any, title: str, series: str, text: Any, step: int = 0) -> bool:
    logger = _get_logger(task)
    if logger is None or text is None:
        return False
    reporter = getattr(logger, "report_text", None)
    if not callable(reporter):
        return False
    payload = str(text)
    if not payload:
        return False
    header = ""
    if title or series:
        header = f"[{title}/{series}]\n"
    payload = f"{header}{payload}"
    try:
        reporter(payload, print_console=False)
        return True
    except Exception:
        try:
            reporter(text=payload, print_console=False)
            return True
        except Exception:
            return False


def log_debug_table(task: Any, title: str, series: str, df: Any, step: int = 0) -> bool:
    logger = _get_logger(task)
    if logger is None or df is None:
        return False
    reporter = getattr(logger, "report_table", None)
    if not callable(reporter):
        return log_debug_text(task, title, series, str(df), step=step)
    dataframe = _to_dataframe(df)
    if dataframe is None:
        return log_debug_text(task, title, series, str(df), step=step)
    try:
        reporter(title=str(title), series=str(series), iteration=int(step), dataframe=dataframe)
        return True
    except Exception:
        try:
            records = dataframe.to_dict(orient="records")
        except Exception:
            records = None
        if records is not None:
            try:
                reporter(title=str(title), series=str(series), iteration=int(step), data=records)
                return True
            except Exception:
                pass
        try:
            csv_text = dataframe.to_csv(index=False)
        except Exception:
            csv_text = str(dataframe)
        return log_debug_text(task, title, series, csv_text, step=step)
