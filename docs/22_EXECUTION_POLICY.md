# 22_EXECUTION_POLICY（実行ポリシー）

Grid/HPO の拡張でタスク数が爆発しないように、pipeline が **exec_policy** を基準に
queue/上限/重い機能の有効化を統一します。

## 設定場所（Hydra）
`conf/exec_policy/base.yaml` がデフォルトです。`conf/config.yaml` の defaults に追加されています。

主なキー：
- `exec_policy.limits.max_jobs`：pipeline が **生成して良い train job 数の上限**
- `exec_policy.limits.max_models`：leaderboard/report に載せる最大モデル数
- `exec_policy.limits.max_hpo_trials`：**モデルごとの HPO trials 上限**（0 は無制限）
- `exec_policy.queues`：process/モデル種別ごとの queue
- `exec_policy.selection`：重い機能のデフォルト OFF（calibration/uncertainty/ci）

## pipeline の enforcing
pipeline は組合せ生成時に `limits.max_jobs` を適用し、超過分は実行しません。
`pipeline_run.json` には以下を明記します。
- `planned_jobs`
- `executed_jobs`
- `skipped_due_to_policy`

`pipeline.grid.max_jobs` は互換性のため残していますが、**exec_policy 側が優先**されます。
デフォルト設定では `${exec_policy.limits.max_jobs}` に揃えています。

## Plan / Dry-run
実行せずに「何ジョブ走るか」を確認する場合は plan モードを使います。

```
pipeline.plan_only=true
```

互換エイリアス（同じ意味）：
- `pipeline.plan=true`
- `pipeline.dry_run=true`

plan モードでも `pipeline_run.json` を出力します（`executed_jobs=0`）。

## 重い機能の selection
`exec_policy.selection.<feature>=false` のとき pipeline は **強制的に OFF** にします。
現在の対象：
- `calibration` → `eval.calibration.enabled`
- `uncertainty` → `eval.uncertainty.enabled`
- `ci` → `eval.ci.enabled`

## ClearML queue の選択
ClearML 有効時のみ queue 設定を使います（local/logging は no-op）。

### Process ごとの queue
`exec_policy.queues` に process 名を指定できます。
デフォルトは `exec_policy.queues.default`（`run.clearml.queue_name` にフォールバック）。

### モデル単位の queue
次の 2 つを組み合わせて指定できます。
- `exec_policy.queues.model_variants`：モデル名→queue の個別指定
- `exec_policy.queues.heavy_model_variants`：重いモデルを `train_model_heavy` queue へ振り分け

## 例：CLI で上限と queue を上書き
```
exec_policy.limits.max_jobs=20 \
exec_policy.limits.max_models=5 \
exec_policy.limits.max_hpo_trials=3 \
exec_policy.queues.default=cpu_queue \
exec_policy.queues.train_model_heavy=gpu_queue \
exec_policy.queues.heavy_model_variants=[xgboost,lgbm]
```
