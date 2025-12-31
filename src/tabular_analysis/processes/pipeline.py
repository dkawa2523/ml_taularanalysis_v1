"""pipeline process.

T009: grid execution + task_id handoff.
- dataset_register/preprocess/train/leaderboard/infer を独立タスクとして実行する接着剤
- grid_run_id を生成し、各タスクへ伝播させる
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Mapping
import uuid

from ..platform_adapter import (
    create_pipeline_controller,
    hash_config,
    hash_recipe,
    hash_split,
    init_task_context,
    is_clearml_enabled,
    pipeline_require_clearml_agent,
    pipeline_step_task_id_ref,
    resolve_version_props,
    save_config_resolved,
    upload_artifact,
    write_manifest,
    write_out_json,
)

_STAGE_BY_TASK = {
    "dataset_register": "01_dataset_register",
    "preprocess": "02_preprocess",
    "train_model": "03_train_model",
    "infer": "04_infer",
    "leaderboard": "05_leaderboard",
}


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
        if isinstance(current, Mapping):
            if key not in current:
                return default
            current = current[key]
            continue
        if not hasattr(current, key):
            return default
        current = getattr(current, key)
    return current


def _set_cfg_value(cfg: Any, dotted_path: str, value: Any) -> bool:
    if cfg is None:
        return False
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(cfg):
        try:
            was_struct = OmegaConf.is_struct(cfg)
        except Exception:
            was_struct = False
        if was_struct:
            try:
                OmegaConf.set_struct(cfg, False)
            except Exception:
                pass
        try:
            OmegaConf.update(cfg, dotted_path, value, merge=False)
            return True
        except Exception:
            return False
        finally:
            if was_struct:
                try:
                    OmegaConf.set_struct(cfg, True)
                except Exception:
                    pass
    current = cfg
    keys = dotted_path.split(".")
    for key in keys[:-1]:
        if isinstance(current, Mapping):
            if key not in current or not isinstance(current[key], Mapping):
                current[key] = {}
            current = current[key]
            continue
        if not hasattr(current, key) or getattr(current, key) is None:
            setattr(current, key, type("CfgNode", (), {})())
        current = getattr(current, key)
    last = keys[-1]
    if isinstance(current, Mapping):
        current[last] = value
        return True
    try:
        setattr(current, last, value)
        return True
    except Exception:
        return False


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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


def _ensure_grid_run_id(cfg: Any) -> str:
    grid_run_id = _normalize_str(_cfg_value(cfg, "run.grid_run_id"))
    if grid_run_id:
        return grid_run_id
    new_id = uuid.uuid4().hex
    _set_cfg_value(cfg, "run.grid_run_id", new_id)
    return new_id


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


def _overrides_to_params(overrides: Mapping[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for key, value in overrides.items():
        formatted = _format_value(value)
        if formatted is None:
            continue
        params[key] = formatted
    return params


def _merge_overrides(*items: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for item in items:
        merged.update(dict(item))
    return merged


def _collect_run_overrides(cfg: Any, grid_run_id: str) -> dict[str, Any]:
    run_cfg = getattr(cfg, "run", None)
    overrides: dict[str, Any] = {
        "run.grid_run_id": grid_run_id,
    }
    if run_cfg is None:
        return overrides
    overrides["run.usecase_id"] = getattr(run_cfg, "usecase_id", None)
    overrides["run.schema_version"] = getattr(run_cfg, "schema_version", None)
    clearml_cfg = getattr(run_cfg, "clearml", None)
    if clearml_cfg is not None:
        overrides["run.clearml.enabled"] = bool(getattr(clearml_cfg, "enabled", False))
        overrides["run.clearml.execution"] = getattr(clearml_cfg, "execution", None)
        overrides["run.clearml.project_root"] = getattr(clearml_cfg, "project_root", None)
        overrides["run.clearml.queue_name"] = getattr(clearml_cfg, "queue_name", None)
        overrides["run.clearml.clone_from_task_id"] = getattr(clearml_cfg, "clone_from_task_id", None)
        extra_tags = getattr(clearml_cfg, "extra_tags", None)
        if extra_tags:
            overrides["run.clearml.extra_tags"] = list(extra_tags)
    return overrides


def _collect_data_overrides(cfg: Any) -> dict[str, Any]:
    data_cfg = getattr(cfg, "data", None)
    overrides: dict[str, Any] = {}
    if data_cfg is None:
        return overrides
    for key in ("dataset_path", "raw_dataset_id", "processed_dataset_id", "target_column"):
        value = getattr(data_cfg, key, None)
        if value is not None:
            overrides[f"data.{key}"] = value
    id_columns = getattr(data_cfg, "id_columns", None)
    if id_columns:
        overrides["data.id_columns"] = list(id_columns)
    drop_columns = getattr(data_cfg, "drop_columns", None)
    if drop_columns:
        overrides["data.drop_columns"] = list(drop_columns)
    split_cfg = getattr(data_cfg, "split", None)
    if split_cfg is not None:
        for key in ("strategy", "test_size", "seed", "group_column", "time_column"):
            value = getattr(split_cfg, key, None)
            if value is not None:
                overrides[f"data.split.{key}"] = value
    return overrides


def _collect_eval_overrides(cfg: Any) -> dict[str, Any]:
    eval_cfg = getattr(cfg, "eval", None)
    overrides: dict[str, Any] = {}
    if eval_cfg is None:
        return overrides
    for key in ("primary_metric", "direction", "cv_folds", "seed"):
        value = getattr(eval_cfg, key, None)
        if value is not None:
            overrides[f"eval.{key}"] = value
    return overrides


def _build_run_root(base_output_dir: Path, grid_run_id: str, name: str) -> Path:
    safe_name = _sanitize_component(name)
    return base_output_dir / "grid" / str(grid_run_id) / safe_name


def _stage_dir(run_root: Path, task_name: str) -> Path:
    stage = _STAGE_BY_TASK[task_name]
    return run_root / stage


def _clearml_project(cfg: Any, stage: str) -> str:
    project_root = _normalize_str(_cfg_value(cfg, "run.clearml.project_root")) or "MFG"
    usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id")) or "unknown"
    return f"{project_root}/{usecase_id}/{stage}"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_cli_task(args: list[str], *, cwd: Path) -> None:
    cmd = [sys.executable, "-m", "tabular_analysis.cli", *args]
    proc = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit={proc.returncode})\n$ {' '.join(cmd)}\n\n{proc.stdout}"
        )


def _resolve_variants(cfg: Any) -> tuple[list[str], list[str]]:
    preprocess_variants = _to_list(_cfg_value(cfg, "pipeline.grid.preprocess_variants"))
    if not preprocess_variants:
        fallback = _normalize_str(_cfg_value(cfg, "preprocess_variant.name")) or _normalize_str(
            _cfg_value(cfg, "group.preprocess.preprocess_variant.name")
        )
        if fallback:
            preprocess_variants = [fallback]
    model_variants = _to_list(_cfg_value(cfg, "pipeline.grid.model_variants"))
    if not model_variants:
        fallback = _normalize_str(_cfg_value(cfg, "model_variant.name")) or _normalize_str(
            _cfg_value(cfg, "group.model.model_variant.name")
        )
        if fallback:
            model_variants = [fallback]
    return preprocess_variants, model_variants


def _collect_step_task_ids(controller: Any) -> dict[str, str]:
    getter = getattr(controller, "get_processed_nodes", None)
    nodes = getter() if callable(getter) else {}
    payload: dict[str, str] = {}
    for name, node in dict(nodes).items():
        task_id = getattr(node, "executed", None)
        if not task_id and getattr(node, "job", None):
            job = node.job
            if hasattr(job, "task_id"):
                task_id = job.task_id() if callable(job.task_id) else job.task_id
        if task_id:
            payload[str(name)] = str(task_id)
    return payload


def _build_ref(*, run_dir: Path | None = None, task_id: str | None = None, **extras: Any) -> dict[str, Any]:
    ref: dict[str, Any] = {}
    if task_id:
        ref["task_id"] = str(task_id)
    if run_dir is not None:
        ref["run_dir"] = str(run_dir)
    for key, value in extras.items():
        if value is not None:
            ref[key] = value
    return ref


def _run_local_pipeline(cfg: Any, grid_run_id: str, *, clearml_enabled: bool) -> dict[str, Any]:
    base_output_dir = Path(getattr(cfg.run, "output_dir", "outputs")).expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[2]

    pipeline_cfg = getattr(cfg, "pipeline", None)
    run_dataset_register = bool(getattr(pipeline_cfg, "run_dataset_register", True))
    run_preprocess = bool(getattr(pipeline_cfg, "run_preprocess", True))
    run_train = bool(getattr(pipeline_cfg, "run_train", True))
    run_leaderboard = bool(getattr(pipeline_cfg, "run_leaderboard", True))
    run_infer = bool(getattr(pipeline_cfg, "run_infer", False))

    preprocess_variants, model_variants = _resolve_variants(cfg)
    max_jobs = int(_cfg_value(cfg, "pipeline.grid.max_jobs") or 0)
    if run_train:
        job_count = len(preprocess_variants) * len(model_variants)
        if max_jobs and job_count > max_jobs:
            raise ValueError(f"grid jobs exceed max_jobs ({job_count} > {max_jobs}).")
    if run_train and not run_preprocess:
        raise ValueError("pipeline.run_preprocess=false cannot be combined with run_train=true.")

    run_overrides = _collect_run_overrides(cfg, grid_run_id)
    data_overrides = _collect_data_overrides(cfg)
    eval_overrides = _collect_eval_overrides(cfg)

    dataset_register_ref: dict[str, Any] | None = None
    preprocess_refs: list[dict[str, Any]] = []
    train_refs: list[dict[str, Any]] = []
    leaderboard_ref: dict[str, Any] | None = None
    infer_ref: dict[str, Any] | None = None

    dataset_out: dict[str, Any] | None = None
    if run_dataset_register:
        run_root = _build_run_root(base_output_dir, grid_run_id, "dataset_register")
        stage_dir = _stage_dir(run_root, "dataset_register")
        args = [
            "task=dataset_register",
            f"run.output_dir={_format_value(run_root)}",
            *_overrides_to_args(run_overrides),
            *_overrides_to_args(data_overrides),
        ]
        _run_cli_task(args, cwd=repo_root)
        dataset_register_ref = _build_ref(run_dir=stage_dir)
        dataset_out = _load_json(stage_dir / "out.json")
        raw_dataset_id = _normalize_str(dataset_out.get("raw_dataset_id"))
        if raw_dataset_id:
            data_overrides["data.raw_dataset_id"] = raw_dataset_id

    preprocess_outputs: dict[str, dict[str, Any]] = {}
    if run_preprocess:
        if not preprocess_variants:
            raise ValueError("pipeline.grid.preprocess_variants is empty.")
        for preprocess_variant in preprocess_variants:
            run_root = _build_run_root(base_output_dir, grid_run_id, f"preprocess__{preprocess_variant}")
            stage_dir = _stage_dir(run_root, "preprocess")
            overrides = _merge_overrides(
                data_overrides, {"group/preprocess": preprocess_variant}
            )
            args = [
                "task=preprocess",
                f"run.output_dir={_format_value(run_root)}",
                *_overrides_to_args(run_overrides),
                *_overrides_to_args(overrides),
            ]
            _run_cli_task(args, cwd=repo_root)
            out = _load_json(stage_dir / "out.json")
            preprocess_refs.append(
                _build_ref(
                    run_dir=stage_dir,
                    preprocess_variant=preprocess_variant,
                    processed_dataset_id=out.get("processed_dataset_id"),
                    split_hash=out.get("split_hash"),
                    recipe_hash=out.get("recipe_hash"),
                )
            )
            preprocess_outputs[preprocess_variant] = {"run_dir": stage_dir, "out": out}

    if run_train:
        if not preprocess_outputs:
            raise ValueError("preprocess outputs are required before train.")
        if not model_variants:
            raise ValueError("pipeline.grid.model_variants is empty.")
        for preprocess_variant, payload in preprocess_outputs.items():
            preprocess_run_dir = payload["run_dir"]
            preprocess_out = payload["out"]
            processed_dataset_id = _normalize_str(preprocess_out.get("processed_dataset_id"))
            for model_variant in model_variants:
                run_root = _build_run_root(
                    base_output_dir, grid_run_id, f"train__{preprocess_variant}__{model_variant}"
                )
                stage_dir = _stage_dir(run_root, "train_model")
                overrides = _merge_overrides(
                    data_overrides,
                    eval_overrides,
                    {
                        "group/model": model_variant,
                        "train.inputs.preprocess_run_dir": str(preprocess_run_dir),
                    },
                )
                if processed_dataset_id:
                    overrides["data.processed_dataset_id"] = processed_dataset_id
                args = [
                    "task=train_model",
                    f"run.output_dir={_format_value(run_root)}",
                    *_overrides_to_args(run_overrides),
                    *_overrides_to_args(overrides),
                ]
                _run_cli_task(args, cwd=repo_root)
                out = _load_json(stage_dir / "out.json")
                train_refs.append(
                    _build_ref(
                        run_dir=stage_dir,
                        preprocess_variant=preprocess_variant,
                        model_variant=model_variant,
                        train_task_id=out.get("train_task_id"),
                        model_id=out.get("model_id"),
                        best_score=out.get("best_score"),
                        primary_metric=out.get("primary_metric"),
                    )
                )

    leaderboard_out: dict[str, Any] | None = None
    if run_leaderboard:
        if not train_refs:
            raise ValueError("train outputs are required before leaderboard.")
        run_root = _build_run_root(base_output_dir, grid_run_id, "leaderboard")
        stage_dir = _stage_dir(run_root, "leaderboard")
        overrides: dict[str, Any] = dict(eval_overrides)
        if clearml_enabled:
            train_task_ids = [
                ref.get("train_task_id") for ref in train_refs if ref.get("train_task_id")
            ]
            if not train_task_ids:
                raise ValueError("train_task_id is missing in train outputs (ClearML mode).")
            overrides["leaderboard.train_task_ids"] = train_task_ids
        else:
            train_run_dirs = [ref.get("run_dir") for ref in train_refs if ref.get("run_dir")]
            overrides["leaderboard.train_run_dirs"] = train_run_dirs
        args = [
            "task=leaderboard",
            f"run.output_dir={_format_value(run_root)}",
            *_overrides_to_args(run_overrides),
            *_overrides_to_args(overrides),
        ]
        _run_cli_task(args, cwd=repo_root)
        leaderboard_out = _load_json(stage_dir / "out.json")
        leaderboard_ref = _build_ref(run_dir=stage_dir)

    if run_infer:
        run_root = _build_run_root(base_output_dir, grid_run_id, "infer")
        stage_dir = _stage_dir(run_root, "infer")
        infer_cfg = getattr(cfg, "infer", None)
        infer_mode = _normalize_str(getattr(infer_cfg, "mode", None)) or "single"
        overrides = {"infer.mode": infer_mode}
        if clearml_enabled:
            train_task_id = None
            if leaderboard_out is not None:
                train_task_id = _normalize_str(leaderboard_out.get("recommended_train_task_id"))
            train_task_id = train_task_id or _normalize_str(getattr(infer_cfg, "train_task_id", None))
            model_id = _normalize_str(getattr(infer_cfg, "model_id", None))
            if train_task_id:
                overrides["infer.train_task_id"] = train_task_id
            elif model_id:
                overrides["infer.model_id"] = model_id
            else:
                raise ValueError("infer requires train_task_id or model_id in ClearML mode.")
        else:
            model_id = None
            train_task_ref = None
            if leaderboard_out is not None:
                model_id = _normalize_str(leaderboard_out.get("recommended_model_id"))
                train_task_ref = _normalize_str(leaderboard_out.get("recommended_train_task_ref"))
            if model_id:
                overrides["infer.model_id"] = model_id
            elif train_task_ref:
                overrides["infer.train_task_id"] = train_task_ref
            else:
                fallback_model = _normalize_str(getattr(infer_cfg, "model_id", None))
                fallback_task = _normalize_str(getattr(infer_cfg, "train_task_id", None))
                if fallback_model:
                    overrides["infer.model_id"] = fallback_model
                elif fallback_task:
                    overrides["infer.train_task_id"] = fallback_task
                else:
                    raise ValueError("infer requires model_id or train_task_id.")
        args = [
            "task=infer",
            f"run.output_dir={_format_value(run_root)}",
            *_overrides_to_args(run_overrides),
            *_overrides_to_args(overrides),
        ]
        _run_cli_task(args, cwd=repo_root)
        infer_ref = _build_ref(run_dir=stage_dir)

    pipeline_run = {
        "grid_run_id": grid_run_id,
        "dataset_register_ref": dataset_register_ref,
        "preprocess_ref": preprocess_refs,
        "train_refs": train_refs,
        "leaderboard_ref": leaderboard_ref,
        "infer_ref": infer_ref,
        "grid": {
            "preprocess_variants": preprocess_variants,
            "model_variants": model_variants,
            "max_jobs": max_jobs,
        },
    }
    return pipeline_run


def _run_clearml_pipeline(cfg: Any, grid_run_id: str) -> dict[str, Any]:
    base_output_dir = Path(getattr(cfg.run, "output_dir", "outputs")).expanduser().resolve()
    pipeline_cfg = getattr(cfg, "pipeline", None)
    run_dataset_register = bool(getattr(pipeline_cfg, "run_dataset_register", True))
    run_preprocess = bool(getattr(pipeline_cfg, "run_preprocess", True))
    run_train = bool(getattr(pipeline_cfg, "run_train", True))
    run_leaderboard = bool(getattr(pipeline_cfg, "run_leaderboard", True))
    run_infer = bool(getattr(pipeline_cfg, "run_infer", False))

    preprocess_variants, model_variants = _resolve_variants(cfg)
    max_jobs = int(_cfg_value(cfg, "pipeline.grid.max_jobs") or 0)
    if run_train:
        job_count = len(preprocess_variants) * len(model_variants)
        if max_jobs and job_count > max_jobs:
            raise ValueError(f"grid jobs exceed max_jobs ({job_count} > {max_jobs}).")
    if run_train and not run_preprocess:
        raise ValueError("pipeline.run_preprocess=false cannot be combined with run_train=true.")

    run_overrides = _collect_run_overrides(cfg, grid_run_id)
    data_overrides = _collect_data_overrides(cfg)
    eval_overrides = _collect_eval_overrides(cfg)

    queue_name = _normalize_str(_cfg_value(cfg, "run.clearml.queue_name"))
    pipeline_name = _normalize_str(_cfg_value(cfg, "run.clearml.task_name")) or "pipeline"
    controller = create_pipeline_controller(cfg, name=pipeline_name)
    pipeline_require_clearml_agent(queue_name)

    dataset_step_name = None
    if run_dataset_register:
        dataset_step_name = "dataset_register"
        run_root = _build_run_root(base_output_dir, grid_run_id, "dataset_register")
        overrides = _merge_overrides(run_overrides, data_overrides, {"run.output_dir": str(run_root)})
        controller.add_step(
            name=dataset_step_name,
            base_task_project=_clearml_project(cfg, _STAGE_BY_TASK["dataset_register"]),
            base_task_name="dataset_register",
            parameter_override={f"Args/{k}": v for k, v in _overrides_to_params(overrides).items()},
            clone_base_task=True,
            cache_executed_step=False,
        )

    preprocess_steps: dict[str, dict[str, Any]] = {}
    if run_preprocess:
        if not preprocess_variants:
            raise ValueError("pipeline.grid.preprocess_variants is empty.")
        for preprocess_variant in preprocess_variants:
            step_name = f"preprocess__{_sanitize_component(preprocess_variant)}"
            run_root = _build_run_root(base_output_dir, grid_run_id, f"preprocess__{preprocess_variant}")
            parents = [dataset_step_name] if dataset_step_name else []
            overrides = _merge_overrides(
                run_overrides,
                data_overrides,
                {"group/preprocess": preprocess_variant, "run.output_dir": str(run_root)},
            )
            controller.add_step(
                name=step_name,
                base_task_project=_clearml_project(cfg, _STAGE_BY_TASK["preprocess"]),
                base_task_name="preprocess",
                parents=parents,
                parameter_override={f"Args/{k}": v for k, v in _overrides_to_params(overrides).items()},
                clone_base_task=True,
                cache_executed_step=False,
            )
            preprocess_steps[preprocess_variant] = {
                "step_name": step_name,
                "run_dir": _stage_dir(run_root, "preprocess"),
            }

    train_steps: list[dict[str, Any]] = []
    if run_train:
        if not preprocess_steps:
            raise ValueError("preprocess outputs are required before train.")
        if not model_variants:
            raise ValueError("pipeline.grid.model_variants is empty.")
        for preprocess_variant, payload in preprocess_steps.items():
            preprocess_run_dir = payload["run_dir"]
            for model_variant in model_variants:
                step_name = f"train__{_sanitize_component(preprocess_variant)}__{_sanitize_component(model_variant)}"
                run_root = _build_run_root(
                    base_output_dir, grid_run_id, f"train__{preprocess_variant}__{model_variant}"
                )
                overrides = _merge_overrides(
                    run_overrides,
                    data_overrides,
                    eval_overrides,
                    {
                        "group/model": model_variant,
                        "train.inputs.preprocess_run_dir": str(preprocess_run_dir),
                        "run.output_dir": str(run_root),
                    },
                )
                controller.add_step(
                    name=step_name,
                    base_task_project=_clearml_project(cfg, _STAGE_BY_TASK["train_model"]),
                    base_task_name="train_model",
                    parents=[payload["step_name"]],
                    parameter_override={f"Args/{k}": v for k, v in _overrides_to_params(overrides).items()},
                    clone_base_task=True,
                    cache_executed_step=False,
                )
                train_steps.append(
                    {
                        "step_name": step_name,
                        "run_dir": _stage_dir(run_root, "train_model"),
                        "preprocess_variant": preprocess_variant,
                        "model_variant": model_variant,
                    }
                )

    leaderboard_step_name = None
    if run_leaderboard:
        if not train_steps:
            raise ValueError("train outputs are required before leaderboard.")
        leaderboard_step_name = "leaderboard"
        run_root = _build_run_root(base_output_dir, grid_run_id, "leaderboard")
        train_task_refs = [pipeline_step_task_id_ref(step["step_name"]) for step in train_steps]
        overrides = _merge_overrides(
            run_overrides,
            eval_overrides,
            {
                "leaderboard.train_task_ids": train_task_refs,
                "run.output_dir": str(run_root),
            },
        )
        controller.add_step(
            name=leaderboard_step_name,
            base_task_project=_clearml_project(cfg, _STAGE_BY_TASK["leaderboard"]),
            base_task_name="leaderboard",
            parents=[step["step_name"] for step in train_steps],
            parameter_override={f"Args/{k}": v for k, v in _overrides_to_params(overrides).items()},
            clone_base_task=True,
            cache_executed_step=False,
        )

    infer_step_name = None
    infer_cfg = getattr(cfg, "infer", None)
    if run_infer:
        infer_step_name = "infer"
        run_root = _build_run_root(base_output_dir, grid_run_id, "infer")
        overrides = _merge_overrides(
            run_overrides,
            {"infer.mode": _normalize_str(getattr(infer_cfg, "mode", None)) or "single"},
            {"run.output_dir": str(run_root)},
        )
        infer_model_id = _normalize_str(getattr(infer_cfg, "model_id", None))
        infer_train_task_id = _normalize_str(getattr(infer_cfg, "train_task_id", None))
        if infer_train_task_id:
            overrides["infer.train_task_id"] = infer_train_task_id
        elif infer_model_id:
            overrides["infer.model_id"] = infer_model_id
        else:
            raise ValueError("infer requires model_id or train_task_id in agent/clone mode.")
        parents = [leaderboard_step_name] if leaderboard_step_name else []
        controller.add_step(
            name=infer_step_name,
            base_task_project=_clearml_project(cfg, _STAGE_BY_TASK["infer"]),
            base_task_name="infer",
            parents=parents,
            parameter_override={f"Args/{k}": v for k, v in _overrides_to_params(overrides).items()},
            clone_base_task=True,
            cache_executed_step=False,
        )

    controller.start_locally(run_pipeline_steps_locally=False)
    step_task_ids = _collect_step_task_ids(controller)

    dataset_register_ref = None
    if dataset_step_name:
        dataset_run_dir = _stage_dir(
            _build_run_root(base_output_dir, grid_run_id, "dataset_register"), "dataset_register"
        )
        dataset_register_ref = _build_ref(
            run_dir=dataset_run_dir, task_id=step_task_ids.get(dataset_step_name)
        )

    preprocess_refs = []
    for preprocess_variant, payload in preprocess_steps.items():
        preprocess_refs.append(
            _build_ref(
                run_dir=payload["run_dir"],
                task_id=step_task_ids.get(payload["step_name"]),
                preprocess_variant=preprocess_variant,
            )
        )

    train_refs = []
    for step in train_steps:
        train_refs.append(
            _build_ref(
                run_dir=step["run_dir"],
                task_id=step_task_ids.get(step["step_name"]),
                preprocess_variant=step["preprocess_variant"],
                model_variant=step["model_variant"],
            )
        )

    leaderboard_ref = None
    if leaderboard_step_name:
        leaderboard_run_dir = _stage_dir(
            _build_run_root(base_output_dir, grid_run_id, "leaderboard"), "leaderboard"
        )
        leaderboard_ref = _build_ref(
            run_dir=leaderboard_run_dir, task_id=step_task_ids.get(leaderboard_step_name)
        )

    infer_ref = None
    if infer_step_name:
        infer_run_dir = _stage_dir(_build_run_root(base_output_dir, grid_run_id, "infer"), "infer")
        infer_ref = _build_ref(run_dir=infer_run_dir, task_id=step_task_ids.get(infer_step_name))

    pipeline_run = {
        "grid_run_id": grid_run_id,
        "dataset_register_ref": dataset_register_ref,
        "preprocess_ref": preprocess_refs,
        "train_refs": train_refs,
        "leaderboard_ref": leaderboard_ref,
        "infer_ref": infer_ref,
        "grid": {
            "preprocess_variants": preprocess_variants,
            "model_variants": model_variants,
            "max_jobs": max_jobs,
        },
    }
    return pipeline_run


def run(cfg: Any) -> None:
    grid_run_id = _ensure_grid_run_id(cfg)
    ctx = init_task_context(cfg, stage=cfg.task.stage, task_name="pipeline")
    save_config_resolved(ctx, cfg)

    clearml_enabled = is_clearml_enabled(cfg)
    execution = _normalize_str(_cfg_value(cfg, "run.clearml.execution")) or "local"

    if clearml_enabled and execution in ("agent", "clone"):
        pipeline_run = _run_clearml_pipeline(cfg, grid_run_id)
    else:
        pipeline_run = _run_local_pipeline(cfg, grid_run_id, clearml_enabled=clearml_enabled)

    pipeline_run_path = ctx.output_dir / "pipeline_run.json"
    pipeline_run_path.write_text(
        json.dumps(pipeline_run, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if clearml_enabled:
        upload_artifact(ctx, "pipeline_run.json", pipeline_run_path)

    out = {"pipeline_run": pipeline_run}
    write_out_json(ctx, out)

    versions = resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    manifest = {
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "process": "pipeline",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "run_dataset_register": bool(getattr(getattr(cfg, "pipeline", None), "run_dataset_register", True)),
            "run_preprocess": bool(getattr(getattr(cfg, "pipeline", None), "run_preprocess", True)),
            "run_train": bool(getattr(getattr(cfg, "pipeline", None), "run_train", True)),
            "run_leaderboard": bool(getattr(getattr(cfg, "pipeline", None), "run_leaderboard", True)),
            "run_infer": bool(getattr(getattr(cfg, "pipeline", None), "run_infer", False)),
        },
        "outputs": {"grid_run_id": grid_run_id, "pipeline_run_path": str(pipeline_run_path)},
        "hashes": {
            "config_hash": hash_config(cfg),
            "split_hash": hash_split({}),
            "recipe_hash": hash_recipe({}),
        },
    }
    write_manifest(ctx, manifest)
