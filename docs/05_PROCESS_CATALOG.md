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
- `eval.primary_metric`/`eval.direction`/`eval.cv_folds`/`eval.seed`/`eval.task_type`

**出力（out.json）**
- `processed_dataset_id`
- `split_hash`
- `recipe_hash`
- `train_task_id`（ClearML Task ID。local では null）
- `model_id`（ClearML Model ID など。local では path）
- `best_score`
- `primary_metric`
- `task_type`
- `n_classes`（classification のみ）

**SKIP（optional deps / inapplicable）**
- `out.json` / `manifest.json` は出力し、`status: "skipped"` と `reason` を追加する
- `model_id` / `best_score` などは null になる（leaderboard 側で除外される）

**FAILED（例: TabPFN の重み未取得）**
- `out.json` / `manifest.json` は出力し、`status: "failed"` と `error`（type/message）を追加する
- `model_id` / `best_score` などは null になる（leaderboard 側で除外される）

**追加 Artifacts**
- `metrics.json`, `preds_valid.parquet`, `classes.json`（classification のみ）, `model_bundle/*`

## train_ensemble
**入力**
- `run.usecase_id`
- `preprocess.variant`
- `ensemble.method` / `ensemble.top_k` / `ensemble.selection_metric`
- `ensemble.exclude_variants` / `ensemble.fallback_rerun_predict`
- `ensemble.weighted.search` / `ensemble.weighted.n_samples` / `ensemble.weighted.seed` / `ensemble.weighted.top_k_max`（method=weighted）
- `ensemble.stacking.meta_model` / `ensemble.stacking.cv_folds` / `ensemble.stacking.seed` / `ensemble.stacking.require_test_split`（method=stacking）

**出力（out.json）**
- `processed_dataset_id`
- `split_hash`
- `recipe_hash`
- `train_task_id`
- `model_id`
- `best_score`
- `primary_metric`
- `task_type`
- `n_classes`（classification のみ）

**追加 Artifacts**
- `metrics.json`, `ensemble_spec.json`, `model_bundle.joblib`
- stacking 時は `ensemble_spec.json` に `primary_metric_source` / `meta_model` / `meta_training_protocol` を記録

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
- 接着剤：plan 生成 + driver 実行（local_sequential / pipeline_controller）。
- `pipeline_run.json`, `plan.json`, `report.md`, `run_summary.json` を出力する（詳細は `docs/60_PIPELINE_TRAIN_CONTRACT.md`）。
- `ensemble.enabled=true` の場合は train_ensemble を含め、leaderboard は単体 + アンサンブルを比較する（`docs/83_ENSEMBLE_POLICY.md`）。
