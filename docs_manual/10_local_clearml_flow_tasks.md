# Local実行＋SPDML結果登録の処理フロー（タスク別詳細）

## 1. 処理フロー（Mermaid）
```mermaid
flowchart TD
  A[dataset_register] --> B[preprocess]
  B --> C1[train_model ...]
  B --> C2[train_model ...]
  C1 --> D[train_ensemble (optional)]
  C2 --> D
  C1 --> E[leaderboard]
  C2 --> E
  D --> E
  E --> F[infer]
```

## 2. SPDML タスクのプロジェクト階層
| タスク | プロジェクト階層 | 目的 | 主要ログ/成果物 |
| --- | --- | --- | --- |
| dataset_register | `.../01_Datasets` | raw dataset登録 | schema/preview/out.json |
| preprocess | `.../02_Preprocess` | processed dataset生成 | recipe/splits/processed_dataset_id |
| train_model | `.../03_TrainModels` | モデル学習 | metrics/model_bundle |
| train_ensemble | `.../04_Ensembles` | アンサンブル学習 | ensemble_spec/model_bundle |
| infer | `.../05_Infer` | 推論 | predictions/plots |
| leaderboard | `.../00_Pipelines` | 比較と推奨 | leaderboard.csv/recommendation |
| pipeline | `.../00_Pipelines` | 接着/計画 | plan.json/run_summary |

## 3. 各タスクの実行内容と SPDML 連携
| タスク | 実行内容 | SPDML 連携 | 備考 |
| --- | --- | --- | --- |
| dataset_register | rawデータ解析/登録 | Dataset登録/Plots | quality gateを実行 |
| preprocess | 前処理+split固定 | processed dataset登録 | bundle保存 |
| train_model | 学習/評価 | Model登録/Plots | optional依存はSKIP |
| train_ensemble | 予測統合 | Model登録/Plots | ensemble.enabled=true時 |
| leaderboard | 比較/推奨 | レポート出力 | comparability判定 |
| infer | 推論 | input/output table | batch/optimize対応 |

## 4. 複数タスクの実行方式
- local/logging: local_sequentialで逐次実行
- pipeline_controllerはここでは使わない

## 5. ユーザー操作ぶれへの工夫
- `grid_run_id` を各タスクに伝播しタグ化
- templateやタグ規約で検索キーを固定
- SKIP時は `status=skipped` と `reason` を出力
