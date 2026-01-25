# Model Card

## Dataset
- processed_dataset_id: local:c85ab7f964e06c43fa5db1e6d9fc50f2facb82320be7b232790713c03ccfdee3
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- schema_version: v1

## Preprocess
- preprocess_variant: {'name': 'stdscaler_ohe', 'numeric_scaler': 'standard', 'categorical_encoder': 'onehot', 'handle_unknown': 'ignore'}
- categorical_encoding: onehot
- recipe_hash: d0bf0716f2ca34406944f5a1d6dc0c933b526ff12d5107c5121228f6f6fbfb8a

## Model
- model_variant: logistic_regression
- model_class: sklearn.linear_model.LogisticRegression
- hyperparams: {"max_iter": 1000, "random_state": 42}
- seed: 42
- task_type: classification
- n_classes: 2

## Metrics
- primary_metric: accuracy (maximize)
- best_score: 0.95
- train_rows: 160
- val_rows: 40
- other_metrics: f1=0.956522, log_loss=0.175947, roc_auc=1

## Calibration / Thresholding / Uncertainty
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Limitations
- Evaluated on a single split; performance may vary on new data.
- Confirm leakage checks and target stability before promotion.
- Not validated for out-of-scope inputs or populations.
