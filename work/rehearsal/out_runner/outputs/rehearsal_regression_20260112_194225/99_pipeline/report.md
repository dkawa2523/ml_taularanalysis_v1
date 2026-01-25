# Pipeline Summary

## Conclusion
- grid_run_id: b47dfc8c0f4c44358d79d00780c5d241
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out_runner/outputs/rehearsal_regression_20260112_194225/grid/b47dfc8c0f4c44358d79d00780c5d241/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.313309
- status: ready
- models_tried: 2
- planned_jobs: 2
- executed_jobs: 2
- skipped_due_to_policy: 0
- train_task_ref: 3504b2ae118f4d9d9f69c287c757f0e2

## Data Overview
- raw_dataset_id: n/a
- processed_dataset_id: 900d42a190e74275b9fbad1fe46004a0
- rows: 240
- feature_columns: 3
- target_column: target

## Data Quality
- data_quality: n/a

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
- warning_count: 0

## Split / Recipe / Hashes
- preprocess_variant: stdscaler_ohe
- split.strategy: random
- split.test_size: 0.2
- split.seed: 42
- split_hash: 533ee5f18057b68a4f2a25c509059eaac051c9d8523b39a871fba1b698343a49
- recipe_hash: d0bf0716f2ca34406944f5a1d6dc0c933b526ff12d5107c5121228f6f6fbfb8a

## Models Tried (Top 10)

| Rank | Model | Preprocess | Metric | Score | Model ID |
| --- | --- | --- | --- | --- | --- |
| 1 | ridge | stdscaler_ohe | rmse | 0.313309 | .../03_train_model/model_bundle.joblib |
| 2 | elasticnet | stdscaler_ohe | rmse | 0.771224 | .../03_train_model/model_bundle.joblib |

## Recommendation
- model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out_runner/outputs/rehearsal_regression_20260112_194225/grid/b47dfc8c0f4c44358d79d00780c5d241/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.313309
- direction: minimize
- train_task_ref: 3504b2ae118f4d9d9f69c287c757f0e2
- rationale: Top-ranked by rmse (minimize). require_comparable=True.

## Notes
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Next Actions
- Try alternative preprocessing variants for robustness.
- Enable pipeline.hpo to explore parameter grids on promising models.
