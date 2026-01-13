"""Manage ClearML template tasks for local server (plan/apply/validate)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Iterable, Optional

from ..clearml import template_manager
from ..platform_adapter import (
    clearml_script_mismatches,
    clearml_task_id,
    clearml_task_script,
    clearml_task_status_from_obj,
    clearml_task_tags,
    create_clearml_task,
    detect_git_branch,
    detect_git_repository_url,
    ensure_clearml_task_args,
    ensure_clearml_task_properties,
    ensure_clearml_task_requirements,
    ensure_clearml_task_script,
    ensure_clearml_task_tags,
    get_clearml_task_args,
    get_clearml_task_script,
    list_clearml_tasks_by_tags,
    resolve_clearml_code_ref_mode,
    resolve_clearml_script_spec,
    update_clearml_task_tags,
)

try:
    from omegaconf import OmegaConf  # type: ignore
except Exception:  # pragma: no cover - optional in some environments
    OmegaConf = None

_OBSOLETE_TAGS = {"template:deprecated", "obsolete:true"}


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


def _find_tag(tags: Iterable[str], prefix: str) -> str | None:
    for tag in tags:
        if str(tag).startswith(prefix):
            return str(tag)
    return None


def _is_obsolete(tags: Iterable[str]) -> bool:
    return any(tag in _OBSOLETE_TAGS for tag in tags)


def _task_script_summary(script: dict[str, Any]) -> str:
    repo = str(script.get("repository") or "none")
    branch = str(script.get("branch") or "none")
    entry = str(script.get("entry_point") or script.get("entrypoint") or "none")
    return f"repo={repo} branch={branch} entry_point={entry}"


def _load_code_ref_mode(repo_root: Path, override: str | None) -> str:
    if override:
        return resolve_clearml_code_ref_mode(None, override=str(override))
    if OmegaConf is None:
        return "branch"
    run_cfg_path = repo_root / "conf" / "run" / "base.yaml"
    if not run_cfg_path.exists():
        return "branch"
    try:
        cfg = OmegaConf.load(run_cfg_path)
    except Exception:
        return "branch"
    return resolve_clearml_code_ref_mode(cfg)


def _build_script_cfg(version_mode: str | None) -> dict[str, Any]:
    cfg: dict[str, Any] = {"run": {"clearml": {"code_ref": {}}}}
    if version_mode:
        cfg["run"]["clearml"]["code_ref"]["mode"] = version_mode
    return cfg


def _resolve_target_script_spec(
    *,
    target: template_manager.TemplateTarget,
    repo: str | None,
    branch: str | None,
    version_mode: str | None,
) -> Any:
    cfg = _build_script_cfg(version_mode)
    return resolve_clearml_script_spec(
        cfg,
        entry_point_override=target.entry_point,
        repo_override=repo,
        branch_override=branch,
        version_mode_override=version_mode,
        task_name_override=target.name,
        canonicalize_pipeline=False,
    )


def _collect_candidate_tasks(
    target: template_manager.TemplateTarget,
    *,
    order_by: Iterable[str] | None = None,
) -> list[Any]:
    candidates = template_manager.build_tag_candidates(target.tags, target.name)
    tasks: list[Any] = []
    seen: set[str] = set()
    for tags in candidates:
        for task in list_clearml_tasks_by_tags(tags, project_name=target.project_name, order_by=order_by):
            task_id = clearml_task_id(task)
            if task_id and task_id in seen:
                continue
            if task_id:
                seen.add(task_id)
            tasks.append(task)
    return tasks


def _deprecate_template_task(task_id: str, *, reason: str) -> None:
    try:
        update_clearml_task_tags(
            task_id,
            add=["template:deprecated", "obsolete:true"],
            remove=["template:true"],
        )
        print(f"[deprecated] {task_id}: {reason}")
    except Exception as exc:
        print(f"[warn] failed to deprecate {task_id}: {exc}")


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
    print(f"template_set_id: {ctx.template_set_id}")
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
    version_mode: str | None,
) -> None:
    for target in targets:
        spec = _resolve_target_script_spec(
            target=target,
            repo=repo,
            branch=branch,
            version_mode=version_mode,
        )
        candidate_tasks = _collect_candidate_tasks(target, order_by=["-last_update"])
        selected_task_id: str | None = None
        superseded_task_ids: list[str] = []
        for task in candidate_tasks:
            task_id = clearml_task_id(task)
            if not task_id:
                continue
            tags = clearml_task_tags(task)
            if _is_obsolete(tags):
                continue
            status = (clearml_task_status_from_obj(task) or "").lower()
            if status and status != "created":
                _deprecate_template_task(task_id, reason=f"status={status}")
                continue
            script = clearml_task_script(task)
            missing_tags = [tag for tag in target.tags if tag not in tags]
            tag_mismatches = []
            if missing_tags:
                tag_mismatches.append(f"missing tags: {', '.join(missing_tags)}")
            script_mismatches = clearml_script_mismatches(spec, script)
            mismatches = [*tag_mismatches, *script_mismatches]
            if mismatches:
                if script_mismatches:
                    try:
                        ensure_clearml_task_script(
                            task_id,
                            repo=spec.repository,
                            branch=spec.branch,
                            entry_point=spec.entry_point,
                            working_dir=spec.working_dir,
                            version_num=spec.version_num,
                            diff="",
                        )
                    except Exception as exc:
                        _deprecate_template_task(task_id, reason=f"script update failed: {exc}")
                        continue
                    script = get_clearml_task_script(task_id)
                    script_mismatches = clearml_script_mismatches(spec, script)
                    mismatches = [*tag_mismatches, *script_mismatches]
                if mismatches:
                    _deprecate_template_task(task_id, reason=", ".join(mismatches))
                    continue
            if selected_task_id is None:
                selected_task_id = task_id
                changes: list[str] = []
                if ensure_clearml_task_script(
                    task_id,
                    repo=spec.repository,
                    branch=spec.branch,
                    entry_point=spec.entry_point,
                    working_dir=spec.working_dir,
                    version_num=spec.version_num,
                    diff="",
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
            else:
                print(f"[info] {target.name}: additional template found {task_id}")
                superseded_task_ids.append(task_id)

        if selected_task_id is None:
            task_id = create_clearml_task(
                project_name=target.project_name,
                task_name=target.task_name,
                module=target.module,
                script=target.script,
                args=target.args,
                repo=spec.repository,
                branch=spec.branch,
                tags=target.tags,
                properties=target.properties,
                requirements=target.requirements,
            )
            ensure_clearml_task_script(
                task_id,
                repo=spec.repository,
                branch=spec.branch,
                entry_point=spec.entry_point,
                working_dir=spec.working_dir,
                version_num=spec.version_num,
                diff="",
            )
            print(f"[create] {target.name}: {task_id}")
        else:
            for task_id in superseded_task_ids:
                _deprecate_template_task(task_id, reason="superseded by current template_set")


def _list_templates(targets: list[template_manager.TemplateTarget]) -> None:
    print("ClearML template list")
    for target in targets:
        print(f"- {target.name}")
        candidate_tasks = _collect_candidate_tasks(target, order_by=["-last_update"])
        if not candidate_tasks:
            print("  [missing] no template tasks found")
            continue
        for task in candidate_tasks:
            task_id = clearml_task_id(task) or "unknown"
            status = clearml_task_status_from_obj(task) or "unknown"
            tags = clearml_task_tags(task)
            template_set = _find_tag(tags, "template_set:") or "template_set:unknown"
            state = "obsolete" if _is_obsolete(tags) else "candidate"
            script = clearml_task_script(task)
            print(
                f"  [{state}] {task_id} status={status} {template_set} {_task_script_summary(script)}"
            )


def _cleanup_obsolete_templates(targets: list[template_manager.TemplateTarget]) -> None:
    print("ClearML template cleanup")
    for target in targets:
        current_set = _find_tag(target.tags, "template_set:")
        if not current_set:
            print(f"- {target.name}: template_set tag is missing; skipped")
            continue
        base_tags = ["template:true", f"process:{target.name}"]
        for prefix in ("usecase:", "schema:", "solution:"):
            tag = _find_tag(target.tags, prefix)
            if tag:
                base_tags.append(tag)
        tasks = list_clearml_tasks_by_tags(base_tags, project_name=target.project_name)
        for task in tasks:
            task_id = clearml_task_id(task)
            if not task_id:
                continue
            tags = clearml_task_tags(task)
            if _is_obsolete(tags):
                continue
            task_set = _find_tag(tags, "template_set:")
            if task_set == current_set:
                continue
            reason = "template_set missing" if not task_set else f"template_set={task_set}"
            _deprecate_template_task(task_id, reason=reason)


def _validate_templates(
    targets: list[template_manager.TemplateTarget],
    *,
    repo: str | None,
    branch: str | None,
    version_mode: str | None,
) -> bool:
    ok = True
    repo_root = _resolve_repo_root()
    for target in targets:
        spec = _resolve_target_script_spec(
            target=target,
            repo=repo,
            branch=branch,
            version_mode=version_mode,
        )
        candidate_tasks = _collect_candidate_tasks(target)
        if not candidate_tasks:
            print(f"[missing] {target.name}: template task not found")
            ok = False
            continue
        found_valid = False
        had_invalid = False
        for task in candidate_tasks:
            task_id = clearml_task_id(task)
            if not task_id:
                continue
            tags = clearml_task_tags(task)
            if _is_obsolete(tags):
                continue
            errors: list[str] = []
            missing_tags = [tag for tag in target.tags if tag not in tags]
            if missing_tags:
                errors.append(f"missing tags: {', '.join(missing_tags)}")

            script = clearml_task_script(task)
            errors.extend(clearml_script_mismatches(spec, script))

            expected_args = _args_to_map(target.args)
            actual_args = get_clearml_task_args(task_id)
            for key, value in expected_args.items():
                if str(actual_args.get(key, "")) != value:
                    errors.append(f"arg mismatch: {key}={value}")

            if errors:
                had_invalid = True
                ok = False
                print(f"[invalid] {target.name}: {task_id} ({', '.join(errors)})")
                continue
            print(f"[ok] {target.name}: {task_id}")
            found_valid = True
            break
        if not found_valid and not had_invalid:
            print(f"[missing] {target.name}: no matching template found")
            ok = False
    return ok


def main(argv: Optional[list[str]] = None) -> int:
    repo_root = _resolve_repo_root()
    parser = argparse.ArgumentParser(
        description="Manage ClearML template tasks (plan/apply/validate)."
    )
    parser.add_argument("--spec", default=str(repo_root / "conf" / "clearml" / "templates.yaml"))
    parser.add_argument("--plan", action="store_true", help="Print template list (no ClearML needed).")
    parser.add_argument("--list", action="store_true", help="List template candidates on ClearML.")
    parser.add_argument("--apply", action="store_true", help="Create/update template tasks on ClearML.")
    parser.add_argument("--validate", action="store_true", help="Validate template tasks on ClearML.")
    parser.add_argument(
        "--cleanup-obsolete",
        action="store_true",
        help="Tag obsolete templates that are outside the current template_set.",
    )
    parser.add_argument("--project-root", default=None, help="Override ClearML project root.")
    parser.add_argument("--usecase-id", default=None, help="Override usecase_id placeholder.")
    parser.add_argument("--schema-version", default=None, help="Override schema_version placeholder.")
    parser.add_argument("--template-set-id", default=None, help="Override template_set_id placeholder.")
    parser.add_argument("--repo", default=None, help="Override ClearML repository URL.")
    parser.add_argument("--branch", default=None, help="Override ClearML repository branch.")
    parser.add_argument(
        "--code-version-mode",
        default=None,
        help="Override run.clearml.code_ref.mode (branch|commit|none; legacy: branch_head|pin_commit).",
    )

    args = parser.parse_args(argv)

    if not args.plan and not args.list and not args.apply and not args.validate and not args.cleanup_obsolete:
        parser.error("Select one of --plan, --list, --apply, --validate, --cleanup-obsolete")

    defaults = template_manager.load_default_context(repo_root)
    ctx = template_manager.TemplateContext(
        project_root=str(args.project_root or defaults.project_root),
        usecase_id=str(args.usecase_id or defaults.usecase_id),
        schema_version=str(args.schema_version or defaults.schema_version),
        template_set_id=str(args.template_set_id or defaults.template_set_id),
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

    repo = args.repo or detect_git_repository_url(repo_root)
    branch = args.branch or detect_git_branch(repo_root)
    version_mode = _load_code_ref_mode(repo_root, args.code_version_mode)
    if not repo:
        print("Warning: repository not detected; pass --repo for agent clone.")
    print(f"code_ref.mode: {version_mode}")

    ok = True
    if args.list:
        _list_templates(targets)
    if args.apply:
        _apply_templates(targets, repo=repo, branch=branch, version_mode=version_mode)
    if args.cleanup_obsolete:
        _cleanup_obsolete_templates(targets)
    if args.validate:
        ok = _validate_templates(targets, repo=repo, branch=branch, version_mode=version_mode)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
