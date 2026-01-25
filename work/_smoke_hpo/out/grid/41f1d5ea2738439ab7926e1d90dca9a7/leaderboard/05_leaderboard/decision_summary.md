# Decision Summary

## Recommendation
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_hpo/out/grid/41f1d5ea2738439ab7926e1d90dca9a7/train__stdscaler_ohe__ridge__alpha_1/03_train_model/model_bundle.joblib
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_hpo/out/grid/41f1d5ea2738439ab7926e1d90dca9a7/train__stdscaler_ohe__ridge__alpha_1/03_train_model
- primary_metric: rmse (minimize)
- best_score: 0.0753718
- task_type: regression

## Comparability
- require_comparable: True
- processed_dataset_id: local:5812668ff82705adef95cfd3b1e34ee71780f41114508e5aef6daf30f416a82e
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
| 1 | ridge | stdscaler_ohe | 0.0753718 | rmse | n/a |
| 2 | ridge | stdscaler_ohe | 0.0774201 | rmse | n/a |
| 3 | ridge | stdscaler_ohe | 0.0891506 | rmse | n/a |

## Extra Capabilities
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Promote Command
```bash
python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_hpo/out/grid/41f1d5ea2738439ab7926e1d90dca9a7/leaderboard/05_leaderboard
```
