"""ClearML template task resolution helpers."""

from __future__ import annotations

from typing import Any, Mapping

from ..platform_adapter import (
    clearml_script_mismatches,
    clearml_task_id,
    clearml_task_script,
    clearml_task_status_from_obj,
    clearml_task_tags,
    list_clearml_tasks_by_tags,
    resolve_clearml_script_spec,
)

_STAGE_BY_PROCESS = {
    "dataset_register": "01_dataset_register",
    "preprocess": "02_preprocess",
    "train_model": "03_train_model",
    "train_ensemble": "04_train_ensemble",
    "infer": "04_infer",
    "leaderboard": "05_leaderboard",
    "pipeline": "99_pipeline",
}
_SOLUTION_TAG = "solution:tabular-analysis"


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


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _template_project_name(cfg: Any, process: str) -> str | None:
    stage = _STAGE_BY_PROCESS.get(process)
    if not stage:
        return None
    project_root = _normalize_str(_cfg_value(cfg, "run.clearml.project_root")) or "MFG"
    template_usecase = _normalize_str(_cfg_value(cfg, "run.clearml.template_usecase_id")) or "TabularAnalysis"
    return f"{project_root}/{template_usecase}/{stage}"


def resolve_template_task_id(cfg: Any, process: str) -> str:
    process_name = _normalize_str(process)
    if not process_name:
        raise ValueError("process is required for template lookup.")
    template_usecase_id = _normalize_str(_cfg_value(cfg, "run.clearml.template_usecase_id"))
    usecase_id = template_usecase_id or _normalize_str(_cfg_value(cfg, "run.usecase_id"))
    schema_version = _normalize_str(_cfg_value(cfg, "run.schema_version"))

    project_name = _template_project_name(cfg, process_name)
    base_tags = ["template:true", f"process:{process_name}"]
    candidates: list[list[str]] = []
    if usecase_id:
        tags = [*base_tags, f"usecase:{usecase_id}"]
        if schema_version:
            tags.append(f"schema:{schema_version}")
        candidates.append(tags)
    if schema_version:
        candidates.append([*base_tags, f"schema:{schema_version}"])
    candidates.append(list(base_tags))

    expected_spec = resolve_clearml_script_spec(
        cfg,
        task_name_override=process_name,
        canonicalize_pipeline=False,
    )
    required_tags = list(base_tags)
    if _SOLUTION_TAG:
        required_tags.append(_SOLUTION_TAG)
    if usecase_id:
        required_tags.append(f"usecase:{usecase_id}")
    if schema_version:
        required_tags.append(f"schema:{schema_version}")
    for tags in candidates:
        tasks = list_clearml_tasks_by_tags(tags, project_name=project_name)
        for task in tasks:
            task_tags = clearml_task_tags(task)
            if "template:deprecated" in task_tags:
                continue
            status = (clearml_task_status_from_obj(task) or "").lower()
            if status and status != "created":
                continue
            if any(required not in task_tags for required in required_tags):
                continue
            script = clearml_task_script(task)
            if clearml_script_mismatches(expected_spec, script):
                continue
            task_id = clearml_task_id(task)
            if task_id:
                return task_id

    message = (
        f"Template task not found for process={process_name}. "
        "Run python -m tabular_analysis.ops.manage_clearml_templates --apply to create templates."
    )
    raise RuntimeError(message)
