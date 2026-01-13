"""ClearML reporting helpers with config-driven toggles."""

from __future__ import annotations

from collections.abc import Mapping as MappingABC, Sequence as SequenceABC
from pathlib import Path
from typing import Any

from . import ui_logger


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
        if isinstance(current, MappingABC):
            if key not in current:
                return default
            current = current[key]
            continue
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
    return bool(value)


def _reporting_flag(cfg: Any, key: str, default: bool) -> bool:
    value = _cfg_value(cfg, f"run.clearml.reporting.{key}", default)
    return _normalize_bool(value, default)


def scalars_enabled(cfg: Any, *, default: bool = True) -> bool:
    return _reporting_flag(cfg, "enable_scalars", default)


def plots_enabled(cfg: Any, *, default: bool = True) -> bool:
    return _reporting_flag(cfg, "enable_plots", default)


def tables_enabled(cfg: Any, *, default: bool = True) -> bool:
    return _reporting_flag(cfg, "enable_tables", default)


def report_scalar(
    task: Any,
    title: str,
    series: str,
    value: Any,
    iteration: int = 0,
    *,
    cfg: Any | None = None,
) -> bool:
    if not scalars_enabled(cfg):
        return False
    return ui_logger.log_scalar(task, title, series, value, step=iteration)


def report_plotly(
    task: Any,
    title: str,
    series: str,
    fig: Any,
    iteration: int = 0,
    *,
    cfg: Any | None = None,
) -> bool:
    if not plots_enabled(cfg):
        return False
    return ui_logger.log_plotly(task, title, series, fig, step=iteration)


def report_table(
    task: Any,
    title: str,
    series: str,
    table: Any,
    iteration: int = 0,
    *,
    cfg: Any | None = None,
    output_path: str | Path | None = None,
    max_rows: int = 20,
    max_columns: int = 20,
) -> bool:
    if not (plots_enabled(cfg) and tables_enabled(cfg)):
        return False
    if table is None:
        return False
    path = _as_path(table)
    if path is not None or _is_plotly_figure(table):
        return ui_logger.log_plotly(task, title, series, table, step=iteration)
    dataframe = _to_dataframe(table, max_rows=max_rows, max_columns=max_columns)
    if dataframe is None:
        return ui_logger.log_debug_table(task, title, series, table, step=iteration)
    fig = _build_plotly_table(dataframe, title=title)
    if fig is not None:
        return ui_logger.log_plotly(task, title, series, fig, step=iteration)
    image_path = _render_table_image(
        dataframe,
        output_path=output_path,
        title=title,
        max_rows=max_rows,
        max_columns=max_columns,
    )
    if image_path is not None:
        return ui_logger.log_plotly(task, title, series, image_path, step=iteration)
    return ui_logger.log_debug_table(task, title, series, dataframe, step=iteration)


def report_input_output_table(
    task: Any,
    title: str,
    series: str,
    input_sample: Any,
    output_sample: Any,
    *,
    cfg: Any | None = None,
    max_rows: int = 5,
    max_input_columns: int = 20,
    max_output_columns: int = 12,
    output_path: str | Path | None = None,
    iteration: int = 0,
) -> bool:
    if not (plots_enabled(cfg) and tables_enabled(cfg)):
        return False
    return ui_logger.report_input_output_table(
        task,
        title,
        series,
        input_sample,
        output_sample,
        max_rows=max_rows,
        max_input_columns=max_input_columns,
        max_output_columns=max_output_columns,
        output_path=output_path,
        step=iteration,
    )


def _as_path(value: Any) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


def _is_plotly_figure(value: Any) -> bool:
    return hasattr(value, "to_plotly_json")


def _to_dataframe(value: Any, *, max_rows: int, max_columns: int) -> Any | None:
    if value is None:
        return None
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return None
    if isinstance(value, pd.DataFrame):
        df = value.copy()
    elif isinstance(value, MappingABC):
        df = pd.DataFrame([dict(value)])
    elif isinstance(value, SequenceABC) and not isinstance(value, (str, bytes)):
        if not value:
            df = pd.DataFrame()
        elif all(isinstance(item, MappingABC) for item in value):
            df = pd.DataFrame([dict(item) for item in value])
        else:
            df = pd.DataFrame(value)
    else:
        return None
    if max_rows > 0:
        df = df.head(max_rows)
    if max_columns > 0:
        try:
            if df.shape[1] > max_columns:
                df = df.iloc[:, :max_columns]
        except Exception:
            pass
    return df


def _plotly_go():
    try:
        import plotly.graph_objects as go  # type: ignore
    except Exception:
        return None
    return go


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    try:
        import pandas as pd  # type: ignore

        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value)
    if len(text) > 80:
        return text[:77] + "..."
    return text


def _build_plotly_table(dataframe: Any, *, title: str) -> Any | None:
    go = _plotly_go()
    if go is None:
        return None
    try:
        columns = list(getattr(dataframe, "columns", []))
    except Exception:
        return None
    values: list[list[str]] = []
    for col in columns:
        try:
            col_values = dataframe[col].tolist()
        except Exception:
            col_values = []
        values.append([_stringify(value) for value in col_values])
    fig = go.Figure(
        data=[
            go.Table(
                header=dict(values=[str(col) for col in columns], fill_color="#F2F2F2", align="left"),
                cells=dict(values=values, fill_color="#FFFFFF", align="left"),
            )
        ]
    )
    fig.update_layout(title=title, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def _import_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None
    return plt


def _write_minimal_png(path: Path) -> None:
    import struct
    import zlib

    width = 1
    height = 1
    raw = b"\x00\xff\xff\xff\xff"
    compressed = zlib.compress(raw)

    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", compressed) + _chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def _render_table_image(
    dataframe: Any,
    *,
    output_path: str | Path | None,
    title: str,
    max_rows: int,
    max_columns: int,
) -> Path | None:
    path = _as_path(output_path)
    if path is None:
        return None
    plt = _import_matplotlib()
    if plt is None:
        _write_minimal_png(path)
        return path
    try:
        df = dataframe.copy()
    except Exception:
        df = dataframe
    if max_rows > 0:
        try:
            df = df.head(max_rows)
        except Exception:
            pass
    if max_columns > 0:
        try:
            if df.shape[1] > max_columns:
                df = df.iloc[:, :max_columns]
        except Exception:
            pass
    try:
        columns = list(getattr(df, "columns", []))
    except Exception:
        columns = []
    rows: list[list[str]] = []
    try:
        values = df.values.tolist()
    except Exception:
        values = []
    for row in values:
        rows.append([_stringify(value) for value in row])
    width = max(4.0, 0.65 * max(1, len(columns)))
    height = max(2.5, 0.35 * max(1, len(rows)))
    fig, ax = plt.subplots(figsize=(width, height))
    ax.axis("off")
    table = ax.table(cellText=rows, colLabels=[str(col) for col in columns], loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    fig.suptitle(title or "Table", fontsize=10)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
