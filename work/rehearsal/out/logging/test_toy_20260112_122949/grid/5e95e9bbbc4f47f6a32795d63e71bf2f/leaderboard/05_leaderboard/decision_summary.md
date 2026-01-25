# Decision Summary

## Recommendation
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122949/grid/5e95e9bbbc4f47f6a32795d63e71bf2f/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- train_task_ref: 846aabb45c5d4e4ba0848eee24dca8ac
- primary_metric: rmse (minimize)
- best_score: 0.00863873
- ranking_score_key: composite_score (maximize)
- composite_score: 0
- task_type: regression

## Comparability
- require_comparable: True
- processed_dataset_id: 109f218bad214d248cdcd9e8b8684c60
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
python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122949/grid/5e95e9bbbc4f47f6a32795d63e71bf2f/leaderboard/05_leaderboard
# ClearML task id (optional): 846aabb45c5d4e4ba0848eee24dca8ac
```
