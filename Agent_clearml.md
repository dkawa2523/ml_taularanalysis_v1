# ClearML Agent / Server Operations Guide

## Purpose
- Provide a clean checklist for new ClearML server onboarding and agent operations.
- Capture the root causes seen so far and the durable fixes.

## What Broke Previously (Root Causes)
1) Old pipeline tasks in the queue referenced the platform repo.
   - Result: `ModuleNotFoundError: No module named 'tabular_analysis'`.
2) `version_num` pinned to an unrelated or missing commit.
   - Result: `fatal: unable to read tree` during git checkout.
3) Template resolution was non-deterministic.
   - Old/failed templates or mismatched repo/branch/entry_point were selected.
4) ClearML Agent did not receive CLI overrides from the entry_point.
   - Dataset_register ran with wrong overrides or fell back to pipeline task.
5) `ml_platform` was missing in agent venv.
   - Result: `ml_platform.integrations.clearml is required` errors.
6) ClearML `set_user_properties` signature differences caused runtime errors.

All items below are designed to prevent these regressions.

## New ClearML Server Setup Checklist
1) Server endpoints
   - Verify `api`, `web`, and `files` endpoints are reachable.
   - Decide TLS/CA policy and ensure the agent trusts the certificate.
2) Client configuration
   - Run `clearml-init` on operators and agents, or set:
     - `CLEARML_API_HOST`
     - `CLEARML_WEB_HOST`
     - `CLEARML_FILES_HOST`
     - `CLEARML_API_ACCESS_KEY`
     - `CLEARML_API_SECRET_KEY`
3) Project naming policy
   - `run.clearml.project_root` controls the top project path.
   - `run.clearml.template_usecase_id` is the dedicated usecase id for templates.

## Agent Setup Checklist
1) Install and expose agent on PATH
   - Ensure `clearml-agent --version` works.
   - If not, add `.venv/bin` to PATH on the agent machine.
2) Queue alignment
   - `run.clearml.queue_name` must match the queue the agent listens on.
3) Git access
   - Use HTTPS repository URLs.
   - If repo is private, ensure credentials/token are available to the agent.
4) Python environment
   - Agent builds its own venv. Make sure the base Python matches the project.
5) Required dependency
   - `ml-platform` must be installable on the agent (see requirements).

## Repository / Config Standards
1) Code repository and branch
   - `run.clearml.code_ref.repository: auto` (uses repo origin URL)
   - `run.clearml.code_ref.branch: auto` (uses current branch)
   - Legacy: `run.clearml.code_repository` / `run.clearml.code_branch`
2) Entry point (mandatory)
   - Remote tasks must use `tools/clearml_entrypoint.py`.
   - Do not use `-m tabular_analysis.cli` in ClearML task scripts.
3) Version policy
   - Default: `run.clearml.code_ref.mode = branch`
   - Production option: `run.clearml.code_ref.mode = commit` (only if commit is reachable on remote).
   - Legacy: `run.clearml.code_version_mode = branch_head` / `pin_commit`

## Repository-side env bootstrap (uv)
1) Template tasks install only minimal tools
   - `clearml` + `uv` are installed by ClearML Agent requirements.
   - All runtime dependencies come from `uv.lock`.
2) Entry point bootstrap
   - `run.clearml.env.bootstrap=uv` triggers `uv sync --all-extras --frozen` into `.venv`.
   - Templates set this by default.
3) Model extras
   - Templates set `run.clearml.env.uv.all_extras=true` for deterministic installs.
4) Disable/bootstrap override
   - Set `run.clearml.env.bootstrap=none` to skip uv.
   - Ensure `uv.lock` exists (`uv lock`) before running ClearML tasks.

## Template Tasks (Deterministic Resolution)
1) Required tags
   - `template:true`
   - `usecase:<TemplateUsecaseId>`
   - `schema:<schema_version>`
   - `process:<name>`
   - `solution:tabular-analysis`
2) Required script match
   - `repository`, `branch`, `entry_point` must match the solution repo.
3) Deterministic selection
   - Exclude `template:deprecated` or non-`created` tasks.
4) Apply/Validate
   - Plan:
     - `python -m tabular_analysis.ops.manage_clearml_templates --plan`
   - Apply:
     - `python -m tabular_analysis.ops.manage_clearml_templates --apply`
   - Validate:
     - `python -m tabular_analysis.ops.manage_clearml_templates --validate`

## Recommended Execution Flow (Test Phase)
1) Template setup
   - Apply/validate templates (above).
2) Run pipeline controller locally (recommended for tests)
   - `run.clearml.execution=pipeline_controller_local`
   - Child tasks are enqueued to the agent queue.
3) Observe child tasks in UI
   - `dataset_register -> preprocess -> train -> leaderboard`.

## Diagnostics (Non-Destructive)
Use `python -m tabular_analysis.ops.clearml_diagnose` to:
- List valid templates per process (repo/branch/entry_point/ version policy).
- Detect mismatched or deprecated templates.
- Detect queued tasks referencing the platform repo and show removal steps.

## Common Failures and Fixes
1) `ModuleNotFoundError: tabular_analysis`
   - Cause: task uses platform repo or wrong entry_point.
   - Fix: refresh templates; remove old tasks from queue.
2) `fatal: unable to read tree <commit>`
   - Cause: invalid `version_num`.
   - Fix: set `run.clearml.code_ref.mode=branch` (legacy: `code_version_mode=branch_head`) or use a valid commit.
3) `ConfigAttributeError: Key 'clearml_policy'`
   - Cause: override used `ops.clearml_policy` instead of `ops/clearml_policy`.
   - Fix: use config group syntax (`ops/clearml_policy=...`).
4) `ml_platform.integrations.clearml is required`
   - Cause: `ml-platform` missing in agent venv.
   - Fix: ensure `ml-platform` is in `requirements/base.txt`.
5) `Invalid task status: expected=created`
   - Cause: failed template tasks cannot be patched.
   - Fix: tag them `template:deprecated` and recreate.

## Post-Setup Validation
1) Template validation command
   - `python -m tabular_analysis.ops.manage_clearml_templates --validate`
2) Minimal pipeline run (toy data)
   - Confirm child tasks are created and their scripts point to the solution repo.
3) Queue hygiene
   - Remove old tasks referencing the platform repo.

## Notes on Old Tasks
Old tasks already in a queue cannot be fixed by code changes alone.
They must be removed from the queue in the ClearML UI.
