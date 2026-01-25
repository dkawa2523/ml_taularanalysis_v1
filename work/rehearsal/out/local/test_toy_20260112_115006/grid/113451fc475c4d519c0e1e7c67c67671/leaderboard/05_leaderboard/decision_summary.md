# Decision Summary

## Recommendation
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260112_115006/grid/113451fc475c4d519c0e1e7c67c67671/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260112_115006/grid/113451fc475c4d519c0e1e7c67c67671/train__stdscaler_ohe__ridge/03_train_model
- primary_metric: rmse (minimize)
- best_score: 0.00863873
- ranking_score_key: composite_score (maximize)
- composite_score: 0
- task_type: regression

## Comparability
- require_comparable: True
- processed_dataset_id: local:17ffec56dcf6c9291a80a2ea4716e01ef4f0cd45976727b8eba6b0f4206c8123
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- recipe_hash: d0bf0716f2ca34406944f5a1d6dc0c933b526ff12d5107c5121228f6f6fbfb8a
- primary_metric: rmse
- direction: minimize
- task_type: regression
- seed: 42
- excluded_count: 0

## Scoring
- normalization: minmax
- metrics: r2, rmse, mae, mse
- weights: r2=1.0, rmse=-1.0, mae=-0.5, mse=-0.2

## Top Models
- source: leaderboard.csv

| rank | model_variant | preprocess_variant | composite_score | best_score | primary_metric | ci |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | ridge | stdscaler_ohe | 0 | 0.00863873 | rmse | n/a |

## Extra Capabilities
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Promote Command
```bash
python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260112_115006/grid/113451fc475c4d519c0e1e7c67c67671/leaderboard/05_leaderboard
```
