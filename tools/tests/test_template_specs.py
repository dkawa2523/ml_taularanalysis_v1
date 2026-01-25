#!/usr/bin/env python3
"""Spec validation for ClearML template tasks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from omegaconf import OmegaConf

REQUIRED_TEMPLATES = {
    "dataset_register",
    "preprocess",
    "train_model",
    "infer",
    "leaderboard",
    "pipeline",
}

REQUIRED_FIELDS = {
    "project_name",
    "task_name_template",
    "entrypoint",
    "default_overrides",
    "tags",
    "properties_minimal",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    data = OmegaConf.to_container(OmegaConf.load(path), resolve=False)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise RuntimeError(f"YAML root must be a mapping: {path}")
    return dict(data)


def _load_stage_map(repo: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in (repo / "conf" / "task").glob("*.yaml"):
        payload = _load_yaml(path)
        task_cfg = payload.get("task") if isinstance(payload.get("task"), dict) else None
        task_name = None
        stage = None
        if task_cfg:
            task_name = task_cfg.get("name")
            stage = task_cfg.get("stage")
        if not task_name:
            task_name = path.stem
        if not stage:
            continue
        mapping[str(task_name)] = str(stage)
    return mapping


def _assert_contains(items: list[str], prefix: str) -> None:
    for item in items:
        if item.startswith(prefix):
            return
    raise AssertionError(f"Missing tag prefix: {prefix}")


def _assert_overrides(overrides: list[str]) -> None:
    if "run.clearml.enabled=true" not in overrides:
        raise AssertionError("default_overrides must include run.clearml.enabled=true")
    if not any(item.startswith("run.clearml.execution=") for item in overrides):
        raise AssertionError("default_overrides must include run.clearml.execution=...")


def _validate_spec(repo: Path) -> None:
    spec_path = repo / "conf" / "clearml" / "templates.yaml"
    if not spec_path.exists():
        raise FileNotFoundError(f"Spec file missing: {spec_path}")
    payload = _load_yaml(spec_path)
    templates = payload.get("templates")
    if not isinstance(templates, dict):
        raise AssertionError("templates must be a mapping")

    template_names = set(str(name) for name in templates.keys())
    missing = REQUIRED_TEMPLATES - template_names
    if missing:
        raise AssertionError(f"Missing templates: {sorted(missing)}")

    stage_map = _load_stage_map(repo)
    for name, spec in templates.items():
        if not isinstance(spec, dict):
            raise AssertionError(f"template {name} must be a mapping")
        for field in REQUIRED_FIELDS:
            if field not in spec:
                raise AssertionError(f"template {name} missing field: {field}")
        project_name = str(spec.get("project_name"))
        task_name = str(spec.get("task_name_template"))
        entrypoint = str(spec.get("entrypoint"))
        overrides = list(spec.get("default_overrides") or [])
        tags = [str(item) for item in (spec.get("tags") or [])]
        props = spec.get("properties_minimal")

        if not project_name:
            raise AssertionError(f"template {name} project_name empty")
        if not task_name:
            raise AssertionError(f"template {name} task_name_template empty")
        if not entrypoint:
            raise AssertionError(f"template {name} entrypoint empty")
        if not isinstance(props, dict):
            raise AssertionError(f"template {name} properties_minimal must be a mapping")

        if "clearml_entrypoint.py" not in entrypoint or f"task={name}" not in entrypoint:
            raise AssertionError(f"template {name} entrypoint must include task={name}")

        _assert_overrides([str(item) for item in overrides])
        _assert_contains(tags, "usecase:")
        _assert_contains(tags, f"process:{name}")
        _assert_contains(tags, "schema:")

        for key in ("usecase_id", "process", "schema_version"):
            if key not in props:
                raise AssertionError(f"template {name} missing properties_minimal.{key}")

        stage = stage_map.get(name)
        if stage and stage not in project_name:
            raise AssertionError(f"template {name} project_name should include stage {stage}")


def _run_plan(repo: Path) -> None:
    cmd = [sys.executable, str(repo / "tools" / "clearml_templates" / "manage_templates.py"), "--plan"]
    proc = subprocess.run(cmd, cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"plan failed (exit={proc.returncode})\n{proc.stdout}")

    plan_json = repo / "artifacts" / "template_plan.json"
    plan_md = repo / "artifacts" / "template_plan.md"
    if not plan_json.exists():
        raise AssertionError("template_plan.json not created")
    if not plan_md.exists():
        raise AssertionError("template_plan.md not created")

    payload = json.loads(plan_json.read_text(encoding="utf-8"))
    template_names = {item.get("name") for item in payload.get("templates", [])}
    missing = REQUIRED_TEMPLATES - template_names
    if missing:
        raise AssertionError(f"plan missing templates: {sorted(missing)}")

    md_text = plan_md.read_text(encoding="utf-8")
    for name in REQUIRED_TEMPLATES:
        if name not in md_text:
            raise AssertionError(f"plan markdown missing {name}")


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    _validate_spec(repo)
    _run_plan(repo)
    print("OK: template specs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
