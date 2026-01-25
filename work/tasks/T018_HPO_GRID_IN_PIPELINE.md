# T018 HPO基盤: pipeline にパラメータグリッド探索を追加（小さく）

## Objective
- まずは「複雑な最適化（Optuna等）」ではなく、**再現性が高いグリッド探索**を pipeline に追加する
- 非DSユーザーでも「数パターン試してベストを選ぶ」ことができるようにする
- 追跡性: 各 trial は train_model の独立実行として残す（leaderboard で比較可能にする）

---

## Scope
1) pipeline 設定に “小さな” HPO グリッドを追加
   - 例: `pipeline.hpo.enabled`
   - 例: `pipeline.hpo.params`（モデルごとにパラメータ候補を定義）
2) pipeline 実装を拡張
   - 既存の model×preprocess の grid に加え、**param の組合せ**も展開
   - 生成した各 train run を `grid_run_id` / `hpo_run_id` でタグ付け（ClearML でも追跡できる）
3) 既存の leaderboard をそのまま使ってベストを選ぶ（ロジックを二重化しない）
4) テスト追加: `tools/tests/smoke_hpo.py`
   - toy データで ridge の alpha を `[0.1, 1.0, 10.0]` のように3通り試す
   - pipeline が完走し、train_model の成果物が複数残り、leaderboard が推薦を出すことを確認

---

## Implementation Notes
- “探索のために train_model を改造して内部ループ” は避ける  
  -> 独立タスク（比較可能な out/manifest）を増やす方針が本プロジェクトの設計（plan2）に合う
- 初期は ridge のみでよい（他モデルは後続で拡張）

---

## Acceptance Criteria
- pipeline で HPO グリッドが有効化できる
- 3通り以上の train run が生成され、leaderboard で比較・推薦できる
- smoke_hpo.py が通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_hpo.py`

---

## Update (2026-01-13)
- `smoke_hpo.py` で dataset_register を先に実行し、`data.raw_dataset_id` を pipeline に渡すように変更
