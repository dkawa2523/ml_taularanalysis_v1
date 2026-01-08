# タスク名・タグ・Properties ポリシー v2（単一の正）

## 目的
ClearML 上で増え続けるタスク/データセットを、少ないキーで検索・比較できるようにする。
命名/タグ/Properties のルールはこのドキュメントを単一の正とする。

## 1) タスク名
### デフォルト（実装の現状）
- task 名は **process 名のまま**（`dataset_register`, `preprocess`, `train_model`, `leaderboard`, `infer`, `pipeline`, `champion_challenger`, `promote_model`, `retrain`, `rollback_model`）
- `run.clearml.task_name` が指定されていればそちらを優先

### train_model の自動命名
`src/tabular_analysis/clearml/naming.py` により、`train_model` は以下の命名に上書きされる:
- `train__{model_abbr}__pp={preprocess_variant}__ds={raw_id_short}`

解決ルール:
- `model_abbr`: `model_variant.name` → `train.model` の順で解決
- `preprocess_variant`: `preprocess_variant.name` → `preprocess.variant` の順で解決
- `raw_dataset_id`: `data.raw_dataset_id` → `data.dataset_path` → `data.processed_dataset_id` の順で解決
- sanitize: `[A-Za-z0-9_-]` 以外を `-` に置換し、連続 `-` を圧縮
- `raw_id_short`: `raw_dataset_id` を 12 文字に短縮（`head~tail` 形式）

### infer の子タスク（optimize/validation）
- `infer__single__trial={N}` または `infer__single__model={model_abbr}__trial={N}`
- validation 入力の複数実行時は `infer__single__case={idx}` 系の命名

## 2) Tags（key:value のみ）
### 標準タグ（全 Task）
`src/tabular_analysis/platform_adapter.py` で自動付与:
- `usecase:<usecase_id>`
- `process:<process>`（`cfg.task.name` が優先）
- `schema:<schema_version>`
- `grid:<grid_run_id>`（`run.grid_run_id` がある場合）
- `retrain:<retrain_run_id>`（`run.retrain_run_id` がある場合）

### 追加タグの入口
- `run.clearml.policy.tags` / `run.clearml.policy.extra_tags`
- `run.clearml.extra_tags`

### 実装が追加するタグ
- train_model: `model:<abbr>`, `preprocess:<variant>`, `dataset:<raw_dataset_id>`（shorten せず全文を sanitize）
- pipeline grid: `grid_cell:<preprocess>__<model>`
- HPO trial: `hpo:<hpo_run_id>`
- promote_model: `stage:<stage>`, `champion:current`（設定時）, `rollback:true`（rollback時）
- rollback_model: `stage:<stage>`, `rollback:true`, `rollback:manual`（target 指定時）
- alerting: `alert:<kind>`, `severity:<level>`

### テンプレートタスク（PipelineController 用）
- `template:true` + `process:<process>`
- `usecase:<usecase_id>` / `schema:<schema_version>` は **一致するものがあれば採用**

### ClearML Dataset（dataset_register）
- `usecase:<usecase_id>`, `process:dataset_register`, `schema:<schema_version>`

## 3) User Properties（最小キー）
### 標準 Properties（全 Task）
`src/tabular_analysis/platform_adapter.py` で自動付与:
- `usecase_id`
- `process`
- `schema_version`
- `code_version`
- `platform_version`
- `grid_run_id`
- `retrain_run_id`（設定時のみ）

### Policy Properties
- `run.clearml.policy.properties` / `run.clearml.policy.extra_properties`（policy が優先）

### プロセス別 Properties（実装が追記）
- preprocess: `processed_dataset_id`, `split_hash`, `recipe_hash`, `schema_hash`, `processed_dataset_version`
- train_model: `processed_dataset_id`, `split_hash`, `model_id`, `primary_metric`, `best_score`, `task_type`, `n_classes`, `best_threshold`, `imbalance_enabled`, `imbalance_strategy`, `imbalance_applied`
- leaderboard: `recommended_train_task_id`, `recommended_model_id`, `excluded_count`, `selection_policy`, `recommended_composite_score`
- infer: `drift_alert`（drift 有効時のみ）
- champion_challenger: `winner`, `primary_metric`, `champion_score`, `challenger_score`, `directional_delta`
- promote_model: `promotion_stage`, `promoted_model_id`, `promotion_source`, `primary_metric`, `best_score`, `registry_model_id`, `registry_status`, `champion_usecase_id`, `champion_registry_path`, `set_champion`, `rollback`, `rollback_from_model_id`
- rollback_model: `rollback_stage`, `rollback_reason`, `rollback_before_model_id`, `rollback_after_model_id`
- retrain: `retrain_run_id`, `grid_run_id`, `auto_promote`, `promote_status`, `winner`
- alerting: `last_alert_kind`, `last_alert_severity`, `last_alert_title`, `last_alert_at`

## 4) ルール
- タグ/Properties は短く。詳細は artifact（json/csv/md）に逃がす。
- task 名は短く（Config 全文を入れない）。必要なら `run.clearml.task_name` で上書き。
- UI 表示の命名を揃えたい場合は `docs/03_CLEARML_UI_CONTRACT.md` の推奨に合わせて `run.clearml.task_name` を明示する。
- HyperParameters は `docs/61_CLEARML_HPARAMS_SECTIONS.md` に従う。
