# Model Card

## Dataset
- processed_dataset_id: 9d5ba8d651eb47f786676aba8e9a1b04
- split_hash: d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f
- schema_version: v1

## Preprocess
- preprocess_variant: stdscaler_ohe
- categorical_encoding: unknown
- recipe_hash: 4dc5a79344a1fe099c7b2484871c0ee63294a5afa57682652aebd795c2071779

## Model
- model_variant: logistic_regression
- model_class: sklearn.linear_model.LogisticRegression
- hyperparams: {"max_iter": 1000, "random_state": 42}
- seed: 42
- task_type: classification
- n_classes: 2

## Metrics
- primary_metric: f1 (max)
- best_score: 0.923077
- train_rows: 160
- val_rows: 40
- other_metrics: accuracy=0.925, log_loss=0.279403, roc_auc=0.952381

## Calibration / Thresholding / Uncertainty
- thresholding: enabled metric=f1 best_threshold=0.4 score=0.923077
- calibration: enabled method=sigmoid mode=prefit
- uncertainty: disabled
- imbalance_handling: disabled

## Limitations
- Evaluated on a single split; performance may vary on new data.
- Confirm leakage checks and target stability before promotion.
- Not validated for out-of-scope inputs or populations.
