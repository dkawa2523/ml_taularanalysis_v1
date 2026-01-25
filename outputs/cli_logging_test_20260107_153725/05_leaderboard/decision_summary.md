# Decision Summary

## Recommendation
- recommended_model_id: outputs/cli_logging_test_20260107_153725/03_train_model/model_bundle.joblib
- train_task_ref: d902074c67e7473bbb0b31cf94eb9c75
- primary_metric: rmse (minimize)
- best_score: 0.273861
- task_type: regression

## Comparability
- require_comparable: True
- processed_dataset_id: 9d5ba8d651eb47f786676aba8e9a1b04
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
| 1 | logistic_regression | stdscaler_ohe | 0.273861 | rmse | n/a |

## Extra Capabilities
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Promote Command
```bash
python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir=outputs/cli_logging_test_20260107_153725/05_leaderboard
# ClearML task id (optional): 820368b4f7fb4d16be0d95beda0d9c33
```
