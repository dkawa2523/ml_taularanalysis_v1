"""UI contract lint for local run outputs."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


STAGE_TO_PROCESS = {
    "01_dataset_register": "dataset_register",
    "02_preprocess": "preprocess",
    "03_train_model": "train_model",
    "04_train_ensemble": "train_ensemble",
    "04_infer": "infer",
    "05_leaderboard": "leaderboard",
    "99_pipeline": "pipeline",
}

REQUIRED_OUT_KEYS = {
    "dataset_register": {"raw_dataset_id"},
    "preprocess": {"processed_dataset_id", "split_hash", "recipe_hash"},
    "train_model": {"model_id", "primary_metric", "best_score", "task_type"},
    "train_ensemble": {"model_id", "primary_metric", "best_score", "task_type"},
    "leaderboard": {"leaderboard_csv", "recommended_model_id"},
    "infer": {"predictions_path"},
    "pipeline": {"pipeline_run"},
}

REQUIRED_ARTIFACTS = ("config_resolved.yaml", "out.json", "manifest.json")
MANIFEST_REQUIRED_KEYS = (
    "schema_version",
    "code_version",
    "platform_version",
    "process",
    "created_at",
    "inputs",
    "outputs",
)


@dataclass
class LintReport:
    oks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def ok(self, message: str) -> None:
        self.oks.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def merge(self, other: "LintReport") -> None:
        self.oks.extend(other.oks)
        self.warnings.extend(other.warnings)
        self.errors.extend(other.errors)

    def emit(self) -> None:
        for message in self.oks:
            print(f"[OK] {message}")
        for message in self.warnings:
            print(f"[WARN] {message}")
        for message in self.errors:
            print(f"[ERROR] {message}")

    def exit_code(self, mode: str) -> int:
        if mode == "fail" and self.errors:
            return 1
        return 0


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_object(path: Path, label: str, report: LintReport) -> dict[str, Any] | None:
    try:
        payload = _load_json(path)
    except Exception as exc:
        report.error(f"Failed to read {label}: {exc}")
        return None
    if not isinstance(payload, dict):
        report.error(f"{label} must contain a JSON object.")
        return None
    return payload


def _manifest_process_name(manifest: dict[str, Any]) -> str | None:
    process = manifest.get("process")
    if isinstance(process, dict):
        process = process.get("name")
    if not process:
        process = manifest.get("process.name")
    if process:
        return str(process)
    return None


def _manifest_config_hash(manifest: dict[str, Any]) -> str | None:
    candidates = ("config_hash", "config_digest", "config_resolved_hash")
    for key in candidates:
        value = manifest.get(key)
        if value:
            return str(value)
    hashes = manifest.get("hashes")
    if isinstance(hashes, dict):
        for key in candidates:
            value = hashes.get(key)
            if value:
                return str(value)
    return None


def _infer_process(run_dir: Path, config_path: Path | None, report: LintReport) -> str | None:
    if config_path is not None and config_path.exists():
        try:
            from omegaconf import OmegaConf  # type: ignore

            cfg = OmegaConf.load(config_path)
            task_name = OmegaConf.select(cfg, "task.name")
            if task_name:
                return str(task_name)
            stage = OmegaConf.select(cfg, "task.stage")
            if stage and str(stage) in STAGE_TO_PROCESS:
                return STAGE_TO_PROCESS[str(stage)]
        except Exception as exc:
            report.warn(f"Failed to parse config_resolved.yaml: {exc}")
    stage_name = run_dir.name
    return STAGE_TO_PROCESS.get(stage_name)


def _lint_manifest(
    manifest_path: Path,
    report: LintReport,
    *,
    expected_process: str | None,
) -> dict[str, Any] | None:
    manifest = _load_json_object(manifest_path, "manifest.json", report)
    if manifest is None:
        return None

    for key in MANIFEST_REQUIRED_KEYS:
        value = manifest.get(key)
        if value is None or value == "":
            report.error(f"manifest.json missing {key}.")

    inputs = manifest.get("inputs")
    if inputs is None:
        report.error("manifest.json missing inputs.")
    elif not isinstance(inputs, dict):
        report.error("manifest.json inputs must be a JSON object.")

    outputs = manifest.get("outputs")
    if outputs is None:
        report.error("manifest.json missing outputs.")
    elif not isinstance(outputs, dict):
        report.error("manifest.json outputs must be a JSON object.")

    config_hash = _manifest_config_hash(manifest)
    if not config_hash:
        report.error("manifest.json missing config_hash (or equivalent tracking key).")

    process_name = _manifest_process_name(manifest)
    if not process_name:
        report.error("manifest.json missing process name (process or process.name).")
    elif expected_process and process_name != expected_process:
        report.error(f"manifest.json process mismatch: {process_name} != {expected_process}")

    return manifest


def _lint_out_json(out_path: Path, report: LintReport, *, process: str | None) -> None:
    out = _load_json_object(out_path, "out.json", report)
    if out is None:
        return
    if not process:
        report.warn("Could not infer process for out.json checks.")
        return
    required = REQUIRED_OUT_KEYS.get(process)
    if not required:
        report.warn(f"No required out.json keys defined for process: {process}")
        return
    missing = sorted([key for key in required if key not in out])
    if missing:
        report.error(f"out.json missing required keys for {process}: {missing}")
    else:
        report.ok(f"out.json required keys satisfied for {process}.")


def _lint_optional_artifacts(run_dir: Path, report: LintReport) -> None:
    for path in run_dir.iterdir():
        if not path.is_file():
            continue
        if path.name in REQUIRED_ARTIFACTS:
            continue
        suffix = path.suffix.lower()
        if suffix == ".json":
            try:
                _load_json(path)
            except Exception as exc:
                report.error(f"Invalid JSON artifact ({path.name}): {exc}")
        elif suffix == ".md":
            try:
                content = path.read_text(encoding="utf-8").strip()
            except Exception as exc:
                report.error(f"Failed to read markdown artifact ({path.name}): {exc}")
                continue
            if not content:
                report.error(f"Markdown artifact is empty: {path.name}")


def lint_run_dir(run_dir: Path) -> LintReport:
    report = LintReport()
    if not run_dir.exists():
        report.error(f"lint-dir does not exist: {run_dir}")
        return report
    if not run_dir.is_dir():
        report.error(f"lint-dir is not a directory: {run_dir}")
        return report

    config_path = run_dir / "config_resolved.yaml"
    out_path = run_dir / "out.json"
    manifest_path = run_dir / "manifest.json"

    for name in REQUIRED_ARTIFACTS:
        path = run_dir / name
        if not path.exists():
            report.error(f"Missing artifact: {path}")
        else:
            report.ok(f"Found artifact: {path.name}")

    expected_process = _infer_process(run_dir, config_path if config_path.exists() else None, report)
    manifest = None
    if manifest_path.exists():
        manifest = _lint_manifest(manifest_path, report, expected_process=expected_process)
    if manifest:
        manifest_process = _manifest_process_name(manifest)
        if manifest_process:
            expected_process = manifest_process

    if out_path.exists():
        _lint_out_json(out_path, report, process=expected_process)

    _lint_optional_artifacts(run_dir, report)
    return report


def lint_run_root(run_root: Path) -> LintReport:
    report = LintReport()
    if not run_root.exists():
        report.error(f"lint-run does not exist: {run_root}")
        return report
    if not run_root.is_dir():
        report.error(f"lint-run is not a directory: {run_root}")
        return report

    stage_dirs: list[Path] = []
    if run_root.name in STAGE_TO_PROCESS:
        stage_dirs.append(run_root)
    else:
        for path in run_root.rglob("*"):
            if not path.is_dir():
                continue
            if path.name in STAGE_TO_PROCESS:
                stage_dirs.append(path)

    if not stage_dirs:
        report.error(f"No stage output directories found under: {run_root}")
        return report

    for stage_dir in sorted(set(stage_dirs), key=lambda path: str(path)):
        report.merge(lint_run_dir(stage_dir))
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint UI contract artifacts in run outputs.")
    parser.add_argument(
        "--run-dir",
        type=str,
        default=None,
        help="Path to a run_dir (e.g., outputs/<...>/03_train_model) to lint.",
    )
    parser.add_argument(
        "--run-root",
        type=str,
        default=None,
        help="Path to a run.output_dir containing stage outputs to lint.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["warn", "fail"],
        default="warn",
        help="warn: report violations without failing; fail: exit non-zero on violations.",
    )
    args = parser.parse_args()
    if not args.run_dir and not args.run_root:
        parser.error("Specify --run-dir and/or --run-root.")
    return args


def main() -> int:
    args = _parse_args()
    report = LintReport()
    if args.run_dir:
        report.merge(lint_run_dir(Path(args.run_dir).expanduser().resolve()))
    if args.run_root:
        report.merge(lint_run_root(Path(args.run_root).expanduser().resolve()))
    report.emit()
    return report.exit_code(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
