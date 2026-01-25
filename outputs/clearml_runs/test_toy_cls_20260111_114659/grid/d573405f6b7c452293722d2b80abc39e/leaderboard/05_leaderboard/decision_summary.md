# Decision Summary

## Recommendation
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_20260111_114659/grid/d573405f6b7c452293722d2b80abc39e/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- train_task_ref: 056cdb9891d34370be429fd5c345c660
- primary_metric: rmse (minimize)
- best_score: 0.33034
- ranking_score_key: composite_score (maximize)
- composite_score: 0
- task_type: regression

## Comparability
- require_comparable: True
- processed_dataset_id: b44ef59fb7fc402f9eeb7db90aff586a
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- recipe_hash: 4dc5a79344a1fe099c7b2484871c0ee63294a5afa57682652aebd795c2071779
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
| 1 | ridge | stdscaler_ohe | 0 | 0.33034 | rmse | n/a |

## Extra Capabilities
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Promote Command
```bash
python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_20260111_114659/grid/d573405f6b7c452293722d2b80abc39e/leaderboard/05_leaderboard
# ClearML task id (optional): fd8eb90b7ae04400a5a2e24f24eaf82f
```
