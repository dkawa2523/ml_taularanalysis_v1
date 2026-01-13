# Pipeline Summary

## Conclusion
- grid_run_id: 6c9e294440f64a42bcc5a3f7d8e6e27f
- recommended_model_id: n/a
- primary_metric: n/a
- best_score: n/a
- status: incomplete
- models_tried: 1
- planned_jobs: 1
- executed_jobs: 1
- skipped_due_to_policy: 0

## Data Overview
- raw_dataset_id: n/a
- processed_dataset_id: ff1c00398cbe4ea09a3ce5eb3a49559a
- rows: 240
- feature_columns: 3
- target_column: target

## Data Quality
- data_quality: n/a

## Comparability
- require_comparable: n/a
- processed_dataset_id: ff1c00398cbe4ea09a3ce5eb3a49559a
- split_hash: 533ee5f18057b68a4f2a25c509059eaac051c9d8523b39a871fba1b698343a49
- recipe_hash: d0bf0716f2ca34406944f5a1d6dc0c933b526ff12d5107c5121228f6f6fbfb8a
- primary_metric: n/a
- direction: n/a
- task_type: n/a
- seed: n/a

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
- Try additional model variants for a stronger baseline.
