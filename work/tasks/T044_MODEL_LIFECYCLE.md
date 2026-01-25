# T044 Model Lifecycle 完成（promote/rollback/champion-challenger）

## Objective
- recommendation（推奨）と promote（採用）を運用として分離し、**モデルのライフサイクル**を完成させる
- rollback（前の production へ戻す）と champion-challenger 比較（現行production vs 新候補）を提供する
- ClearML が無い環境でも “ローカルレジストリ状態” で同等の運用検証ができるようにする

---

## Scope
### 1) rollback_model プロセス追加
- 新規：`rollback_model`
  - 入力：`stage`（例：production）、`reason`、（任意）`target_model_id`
  - 挙動：
    - ClearML 有効：Model Registry の tag/property を更新して “前の production” に戻す
    - ClearML 無効：`run.output_dir/model_registry_state.json` のようなローカル状態で stage を更新
  - 出力：`rollback.json`（before/after の model_ref、理由、timestamp）

### 2) champion_challenger プロセス追加
- 新規：`champion_challenger`
  - 入力：`champion_model_ref`（省略時は production）、`challenger_model_ref`、`eval_dataset_ref`
  - comparability：
    - 同一の processed_dataset_id + split_hash を優先（無ければ明確に warn）
  - 出力：
    - `champion_challenger.csv`（両者の主要指標、差分）
    - `decision.json`（勝者、差分、根拠、注意点）
    - `summary.md`（非DS向けに結論を明文化）
- 既存の leaderboard/recommendation を活用しつつ “運用意思決定” に寄せる

### 3) docs
- `docs/23_MODEL_LIFECYCLE.md` 追加
  - promote/rollback/champion-challenger の意味
  - ClearML有効/無効の差
  - UI上で見るべきポイント（properties/tags）

---

## Acceptance Criteria
- rollback_model がローカルモードで動作し、state が更新される
- champion_challenger がローカルで動作し、比較表と decision が出る
- ClearML 有効時は registry 操作が adapter 経由で行える（ただし verify は offline で通る設計）
- docs が整備されている

---

## Verification
```bash
python -m compileall -q src
python tools/tests/test_model_lifecycle_local.py
```
