# 26_REPRODUCIBLE_RUNTIME (Env Snapshot and Lockfile Guide)

This document describes the runtime snapshot artifacts and lockfile workflow used to
improve reproducibility without changing existing dependency layouts.

## Env snapshot outputs
Each task captures a runtime snapshot during common initialization and writes:
- `env.json`: python version, OS/platform details, and solution version (git hash when available)
- `pip_freeze.txt`: `python -m pip freeze` output (fallbacks to `pip list --format=freeze` when needed)

These files are written under each task's run directory (for example:
`outputs/<stage>/env.json`, `outputs/<stage>/pip_freeze.txt`). When ClearML is enabled,
both files are uploaded as artifacts for UI traceability. When ClearML is disabled,
the upload step is a no-op but local files are still created.

## Lockfile workflow (optional)
`requirements/lock.txt` is an optional, environment-specific lockfile meant to capture
fully resolved dependencies without changing the existing `requirements/base.txt` layout.

### Update steps
1. Install (or update) the base requirements in your target environment:
   ```bash
   python -m pip install -r requirements/base.txt
   ```
2. If optional dependencies are needed, install them as well.
3. Freeze the resolved environment into the lockfile:
   ```bash
   python -m pip freeze > requirements/lock.txt
   ```

Keep `requirements/base.txt` (and optional lists) as the source of truth. The lockfile is
used for reproducible runs, CI snapshots, or forensic debugging when needed.
