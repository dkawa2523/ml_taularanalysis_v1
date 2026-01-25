# T049 Retrain Orchestration（監視→再学習→推薦）

## Objective
- drift/品質の検知結果を「再学習」へ接続し、運用ループを完成させる
- retrain の結果を recommendation として記録し、推論時の選択に使える状態にする
- ClearML 有効時は “ひとまとまり” として追える（grid_run_id / retrain_run_id）ようにする

---

## Scope
### 1) retrain プロセス追加
- 新規：`retrain`
  - 入力：
    - `dataset_path` / `dataset_id`（最新データ）
  - 実行：
    - pipeline を再実行（exec_policy を尊重）
    - recommendation を取得
  - 出力：
    - `retrain_summary.md`
    - `retrain_decision.json`（推薦モデル、理由）
    - `retrain_run.json`（関連タスクの参照一覧）

### 2) docs
- `docs/28_RETRAIN.md` を追加し、運用手順（監視→retrain→推薦）を整理

---

## Acceptance Criteria
- ローカルで retrain が動き、decision が生成される
- ClearML 無効でも verify が通る

---

## Verification
```bash
python -m compileall -q src
python tools/tests/test_retrain_local.py
```
