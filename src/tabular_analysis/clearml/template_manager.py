"""ClearML template task specs and plan helpers."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from omegaconf import OmegaConf


@dataclass(frozen=True)
class TemplateContext:
    project_root: str
    usecase_id: str
    schema_version: str


@dataclass(frozen=True)
class TemplateSpec:
    name: str
    project_name: str
    task_name_template: str
    entrypoint: str
    default_overrides: list[str]
    requirements: list[str]
    tags: list[str]
    properties_minimal: dict[str, Any]


@dataclass(frozen=True)
class TemplateTarget:
    name: str
    project_name: str
    task_name: str
    entrypoint: str
    module: str | None
    script: str | None
    entry_point: str
    args: list[str]
    requirements: list[str]
    tags: list[str]
    properties: dict[str, Any]


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"YAML not found: {path}")
    data = OmegaConf.to_container(OmegaConf.load(path), resolve=False)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return dict(data)


def _format_value(value: Any, ctx: Mapping[str, Any]) -> Any:
    if isinstance(value, str):
        return value.format_map(_SafeFormatDict(ctx))
    if isinstance(value, list):
        return [_format_value(item, ctx) for item in value]
    if isinstance(value, dict):
        return {key: _format_value(val, ctx) for key, val in value.items()}
    return value


def _dedupe(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        if item is None:
            continue
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def load_default_context(repo_root: Path) -> TemplateContext:
    run_cfg_path = repo_root / "conf" / "run" / "base.yaml"
    if not run_cfg_path.exists():
        return TemplateContext(project_root="MFG", usecase_id="TabularAnalysis", schema_version="v1")
    cfg = OmegaConf.load(run_cfg_path)
    clearml_cfg = getattr(cfg, "clearml", None)
    project_root = getattr(clearml_cfg, "project_root", None) or "MFG"
    template_usecase_id = getattr(clearml_cfg, "template_usecase_id", None)
    usecase_id = template_usecase_id or getattr(cfg, "usecase_id", None) or "TabularAnalysis"
    schema_version = getattr(cfg, "schema_version", None) or "v1"
    return TemplateContext(
        project_root=str(project_root),
        usecase_id=str(usecase_id),
        schema_version=str(schema_version),
    )


def load_template_specs(spec_path: Path, ctx: TemplateContext) -> list[TemplateSpec]:
    raw = _load_yaml(spec_path)
    templates = raw.get("templates")
    if not isinstance(templates, dict):
        raise ValueError("templates must be a mapping")

    context = {
        "project_root": ctx.project_root,
        "usecase_id": ctx.usecase_id,
        "schema_version": ctx.schema_version,
    }
    specs: list[TemplateSpec] = []
    for name, payload in templates.items():
        if not isinstance(payload, dict):
            raise ValueError(f"template {name} must be a mapping")
        rendered = _format_value(payload, context)
        specs.append(
            TemplateSpec(
                name=str(name),
                project_name=str(rendered.get("project_name", "")),
                task_name_template=str(rendered.get("task_name_template", "")),
                entrypoint=str(rendered.get("entrypoint", "")),
                default_overrides=[str(item) for item in (rendered.get("default_overrides") or [])],
                requirements=normalize_requirements(rendered.get("requirements")),
                tags=[str(item) for item in (rendered.get("tags") or [])],
                properties_minimal=dict(rendered.get("properties_minimal") or {}),
            )
        )
    return specs


def parse_entrypoint(entrypoint: str) -> tuple[str | None, str | None, list[str], str]:
    parts = shlex.split(entrypoint)
    if not parts:
        raise ValueError("entrypoint is empty")
    if parts[0] in {"python", "python3"}:
        parts = parts[1:]
    if not parts:
        raise ValueError("entrypoint missing command")
    if parts[0] == "-m":
        if len(parts) < 2:
            raise ValueError("entrypoint module is missing")
        module = parts[1]
        args = parts[2:]
        entry_point = f"-m {module}"
        return (module, None, args, entry_point)
    script = parts[0]
    args = parts[1:]
    return (None, script, args, script)


def normalize_overrides(args: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for item in args:
        text = str(item).strip()
        if not text:
            continue
        if "=" not in text:
            raise ValueError(f"override must be key=value: {text}")
        normalized.append(text)
    return normalized


def normalize_requirements(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        items = [values]
    elif isinstance(values, list) or isinstance(values, tuple):
        items = list(values)
    else:
        raise ValueError("requirements must be a list or string")
    normalized: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        normalized.append(text)
    return normalized


def _find_tag(tags: Iterable[str], prefix: str) -> str | None:
    for tag in tags:
        if str(tag).startswith(prefix):
            return str(tag)
    return None


def build_tag_candidates(tags: Iterable[str], process: str) -> list[list[str]]:
    base = _dedupe(["template:true", f"process:{process}"])
    usecase_tag = _find_tag(tags, "usecase:")
    schema_tag = _find_tag(tags, "schema:")
    candidates: list[list[str]] = []
    if usecase_tag:
        variant = [*base, usecase_tag]
        if schema_tag:
            variant.append(schema_tag)
        candidates.append(_dedupe(variant))
    if schema_tag:
        candidates.append(_dedupe([*base, schema_tag]))
    candidates.append(base)
    return candidates


def resolve_template_targets(
    specs: Iterable[TemplateSpec],
    ctx: TemplateContext,
    *,
    solution_tag: str = "solution:tabular-analysis",
) -> list[TemplateTarget]:
    targets: list[TemplateTarget] = []
    for spec in specs:
        module, script, entry_args, entry_point = parse_entrypoint(spec.entrypoint)
        args = normalize_overrides([*entry_args, *spec.default_overrides])
        requirements = list(spec.requirements)
        tags = _dedupe(
            [
                "template:true",
                f"process:{spec.name}",
                solution_tag,
                *spec.tags,
            ]
        )
        properties = dict(spec.properties_minimal)
        properties.setdefault("usecase_id", ctx.usecase_id)
        properties.setdefault("process", spec.name)
        properties.setdefault("schema_version", ctx.schema_version)
        targets.append(
            TemplateTarget(
                name=spec.name,
                project_name=spec.project_name,
                task_name=spec.task_name_template,
                entrypoint=spec.entrypoint,
                module=module,
                script=script,
                entry_point=entry_point,
                args=args,
                requirements=requirements,
                tags=tags,
                properties=properties,
            )
        )
    return targets
