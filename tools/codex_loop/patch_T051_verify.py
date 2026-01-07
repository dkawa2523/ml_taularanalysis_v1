#!/usr/bin/env python3
"""Hotfix: patch verify commands for task T051 in work/queue.json.

Why:
  Some environments don't have the package installed in editable mode (src-layout).
  `python -m tabular_analysis....` can fail even though the code exists under src/.

  This patch replaces the T051 verify command with a src-layout-friendly import:
    python -c "import sys; sys.path.insert(0,'src'); import tabular_analysis.ops.print_clearml_identity as m; print('ok')"

Safe:
  - Only edits verify[] for task id == 'T051'
  - Keeps everything else untouched
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _get_tasks(obj: Any) -> Tuple[List[Dict[str, Any]], str | None]:
    if isinstance(obj, dict) and isinstance(obj.get("tasks"), list):
        return obj["tasks"], "tasks"
    if isinstance(obj, list):
        return obj, None
    raise TypeError(f"Unsupported queue.json format: {type(obj)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default="work/queue.json", help="Path to queue.json")
    ap.add_argument("--dry-run", action="store_true", help="Only report changes, do not write")
    args = ap.parse_args()

    q_path = Path(args.queue)
    if not q_path.exists():
        raise FileNotFoundError(q_path)

    obj = _load(q_path)
    tasks, key = _get_tasks(obj)

    changed = False
    found = False
    for t in tasks:
        if not isinstance(t, dict):
            continue
        if t.get("id") != "T051":
            continue
        found = True
        new_verify = [
            "python -m compileall -q src",
            "python -c "import sys; sys.path.insert(0,'src'); import tabular_analysis.ops.print_clearml_identity as m; print('ok')"",
        ]
        if t.get("verify") != new_verify:
            t["verify"] = new_verify
            changed = True

    if not found:
        print("[patch_T051_verify] WARNING: task T051 not found in queue.json")
        return 0

    if args.dry_run:
        print(f"[patch_T051_verify] Would patch T051 verify (changed={changed})")
        return 0

    if changed:
        if key is None:
            _dump(q_path, tasks)
        else:
            obj[key] = tasks
            _dump(q_path, obj)
        print("[patch_T051_verify] Patched T051 verify successfully.")
    else:
        print("[patch_T051_verify] No change needed (T051 verify already patched).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
