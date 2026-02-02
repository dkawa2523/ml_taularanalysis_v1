# ClearML Agent Troubleshooting (child tasks / templates)

## Windows 補足
- `/tmp/...` は Windows では `"$env:TEMP\\..."` に置き換えてください。

## Quick triage order (when child tasks are not created)
1) Pipeline task script: repository/branch/entry_point
2) Queue/Agent status
3) Agent log: ModuleNotFoundError

## 1) Pipeline task script check
- repository/branch must point to the solution repo/branch (not platform)
- entry_point must be `tools/clearml_entrypoint.py`

### Task.get_script() command example
```bash
python - <<'PY'
from clearml import Task

task = Task.get_task(task_id="<PIPELINE_TASK_ID>")
print(task.get_script())
PY
```

If repository/branch is wrong, update the task script or re-run the pipeline with
`run.clearml.code_ref.repository` / `run.clearml.code_ref.branch` set correctly
(legacy: `run.clearml.code_repository` / `run.clearml.code_branch`).

## 2) Queue/Agent checks
- pipeline task `run.clearml.queue_name` matches the queue the agent listens on
- agent is running and shows as online in ClearML

## 3) Agent log: ModuleNotFoundError
- the repo may not be cloned or dependencies are missing
- confirm the template uses `tools/clearml_entrypoint.py` and requirements include `-e .`
- refresh templates if needed:
  `python -m tabular_analysis.ops.manage_clearml_templates --apply`

## List override pitfalls (T075)
Bad (JSON list with spaces/quotes; agent splits tokens):
`pipeline.grid.model_variants=["catboost", "elasticnet"]`

Good (Hydra list, no spaces/quotes):
`pipeline.grid.model_variants=[catboost,elasticnet]`
Same rule applies to `pipeline.grid.preprocess_variants`.

If you see split tokens in agent logs, regenerate the entry_point by re-running
pipeline controller or updating the task script.

## Hydra override (child task)
- child では **run.clearml.project_name を使わない**（Hydra struct に無く失敗するため）。
- 子タスクの project を変える場合は **task.project_name のみ**を override する。
- どうしても新規キーを上書きする場合は `+key=value` で追加する（例: `+run.clearml.project_name=...`）。

## Trial ログ回収（--rm 対策）
child task の失敗ログが消える場合は以下を前提にする。

1) agent-services で --rm を外す  
`docker-compose.override.yml` に追加:
```
CLEARML_AGENT_SERVICES_DOCKER_RESTART: "no"
```
（restart policy が付くと `--rm` が外れる）

2) docker logs を即時回収  
```
python tools/clearml/watch_trial_logs.py --parent-task-id <PARENT_TASK_ID> --log-dir <TEMP>/clearml_trial_logs
```

注意:
- コンテナが残るため、不要になったら `docker container prune` で掃除する。
