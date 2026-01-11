# ClearML UI Checklist (Trial Phase)

This checklist verifies that Datasets, Plots, Scalars, Controller, Templates, and HyperParameters match the UI contract.
See also: `docs/03_CLEARML_UI_CONTRACT.md`, `docs/50_CLEARML_PROCESSED_DATASET_CONTRACT.md`,
`docs/51_CLEARML_PLOTS_SCALARS_DEBUGSAMPLES_CONTRACT.md`, `docs/52_CLEARML_PIPELINE_CONTROLLER_CONTRACT.md`,
`docs/53_CLEARML_HYPERPARAMETERS_CONTRACT.md`, `docs/54_CLEARML_MINIMALITY_GUIDE.md`.

## 0. Preconditions
- [ ] ClearML server is reachable and `clearml-init` is complete.
- [ ] A run exists (logging or pipeline_controller).
- [ ] `usecase_id` is known (from `work/rehearsal/rehearsal_log.md` or output dir).

## 1. Project tree and required artifacts
- [ ] Project path matches `<ROOT>/TabularAnalysis/<usecase_id>/<Stage>`.
- [ ] Each task has `config_resolved.yaml`, `out.json`, `manifest.json` as artifacts.
- [ ] Tags and user properties include required keys (see `docs/03_CLEARML_UI_CONTRACT.md`).
- [ ] Pipeline task has `pipeline_run.json` (if pipeline ran).

## 2. Processed dataset (Datasets)
- [ ] `preprocess` output contains `processed_dataset_id` in `out.json`.
- [ ] ClearML Datasets has a dataset named like `processed__{usecase_id}__{preprocess_variant}__{split_hash}__v{schema_version}`.
- [ ] Dataset tags include `usecase:<id>`, `process:preprocess`, `type:processed`, `schema:v<schema_version>`.
- [ ] SDK check:
```bash
python - <<'PY'
from clearml import Dataset

dataset_id = "<processed_dataset_id>"
dataset = Dataset.get(dataset_id=dataset_id)
print(dataset.id, dataset.name, dataset.get_tags())
print(dataset.get_local_copy())
PY
```
- [ ] Dataset files match `docs/50_CLEARML_PROCESSED_DATASET_CONTRACT.md` (splits.json, schema.json, recipe.json, preprocess_bundle.joblib, meta.json, etc).

## 3. Scalars, Plots, Debug Samples (UI)
- [ ] Train task scalars show `metrics/<primary_metric>` and expected secondary metrics.
- [ ] Plots show feature importance, confusion matrix / roc curve (classification) or residual plot (regression).
- [ ] Debug samples show small input/output examples (report_text or report_table).
- [ ] Leaderboard task shows `leaderboard/best_score` scalar and top-k plot.
- [ ] Pipeline task shows `pipeline/num_models`, `pipeline/num_succeeded`, `pipeline/num_failed`.

## 4. HyperParameters and Configuration (minimality)
- [ ] Common keys only: `usecase_id`, `schema_version`, `code_version` (if available), `clearml.execution`.
- [ ] dataset_register: `data.dataset_path`, `data.target_column` (if logging).
- [ ] preprocess: `raw_dataset_id` or `dataset_path`, `preprocess.variant`, `split.strategy`, `split.seed`, `processed_dataset.store_features`.
- [ ] train_model: `processed_dataset_id`, `task_type`, `primary_metric`, `model.variant`, `model.params.*` (major params only).
- [ ] leaderboard: `primary_metric`, `direction`, `compare.require_comparable`, `selection.top_k`.
- [ ] infer: `model_id`, `infer.mode`, `schema_policy`.
- [ ] No full config dump in HyperParameters (noise control).

## 5. Pipeline Controller and templates
- [ ] Template tasks exist with tags `template:true` and `process:<dataset_register|preprocess|train_model|leaderboard|infer>`.
- [ ] PipelineController run creates child tasks and queues them.
- [ ] Child tasks show `clearml.execution=logging` in HyperParameters.
- [ ] `pipeline_run.json` lists child task IDs and matches UI tasks.
- [ ] Queue name matches `run.clearml.queue_name` or `exec_policy.queues.*`.

## 6. Plots vs artifacts sanity
- [ ] Plots appear in ClearML UI (not only PNG artifacts).
- [ ] Large artifacts upload successfully on the local server.

## 7. If anything is missing
- [ ] Record gaps in `docs/issues` with reproduction steps and screenshots (if possible).
