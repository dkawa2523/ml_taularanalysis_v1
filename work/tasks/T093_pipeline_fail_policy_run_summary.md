# T093 Pipeline: 部分失敗（partial failure）ポリシーを固定し、run_summary.json を必ず生成する

## 背景
- optional deps / inapplicable を SKIP にしたことで、pipeline は “全部成功” だけでなく、
  - 一部 SKIP
  - 一部 FAIL
  でも、業務上は有用なケースが増える。
- そのため pipeline の成否判定を「固定ルール」として明文化し、実装で統一する必要がある。

## ゴール
1. `pipeline.fail_policy` を実装し、以下を pipeline の共通ルールとして固定する：
   - `allow_skipped: bool`
   - `allowed_failures: int`
   - `fail_fast: bool`
   - `min_successful_train_tasks: int`
2. pipeline controller タスク（または pipeline 実行の親タスク）に必ず artifact を残す：
   - `plan.json`（T091 の plan）
   - `run_summary.json`（成功/失敗/skip の一覧、推薦/最良、リンク）
3. 成否判定：
   - successful_train >= min_successful_train_tasks かつ allowed_failures 以内なら SUCCESS（degraded を summary に記録）
   - それ以外は FAILED
4. leaderboard の出力がある場合は、それを “最終意思決定” の入口にする（推薦/比較）

## 非ゴール
- Local/Agent driver 統一（T095）。
- UIのグラフ拡充（既存の仕組みを壊さず、summaryを追加する）。

## 作業手順
### 1) 現行 pipeline の親タスクがどこで終了するか確認
- pipeline controller（ClearML PipelineController）を使う場合、どの時点で “pipelineタスク” が終了扱いになるか確認。
- Local 実行時も同様に親タスクがあるのか確認（無ければ driver 側で親タスクを作るのはT095）。

### 2) run_summary のスキーマ設計（最小）
含めるべき情報：
- usecase_id / project_root / code_identity（repo/branch/commit）
- preprocess_variants 実行結果（status, ids）
- train_tasks 実行結果（status, model_id, metrics への参照）
- ensemble_tasks 実行結果（status, method, 参照）
- leaderboard の参照（task_id / artifact path）
- 推薦候補（best model / best ensemble）とその理由（primary_metric）
- degraded フラグ（skip/failの有無）

### 3) 失敗/skip の集計ロジックを実装
- T092 の SKIP/FAIL の情報を用いて集計する。
- allowed_failures を超えたら fail_fast=True の場合は早期停止できるようにする（実行方式が可能なら）。
- min_successful_train_tasks を下回る場合は最終的に FAILED。

### 4) artifact 出力（ClearML / local 両対応）
- ClearML 有効時：Task の artifact として `plan.json` と `run_summary.json` をアップロード
- ClearML 無効時：`run.output_dir` 配下に同じファイルを保存（ローカル検証のため）

### 5) docs: ルール固定を明文化
- “部分失敗とは何か”
- “SKIP は成功とは別扱いだが、allow_skipped で許容できる”
- “fail_policy の推奨値（試験段階/本番段階）”
を docs に追記。

## 受け入れ基準
- pipeline 実行の最後に `run_summary.json` が必ず生成される（ClearML on/off 両方）。
- SKIP/FAIL が混ざっても、fail_policy に基づき SUCCESS/FAILED が一貫して判定される。
- leaderboard が存在する場合、summary に推薦（best）が記載される。

## テスト
- `python -m compileall -q src`
- toy 実行で、意図的に 1モデルを SKIP（missing deps）にしても pipeline が成功扱いになる（min_successful_train_tasks を満たす）
- 意図的に多く失敗させて allowed_failures を超えた場合に FAILED になる

---

## Update (2026-01-13)
- `plan.json` / `run_summary.json` の生成は未実装で、Phase 2 (T101) の中核対応
