# Model Card

## Dataset
- processed_dataset_id: local:39ed5d575490da4014df84597910a40986eca32808cd3d8d08321814f9df5266
- split_hash: a2970c9c1feb13bd5710e3f6213f4115e878ff00d77e23b73d8ff10e0529a13e
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
- best_score: 0.0108291
- train_rows: 144
- val_rows: 36
- other_metrics: mae=0.00977229, r2=0.999763

## Calibration / Thresholding / Uncertainty
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Limitations
- Evaluated on a single split; performance may vary on new data.
- Confirm leakage checks and target stability before promotion.
- Not validated for out-of-scope inputs or populations.
