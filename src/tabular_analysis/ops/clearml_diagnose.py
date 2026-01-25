"""ClearML diagnostics for template resolution and queue hygiene."""

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
    list_clearml_tasks_by_tags,
    normalize_clearml_entry_point,
    normalize_clearml_repository,
    resolve_clearml_script_spec,
)


def _resolve_repo_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for base in candidates:
        for parent in [base, *base.parents]:
            if (parent / "conf").exists():
                return parent
    return Path.cwd()


def _resolve_config_dir(explicit: Optional[str]) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"--config-dir does not exist: {path}")
        return path
    env = Path.cwd() / "conf"
    if env.exists():
        return env
    fallback = Path(__file__).resolve().parents[2] / "conf"
    if fallback.exists():
        return fallback
    raise FileNotFoundError("conf/ directory was not found. Run from repository root or set --config-dir.")


def _compose_config(config_dir: Path, config_name: str, overrides: Iterable[str]):
    from hydra import compose, initialize_config_dir  # type: ignore

    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        return compose(config_name=config_name, overrides=list(overrides))


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


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _task_script_summary(script: dict[str, Any]) -> str:
    repo = normalize_clearml_repository(script.get("repository")) or "none"
    branch = _normalize_str(script.get("branch")) or "none"
    entry = normalize_clearml_entry_point(script.get("entry_point")) or "none"
    version = _normalize_str(script.get("version_num")) or ""
    version_text = version if version else "branch_head"
    return f"repo={repo} branch={branch} entry_point={entry} version={version_text}"


def _report_templates(
    cfg: Any,
    *,
    repo_override: str | None,
    branch_override: str | None,
    version_mode_override: str | None,
) -> None:
    repo_root = _resolve_repo_root()
    defaults = template_manager.load_default_context(repo_root)
    ctx = template_manager.TemplateContext(
        project_root=str(defaults.project_root),
        usecase_id=str(defaults.usecase_id),
        schema_version=str(defaults.schema_version),
        solution_root=str(defaults.solution_root),
        group_map=dict(defaults.group_map),
    )
    spec_path = repo_root / "conf" / "clearml" / "templates.yaml"
    specs = template_manager.load_template_specs(spec_path, ctx)
    targets = template_manager.resolve_template_targets(specs, ctx)

    print("Template diagnostics")
    for target in targets:
        try:
            spec = resolve_clearml_script_spec(
                cfg,
                entry_point_override=target.entry_point,
                repo_override=repo_override,
                branch_override=branch_override,
                version_mode_override=version_mode_override,
                task_name_override=target.name,
                canonicalize_pipeline=False,
            )
        except Exception as exc:
            print(f"- {target.name}")
            print(f"  [error] failed to resolve script spec: {exc}")
            continue
        expected_summary = (
            f"repo={normalize_clearml_repository(spec.repository) or 'none'} "
            f"branch={_normalize_str(spec.branch) or 'none'} "
            f"entry_point={normalize_clearml_entry_point(spec.entry_point) or 'none'} "
            f"version_policy={spec.version_policy} "
            f"version_num={spec.version_num or ''}"
        )
        print(f"- {target.name}")
        print(f"  expected: {expected_summary}")

        candidates = template_manager.build_tag_candidates(target.tags, target.name)
        tasks: list[Any] = []
        seen: set[str] = set()
        for tags in candidates:
            for task in list_clearml_tasks_by_tags(tags, project_name=target.project_name):
                task_id = clearml_task_id(task)
                if task_id and task_id in seen:
                    continue
                if task_id:
                    seen.add(task_id)
                tasks.append(task)
        if not tasks:
            print("  [missing] no template tasks found")
            continue

        selected_task_id: str | None = None
        for task in tasks:
            task_id = clearml_task_id(task) or "unknown"
            tags = clearml_task_tags(task)
            status = clearml_task_status_from_obj(task) or "unknown"
            script = clearml_task_script(task)
            missing_tags = [tag for tag in target.tags if tag not in tags]
            tag_mismatches = []
            if missing_tags:
                tag_mismatches.append(f"missing tags: {', '.join(missing_tags)}")
            script_mismatches = clearml_script_mismatches(spec, script)
            mismatches = [*tag_mismatches, *script_mismatches]
            deprecated = "template:deprecated" in tags
            if not mismatches and not deprecated and selected_task_id is None:
                selected_task_id = task_id
                print(f"  [ok] {task_id} status={status} {_task_script_summary(script)}")
                continue
            reason = ", ".join(mismatches) if mismatches else "deprecated"
            label = "deprecated" if deprecated else "mismatch"
            print(f"  [{label}] {task_id} status={status} {_task_script_summary(script)} ({reason})")

        if selected_task_id is None:
            print("  [missing] no matching template found")


def _scan_queue(queue_name: str, expected_repo: str | None) -> None:
    try:
        from clearml import Task  # type: ignore
    except Exception as exc:
        print(f"[queue] clearml import failed: {exc}")
        return
    getter = getattr(Task, "get_queue_id", None)
    if not callable(getter):
        print("[queue] Task.get_queue_id not available; queue scan skipped.")
        return
    try:
        queue_id = getter(queue_name)
    except Exception as exc:
        print(f"[queue] queue lookup failed ({queue_name}): {exc}")
        return
    if not queue_id:
        print(f"[queue] queue not found: {queue_name}")
        return
    try:
        tasks = Task.get_tasks(task_filter={"status": ["queued"], "queue": [queue_id]})
    except Exception as exc:
        print(f"[queue] task listing failed ({queue_name}): {exc}")
        return
    expected_norm = normalize_clearml_repository(expected_repo) if expected_repo else None
    mismatched: list[str] = []
    for task in tasks or []:
        task_id = clearml_task_id(task) or "unknown"
        script = clearml_task_script(task)
        repo = normalize_clearml_repository(script.get("repository"))
        if expected_norm and repo and repo != expected_norm:
            mismatched.append(f"{task_id} repo={repo}")
    if not mismatched:
        print(f"[queue] {queue_name}: no queued tasks referencing a different repo.")
        return
    print(f"[queue] {queue_name}: tasks referencing a different repo")
    for item in mismatched:
        print(f"  - {item}")
    print("  UI steps: ClearML UI -> Queues -> select queue -> remove the listed tasks.")


def main(argv: Optional[list[str]] = None) -> int:
    repo_root = _resolve_repo_root()
    parser = argparse.ArgumentParser(description="Diagnose ClearML templates and queued tasks.")
    parser.add_argument("--config-dir", type=str, default=None, help="Path to conf/ directory.")
    parser.add_argument("--config-name", type=str, default="config", help="Hydra config name.")
    parser.add_argument("--repo", type=str, default=None, help="Override expected repository URL.")
    parser.add_argument("--branch", type=str, default=None, help="Override expected branch.")
    parser.add_argument(
        "--code-ref-mode",
        type=str,
        default=None,
        help="Override run.clearml.code_ref.mode (branch|commit|none).",
    )
    parser.add_argument(
        "--code-version-mode",
        type=str,
        default=None,
        help="Override run.clearml.code_version_mode (legacy: branch_head|pin_commit).",
    )
    parser.add_argument("--queue", action="append", default=[], help="Queue name to scan for stale tasks.")
    parser.add_argument("--force", action="store_true", help="Enable destructive actions (not used).")
    args, overrides = parser.parse_known_args(argv)

    if not _clearml_config_present(repo_root):
        print("ClearML config not detected; diagnose requires ClearML credentials.")
        return 1

    cfg = _compose_config(_resolve_config_dir(args.config_dir), args.config_name, overrides)

    _report_templates(
        cfg,
        repo_override=args.repo,
        branch_override=args.branch,
        version_mode_override=args.code_ref_mode or args.code_version_mode,
    )

    if args.queue:
        try:
            spec = resolve_clearml_script_spec(
                cfg,
                repo_override=args.repo,
                branch_override=args.branch,
                version_mode_override=args.code_ref_mode or args.code_version_mode,
            )
        except Exception as exc:
            print(f"[queue] failed to resolve script spec: {exc}")
            spec = None
        expected_repo = args.repo or normalize_clearml_repository(
            spec.repository if spec is not None else None
        )
        for queue_name in args.queue:
            if queue_name:
                _scan_queue(str(queue_name), expected_repo)

    if args.force:
        print("Note: destructive operations are not implemented; use the UI to dequeue/abort tasks.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
