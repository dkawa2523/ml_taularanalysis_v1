"""Scan installed ml_platform package and print a small API summary.

目的:
- Solution 側が platform API 名を推測しすぎて迷走するのを防ぐ
- platform_adapter.py の candidates 更新を支援する

使い方:
  python tools/codex_loop/platform_scan.py > work/platform_api_summary.txt
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from types import ModuleType


def safe_import(name: str) -> ModuleType | None:
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def main() -> int:
    mod = safe_import("ml_platform")
    if mod is None:
        print("ml_platform is not importable. Install ml_platform first.")
        return 1

    print(f"ml_platform module: {mod!r}")
    try:
        import importlib.metadata as md

        ver = md.version("ml-platform")
        print(f"dist version (ml-platform): {ver}")
    except Exception:
        pass

    pkg_path = getattr(mod, "__path__", None)
    if pkg_path is None:
        print("ml_platform has no __path__ (not a package?)")
        return 0

    print("\n== Top-level submodules ==")
    for m in sorted({p.name for p in pkgutil.iter_modules(pkg_path)}):
        print("-", m)

    print("\n== Candidate init_task locations ==")
    candidates = [
        "ml_platform.utils",
        "ml_platform.clearml.task_factory",
        "ml_platform.integrations.clearml.task_factory",
        "ml_platform.artifacts.manifest",
        "ml_platform.artifacts.hashes",
    ]
    for name in candidates:
        m = safe_import(name)
        if m is None:
            print(f"- {name}: (import failed)")
            continue
        keys = [k for k in dir(m) if any(s in k.lower() for s in ["init", "manifest", "hash", "out", "artifact"])][:50]
        print(f"- {name}: {keys}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
