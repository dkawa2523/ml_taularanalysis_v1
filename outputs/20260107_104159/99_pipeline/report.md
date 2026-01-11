# Pipeline Summary

## Conclusion
- grid_run_id: a5573474688b428fb5073cd5ad00b032
- recommended_model_id: n/a
- primary_metric: n/a
- best_score: n/a
- status: incomplete
- models_tried: 2
- planned_jobs: 2
- executed_jobs: 2
- skipped_due_to_policy: 0

## Data Overview
- raw_dataset_id: n/a
- processed_dataset_id: n/a
- rows: n/a
- feature_columns: n/a
- target_column: n/a

## Data Quality
- data_quality: n/a

## Comparability
- require_comparable: n/a
- processed_dataset_id: n/a
- split_hash: n/a
- recipe_hash: n/a
- primary_metric: n/a
- direction: n/a
- task_type: n/a
- seed: n/a

## Split / Recipe / Hashes
- preprocess_variant: stdscaler_ohe
- split.strategy: n/a
- split.test_size: n/a
- split.seed: n/a
- split_hash: n/a
- recipe_hash: n/a

## Models Tried (Top 10)

| Rank | Model | Preprocess | Metric | Score | Model ID |
| --- | --- | --- | --- | --- | --- |
| 1 | logistic_regression | stdscaler_ohe | n/a | n/a | n/a |
| 2 | random_forest | stdscaler_ohe | n/a | n/a | n/a |

## Recommendation
- model_id: n/a
- primary_metric: n/a
- best_score: n/a

## Notes
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Next Actions
- Wait for training/leaderboard to finish, then regenerate the report.
- Run leaderboard to select the best model explicitly.
- Try alternative preprocessing variants for robustness.
