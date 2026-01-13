"""Pre-flight checks (doctor).

- ml_platform import/version check
- ClearML connection check (when enabled)
- solution structure check
- UI contract lint for local run outputs
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from . import platform_adapter
from .ops import ui_contract_lint
from .ops.clearml_identity import build_project_name, resolve_clearml_identity


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


def _check_platform(cfg: Any | None, report: DoctorReport) -> None:
    base_cfg = cfg
    if base_cfg is None:
        base_cfg = {"run": {"schema_version": "unknown"}}
    try:
        versions = platform_adapter.resolve_version_props(base_cfg, clearml_enabled=True)
    except Exception as exc:
        report.error(f"ml_platform import/version check failed: {exc}")
        return
    platform_version = versions.get("platform_version", "unknown")
    report.ok(f"ml_platform version: {platform_version}")


def _clearml_project_name(cfg: Any) -> str:
    stage = _cfg_select(cfg, "task.stage", "doctor")
    identity = resolve_clearml_identity(cfg)
    return build_project_name(cfg, stage=stage, usecase_id=identity.usecase_id)


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
    code_ref_mode = platform_adapter.resolve_clearml_code_ref_mode(cfg)

    if execution in ("agent", "clone", "pipeline_controller", "pipeline_controller_local"):
        if code_ref_mode == "none":
            report.error("run.clearml.code_ref.mode=none is not allowed for agent/pipeline execution.")

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


def _merge_lint_report(report: DoctorReport, lint_report: ui_contract_lint.LintReport, mode: str) -> None:
    for message in lint_report.oks:
        report.ok(message)
    for message in lint_report.warnings:
        report.warn(message)
    if mode == "fail":
        for message in lint_report.errors:
            report.error(message)
    else:
        for message in lint_report.errors:
            report.warn(message)


def _check_conf_dir(config_dir: Optional[str], report: DoctorReport) -> Path | None:
    try:
        resolved = _resolve_config_dir(config_dir)
    except Exception as exc:
        report.error(f"conf directory check failed: {exc}")
        return None
    report.ok(f"Found conf directory: {resolved}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pre-flight checks for the solution environment.")
    parser.add_argument(
        "--lint-dir",
        type=str,
        default=None,
        help="Path to a run_dir (e.g., outputs/<...>/03_train_model) for UI contract lint.",
    )
    parser.add_argument(
        "--lint-run",
        type=str,
        default=None,
        help="Path to a run.output_dir containing stage outputs for contract lint.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["warn", "fail"],
        default="warn",
        help="UI contract lint mode (warn: report only, fail: exit non-zero on violations).",
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

    config_dir = _check_conf_dir(args.config_dir, report)
    cfg = None
    if config_dir is not None:
        try:
            cfg = _compose_config(config_dir, overrides)
            report.ok("Config composed successfully.")
        except Exception as exc:
            report.error(f"Config resolution failed: {exc}")

    _check_platform(cfg, report)

    if cfg is not None:
        _check_clearml(cfg, report)

    if args.lint_dir:
        lint_report = ui_contract_lint.lint_run_dir(Path(args.lint_dir).expanduser().resolve())
        _merge_lint_report(report, lint_report, args.mode)
    if args.lint_run:
        lint_report = ui_contract_lint.lint_run_root(Path(args.lint_run).expanduser().resolve())
        _merge_lint_report(report, lint_report, args.mode)

    report.emit()
    return report.exit_code(strict=bool(args.strict))


if __name__ == "__main__":
    raise SystemExit(main())
