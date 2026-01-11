# 10_OPERATION_MODES（実行モード）

実行モードは `run.clearml.execution` で切り替えます。

- `local`：ClearML を使わずローカル実行（開発・デバッグ）
- `logging`：ローカル実行しつつ ClearML に記録
- `agent`：`Task.execute_remotely(queue=...)` で投入
- `clone`：テンプレ Task を clone して投入（運用品質）
- `pipeline_controller`：PipelineController で子タスクを生成

## 推奨フロー
1. 開発初期は `local` で速く回す
2. UI 契約確認は `logging` を使う
3. 運用は `agent` or `clone` を UseCase ごとに固定

## Pipeline HPO grid (small)
- Enable with `pipeline.hpo.enabled=true`
- Define per-model grids under `pipeline.hpo.params.<model>` (example: ridge alpha list)
- Each train run emits its own artifacts; ClearML tags include `hpo:<hpo_run_id>` for filtering

## 事前チェック（doctor）
- ClearML 接続確認（enabled=true の場合）
- queue 名・clone template task_id の存在確認
- ml_platform の version / import 確認
