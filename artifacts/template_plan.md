# ClearML Template Task Plan

Generated: 2026-01-01T16:39:09Z
Spec: `/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/conf/clearml/templates.yaml`

## Context
- project_root: `MFG`
- usecase_id: `TabularAnalysis`
- schema_version: `v1`

## Templates
### dataset_register
- project_name: `MFG/TabularAnalysis/01_dataset_register`
- task_name: `dataset_register`
- entrypoint: `python -m tabular_analysis.cli task=dataset_register`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging`
- tags: `usecase:TabularAnalysis, process:dataset_register, schema:v1`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "dataset_register", "schema_version": "v1"}`

### preprocess
- project_name: `MFG/TabularAnalysis/02_preprocess`
- task_name: `preprocess`
- entrypoint: `python -m tabular_analysis.cli task=preprocess`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging`
- tags: `usecase:TabularAnalysis, process:preprocess, schema:v1`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "preprocess", "schema_version": "v1"}`

### train_model
- project_name: `MFG/TabularAnalysis/03_train_model`
- task_name: `train_model`
- entrypoint: `python -m tabular_analysis.cli task=train_model`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging`
- tags: `usecase:TabularAnalysis, process:train_model, schema:v1`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "train_model", "schema_version": "v1"}`

### infer
- project_name: `MFG/TabularAnalysis/04_infer`
- task_name: `infer`
- entrypoint: `python -m tabular_analysis.cli task=infer`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging`
- tags: `usecase:TabularAnalysis, process:infer, schema:v1`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "infer", "schema_version": "v1"}`

### leaderboard
- project_name: `MFG/TabularAnalysis/05_leaderboard`
- task_name: `leaderboard`
- entrypoint: `python -m tabular_analysis.cli task=leaderboard`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging`
- tags: `usecase:TabularAnalysis, process:leaderboard, schema:v1`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "leaderboard", "schema_version": "v1"}`

### pipeline
- project_name: `MFG/TabularAnalysis/99_pipeline`
- task_name: `pipeline`
- entrypoint: `python -m tabular_analysis.cli task=pipeline`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging`
- tags: `usecase:TabularAnalysis, process:pipeline, schema:v1`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "pipeline", "schema_version": "v1"}`

### promote_model
- project_name: `MFG/TabularAnalysis/06_promote_model`
- task_name: `promote_model`
- entrypoint: `python -m tabular_analysis.cli task=promote_model`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging`
- tags: `usecase:TabularAnalysis, process:promote_model, schema:v1`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "promote_model", "schema_version": "v1"}`

## Apply
```bash
python tools/clearml_templates/manage_templates.py --apply
```
Lock file: `/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/conf/clearml/templates.lock.yaml`

## Validate
```bash
python tools/clearml_templates/manage_templates.py --validate
```