# 03_CLEARML_UI_CONTRACT（ClearML UI 契約）

このドキュメントは **非DSユーザーが ClearML UI だけで判断できる**ための契約です。

## Project 階層（固定）
`MFG/<UseCase>/<Stage>`

例：
- `MFG/TabularAnalysis/01_dataset_register`
- `MFG/TabularAnalysis/02_preprocess`
- `MFG/TabularAnalysis/03_train_model`
- `MFG/TabularAnalysis/04_infer`
- `MFG/TabularAnalysis/05_leaderboard`
- `MFG/TabularAnalysis/99_pipeline`

## Task 名（推奨）
`<process>__<variant>__v<schema_version>`

例：
- `train_model__lgbm__preprocess=stdscaler_ohe__v1`

## Tags（最低限、固定キー）
- `usecase:<usecase_id>`
- `process:<process>`
- `schema:<schema_version>`
- `grid:<grid_run_id>`（pipeline 実行時）

## User Properties（固定キー）
- `usecase_id`
- `process`
- `schema_version`
- `code_version`
- `platform_version`
- `grid_run_id`

追加（プロセス別）例：
- preprocess: `processed_dataset_id`, `split_hash`, `recipe_hash`
- train_model: `processed_dataset_id`, `split_hash`, `model_id`, `primary_metric`, `best_score`
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
- train_model: `metrics.json`, `model_bundle/*`, `feature_importance.csv`
- leaderboard: `leaderboard.csv`, `recommendation.json`, `summary.md`
- infer: `predictions.*`, `input_preview.*`

## Plots（軽量デフォルト）
- デフォルトは軽い図（重要度・残差など）
- SHAP 等の重い可視化は config フラグでオンデマンド（デフォルトOFF）
