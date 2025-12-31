# T007 leaderboard 実装: 比較可能性チェック + 推奨

## Objective
- 複数の train_model 実行結果を集計し、比較可能性を担保した leaderboard を生成する
- 非DSが「どれを採用すべきか」を迷わないように、recommendation を出力する

## Inputs
- ClearML enabled 時：`leaderboard.train_task_ids`（train task id の配列）
- ClearML disabled 時：`leaderboard.train_run_dirs`（ローカル run ディレクトリの配列）

## Required Outputs
- `leaderboard.csv`
  - columns: rank, best_score, primary_metric, model_id, preprocess_variant, model_variant, train_task_ref, processed_dataset_id, split_hash
- `recommendation.json`
  - `recommended_*` (train_task_ref, model_id, best_score, primary_metric)
- `out.json`
  - `recommended_train_task_id`/`recommended_model_id`/...（local 時は id を null にして ref を持たせてもよい）

## Implementation Notes
- 比較可能性のチェック：docs/07
- `require_comparable=true` の場合は、(processed_dataset_id, split_hash) が一致しないものを除外し、excluded_count を出す
- ranking は eval.direction に従う
- ClearML enabled では train task から properties と artifacts(out.json) を取得できるようにする（platform に util がある場合は使う）

## Acceptance Criteria
- local モードで leaderboard が完走し、leaderboard.csv と recommendation.json が生成される
- `excluded_count` が out.json に出力される

## Verification（例）
```bash
python -m tabular_analysis.cli task=leaderboard run.clearml.enabled=false
```

> NOTE: T006 で決めた「train の入力受け渡し方式」に合わせて、leaderboard の入力も一貫した形にしてください。
