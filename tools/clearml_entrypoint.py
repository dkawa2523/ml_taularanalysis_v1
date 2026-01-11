#!/usr/bin/env python3
"""ClearML entrypoint wrapper for src/ layout."""

import os
import sys
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for base in candidates:
        for parent in [base, *base.parents]:
            if (parent / "conf").exists():
                return parent
    raise RuntimeError("Could not locate repo root containing conf/ directory.")


def _flatten_params(prefix: str, value: Any, out: dict[str, Any], *, sep: str = ".") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            next_prefix = f"{prefix}{sep}{key}" if prefix else str(key)
            _flatten_params(next_prefix, item, out, sep=sep)
        return
    if prefix:
        out[prefix] = value


def _extract_cli_keys(argv: list[str]) -> set[str]:
    keys: set[str] = set()
    for item in argv:
        if not item or item.startswith("-") or "=" not in item:
            continue
        key = item.split("=", 1)[0].strip()
        if key:
            keys.add(key)
    return keys


def _looks_like_container(text: str) -> bool:
    return (text.startswith("[") and text.endswith("]")) or (text.startswith("{") and text.endswith("}"))


def _needs_quote(text: str) -> bool:
    if not text:
        return True
    if _looks_like_container(text):
        return False
    for ch in text:
        if ch.isspace() or ch in "(),":
            return True
    return False


def _quote(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _format_override_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    return _quote(text) if _needs_quote(text) else text


def _load_clearml_overrides() -> dict[str, Any]:
    def _warn(message: str) -> None:
        print(f"[clearml_entrypoint] {message}", file=sys.stderr)

    def _resolve_task_id() -> str | None:
        for key in (
            "CLEARML_TASK_ID",
            "TRAINS_TASK_ID",
            "CLEARML_AGENT_TASK_ID",
            "TASK_ID",
            "CLEARML_TASK",
        ):
            value = os.getenv(key)
            if value:
                return str(value)
        return None

    try:
        from clearml import Task  # type: ignore
    except Exception:
        return {}
    def _collect_overrides(task: Any) -> dict[str, Any]:
        overrides: dict[str, Any] = {}
        params: Any = {}
        try:
            params = task.get_parameters() or {}
        except Exception:
            params = {}
        if isinstance(params, dict):
            args_section = params.get("Args")
            if isinstance(args_section, dict):
                for key, value in args_section.items():
                    _flatten_params(str(key), value, overrides, sep="/")
            else:
                for key, value in params.items():
                    if not isinstance(key, str) or not key.startswith("Args/"):
                        continue
                    override_key = key[5:]
                    if override_key:
                        overrides[override_key] = value
        if overrides:
            return overrides
        params = {}
        try:
            params = task.get_parameters_as_dict() or {}
        except Exception:
            params = {}
        args_section = params.get("Args") if isinstance(params, dict) else None
        if isinstance(args_section, dict):
            for key, value in args_section.items():
                _flatten_params(str(key), value, overrides, sep="/")
        elif isinstance(params, dict):
            for key, value in params.items():
                if not isinstance(key, str) or not key.startswith("Args/"):
                    continue
                override_key = key[5:]
                if override_key:
                    overrides[override_key] = value
        return overrides

    task = Task.current_task()
    if task is not None:
        overrides = _collect_overrides(task)
        if overrides:
            return overrides

    task_id = _resolve_task_id()
    if task_id:
        try:
            task = Task.get_task(task_id=str(task_id))
        except Exception:
            _warn(f"failed to load ClearML task {task_id}; using CLI defaults.")
            task = None
        if task is not None:
            overrides = _collect_overrides(task)
            if overrides:
                return overrides
            _warn("no ClearML overrides detected; check task parameters and agent environment.")
    return {}


def _merge_clearml_overrides(argv: list[str]) -> list[str]:
    overrides = _load_clearml_overrides()
    if not overrides:
        return argv
    existing = _extract_cli_keys(argv)
    merged = list(argv)
    for key, value in overrides.items():
        if key in existing:
            continue
        merged.append(f"{key}={_format_override_value(value)}")
    return merged


def main(argv: list[str] | None = None) -> None:
    repo_root = _find_repo_root()
    src_path = repo_root / "src"
    src_str = str(src_path)
    if src_path.exists() and src_str not in sys.path:
        sys.path.insert(0, src_str)

    if not os.getenv("TABULAR_ANALYSIS_CONFIG_DIR"):
        os.environ["TABULAR_ANALYSIS_CONFIG_DIR"] = str(repo_root / "conf")

    args = _merge_clearml_overrides(list(argv or []))

    from tabular_analysis import cli

    cli.main(args)


if __name__ == "__main__":
    main(sys.argv[1:])
