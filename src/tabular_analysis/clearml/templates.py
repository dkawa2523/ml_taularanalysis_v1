"""ClearML template task resolution helpers."""

from __future__ import annotations

from typing import Any, Mapping

from ..platform_adapter import find_clearml_task_id_by_tags

_STAGE_BY_PROCESS = {
    "dataset_register": "01_dataset_register",
    "preprocess": "02_preprocess",
    "train_model": "03_train_model",
    "infer": "04_infer",
    "leaderboard": "05_leaderboard",
    "promote_model": "06_promote_model",
    "pipeline": "99_pipeline",
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
    usecase_id = _normalize_str(_cfg_value(cfg, "run.usecase_id"))
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

    for tags in candidates:
        task_id = find_clearml_task_id_by_tags(tags, project_name=project_name)
        if task_id:
            return task_id

    message = (
        f"Template task not found for process={process_name}. "
        "Run python -m tabular_analysis.ops.manage_clearml_templates --apply to create templates."
    )
    raise RuntimeError(message)
