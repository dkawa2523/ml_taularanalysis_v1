# 監視・ドリフト・アラート

## ドリフト監視（drift）
- 設定: `conf/monitor/base.yaml`
- 既定: `monitor.drift.enabled=false`
- 指標: `psi`, `ks`
- しきい値: `monitor.drift.alert_thresholds`（例: `psi: 0.2`）
- 実装: `src/tabular_analysis/monitoring/drift.py`

## アラート
- 有効化: `run.alerts.enabled=true`（または `alerts.enabled`）
- 送信先:
  - file: `alerts.jsonl`（既定で有効）
  - stdout: `run.alerts.sinks.stdout.enabled`
  - webhook: `run.alerts.sinks.webhook.url`
- 実装: `src/tabular_analysis/ops/alerting.py`

## 運用メモ
- drift/alert の有効化は **ジョブ単位** で制御
- 詳細手順は `docs/16_OPERATIONS_RUNBOOK.md` を参照
