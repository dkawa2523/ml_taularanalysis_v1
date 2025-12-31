"""Pre-flight checks (doctor).

- ml_platform import/version check
- ClearML connection check (when enabled)
- solution structure check
- UI contract lint for local run_dir
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from . import platform_adapter


_STAGE_TO_PROCESS = {
    "01_dataset_register": "dataset_register",
    "02_preprocess": "preprocess",
    "03_train_model": "train_model",
    "04_infer": "infer",
    "05_leaderboard": "leaderboard",
    "99_pipeline": "pipeline",
}

_REQUIRED_OUT_KEYS = {
    "dataset_register": {"raw_dataset_id", "raw_schema"},
    "preprocess": {"processed_dataset_id", "preprocess_variant", "split_hash", "recipe_hash"},
    "train_model": {
        "processed_dataset_id",
        "split_hash",
        "recipe_hash",
        "train_task_id",
        "model_id",
        "best_score",
        "primary_metric",
    },
    "leaderboard": {"leaderboard_csv", "recommended_train_task_id", "recommended_model_id", "excluded_count"},
    "infer": {"predictions_path", "input_preview_path", "mode", "model_id"},
    "pipeline": {"pipeline_run"},
}


@dataclass
class DoctorReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def ok(self, message: str) -> None:
        self.messages.append(f"[OK] {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        self.messages.append(f"[WARN] {message}")

    def error(self, message: str) -> None:
        self.errors.append(message)
        self.messages.append(f"[ERROR] {message}")

    def emit(self) -> None:
        for line in self.messages:
            print(line)

    def exit_code(self, strict: bool) -> int:
        if self.errors:
            return 1
        if strict and self.warnings:
            return 1
        return 0


def _cfg_select(cfg: Any, dotted_path: str, default: Any | None = None) -> Any:
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
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(key)
        else:
            current = getattr(current, key, None)
    return default if current is None else current


def _resolve_config_dir(explicit: Optional[str]) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"--config-dir does not exist: {path}")
        return path
    env = Path.cwd() / "conf"
    if env.exists():
        return env
    fallback = Path(__file__).resolve().parents[2] / "conf"
    if fallback.exists():
        return fallback
    raise FileNotFoundError("conf/ directory was not found. Run from repository root or set --config-dir.")


def _compose_config(config_dir: Path, overrides: Iterable[str]) -> Any:
    from hydra import compose, initialize_config_dir  # type: ignore

    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        return compose(config_name="config", overrides=list(overrides))


def _check_platform(cfg: Any, report: DoctorReport) -> None:
    try:
        versions = platform_adapter.resolve_version_props(cfg, clearml_enabled=True)
    except Exception as exc:
        report.error(f"ml_platform import/version check failed: {exc}")
        return
    platform_version = versions.get("platform_version", "unknown")
    report.ok(f"ml_platform version: {platform_version}")


def _clearml_project_name(cfg: Any) -> str:
    project_root = _cfg_select(cfg, "run.clearml.project_root", "MFG")
    usecase_id = _cfg_select(cfg, "run.usecase_id", "unknown")
    stage = _cfg_select(cfg, "task.stage", "doctor")
    return f"{project_root}/{usecase_id}/{stage}"


def _check_clearml_queue(queue_name: str, report: DoctorReport) -> None:
    try:
        from clearml import Task  # type: ignore
    except Exception as exc:
        report.error(f"ClearML import failed: {exc}")
        return
    getter = getattr(Task, "get_queue_id", None)
    if not callable(getter):
        report.warn("ClearML Task.get_queue_id not available; queue existence check skipped.")
        return
    try:
        queue_id = getter(queue_name)
    except Exception as exc:
        report.error(f"ClearML queue lookup failed ({queue_name}): {exc}")
        return
    if not queue_id:
        report.error(f"ClearML queue not found: {queue_name}")
        return
    report.ok(f"ClearML queue exists: {queue_name}")


def _check_clearml_clone_task(task_id: str, report: DoctorReport) -> None:
    try:
        from clearml import Task  # type: ignore
    except Exception as exc:
        report.error(f"ClearML import failed: {exc}")
        return
    try:
        Task.get_task(task_id=str(task_id))
    except Exception as exc:
        report.error(f"ClearML clone task not found: {task_id} ({exc})")
        return
    report.ok(f"ClearML clone task exists: {task_id}")


def _check_clearml(cfg: Any, report: DoctorReport) -> None:
    if not platform_adapter.is_clearml_enabled(cfg):
        report.ok("ClearML disabled; skipping connection checks.")
        return
    try:
        from clearml import Task  # type: ignore
    except Exception as exc:
        report.error(f"ClearML import failed: {exc}")
        return

    project_name = _clearml_project_name(cfg)
    task_name = "doctor_check"
    try:
        task = Task.init(
            project_name=project_name,
            task_name=task_name,
            reuse_last_task_id=True,
            auto_connect_frameworks=False,
        )
        task.close()
    except Exception as exc:
        report.error(f"ClearML Task.init failed: {exc}")
        return
    report.ok("ClearML Task.init succeeded.")

    execution = str(_cfg_select(cfg, "run.clearml.execution", "local"))
    queue_name = _cfg_select(cfg, "run.clearml.queue_name")
    clone_from_task_id = _cfg_select(cfg, "run.clearml.clone_from_task_id")

    if execution in ("agent", "clone"):
        if not queue_name:
            report.error("run.clearml.queue_name is required for agent/clone execution.")
        else:
            _check_clearml_queue(str(queue_name), report)

    if execution == "clone":
        if not clone_from_task_id:
            report.error("run.clearml.clone_from_task_id is required for clone execution.")
        else:
            _check_clearml_clone_task(str(clone_from_task_id), report)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _infer_process(run_dir: Path, config_path: Path | None, report: DoctorReport) -> str | None:
    if config_path is not None and config_path.exists():
        try:
            from omegaconf import OmegaConf  # type: ignore

            cfg = OmegaConf.load(config_path)
            task_name = OmegaConf.select(cfg, "task.name")
            if task_name:
                return str(task_name)
            stage = OmegaConf.select(cfg, "task.stage")
            if stage and str(stage) in _STAGE_TO_PROCESS:
                return _STAGE_TO_PROCESS[str(stage)]
        except Exception as exc:
            report.warn(f"Failed to parse config_resolved.yaml: {exc}")
    stage_name = run_dir.name
    return _STAGE_TO_PROCESS.get(stage_name)


def _lint_run_dir(run_dir: Path, report: DoctorReport) -> None:
    if not run_dir.exists():
        report.error(f"lint-dir does not exist: {run_dir}")
        return
    if not run_dir.is_dir():
        report.error(f"lint-dir is not a directory: {run_dir}")
        return

    config_path = run_dir / "config_resolved.yaml"
    out_path = run_dir / "out.json"
    manifest_path = run_dir / "manifest.json"

    for path in (config_path, out_path, manifest_path):
        if not path.exists():
            report.error(f"Missing artifact: {path}")
        else:
            report.ok(f"Found artifact: {path.name}")

    if not out_path.exists():
        return

    try:
        out = _load_json(out_path)
    except Exception as exc:
        report.error(f"Failed to read out.json: {exc}")
        return
    if not isinstance(out, dict):
        report.error("out.json must contain a JSON object.")
        return

    process = _infer_process(run_dir, config_path if config_path.exists() else None, report)
    if not process:
        report.warn("Could not infer process for contract lint.")
        return

    required = _REQUIRED_OUT_KEYS.get(process)
    if not required:
        report.warn(f"No required out.json keys defined for process: {process}")
        return
    missing = sorted([key for key in required if key not in out])
    if missing:
        report.error(f"out.json missing required keys for {process}: {missing}")
    else:
        report.ok(f"out.json required keys satisfied for {process}.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pre-flight checks for the solution environment.")
    parser.add_argument(
        "--lint-dir",
        type=str,
        default=None,
        help="Path to a run_dir (e.g., outputs/<...>/03_train_model) for UI contract lint.",
    )
    parser.add_argument(
        "--config-dir",
        type=str,
        default=None,
        help="Hydra config directory (defaults to ./conf).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors.",
    )
    args, overrides = parser.parse_known_args()

    report = DoctorReport()

    cfg = None
    try:
        config_dir = _resolve_config_dir(args.config_dir)
        report.ok(f"Found conf directory: {config_dir}")
        cfg = _compose_config(config_dir, overrides)
        report.ok("Config composed successfully.")
    except Exception as exc:
        report.error(f"Config resolution failed: {exc}")

    if cfg is not None:
        _check_platform(cfg, report)
        _check_clearml(cfg, report)

    if args.lint_dir:
        _lint_run_dir(Path(args.lint_dir).expanduser().resolve(), report)

    report.emit()
    return report.exit_code(strict=bool(args.strict))


if __name__ == "__main__":
    raise SystemExit(main())
