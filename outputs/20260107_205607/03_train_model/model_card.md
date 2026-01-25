# Model Card

## Dataset
- processed_dataset_id: local:0d04abe93431647ef713d37d397e91014a6da5844250b6d4b5979ef608b924a8
- split_hash: 8aa818dc1c1e4aebd0939754d3ecc60c630509aa7f7577f4773a5ea65645cd2e
- schema_version: v1

## Preprocess
- preprocess_variant: {'name': 'stdscaler_ohe', 'numeric_scaler': 'standard', 'categorical_encoder': 'onehot', 'handle_unknown': 'ignore'}
- categorical_encoding: onehot
- recipe_hash: 7887efea9c84c68baea8f1f0f9a255b4f49d119173213d19b1a3ab7afe35670c

## Model
- model_variant: linear_regression
- model_class: sklearn.linear_model.LinearRegression
- hyperparams: {}
- seed: 42
- task_type: regression

## Metrics
- primary_metric: rmse (minimize)
- best_score: 1.1
- train_rows: 3
- val_rows: 1
- other_metrics: mae=1.1, mse=1.21, r2=n/a

## Calibration / Thresholding / Uncertainty
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Limitations
- Evaluated on a single split; performance may vary on new data.
- Confirm leakage checks and target stability before promotion.
- Not validated for out-of-scope inputs or populations.
