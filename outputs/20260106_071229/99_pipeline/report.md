# Pipeline Summary

## Conclusion
- grid_run_id: 54f0609d87dc45ba94facce734c7a9cc
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/20260106_071229/grid/54f0609d87dc45ba94facce734c7a9cc/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.33034
- status: ready
- models_tried: 1
- planned_jobs: 1
- executed_jobs: 1
- skipped_due_to_policy: 0
- train_task_ref: 5bc70c49bf9b465dba6a6ec00cd9466c

## Data Overview
- raw_dataset_id: 817e11ce55ac40bf868130b16cd70afd
- processed_dataset_id: b94338318a234f34a19dc845646d74f5
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
- processed_dataset_id: b94338318a234f34a19dc845646d74f5
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- recipe_hash: 4dc5a79344a1fe099c7b2484871c0ee63294a5afa57682652aebd795c2071779
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
- recipe_hash: 4dc5a79344a1fe099c7b2484871c0ee63294a5afa57682652aebd795c2071779

## Models Tried (Top 10)

| Rank | Model | Preprocess | Metric | Score | Model ID |
| --- | --- | --- | --- | --- | --- |
| 1 | ridge | stdscaler_ohe | rmse | 0.33034 | .../03_train_model/model_bundle.joblib |

## Recommendation
- model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/20260106_071229/grid/54f0609d87dc45ba94facce734c7a9cc/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.33034
- direction: minimize
- train_task_ref: 5bc70c49bf9b465dba6a6ec00cd9466c
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
