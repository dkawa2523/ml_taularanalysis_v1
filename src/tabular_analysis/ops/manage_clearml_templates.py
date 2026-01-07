"""Manage ClearML template tasks for local server (plan/apply/validate)."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from ..clearml import template_manager
from ..platform_adapter import (
    create_clearml_task,
    ensure_clearml_task_args,
    ensure_clearml_task_properties,
    ensure_clearml_task_requirements,
    ensure_clearml_task_script,
    ensure_clearml_task_tags,
    find_clearml_task_id_by_tags,
    get_clearml_task_args,
    get_clearml_task_script,
    get_clearml_task_tags,
)


def _resolve_repo_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for base in candidates:
        for parent in [base, *base.parents]:
            if (parent / "conf").exists():
                return parent
    return Path(__file__).resolve().parents[3]


def _clearml_config_present(repo_root: Path) -> bool:
    env_path = os.getenv("CLEARML_CONFIG_FILE")
    if env_path:
        if Path(env_path).expanduser().exists():
            return True
    for key in ("CLEARML_API_ACCESS_KEY", "CLEARML_API_SECRET_KEY", "CLEARML_API_HOST", "CLEARML_WEB_HOST"):
        if os.getenv(key):
            return True
    for candidate in (
        repo_root / "clearml.conf",
        Path.home() / "clearml.conf",
        Path.home() / ".clearml.conf",
        Path.home() / ".config" / "clearml.conf",
    ):
        if candidate.exists():
            return True
    return False


def _detect_repo_url(repo_root: Path) -> str | None:
    candidates = [
        ["git", "config", "--get", "remote.origin.url"],
        ["git", "remote", "get-url", "origin"],
    ]
    for cmd in candidates:
        proc = subprocess.run(
            cmd,
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode == 0:
            value = proc.stdout.strip()
            if value:
                return value
    return None


def _detect_branch(repo_root: Path) -> str | None:
    cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    if not value or value == "HEAD":
        return None
    return value


def _normalize_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_entry_point(value: Optional[str]) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    parts = text.split()
    if parts and parts[0] in {"python", "python3"}:
        parts = parts[1:]
    return " ".join(parts)


def _args_to_map(args: Iterable[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in args:
        text = str(item).strip()
        if not text:
            continue
        if "=" not in text:
            raise ValueError(f"override must be key=value: {text}")
        key, value = text.split("=", 1)
        parsed[str(key)] = str(value)
    return parsed


def _find_template_task_id(target: template_manager.TemplateTarget) -> str | None:
    candidates = template_manager.build_tag_candidates(target.tags, target.name)
    for tags in candidates:
        task_id = find_clearml_task_id_by_tags(tags, project_name=target.project_name)
        if task_id:
            return task_id
    return None


def _print_plan(
    ctx: template_manager.TemplateContext,
    spec_path: Path,
    targets: list[template_manager.TemplateTarget],
) -> None:
    print("ClearML template plan")
    print(f"spec: {spec_path}")
    print(f"project_root: {ctx.project_root}")
    print(f"usecase_id: {ctx.usecase_id}")
    print(f"schema_version: {ctx.schema_version}")
    print("")
    for target in targets:
        print(f"- {target.name}")
        print(f"  project_name: {target.project_name}")
        print(f"  task_name: {target.task_name}")
        print(f"  entrypoint: {target.entrypoint}")
        print(f"  args: {', '.join(target.args)}")
        print(f"  tags: {', '.join(target.tags)}")
        print("")


def _apply_templates(
    targets: list[template_manager.TemplateTarget],
    *,
    repo: str | None,
    branch: str | None,
) -> None:
    for target in targets:
        task_id = _find_template_task_id(target)
        if not task_id:
            task_id = create_clearml_task(
                project_name=target.project_name,
                task_name=target.task_name,
                module=target.module,
                script=target.script,
                args=target.args,
                repo=repo,
                branch=branch,
                tags=target.tags,
                properties=target.properties,
                requirements=target.requirements,
            )
            ensure_clearml_task_script(
                task_id,
                repo=repo,
                branch=branch,
                entry_point=target.entry_point,
                working_dir=None,
            )
            print(f"[create] {target.name}: {task_id}")
            continue

        changes: list[str] = []
        if ensure_clearml_task_script(
            task_id,
            repo=repo,
            branch=branch,
            entry_point=target.entry_point,
            working_dir=None,
        ):
            changes.append("script")
        if ensure_clearml_task_tags(task_id, target.tags):
            changes.append("tags")
        if ensure_clearml_task_requirements(task_id, target.requirements):
            changes.append("requirements")
        if ensure_clearml_task_properties(task_id, target.properties):
            changes.append("properties")
        if ensure_clearml_task_args(task_id, target.args):
            changes.append("args")
        if changes:
            print(f"[update] {target.name}: {', '.join(changes)}")
        else:
            print(f"[skip] {target.name}: no changes")


def _validate_templates(
    targets: list[template_manager.TemplateTarget],
    *,
    repo: str | None,
    branch: str | None,
) -> bool:
    ok = True
    for target in targets:
        task_id = _find_template_task_id(target)
        if not task_id:
            print(f"[missing] {target.name}: template task not found")
            ok = False
            continue
        errors: list[str] = []
        tags = get_clearml_task_tags(task_id)
        missing_tags = [tag for tag in target.tags if tag not in tags]
        if missing_tags:
            errors.append(f"missing tags: {', '.join(missing_tags)}")

        script = get_clearml_task_script(task_id)
        entry_point = _normalize_entry_point(script.get("entry_point"))
        expected_entry = _normalize_entry_point(target.entry_point)
        if expected_entry and entry_point != expected_entry:
            errors.append(f"entry_point mismatch: {entry_point or 'none'}")
        if repo:
            repo_value = _normalize_text(script.get("repository"))
            if repo_value != _normalize_text(repo):
                errors.append(f"repository mismatch: {repo_value or 'none'}")
        if branch:
            branch_value = _normalize_text(script.get("branch"))
            if branch_value != _normalize_text(branch):
                errors.append(f"branch mismatch: {branch_value or 'none'}")

        expected_args = _args_to_map(target.args)
        actual_args = get_clearml_task_args(task_id)
        for key, value in expected_args.items():
            if str(actual_args.get(key, "")) != value:
                errors.append(f"arg mismatch: {key}={value}")

        if errors:
            ok = False
            print(f"[invalid] {target.name}: {', '.join(errors)}")
        else:
            print(f"[ok] {target.name}: {task_id}")
    return ok


def main(argv: Optional[list[str]] = None) -> int:
    repo_root = _resolve_repo_root()
    parser = argparse.ArgumentParser(
        description="Manage ClearML template tasks (plan/apply/validate)."
    )
    parser.add_argument("--spec", default=str(repo_root / "conf" / "clearml" / "templates.yaml"))
    parser.add_argument("--plan", action="store_true", help="Print template list (no ClearML needed).")
    parser.add_argument("--apply", action="store_true", help="Create/update template tasks on ClearML.")
    parser.add_argument("--validate", action="store_true", help="Validate template tasks on ClearML.")
    parser.add_argument("--project-root", default=None, help="Override ClearML project root.")
    parser.add_argument("--usecase-id", default=None, help="Override usecase_id placeholder.")
    parser.add_argument("--schema-version", default=None, help="Override schema_version placeholder.")
    parser.add_argument("--repo", default=None, help="Override ClearML repository URL.")
    parser.add_argument("--branch", default=None, help="Override ClearML repository branch.")

    args = parser.parse_args(argv)

    if not args.plan and not args.apply and not args.validate:
        parser.error("Select one of --plan, --apply, --validate")

    defaults = template_manager.load_default_context(repo_root)
    ctx = template_manager.TemplateContext(
        project_root=str(args.project_root or defaults.project_root),
        usecase_id=str(args.usecase_id or defaults.usecase_id),
        schema_version=str(args.schema_version or defaults.schema_version),
    )
    spec_path = Path(args.spec)
    if not spec_path.is_absolute():
        spec_path = (repo_root / spec_path).resolve()
    specs = template_manager.load_template_specs(spec_path, ctx)
    targets = template_manager.resolve_template_targets(specs, ctx)

    if args.plan:
        _print_plan(ctx, spec_path, targets)
        return 0

    if not _clearml_config_present(repo_root):
        print("ClearML config not detected; run clearml-init or set CLEARML_CONFIG_FILE.")
        return 1

    repo = args.repo or _detect_repo_url(repo_root)
    branch = args.branch or _detect_branch(repo_root)
    if not repo:
        print("Warning: repository not detected; pass --repo for agent clone.")

    if args.apply:
        _apply_templates(targets, repo=repo, branch=branch)
        return 0

    if args.validate:
        ok = _validate_templates(targets, repo=repo, branch=branch)
        return 0 if ok else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
