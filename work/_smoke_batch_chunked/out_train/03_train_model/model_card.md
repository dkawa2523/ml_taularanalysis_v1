# Model Card

## Dataset
- processed_dataset_id: local:cbef1ed7fc48556fcfe7aff6e664ba5d8ab9f10c76a9fee6fc3efe3a711fa7d3
- split_hash: 1deded5763a0af64747642967757cba95ecc3742489523fc7fe4220b36acfc91
- schema_version: v1

## Preprocess
- preprocess_variant: {'name': 'stdscaler_ohe', 'numeric_scaler': 'standard', 'categorical_encoder': 'onehot', 'handle_unknown': 'ignore'}
- categorical_encoding: onehot
- recipe_hash: d0bf0716f2ca34406944f5a1d6dc0c933b526ff12d5107c5121228f6f6fbfb8a

## Model
- model_variant: ridge
- model_class: {'regression': 'sklearn.linear_model.Ridge', 'classification': 'sklearn.linear_model.RidgeClassifier'}
- hyperparams: {"alpha": 1.0, "random_state": 42}
- seed: 42
- task_type: regression

## Metrics
- primary_metric: rmse (minimize)
- best_score: 9.63786e-05
- train_rows: 16000
- val_rows: 4000
- other_metrics: mae=8.39855e-05, r2=1

## Calibration / Thresholding / Uncertainty
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Limitations
- Evaluated on a single split; performance may vary on new data.
- Confirm leakage checks and target stability before promotion.
- Not validated for out-of-scope inputs or populations.
