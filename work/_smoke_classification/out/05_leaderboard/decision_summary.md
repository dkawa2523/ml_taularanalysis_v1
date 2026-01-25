# Decision Summary

## Recommendation
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_classification/out/03_train_model/model_bundle.joblib
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_classification/out/03_train_model
- primary_metric: accuracy (maximize)
- best_score: 0.95
- ranking_score_key: best_score (maximize)
- task_type: classification
- n_classes: 2

## Comparability
- require_comparable: True
- processed_dataset_id: local:c85ab7f964e06c43fa5db1e6d9fc50f2facb82320be7b232790713c03ccfdee3
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- recipe_hash: d0bf0716f2ca34406944f5a1d6dc0c933b526ff12d5107c5121228f6f6fbfb8a
- primary_metric: accuracy
- direction: maximize
- task_type: classification
- seed: 42
- excluded_count: 0
- warning_count: 5 (see summary.md)

## Scoring
- normalization: minmax
- metrics: r2, rmse, mae, mse
- weights: r2=1.0, rmse=-1.0, mae=-0.5, mse=-0.2

## Top Models
- source: leaderboard.csv

| rank | model_variant | preprocess_variant | composite_score | best_score | primary_metric | ci |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | logistic_regression | stdscaler_ohe | n/a | 0.95 | accuracy | n/a |

## Extra Capabilities
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Promote Command
```bash
python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_classification/out/05_leaderboard
```
