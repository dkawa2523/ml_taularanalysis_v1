#!/usr/bin/env python3
"""Codex loop runner (Solution-side) - v2.

この runner は、Codex CLI を使って `work/queue.json` のタスクを順番に実行し、
verify が通った場合のみ `work/state.json` を `done` に更新します。

v2 で強化した点（ユーザ課題の再発防止）
- **lock**: 多重起動で state が壊れるのを防ぐ
- **in_progress 自動復旧**: 中断により in_progress のまま止まる問題を解消
- **保護ファイル検知**: work/queue.json / work/state.json / work/tasks/** が Codex に編集されると失敗
- **反復ループ化**: 再帰をやめ、オプションを保持したまま連続実行
- **（任意）git clean 強制**: dirty 状態が must_change 判定を壊す事故を防ぐ

注意
- Codex CLI の起動方法は環境差があるため、`tools/codex_loop/runtime.json` を編集してください。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# -------------------------
# JSON helpers (atomic)
# -------------------------


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# -------------------------
# Queue / State
# -------------------------


@dataclass
class QueueTask:
    id: str
    title: str
    md: str
    deps: List[str]
    must_change_globs: List[str]
    verify: List[str]


@dataclass
class Queue:
    version: int
    solution: str
    tasks: List[QueueTask]


def load_queue(repo: Path) -> Queue:
    qpath = repo / "work/queue.json"
    if not qpath.exists():
        raise FileNotFoundError(f"queue.json not found: {qpath}")
    obj = read_json(qpath)
    tasks = [
        QueueTask(
            id=t["id"],
            title=t["title"],
            md=t["md"],
            deps=t.get("deps", []),
            must_change_globs=t.get("must_change_globs", []),
            verify=t.get("verify", []),
        )
        for t in obj.get("tasks", [])
    ]
    return Queue(version=int(obj.get("version", 1)), solution=str(obj.get("solution", "")), tasks=tasks)


def load_state(repo: Path, queue: Queue) -> dict:
    spath = repo / "work/state.json"
    if spath.exists():
        state = read_json(spath)
    else:
        state = {"version": 1, "tasks": {}}

    tasks_state = state.setdefault("tasks", {})
    for t in queue.tasks:
        tasks_state.setdefault(t.id, {"status": "todo"})

    # clean up unknown tasks (queue から消えたタスク)
    for k in list(tasks_state.keys()):
        if k not in {t.id for t in queue.tasks}:
            tasks_state.pop(k, None)

    write_json_atomic(spath, state)
    return state


def save_state(repo: Path, state: dict) -> None:
    write_json_atomic(repo / "work/state.json", state)


def task_status(state: dict, task_id: str) -> str:
    return state.get("tasks", {}).get(task_id, {}).get("status", "todo")


def is_done(state: dict, task_id: str) -> bool:
    return task_status(state, task_id) == "done"


def is_runnable(state: dict, task_id: str) -> bool:
    return task_status(state, task_id) in {"todo", "failed"}


def next_runnable_task(queue: Queue, state: dict, only_task_id: Optional[str] = None) -> Optional[QueueTask]:
    tasks = queue.tasks
    if only_task_id:
        tasks = [t for t in tasks if t.id == only_task_id]
    for t in tasks:
        if not is_runnable(state, t.id):
            continue
        if any(not is_done(state, dep) for dep in t.deps):
            continue
        return t
    return None


# -------------------------
# Lock
# -------------------------


def lock_path(repo: Path) -> Path:
    return repo / "work" / ".codex_lock.json"


def acquire_lock(repo: Path, *, force: bool) -> None:
    lp = lock_path(repo)
    if lp.exists() and not force:
        # Best-effort: stale lock detection (crash-safe)
        try:
            info_obj = read_json(lp)
            pid = int(info_obj.get("pid", -1))
        except Exception:
            info_obj = None
            pid = -1

        if pid > 0 and os.name != "nt":
            try:
                # signal 0: existence check
                os.kill(pid, 0)
                # If no exception, process exists -> treat as locked
                info = lp.read_text(encoding="utf-8")
                raise RuntimeError(
                    "[codex_loop] Lock file exists. Another runner may be running.\n"
                    f"Lock: {lp}\n\n{info}\n\n"
                    "If you are sure no runner is running, re-run with --force-lock."
                )
            except PermissionError:
                info = lp.read_text(encoding="utf-8")
                raise RuntimeError(
                    "[codex_loop] Lock file exists (permission denied to check pid).\n"
                    f"Lock: {lp}\n\n{info}\n\n"
                    "If you are sure no runner is running, re-run with --force-lock."
                )
            except ProcessLookupError:
                # stale lock -> override
                print(f"[codex_loop] WARN: stale lock detected (pid={pid}). overriding lock.")
        else:
            info = lp.read_text(encoding="utf-8")
            raise RuntimeError(
                "[codex_loop] Lock file exists. Another runner may be running, or the previous run crashed.\n"
                f"Lock: {lp}\n\n{info}\n\n"
                "If you are sure no runner is running, re-run with --force-lock."
            )
    obj = {
        "pid": os.getpid(),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "repo": str(repo),
    }
    lp.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(lp, obj)


def release_lock(repo: Path) -> None:
    lp = lock_path(repo)
    if lp.exists():
        try:
            lp.unlink()
        except Exception:
            pass


# -------------------------
# Git helpers (optional)
# -------------------------


def has_git(repo: Path) -> bool:
    return (repo / ".git").exists()


def git_status_porcelain(repo: Path) -> str:
    code, out = run_subprocess(["bash", "-lc", "git status --porcelain"], cwd=repo)
    if code != 0:
        return ""
    return out.strip()


# -------------------------
# File hashing (must_change & protected)
# -------------------------


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expand_globs(repo: Path, patterns: List[str]) -> List[Path]:
    files: List[Path] = []
    for pat in patterns:
        for p in repo.glob(pat):
            if p.is_file():
                if ".venv" in p.parts or "__pycache__" in p.parts:
                    continue
                files.append(p)
    seen: set[Path] = set()
    uniq: List[Path] = []
    for p in files:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        uniq.append(p)
    return uniq


def snapshot_hashes(repo: Path, patterns: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in expand_globs(repo, patterns):
        try:
            out[str(p)] = sha256_file(p)
        except Exception:
            out[str(p)] = "<unreadable>"
    return out


def snapshot_files(repo: Path, patterns: List[str], snapshot_dir: Path) -> List[Tuple[Path, Path]]:
    """Copy matched files into snapshot_dir, preserving relative paths.

    Returns a list of (src, dst) pairs.
    """
    copied: List[Tuple[Path, Path]] = []
    files = expand_globs(repo, patterns)
    for src in files:
        rel = src.relative_to(repo)
        dst = snapshot_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append((src, dst))
    return copied


def restore_snapshot(repo: Path, snapshot_dir: Path) -> None:
    """Restore files from snapshot_dir back into repo."""
    if not snapshot_dir.exists():
        return
    for src in snapshot_dir.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(snapshot_dir)
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def changed_keys(before: Dict[str, str], after: Dict[str, str]) -> List[str]:
    keys = set(before.keys()) | set(after.keys())
    changed: List[str] = []
    for k in sorted(keys):
        if before.get(k) != after.get(k):
            changed.append(k)
    return changed


def protected_globs() -> List[str]:
    # 進捗と指示書は runner の整合性のため “不変” 扱い
    return [
        "work/queue.json",
        "work/state.json",
        "work/tasks/**",
    ]


# -------------------------
# Prompt / runtime / codex invocation
# -------------------------


def load_runtime(repo: Path) -> dict:
    rpath = repo / "tools/codex_loop/runtime.json"
    if not rpath.exists():
        raise FileNotFoundError(
            f"runtime.json not found: {rpath}\n"
            "-> run: bash tools/codex_loop/selfcheck_codex_exec.sh (and edit runtime.json if needed)"
        )
    return read_json(rpath)


def runtime_guard_no_prompt_file(runtime: dict) -> None:
    """Fail fast if runtime args include an unsupported flag.

    User env reports: `codex exec` in some builds does NOT accept `--prompt-file`.
    If the runtime template was accidentally edited to include that flag, we
    stop here with a clear error instead of letting Codex CLI fail later.
    """

    tokens: List[str] = []
    for a in runtime.get("cmd", []) + runtime.get("args", []):
        if isinstance(a, str):
            tokens.append(a)

    if any("--prompt-file" in t for t in tokens):
        raise ValueError(
            "runtime.json contains '--prompt-file', but your Codex CLI build does not support it.\n"
            "Fix: remove --prompt-file and pass prompt as positional [PROMPT], or use the bundled wrapper:\n"
            "  cmd: ['bash','tools/codex_loop/codex_exec.sh']\n"
            "  args: ['default','{prompt_file}']\n"
        )


def build_prompt(repo: Path, task: QueueTask, run_dir: Path, *, extra: str = "") -> str:
    """Build a compact prompt.

    IMPORTANT:
    - Some Codex CLI builds do NOT support a --prompt-file flag.
      This runner therefore prefers passing the prompt as a positional argument
      (see runtime.json.template) and keeps the prompt reasonably small.
    - We do NOT embed the full CODEX_GUIDE or the full task markdown here.
      Codex should open and read them from disk to avoid OS command-length limits.
    """

    # Keep repo context short to reduce command-length issues on macOS.
    tree_hint = "\n".join(
        [
            "conf/  (Hydra configs)",
            "src/tabular_analysis/  (implementation)",
            "docs/  (spec/contract)",
            "work/tasks/  (task specs - DO NOT EDIT)",
            "tools/codex_loop/  (runner)",
        ]
    )

    memo = ""
    last_failure = repo / "work/last_failure.md"
    if last_failure.exists():
        # Keep the memo bounded to avoid prompt bloat.
        memo = last_failure.read_text(encoding="utf-8")
        if len(memo) > 8000:
            memo = memo[:8000] + "\n... (truncated)\n"

    prompt = f"""
# Codex Task Runner (compact prompt)

You are Codex CLI. Edit the repository to complete the next task.

Repo root: {repo}
Task: {task.id} {task.title}
Run dir (logs): {run_dir}

READ THESE FILES (do not edit them):
- work/CODEX_GUIDE.md
- {task.md}

NON-NEGOTIABLE RULES:
- Do NOT modify: work/queue.json, work/state.json, work/tasks/**
- Do NOT modify the Platform repo. Only this Solution repo.
- Keep all Platform dependencies inside: src/tabular_analysis/platform_adapter.py
- Do not break the UI contract: docs/03_CLEARML_UI_CONTRACT.md
- Make ALL verification commands pass (defined in work/queue.json for this task).

Repo structure hint:
{tree_hint}

If you need platform APIs, inspect the installed `ml_platform` via Python, and update
platform_adapter accordingly. Prefer reusing ml_platform (P201-P204) features.

Previous failure memo (if any):
{memo}

{extra}
"""
    return prompt.strip() + "\n"


def render_cmd(runtime: dict, *, prompt_file: Path, repo: Path) -> Tuple[List[str], List[str]]:
    """Render the codex command.

    Returns (cmd, cmd_for_log).

    Supported placeholders in runtime.json:
    - {repo}
    - {prompt_file}
    - {prompt}  (preferred; expanded to the prompt text)

    If neither {prompt} nor {prompt_file} is present, we append the prompt as
    the last positional argument.
    """

    cmd = runtime.get("cmd")
    args = runtime.get("args", [])
    if not isinstance(cmd, list) or not cmd:
        raise ValueError("runtime.json: cmd must be a non-empty list")
    if not isinstance(args, list):
        raise ValueError("runtime.json: args must be a list")

    prompt_text = prompt_file.read_text(encoding="utf-8")

    rendered: List[str] = []
    rendered_log: List[str] = []

    has_prompt_placeholder = False
    has_prompt_file_placeholder = False

    for a in cmd + args:
        if not isinstance(a, str):
            raise ValueError("runtime.json: cmd/args items must be strings")

        if "{prompt}" in a:
            has_prompt_placeholder = True

        if "{prompt_file}" in a:
            has_prompt_file_placeholder = True

    for a in cmd + args:
        a = str(a)
        a = a.replace("{repo}", str(repo))
        if a == "{prompt}":
            rendered.append(prompt_text)
            rendered_log.append("<PROMPT>")
            continue
        if "{prompt}" in a:
            # Avoid embedding prompt inside another token; treat as positional.
            a = a.replace("{prompt}", "")
        if a == "{prompt_file}":
            rendered.append(str(prompt_file))
            rendered_log.append(str(prompt_file))
            continue
        a = a.replace("{prompt_file}", str(prompt_file))
        rendered.append(a)
        rendered_log.append(a)

    if not has_prompt_placeholder and not has_prompt_file_placeholder:
        # Most Codex CLI builds accept PROMPT as the final positional argument.
        rendered.append(prompt_text)
        rendered_log.append("<PROMPT>")

    return rendered, rendered_log


def run_subprocess(
    cmd: List[str],
    *,
    cwd: Path,
    env: Optional[Dict[str, str]] = None,
    timeout_sec: Optional[int] = None,
) -> Tuple[int, str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update({k: str(v) for k, v in env.items()})

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_sec,
        )
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as e:
        return 124, f"TIMEOUT: {e}\n"


# -------------------------
# Verification
# -------------------------


def run_verify(repo: Path, commands: List[str], run_dir: Path) -> Tuple[bool, str]:
    logs: List[str] = []
    for i, c in enumerate(commands, start=1):
        logs.append(f"\n$ ({i}/{len(commands)}) {c}\n")
        code, out = run_subprocess(["bash", "-lc", c], cwd=repo)
        logs.append(out)
        if code != 0:
            logs.append(f"\n[verify] FAILED (exit={code})\n")
            (run_dir / "verify_failed.txt").write_text("".join(logs), encoding="utf-8")
            return False, "".join(logs)
    (run_dir / "verify_ok.txt").write_text("".join(logs), encoding="utf-8")
    return True, "".join(logs)


# -------------------------
# Misc: state recovery / status
# -------------------------


def reset_in_progress(state: dict) -> int:
    """in_progress を failed に倒す（中断復旧）。"""
    n = 0
    for tid, obj in state.get("tasks", {}).items():
        if obj.get("status") == "in_progress":
            obj["status"] = "failed"
            obj["note"] = "auto-reset from in_progress (previous run interrupted)"
            n += 1
    return n


def print_status(queue: Queue, state: dict) -> None:
    rows = []
    for t in queue.tasks:
        s = task_status(state, t.id)
        rows.append((t.id, s, t.title))
    print("\n".join([f"{a}\t{b}\t{c}" for a, b, c in rows]))


# -------------------------
# Main
# -------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Repository root")
    parser.add_argument("--once", action="store_true", help="Run only one task")
    parser.add_argument("--dry-run", action="store_true", help="Do not invoke codex; just show next runnable task")
    parser.add_argument("--task-id", default=None, help="Run a specific task id")
    parser.add_argument("--max-retries", type=int, default=1, help="Retry count when verification fails")
    parser.add_argument("--reset-in-progress", action="store_true", help="Reset tasks stuck in in_progress to failed")
    parser.add_argument("--status", action="store_true", help="Print task status and exit")
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="Fail if git working tree is dirty (optional safety rail)",
    )
    parser.add_argument("--force-lock", action="store_true", help="Ignore lock file and proceed")
    parser.add_argument(
        "--no-preverify-failed",
        dest="preverify_failed",
        action="store_false",
        help="Disable pre-verify for failed tasks (default: enabled).",
    )
    parser.set_defaults(preverify_failed=True)
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    queue = load_queue(repo)
    state = load_state(repo, queue)

    # Auto-recovery: if the previous run was interrupted, tasks can remain "in_progress" forever.
    # We proactively fold them back to "failed" so the next run can retry.
    n_auto = reset_in_progress(state)
    if n_auto:
        save_state(repo, state)
        print(f"[codex_loop] auto-reset {n_auto} in_progress task(s) -> failed")

    # If the user only wanted recovery, exit here.
    if args.reset_in_progress:
        return 0

    if args.status:
        print_status(queue, state)
        return 0

    # Optional safety rail: require clean working tree
    if args.require_clean and has_git(repo):
        dirty = git_status_porcelain(repo)
        if dirty:
            print("[codex_loop] ERROR: git working tree is dirty.", file=sys.stderr)
            print(dirty, file=sys.stderr)
            return 2

    if args.dry_run:
        t = next_runnable_task(queue, state, only_task_id=args.task_id)
        if t is None:
            print("[codex_loop] No runnable tasks. All done?")
            return 0
        print(f"[codex_loop] Next task: {t.id} {t.title}")
        return 0

    # Acquire lock for the whole run
    try:
        acquire_lock(repo, force=args.force_lock)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2

    try:
        runtime = load_runtime(repo)
        runtime_guard_no_prompt_file(runtime)
        timeout_sec = runtime.get("timeout_sec")
        env = runtime.get("env", {})

        max_retries = max(0, int(args.max_retries))

        # Main loop
        while True:
            task = next_runnable_task(queue, state, only_task_id=args.task_id)
            if task is None:
                print("[codex_loop] No runnable tasks. All done?")
                return 0

            prev_status = task_status(state, task.id)
            print(f"[codex_loop] Running: {task.id} {task.title}")

            # Mark in_progress
            state["tasks"][task.id]["status"] = "in_progress"
            state["tasks"][task.id]["started_at"] = datetime.now().isoformat(timespec="seconds")
            save_state(repo, state)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir = repo / "work" / "runs" / f"{ts}_{task.id}"
            run_dir.mkdir(parents=True, exist_ok=True)

            # Pre-verify for reruns: if a task previously failed but is already satisfied, skip Codex.
            if getattr(args, "preverify_failed", True) and prev_status == "failed" and task.verify:
                pv_ok, pv_log = run_verify(repo, task.verify, run_dir)
                # keep preverify logs separate from post-codex verify logs
                ok_path = run_dir / "verify_ok.txt"
                fail_path = run_dir / "verify_failed.txt"
                if pv_ok and ok_path.exists():
                    ok_path.rename(run_dir / "preverify_ok.txt")
                if (not pv_ok) and fail_path.exists():
                    fail_path.rename(run_dir / "preverify_failed.txt")
                if pv_ok:
                    state["tasks"][task.id]["status"] = "done"
                    state["tasks"][task.id]["last_run"] = str(run_dir)
                    state["tasks"][task.id]["finished_at"] = datetime.now().isoformat(timespec="seconds")
                    save_state(repo, state)
                    lf = repo / "work/last_failure.md"
                    if lf.exists():
                        lf.unlink()
                    print(f"[codex_loop] PREVERIFY OK: {task.id} already satisfied; skipping codex.")
                    if args.once or args.task_id:
                        return 0
                    continue

            # Snapshots
            before_must = snapshot_hashes(repo, task.must_change_globs)
            before_protected = snapshot_hashes(repo, protected_globs())
            protected_snapshot_dir = run_dir / "protected_snapshot"
            # 保存しておくことで、Codex が誤って progress/指示書を編集した場合でも自動で復旧できる
            snapshot_files(repo, protected_globs(), protected_snapshot_dir)
            (run_dir / "must_change_before.json").write_text(json.dumps(before_must, ensure_ascii=False, indent=2), encoding="utf-8")
            (run_dir / "protected_before.json").write_text(json.dumps(before_protected, ensure_ascii=False, indent=2), encoding="utf-8")

            prompt = build_prompt(repo, task, run_dir)
            prompt_file = run_dir / "prompt.md"
            prompt_file.write_text(prompt, encoding="utf-8")

            last_stdout = ""
            ok = False

            for attempt in range(1, max_retries + 2):
                cmd, cmd_for_log = render_cmd(runtime, prompt_file=prompt_file, repo=repo)
                (run_dir / f"codex_cmd_{attempt}.txt").write_text(" ".join(cmd_for_log) + "\n", encoding="utf-8")

                # Helpful console log for debugging (prompt is masked as <PROMPT>)
                print(f"[codex_loop] Codex cmd: {' '.join(cmd_for_log)}")

                code, out = run_subprocess(cmd, cwd=repo, env=env, timeout_sec=timeout_sec)
                last_stdout = out
                (run_dir / f"codex_stdout_{attempt}.txt").write_text(out, encoding="utf-8")

                if code != 0:
                    (repo / "work" / "last_failure.md").write_text(
                        f"# Last failure\n\nTask: {task.id} {task.title}\nAttempt: {attempt}\n\nCodex command exited with {code}.\n\n`````\n{out}\n`````\n",
                        encoding="utf-8",
                    )
                    continue

                # Protected files check (Codex が触ると進捗が壊れる)
                after_protected = snapshot_hashes(repo, protected_globs())
                protected_changed = changed_keys(before_protected, after_protected)
                (run_dir / "protected_after.json").write_text(json.dumps(after_protected, ensure_ascii=False, indent=2), encoding="utf-8")
                (run_dir / "protected_changed.txt").write_text("\n".join(protected_changed) + "\n", encoding="utf-8")
                if protected_changed:
                    msg = "Protected files were modified by Codex (this is not allowed):\n" + "\n".join(protected_changed)
                    # 自動復旧（progress/指示書の破壊は非常に影響が大きいため）
                    restore_snapshot(repo, protected_snapshot_dir)
                    (repo / "work" / "last_failure.md").write_text(
                        f"# Last failure\n\nTask: {task.id} {task.title}\nAttempt: {attempt}\n\n{msg}\n",
                        encoding="utf-8",
                    )
                    continue

                # must_change check
                after_must = snapshot_hashes(repo, task.must_change_globs)
                changed = changed_keys(before_must, after_must)
                (run_dir / "must_change_after.json").write_text(json.dumps(after_must, ensure_ascii=False, indent=2), encoding="utf-8")
                (run_dir / "must_change_changed.txt").write_text("\n".join(changed) + "\n", encoding="utf-8")
                if task.must_change_globs and not changed:
                    msg = (
                        f"must_change_globs に該当するファイルが変更されていません: {task.must_change_globs} "
                        f"(task may already be satisfied; continuing to verify)"
                    )
                    (run_dir / "must_change_warning.txt").write_text(msg + "\n", encoding="utf-8")
                    print(f"[codex_loop] WARN: {msg}")

                # verify
                v_ok, v_log = run_verify(repo, task.verify, run_dir)
                if v_ok:
                    ok = True
                    break
                (repo / "work" / "last_failure.md").write_text(
                    f"# Last failure\n\nTask: {task.id} {task.title}\nAttempt: {attempt}\n\nVerification failed.\n\n`````\n{v_log}\n`````\n",
                    encoding="utf-8",
                )

            if ok:
                state["tasks"][task.id]["status"] = "done"
                state["tasks"][task.id]["last_run"] = str(run_dir)
                state["tasks"][task.id]["finished_at"] = datetime.now().isoformat(timespec="seconds")
                save_state(repo, state)
                lf = repo / "work/last_failure.md"
                if lf.exists():
                    lf.unlink()
                print(f"[codex_loop] DONE: {task.id} {task.title}")
                if args.once or args.task_id:
                    return 0
                continue

            # failed
            state["tasks"][task.id]["status"] = "failed"
            state["tasks"][task.id]["last_run"] = str(run_dir)
            state["tasks"][task.id]["last_stdout_tail"] = last_stdout[-2000:]
            state["tasks"][task.id]["finished_at"] = datetime.now().isoformat(timespec="seconds")
            save_state(repo, state)
            print(f"[codex_loop] FAILED: {task.id} {task.title} (see {run_dir})", file=sys.stderr)
            # Show quick failure hint (tail of last_failure.md) to reduce back-and-forth.
            lf = repo / "work" / "last_failure.md"
            if lf.exists():
                try:
                    txt = lf.read_text(encoding="utf-8")
                    tail = txt.splitlines()[-60:]
                    print("[codex_loop] ---- work/last_failure.md (tail) ----", file=sys.stderr)
                    print("\n".join(tail), file=sys.stderr)
                    print("[codex_loop] --------------------------------------", file=sys.stderr)
                except Exception:
                    pass
            return 1

    finally:
        release_lock(repo)


if __name__ == "__main__":
    raise SystemExit(main())
