# 05_PROCESS_CATALOG（プロセスカタログ）

本 Solution の各タスクは独立して実行でき、I/O を `out.json` と `manifest.json` で追跡します。

> **Local mode 注意（重要）**
> - `run.clearml.enabled=false` または `run.clearml.execution=local` の場合、
>   out.json の `*_id` フィールドは ClearML の ID ではなく **ローカルパス等の参照（ref）** になることがあります。
> - Solution 内では “ID” という名前でも **参照（ref）** として扱い、
>   「ClearML ID かローカルパスか」は adapter / process 側で吸収します。

## dataset_register
**入力**
- `data.dataset_path`（CSV/Parquet へのパス）

**出力（out.json）**
- `raw_dataset_id`（ClearML Dataset ID など）
- `raw_schema`（列・型・欠損率など）

**追加 Artifacts**
- `schema.json`, `preview.csv`（任意）

## preprocess
**入力**
- `data.raw_dataset_id` または `data.dataset_path`
- `preprocess.variant`
- `data.split.*`

**出力（out.json）**
- `processed_dataset_id`
- `preprocess_variant`
- `split_hash`
- `recipe_hash`

**追加 Artifacts**
- `recipe.json`, `summary.md`, `preprocess_bundle.*`, `schema.json`

## train_model
**入力**
- `train.inputs.preprocess_run_dir`（preprocess の出力ディレクトリ）
- `data.processed_dataset_id`（preprocess out.json の整合チェック用。ClearML では Dataset ID）
- `model_variant`
- `eval.primary_metric`/`eval.direction`/`eval.cv_folds`/`eval.seed`

**出力（out.json）**
- `processed_dataset_id`
- `split_hash`
- `recipe_hash`
- `train_task_id`（ClearML Task ID。local では null）
- `model_id`（ClearML Model ID など。local では path）
- `best_score`
- `primary_metric`

**追加 Artifacts**
- `metrics.json`, `model_bundle/*`

## leaderboard
**入力**
- `leaderboard.train_task_ids` (ClearML task IDs)
- `leaderboard.train_run_dirs` (local run directories; fallback to train_task_ids when ClearML disabled)

**出力（out.json）**
- `leaderboard_csv`
- `recommended_train_task_id`
- `recommended_model_id`
- `excluded_count`

**追加 Artifacts**
- `leaderboard.csv`, `recommendation.json`, `summary.md`

## infer
**入力**
- `infer.model_id` または `infer.train_task_id`
- `infer.mode`（single/batch/optimize）

**出力（out.json）**
- `predictions_path` など

## pipeline
- 接着剤：grid 実行と task_id の受け渡し。重い処理は持たない。
