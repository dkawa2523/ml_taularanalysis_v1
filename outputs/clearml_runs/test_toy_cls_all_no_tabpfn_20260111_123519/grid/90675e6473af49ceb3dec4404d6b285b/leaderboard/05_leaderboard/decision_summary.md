# Decision Summary

## Recommendation
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__catboost/03_train_model/model_bundle.joblib
- train_task_ref: 80779c9030394e97833644b2c32e74ae
- primary_metric: accuracy (minimize)
- best_score: 0.85
- ranking_score_key: best_score (minimize)
- task_type: classification
- n_classes: 2

## Comparability
- require_comparable: True
- processed_dataset_id: 00546bfb148a4b44bfd7cd2ce45a3e38
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- recipe_hash: 4dc5a79344a1fe099c7b2484871c0ee63294a5afa57682652aebd795c2071779
- primary_metric: accuracy
- direction: minimize
- task_type: classification
- seed: 42
- excluded_count: 0
- warning_count: 9 (see summary.md)

## Scoring
- normalization: minmax
- metrics: r2, rmse, mae, mse
- weights: r2=1.0, rmse=-1.0, mae=-0.5, mse=-0.2

## Top Models
- source: leaderboard.csv

| rank | model_variant | preprocess_variant | composite_score | best_score | primary_metric | ci |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | catboost | unknown | n/a | 0.85 | accuracy | n/a |
| 2 | gradient_boosting | stdscaler_ohe | n/a | 0.85 | accuracy | n/a |
| 3 | knn | stdscaler_ohe | n/a | 0.85 | accuracy | n/a |
| 4 | lgbm | unknown | n/a | 0.85 | accuracy | n/a |
| 5 | extra_trees | stdscaler_ohe | n/a | 0.875 | accuracy | n/a |

## Extra Capabilities
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Promote Command
```bash
python -m tabular_analysis.cli task=promote_model promotion.source_leaderboard_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/leaderboard/05_leaderboard
# ClearML task id (optional): a678d672803f4608a2de542caf6a7d78
```
