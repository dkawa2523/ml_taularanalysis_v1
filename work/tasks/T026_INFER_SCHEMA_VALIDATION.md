# T026 推論の堅牢化: 入力スキーマ検証 + エラーレポート（strict/warn/coerce）

## Objective
- 推論入力が学習時スキーマとズレた時に "静かに壊れる" のを防ぐ
- エラー時も "何が足りない/違う" が追えるように、errors.json/csv を出す

---

## Scope
1) infer config 追加
- `conf/task/infer/base.yaml` に `infer.validation.mode: warn` を追加
  - `warn`（デフォルト）: warning を summary に書き、可能なら欠損列は NaN 埋めで続行
  - `strict`: 不一致があれば失敗（非ゼロ）
  - `coerce`: 型変換を試みる（失敗したセルは NaN 等）

2) infer 実装
- model_bundle から期待特徴量（schema）を取得できるようにし、入力 df の列名・型を検証
- 以下を `infer_dir/errors.json` と `errors.csv` に記録（ある場合）
  - missing_columns
  - extra_columns
  - dtype_mismatch
  - coerce_failures（行/列/理由）

3) 出力契約
- `out.json` に以下を追加（必須）
  - `schema_validation: {mode, ok, warnings_count, errors_count}`
  - `errors_path`（errors がある場合）

4) テスト追加
- `tools/tests/smoke_infer_schema_validation.py`
  - train_model まで実行
  - infer 用入力データから 1 列落として infer を実行
  - warn モード: 完走し、errors.json が出る
  - strict モード: 失敗する（return code != 0）

---

## Acceptance Criteria
- warn/strict/coerce が切り替えられる
- warn では完走 + errors が出る
- strict では失敗
- smoke_infer_schema_validation.py が通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_infer_schema_validation.py`
