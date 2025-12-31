# T006 train_model 実装: 学習 + model_bundle + metrics

## Objective
- preprocess の出力（processed_dataset_id / split / preprocess_bundle）を入力として、モデルを学習し、比較可能な metrics を出力する
- model を bundle 化して infer で再利用できる状態にする

## Inputs
- preprocess の out.json（少なくとも processed_dataset_id / split_hash / recipe_hash）
- preprocess bundle artifact（preprocess_bundle.joblib）
- `train.model`（conf/group/model/*.yaml）
- `eval.*`（primary_metric, direction, cv_folds, seed）

## Required Outputs
- `out.json`
  - `model_id`（ClearML Model ID または local path）
  - `train_task_id`（ClearML task id。local では null 可）
  - `best_score`
  - `primary_metric`
  - `processed_dataset_id`, `split_hash`, `recipe_hash`
- `manifest.json`
- 追加 Artifacts（最低限）
  - `metrics.json`
  - `model_bundle.joblib`

## Implementation Notes
- `registry/models.py` で model_variant を解釈してモデルを生成する（importlib で class_path から import）
- `registry/metrics.py` で rmse/mae/r2 を提供する（sklearn.metrics を使用）
- leakage 防止：preprocess bundle は **train split で fit 済み**が前提（T005）。train_model 側で再 fit しない（禁止）
- best_score は eval.direction（minimize/maximize）で解釈し、properties にも入れる（docs/03）

## Acceptance Criteria
- local モードで train_model が完走し、outputs/03_train_model/ に out.json/manifest.json/metrics.json/model_bundle.joblib が生成される
- 同じ split_hash / processed_dataset_id の条件で leaderboard が比較可能になる（T007で検証）

## Verification（例）
T005 の preprocess 実行後に続けて実行できるように実装してください。
```bash
python -m tabular_analysis.cli task=train_model run.clearml.enabled=false
```

> NOTE: この段階では「入力の受け渡し」をどう解決するかが重要です。推奨は次のいずれか：
> - `train` config に `inputs.preprocess_run_dir` を持たせてそこから artifacts を読む
> - ClearML enabled 時は preprocess task_id を指定して artifacts を引く
> どちらにするかは T006 内で決め、docs/05 と out.json 契約に反映してください。
