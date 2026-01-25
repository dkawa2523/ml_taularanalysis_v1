# T049 Retrain Orchestration（監視→再学習→比較→任意promote）

## Objective
- drift/品質の検知結果を「再学習」へ接続し、運用ループを完成させる
- retrain の結果を champion と比較し、採用判断（auto_promoteはオプション）を出力する
- ClearML 有効時は “ひとまとまり” として追える（grid_run_id / retrain_run_id）ようにする

---

## Scope
### 1) retrain プロセス追加
- 新規：`retrain`
  - 入力：
    - `dataset_path` / `dataset_id`（最新データ）
    - `baseline_stage`（既定 production）
    - `auto_promote`（default false）
    - `promote_criteria`（例：metric 改善幅、CI で劣化していない等）
  - 実行：
    - pipeline を再実行（exec_policy を尊重）
    - recommendation を取得
    - champion-challenger を実行して差分を算出
  - 出力：
    - `retrain_summary.md`
    - `retrain_decision.json`（採用/不採用、理由、差分、注意点）
    - `retrain_run.json`（関連タスクの参照一覧）

### 2) opt-in で auto_promote
- auto_promote=true の場合のみ promote_model を呼ぶ
- promote の前に “比較可能性” を確認し、満たせない場合は明確に skip する

### 3) docs
- `docs/28_RETRAIN.md` を追加し、運用手順（監視→retrain→promote）を整理

---

## Acceptance Criteria
- ローカルで retrain が動き、decision が生成される
- auto_promote=false では registry 状態を変えない
- ClearML 無効でも verify が通る

---

## Verification
```bash
python -m compileall -q src
python tools/tests/test_retrain_local.py
```
