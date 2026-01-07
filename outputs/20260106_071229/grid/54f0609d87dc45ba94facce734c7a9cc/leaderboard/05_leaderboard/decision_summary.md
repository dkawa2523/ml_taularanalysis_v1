# Decision Summary

## Recommendation
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/20260106_071229/grid/54f0609d87dc45ba94facce734c7a9cc/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- train_task_ref: 5bc70c49bf9b465dba6a6ec00cd9466c
- primary_metric: rmse (minimize)
- best_score: 0.33034
- task_type: regression

## Comparability
- require_comparable: True
- processed_dataset_id: b94338318a234f34a19dc845646d74f5
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- recipe_hash: 4dc5a79344a1fe099c7b2484871c0ee63294a5afa57682652aebd795c2071779
- primary_metric: rmse
- direction: minimize
- task_type: regression
- seed: 42
- excluded_count: 0

## Top Models
- source: leaderboard.csv

| rank | model_variant | preprocess_variant | best_score | primary_metric | ci |
| --- | --- | --- | --- | --- | --- |
| 1 | ridge | stdscaler_ohe | 0.33034 | rmse | n/a |

## Extra Capabilities
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Promote Command
```bash
python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/20260106_071229/grid/54f0609d87dc45ba94facce734c7a9cc/leaderboard/05_leaderboard
# ClearML task id (optional): 5bc70c49bf9b465dba6a6ec00cd9466c
```
