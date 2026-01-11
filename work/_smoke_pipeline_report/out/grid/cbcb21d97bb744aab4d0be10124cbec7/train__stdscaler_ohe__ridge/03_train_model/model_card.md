# Model Card

## Dataset
- processed_dataset_id: local:3c4b8cb7e44b91b2c04a472a2d898b945bd22e94379cb95dfbeaf1abafd2f7cc
- split_hash: 03ab4e4731489ffde249a4a5ecafb978fcdd192ab0d5d240e1ce0c4b72969603
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
- best_score: 0.0156147
- train_rows: 128
- val_rows: 32
- other_metrics: mae=0.0136148, r2=0.999638

## Calibration / Thresholding / Uncertainty
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Limitations
- Evaluated on a single split; performance may vary on new data.
- Confirm leakage checks and target stability before promotion.
- Not validated for out-of-scope inputs or populations.
