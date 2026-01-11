# 学習パイプライン（回帰） 契約 v1（update-3_clearml）

## 目的
- pipeline は **ClearML Dataset 登録から始めない**。ユーザーは事前に `dataset_register` を実行し、`raw_dataset_id` を得る。
- pipeline は `raw_dataset_id`（= ClearML Dataset ID）を入力として、以下を一括実行する:
  1) preprocess（選択した前処理 variant）
  2) train_model（回帰モデルを複数。基本は「回帰ほぼ全て」= model_set）
  3) leaderboard（比較・評価・推薦）
- ClearML 上では **個別タスクとして実行され、追跡・比較が可能**であること。

## 入力
- 必須: `data.raw_dataset_id`
- 任意: `pipeline.run_dataset_register`（default: false。true の場合のみ dataset_register を実行）
- 任意: `pipeline.preprocess_variant`
- 任意: `pipeline.model_set`（例: `regression_all`）または `pipeline.model_variants`（明示リスト）
- 任意: `eval.metrics`（標準: R2, MSE, RMSE, MAE）

### model_set の解決
- `pipeline.model_set` は `conf/pipeline/model_sets/<name>.yaml` を参照し、`pipeline.model_variants` に展開される。
- `auto: true` の場合は registry の `list_model_variants(task_type=...)` で自動列挙する（`model_variant.class_path` の regression/classification 定義 or `model_variant.task_type` を参照）。
- 固定リスト運用にしたい場合は `variants` を明示し、新しい回帰モデルを追加したら `conf/pipeline/model_sets/regression_all.yaml` を更新する。

## 出力
- preprocess: `processed_dataset_id`（ClearML Dataset）
- train_model: `model_id`（ClearML Model Registry 参照） + 指標（Scalars/Plots）
- leaderboard: `leaderboard.csv` + `recommendation.json`（推奨モデル）

## 運用上の前提
- dataset_register はローカル実行で良い（試験段階）。社内サーバ移行時も同じ。
- pipeline は `data.raw_dataset_id` 入力を前提とし、`data.dataset_path` は dataset_register のみに使う。
- pipeline は ClearML PipelineController で実行し、UI 左タブ **PIPELINES** に表示されることを目標。
- ローカルで一括実行したい場合は、別途 `local_orchestrator` を使う（docs/67）。

## タスク名 / タグ / Properties
- 命名/タグ/Properties は `docs/66_NAMING_TAGGING_POLICY.md` を単一の正とする。
- pipeline 実行時は `run.grid_run_id` が各タスクに伝播し、`grid:<grid_run_id>` が付与される。
