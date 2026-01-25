#!/usr/bin/env python3
"""ClearML entrypoint wrapper for src/ layout."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_BOOTSTRAP_ENV = "TABULAR_ANALYSIS_BOOTSTRAPPED"


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


def _strip_quotes(text: str) -> str:
    if len(text) >= 2 and ((text[0] == text[-1] == "'") or (text[0] == text[-1] == '"')):
        return text[1:-1]
    return text


def _parse_cli_overrides(argv: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in argv:
        if not item or item.startswith("-") or "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip()
        if key.startswith("+"):
            key = key.lstrip("+")
        if not key:
            continue
        overrides[key] = _strip_quotes(value.strip())
    return overrides


def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    text = value.strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    text = _strip_quotes(value.strip())
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    items = [item.strip() for item in text.split(",") if item.strip()]
    return [_strip_quotes(item) for item in items if item]


def _is_clearml_context() -> bool:
    return any(
        os.getenv(key)
        for key in (
            "CLEARML_TASK_ID",
            "TRAINS_TASK_ID",
            "CLEARML_AGENT_TASK_ID",
            "CLEARML_TASK",
        )
    )


def _resolve_bootstrap_mode(overrides: dict[str, str]) -> str:
    for key in ("run.clearml.env.bootstrap", "run.clearml.bootstrap"):
        value = overrides.get(key)
        if value:
            return value.strip().lower()
    for key in ("TABULAR_ANALYSIS_CLEARML_BOOTSTRAP", "TABULAR_ANALYSIS_BOOTSTRAP"):
        value = os.getenv(key)
        if value:
            return value.strip().lower()
    return "none"


def _resolve_task_name(overrides: dict[str, str]) -> str | None:
    for key in ("task", "task.name"):
        value = overrides.get(key)
        if value:
            name = value.split("/")[-1].strip()
            return name or None
    return None


def _infer_optimize_enabled(overrides: dict[str, str]) -> bool:
    for key in ("infer.mode", "infer/mode"):
        value = overrides.get(key)
        if value and value.strip().lower() == "optimize":
            return True
    return False


def _resolve_uv_extras(overrides: dict[str, str]) -> list[str]:
    extras: list[str] = []
    explicit = overrides.get("run.clearml.env.uv.extras")
    if explicit:
        extras = _parse_list(explicit)
    else:
        task_name = _resolve_task_name(overrides)
        if task_name in {"train_model", "train_ensemble", "infer"}:
            extras = ["models", "tabpfn"]
    if _infer_optimize_enabled(overrides) and "optuna" not in extras:
        extras.append("optuna")
    return extras


def _resolve_uv_settings(overrides: dict[str, str]) -> tuple[str, list[str], bool, bool]:
    venv_dir = overrides.get("run.clearml.env.uv.venv_dir") or ".venv"
    extras = _resolve_uv_extras(overrides)
    all_extras = _parse_bool(overrides.get("run.clearml.env.uv.all_extras"), default=False)
    frozen = _parse_bool(overrides.get("run.clearml.env.uv.frozen"), default=True)
    return (venv_dir, extras, all_extras, frozen)


def _ensure_uv_available() -> None:
    if shutil.which("uv"):
        return
    subprocess.run([sys.executable, "-m", "pip", "install", "uv"], check=True)


def _uv_sync(
    repo_root: Path,
    venv_path: Path,
    *,
    extras: list[str],
    all_extras: bool,
    frozen: bool,
) -> None:
    # Use module invocation so we don't depend on a PATH entry for the uv binary.
    cmd = [sys.executable, "-m", "uv", "sync", "--project", str(repo_root)]
    if frozen:
        cmd.append("--frozen")
    if all_extras:
        cmd.append("--all-extras")
    else:
        for extra in extras:
            cmd.extend(["--extra", extra])
    env = os.environ.copy()
    env["UV_PROJECT_ENVIRONMENT"] = str(venv_path)
    env.setdefault("UV_PYTHON", sys.executable)
    subprocess.run(cmd, check=True, env=env)


def _reexec_with_python(python_path: Path, argv: list[str]) -> None:
    os.environ[_BOOTSTRAP_ENV] = "1"
    os.execv(str(python_path), [str(python_path), *argv])


def _can_import(python_path: Path, module: str) -> bool:
    try:
        subprocess.run(
            [str(python_path), "-c", f"import {module}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return True
    except Exception:
        return False


def _maybe_bootstrap_uv(repo_root: Path, argv: list[str]) -> None:
    if os.getenv(_BOOTSTRAP_ENV):
        return
    overrides = _parse_cli_overrides(argv)
    mode = _resolve_bootstrap_mode(overrides)
    if mode in {"none", "false", "0", "off"}:
        return
    if mode == "auto" and not _is_clearml_context():
        return
    venv_dir, extras, all_extras, frozen = _resolve_uv_settings(overrides)
    lock_path = repo_root / "uv.lock"
    if frozen and not lock_path.exists():
        raise RuntimeError("uv.lock is required for frozen ClearML bootstrap.")
    _ensure_uv_available()
    venv_path = Path(venv_dir)
    if not venv_path.is_absolute():
        venv_path = (repo_root / venv_path).resolve()
    _uv_sync(
        repo_root,
        venv_path,
        extras=extras,
        all_extras=all_extras,
        frozen=frozen,
    )
    python_path = (venv_path / "bin" / "python").resolve()
    if os.name == "nt":
        python_path = (venv_path / "Scripts" / "python.exe").resolve()
    if not python_path.exists():
        raise RuntimeError(f"uv venv python not found: {python_path}")
    if not _can_import(python_path, "hydra"):
        print(
            "[clearml_entrypoint] uv venv missing hydra; falling back to current env bootstrap.",
            file=sys.stderr,
        )
        fallback_env = Path(sys.prefix).resolve()
        _uv_sync(
            repo_root,
            fallback_env,
            extras=extras,
            all_extras=all_extras,
            frozen=frozen,
        )
        os.environ[_BOOTSTRAP_ENV] = "1"
        return
    _reexec_with_python(python_path, [str(Path(__file__)), *argv])


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
    _maybe_bootstrap_uv(repo_root, args)

    from tabular_analysis import cli

    cli.main(args)


if __name__ == "__main__":
    main(sys.argv[1:])
