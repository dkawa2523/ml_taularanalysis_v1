# ClearML Template Task Plan

Generated: 2026-01-25T02:43:18Z
Spec: `/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/conf/clearml/templates.yaml`

## Context
- project_root: `MFG`
- usecase_id: `TabularAnalysis`
- schema_version: `v1`

## Templates
### dataset_register
- project_name: `MFG/TabularAnalysis/01_dataset_register`
- task_name: `dataset_register`
- entrypoint: `python tools/clearml_entrypoint.py task=dataset_register`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging, run.clearml.env.bootstrap=uv, run.clearml.env.uv.all_extras=true`
- tags: `template:true, usecase:TabularAnalysis, process:dataset_register, schema:v1, solution:tabular-analysis`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "dataset_register", "schema_version": "v1"}`

### preprocess
- project_name: `MFG/TabularAnalysis/02_preprocess`
- task_name: `preprocess`
- entrypoint: `python tools/clearml_entrypoint.py task=preprocess`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging, run.clearml.env.bootstrap=uv, run.clearml.env.uv.all_extras=true`
- tags: `template:true, usecase:TabularAnalysis, process:preprocess, schema:v1, solution:tabular-analysis`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "preprocess", "schema_version": "v1"}`

### train_model
- project_name: `MFG/TabularAnalysis/03_train_model`
- task_name: `train_model`
- entrypoint: `python tools/clearml_entrypoint.py task=train_model`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging, run.clearml.env.bootstrap=uv, run.clearml.env.uv.all_extras=true`
- tags: `template:true, usecase:TabularAnalysis, process:train_model, schema:v1, solution:tabular-analysis`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "train_model", "schema_version": "v1"}`

### train_ensemble
- project_name: `MFG/TabularAnalysis/04_train_ensemble`
- task_name: `train_ensemble`
- entrypoint: `python tools/clearml_entrypoint.py task=train_ensemble`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging, run.clearml.env.bootstrap=uv, run.clearml.env.uv.all_extras=true`
- tags: `template:true, usecase:TabularAnalysis, process:train_ensemble, schema:v1, solution:tabular-analysis`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "train_ensemble", "schema_version": "v1"}`

### infer
- project_name: `MFG/TabularAnalysis/04_infer`
- task_name: `infer`
- entrypoint: `python tools/clearml_entrypoint.py task=infer`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging, run.clearml.env.bootstrap=uv, run.clearml.env.uv.all_extras=true`
- tags: `template:true, usecase:TabularAnalysis, process:infer, schema:v1, solution:tabular-analysis`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "infer", "schema_version": "v1"}`

### leaderboard
- project_name: `MFG/TabularAnalysis/05_leaderboard`
- task_name: `leaderboard`
- entrypoint: `python tools/clearml_entrypoint.py task=leaderboard`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging, run.clearml.env.bootstrap=uv, run.clearml.env.uv.all_extras=true`
- tags: `template:true, usecase:TabularAnalysis, process:leaderboard, schema:v1, solution:tabular-analysis`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "leaderboard", "schema_version": "v1"}`

### pipeline
- project_name: `MFG/TabularAnalysis/99_pipeline`
- task_name: `pipeline`
- entrypoint: `python tools/clearml_entrypoint.py task=pipeline`
- default_overrides: `run.clearml.enabled=true, run.clearml.execution=logging, run.clearml.env.bootstrap=uv, run.clearml.env.uv.all_extras=true`
- tags: `template:true, usecase:TabularAnalysis, process:pipeline, schema:v1, solution:tabular-analysis`
- properties_minimal: `{"usecase_id": "TabularAnalysis", "process": "pipeline", "schema_version": "v1"}`

## Apply
```bash
python tools/clearml_templates/manage_templates.py --apply
```
Lock file: `/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/conf/clearml/templates.lock.yaml`

## Validate
```bash
python tools/clearml_templates/manage_templates.py --validate
```