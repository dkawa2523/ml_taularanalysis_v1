# Pipeline Summary

## Conclusion
- grid_run_id: ba100fe6f6f046239a34635479d0d6f7
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_report/out/grid/ba100fe6f6f046239a34635479d0d6f7/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.0100875
- status: ready
- models_tried: 1
- planned_jobs: 1
- executed_jobs: 1
- skipped_due_to_policy: 0
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_report/out/grid/ba100fe6f6f046239a34635479d0d6f7/train__stdscaler_ohe__ridge/03_train_model

## Data Overview
- raw_dataset_id: local:4dd16162b6de06cd75c7b537734834eb9bc9269475c2db8618deee0dcddfdaae
- processed_dataset_id: local:288a3dda65df1da880d1a7ab7977491d0864bd9ffe4a5591a493304d64fc1308
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
- processed_dataset_id: local:288a3dda65df1da880d1a7ab7977491d0864bd9ffe4a5591a493304d64fc1308
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
| 1 | ridge | stdscaler_ohe | rmse | 0.0100875 | .../03_train_model/model_bundle.joblib |

## Recommendation
- model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_report/out/grid/ba100fe6f6f046239a34635479d0d6f7/train__stdscaler_ohe__ridge/03_train_model/model_bundle.joblib
- primary_metric: rmse
- best_score: 0.0100875
- direction: minimize
- train_task_ref: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/_smoke_report/out/grid/ba100fe6f6f046239a34635479d0d6f7/train__stdscaler_ohe__ridge/03_train_model
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
