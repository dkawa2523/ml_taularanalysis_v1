# T008 infer 実装: single/batch（optimizeは任意）

## Objective
- train_model が出力した model_bundle を読み込み、推論を実行する
- single/batch の 2モードをまず確実に実装する（optimize は後回し可）

## Inputs
- ClearML enabled 時：`infer.train_task_id` または `infer.model_id`
- ClearML disabled 時：`infer.model_bundle_path`
- `infer.mode`（conf/group/infer_mode/*.yaml）

## Required Outputs
- `predictions.csv`（batch の場合）または `prediction.json`（single の場合）
- `out.json`（predictions_path 等）
- `manifest.json`

## Implementation Notes
- model_bundle には以下が入っている想定：
  - model
  - preprocess_bundle（fitted pipeline）
  - schema（入力検証用）
- batch の入力は CSV を基本とする（target_column は存在しなくてよい）
- single の入力は JSON（key: column_name -> value）

## Acceptance Criteria
- local モードで single/batch 推論が完走し、予測が保存される
- preprocess と一致した変換が適用される（fit はしない）

## Verification（例）
```bash
python -m tabular_analysis.cli task=infer run.clearml.enabled=false
```
