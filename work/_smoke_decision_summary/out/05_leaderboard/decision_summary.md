# Decision Summary

## Recommendation
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_decision_summary/out/03_train_model/model_bundle.joblib
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_decision_summary/out/03_train_model
- primary_metric: rmse (minimize)
- best_score: 0.0108291
- task_type: regression

## Comparability
- require_comparable: True
- processed_dataset_id: local:39ed5d575490da4014df84597910a40986eca32808cd3d8d08321814f9df5266
- split_hash: a2970c9c1feb13bd5710e3f6213f4115e878ff00d77e23b73d8ff10e0529a13e
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
| 1 | ridge | stdscaler_ohe | 0.0108291 | rmse | n/a |

## Extra Capabilities
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Promote Command
```bash
python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_decision_summary/out/05_leaderboard
```
