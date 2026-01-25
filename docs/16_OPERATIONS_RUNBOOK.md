# 16_OPERATIONS_RUNBOOK (Promotion Flow)

## Goal
運用担当者が **pipeline 実行 → leaderboard レビュー → promote_model** まで迷わず進められるよう、
最低限の手順と確認ポイントをまとめます。

## Audience
- 運用担当 / 開発者
- ClearML を使う運用（logging/agent/clone）とローカル運用の両方を対象

## Preconditions
- Python 3.10+ / `uv sync --frozen` (ClearML parity: `uv sync --all-extras --frozen`)
- データ入力が確定していること（`data.dataset_path` または `data.raw_dataset_id`）
- ClearML を使う場合は `clearml.conf` / 環境変数の設定が完了していること

## Pre-flight Checks (Recommended)
```bash
# 基本チェック（conf/ / platform import / ClearML 接続チェック）
python -m tabular_analysis.doctor

# ClearML agent/clone を使う場合の例
python -m tabular_analysis.doctor \
  run.clearml.enabled=true \
  run.clearml.execution=agent \
  run.clearml.queue_name=default
```

環境が不安定なときは quick verify で最低限の動作確認を行います。
```bash
python tools/tests/verify_all.py --quick
```

## Flow
### 1) dataset_register（raw_dataset_id を取得）
Local mode（ClearML 無効）:
```bash
python -m tabular_analysis.cli task=dataset_register \
  run.clearml.enabled=false \
  run.output_dir=outputs/20260101_120000 \
  data.dataset_path=/path/to/data.csv \
  data.target_column=target
```

ClearML logging mode（ローカル実行 + ログ記録）:
```bash
python -m tabular_analysis.cli task=dataset_register \
  run.clearml.enabled=true \
  run.clearml.execution=logging \
  run.output_dir=outputs/20260101_120000 \
  data.dataset_path=/path/to/data.csv \
  data.target_column=target
```

### 2) Pipeline 実行（train + leaderboard まで）
Local mode（ClearML 無効）:
```bash
python -m tabular_analysis.cli task=pipeline \
  run.clearml.enabled=false \
  run.output_dir=outputs/20260101_120000 \
  data.raw_dataset_id=local:<RAW_DATASET_ID> \
  data.dataset_path=/path/to/data.csv \
  data.target_column=target
```

ClearML logging mode（ローカル実行 + ログ記録）:
```bash
python -m tabular_analysis.cli task=pipeline \
  run.clearml.enabled=true \
  run.clearml.execution=logging \
  run.output_dir=outputs/20260101_120000 \
  data.raw_dataset_id=<RAW_DATASET_ID>
```

Agent 実行は PipelineController を使う。
```bash
python -m tabular_analysis.cli task=pipeline \
  run.clearml.enabled=true \
  run.clearml.execution=pipeline_controller \
  run.clearml.queue_name=default \
  data.raw_dataset_id=<RAW_DATASET_ID>
```

### 2.1) Dry-run（plan だけ確認）
実行前に plan を確認し、タスク数と project 階層を把握します。
```bash
python -m tabular_analysis.cli task=pipeline --dry-run \
  run.clearml.enabled=true \
  run.clearml.execution=pipeline_controller \
  data.raw_dataset_id=<RAW_DATASET_ID>
```

確認ポイント:
- preprocess/train/ensemble の件数
- fail_policy / limits / parallelism の値
- project layout の例が意図通りか

limits を超えた場合は、`pipeline.groups.*` の include/exclude を調整するか、
`pipeline.limits.max_*` を試験時のみ一時的に引き上げます。

### 2.2) Full run（安全に上限を引き上げる）
1) dry-run で plan を確認
2) queue/agent の空きと並列数を確認
3) `pipeline.limits.*` と `pipeline.parallelism.*` を明示指定して実行

例:
```bash
python -m tabular_analysis.cli task=pipeline \
  run.clearml.enabled=true \
  run.clearml.execution=pipeline_controller \
  run.clearml.queue_name=default \
  data.raw_dataset_id=<RAW_DATASET_ID> \
  pipeline.limits.max_preprocess_variants=5 \
  pipeline.limits.max_train_tasks=50 \
  pipeline.limits.max_ensemble_tasks=5 \
  pipeline.parallelism.max_concurrent_steps=6 \
  pipeline.parallelism.max_concurrent_train=4
```

### 2) Leaderboard レビュー
- `outputs/.../05_leaderboard/leaderboard.csv` と `recommendation.json` を確認
- `primary_metric` / `direction` が意図どおりか確認
- `split_hash` / `recipe_hash` が一致しているか確認（比較可能性の保証）

### 3) Promote（staging/production/archived）
- promote.stage: `staging | production | archived`（default: production）
- promote.set_champion: `true|false`（default: true）
- promote.rollback: `true|false`（default: false）
- champion registry: `work/registry/champions.json`（usecase_id ごとに管理）

Local mode での例:
```bash
python -m tabular_analysis.cli task=promote_model \
  run.clearml.enabled=false \
  run.output_dir=outputs/20260101_120000 \
  promotion.source_leaderboard_dir=outputs/20260101_120000/05_leaderboard \
  promote.stage=staging \
  promote.set_champion=true \
  promotion.note="initial candidate"
```

ClearML 有効時は leaderboard task_id も指定可能です:
```bash
python -m tabular_analysis.cli task=promote_model \
  run.clearml.enabled=true \
  promotion.source_leaderboard_dir=<leaderboard_task_id> \
  promote.stage=production \
  promote.set_champion=true \
  promotion.note="approved by ops"
```

`promotion.recommended_model_id` を直接指定することで、推薦を上書きできます。
`promotion.*` / `promote.*` はどちらも利用可能（promote が優先）。

## Post-Promotion Checks
- `promotion.json` / `summary.md` / `out.json` / `manifest.json` を確認
- `work/registry/champions.json` が更新されていることを確認
- ClearML では registry 登録の status と tags/properties を確認
  - tags: `stage:<stage>` / `usecase:<id>` / `process:promote_model`
  - properties: `metric` / `score` / `split_hash` / `recipe_hash` / `processed_dataset_id`

## Rollback / Archive
- 不具合が出た場合は `promote.stage=archived` で該当モデルをアーカイブ
- 直前の champion へ戻す場合は `promote.rollback=true` を使う（rollback は `work/registry/champions.json` の履歴を参照）
- 直前に安定していたモデルを再度 `promote_model` で `production` に昇格
- デプロイ側は `registry_model_id` / `model_id` を元に復旧

## Troubleshooting
- `model_bundle.joblib` が見つからない: train 出力か ClearML の artifact を確認
- registry 登録失敗: ClearML 認証 / ネットワーク / registry 側の権限を確認
- UI 契約が疑わしい: `python -m tabular_analysis.doctor --lint-run <output_dir>` を実行

## Outputs
- 共通: `config_resolved.yaml`, `out.json`, `manifest.json`
- pipeline: `pipeline_run.json`, `report.md`
- promote_model: `promotion.json`, `summary.md`, `work/registry/champions.json`
