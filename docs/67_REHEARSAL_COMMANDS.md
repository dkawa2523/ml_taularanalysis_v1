# 試験（ローカル→社内）リハーサルコマンド v2

## 0) 前提
- `run.clearml.enabled=true` の場合は ClearML 設定済みであること
- pipeline はデフォルトで `pipeline.run_dataset_register=false`（`data.raw_dataset_id` が必須）

## 1) dataset_register（raw_dataset_id を取得）
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

## 2) pipeline（dataset_register 後に実行）
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

### ローカル（ClearML 無効）
```bash
python -m tabular_analysis.cli task=pipeline \
  run.clearml.enabled=false \
  data.raw_dataset_id=local:<HASH> data.dataset_path=/tmp/ta_rehearsal_data/toy_reg.csv \
  pipeline.preprocess_variant=stdscaler_ohe pipeline.model_set=regression_all
```

## 3) ローカル一括（agent 不要、ClearML task を分割生成）
```bash
python -m tabular_analysis.ops.local_orchestrator train_regression \
  --dataset-path /tmp/ta_rehearsal_data/toy_reg.csv --target-column target \
  --preprocess stdscaler_ohe --model-set regression_all --clearml --project-root LOCAL \
  --output-root outputs/local_orchestrator_demo

python -m tabular_analysis.ops.local_orchestrator train_regression \
  --raw-dataset-id <RAW_DATASET_ID> --target-column target \
  --preprocess stdscaler_ohe --model-set regression_all --clearml --project-root LOCAL
```

## 4) infer single/batch/optimize
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
