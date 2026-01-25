# Decision Summary

## Recommendation
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_report/out/grid/ba100fe6f6f046239a34635479d0d6f7/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_report/out/grid/ba100fe6f6f046239a34635479d0d6f7/train__stdscaler_ohe__ridge/03_train_model
- primary_metric: rmse (minimize)
- best_score: 0.0100875
- task_type: regression

## Comparability
- require_comparable: True
- processed_dataset_id: local:288a3dda65df1da880d1a7ab7977491d0864bd9ffe4a5591a493304d64fc1308
- split_hash: 03ab4e4731489ffde249a4a5ecafb978fcdd192ab0d5d240e1ce0c4b72969603
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
| 1 | ridge | stdscaler_ohe | 0.0100875 | rmse | n/a |

## Extra Capabilities
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Promote Command
```bash
python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_report/out/grid/ba100fe6f6f046239a34635479d0d6f7/leaderboard/05_leaderboard
```
