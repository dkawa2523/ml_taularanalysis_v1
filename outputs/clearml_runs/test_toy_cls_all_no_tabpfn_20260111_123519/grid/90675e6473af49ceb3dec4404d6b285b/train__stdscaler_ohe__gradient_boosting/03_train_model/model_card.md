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
- model_variant: gradient_boosting
- model_class: {'regression': 'sklearn.ensemble.GradientBoostingRegressor', 'classification': 'sklearn.ensemble.GradientBoostingClassifier'}
- hyperparams: {"learning_rate": 0.1, "max_depth": 3, "min_samples_leaf": 2, "n_estimators": 100, "random_state": 42}
- seed: 42
- task_type: classification
- n_classes: 2

## Metrics
- primary_metric: accuracy (max)
- best_score: 0.85
- train_rows: 160
- val_rows: 40
- other_metrics: f1=0.833333, log_loss=0.296217, roc_auc=0.934837

## Calibration / Thresholding / Uncertainty
- thresholding: disabled
- calibration: disabled
- uncertainty: disabled
- imbalance_handling: disabled

## Limitations
- Evaluated on a single split; performance may vary on new data.
- Confirm leakage checks and target stability before promotion.
- Not validated for out-of-scope inputs or populations.
