"""Optuna Plotly visuals for optimize infer mode."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence


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


def _render_placeholder(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageDraw  # type: ignore

        img = Image.new("RGB", (640, 420), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(10, 10), (630, 410)], outline=(0, 0, 0), width=2)
        draw.text((20, 20), title, fill=(0, 0, 0))
        img.save(path, format="PNG")
        return
    except Exception:
        _write_minimal_png(path)


def _fallback_image(path: Path | None, title: str) -> Path | None:
    if path is None:
        return None
    _render_placeholder(path, title)
    return path


def _normalize_params(params: Sequence[str] | None) -> list[str] | None:
    if not params:
        return None
    normalized: list[str] = []
    for item in params:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized or None


def build_optimization_history(
    study: Any,
    *,
    log_scale: bool = False,
    output_path: Path | None = None,
) -> Any | Path | None:
    try:
        from optuna.visualization import plot_optimization_history  # type: ignore
    except Exception:
        return _fallback_image(output_path, "Optimization History")
    try:
        fig = plot_optimization_history(study)
    except Exception:
        return _fallback_image(output_path, "Optimization History")
    if log_scale and hasattr(fig, "update_yaxes"):
        try:
            fig.update_yaxes(type="log")
        except Exception:
            pass
    return fig


def build_parallel_coordinate(
    study: Any,
    *,
    output_path: Path | None = None,
) -> Any | Path | None:
    try:
        from optuna.visualization import plot_parallel_coordinate  # type: ignore
    except Exception:
        return _fallback_image(output_path, "Parallel Coordinate")
    try:
        fig = plot_parallel_coordinate(study)
    except Exception:
        return _fallback_image(output_path, "Parallel Coordinate")
    return fig


def build_param_importance(
    study: Any,
    *,
    output_path: Path | None = None,
) -> Any | Path | None:
    try:
        from optuna.visualization import plot_param_importances  # type: ignore
    except Exception:
        return _fallback_image(output_path, "Param Importances")
    try:
        fig = plot_param_importances(study)
    except Exception:
        return _fallback_image(output_path, "Param Importances")
    return fig


def build_contour(
    study: Any,
    *,
    params: Sequence[str] | None = None,
    output_path: Path | None = None,
) -> Any | Path | None:
    try:
        from optuna.visualization import plot_contour  # type: ignore
    except Exception:
        return _fallback_image(output_path, "Response Surface")
    param_list = _normalize_params(params)
    try:
        if param_list:
            fig = plot_contour(study, params=param_list)
        else:
            fig = plot_contour(study)
    except Exception:
        return _fallback_image(output_path, "Response Surface")
    return fig
