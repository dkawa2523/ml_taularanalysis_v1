# Model Card

## Dataset
- processed_dataset_id: 43ca7b4032214e9f84bf9e9b5dfbaa2a
- split_hash: 533ee5f18057b68a4f2a25c509059eaac051c9d8523b39a871fba1b698343a49
- schema_version: v1

## Preprocess
- preprocess_variant: {'name': 'stdscaler_ohe', 'numeric_scaler': 'standard', 'categorical_encoder': 'onehot', 'handle_unknown': 'ignore'}
- categorical_encoding: onehot
- recipe_hash: d0bf0716f2ca34406944f5a1d6dc0c933b526ff12d5107c5121228f6f6fbfb8a

## Model
- model_variant: lasso
- model_class: sklearn.linear_model.Lasso
- hyperparams: {"alpha": 1.0, "max_iter": 5000, "random_state": 42}
- seed: 42
- task_type: regression

## Metrics
- primary_metric: rmse (minimize)
- best_score: 0.771224
- train_rows: 192
- val_rows: 48
- other_metrics: mae=0.652264, mse=0.594786, r2=-0.00454882

## Calibration / Thresholding / Uncertainty
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Limitations
- Evaluated on a single split; performance may vary on new data.
- Confirm leakage checks and target stability before promotion.
- Not validated for out-of-scope inputs or populations.
