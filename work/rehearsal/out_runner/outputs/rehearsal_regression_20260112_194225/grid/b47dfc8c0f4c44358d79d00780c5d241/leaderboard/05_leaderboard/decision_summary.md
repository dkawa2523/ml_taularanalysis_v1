# Decision Summary

## Recommendation
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out_runner/outputs/rehearsal_regression_20260112_194225/grid/b47dfc8c0f4c44358d79d00780c5d241/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- train_task_ref: 3504b2ae118f4d9d9f69c287c757f0e2
- primary_metric: rmse (minimize)
- best_score: 0.313309
- ranking_score_key: composite_score (maximize)
- composite_score: 0.37037
- task_type: regression

## Comparability
- require_comparable: True
- processed_dataset_id: 900d42a190e74275b9fbad1fe46004a0
- split_hash: 533ee5f18057b68a4f2a25c509059eaac051c9d8523b39a871fba1b698343a49
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
| 1 | ridge | stdscaler_ohe | 0.37037 | 0.313309 | rmse | n/a |
| 2 | elasticnet | stdscaler_ohe | -0.62963 | 0.771224 | rmse | n/a |

## Extra Capabilities
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Promote Command
```bash
python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out_runner/outputs/rehearsal_regression_20260112_194225/grid/b47dfc8c0f4c44358d79d00780c5d241/leaderboard/05_leaderboard
# ClearML task id (optional): fced58d1b497452089c38cac34246d77
```
