"""Local orchestrator for one-shot regression training without ClearML agent."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Mapping, Optional


def _resolve_repo_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for base in candidates:
        for parent in [base, *base.parents]:
            if (parent / "conf").exists():
                return parent
    return Path.cwd()


def _resolve_config_dir(repo_root: Path) -> Path:
    config_dir = repo_root / "conf"
    if not config_dir.exists():
        raise FileNotFoundError("conf/ directory was not found.")
    return config_dir


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _sanitize_component(value: str) -> str:
    cleaned = []
    for ch in value:
        if ch.isalnum() or ch in ("-", "_"):
            cleaned.append(ch)
        else:
            cleaned.append("_")
    result = "".join(cleaned).strip("_")
    return result or "item"


def _needs_quote(text: str) -> bool:
    if not text:
        return True
    for ch in text:
        if ch.isspace() or ch in "[]{}(),=":
            return True
    return False


def _quote_string(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _format_list(values: Iterable[Any]) -> str:
    items = []
    for item in values:
        if item is None:
            continue
        if isinstance(item, bool):
            items.append("true" if item else "false")
        elif isinstance(item, (int, float)):
            items.append(str(item))
        else:
            items.append(_quote_string(str(item)))
    return "[" + ",".join(items) + "]"


def _format_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        return _format_list(value)
    text = str(value)
    if _needs_quote(text):
        return _quote_string(text)
    return text


def _overrides_to_args(overrides: Mapping[str, Any]) -> list[str]:
    args: list[str] = []
    for key, value in overrides.items():
        formatted = _format_value(value)
        if formatted is None:
            continue
        args.append(f"{key}={formatted}")
    return args


def _run_cli_task(args: list[str], *, cwd: Path, config_dir: Path, step_name: str) -> None:
    cmd = [sys.executable, "-m", "tabular_analysis.cli", *args]
    env = os.environ.copy()
    env.setdefault("TABULAR_ANALYSIS_CONFIG_DIR", str(config_dir))
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"{step_name} failed (exit={proc.returncode})\n$ {' '.join(cmd)}\n\n{proc.stdout}"
        )


def _find_out_json(run_root: Path, *, exclude: set[Path] | None = None) -> Path:
    if not run_root.exists():
        raise FileNotFoundError(f"run.output_dir not found: {run_root}")
    candidates: list[Path] = []
    exclude = exclude or set()
    for path in run_root.rglob("out.json"):
        resolved = path.resolve()
        if resolved in exclude:
            continue
        candidates.append(path)
    if not candidates:
        raise FileNotFoundError(f"out.json not found under run.output_dir: {run_root}")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _load_out_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_list(values: Any) -> list[str]:
    if values is None:
        return []
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_list(values):
        return [str(v) for v in values if v is not None]
    if isinstance(values, (list, tuple, set)):
        return [str(v) for v in values if v is not None]
    return [str(values)]


def _load_model_set_payload(path: Path) -> Any:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception as exc:
        raise RuntimeError("OmegaConf is required to load model_set configs.") from exc
    try:
        cfg = OmegaConf.load(path)
    except Exception as exc:
        raise ValueError(f"Failed to load model_set config: {path}") from exc
    try:
        return OmegaConf.to_container(cfg, resolve=False)
    except Exception:
        return cfg


def _normalize_model_set_name(value: str) -> str:
    name = value.strip()
    if not name:
        return ""
    if Path(name).name != name:
        raise ValueError(f"Invalid model_set name: {value}")
    return name


def _resolve_model_set_variants(repo_root: Path, model_set: str, *, task_type: str) -> list[str]:
    name = _normalize_model_set_name(model_set)
    if not name:
        return []
    path = repo_root / "conf" / "pipeline" / "model_sets" / f"{name}.yaml"
    if not path.exists():
        raise ValueError(f"model_set '{name}' not found: {path}")
    payload = _load_model_set_payload(path)
    variants: list[str] = []
    if isinstance(payload, Mapping):
        variants = _to_list(payload.get("variants"))
        auto = bool(payload.get("auto"))
        payload_task_type = _normalize_str(payload.get("task_type")) or task_type
        if auto and not payload_task_type:
            raise ValueError(f"model_set '{name}' requires task_type when auto=true.")
        if auto or (payload_task_type and not variants):
            from ..registry.models import list_model_variants

            variants = list_model_variants(task_type=payload_task_type)
        exclude = set(_to_list(payload.get("exclude")))
        if exclude:
            variants = [item for item in variants if item not in exclude]
    elif isinstance(payload, list):
        variants = _to_list(payload)
    else:
        raise ValueError(f"model_set config must be mapping or list: {path}")
    deduped: list[str] = []
    seen: set[str] = set()
    for item in variants:
        name = _normalize_str(item)
        if not name or name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return deduped


def _default_output_root(repo_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return repo_root / "outputs" / f"local_orchestrator_{stamp}"


def _resolve_output_root(repo_root: Path, output_root: str | None) -> Path:
    root = Path(output_root).expanduser() if output_root else _default_output_root(repo_root)
    if not root.is_absolute():
        root = repo_root / root
    return root.resolve()


def _build_step_root(run_root: Path, step_name: str) -> Path:
    return run_root / _sanitize_component(step_name)


def _run_step(
    *,
    task_name: str,
    step_name: str,
    run_root: Path,
    overrides: Mapping[str, Any],
    cwd: Path,
    config_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    run_root.mkdir(parents=True, exist_ok=True)
    existing = {path.resolve() for path in run_root.rglob("out.json")}
    args = [f"task={task_name}", *_overrides_to_args(overrides)]
    _run_cli_task(args, cwd=cwd, config_dir=config_dir, step_name=step_name)
    out_path = _find_out_json(run_root, exclude=existing)
    return out_path, _load_out_json(out_path)


def _build_clearml_overrides(enabled: bool, project_root: str | None) -> dict[str, Any]:
    execution = "logging" if enabled else "local"
    overrides: dict[str, Any] = {
        "run.clearml.enabled": enabled,
        "run.clearml.execution": execution,
    }
    if project_root:
        overrides["run.clearml.project_root"] = project_root
    return overrides


def _train_regression(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo_root()
    config_dir = _resolve_config_dir(repo_root)
    run_root = _resolve_output_root(repo_root, args.output_root)
    run_root.mkdir(parents=True, exist_ok=True)

    preprocess_variant = _normalize_str(args.preprocess)
    model_set = _normalize_str(args.model_set)
    if not preprocess_variant:
        raise ValueError("--preprocess is required.")
    if not model_set:
        raise ValueError("--model-set is required.")

    dataset_path = _normalize_str(args.dataset_path)
    raw_dataset_id = _normalize_str(args.raw_dataset_id)
    target_column = _normalize_str(args.target_column)
    if not target_column:
        raise ValueError("--target-column is required.")
    if not raw_dataset_id and not dataset_path:
        raise ValueError("Either --dataset-path or --raw-dataset-id is required.")
    if raw_dataset_id and raw_dataset_id.startswith("local:") and not dataset_path:
        raise ValueError("--dataset-path is required when --raw-dataset-id is local:<hash>.")

    clearml_enabled = bool(args.clearml)
    project_root = _normalize_str(args.project_root)
    clearml_overrides = _build_clearml_overrides(clearml_enabled, project_root)

    if dataset_path:
        dataset_path = str(Path(dataset_path).expanduser().resolve())

    if not raw_dataset_id:
        step_root = _build_step_root(run_root, "dataset_register")
        overrides: dict[str, Any] = {
            "run.output_dir": str(step_root),
            "data.dataset_path": dataset_path,
            "data.target_column": target_column,
        }
        overrides.update(clearml_overrides)
        out_path, out = _run_step(
            task_name="dataset_register",
            step_name="dataset_register",
            run_root=step_root,
            overrides=overrides,
            cwd=repo_root,
            config_dir=config_dir,
        )
        raw_dataset_id = _normalize_str(out.get("raw_dataset_id"))
        if not raw_dataset_id:
            raise RuntimeError(f"dataset_register out.json missing raw_dataset_id: {out_path}")

    preprocess_step = f"preprocess__{preprocess_variant}"
    preprocess_root = _build_step_root(run_root, preprocess_step)
    preprocess_overrides: dict[str, Any] = {
        "group/preprocess": preprocess_variant,
        "run.output_dir": str(preprocess_root),
        "data.target_column": target_column,
        "data.raw_dataset_id": raw_dataset_id,
    }
    if dataset_path and raw_dataset_id and raw_dataset_id.startswith("local:"):
        preprocess_overrides["data.dataset_path"] = dataset_path
    preprocess_overrides.update(clearml_overrides)
    preprocess_out_path, preprocess_out = _run_step(
        task_name="preprocess",
        step_name="preprocess",
        run_root=preprocess_root,
        overrides=preprocess_overrides,
        cwd=repo_root,
        config_dir=config_dir,
    )
    preprocess_run_dir = preprocess_out_path.parent
    processed_dataset_id = _normalize_str(preprocess_out.get("processed_dataset_id"))

    model_variants = _resolve_model_set_variants(repo_root, model_set, task_type="regression")
    if not model_variants:
        raise RuntimeError(f"model_set '{model_set}' resolved to no model variants.")

    train_task_ids: list[str] = []
    train_run_dirs: list[str] = []
    for model_variant in model_variants:
        step_name = f"train__{preprocess_variant}__{model_variant}"
        train_root = _build_step_root(run_root, step_name)
        train_overrides: dict[str, Any] = {
            "group/model": model_variant,
            "train.inputs.preprocess_run_dir": str(preprocess_run_dir),
            "run.output_dir": str(train_root),
            "data.target_column": target_column,
            "data.raw_dataset_id": raw_dataset_id,
        }
        if processed_dataset_id:
            train_overrides["data.processed_dataset_id"] = processed_dataset_id
        train_overrides.update(clearml_overrides)
        train_out_path, train_out = _run_step(
            task_name="train_model",
            step_name=f"train_model:{model_variant}",
            run_root=train_root,
            overrides=train_overrides,
            cwd=repo_root,
            config_dir=config_dir,
        )
        train_run_dirs.append(str(train_out_path.parent))
        train_task_id = _normalize_str(train_out.get("train_task_id"))
        if train_task_id:
            train_task_ids.append(train_task_id)

    leaderboard_root = _build_step_root(run_root, "leaderboard")
    leaderboard_overrides: dict[str, Any] = {"run.output_dir": str(leaderboard_root)}
    if clearml_enabled:
        if not train_task_ids:
            raise RuntimeError("No train_task_id found in train_model outputs (ClearML enabled).")
        leaderboard_overrides["leaderboard.train_task_ids"] = train_task_ids
    else:
        leaderboard_overrides["leaderboard.train_run_dirs"] = train_run_dirs
    leaderboard_overrides.update(clearml_overrides)
    leaderboard_out_path, leaderboard_out = _run_step(
        task_name="leaderboard",
        step_name="leaderboard",
        run_root=leaderboard_root,
        overrides=leaderboard_overrides,
        cwd=repo_root,
        config_dir=config_dir,
    )

    recommended_model_id = _normalize_str(leaderboard_out.get("recommended_model_id"))
    recommended_train_task_id = _normalize_str(leaderboard_out.get("recommended_train_task_id"))

    summary = {
        "run_root": str(run_root),
        "raw_dataset_id": raw_dataset_id,
        "processed_dataset_id": processed_dataset_id,
        "train_task_ids": train_task_ids,
        "train_run_dirs": train_run_dirs,
        "recommended_model_id": recommended_model_id,
        "recommended_train_task_id": recommended_train_task_id,
        "leaderboard_out": str(leaderboard_out_path),
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run dataset_register/preprocess/train/leaderboard locally in one command."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_regression = subparsers.add_parser(
        "train_regression",
        help="Run regression pipeline locally while creating ClearML tasks per step.",
    )
    train_regression.add_argument("--dataset-path", type=str, default=None, help="Path to CSV/Parquet.")
    train_regression.add_argument(
        "--raw-dataset-id",
        type=str,
        default=None,
        help="ClearML Dataset ID or local:<hash> to skip dataset_register.",
    )
    train_regression.add_argument("--target-column", type=str, required=True, help="Target column name.")
    train_regression.add_argument(
        "--preprocess", type=str, required=True, help="Preprocess variant (group/preprocess)."
    )
    train_regression.add_argument(
        "--model-set",
        type=str,
        required=True,
        help="Model set name (conf/pipeline/model_sets/*.yaml).",
    )
    train_regression.add_argument(
        "--clearml",
        action="store_true",
        help="Enable ClearML logging (creates individual tasks per step).",
    )
    train_regression.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="ClearML project root (run.clearml.project_root).",
    )
    train_regression.add_argument(
        "--output-root",
        type=str,
        default=None,
        help="Base output directory for the orchestrator run.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "train_regression":
        return _train_regression(args)
    parser.error("Unknown command.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
