# ClearML HyperParameters 分類（セクション） 契約 v1

## ゴール
ClearML UI の Configuration > Hyperparameters が **GENERAL一択**にならないよう、セクションを分ける。

## 方針
- `Task.connect(params_dict, name="<Section>")` を使用してセクションを作る。
- 全設定を入れない（ノイズ回避）。再実行・比較に必要な最小キーのみ。
- 具体的な抽出は `src/tabular_analysis/clearml/hparams.py` に集約。
- 値が空のセクションは表示しない（キーがある時のみ connect）。

## セクション（使用名）
- `Inputs` : data.dataset_path, infer.mode, schema_policy など
- `Dataset` : raw/processed dataset_id など
- `Preprocess` : preprocess.variant, split.*, processed_dataset.store_features
- `Model` : model.variant, model.params.*
- `Eval` : task_type, primary_metric, direction, compare.require_comparable, selection.top_k
- `Optimize` : 探索/最適化がある場合のみ
- `Execution` : usecase_id, schema_version, code_version, clearml.execution
- `Links` : upstream task refs など（必要時のみ）

## 各タスクの必須キー例
### dataset_register
- Inputs: data.dataset_path, data.target_column
- Dataset: raw_dataset_id（入力がある場合のみ）
- Execution: usecase_id, schema_version, code_version, clearml.execution

### preprocess
- Inputs: data.dataset_path（raw_dataset_id がない場合）
- Dataset: raw_dataset_id
- Preprocess: preprocess.variant, split.strategy, split.seed, processed_dataset.store_features
- Execution: usecase_id, schema_version, code_version, clearml.execution

### train_model
- Dataset: processed_dataset_id
- Model: model.variant, model.params.*
- Eval: task_type, primary_metric
- Execution: usecase_id, schema_version, code_version, clearml.execution

### leaderboard
- Eval: primary_metric, direction, compare.require_comparable, selection.top_k
- Execution: usecase_id, schema_version, code_version, clearml.execution

### infer
- Inputs: infer.mode, input.source, input.path/json, schema_policy
- Model: model_id, model_abbr
- Dataset: train_task_id, raw/processed dataset_id, preprocess_variant, split_hash, recipe_hash
- Execution: usecase_id, schema_version, code_version, clearml.execution
