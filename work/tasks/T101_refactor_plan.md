# T101 Refactor Plan: Spec Alignment (Pipeline v2 / Ensemble / Rehearsal)

## 目的
- docs と実装の齟齬を解消し、ClearML UI 契約どおりに実行できる状態へ戻す
- 既存の設計思想（薄いClearML層 / plan共有 / 冗長化回避）を崩さずに修正する

## 現状の主な課題（優先度順）
### P0
1) Pipeline v2 仕様が未実装
   - `plan.json` / `run_summary.json` / fail_policy / groups/profile が未反映
   - docs: `docs/60_PIPELINE_TRAIN_CONTRACT.md` / `docs/52_CLEARML_PIPELINE_CONTROLLER_CONTRACT.md`

2) Ensemble が未実装
   - `train_ensemble` が存在せず、leaderboard で比較できない
   - docs: `docs/83_ENSEMBLE_POLICY.md` / `docs/55_CLEARML_UI_CHECKLIST.md`

3) Rehearsal runner と UI audit の不足
   - docs が参照する `run_pipeline_v2.py` / `rehearsal_verify_clearml_ui.py` が無い
   - `run_rehearsal.py` は pipeline 入力契約（raw_dataset_id 必須）と噛み合っていない

### P1
4) ClearML reporting toggle 未実装
   - `run.clearml.reporting.*` が無く、Scalars/Plots/Debug Samples を抑制できない

5) ClearML code_ref 設定の不整合
   - docs は `run.clearml.code_ref.*`、実装は `run.clearml.code_repository` / `code_branch` が主
   - HyperParameters は alias で暫定対応済み、config と script 生成は未統一

6) Template Project レイアウトのズレ
   - `conf/clearml/templates.yaml` の project 名が UI 契約の group 名と一致しない

## 提案する修正方針（段階的）
### Phase 1: 実行基盤の整合
- T077: `code_ref` の config / script 生成統一
- T082: reporting toggle 実装
- T079: template project 名を project_layout に合わせて再整理
- T087/T096/T100: rehearsal runner & UI audit の実装/差し替え

### Phase 2: Pipeline v2 の実装
- T089/T091: profile+groups を plan へ反映
- T093/T094: fail_policy / run_summary / limits の実装
- T095: Local/Agent で plan 共有の見え方一致を確認

### Phase 3: Ensemble 実装
- T083/T084/T085: mean_topk / weighted / stacking を追加
- T086: leaderboard で比較・推薦

### Phase 4: Docs と運用の再整備
- T098/T099: UI checklist / docs の整合確認
- ClearML UI での再確認（logging / pipeline_controller）

## 既存タスクとの関係
- Pipeline v2: T089, T091, T093, T094, T095
- Ensemble: T083, T084, T085, T086
- Rehearsal/UI audit: T087, T096, T100
- ClearML設定統一: T077, T079, T082
- Docs整合: T098, T099

## 検証
- `PYTHONPATH=src python3 tools/tests/verify_all.py --quick`
- logging + pipeline_controller で UI 契約を再確認（`docs/55_CLEARML_UI_CHECKLIST.md`）
