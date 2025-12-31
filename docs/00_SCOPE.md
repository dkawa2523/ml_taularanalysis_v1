# 00_SCOPE（スコープ）

この Solution（ml-solution-tabular-analysis）は **テーブル（tabular）データ**の
学習・比較・推論を、ClearML 上で再利用可能な独立タスクとして提供することを目的とします。

## 対象（in-scope）
- 入力：CSV/Parquet 等の 2次元テーブル
- 目的変数：1列（まずは回帰を主対象。分類は後続で拡張）
- 基本フロー：
  - dataset_register → preprocess（split固定） → train_model（複数） → leaderboard → infer → pipeline（接着剤）

## 重要な方針（不変）
- **親子タスクを作らない**：比較と判断は leaderboard、接着は pipeline
- **比較可能性を壊さない**：split は preprocess の責務。train は再分割しない
- **追跡性を必須化**：全タスクで config_resolved.yaml / out.json / manifest.json を保存

## 対象外（out-of-scope）
- 画像/音声/NLP 等（別 Solution repo を作る）
- 大規模分散学習
- 例外的なドメイン固有処理を platform に入れること（禁止）
