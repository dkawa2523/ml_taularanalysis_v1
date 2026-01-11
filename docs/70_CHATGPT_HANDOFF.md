# 70_CHATGPT_HANDOFF (ClearML update5-clearml)

This note summarizes the changes and verification performed in the recent ChatGPT/Codex session
so another agent can quickly understand intent, edits, and current status.

## Scope and Goals
- Stabilize ClearML template resolution and remote execution.
- Ensure all remote tasks point to the solution repo and use the unified entry point.
- Make version pinning optional (default: branch head).
- Add diagnostics and operator-friendly guidance.

## Branch and Commits
- Branch: `update5-clearml`
- Commits applied in this session (newest first):
  - `3381002` Enable TabPFN auto-download for full model runs
  - `3f59b99` Skip failed templates when applying
  - `62b6d18` Clear template task diffs on apply
  - `082c454` Update ClearML pipeline diagnostics and templates

## Code Changes (Intent + Files)
### ClearML script spec + entry point unification
- `tools/clearml_entrypoint.py`: merges Hydra overrides from Task parameters + env vars and ensures repo root is on `sys.path`.
- `src/tabular_analysis/platform_adapter.py`: centralized ClearML script resolution and added support for clearing `script.diff`.
- `conf/clearml/templates.yaml`: all remote templates use `python tools/clearml_entrypoint.py ...`.

### Deterministic template management
- `src/tabular_analysis/ops/manage_clearml_templates.py`: deterministic selection, skip failed templates, deprecate mismatches,
  and clear `script.diff` when applying.
- `tools/clearml_templates/manage_templates.py`: clear `script.diff` on apply.
- `conf/clearml/templates.lock.yaml`: lock file added for template specs.

### Diagnostics and troubleshooting
- `src/tabular_analysis/ops/clearml_diagnose.py`: report valid/invalid templates and queue hygiene.
- `docs/69_CLEARML_TROUBLESHOOTING.md`, `docs/68_CLEARML_AGENT_TROUBLESHOOTING.md`: updated operational guidance.
- `Agent_clearml.md`: consolidated setup and ops checklist.

### UI logging fix
- `src/tabular_analysis/clearml/ui_logger.py`: `report_table` uses `table_plot` (ClearML-compatible).

### Optional model support
- `conf/group/model/tabpfn.yaml`: `auto_download: true` for TabPFN weights.

### Pipeline testing helper
- `tools/tests/clearml_pipeline_probe.py`: helper for ClearML pipeline verification.

## Operational Actions Performed
### Template refresh
- Applied templates on `update5-clearml` and cleared template diffs.
- Commands used:
  - `python -m tabular_analysis.ops.manage_clearml_templates --apply --branch update5-clearml`
  - `python -m tabular_analysis.ops.manage_clearml_templates --validate --branch update5-clearml`
  - `python -m tabular_analysis.ops.clearml_diagnose --queue default`

### ClearML pipeline runs (summary)
#### Classification full-model run
- All models except TabPFN completed; TabPFN failed due to Hugging Face gated model access.
- Action: either supply `HF_TOKEN` on agent or exclude `tabpfn`.

#### Regression full-model run (current)
- Usecase id: `test_toy_reg_all_20260111_131252`
- Pipeline controller task id: `2f33c0c6165c49dfaad1b753bf143b59` (status: in_progress, checked 2026-01-11 13:33 +0900).
- Dataset path: `/tmp/ta_rehearsal_data/toy_reg.csv`
- Expected model variants (regression): `catboost, elasticnet, extra_trees, gaussian_process, gradient_boosting, knn, lasso, lgbm,
  linear_regression, mlp, random_forest, ridge, svc, svr, tabpfn, xgboost`.

## Known Issues / Gotchas
1) ClearML agent failing to apply git diff
   - Cause: local repo has uncommitted diff entries that refer to files not in the remote repo.
   - Mitigation: set `CLEARML_VCS_DIFF=""` (and optionally `CLEARML_VCS_STATUS=""`) or keep the repo clean.

2) TabPFN gated weights
   - Requires Hugging Face access; set `HF_TOKEN` on the agent or omit `tabpfn`.

3) `pipeline.model_set` is not in the schema
   - Use `+pipeline.model_set=regression_all` (Hydra adds new key).

4) Agent warning about missing `clearml-agent`
   - CLI emits `[warn] clearml-agent not found` but continues. Ensure agent is running and watching the queue.

## How to Re-Verify (Quick)
```bash
# Templates
python -m tabular_analysis.ops.manage_clearml_templates --validate --branch update5-clearml

# Diagnostics
python -m tabular_analysis.ops.clearml_diagnose --queue default

# Regression full-model pipeline (controller)
python -m tabular_analysis.cli task=pipeline \
  run.clearml.enabled=true \
  run.clearml.execution=pipeline_controller \
  run.clearml.queue_name=default \
  run.usecase_id=test_toy_reg_all_<timestamp> \
  data.dataset_path=/tmp/ta_rehearsal_data/toy_reg.csv \
  data.target_column=target \
  pipeline.run_dataset_register=true \
  +pipeline.model_set=regression_all
```

## Next Checks for a New Agent
- Confirm the regression pipeline controller task finishes and child tasks are created under
  `MFG/TabularAnalysis/<usecase_id>/<stage>` projects.
- If any task fails, inspect `clearml` console output for dependency or diff-apply errors.
- If TabPFN is required, confirm HF token is available in the agent environment.
