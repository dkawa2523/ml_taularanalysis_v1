# 23_MODEL_LIFECYCLE (Promote / Rollback / Champion-Challenger)

This document completes the model lifecycle flow by separating recommendation from promotion and adding rollback
and champion-challenger comparison.

## Promote vs Recommend
- `leaderboard` produces a recommendation only (no registry changes).
- `promote_model` records an adoption decision and, when ClearML is enabled, registers the model and applies tags.

## rollback_model
Inputs:
- `rollback.stage` (default: production)
- `rollback.reason`
- `rollback.target_model_id` (optional)

Behavior:
- ClearML enabled: update model registry tags/metadata so the previous production becomes current.
- ClearML disabled: update `run.output_dir/model_registry_state.json` to move stage history.

Outputs:
- `rollback.json` (before/after model refs, reason, timestamp)

## champion_challenger
Inputs:
- `champion_model_ref` (optional, defaults to production)
- `challenger_model_ref` (required)
- `eval_dataset_ref` (optional)

Comparability:
- Prefer same `processed_dataset_id` and `split_hash` across both models.
- Emit warnings when mismatched or missing.

Outputs:
- `champion_challenger.csv` (side-by-side primary metric with delta)
- `decision.json` (winner, deltas, rationale, warnings)
- `summary.md` (non-DS friendly conclusion)

## UI checks (ClearML)
- Model Registry tags: `stage:<stage>` and `usecase:<id>`
- Model metadata: `metric`, `score`, `processed_dataset_id`, `split_hash`
- Task artifacts: `rollback.json`, `champion_challenger.csv`, `decision.json`, `summary.md`
