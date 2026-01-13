# Model Card

## Dataset
- processed_dataset_id: 9d5ba8d651eb47f786676aba8e9a1b04
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- schema_version: v1

## Preprocess
- preprocess_variant: {'name': 'stdscaler_ohe', 'numeric_scaler': 'standard', 'categorical_encoder': 'onehot', 'handle_unknown': 'ignore'}
- categorical_encoding: onehot
- recipe_hash: 4dc5a79344a1fe099c7b2484871c0ee63294a5afa57682652aebd795c2071779

## Model
- model_variant: logistic_regression
- model_class: sklearn.linear_model.LogisticRegression
- hyperparams: {"max_iter": 1000, "random_state": 42}
- seed: 42
- task_type: regression

## Metrics
- primary_metric: rmse (minimize)
- best_score: 0.273861
- train_rows: 160
- val_rows: 40
- other_metrics: mae=0.075, r2=0.699248

## Calibration / Thresholding / Uncertainty
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Limitations
- Evaluated on a single split; performance may vary on new data.
- Confirm leakage checks and target stability before promotion.
- Not validated for out-of-scope inputs or populations.
