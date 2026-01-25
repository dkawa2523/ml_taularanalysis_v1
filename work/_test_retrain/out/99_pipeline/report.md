# Pipeline Summary

## Conclusion
- grid_run_id: e0e6eb8f673147f0b729c012f77c6c11
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_test_retrain/out/grid/e0e6eb8f673147f0b729c012f77c6c11/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.104573
- status: ready
- models_tried: 1
- planned_jobs: 1
- executed_jobs: 1
- skipped_due_to_policy: 0
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_test_retrain/out/grid/e0e6eb8f673147f0b729c012f77c6c11/train__stdscaler_ohe__ridge/03_train_model

## Data Overview
- raw_dataset_id: local:373cd05bc0a4f6804b6ba4278b5142948f13de60c6f2a887bb2ec7eebb4af66b
- processed_dataset_id: local:a5527dfd7b0ac70425e63e2e105b913099f7817e63efbf9290a3a6f1d1b79f7c
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
- processed_dataset_id: local:a5527dfd7b0ac70425e63e2e105b913099f7817e63efbf9290a3a6f1d1b79f7c
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
| 1 | ridge | stdscaler_ohe | rmse | 0.104573 | .../03_train_model/model_bundle.joblib |

## Recommendation
- model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_test_retrain/out/grid/e0e6eb8f673147f0b729c012f77c6c11/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.104573
- direction: minimize
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_test_retrain/out/grid/e0e6eb8f673147f0b729c012f77c6c11/train__stdscaler_ohe__ridge/03_train_model
- rationale: Top-ranked by rmse (minimize). require_comparable=True.

## Notes
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Next Actions
- Try additional model variants for a stronger baseline.
- Try alternative preprocessing variants for robustness.
- Enable pipeline.hpo to explore parameter grids on promising models.
