# 28_RETRAIN (Monitoring -> Retrain -> Compare -> Optional Promote)

This document describes the retrain orchestration that connects monitoring signals to a full retrain loop.

## Goal
- Re-run the training pipeline on new data and capture the recommendation.
- Compare the new recommendation against the current champion.
- Optionally promote the challenger when criteria are satisfied.

## Inputs
- Latest data:
  - `data.dataset_path` (local CSV/Parquet), or
  - `data.raw_dataset_id` (ClearML Dataset ID)
- Baseline selection:
  - `retrain.baseline_stage` (default: `production`)
  - `retrain.champion_model_ref` (optional override; recommended for ClearML-only registry)
- Auto promotion (opt-in):
  - `retrain.auto_promote` (default: false)
  - `retrain.promote_stage` (default: baseline_stage)
  - `retrain.promote_criteria.min_improvement` (default: 0.0)
  - `retrain.promote_criteria.require_comparable` (default: true)

## Flow
1) Run `pipeline` with the latest dataset (exec_policy is respected).
2) Read the leaderboard recommendation (challenger).
3) Run `champion_challenger` to compare against the baseline champion.
4) If `auto_promote=true` and criteria pass, call `promote_model`.

## Outputs
Retrain task artifacts:
- `retrain_summary.md`
- `retrain_decision.json` (winner, deltas, auto-promote status)
- `retrain_run.json` (references to pipeline/leaderboard/champion_challenger/promote)

Pipeline/compare outputs remain in their own stages:
- `99_pipeline/pipeline_run.json`
- `05_leaderboard/decision_summary.json` (via pipeline)
- `07_champion_challenger/decision.json`
- `06_promote_model/promotion.json` (when auto-promote succeeds)

## ClearML Traceability
- Tasks carry `grid:<grid_run_id>` and `retrain:<retrain_run_id>` tags.
- `retrain_run_id` is stored in user properties for the retrain task.

## Examples
Local retrain (no auto promotion):
```bash
python -m tabular_analysis.cli task=retrain \
  run.clearml.enabled=false \
  run.output_dir=outputs/20260102_090000 \
  data.dataset_path=/path/to/latest.csv \
  data.target_column=target \
  retrain.auto_promote=false
```

Auto-promote when challenger beats champion:
```bash
python -m tabular_analysis.cli task=retrain \
  run.clearml.enabled=false \
  run.output_dir=outputs/20260102_090000 \
  data.dataset_path=/path/to/latest.csv \
  data.target_column=target \
  retrain.auto_promote=true \
  retrain.promote_criteria.min_improvement=0.0
```

ClearML note:
- When ClearML registry is the source of truth, provide `retrain.champion_model_ref` explicitly
  so the champion can be compared without a local registry file.
