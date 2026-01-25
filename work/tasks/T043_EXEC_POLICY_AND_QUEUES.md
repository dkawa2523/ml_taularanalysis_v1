# T043 実行ポリシー（queue/予算/上限）標準化で“タスク爆発”を防ぐ

## Objective
- Grid/HPO/派生機能が増えても ClearML が破綻しないように、**実行ポリシー（queue/budget/上限）**を統一する
- pipeline がポリシーを強制し、意図せぬ “タスク爆発” を防ぐ
- ローカルでも同じ制約が効く（Dry-run/Plan で見える）状態にする

---

## Scope
### 1) exec_policy 設定の追加（Hydra）
- 例：`conf/run/exec_policy/base.yaml`
  - `limits.max_jobs`（生成して良い train の最大数）
  - `limits.max_models`（leaderboard に載せる最大モデル数）
  - `limits.max_hpo_trials`
  - `queues`：process→queue 名のマップ（ClearML有効時に利用）
  - `selection`：heavy 機能のデフォルトOFF（例：shap/calibration/uncertainty など）
- 既存 config 構造を壊さずに group として追加

### 2) pipeline の enforcing
- `pipeline` は組合せ生成前に `max_jobs` を見て制限する
- `--plan` / `dry_run` 的なモード（既存があれば拡張）で、実際に実行せず「何ジョブ走るか」を出力できる
- 実行時は `pipeline_run.json` に
  - `planned_jobs`
  - `executed_jobs`
  - `skipped_due_to_policy`
  を明記

### 3) ClearML 有効時の queue 選択
- process/model の種類に応じて queue 名を選べること（例：heavy モデルは heavy queue）
- queue 名は config で上書き可能だが、デフォルトは用途に沿ったものに固定

---

## Acceptance Criteria
- `exec_policy` を設定することで pipeline が `max_jobs` を超えない
- plan/dry-run で “何が走る予定か” を artifact に出せる
- ClearML 無効でも verify が通る（queue 連携部分は no-op）
- docs（`docs/22_EXECUTION_POLICY.md`）が追加され、運用ルールが明文化されている

---

## Verification
```bash
python -m compileall -q src
python tools/tests/test_exec_policy.py
```
