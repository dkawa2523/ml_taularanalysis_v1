# Model Card

## Dataset
- processed_dataset_id: 109f218bad214d248cdcd9e8b8684c60
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
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
- best_score: 0.00863873
- train_rows: 160
- val_rows: 40
- other_metrics: mae=0.00821124, mse=7.46277e-05, r2=0.999793

## Calibration / Thresholding / Uncertainty
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Limitations
- Evaluated on a single split; performance may vary on new data.
- Confirm leakage checks and target stability before promotion.
- Not validated for out-of-scope inputs or populations.
