# Decision Summary

## Recommendation
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_test_retrain/out/grid/e0e6eb8f673147f0b729c012f77c6c11/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_test_retrain/out/grid/e0e6eb8f673147f0b729c012f77c6c11/train__stdscaler_ohe__ridge/03_train_model
- primary_metric: rmse (minimize)
- best_score: 0.104573
- task_type: regression

## Comparability
- require_comparable: True
- processed_dataset_id: local:a5527dfd7b0ac70425e63e2e105b913099f7817e63efbf9290a3a6f1d1b79f7c
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- recipe_hash: d0bf0716f2ca34406944f5a1d6dc0c933b526ff12d5107c5121228f6f6fbfb8a
- primary_metric: rmse
- direction: minimize
- task_type: regression
- seed: 42
- excluded_count: 0

## Top Models
- source: leaderboard.csv

| rank | model_variant | preprocess_variant | best_score | primary_metric | ci |
| --- | --- | --- | --- | --- | --- |
| 1 | ridge | stdscaler_ohe | 0.104573 | rmse | n/a |

## Extra Capabilities
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Promote Command
```bash
python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_test_retrain/out/grid/e0e6eb8f673147f0b729c012f77c6c11/leaderboard/05_leaderboard
```
