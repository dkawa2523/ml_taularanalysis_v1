# 84_REHEARSAL_GUIDE（リハーサル手順と切替ポイント）

## 目的
試験段階のリハーサルを **毎回同じ手順**で実行し、
ローカル ClearML から社内 ClearML への移行をスムーズにする。

## 主要ツール（tools/rehearsal/）
- `run_rehearsal.py`:
  - mode: `local` / `logging`
  - 生成物: `work/rehearsal/out/` と `work/rehearsal/rehearsal_log.md`
- `run_pipeline_v2.py`:
  - dataset_register + pipeline + 自動検証（local / logging / agent）
  - `usecase_id` / `pipeline_task_id` / `dataset_id` を最後に表示
- `run_train_pipeline.py`:
  - `run_pipeline_v2.py` の互換 runner（旧名）
- `inspect_clearml_usecase.py`:
  - usecase_id タグで ClearML Task 一覧を表示
- `plan_migration.py`:
  - local -> internal の差分チェック支援

`run_pipeline_v2.py` の自動検証（最低限）:
- usecase タグで pipeline / preprocess / train / ensemble / leaderboard が存在
- Project 階層が `<ROOT>/<solution_root>/<usecase_id>/<process_group>` に沿う
- HyperParameters がカテゴリ分割されている
- Scalars / Plots が空ではない
- processed dataset のファイルと meta.json のキーが揃っている
- pipeline task に `run_summary.json` が紐づいている

## リハーサルの基本手順
### 1) 完全ローカル（ClearML 無効）
```bash
python tools/rehearsal/run_pipeline_v2.py --execution local \
  --task-type regression --preprocess stdscaler_ohe --models ridge,elasticnet
```
- 目的: 処理が完走することを確認

### 2) ローカル ClearML（logging）
```bash
python tools/rehearsal/run_pipeline_v2.py --execution logging \
  --task-type regression --preprocess stdscaler_ohe --models ridge,elasticnet \
  --project-root LOCAL
```
- 目的: UI 契約（Artifacts/Tags/Properties/Project）を確認

### 3) PipelineController + Agent
```bash
# テンプレ作成（未作成の場合）
python -m tabular_analysis.ops.manage_clearml_templates --apply --project-root LOCAL

# Agent 起動（queue は合わせる）
# clearml-agent daemon --queue default --foreground

# PipelineController 実行
python tools/rehearsal/run_pipeline_v2.py --execution agent --queue-name default \
  --task-type regression --preprocess stdscaler_ohe --models ridge,elasticnet \
  --project-root LOCAL
```
- 目的: 子タスク生成・queue 投入・PIPELINES 表示を確認
- pipeline_controller は template clone 前提。commit pin 回避は `docs/69_CLEARML_TROUBLESHOOTING.md` を参照。

### 4) ClearML の Task 一覧チェック
```bash
python tools/rehearsal/inspect_clearml_usecase.py --usecase-id <USECASE_ID>
```

### 4.5) ClearML UI 構造の自動検証（T100）
```bash
python tools/tests/rehearsal_verify_clearml_ui.py --usecase-id <USECASE_ID>
```
- pipeline/child task の存在、commit pin、HyperParameters セクション分割を確認

## ローカル -> 社内 ClearML へ切替えるポイント
1) `clearml.conf` または環境変数（API/WEB/FILES）を切替
2) まず logging で実行し、Artifacts の保存先/権限/容量を確認
3) Agent 実行に進む（queue 設定・Agent 環境の差分に注意）
4) 差分は `docs/issues/` に記録

補助ツール:
```bash
python tools/rehearsal/plan_migration.py --from local --to internal
```

## 失敗したときに見る場所
- `<output_dir>/99_pipeline/run_summary.json`: fail/skip の集計と理由
- 各タスクの `skip_reason.json`: skip 時の詳細
- `conf/run/base.yaml` の `run.clearml.template_set_id`: agent/テンプレの世代ズレ確認
- `<output_dir>/99_pipeline/report_links.json`: ClearML task_id の対応表

## 変更ポイントまとめ
- `conf/run/base.yaml`: `run.clearml.enabled` / `run.clearml.execution`
- `conf/clearml/project_layout.yaml`: Project 階層
- `conf/clearml/templates.yaml`: テンプレ Task の project/entrypoint
- 事前チェックは `docs/42_REHEARSAL_SCENARIOS.md` / `docs/67_REHEARSAL_COMMANDS.md` を参照
