# T009 pipeline 実装: grid 実行 + task_id 受け渡し

## Objective
- pipeline を「接着剤」として実装し、grid（preprocess×model）を安全に回せるようにする
- pipeline 自体は重い処理を持たず、各独立タスクの実行計画・起動・ID受け渡しを担当する

## Inputs
- `pipeline.*`（conf/task/pipeline/base.yaml）
  - run_dataset_register/run_preprocess/run_train/run_leaderboard/run_infer
  - grid.preprocess_variants / grid.model_variants / max_jobs

## Required Outputs
- `pipeline_run.json`
  - grid_run_id
  - dataset_register_ref
  - preprocess_ref
  - train_refs[...] (variant metadata + task_id or run_dir)
  - leaderboard_ref
  - infer_ref

## Implementation Notes
- local モード（run.clearml.execution=local）では、まず「サブプロセス実行」で確実に分離する
  - 例: `python -m tabular_analysis.cli task=preprocess ...` を subprocess で呼ぶ
  - 出力ディレクトリを stage ごとに分け、out.json で次工程へ渡す
- ClearML enabled の場合は platform の機能を使って agent/clone 実行へ投げる（実行戦略は docs/10）
- grid_run_id は UUID などで生成し、全タスクに tags/properties で付与する（docs/03）

## Acceptance Criteria
- local モードで pipeline が完走し、pipeline_run.json が出力される
- grid の組み合わせ数が max_jobs を超える場合にエラーまたは制限される

## Verification（例）
```bash
python -m tabular_analysis.cli task=pipeline run.clearml.enabled=false run.clearml.execution=local
```
