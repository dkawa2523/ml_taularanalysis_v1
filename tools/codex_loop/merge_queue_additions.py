#!/usr/bin/env python3
"""Merge queue_additions JSON into work/queue.json.

This repo has evolved over multiple ZIP overlays; queue schema may vary slightly.
We try to be conservative:

- If both queue and additions have a top-level "tasks" list, append unique tasks by id.
- If the queue file is a plain list, treat it as the tasks list.

Usage:
  python tools/codex_loop/merge_queue_additions.py --queue work/queue.json --add work/queue_additions_T051_T055.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _extract_tasks(obj: Any) -> tuple[list[dict], str | None]:
    """Return (tasks, container_key).

    container_key is "tasks" if obj is dict with tasks; None if obj itself is list.
    """
    if isinstance(obj, list):
        return obj, None
    if isinstance(obj, dict) and isinstance(obj.get("tasks"), list):
        return obj["tasks"], "tasks"
    raise ValueError("Unsupported queue format: expected list or dict with 'tasks' list")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", required=True)
    ap.add_argument("--add", required=True)
    args = ap.parse_args()

    q_path = Path(args.queue)
    a_path = Path(args.add)

    q_obj = _load(q_path)
    a_obj = _load(a_path)

    q_tasks, q_key = _extract_tasks(q_obj)
    a_tasks, _ = _extract_tasks(a_obj)

    existing = {t.get("id") for t in q_tasks if isinstance(t, dict)}
    merged = list(q_tasks)
    appended = 0
    for t in a_tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        if tid and tid not in existing:
            merged.append(t)
            existing.add(tid)
            appended += 1

    if q_key is None:
        _dump(q_path, merged)
    else:
        q_obj[q_key] = merged
        _dump(q_path, q_obj)

    print(f"Merged {appended} tasks into {q_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
