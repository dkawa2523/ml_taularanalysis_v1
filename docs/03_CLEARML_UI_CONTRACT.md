# 03_CLEARML_UI_CONTRACT（ClearML UI 契約）

このドキュメントは **非DSユーザーが ClearML UI だけで判断できる**ための契約です。

## Project 階層（固定）
`<ROOT>/TabularAnalysis/<usecase_id>/<Stage>`

- ROOT: `run.clearml.project_root`（または `TABULAR_ANALYSIS_CLEARML_PROJECT_ROOT`）
- usecase_id: `run.usecase_id`（未指定なら `run.usecase_id_policy` で自動生成）

例：
- `MFG/TabularAnalysis/test_toy_20260101_120000/01_dataset_register`
- `MFG/TabularAnalysis/test_toy_20260101_120000/02_preprocess`
- `MFG/TabularAnalysis/test_toy_20260101_120000/03_train_model`
- `MFG/TabularAnalysis/test_toy_20260101_120000/04_infer`
- `MFG/TabularAnalysis/test_toy_20260101_120000/05_leaderboard`
- `MFG/TabularAnalysis/test_toy_20260101_120000/99_pipeline`

## Task 名（推奨）
`<process>__<variant>__v<schema_version>`

例：
- `train_model__lgbm__preprocess=stdscaler_ohe__v1`

## Tags（最低限、固定キー）
- `usecase:<usecase_id>`
- `process:<process>`
- `schema:<schema_version>`
- `grid:<grid_run_id>`（pipeline 実行時）

追加タグは `run.clearml.policy.tags` / `run.clearml.extra_tags` で付与できるが、上記キーは必須。
## User Properties（固定キー）
- `usecase_id`
- `process`
- `schema_version`
- `code_version`
- `platform_version`
- `grid_run_id`

追加の user properties は `run.clearml.policy.properties` で付与できるが、上記キーは必須。
追加（プロセス別）例：
- preprocess: `processed_dataset_id`, `split_hash`, `recipe_hash`
- train_model: `processed_dataset_id`, `split_hash`, `model_id`, `primary_metric`, `best_score`, `task_type`, `n_classes`
- leaderboard: `recommended_train_task_id`, `recommended_model_id`, `excluded_count`

## HyperParameters（汚染防止：重要）
- **そのタスクの再現に必要な入力のみ**を記録する
- pipeline の設定や出力値を train の HyperParameters に混ぜない

## Artifacts（全タスク必須）
- `config_resolved.yaml`
- `out.json`
- `manifest.json`

プロセス別追加（例）：
- preprocess: `recipe.json`, `summary.md`, `preprocess_bundle.*`, `schema.json`
- train_model: `metrics.json`, `metrics_ci.json` (when `eval.ci.enabled=true`), `model_bundle/*`, `model_card.md`, `feature_importance.csv`, `feature_importance.png`, `residuals.png`, `confusion_matrix.csv`, `confusion_matrix.png`, `roc_curve.png`
- leaderboard: `leaderboard.csv`, `recommendation.json`, `summary.md`, `decision_summary.md`, `decision_summary.json`, `recommended_plot.png` (optional)
- pipeline: `pipeline_run.json`, `report.md`
- infer: `predictions.*`, `input_preview.*`, `drift_report.json`, `drift_report.md` (when drift enabled)

## Lint ルール（doctor/CI）
- 必須 artifact: `config_resolved.yaml`, `out.json`, `manifest.json`
- `manifest.json` 必須キー: `schema_version`, `code_version`, `platform_version`, `process`, `created_at`, `inputs`, `outputs`, `hashes.config_hash`
- `out.json` 必須キー（プロセス別）
  - dataset_register: `raw_dataset_id`
  - preprocess: `processed_dataset_id`, `split_hash`, `recipe_hash`
  - train_model: `model_id`, `primary_metric`, `best_score`, `task_type`
  - leaderboard: `leaderboard_csv`, `recommended_model_id`
  - infer: `predictions_path`
  - pipeline: `pipeline_run`
- 任意 artifact は **存在すれば整形チェックのみ**（JSON は parse、MD は空でないこと）
- 実行例: `python -m tabular_analysis.doctor --lint-run <output_dir> --mode fail`

## Plots（軽量デフォルト）
- デフォルトは軽い図（重要度・残差など）
- 例: `feature_importance.png`, `residuals.png`, `confusion_matrix.png`, `roc_curve.png`
- SHAP 等の重い可視化は config フラグでオンデマンド（デフォルトOFF）
