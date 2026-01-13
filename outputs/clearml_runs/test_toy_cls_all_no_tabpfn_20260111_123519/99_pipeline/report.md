# Pipeline Summary

## Conclusion
- grid_run_id: 90675e6473af49ceb3dec4404d6b285b
- recommended_model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__catboost/03_train_model/model_bundle.joblib
- primary_metric: accuracy
- best_score: 0.85
- status: ready
- models_tried: 10
- planned_jobs: 13
- executed_jobs: 13
- skipped_due_to_policy: 0
- train_task_ref: 80779c9030394e97833644b2c32e74ae

## Data Overview
- raw_dataset_id: e3cac04a06e6443287394335a0286c41
- processed_dataset_id: 00546bfb148a4b44bfd7cd2ce45a3e38
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
- processed_dataset_id: 00546bfb148a4b44bfd7cd2ce45a3e38
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- recipe_hash: 4dc5a79344a1fe099c7b2484871c0ee63294a5afa57682652aebd795c2071779
- primary_metric: accuracy
- direction: minimize
- task_type: classification
- seed: 42
- excluded_count: 0
- warning_count: 9

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
| 1 | catboost | unknown | accuracy | 0.85 | .../03_train_model/model_bundle.joblib |
| 2 | gradient_boosting | stdscaler_ohe | accuracy | 0.85 | .../03_train_model/model_bundle.joblib |
| 3 | knn | stdscaler_ohe | accuracy | 0.85 | .../03_train_model/model_bundle.joblib |
| 4 | lgbm | unknown | accuracy | 0.85 | .../03_train_model/model_bundle.joblib |
| 5 | extra_trees | stdscaler_ohe | accuracy | 0.875 | .../03_train_model/model_bundle.joblib |
| 6 | gaussian_process | stdscaler_ohe | accuracy | 0.875 | .../03_train_model/model_bundle.joblib |
| 7 | random_forest | stdscaler_ohe | accuracy | 0.875 | .../03_train_model/model_bundle.joblib |
| 8 | mlp | stdscaler_ohe | accuracy | 0.9 | .../03_train_model/model_bundle.joblib |
| 9 | svc | stdscaler_ohe | accuracy | 0.9 | .../03_train_model/model_bundle.joblib |
| 10 | svr | stdscaler_ohe | accuracy | 0.9 | .../03_train_model/model_bundle.joblib |

## Recommendation
- model_id: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__catboost/03_train_model/model_bundle.joblib
- primary_metric: accuracy
- best_score: 0.85
- direction: minimize
- train_task_ref: 80779c9030394e97833644b2c32e74ae
- rationale: Top-ranked by accuracy (minimize). require_comparable=True.

## Notes
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Next Actions
- Try alternative preprocessing variants for robustness.
- Enable pipeline.hpo to explore parameter grids on promising models.
