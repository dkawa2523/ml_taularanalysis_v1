# Model Card

## Dataset
- processed_dataset_id: 00546bfb148a4b44bfd7cd2ce45a3e38
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- schema_version: v1

## Preprocess
- preprocess_variant: {'name': 'stdscaler_ohe', 'numeric_scaler': 'standard', 'categorical_encoder': 'onehot', 'handle_unknown': 'ignore'}
- categorical_encoding: onehot
- recipe_hash: 4dc5a79344a1fe099c7b2484871c0ee63294a5afa57682652aebd795c2071779

## Model
- model_variant: xgboost
- model_class: {'regression': 'xgboost.XGBRegressor', 'classification': 'xgboost.XGBClassifier'}
- hyperparams: {"colsample_bytree": 0.8, "learning_rate": 0.05, "max_depth": 6, "n_estimators": 500, "random_state": 42, "subsample": 0.8}
- seed: 42
- task_type: classification
- n_classes: 2

## Metrics
- primary_metric: accuracy (max)
- best_score: 0.9
- train_rows: 160
- val_rows: 40
- other_metrics: f1=0.894737, log_loss=0.267753, roc_auc=0.937343

## Calibration / Thresholding / Uncertainty
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Limitations
- Evaluated on a single split; performance may vary on new data.
- Confirm leakage checks and target stability before promotion.
- Not validated for out-of-scope inputs or populations.
