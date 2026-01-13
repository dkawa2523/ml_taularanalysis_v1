# Pipeline Summary

## Conclusion
- grid_run_id: aaee4b53e6a14c97813ae683453fde8d
- recommended_model_id: n/a
- primary_metric: n/a
- best_score: n/a
- status: incomplete
- models_tried: 14
- planned_jobs: 14
- executed_jobs: 14
- skipped_due_to_policy: 0

## Data Overview
- raw_dataset_id: 66a230f19ac2400e92ed7cf7739a184f
- processed_dataset_id: n/a
- rows: 200
- feature_columns: 3
- target_column: target

## Data Quality
- rows_scanned: 200
- duplicates: 0 (0.0%)
- missing_top: n/a
- leak_suspects: n/a

## Comparability
- require_comparable: n/a
- processed_dataset_id: n/a
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- recipe_hash: 4dc5a79344a1fe099c7b2484871c0ee63294a5afa57682652aebd795c2071779
- primary_metric: n/a
- direction: n/a
- task_type: n/a
- seed: n/a

## Split / Recipe / Hashes
- preprocess_variant: stdscaler_ohe
- split.strategy: random
- split.test_size: 0.2
- split.seed: 42
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- recipe_hash: 4dc5a79344a1fe099c7b2484871c0ee63294a5afa57682652aebd795c2071779

## Models Tried (Top 10)

| Rank | Model | Preprocess | Metric | Score | Model ID |
| --- | --- | --- | --- | --- | --- |
| 1 | catboost | stdscaler_ohe | n/a | n/a | n/a |
| 2 | extra_trees | stdscaler_ohe | n/a | n/a | n/a |
| 3 | gaussian_process | stdscaler_ohe | n/a | n/a | n/a |
| 4 | gradient_boosting | stdscaler_ohe | n/a | n/a | n/a |
| 5 | knn | stdscaler_ohe | n/a | n/a | n/a |
| 6 | lgbm | stdscaler_ohe | n/a | n/a | n/a |
| 7 | logistic_regression | stdscaler_ohe | n/a | n/a | n/a |
| 8 | mlp | stdscaler_ohe | n/a | n/a | n/a |
| 9 | random_forest | stdscaler_ohe | n/a | n/a | n/a |
| 10 | ridge | stdscaler_ohe | n/a | n/a | n/a |

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
