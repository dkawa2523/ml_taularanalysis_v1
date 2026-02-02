# 試験（ローカル→社内）リハーサルコマンド v2

## Windows 補足
- `/tmp/...` は Windows では `"$env:TEMP\\..."` に置き換えてください。
- bash 前提の例は PowerShell での実行に置換してください（詳細は `docs_manual/90_windows.md`）。

## 0) Python runner（推奨・自動検証つき）
```bash
python tools/rehearsal/run_pipeline_v2.py --execution local \
  --task-type regression --preprocess stdscaler_ohe --models ridge,elasticnet

python tools/rehearsal/run_pipeline_v2.py --execution logging \
  --task-type regression --preprocess stdscaler_ohe --models ridge,elasticnet \
  --project-root LOCAL

python tools/rehearsal/run_pipeline_v2.py --execution agent --queue-name default \
  --task-type regression --preprocess stdscaler_ohe --models ridge,elasticnet \
  --project-root LOCAL
```
- dataset_register + pipeline を 1コマンドで実行し、ClearML の基本検証まで行う
- 最後に `usecase_id` / `pipeline_task_id` / `dataset_id` / 検索タグを表示する

## 0.5) ClearML UI 構造の自動検証（T100）
```bash
python tools/tests/rehearsal_verify_clearml_ui.py --usecase-id <USECASE_ID>
```
- pipeline / preprocess / train / ensemble / leaderboard の存在と構造を自動チェック
- version_num pin と HyperParameters セクション分割も警告として表示

## 1) 前提
- `run.clearml.enabled=true` の場合は ClearML 設定済みであること
- pipeline は `data.raw_dataset_id` 必須で dataset_register は含まない

## 2) dataset_register（raw_dataset_id を取得）
### ClearML logging
```bash
python -m tabular_analysis.cli task=dataset_register \
  run.clearml.enabled=true run.clearml.execution=logging \
  data.dataset_path=/tmp/ta_rehearsal_data/toy_reg.csv data.target_column=target
```
- 出力: `outputs/.../01_dataset_register/out.json` の `raw_dataset_id` を控える

### ローカルのみ
```bash
python -m tabular_analysis.cli task=dataset_register \
  run.clearml.enabled=false \
  data.dataset_path=/tmp/ta_rehearsal_data/toy_reg.csv data.target_column=target
```
- 出力: `raw_dataset_id=local:<hash>`（以降の pipeline で `data.dataset_path` と併用）

## 3) pipeline（dataset_register 後に実行）
### ClearML logging（ローカル実行 + 記録）
```bash
python -m tabular_analysis.cli task=pipeline \
  run.clearml.enabled=true run.clearml.execution=logging \
  data.raw_dataset_id=<RAW_DATASET_ID> \
  pipeline.preprocess_variant=stdscaler_ohe pipeline.model_set=regression_all
```

### PipelineController（agent 実行）
```bash
# 事前にテンプレを作る場合:
# python -m tabular_analysis.ops.manage_clearml_templates --apply
# agent起動: clearml-agent daemon --foreground --queue default --create-queue
python -m tabular_analysis.cli task=pipeline \
  run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default \
  data.raw_dataset_id=<RAW_DATASET_ID> \
  pipeline.preprocess_variant=stdscaler_ohe pipeline.model_set=regression_all
```
※ grid override を入れる場合は Hydra list 形式（スペース/クォートなし）で指定する。\
例: `pipeline.grid.model_variants=[ridge,lasso] pipeline.grid.preprocess_variants=[stdscaler_ohe]`
※ pipeline_controller は template clone 前提。commit pin を避けるため `run.clearml.code_ref.mode=branch` を推奨（`docs/69_CLEARML_TROUBLESHOOTING.md`）。

### ローカル（ClearML 無効）
```bash
python -m tabular_analysis.cli task=pipeline \
  run.clearml.enabled=false \
  data.raw_dataset_id=local:<HASH> data.dataset_path=/tmp/ta_rehearsal_data/toy_reg.csv \
  pipeline.preprocess_variant=stdscaler_ohe pipeline.model_set=regression_all
```

## 4) ローカル一括（agent 不要、ClearML task を分割生成）
```bash
python -m tabular_analysis.ops.local_orchestrator train_regression \
  --dataset-path /tmp/ta_rehearsal_data/toy_reg.csv --target-column target \
  --preprocess stdscaler_ohe --model-set regression_all --clearml --project-root LOCAL \
  --output-root outputs/local_orchestrator_demo

python -m tabular_analysis.ops.local_orchestrator train_regression \
  --raw-dataset-id <RAW_DATASET_ID> --target-column target \
  --preprocess stdscaler_ohe --model-set regression_all --clearml --project-root LOCAL
```

## 5) infer single/batch/optimize
```bash
python -m tabular_analysis.cli task=infer infer.mode=single \
  infer.model_id=<MODEL_ID> infer.input_path=/tmp/infer.csv

python -m tabular_analysis.cli task=infer infer.mode=batch \
  infer.model_id=<MODEL_ID> infer.batch.inputs_path=/tmp/batch_inputs.csv

python -m tabular_analysis.cli task=infer infer.mode=optimize \
  infer.model_id=<MODEL_ID> infer.optimize.n_trials=30 \
  infer.optimize.search_space='[{name:num1,type:float,low:-3,high:3},{name:num2,type:float,low:0,high:10},{name:cat,type:categorical,choices:[a,b,c]}]'
```
※ optimize は `infer.optimize.search_space` が必須。モデルの入力特徴に合わせて指定する。
