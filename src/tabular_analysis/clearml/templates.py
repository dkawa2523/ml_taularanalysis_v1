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
    "promote_model": "06_promote_model",
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
    template_usecase = _normalize_str(_cfg_value(cfg, "run.clearml.template_usecase_id"))
    if not template_usecase:
        template_usecase = _normalize_str(_cfg_value(cfg, "run.clearml.project_layout.solution_root"))
    if not template_usecase:
        template_usecase = _normalize_str(_cfg_value(cfg, "run.usecase_id")) or "unknown"
    return f"{project_root}/{template_usecase}/{stage}"


def resolve_template_task_id(cfg: Any, process: str) -> str:
    process_name = _normalize_str(process)
    if not process_name:
        raise ValueError("process is required for template lookup.")
    template_usecase_id = _normalize_str(_cfg_value(cfg, "run.clearml.template_usecase_id"))
    template_set_id = _normalize_str(_cfg_value(cfg, "run.clearml.template_set_id"))
    usecase_id = template_usecase_id or _normalize_str(_cfg_value(cfg, "run.usecase_id"))
    schema_version = _normalize_str(_cfg_value(cfg, "run.schema_version"))

    project_name = _template_project_name(cfg, process_name)
    base_tags = ["template:true", f"process:{process_name}"]
    if template_set_id:
        base_tags.append(f"template_set:{template_set_id}")
    if _SOLUTION_TAG:
        base_tags.append(_SOLUTION_TAG)
    candidates: list[list[str]] = []
    usecase_candidates = []
    if usecase_id:
        usecase_candidates.append(usecase_id)
    run_usecase = _normalize_str(_cfg_value(cfg, "run.usecase_id"))
    if run_usecase and run_usecase not in usecase_candidates:
        usecase_candidates.append(run_usecase)
    for value in usecase_candidates:
        tags = [*base_tags, f"usecase:{value}"]
        if schema_version:
            candidates.append([*tags, f"schema:{schema_version}"])
        candidates.append(tags)
    if schema_version:
        candidates.append([*base_tags, f"schema:{schema_version}"])
    candidates.append(list(base_tags))

    expected_spec = resolve_clearml_script_spec(
        cfg,
        task_name_override=process_name,
        canonicalize_pipeline=False,
    )
    for tags in candidates:
        tasks = list_clearml_tasks_by_tags(tags, project_name=project_name)
        matches: list[str] = []
        for task in tasks:
            task_tags = clearml_task_tags(task)
            if "template:deprecated" in task_tags or "obsolete:true" in task_tags:
                continue
            status = (clearml_task_status_from_obj(task) or "").lower()
            if status and status != "created":
                continue
            if any(required not in task_tags for required in tags):
                continue
            script = clearml_task_script(task)
            if clearml_script_mismatches(expected_spec, script):
                continue
            task_id = clearml_task_id(task)
            if task_id:
                matches.append(task_id)
        if not matches:
            continue
        if len(matches) > 1:
            raise RuntimeError(
                "Multiple ClearML templates found for process="
                f"{process_name}: {', '.join(matches)}"
            )
        return matches[0]

    message = (
        f"Template task not found for process={process_name}. "
        "Run python -m tabular_analysis.ops.manage_clearml_templates --apply to create templates."
    )
    raise RuntimeError(message)
