#!/usr/bin/env python3
"""Watch ClearML child task containers and persist docker logs.

Usage:
  python tools/clearml/watch_trial_logs.py --parent-task-id <TASK_ID> --log-dir /tmp/clearml_trial_logs
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict
import subprocess

from clearml.backend_api.session import Session


def _run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True, errors="ignore").strip()


def _docker_containers() -> list[tuple[str, str, str]]:
    try:
        output = _run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                "label=clearml-parent-worker-id=clearml-services",
                "--format",
                "{{.ID}} {{.Names}} {{.Labels}}",
            ]
        )
    except Exception:
        return []
    rows: list[tuple[str, str, str]] = []
    for line in output.splitlines():
        parts = line.split(" ", 2)
        if len(parts) != 3:
            continue
        rows.append((parts[0], parts[1], parts[2]))
    return rows


def _task_id_from_labels(labels: str) -> str | None:
    key = "clearml-worker-id=clearml-services:service:"
    if key not in labels:
        return None
    tail = labels.split(key, 1)[1]
    return tail.split(",", 1)[0] if tail else None


def _fetch_child_tasks(session: Session, parent_task_id: str) -> dict[str, str]:
    resp = session.send_request(
        "tasks",
        "get_all",
        version="2.23",
        json={
            "tags": [f"parent:{parent_task_id}"],
            "page": 0,
            "page_size": 500,
            "only_fields": ["id", "status"],
        },
    )
    if not resp.ok:
        return {}
    tasks = resp.json().get("data", {}).get("tasks", [])
    return {t.get("id"): t.get("status") for t in tasks if t.get("id")}


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch ClearML trial logs (docker).")
    parser.add_argument("--parent-task-id", required=True)
    parser.add_argument("--log-dir", default="/tmp/clearml_trial_logs")
    parser.add_argument("--tail", type=int, default=200)
    parser.add_argument("--poll-sec", type=int, default=10)
    parser.add_argument("--timeout-sec", type=int, default=900)
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    session = Session()
    seen: Dict[str, str] = {}
    start = time.time()

    while time.time() - start < args.timeout_sec:
        child_status = _fetch_child_tasks(session, args.parent_task_id)
        for cid, name, labels in _docker_containers():
            task_id = _task_id_from_labels(labels)
            if not task_id or task_id in seen:
                continue
            out_path = log_dir / f"trial_{task_id}.log"
            try:
                logs = _run(["docker", "logs", "--tail", str(args.tail), name])
                out_path.write_text(logs)
                seen[task_id] = child_status.get(task_id, "unknown")
            except Exception:
                continue

        # break early when parent finished and all children reported
        presp = session.send_request(
            "tasks",
            "get_by_id",
            version="2.23",
            json={"task": args.parent_task_id},
        )
        pstatus = presp.json().get("data", {}).get("task", {}).get("status") if presp.ok else "unknown"
        if pstatus in ("failed", "completed") and child_status:
            break
        time.sleep(args.poll_sec)

    # dump failed tails
    child_status = _fetch_child_tasks(session, args.parent_task_id)
    for task_id, status in child_status.items():
        if status != "failed":
            continue
        path = log_dir / f"trial_{task_id}.log"
        if not path.exists():
            print(f"failed_no_log {task_id}")
            continue
        tail = "\n".join(path.read_text(errors="ignore").splitlines()[-40:])
        print(f"--- tail {task_id} ---\n{tail}\n---")


if __name__ == "__main__":
    main()
