#!/usr/bin/env python3
"""Inspect ClearML tasks for a usecase id."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tabular_analysis import platform_adapter

_PROCESS_ORDER = [
    "dataset_register",
    "preprocess",
    "train_model",
    "train_ensemble",
    "leaderboard",
    "infer",
    "pipeline",
]


def _process_from_tags(tags: Iterable[str]) -> str:
    for tag in tags:
        if tag.startswith("process:"):
            return tag.split(":", 1)[1]
    return "unknown"


def _task_name(task: object) -> str:
    return (
        str(getattr(task, "name", None) or getattr(task, "task_name", None) or "").strip()
    )


def _list_tasks(usecase_id: str) -> tuple[list[object] | None, str | None]:
    try:
        tasks = platform_adapter.list_clearml_tasks_by_tags(
            [f"usecase:{usecase_id}"], allow_archived=True, order_by=["-last_update"]
        )
    except platform_adapter.PlatformAdapterError as exc:
        return None, str(exc)
    return list(tasks), None


def _print_pipeline_failure(tasks: Iterable[object]) -> None:
    for task in tasks:
        status = platform_adapter.clearml_task_status_from_obj(task) or ""
        if "failed" not in status.lower():
            continue
        script = platform_adapter.clearml_task_script(task)
        print("  pipeline failed: script pin")
        print(f"    repository: {script.get('repository') or 'none'}")
        print(f"    branch: {script.get('branch') or 'none'}")
        print(f"    entry_point: {script.get('entry_point') or 'none'}")
        print(f"    version_num: {script.get('version_num') or 'none'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect ClearML tasks for a usecase id.")
    parser.add_argument("--usecase-id", required=True, help="Target usecase id (tags).")
    args = parser.parse_args(argv)

    tasks, err = _list_tasks(args.usecase_id)
    if tasks is None:
        print(f"[warn] ClearML query skipped: {err}")
        return 0

    print(f"usecase_id: {args.usecase_id}")
    if not tasks:
        print("No ClearML tasks found.")
        return 0

    grouped: dict[str, list[object]] = {}
    for task in tasks:
        tags = platform_adapter.clearml_task_tags(task)
        process = _process_from_tags(tags)
        grouped.setdefault(process, []).append(task)

    ordered = [*[_p for _p in _PROCESS_ORDER if _p in grouped], *sorted(set(grouped) - set(_PROCESS_ORDER))]
    for process in ordered:
        task_list = grouped.get(process, [])
        if not task_list:
            continue
        print(f"- {process}")
        for task in task_list:
            task_id = platform_adapter.clearml_task_id(task) or "unknown"
            status = platform_adapter.clearml_task_status_from_obj(task) or "unknown"
            name = _task_name(task)
            if name:
                print(f"  {status:10} {task_id} {name}")
            else:
                print(f"  {status:10} {task_id}")
        if process == "pipeline":
            _print_pipeline_failure(task_list)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
