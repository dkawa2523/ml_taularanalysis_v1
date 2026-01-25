# Leaderboard Summary

- total_runs: 13
- included: 13
- excluded: 0
- require_comparable: True
- ranking_score_key: best_score
- ranking_direction: minimize
- scoring.normalization: minmax
- primary_metric: accuracy
- direction: minimize
- task_type: classification
- seed: 42
- processed_dataset_id: 00546bfb148a4b44bfd7cd2ce45a3e38
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f

## Top Results
- rank 1: best_score=0.85 model_id=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__catboost/03_train_model/model_bundle.joblib train_task_ref=80779c9030394e97833644b2c32e74ae
- rank 2: best_score=0.85 model_id=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__gradient_boosting/03_train_model/model_bundle.joblib train_task_ref=947188cd11754578a5bcfaa134dca9dd
- rank 3: best_score=0.85 model_id=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__knn/03_train_model/model_bundle.joblib train_task_ref=ecbdf97c1d044cada28614b6bbcad01d
- rank 4: best_score=0.85 model_id=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__lgbm/03_train_model/model_bundle.joblib train_task_ref=88bd1ec94870492eb2a91912996ca59f
- rank 5: best_score=0.875 model_id=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__extra_trees/03_train_model/model_bundle.joblib train_task_ref=45d5db04cb8541759e0cdc40b25b3468
- rank 6: best_score=0.875 model_id=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__gaussian_process/03_train_model/model_bundle.joblib train_task_ref=18df80a2fa924e22a6c0f4dc24086536
- rank 7: best_score=0.875 model_id=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__random_forest/03_train_model/model_bundle.joblib train_task_ref=f1cf9069f6084e5087dd43845515e12e
- rank 8: best_score=0.9 model_id=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__mlp/03_train_model/model_bundle.joblib train_task_ref=eaa8e37ff51544d5992f20aa01eb6277
- rank 9: best_score=0.9 model_id=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__svc/03_train_model/model_bundle.joblib train_task_ref=8fd14440da224a3fb5a592e0612c6959
- rank 10: best_score=0.9 model_id=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/outputs/clearml_runs/test_toy_cls_all_no_tabpfn_20260111_123519/grid/90675e6473af49ceb3dec4404d6b285b/train__stdscaler_ohe__svr/03_train_model/model_bundle.joblib train_task_ref=e9a431f423f94e9290dd8d76a9a79d9c

## Warnings
- 80779c9030394e97833644b2c32e74ae: Failed to load model_bundle.joblib: No module named 'catboost'
- 88bd1ec94870492eb2a91912996ca59f: Failed to load model_bundle.joblib: No module named 'lightgbm'
- 456813bea678440094a20b0aed271949: Failed to load model_bundle.joblib: No module named 'xgboost'
- metric 'r2' missing in all runs; skipping in composite score.
- metric 'rmse' missing in all runs; skipping in composite score.
- metric 'mae' missing in all runs; skipping in composite score.
- metric 'mse' missing in all runs; skipping in composite score.
- Composite scoring unavailable; falling back to primary metric ranking.
- Invalid direction max; defaulting to minimize.
