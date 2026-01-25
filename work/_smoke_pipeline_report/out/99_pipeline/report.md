# Pipeline Summary

## Conclusion
- grid_run_id: cbcb21d97bb744aab4d0be10124cbec7
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_pipeline_report/out/grid/cbcb21d97bb744aab4d0be10124cbec7/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.0156147
- status: ready
- models_tried: 1
- planned_jobs: 1
- executed_jobs: 1
- skipped_due_to_policy: 0
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_pipeline_report/out/grid/cbcb21d97bb744aab4d0be10124cbec7/train__stdscaler_ohe__ridge/03_train_model

## Data Overview
- raw_dataset_id: local:15be20c63de64d1e60d9aa14d0d01ef282f5f3cb248aa148c2ec4bd9fe852704
- processed_dataset_id: local:3c4b8cb7e44b91b2c04a472a2d898b945bd22e94379cb95dfbeaf1abafd2f7cc
- rows: 160
- feature_columns: 3
- target_column: target

## Data Quality
- rows_scanned: 160
- duplicates: 0 (0.0%)
- missing_top: n/a
- leak_suspects: n/a

## Comparability
- require_comparable: True
- processed_dataset_id: local:3c4b8cb7e44b91b2c04a472a2d898b945bd22e94379cb95dfbeaf1abafd2f7cc
- split_hash: 03ab4e4731489ffde249a4a5ecafb978fcdd192ab0d5d240e1ce0c4b72969603
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
- split_hash: 03ab4e4731489ffde249a4a5ecafb978fcdd192ab0d5d240e1ce0c4b72969603
- recipe_hash: d0bf0716f2ca34406944f5a1d6dc0c933b526ff12d5107c5121228f6f6fbfb8a

## Models Tried (Top 10)

| Rank | Model | Preprocess | Metric | Score | Model ID |
| --- | --- | --- | --- | --- | --- |
| 1 | ridge | stdscaler_ohe | rmse | 0.0156147 | .../03_train_model/model_bundle.joblib |

## Recommendation
- model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_pipeline_report/out/grid/cbcb21d97bb744aab4d0be10124cbec7/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.0156147
- direction: minimize
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_pipeline_report/out/grid/cbcb21d97bb744aab4d0be10124cbec7/train__stdscaler_ohe__ridge/03_train_model
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
