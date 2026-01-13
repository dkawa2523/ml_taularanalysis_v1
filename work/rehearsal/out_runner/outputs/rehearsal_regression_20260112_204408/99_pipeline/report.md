# Pipeline Summary

## Conclusion
- grid_run_id: 4eeb39d98bca4d0e99ee6227e785203b
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out_runner/outputs/rehearsal_regression_20260112_204408/grid/4eeb39d98bca4d0e99ee6227e785203b/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.313309
- status: ready
- models_tried: 3
- planned_jobs: 3
- executed_jobs: 3
- skipped_due_to_policy: 0
- train_task_ref: 8f0f04eae9b149efb611457d74337e57

## Data Overview
- raw_dataset_id: n/a
- processed_dataset_id: 52a878767f3b4177a293c7c52d7b8805
- rows: 240
- feature_columns: 3
- target_column: target

## Data Quality
- data_quality: n/a

## Comparability
- require_comparable: True
- processed_dataset_id: 52a878767f3b4177a293c7c52d7b8805
- split_hash: 533ee5f18057b68a4f2a25c509059eaac051c9d8523b39a871fba1b698343a49
- recipe_hash: d0bf0716f2ca34406944f5a1d6dc0c933b526ff12d5107c5121228f6f6fbfb8a
- primary_metric: rmse
- direction: minimize
- task_type: regression
- seed: 42
- excluded_count: 1
- warning_count: 1

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
| 3 | lasso | stdscaler_ohe | rmse | 0.771224 | .../03_train_model/model_bundle.joblib |

## Recommendation
- model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out_runner/outputs/rehearsal_regression_20260112_204408/grid/4eeb39d98bca4d0e99ee6227e785203b/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.313309
- direction: minimize
- train_task_ref: 8f0f04eae9b149efb611457d74337e57
- rationale: Top-ranked by rmse (minimize). require_comparable=True. excluded_count=1.

## Notes
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Next Actions
- Try alternative preprocessing variants for robustness.
- Enable pipeline.hpo to explore parameter grids on promising models.
