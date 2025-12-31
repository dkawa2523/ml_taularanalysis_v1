# 10_OPERATION_MODES（実行モード）

実行モードは `run.clearml.execution` で切り替えます。

- `local`：ClearML を使わずローカル実行（開発・デバッグ）
- `logging`：ローカル実行しつつ ClearML に記録
- `agent`：`Task.execute_remotely(queue=...)` で投入
- `clone`：テンプレ Task を clone して投入（運用品質）

## 推奨フロー
1. 開発初期は `local` で速く回す
2. UI 契約確認は `logging` を使う
3. 運用は `agent` or `clone` を UseCase ごとに固定

## 事前チェック（doctor）
- ClearML 接続確認（enabled=true の場合）
- queue 名・clone template task_id の存在確認
- ml_platform の version / import 確認
