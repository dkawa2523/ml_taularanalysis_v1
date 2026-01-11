# Pipeline Summary

## Conclusion
- grid_run_id: 4a80cf1d637248a3b3167365ea2b1e6a
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_hpo/out/grid/4a80cf1d637248a3b3167365ea2b1e6a/train__stdscaler_ohe__ridge__alpha_1/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.0753718
- status: ready
- models_tried: 3
- planned_jobs: 3
- executed_jobs: 3
- skipped_due_to_policy: 0
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_hpo/out/grid/4a80cf1d637248a3b3167365ea2b1e6a/train__stdscaler_ohe__ridge__alpha_1/03_train_model

## Data Overview
- raw_dataset_id: local:47b97e941a790f6f068d82313f79d6059cdae16e7b7466fe9bf2b810b9b93fff
- processed_dataset_id: local:5812668ff82705adef95cfd3b1e34ee71780f41114508e5aef6daf30f416a82e
- rows: 200
- feature_columns: 3
- target_column: target

## Data Quality
- rows_scanned: 200
- duplicates: 0 (0.0%)
- missing_top: n/a
- leak_suspects: n/a

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
- warning_count: 0

## Split / Recipe / Hashes
- preprocess_variant: stdscaler_ohe
- split.strategy: random
- split.test_size: 0.2
- split.seed: 42
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- recipe_hash: d0bf0716f2ca34406944f5a1d6dc0c933b526ff12d5107c5121228f6f6fbfb8a

## Models Tried (Top 10)

| Rank | Model | Preprocess | Metric | Score | Model ID |
| --- | --- | --- | --- | --- | --- |
| 1 | ridge | stdscaler_ohe | rmse | 0.0753718 | .../03_train_model/model_bundle.joblib |
| 2 | ridge | stdscaler_ohe | rmse | 0.0774201 | .../03_train_model/model_bundle.joblib |
| 3 | ridge | stdscaler_ohe | rmse | 0.0891506 | .../03_train_model/model_bundle.joblib |

## Recommendation
- model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_hpo/out/grid/4a80cf1d637248a3b3167365ea2b1e6a/train__stdscaler_ohe__ridge__alpha_1/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.0753718
- direction: minimize
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_hpo/out/grid/4a80cf1d637248a3b3167365ea2b1e6a/train__stdscaler_ohe__ridge__alpha_1/03_train_model
- rationale: Top-ranked by rmse (minimize). require_comparable=True.

## Notes
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Next Actions
- Try additional model variants for a stronger baseline.
- Try alternative preprocessing variants for robustness.
