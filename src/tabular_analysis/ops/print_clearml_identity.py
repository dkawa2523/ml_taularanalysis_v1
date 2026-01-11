"""Print ClearML identity preview for the composed config."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Optional

from .clearml_identity import resolve_clearml_identity, resolve_clearml_metadata


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


def _parse_now(value: Optional[str]) -> datetime | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in ("now", "utcnow"):
        return datetime.now(timezone.utc)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = None
    if parsed is not None:
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    for fmt in ("%Y%m%d_%H%M%S", "%Y-%m-%d_%H%M%S", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=timezone.utc)
    raise ValueError("Invalid --now; use ISO-8601 or YYYYmmdd_HHMMSS.")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Show ClearML project/tags/properties for the composed config."
    )
    parser.add_argument("--config-dir", type=str, default=None, help="Path to conf/ directory.")
    parser.add_argument("--config-name", type=str, default="config", help="Hydra config name.")
    parser.add_argument("--stage", type=str, default=None, help="Override task stage for project naming.")
    parser.add_argument("--task-name", type=str, default=None, help="Override task name for tags/properties.")
    parser.add_argument(
        "--now",
        type=str,
        default=None,
        help="Timestamp override for usecase_id generation (ISO-8601 or YYYYmmdd_HHMMSS).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args, overrides = parser.parse_known_args(argv)

    cfg = _compose_config(_resolve_config_dir(args.config_dir), args.config_name, overrides)
    try:
        now = _parse_now(args.now)
    except ValueError as exc:
        parser.error(str(exc))
    identity = resolve_clearml_identity(cfg, now=now)

    stage = args.stage or getattr(getattr(cfg, "task", None), "stage", None) or "unknown"
    task_name = args.task_name or getattr(getattr(cfg, "task", None), "name", None) or "task"

    metadata = resolve_clearml_metadata(
        cfg,
        stage=stage,
        task_name=task_name,
        identity=identity,
        clearml_enabled=False,
    )
    from .. import platform_adapter

    code_repo, code_branch = platform_adapter.resolve_clearml_code_reference(cfg)
    metadata["code_repository"] = code_repo
    metadata["code_branch"] = code_branch
    usecase_policy = getattr(getattr(cfg, "run", None), "usecase_id_policy", None)
    clearml_policy = getattr(getattr(getattr(cfg, "run", None), "clearml", None), "policy", None)
    metadata["policies"] = {
        "usecase_id_policy": getattr(usecase_policy, "name", None),
        "clearml_policy": getattr(clearml_policy, "name", None),
    }

    if args.json:
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return 0

    print(f"project_root: {metadata['project_root']}")
    print(f"project_name: {metadata['project_name']}")
    print(f"code_repository: {metadata.get('code_repository')}")
    print(f"code_branch: {metadata.get('code_branch')}")
    print(f"usecase_id: {metadata['usecase_id']}")
    print("tags:")
    for tag in metadata["tags"]:
        print(f"  - {tag}")
    print("user_properties:")
    for key, value in metadata["user_properties"].items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
