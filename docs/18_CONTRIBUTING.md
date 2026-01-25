# 18_CONTRIBUTING (Development Guide)

## Scope
This guide documents the minimum workflow for day-to-day development and PRs.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/base.txt
pip install -e .
```

uv alternative:
```bash
uv sync --frozen
```

Optional model extras:
```bash
uv sync --extra models
# TabPFN (optional)
uv sync --extra tabpfn
```

## Branching
- Create a short-lived branch from `main` (examples: `feature/<topic>`, `fix/<topic>`, `chore/<topic>`).
- Keep changes focused; update docs when changing contracts or config behavior.

## Pull Request Checklist
- Explain the intent, scope, and verification status.
- Update docs when required (UI contract, config, or ops changes).
- Do not edit protected runtime files: `work/queue.json`, `work/state.json`, `work/tasks/**`.

## Verification
Run the quick suite before opening a PR:
```bash
python tools/tests/verify_all.py --quick
```

Use the full suite when preparing a release or larger refactor:
```bash
python tools/tests/verify_all.py --full
```

CI runs the quick suite on every push/PR.

## Repository Constraints
- Platform API dependencies must stay inside `src/tabular_analysis/platform_adapter.py`.
- Do not change the ClearML UI contract without updating `docs/03_CLEARML_UI_CONTRACT.md`.
- Keep `conf/` and `docs/` in sync when configuration or behavior changes.
