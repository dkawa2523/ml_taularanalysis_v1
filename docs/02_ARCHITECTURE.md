# 02_ARCHITECTURE（全体アーキテクチャ）

## 原則
- 各プロセスは **独立タスク**として実行可能
- 追跡性は **manifest/out.json/properties** によって担保
- 親子タスクは作らない（UI の迷い・再実行のしにくさを回避）

## タスクの依存関係（概略）

```mermaid
flowchart LR
  A[dataset_register] --> B[preprocess]
  B --> C1[train_model ...]
  B --> C2[train_model ...]
  C1 --> D[leaderboard]
  C2 --> D
  D --> E[infer]

  P[pipeline] --> A
  P --> B
  P --> C1
  P --> C2
  P --> D
  P --> E
```

- `pipeline` は「接着剤」。重い処理を持たず、IDの受け渡しと実行制御を行う。
- `leaderboard` は比較と推奨の唯一の場所。

## Metadata Linking（追跡性）
- 各タスクは `out.json` と `manifest.json` を出力する
- `pipeline` は `pipeline_run.json` を出力し、実行した task_id 一覧を保存する
- 比較可能性のキー：`processed_dataset_id` と `split_hash`
