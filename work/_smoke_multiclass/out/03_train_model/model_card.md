# Model Card

## Dataset
- processed_dataset_id: local:3c67b1e6e13ceb5c9c3c863fc9b7afa85eac6a743d5ea8883417c6eff17b4cda
- split_hash: 0bdc9a83dcef87e758d84dedcb5a3561f6b3272088ff1a98bf3c381999d789a0
- schema_version: v1

## Preprocess
- preprocess_variant: {'name': 'stdscaler_ohe', 'numeric_scaler': 'standard', 'categorical_encoder': 'onehot', 'handle_unknown': 'ignore'}
- categorical_encoding: onehot
- recipe_hash: 6dd3314922b3cca78f6b299cf3b6f2ce22481d5ca36ffbb531833e81b3928bc2

## Model
- model_variant: logistic_regression
- model_class: sklearn.linear_model.LogisticRegression
- hyperparams: {"max_iter": 1000, "random_state": 42}
- seed: 42
- task_type: classification
- n_classes: 3

## Metrics
- primary_metric: f1_macro (maximize)
- best_score: 0.811162
- train_rows: 192
- val_rows: 48
- other_metrics: accuracy=0.8125, logloss=0.527825

## Calibration / Thresholding / Uncertainty
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Limitations
- Evaluated on a single split; performance may vary on new data.
- Confirm leakage checks and target stability before promotion.
- Not validated for out-of-scope inputs or populations.
