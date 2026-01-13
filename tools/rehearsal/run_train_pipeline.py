#!/usr/bin/env python3
"""Rehearsal runner for dataset_register + pipeline (local or agent)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tabular_analysis import platform_adapter
from tabular_analysis.registry.models import list_model_variants

_DEFAULT_MODELS = {
    "regression": ["ridge", "elasticnet"],
    "classification": ["logistic_regression", "random_forest"],
}

_SMALL_MODELS = {
    "regression": ["ridge", "lasso", "elasticnet"],
    "classification": ["logistic_regression", "random_forest"],
}

_REQUIRED_PROCESSES = [
    "pipeline",
    "preprocess",
    "train_model",
    "train_ensemble",
    "leaderboard",
]

_EXPECTED_HPARAM_SECTIONS = {
    "inputs",
    "dataset",
    "preprocess",
    "model",
    "eval",
    "pipeline",
    "clearml",
}

_REQUIRED_DATASET_FILES = (
    "splits.json",
    "schema.json",
    "recipe.json",
    "preprocess_bundle.joblib",
    "meta.json",
)

_REQUIRED_META_KEYS = (
    "processed_dataset_hash",
    "recipe_hash",
    "split_hash",
    "schema_hash",
    "bundle_hash",
    "preprocess_variant",
    "store_features",
)

_PROCESS_ORDER = [
    "dataset_register",
    "preprocess",
    "train_model",
    "train_ensemble",
    "leaderboard",
    "infer",
    "pipeline",
]


def _format_cmd(cmd: Sequence[str]) -> str:
    return " ".join(_quote_arg(part) for part in cmd)


def _quote_arg(value: object) -> str:
    text = str(value)
    if not text:
        return "''"
    if re.search(r"[\s\[\]{}(),=]", text):
        return "'" + text.replace("'", "'\\''") + "'"
    return text


def _run(
    cmd: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str],
    log_path: Path | None = None,
) -> str:
    line = f"$ {_format_cmd(cmd)}"
    print(line)
    proc = subprocess.run(
        list(cmd),
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    stdout = proc.stdout or ""
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(stdout, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed (exit={proc.returncode})\n{line}\n\n{stdout}")
    return stdout


def _utc_stamp(now: dt.datetime | None = None) -> tuple[str, str]:
    now_value = now or dt.datetime.now(dt.timezone.utc)
    stamp = now_value.strftime("%Y%m%d_%H%M%S")
    iso = now_value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return stamp, iso


def _sanitize_identifier(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "-", value)
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    return sanitized.strip("-_") or "unknown"


def _normalize_task_type(value: str) -> str:
    text = str(value or "").strip().lower()
    if text in ("classification", "clf", "class"):
        return "classification"
    return "regression"


def _split_csv(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def _flatten(values: Iterable[Iterable[str] | str] | None) -> list[str]:
    items: list[str] = []
    if not values:
        return items
    for group in values:
        if isinstance(group, str):
            items.extend(_split_csv(group))
            continue
        for item in group:
            items.extend(_split_csv(str(item)))
    return items


def _resolve_preprocess(values: Iterable[Iterable[str] | str] | None) -> list[str]:
    items = _flatten(values)
    return items if items else ["stdscaler_ohe"]


def _resolve_models(task_type: str, value: str | None) -> list[str]:
    if value is None:
        return list(_DEFAULT_MODELS.get(task_type, []))
    text = str(value).strip().lower()
    if not text:
        return list(_DEFAULT_MODELS.get(task_type, []))
    if text == "small":
        return list(_SMALL_MODELS.get(task_type, []))
    if text == "all":
        variants = list_model_variants(task_type=task_type)
        if not variants:
            raise RuntimeError(f"No model variants found for task_type={task_type}.")
        return variants
    items = _split_csv(value)
    return items if items else list(_DEFAULT_MODELS.get(task_type, []))


def _json_arg(value: object) -> str:
    return json.dumps(value, separators=(",", ":"))


def _make_toy_dataset(path: Path, *, task_type: str) -> None:
    try:
        import numpy as np  # type: ignore
        import pandas as pd  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError(
            "pandas/numpy are required for rehearsal runs. Install requirements/base.txt first."
        ) from exc

    rng = np.random.default_rng(42)
    n = 240
    df = pd.DataFrame(
        {
            "num1": rng.normal(0, 1, size=n),
            "num2": rng.normal(3, 2, size=n),
            "cat": rng.choice(["a", "b", "c"], size=n),
        }
    )
    if task_type == "classification":
        logits = (
            0.6 * df["num1"].to_numpy()
            - 0.4 * df["num2"].to_numpy()
            + (df["cat"].to_numpy() == "b").astype(float) * 0.8
        )
        proba = 1.0 / (1.0 + np.exp(-logits))
        df["target"] = (proba > 0.5).astype(int)
    else:
        noise = rng.normal(0, 0.3, size=n)
        df["target"] = (
            0.4 * df["num1"].to_numpy()
            - 0.2 * df["num2"].to_numpy()
            + (df["cat"].to_numpy() == "b").astype(float) * 0.5
            + noise
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _summarize_error(exc: Exception) -> str:
    text = str(exc).strip().replace("\r\n", "\n")
    if len(text) > 2000:
        return text[:2000] + "..."
    return text


def _collect_ids(values: Iterable[str | None]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _process_from_tags(tags: Iterable[str]) -> str:
    for tag in tags:
        if tag.startswith("process:"):
            return tag.split(":", 1)[1]
    return "unknown"


def _list_clearml_tasks(usecase_id: str) -> tuple[list[object] | None, str | None]:
    tags = [f"usecase:{usecase_id}"]
    try:
        tasks = platform_adapter.list_clearml_tasks_by_tags(
            tags, allow_archived=True, order_by=["-last_update"]
        )
    except platform_adapter.PlatformAdapterError as exc:
        return None, str(exc)
    return list(tasks), None


def _summarize_clearml_tasks(tasks: Iterable[object]) -> dict[str, list[dict[str, str | None]]]:
    summary: dict[str, list[dict[str, str | None]]] = {}
    for task in tasks:
        tags = platform_adapter.clearml_task_tags(task)
        process = _process_from_tags(tags)
        summary.setdefault(process, []).append(
            {
                "task_id": platform_adapter.clearml_task_id(task),
                "status": platform_adapter.clearml_task_status_from_obj(task),
                "name": getattr(task, "name", None) or getattr(task, "task_name", None),
            }
        )
    return summary


def _print_clearml_tasks(usecase_id: str, tasks: Iterable[object]) -> None:
    grouped: dict[str, list[object]] = {}
    for task in tasks:
        tags = platform_adapter.clearml_task_tags(task)
        process = _process_from_tags(tags)
        grouped.setdefault(process, []).append(task)

    print(f"ClearML tasks (usecase_id={usecase_id}):")
    ordered = [*[_p for _p in _PROCESS_ORDER if _p in grouped], *sorted(set(grouped) - set(_PROCESS_ORDER))]
    for process in ordered:
        task_list = grouped.get(process, [])
        if not task_list:
            continue
        print(f"- {process}")
        for task in task_list:
            task_id = platform_adapter.clearml_task_id(task) or "unknown"
            status = platform_adapter.clearml_task_status_from_obj(task) or "unknown"
            name = getattr(task, "name", None) or getattr(task, "task_name", None) or ""
            print(f"  {status:10} {task_id} {name}")
        if process == "pipeline":
            for task in task_list:
                status = platform_adapter.clearml_task_status_from_obj(task) or ""
                if "failed" not in status.lower():
                    continue
                script = platform_adapter.clearml_task_script(task)
                print("  pipeline failed: script pin")
                print(f"    repository: {script.get('repository') or 'none'}")
                print(f"    branch: {script.get('branch') or 'none'}")
                print(f"    entry_point: {script.get('entry_point') or 'none'}")
                print(f"    version_num: {script.get('version_num') or 'none'}")


def _resolve_repo_root(value: str) -> Path:
    repo = Path(value).expanduser().resolve()
    if not (repo / "conf").exists():
        raise FileNotFoundError(f"conf/ not found under repo root: {repo}")
    return repo


def _eval_overrides(task_type: str) -> list[str]:
    overrides = [f"eval.task_type={task_type}"]
    if task_type == "classification":
        overrides.append("eval.primary_metric=f1")
    return overrides


def _normalize_execution(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if text in ("local", "logging", "agent"):
        return text
    if not text:
        return "local"
    raise ValueError(f"Unsupported execution mode: {value}")


def _resolve_config_dir(repo_root: Path, override: str | None) -> Path:
    if override:
        path = Path(override).expanduser()
        return path if path.is_absolute() else repo_root / path
    env_value = os.getenv("TABULAR_ANALYSIS_CONFIG_DIR")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return repo_root / "conf"


def _load_clearml_layout(config_dir: Path) -> dict[str, Any]:
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        return {}
    layout_path = config_dir / "clearml" / "project_layout.yaml"
    run_path = config_dir / "run" / "base.yaml"
    layout: dict[str, Any] = {}
    run_cfg: dict[str, Any] = {}
    if layout_path.exists():
        try:
            layout = OmegaConf.to_container(OmegaConf.load(layout_path), resolve=True) or {}
        except Exception:
            layout = {}
    if run_path.exists():
        try:
            run_cfg = OmegaConf.to_container(OmegaConf.load(run_path), resolve=True) or {}
        except Exception:
            run_cfg = {}
    clearml_cfg = run_cfg.get("clearml") if isinstance(run_cfg, Mapping) else None
    project_root = None
    if isinstance(clearml_cfg, Mapping):
        project_root = clearml_cfg.get("project_root")
    group_map = {}
    if isinstance(layout, Mapping):
        group_map = layout.get("group_map") if isinstance(layout.get("group_map"), Mapping) else {}
    return {
        "project_root": project_root,
        "solution_root": layout.get("solution_root") if isinstance(layout, Mapping) else None,
        "separator": layout.get("separator") if isinstance(layout, Mapping) else None,
        "group_map": group_map,
    }


def _build_project_prefix(
    *, project_root: str | None, solution_root: str | None, usecase_id: str, separator: str | None
) -> str:
    sep = separator or "/"
    parts = [str(part).strip(sep) for part in (project_root, solution_root, usecase_id) if part]
    return sep.join(parts)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return _read_json(path)
    except Exception:
        return None


def _extract_preprocess_entry(run_summary: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not run_summary:
        return None
    entries = run_summary.get("preprocess_variants") or run_summary.get("preprocess_tasks") or []
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        if entry.get("processed_dataset_id"):
            return dict(entry)
    return dict(entries[0]) if entries else None


def _check_dataset_files(dataset_dir: Path, *, errors: list[str]) -> None:
    if not dataset_dir.exists():
        errors.append(f"processed dataset directory not found: {dataset_dir}")
        return
    missing = [name for name in _REQUIRED_DATASET_FILES if not (dataset_dir / name).exists()]
    if missing:
        errors.append(f"processed dataset missing files: {', '.join(missing)}")
        return
    meta_path = dataset_dir / "meta.json"
    meta = _read_json_optional(meta_path) or {}
    missing_keys = [key for key in _REQUIRED_META_KEYS if key not in meta]
    if missing_keys:
        errors.append(f"processed dataset meta.json missing keys: {', '.join(missing_keys)}")
        return
    if bool(meta.get("store_features", True)):
        for name in ("X.parquet", "y.parquet"):
            if not (dataset_dir / name).exists():
                errors.append(f"processed dataset missing feature file: {name}")


def _verify_processed_dataset(
    *,
    run_summary: Mapping[str, Any] | None,
    clearml_enabled: bool,
    errors: list[str],
) -> str | None:
    entry = _extract_preprocess_entry(run_summary)
    if not entry:
        errors.append("preprocess entry not found in run_summary.json.")
        return None
    processed_dataset_id = str(entry.get("processed_dataset_id") or "").strip()
    if not processed_dataset_id:
        errors.append("processed_dataset_id missing in preprocess summary.")
        return None
    run_dir = entry.get("run_dir")
    if processed_dataset_id.startswith("local:") or not clearml_enabled:
        if not run_dir:
            errors.append("preprocess run_dir missing for local processed dataset check.")
            return processed_dataset_id
        dataset_dir = Path(str(run_dir)) / "processed_dataset"
        _check_dataset_files(dataset_dir, errors=errors)
        return processed_dataset_id
    try:
        dataset_dir = platform_adapter.get_clearml_dataset_local_copy(processed_dataset_id)
    except platform_adapter.PlatformAdapterError as exc:
        errors.append(f"ClearML processed dataset not accessible: {exc}")
        return processed_dataset_id
    _check_dataset_files(dataset_dir, errors=errors)
    return processed_dataset_id


def _verify_clearml_tasks(
    *,
    tasks: list[object],
    usecase_id: str,
    project_prefix: str | None,
    group_map: Mapping[str, Any],
    pipeline_task_id: str | None,
    errors: list[str],
    warnings: list[str],
) -> tuple[bool, bool, str | None]:
    grouped: dict[str, list[object]] = {}
    for task in tasks:
        tags = platform_adapter.clearml_task_tags(task)
        process = _process_from_tags(tags)
        grouped.setdefault(process, []).append(task)

    missing = [process for process in _REQUIRED_PROCESSES if process not in grouped]
    if missing:
        errors.append(f"missing ClearML tasks for processes: {', '.join(missing)}")

    if project_prefix:
        for process in _REQUIRED_PROCESSES:
            for task in grouped.get(process, []):
                project = platform_adapter.clearml_task_project(task)
                if not project:
                    errors.append(f"ClearML project missing for {process} task.")
                    continue
                if project_prefix not in project:
                    errors.append(
                        f"ClearML project path mismatch for {process}: expected prefix '{project_prefix}', got '{project}'."
                    )
                expected_group = str(group_map.get(process) or process)
                if expected_group and expected_group not in project:
                    errors.append(
                        f"ClearML project group mismatch for {process}: expected '{expected_group}' in '{project}'."
                    )

    hparam_checked = False
    for process in ("pipeline", "train_model"):
        task_list = grouped.get(process) or []
        if not task_list:
            continue
        hparam_checked = True
        sections = platform_adapter.clearml_task_parameters_sections(task_list[0])
        section_names = {name.lower() for name in sections.keys()}
        if not section_names:
            warnings.append(f"HyperParameters missing for {process} task.")
            continue
        if section_names == {"general"}:
            errors.append(f"HyperParameters are not categorized for {process} task (General only).")
            continue
        if not (section_names & _EXPECTED_HPARAM_SECTIONS):
            errors.append(
                f"HyperParameters sections look unclassified for {process} task: {', '.join(sorted(section_names))}."
            )

    scalars_ok = False
    plots_ok = False
    for process in ("train_model", "train_ensemble", "leaderboard", "pipeline"):
        for task in grouped.get(process, []):
            if not scalars_ok and platform_adapter.clearml_task_has_scalars(task):
                scalars_ok = True
            if not plots_ok and platform_adapter.clearml_task_has_plots(task):
                plots_ok = True
            if scalars_ok and plots_ok:
                break
        if scalars_ok and plots_ok:
            break
    if not scalars_ok:
        errors.append("ClearML scalars are missing (no reported scalars found).")
    if not plots_ok:
        errors.append("ClearML plots are missing (no reported plots found).")

    pipeline_task = None
    if pipeline_task_id:
        for task in tasks:
            if platform_adapter.clearml_task_id(task) == pipeline_task_id:
                pipeline_task = task
                break
    if pipeline_task is None:
        pipeline_tasks = grouped.get("pipeline") or []
        if pipeline_tasks:
            pipeline_task = pipeline_tasks[0]
    pipeline_task_id_resolved = platform_adapter.clearml_task_id(pipeline_task) if pipeline_task else None
    if pipeline_task is None:
        errors.append("pipeline task not found in ClearML.")
    elif not platform_adapter.clearml_task_has_artifact(pipeline_task, "run_summary.json"):
        errors.append("pipeline ClearML task missing run_summary.json artifact.")

    return scalars_ok, plots_ok, pipeline_task_id_resolved


def _run_verification(
    *,
    usecase_id: str,
    output_dir: Path,
    run_summary: Mapping[str, Any] | None,
    clearml_enabled: bool,
    clearml_tasks: list[object] | None,
    pipeline_task_id: str | None,
    config_dir: Path,
    project_root_override: str | None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    run_summary_path = output_dir / "99_pipeline" / "run_summary.json"
    if run_summary is None:
        errors.append(f"run_summary.json not found: {run_summary_path}")

    processed_dataset_id = _verify_processed_dataset(
        run_summary=run_summary, clearml_enabled=clearml_enabled, errors=errors
    )

    layout = _load_clearml_layout(config_dir)
    project_root = project_root_override
    if not project_root and run_summary:
        context = run_summary.get("context") if isinstance(run_summary, Mapping) else None
        if isinstance(context, Mapping):
            project_root = context.get("project_root")
    if not project_root:
        project_root = layout.get("project_root")
    project_prefix = None
    if project_root:
        project_prefix = _build_project_prefix(
            project_root=str(project_root),
            solution_root=str(layout.get("solution_root") or ""),
            usecase_id=usecase_id,
            separator=str(layout.get("separator") or "/"),
        )
    elif clearml_enabled:
        warnings.append("ClearML project_root not resolved; project hierarchy check skipped.")

    resolved_pipeline_task_id = pipeline_task_id
    if clearml_enabled:
        if clearml_tasks is None:
            errors.append("ClearML tasks could not be listed for verification.")
        else:
            _, _, resolved_pipeline_task_id = _verify_clearml_tasks(
                tasks=clearml_tasks,
                usecase_id=usecase_id,
                project_prefix=project_prefix,
                group_map=layout.get("group_map") or {},
                pipeline_task_id=pipeline_task_id,
                errors=errors,
                warnings=warnings,
            )

    status = "success" if not errors else "failure"
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "processed_dataset_id": processed_dataset_id,
        "project_prefix": project_prefix,
        "pipeline_task_id": resolved_pipeline_task_id or pipeline_task_id,
        "clearml_checked": bool(clearml_enabled),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run dataset_register + pipeline rehearsal.")
    parser.add_argument(
        "--execution",
        choices=["local", "logging", "agent"],
        default=None,
        help="Execution mode: local (no ClearML), logging (local + ClearML), agent (PipelineController).",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "logging", "agent"],
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--task-type", choices=["regression", "classification"], default="regression")
    parser.add_argument(
        "--models",
        default=None,
        help="Model variants (comma-separated) or 'all'/'small'. Default uses a tiny set.",
    )
    parser.add_argument("--preprocess", action="append", nargs="+", help="Preprocess variant(s).")
    parser.add_argument("--usecase-id", default=None)
    parser.add_argument("--project-root", default=None, help="ClearML project root override.")
    parser.add_argument("--queue-name", default=None, help="ClearML queue name (agent mode).")
    parser.add_argument("--dataset-path", default=None, help="Dataset path (default: auto toy data).")
    parser.add_argument(
        "--out-root",
        default="/tmp/ta_rehearsal_runs",
        help="Output root (run_summary.json is written here).",
    )
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    parser.add_argument("--config-dir", default=None, help="Config directory (default: repo conf/).")
    parser.add_argument("--no-verify", action="store_true", help="Skip post-run verification checks.")
    args = parser.parse_args(argv)

    task_type = _normalize_task_type(args.task_type)
    repo_root = _resolve_repo_root(args.repo_root)
    config_dir = _resolve_config_dir(repo_root, args.config_dir)
    out_root = Path(args.out_root).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    stamp, timestamp_iso = _utc_stamp()
    usecase_id = args.usecase_id or f"rehearsal_{task_type}_{stamp}"
    usecase_id = _sanitize_identifier(usecase_id)

    dataset_path = None
    if args.dataset_path:
        candidate = Path(args.dataset_path).expanduser()
        dataset_path = candidate if candidate.is_absolute() else repo_root / candidate
    if dataset_path is None:
        dataset_path = out_root / "data" / usecase_id / f"toy_{task_type}.csv"
    dataset_path = dataset_path.resolve()
    output_dir = out_root / "outputs" / usecase_id
    log_dir = out_root / "logs" / usecase_id

    preprocess_variants = _resolve_preprocess(args.preprocess)
    model_variants = _resolve_models(task_type, args.models)
    eval_overrides = _eval_overrides(task_type)

    execution = _normalize_execution(args.execution or args.mode)
    clearml_enabled = execution in ("logging", "agent")
    if execution == "agent":
        clearml_execution = "pipeline_controller"
    elif execution == "logging":
        clearml_execution = "logging"
    else:
        clearml_execution = "local"
    clearml_warning: str | None = None
    clearml_tasks: list[object] | None = None

    if clearml_enabled:
        tasks, err = _list_clearml_tasks(usecase_id)
        if err:
            print(f"[error] ClearML is required for execution={execution}: {err}", file=sys.stderr)
            return 2
        clearml_tasks = tasks

    py = sys.executable
    env = os.environ.copy()
    env.setdefault("TABULAR_ANALYSIS_CONFIG_DIR", str(config_dir))

    dataset_cmd: list[str] = [
        py,
        "-m",
        "tabular_analysis.cli",
        "task=dataset_register",
        f"run.output_dir={output_dir}",
        f"run.usecase_id={usecase_id}",
        f"data.dataset_path={dataset_path}",
        "data.target_column=target",
        *eval_overrides,
    ]
    if clearml_enabled:
        dataset_cmd.extend(["run.clearml.enabled=true", "run.clearml.execution=logging"])
    else:
        dataset_cmd.append("run.clearml.enabled=false")
    if args.project_root:
        dataset_cmd.append(f"run.clearml.project_root={args.project_root}")

    summary: dict[str, object] = {}
    status = "success"
    error: str | None = None
    raw_dataset_id: str | None = None
    processed_dataset_id: str | None = None
    pipeline_task_id: str | None = None
    train_task_ids: list[str] = []
    preprocess_task_ids: list[str] = []
    leaderboard_task_id: str | None = None
    clearml_tasks_summary: dict[str, list[dict[str, str | None]]] | None = None
    verification: dict[str, Any] | None = None
    run_summary: dict[str, Any] | None = None

    try:
        if not dataset_path.exists():
            _make_toy_dataset(dataset_path, task_type=task_type)
        _run(dataset_cmd, cwd=repo_root, env=env, log_path=log_dir / "dataset_register.log")

        dataset_out_path = output_dir / "01_dataset_register" / "out.json"
        if not dataset_out_path.exists():
            raise FileNotFoundError(f"dataset_register output not found: {dataset_out_path}")
        dataset_out = json.loads(dataset_out_path.read_text(encoding="utf-8"))
        raw_dataset_id = str(dataset_out.get("raw_dataset_id") or "").strip() or None
        if not raw_dataset_id:
            raise RuntimeError("raw_dataset_id not found in dataset_register output.")

        pipeline_cmd: list[str] = [
            py,
            "-m",
            "tabular_analysis.cli",
            "task=pipeline",
            f"run.output_dir={output_dir}",
            f"run.usecase_id={usecase_id}",
            f"data.raw_dataset_id={raw_dataset_id}",
            f"pipeline.preprocess_variants={_json_arg(preprocess_variants)}",
            f"pipeline.model_variants={_json_arg(model_variants)}",
            "ensemble.enabled=true",
            "ensemble.top_k=1",
            *eval_overrides,
        ]
        if raw_dataset_id.startswith("local:"):
            pipeline_cmd.append(f"data.dataset_path={dataset_path}")
        if clearml_enabled:
            pipeline_cmd.extend(
                [f"run.clearml.enabled=true", f"run.clearml.execution={clearml_execution}"]
            )
            if args.queue_name:
                pipeline_cmd.append(f"run.clearml.queue_name={args.queue_name}")
        else:
            pipeline_cmd.append("run.clearml.enabled=false")
            pipeline_cmd.append("run.clearml.execution=local")
        if args.project_root:
            pipeline_cmd.append(f"run.clearml.project_root={args.project_root}")

        _run(pipeline_cmd, cwd=repo_root, env=env, log_path=log_dir / "pipeline.log")

        pipeline_out_path = output_dir / "99_pipeline" / "out.json"
        if pipeline_out_path.exists():
            pipeline_out = json.loads(pipeline_out_path.read_text(encoding="utf-8"))
        else:
            pipeline_out = {}
        pipeline_run = pipeline_out.get("pipeline_run") if isinstance(pipeline_out, dict) else {}
        if isinstance(pipeline_run, dict):
            preprocess_task_ids = _collect_ids(
                ref.get("task_id") for ref in pipeline_run.get("preprocess_ref") or []
            )
            train_task_ids = _collect_ids(
                ref.get("train_task_id") or ref.get("task_id")
                for ref in pipeline_run.get("train_refs") or []
            )
            leaderboard_ref = pipeline_run.get("leaderboard_ref") or {}
            if isinstance(leaderboard_ref, dict):
                leaderboard_task_id = leaderboard_ref.get("task_id")

        report_links_path = output_dir / "99_pipeline" / "report_links.json"
        if report_links_path.exists():
            report_links = json.loads(report_links_path.read_text(encoding="utf-8"))
            if isinstance(report_links, dict):
                pipeline_entry = report_links.get("pipeline") or {}
                if isinstance(pipeline_entry, dict):
                    pipeline_task_id = pipeline_entry.get("task_id") or pipeline_task_id
                if not train_task_ids:
                    train_entries = report_links.get("train") or []
                    if isinstance(train_entries, list):
                        train_task_ids = _collect_ids(entry.get("task_id") for entry in train_entries)

        if clearml_enabled:
            tasks, err = _list_clearml_tasks(usecase_id)
            if tasks is not None:
                clearml_tasks = tasks
                clearml_tasks_summary = _summarize_clearml_tasks(tasks)
                if not pipeline_task_id:
                    pipeline_tasks = clearml_tasks_summary.get("pipeline") or []
                    if pipeline_tasks:
                        pipeline_task_id = pipeline_tasks[0].get("task_id")
                _print_clearml_tasks(usecase_id, tasks)
            else:
                clearml_tasks = None
                clearml_warning = err or clearml_warning
                print(f"[warn] ClearML task listing skipped: {clearml_warning}")

        run_summary_path = output_dir / "99_pipeline" / "run_summary.json"
        run_summary = _read_json_optional(run_summary_path)
        entry = _extract_preprocess_entry(run_summary)
        if entry:
            processed_dataset_id = str(entry.get("processed_dataset_id") or "").strip() or processed_dataset_id
    except Exception as exc:
        status = "failure"
        error = _summarize_error(exc)
    finally:
        if args.no_verify:
            verification = {"status": "skipped", "reason": "no-verify"}
        elif status != "success":
            verification = {"status": "skipped", "reason": "run_failed"}
        else:
            verification = _run_verification(
                usecase_id=usecase_id,
                output_dir=output_dir,
                run_summary=run_summary,
                clearml_enabled=clearml_enabled,
                clearml_tasks=clearml_tasks,
                pipeline_task_id=pipeline_task_id,
                config_dir=config_dir,
                project_root_override=args.project_root,
            )
            if verification.get("status") == "failure":
                status = "failure"
        summary = {
            "status": status,
            "error": error,
            "timestamp_utc": timestamp_iso,
            "usecase_id": usecase_id,
            "execution": execution,
            "task_type": task_type,
            "models": args.models,
            "model_variants": model_variants,
            "preprocess_variants": preprocess_variants,
            "repo_root": str(repo_root),
            "out_root": str(out_root),
            "output_dir": str(output_dir),
            "dataset_path": str(dataset_path),
            "raw_dataset_id": raw_dataset_id,
            "processed_dataset_id": processed_dataset_id
            or (verification or {}).get("processed_dataset_id"),
            "pipeline_task_id": pipeline_task_id,
            "train_task_ids": train_task_ids,
            "preprocess_task_ids": preprocess_task_ids,
            "leaderboard_task_id": leaderboard_task_id,
            "clearml": {
                "enabled": clearml_enabled,
                "execution": clearml_execution,
                "queue_name": args.queue_name,
                "project_root": args.project_root,
                "warning": clearml_warning,
            },
            "clearml_tasks": clearml_tasks_summary,
            "verification": verification,
        }
        summary_path = out_root / "run_summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")
        output_summary_path = output_dir / "run_summary.json"
        output_summary_path.parent.mkdir(parents=True, exist_ok=True)
        output_summary_path.write_text(
            json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8"
        )

    processed_value = processed_dataset_id or (verification or {}).get("processed_dataset_id") or "unknown"
    pipeline_value = pipeline_task_id or (verification or {}).get("pipeline_task_id") or "unknown"

    print("")
    print("Rehearsal summary:")
    print(f"- usecase_id: {usecase_id}")
    print(f"- raw_dataset_id: {raw_dataset_id or 'unknown'}")
    print(f"- processed_dataset_id: {processed_value}")
    print(f"- pipeline_task_id: {pipeline_value}")
    print(f"- output_dir: {output_dir}")
    print(f"- search tag: usecase:{usecase_id}")
    if verification:
        print(f"- verification: {verification.get('status')}")
        if verification.get("errors"):
            print("  errors:")
            for item in verification.get("errors", []):
                print(f"    - {item}")
        if verification.get("warnings"):
            print("  warnings:")
            for item in verification.get("warnings", []):
                print(f"    - {item}")

    return 0 if status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
