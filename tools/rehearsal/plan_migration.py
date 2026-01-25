#!/usr/bin/env python3
"""Print guidance for migrating ClearML rehearsal from local to internal."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class MigrationGuide:
    title: str
    checklist: Sequence[str]
    steps: Sequence[str]
    common_errors: Sequence[str]
    notes: Sequence[str]


def _print_section(title: str, lines: Iterable[str]) -> None:
    print()
    print(title)
    print("-" * len(title))
    for line in lines:
        print(f"- {line}")


def _render_guide(guide: MigrationGuide) -> None:
    print(guide.title)
    print("=" * len(guide.title))
    print()
    print("This script prints guidance only. It does not test connectivity.")
    _print_section("Difference checklist", guide.checklist)
    _print_section("Switch steps (trial phase)", guide.steps)
    _print_section("Common errors", guide.common_errors)
    if guide.notes:
        _print_section("Notes", guide.notes)


def _guides() -> dict[tuple[str, str], MigrationGuide]:
    return {
        ("local", "internal"): MigrationGuide(
            title="ClearML migration plan: local -> internal",
            checklist=[
                "ClearML endpoints (API/Web/Files) updated in clearml.conf or env.",
                "Artifacts storage reachable (files host or object storage), including large uploads.",
                "Dataset and model paths resolve in the agent environment (mounts/object store).",
                "Agent runtime parity: Python version, packages, OS libs, GPU drivers, container image.",
                "Permissions for project/task creation, cloning, reports, and artifact uploads.",
                "Network and proxy settings allow access to files host, registry, and data sources.",
                "UI contract stays consistent: project root, tags, and properties.",
            ],
            steps=[
                "Back up local clearml.conf and note current hosts.",
                "Set internal CLEARML_* endpoints or clearml.conf entries.",
                "Run logging mode locally to validate UI and artifact upload.",
                "Clone from UI and enqueue to the target queue (do not hardcode queue names).",
                "Check large artifact uploads and report rendering.",
                "Record differences in docs/issues and update docs/42_REHEARSAL_SCENARIOS.md.",
            ],
            common_errors=[
                "401/403 from API: missing permissions or invalid credentials.",
                "File server 404/timeout: files host misconfigured or blocked by proxy.",
                "Artifact upload failure: storage credentials or size limits.",
                "Agent failure: missing packages, incompatible Python, or missing system libraries.",
                "Dataset not found: path differs between local and agent environments.",
                "Task stuck in queue: no agent registered to the queue.",
            ],
            notes=[
                "Trial phase does not fix queue/permission/retention policies in code.",
                "Use docs/42_REHEARSAL_SCENARIOS.md for the full rehearsal flow.",
            ],
        )
    }


def main() -> int:
    env_choices = ("internal", "local")
    ap = argparse.ArgumentParser(
        description="Print migration checklists for ClearML rehearsal environments."
    )
    ap.add_argument(
        "--from",
        dest="from_env",
        default="local",
        choices=env_choices,
        help="Source environment (default: local).",
    )
    ap.add_argument(
        "--to",
        dest="to_env",
        default="internal",
        choices=env_choices,
        help="Target environment (default: internal).",
    )
    args = ap.parse_args()

    if args.from_env == args.to_env:
        print(f"No migration needed: {args.from_env} -> {args.to_env}")
        return 0

    guides = _guides()
    guide = guides.get((args.from_env, args.to_env))
    if not guide:
        supported = ", ".join(f"{src}->{dst}" for src, dst in guides)
        print(f"Unsupported migration: {args.from_env} -> {args.to_env}")
        print(f"Supported migrations: {supported}")
        return 2

    _render_guide(guide)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
